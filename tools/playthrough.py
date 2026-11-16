"""Capture genuine Ren'Py execution; aggregate actual Say source-position union.

The CLI never interprets .rpy branches. catalog.scan only supplies the comparison
set of source Say positions. Every captured text and choice is emitted by Ren'Py.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,sys,time
from catalog import scan
from release import story_digest

# Shared public fingerprint entry point for the offline reader.
source_fingerprint = story_digest
PROJECT=Path(__file__).resolve().parents[1]
ROOT=PROJECT
from paths import WORK, SDK
ROUTES=('haruka','chinatsu','rin','akari')

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    temp.replace(path)

def runtime_digest(project=PROJECT):
    project=Path(project)
    h=hashlib.sha256()
    files=[project/'game/core.rpy',project/'game/flow.rpy',project/'game/screens.rpy',project/'game/author_playthrough.rpy']
    files+=sorted((project/'game/story').glob('*.rpy'))
    files+=sorted((project/'game/data').glob('*.json'))
    for p in files:
        h.update(p.relative_to(project).as_posix().encode());h.update(b'\0');h.update(p.read_bytes());h.update(b'\0')
    return h.hexdigest()

def copied_story_digest(project):
    h=hashlib.sha256();game=project/'game'
    for path in sorted((game/'story').glob('*.rpy')):
        h.update(path.relative_to(game).as_posix().encode('utf8'));h.update(b'\0');h.update(path.read_bytes());h.update(b'\0')
    return h.hexdigest()

def private_project(directory):
    """Isolate BOTH Ren'Py save locations. Assets alone are read-only links."""
    target=directory/'project';game=target/'game'
    if target.exists():shutil.rmtree(target)
    game.mkdir(parents=True)
    source=PROJECT/'game'
    for p in source.iterdir():
        if p.name in ('saves','cache','screenshots'):continue
        q=game/p.name
        if p.name in ('images','audio','fonts'):
            q.symlink_to(p.resolve(),target_is_directory=True)
        elif p.is_dir():shutil.copytree(p,q)
        elif p.suffix in ('.rpy','.rpyc') or p.name=='script_version.txt':shutil.copy2(p,q)
    profile=directory/'profile'
    if profile.exists():shutil.rmtree(profile)
    return target,profile

def validate_run(directory):
    metadata=json.loads((directory/'run.json').read_text())
    lines=[json.loads(line) for line in (directory/'events.jsonl').read_text().splitlines()]
    assert lines and lines[0]['kind']=='run_start','Missing native run_start'
    expected='ending' if metadata['completed'] else 'checkpoint'
    assert lines[-1]['kind']==expected,'Missing native ending/checkpoint'
    assert bool(lines[-1]['completed'])==bool(metadata['completed'])
    assert metadata['say_count']==sum(x['kind']=='say' for x in lines)
    assert metadata['choice_count']==sum(x['kind']=='choice' for x in lines)
    if metadata['completed']:
        assert lines[-1]['route_id']==metadata['route_id']
    return metadata,lines

def aggregate(output,case_ids,source_hash,runtime_hash,publish_evidence=True):
    _,source_report,source_rows=scan()
    chapter_ids=set(json.loads((PROJECT/'game/data/chapters.json').read_text()))
    expected={('game/'+x['source'].removeprefix('game/'),x['line']):x for x in source_rows if x['chapter'] in chapter_ids}
    observed={};runs=[];completed=set();errors=[]
    for case_id in case_ids:
        directory=output/case_id
        if not (directory/'run.json').is_file():
            errors.append({'path_id':case_id,'error':'Missing completed capture metadata'});continue
        try:meta,events=validate_run(directory)
        except Exception as exc:
            errors.append({'path_id':case_id,'error':str(exc)});continue
        if meta['source_fingerprint']!=source_hash or meta['runtime_fingerprint']!=runtime_hash:
            errors.append({'path_id':case_id,'error':'Source/runtime fingerprint differs'});continue
        meta=dict(meta,events=case_id+'/events.jsonl',metadata=case_id+'/run.json')
        runs.append(meta)
        if meta['completed']:completed.add(meta['route_id'])
        for item in events:
            if item['kind']!='say':continue
            position=(item['source'],item['line'])
            if position not in expected:
                errors.append({'path_id':case_id,'error':'Native Say source position not in current source catalog','source':position[0],'line':position[1]});continue
            size=len(item['text'])
            if position not in observed or observed[position]['characters']<size:
                observed[position]={'characters':size,'chapter':item['chapter'],'text':item['text'],'paths':[case_id],'node_id':item['node_id']}
            elif case_id not in observed[position]['paths']:observed[position]['paths'].append(case_id)
    uncovered=[{'source':key[0],'line':key[1],'chapter':row['chapter'],'text':row['text']} for key,row in expected.items() if key not in observed]
    chapters={}
    for row in observed.values():chapters[row['chapter']]=chapters.get(row['chapter'],0)+row['characters']
    current_hash=story_digest()
    current_runtime=runtime_digest()
    evidence={'format_version':1,'story_sha256':source_hash,'current_story_sha256':current_hash,'runtime_sha256':runtime_hash,'current_runtime_sha256':current_runtime,'runtime_changed':current_runtime!=runtime_hash,'native_script':True,'text_only':True,'total_characters':sum(x['characters'] for x in observed.values()),'completed_routes':sorted(completed),'uncovered_story_lines':uncovered,'observed_story_nodes':len(observed),'source_story_nodes':len(expected),'source_characters':sum(len(x['text']) for x in expected.values()),'chapters':chapters,'source_changed':current_hash!=source_hash,'errors':errors,'runs':runs,'measurement':'Actual native Say source-position union. Same source position with dynamic text variants contributes only its maximum observed length; shared chapters count once.'}
    index={'format_version':1,'source_fingerprint':source_hash,'runtime_fingerprint':runtime_hash,'runs':runs,'union':{'characters':evidence['total_characters'],'nodes':len(observed),'chapters':chapters},'coverage':{'source_nodes':len(expected),'uncovered_nodes':len(uncovered),'completed_routes':sorted(completed),'errors':errors,'source_changed':evidence['source_changed'],'runtime_changed':evidence['runtime_changed']}}
    write_json(output/'index.json',index)
    if publish_evidence:
        write_json(PROJECT/'docs/playthrough-coverage.json',evidence)
    write_json(output/'coverage.json',evidence)
    write_json(output/'say-union.json',[{'source':key[0],'line':key[1],**value} for key,value in sorted(observed.items())])
    print(json.dumps({'native_characters':evidence['total_characters'],'completed_routes':evidence['completed_routes'],'uncovered_nodes':len(uncovered),'errors':len(errors),'source_changed':evidence['source_changed'],'index':str(output/'index.json')},ensure_ascii=False),flush=True)
    return evidence

def execute(case,output,args,source_hash,runtime_hash):
    case_id=case['path_id']
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',case_id):raise ValueError('Invalid path_id '+case_id)
    if case['route_id'] not in ROUTES:raise ValueError('Invalid route '+case['route_id'])
    variant=int(case.get('variant',0))
    if variant not in (0,1):raise ValueError('variant must be 0 (first) or 1 (second)')
    directory=output/case_id;directory.mkdir(parents=True,exist_ok=True)
    if args.resume and (directory/'run.json').is_file():
        try:
            old,_=validate_run(directory)
            if old['source_fingerprint']==source_hash and old['runtime_fingerprint']==runtime_hash and old['variant']==variant and old.get('choices',{})==case.get('choices',{}) and old.get('stop_after')==args.stop_after:
                print('REUSE',case_id,flush=True);return True
        except Exception:pass
    (directory/'run.json').unlink(missing_ok=True)
    project,profile=private_project(directory)
    if copied_story_digest(project)!=source_hash:raise RuntimeError("Story changed while creating private snapshot; retry after writer finishes")
    if runtime_digest(project)!=runtime_hash:raise RuntimeError("Runtime/data changed while creating private snapshot; retry after edits finish")
    settings={**case,'variant':variant,'directory':str(directory),'source_fingerprint':source_hash,'runtime_fingerprint':runtime_hash,'max_menus':args.max_menus,'stop_after':args.stop_after}
    write_json(directory/'case.json',settings)
    env=os.environ.copy();env.update(AFTER_OBSERVING_AUTHOR='1',AFTER_OBSERVING_CAPTURE='1',AFTER_OBSERVING_CAPTURE_CASE=str(directory/'case.json'),SDL_AUDIODRIVER='dummy',LIBGL_ALWAYS_SOFTWARE='1',DISPLAY=args.display)
    command=[str(args.sdk/'renpy.sh'),str(project),'--savedir',str(profile),'test','playthrough','--overwrite-screenshots']
    print('RUN',case_id,flush=True);start=time.monotonic()
    try:
        with (directory/'native.log').open('w') as log:result=subprocess.run(command,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=args.timeout)
        if result.returncode:raise RuntimeError('Native process exited '+str(result.returncode))
        meta,_=validate_run(directory)
        if not args.stop_after and not meta['completed']:raise RuntimeError('Did not reach requested native ending')
        print('DONE',case_id,meta['say_count'],'Say',round(time.monotonic()-start,2),'s',flush=True)
        return True
    except Exception as exc:
        write_json(directory/'failure.json',{'path_id':case_id,'error':str(exc),'native_log':str(directory/'native.log')})
        print('FAILED',case_id,str(exc),str(directory/'native.log'),flush=True);return False

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--routes',nargs='+',choices=ROUTES,default=list(ROUTES))
    parser.add_argument('--variants',nargs='+',choices=['first','second'],default=['first','second'])
    parser.add_argument('--case-file',type=Path,help='JSON cases[] with path_id, route_id, variant (0/1), choices {menu_id or ordinal: zero-based index}; added to requested defaults')
    parser.add_argument('--only-cases',action='store_true')
    parser.add_argument('--output',type=Path,default=WORK/'playthrough')
    parser.add_argument('--sdk',type=Path,default=SDK)
    parser.add_argument('--display',default=os.environ.get('DISPLAY',':94'))
    parser.add_argument('--timeout',type=int,default=1800)
    parser.add_argument('--max-menus',type=int,default=150)
    parser.add_argument('--stop-after',help='Development smoke capture only; never claims a completed route')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--aggregate-only',action='store_true')
    args=parser.parse_args();args.sdk=args.sdk.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    cases=[] if args.only_cases else [{'path_id':route+'-'+variant,'route_id':route,'variant':0 if variant=='first' else 1,'choices':{}} for route in args.routes for variant in args.variants]
    if args.case_file:
        raw=json.loads(args.case_file.read_text());cases+=raw['cases'] if isinstance(raw,dict) else raw
    if not cases:parser.error('No capture cases requested')
    if len({x['path_id'] for x in cases})!=len(cases):parser.error('Duplicate path_id')
    source_hash=story_digest();runtime_hash=runtime_digest();failures=0
    if not args.aggregate_only:
        for case in cases:
            if not execute(case,output,args,source_hash,runtime_hash):failures+=1
    evidence=aggregate(output,[x['path_id'] for x in cases],source_hash,runtime_hash,publish_evidence=not bool(args.stop_after))
    if failures or evidence['errors'] or evidence['source_changed'] or evidence['runtime_changed']:raise SystemExit(1)
    full_request=(not args.only_cases and not args.stop_after and set(args.routes)==set(ROUTES) and set(args.variants)=={'first','second'})
    if full_request and (evidence['uncovered_story_lines'] or set(evidence['completed_routes'])!=set(ROUTES)):
        raise SystemExit('Complete capture requested, but native story coverage or route endings remain incomplete')
if __name__=='__main__':main()
