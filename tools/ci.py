"""Portable CI entry points. Source checks, native runs and releases share guards."""
import argparse,hashlib,json,os,re,shutil,subprocess,sys,tarfile,zipfile,urllib.request,urllib.error,platform
from pathlib import Path
from paths import PROJECT as R, WORK, SDK, DIST, VERSION, PACKAGE

def run(*command,env=None,cwd=R):
    subprocess.run(list(map(str,command)),cwd=cwd,env=env,check=True)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()

def sdk():
    lock=json.loads((R/'.github/toolchain.json').read_text())
    if os.environ.get('RENPY_SDK'):
        if not (SDK/'renpy.sh').is_file():raise SystemExit('RENPY_SDK must point to a complete SDK')
        print('Using explicitly supplied SDK:',SDK);return
    archive=WORK/'cache/renpy-sdkarm.tar.bz2';archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists() or sha(archive)!=lock['renpy_sha256']:
        archive.unlink(missing_ok=True)
        run('curl','--fail','--location','--retry','3','--limit-rate',str(lock['download_bytes_per_second']),lock['renpy_url'],'--output',archive)
    if sha(archive)!=lock['renpy_sha256']:raise SystemExit('SDK checksum mismatch')
    # Re-extract the verified archive rather than trusting a mutable extracted cache.
    if SDK.exists():shutil.rmtree(SDK)
    SDK.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive) as tf:tf.extractall(SDK.parent,filter='data')
    if not (SDK/'renpy.sh').is_file():raise SystemExit('SDK archive layout differs from the lock')

def deps():
    wheels=WORK/'cache/python-wheels';wheels.mkdir(parents=True,exist_ok=True)
    for line in (R/'requirements-ci.lock').read_text().splitlines():
        name,version=line.split()[0].split('==');allowed=set(re.findall(r'sha256:([a-f0-9]{64})',line))
        with urllib.request.urlopen('https://pypi.org/pypi/'+name+'/'+version+'/json',timeout=30) as f:metadata=json.load(f)
        abi='cp'+str(sys.version_info.major)+str(sys.version_info.minor)
        arch='aarch64' if platform.machine() in ('aarch64','arm64') else 'x86_64'
        candidates=[x for x in metadata['urls'] if x['filename'].endswith('.whl') and (x['filename'].endswith('py3-none-any.whl') or (abi+'-'+abi+'-manylinux' in x['filename'] and arch in x['filename']))]
        if not candidates:raise SystemExit('No locked wheel for this Python/platform: '+name)
        item=candidates[0];path=wheels/item['filename'];expected=item['digests']['sha256']
        if expected not in allowed:raise SystemExit('Wheel not in requirements lock')
        if not path.exists() or sha(path)!=expected:
            run('curl','--fail','--location','--retry','3','--limit-rate','3000000',item['url'],'--output',path)
        if sha(path)!=expected:raise SystemExit('Wheel checksum differs')
    run(sys.executable,'-m','pip','install','--no-index','--no-deps','--require-hashes','--find-links',wheels,'-r',R/'requirements-ci.lock')

def baseline():
    """Seed statement IDs before compilation; do not invent fresh IDs each build."""
    source=R/'save-baseline'
    repo=os.environ.get('GITHUB_REPOSITORY')
    if repo and re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):
        headers={'User-Agent':'after-observing-build'}
        token=os.environ.get('GITHUB_TOKEN')
        if token:headers['Authorization']='Bearer '+token
        try:
            request=urllib.request.Request('https://api.github.com/repos/'+repo+'/releases/latest',headers=headers)
            with urllib.request.urlopen(request,timeout=30) as f:release=json.load(f)
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
            release=None
        if release:
            assets={x['name']:x for x in release['assets']}
            if not {'save-baseline.zip','SHA256SUMS.txt'}.issubset(assets):raise SystemExit('Latest stable release lacks its save baseline')
            cache=WORK/'baseline-download';cache.mkdir(parents=True,exist_ok=True)
            for name in ['save-baseline.zip','SHA256SUMS.txt']:
                url=assets[name]['browser_download_url']
                if not url.startswith('https://github.com/'+repo+'/releases/download/'):raise SystemExit('Unexpected baseline URL')
                run('curl','--fail','--location','--retry','3','--limit-rate','3000000',url,'--output',cache/name)
            expected=next((line.split('  ',1)[0] for line in (cache/'SHA256SUMS.txt').read_text().splitlines() if line.endswith('  save-baseline.zip')),None)
            if not expected or sha(cache/'save-baseline.zip')!=expected:raise SystemExit('Released baseline checksum differs')
            source=cache/'extracted'
            if source.exists():shutil.rmtree(source)
            source.mkdir()
            with zipfile.ZipFile(cache/'save-baseline.zip') as z:
                for name in z.namelist():
                    if name.startswith('/') or '..' in Path(name).parts:raise SystemExit('Unsafe save baseline')
                z.extractall(source)
    manifest=json.loads((source/'manifest.json').read_text())
    for row in manifest['files']:
        if not re.fullmatch(r'game/(?:story/)?[A-Za-z0-9_]+\.rpyc',row['path']):raise SystemExit('Unexpected save baseline member')
        p=source/row['path'];target=R/row['path']
        if sha(p)!=row['sha256']:raise SystemExit('Save baseline checksum mismatch')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    print('Seeded',len(manifest['files']),'compiled statement-ID baselines.')

def static():
    from release import check
    check(static=True)
    # Public source must contain materialized files, not local absolute aliases.
    bad=[]
    for p in (R/'game').rglob('*'):
        if p.is_symlink():bad.append(str(p.relative_to(R)))
        if p.is_file() and p.stat().st_size>=100*1024*1024:bad.append('oversized Git blob: '+str(p.relative_to(R)))
    secret=re.compile(rb'(?:sk-proj-|gh[pousr]_)[A-Za-z0-9_-]{30,}')
    for folder in ['game','tools','.github']:
        for p in (R/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.rpy','.py','.json','.yml','.yaml','.txt') and secret.search(p.read_bytes()):bad.append('credential-like value: '+str(p.relative_to(R)))
    if bad:raise SystemExit('\n'.join(bad))
    print('Static source, asset and credential checks passed.')

def native():
    static()
    if not os.environ.get('DISPLAY'):raise SystemExit('Run native checks under xvfb-run on Linux')
    run(sys.executable,'tools/layout_rows.py')
    run(sys.executable,'tools/playthrough.py','--sdk',SDK,'--resume')
    run(sys.executable,'tools/release.py','check')
    q=WORK/'qa/native-ui';project=q/'project'
    if q.exists():shutil.rmtree(q)
    (project/'docs').mkdir(parents=True)
    shutil.copytree(R/'game',project/'game',ignore=shutil.ignore_patterns('images','audio','fonts','saves','cache','*.rpyc','*.rpyb'))
    for key in ['images','audio','fonts']:(project/'game'/key).symlink_to(R/'game'/key,target_is_directory=True)
    shutil.copy2(R/'docs/layout-rows.json',project/'docs/layout-rows.json')
    env=os.environ.copy();env.update(AFTER_OBSERVING_AUTHOR='1',SDL_AUDIODRIVER='dummy',LIBGL_ALWAYS_SOFTWARE='1',AO_SCREENSHOT_DIR=str(q/'screens'))
    with (q/'native.log').open('w') as f:
        result=subprocess.run([str(SDK/'renpy.sh'),str(project),'--savedir',str(q/'profile'),'test','shell','c_review','story_navigation','visual_references','visual_assets.dialogue_layout','--overwrite-screenshots'],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
    print((q/'native.log').read_text()[-3000:]);result.check_returncode()

def build():
    run(sys.executable,'tools/release.py','build')
    run(sys.executable,'tools/release.py','verify')
    run(sys.executable,'tools/package_smoke.py','--display',os.environ.get('DISPLAY',':99'))
    run(sys.executable,'tools/reader.py')
    bundle()

def bundle():
    DIST.mkdir(exist_ok=True,parents=True)
    from release import runtime_digest,story_digest
    evidence=WORK/'evidence';evidence.mkdir(exist_ok=True,parents=True)
    for name in ['playthrough-coverage.json','body-statistics.json','reader-report.json','package-verification.json','package-smoke.json','package-smoke.md']:
        p=R/'docs'/name
        if p.exists():shutil.copy2(p,evidence/name)
    for p in (WORK/'playthrough').glob('*/native.log'):shutil.copy2(p,evidence/(p.parent.name+'.log'))
    for p in [WORK/'qa/native-ui/native.log',WORK/'qa/lint.log',WORK/'qa/build.log']:
        if p.exists():shutil.copy2(p,evidence/(p.parent.parent.name+'-'+p.name))
    coverage=json.loads((R/'docs/playthrough-coverage.json').read_text())
    if coverage['runtime_sha256']!=runtime_digest() or coverage['story_sha256']!=story_digest():raise SystemExit('Evidence changed before bundling')
    with zipfile.ZipFile(DIST/'verification-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(evidence.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(evidence))
    # A release carries its own next-build baseline. Keep this separate from saves.
    stage=WORK/'staging'/PACKAGE
    files=[]
    with zipfile.ZipFile(DIST/'save-baseline.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted((stage/'game').rglob('*.rpyc')):
            rel=p.relative_to(stage).as_posix();z.write(p,rel);files.append({'path':rel,'sha256':sha(p)})
        z.writestr('manifest.json',json.dumps({'version':game_version(),'files':files},indent=2))
    paths=[DIST/name for name in [PACKAGE+'-win.zip',PACKAGE+'-linux.tar.bz2',PACKAGE+'-reader.html','verification-evidence.zip','save-baseline.zip']]
    if not all(p.is_file() for p in paths):raise SystemExit('Release output is incomplete')
    (DIST/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in paths))

def tag(tag):
    version=game_version()
    if not re.fullmatch(r'v[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:-[A-Za-z0-9.]+)?',tag):raise SystemExit('Invalid release tag')
    if tag!='v'+version:raise SystemExit('Release tag must exactly match game version: v'+version)

def game_version():return re.search(r'define config.version = "([^"]+)"',(R/'game/core.rpy').read_text())[1]

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['sdk','deps','baseline','static','native','build','bundle','tag']);parser.add_argument('--tag');a=parser.parse_args()
    if a.command=='tag':tag(a.tag or '')
    else:globals()[a.command]()
