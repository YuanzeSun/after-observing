"""Publish verified outputs. No credentials are stored in this repository."""
import argparse,hashlib,json,os,re,subprocess,tarfile,urllib.request,urllib.error,urllib.parse,zipfile
from pathlib import Path
from paths import PROJECT as R, WORK, DIST, VERSION, PACKAGE

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def verified_files():
    sums=DIST/'SHA256SUMS.txt';files=[]
    allowed={PACKAGE+'-win.zip',PACKAGE+'-linux.tar.bz2',PACKAGE+'-reader.html','verification-evidence.zip','save-baseline.zip'}
    for line in sums.read_text().splitlines():
        value,name=line.split('  ',1)
        if name not in allowed or Path(name).name!=name:raise SystemExit('Unexpected release asset')
        p=DIST/name
        if not p.is_file() or p.is_symlink() or digest(p)!=value:raise SystemExit('Release checksum mismatch: '+name)
        files.append(p)
    if {p.name for p in files}!=allowed:raise SystemExit('Incomplete release manifest')
    return files+[sums]

def api(method,url,body=None):
    token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:raise SystemExit('GitHub publishing needs the workflow GITHUB_TOKEN')
    data=None if body is None else json.dumps(body).encode()
    request=urllib.request.Request(url,data=data,method=method,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'after-observing-release'})
    with urllib.request.urlopen(request,timeout=60) as f:return json.load(f) if f.status!=204 else None

def verify_uploaded(files,assets):
    actual={a['name']:a for a in assets}
    for p in files:
        a=actual.get(p.name)
        if not a or a['size']!=p.stat().st_size or a.get('digest')!='sha256:'+digest(p):raise SystemExit('Uploaded asset name/size/digest differs: '+p.name)

def github(args):
    if args.tag!='v'+VERSION:raise SystemExit('Tag must match config.version')
    files=verified_files();repository=os.environ.get('GITHUB_REPOSITORY','YuanzeSun/after-observing')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):raise SystemExit('Invalid repository')
    print('Verified release:',repository,args.tag,[p.name for p in files])
    if args.dry_run:return
    base='https://api.github.com/repos/'+repository
    try:release=api('GET',base+'/releases/tags/'+urllib.parse.quote(args.tag,safe=''))
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
        preview=json.loads((R/'.github/release-policy.json').read_text())['prerelease']
        release=api('POST',base+'/releases',{'tag_name':args.tag,'target_commitish':commit,'name':'观测结束以后 '+VERSION,'draft':True,'prerelease':preview or '-' in VERSION,'body':(R/'docs/RELEASE_NOTES.md').read_text()})
    if not release['draft']:
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
        if release['target_commitish']!=commit:raise SystemExit('Published tag belongs to a different commit')
        names={p.name for p in files};existing={a['name']:a for a in release['assets']}
        if not names.issubset(existing):raise SystemExit('Published release is incomplete; refusing overwrite')
        sums=existing['SHA256SUMS.txt'];url=sums['browser_download_url']
        if not url.startswith('https://github.com/'+repository+'/releases/download/'):raise SystemExit('Unexpected checksum URL')
        with urllib.request.urlopen(url,timeout=30) as f:raw=f.read(131073)
        if len(raw)>131072:raise SystemExit('Unexpected checksum size')
        for line in raw.decode().splitlines():
            value,name=line.split('  ',1)
            if name not in existing or existing[name].get('digest')!='sha256:'+value:raise SystemExit('Published asset digest does not match its manifest')
        print('Same commit is already completely published; preserved immutable release:',release['html_url']);return
    if not release['draft'] and args.draft:raise SystemExit('Refusing to modify an already published release')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
    if release['target_commitish']!=commit:
        try:
            ref=api('GET',base+'/git/ref/tags/'+urllib.parse.quote(args.tag,safe=''))
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
            ref=None
        if ref and ref['object']['sha']!=commit:raise SystemExit('Existing tag points to a different commit; use a new version')
        release=api('PATCH',base+'/releases/'+str(release['id']),{'target_commitish':commit})
    token=os.environ.get('GH_TOKEN') or os.environ['GITHUB_TOKEN']
    existing={a['name']:a for a in release['assets']}
    # GitHub normalizes non-ASCII asset names; remove only legacy generated aliases.
    for legacy in [VERSION+'.html',VERSION+'离线全文.html']:
        if legacy in existing:api('DELETE',base+'/releases/assets/'+str(existing[legacy]['id']))
    for p in files:
        if p.name in existing:
            a=existing[p.name]
            if a.get('digest')=='sha256:'+digest(p):continue
            if not release['draft']:raise SystemExit('Published assets are immutable; use a new version')
            api('DELETE',base+'/releases/assets/'+str(a['id']))
        url=release['upload_url'].split('{',1)[0]+'?'+urllib.parse.urlencode({'name':p.name})
        # curl reads the authorization from stdin, never from command arguments.
        headers='Authorization: Bearer '+token+'\nContent-Type: application/octet-stream\n'
        subprocess.run(['curl','--fail','--silent','--show-error','--request','POST','--header','@-','--data-binary','@'+str(p),url],input=headers.encode(),stdout=subprocess.DEVNULL,check=True)
    uploaded=api('GET',base+'/releases/'+str(release['id']))
    verify_uploaded(files,uploaded['assets'])
    if release['draft'] and not args.draft:api('PATCH',base+'/releases/'+str(release['id']),{'draft':False})
    print('Release uploaded:',release['html_url'])

def itch(args):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*',args.target):raise SystemExit('ITCH_TARGET must be account/project')
    files=verified_files();print('Verified itch target:',args.target)
    if args.dry_run:return
    if not os.environ.get('BUTLER_API_KEY'):raise SystemExit('Set BUTLER_API_KEY as a GitHub Actions secret')
    lock=json.loads((R/'.github/toolchain.json').read_text());archive=WORK/'cache/butler.zip';archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists() or digest(archive)!=lock['butler_sha256']:
        subprocess.run(['curl','--fail','--location','--retry','3','--limit-rate','3000000',lock['butler_url'],'--output',str(archive)],check=True)
    if digest(archive)!=lock['butler_sha256']:raise SystemExit('Butler checksum mismatch')
    tool=WORK/'butler';tool.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if name.startswith('/') or '..' in Path(name).parts:raise SystemExit('Unsafe butler archive')
        z.extractall(tool)
    executable=tool/'butler';executable.chmod(0o755)
    subprocess.run([str(executable),'version'],check=True)
    for channel,suffix,entry in [('windows','-win.zip','.exe'),('linux','-linux.tar.bz2','.sh')]:
        package=DIST/(PACKAGE+suffix);destination=WORK/'itch'/channel
        if destination.exists():__import__('shutil').rmtree(destination)
        destination.mkdir(parents=True)
        if suffix.endswith('.zip'):
            with zipfile.ZipFile(package) as z:
                for name in z.namelist():
                    if name.startswith('/') or '..' in Path(name).parts:raise SystemExit('Unsafe game archive')
                z.extractall(destination)
        else:
            with tarfile.open(package) as t:t.extractall(destination,filter='data')
        candidates=list(destination.glob('*/'+PACKAGE+entry))
        if len(candidates)!=1:raise SystemExit('Game launcher missing')
        game=candidates[0].parent
        (game/'.itch.toml').write_text('[[actions]]\nname = "play"\npath = '+json.dumps(candidates[0].name)+'\n')
        subprocess.run([str(executable),'push',str(game),args.target+':'+channel,'--userversion',VERSION],check=True)

def fetch(args):
    if args.tag!='v'+VERSION:raise SystemExit('Checkout the exact release tag before syncing')
    repo=os.environ.get('GITHUB_REPOSITORY','YuanzeSun/after-observing')
    release=api('GET','https://api.github.com/repos/'+repo+'/releases/tags/'+urllib.parse.quote(args.tag,safe=''))
    if release['draft']:raise SystemExit('Publish the GitHub release before syncing it to itch.io')
    assets={a['name']:a for a in release['assets']};names=[PACKAGE+'-win.zip',PACKAGE+'-linux.tar.bz2',PACKAGE+'-reader.html','verification-evidence.zip','save-baseline.zip','SHA256SUMS.txt']
    DIST.mkdir(exist_ok=True,parents=True)
    for name in names:
        if name not in assets:raise SystemExit('Release asset missing: '+name)
        url=assets[name]['browser_download_url']
        if not url.startswith('https://github.com/'+repo+'/releases/download/'):raise SystemExit('Unexpected release download URL')
        subprocess.run(['curl','--fail','--location','--retry','3','--limit-rate','3000000',url,'--output',str(DIST/name)],check=True)
    verified_files()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('provider',choices=['github','itch','fetch']);p.add_argument('--tag',default='v'+VERSION);p.add_argument('--target',default=os.environ.get('ITCH_TARGET',''));p.add_argument('--draft',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    globals()[a.provider](a)
