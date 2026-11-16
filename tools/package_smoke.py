"""Run native fragment checks with an extracted distribution's own launcher.

This is intentionally not a second full-playthrough claim. Ending fixtures are
the captured first Say of each real last chapter, from the accepted run index.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,shutil,subprocess,tarfile,time
from paths import PROJECT as R, WORK, DIST, PACKAGE
ROOT=R
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,default=DIST/(PACKAGE+'-linux.tar.bz2'));ap.add_argument('--index',type=Path,default=WORK/'playthrough/index.json');ap.add_argument('--display',default=':94');a=ap.parse_args()
 if not a.archive.is_file():raise SystemExit('Build and verify the Linux distribution first: '+str(a.archive))
 coverage=json.loads((R/'docs/playthrough-coverage.json').read_text())
 from release import story_digest
 from playthrough import runtime_digest
 assert coverage['story_sha256']==story_digest(),'story evidence is stale'
 assert coverage['runtime_sha256']==runtime_digest(),'runtime evidence is stale'
 assert coverage['completed_routes']==sorted(['haruka','chinatsu','rin','akari']),'four route completions required'
 assert coverage['uncovered_story_lines']==[],'full source coverage required before package checks'
 index=json.loads(a.index.read_text());fixtures={}
 assert index['source_fingerprint']==coverage['story_sha256'],'index story mismatch'
 assert index['runtime_fingerprint']==coverage['runtime_sha256'],'index runtime mismatch'
 for route in ['haruka','chinatsu','rin','akari']:
  prefix={'haruka':'h','chinatsu':'c','rin':'r','akari':'a'}[route]
  run=next(x for x in index['runs'] if x['route_id']==route and x['completed'])
  rows=[json.loads(line) for line in (a.index.parent/run['events']).read_text().splitlines()]
  first=next(row for row in rows if row.get('kind')=='say' and row.get('chapter')==prefix+'01')
  last=next(row for row in rows if row.get('kind')=='say' and row.get('chapter')==prefix+'10')
  fixtures[route]={'run_id':run['path_id'],'first':first,'last':last}
 original_hash=sha(a.archive);stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
 q=WORK/'qa'/('package-smoke-'+stamp);q.mkdir(parents=True)
 with tarfile.open(a.archive) as tar:
  members=tar.getmembers()
  for m in members:
   assert not m.name.startswith('/') and '..' not in Path(m.name).parts,'unsafe archive member'
  tar.extractall(q,filter='data')
 games=[p.parent.parent for p in q.glob('*/game/assets.rpa')];assert len(games)==1,games
 project=games[0];marker=project/'game/_release_build';assert marker.is_file();marker.unlink()
 shutil.copy2(R/'game/author_package_tests.rpy',project/'game/author_package_tests.rpy')
 fixture_file=q/'fixtures.json';fixture_file.write_text(json.dumps(fixtures,ensure_ascii=False,indent=2)+'\n')
 records=q/'records.jsonl';records.write_text('');screens=q/'screens';screens.mkdir()
 launchers=list(project.glob('*.sh'));assert len(launchers)==1,launchers
 launcher=launchers[0];env=os.environ.copy();env.update(DISPLAY=a.display,SDL_AUDIODRIVER='dummy',LIBGL_ALWAYS_SOFTWARE='1',AFTER_OBSERVING_AUTHOR='1',AO_PACKAGE_FIXTURES=str(fixture_file),AO_PACKAGE_RECORDS=str(records),AO_PACKAGE_SCREENSHOTS=str(screens))
 log=q/'native.log';started=time.time()
 with log.open('w') as f:
  # Even a distributed launcher requires an explicit base directory before the
  # developer `test` command; otherwise `test` is mistaken for a directory.
  completed=subprocess.run([str(launcher),str(project),'--savedir',str(q/'profile'),'test','package_smoke'],cwd=project,env=env,stdout=f,stderr=subprocess.STDOUT)
 output=log.read_text();events=[json.loads(line) for line in records.read_text().splitlines()]
 cases=re.search(r'Test cases\s*:\s*(\d+)\s*\|\s*(\d+) passed',output)
 assertions=re.search(r'Assertions\s*:\s*(\d+)\s*\|\s*(\d+) passed',output)
 route_set={'haruka','chinatsu','rin','akari'}
 content_ok=all({x['route'] for x in events if x['phase']==phase}==route_set for phase in ['entry-save-load','last-chapter-ending-reselect'])
 local_runtime=bool(events) and all(Path(x['runtime']).is_relative_to(project) and Path(x['renpy_module']).is_relative_to(project) for x in events)
 passed=completed.returncode==0 and '[rpytest] Status: PASSED' in output and content_ok and local_runtime and sha(a.archive)==original_hash
 report={'passed':passed,'native_exit_code':completed.returncode,'archive':str(a.archive),'archive_sha256':original_hash,'archive_unchanged':sha(a.archive)==original_hash,'launcher':str(launcher),'runtime_paths':sorted({x['runtime'] for x in events}),'renpy_module_paths':sorted({x['renpy_module'] for x in events}),'cases':{'total':int(cases[1]),'passed':int(cases[2])} if cases else None,'assertions':{'total':int(assertions[1]),'passed':int(assertions[2])} if assertions else None,'seconds':time.time()-started,'qa_project':str(project),'native_log':str(log),'screenshots':[str(p) for p in sorted(screens.glob('*.png'))],'records':events,'story_sha256':coverage['story_sha256'],'runtime_sha256':coverage['runtime_sha256'],'boundaries':['Uses extracted Linux .sh and its runtime; no SDK runner.','Keeps assets.rpa and verifies actual resource rendering; manual saves/load and chapter backups checked.','Only the QA extraction removes _release_build and injects the author test file. Original archives are unchanged.','Four route entries are tested with no completed-route awards. Last chapters start from real captured choice facts and completed events.','Ending checks are last-chapter fragments, not full packaged route playthroughs. Full native story coverage is evidenced separately.','Audio driver is dummy here. Actual 22-segment native audio output has a separate report.','No Windows physical-device validation is implied.']}
 (R/'docs/package-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (R/'docs/package-smoke.md').write_text('# Linux独立发行包片段烟测\n\n'+('通过。' if passed else '未通过，见日志。')+' 使用解压包自己的启动器与运行库，保留assets.rpa；没有调用SDK启动器。\n\n'+f"原生退出码：{completed.returncode}；用例：{report['cases']}；断言：{report['assertions']}。\n\n四线首次入口、真实第一句与RPA立绘、手动存读档变量恢复、章首备份、实际末章到结局UI及重选入口分别检查。末章前情来自正式全路径导出的真实第一Say，属于片段烟测；不把它写成包内完整通关。完整八路径与可达正文证据另见playthrough-coverage.json。\n\n原始发行包未修改；仅QA解压副本移除发布标记、注入作者工具。虚拟音频输出不计实际听音，Windows未实机验证。\n\n日志：`"+str(log)+'`\n\n截图目录：`'+str(screens)+'`\n\n归档SHA256：`'+original_hash+'`\n',encoding='utf-8')
 print(json.dumps({k:report[k] for k in ['passed','native_exit_code','cases','assertions','archive_sha256','launcher','seconds']},ensure_ascii=False,indent=2))
 if not passed:raise SystemExit(1)
if __name__=='__main__':main()
