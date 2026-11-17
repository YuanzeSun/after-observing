"""One entry point: check, lint, stage, build and verify. Complete-release guards are deliberate."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,shutil,subprocess,sys,ast,zipfile,tarfile,posixpath
from catalog import scan
from paths import PROJECT as R, WORK, SDK, DIST as DEST, VERSION, PACKAGE
ROOT=R;G=R/'game'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def story_digest():
 h=hashlib.sha256()
 for p in sorted((G/'story').glob('*.rpy')):
  h.update(p.relative_to(G).as_posix().encode());h.update(b'\0');h.update(p.read_bytes());h.update(b'\0')
 return h.hexdigest()
def runtime_digest():
 h=hashlib.sha256()
 files=[G/'core.rpy',G/'flow.rpy',G/'screens.rpy',G/'author_playthrough.rpy']+sorted((G/'story').glob('*.rpy'))+sorted((G/'data').glob('*.json'))
 for p in files:
  h.update(p.relative_to(R).as_posix().encode());h.update(b'\0');h.update(p.read_bytes());h.update(b'\0')
 return h.hexdigest()
def check(draft=False,static=False):
 scenes,report,rows=scan();assets=json.loads((G/'data/assets.json').read_text());problems=[]
 # Compare evidence against the exact generated catalog that will be shipped.
 (G/'data/scenes.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2)+'\n')
 for label in report['unexpected_labels']:problems.append('unregistered story label '+label)
 for key,s in scenes.items():
  if s['background'] not in assets['backgrounds']:problems.append(f'{key}: unknown background {s["background"]}')
  try:datetime.date.fromisoformat(s['date'])
  except ValueError:problems.append(f'{key}: invalid date')
  if s['music'] and s['music'] not in ('theme','club','daily','night','quiet','tender','ending','haruka','chinatsu','rin','akari','playful','waiting','rain','distance','resolve','warm'):problems.append(f'{key}: unknown music')
  if s.get('phone') and s['phone'] not in 'hcra':problems.append(f'{key}: unknown phone speaker')
  for actor in s['actors']:
   if actor[0] not in 'hcra' or actor[1] not in ('uniform','winter','casual') or actor[2] not in ('normal','smile','puzzled','displeased','shy','sad'):problems.append(f'{key}: invalid actor {actor}')
   if len(actor)>3 and actor[3] not in ('pose1','pose2'):problems.append(f'{key}: invalid pose')
 referenced=set(assets.get('npc_portraits',{}).values())|set(assets.get('references',{}).values())|set(assets['backgrounds'].values())|set(assets['cgs'].values())|{'images/v11/title.png'}
 photo_keys=['01_bus_bag','02_shop_shutter','03_school_rain','04_platform_green','05_lodge_waiting','06_ticket_window','07_laundry_light','08_bicycle_return','09_shop_box','10_closed_stall','11_last_bus','12_door_lamp']
 referenced.update('images/release/photo_'+key+'.png' for key in photo_keys)
 for x in assets['sprites']:
  if x['kind']=='sprite':referenced.add(x['path'])
 for p in (G/'story').glob('*.rpy'):
  for key in re.findall(r'\$\s*cg\([\'"]([^\'"]+)',p.read_text()):
   if key not in assets['cgs']:problems.append('unknown CG '+key)
  for key in re.findall(r'\$\s*photo\([\'"]([^\'"]+)',p.read_text()):referenced.add('images/release/photo_'+key+'.png')
 if not draft:
  problems+=['missing chapter '+x for x in report['missing_chapters']]
  problems+=['empty chapter '+x for x in json.loads((G/'data/chapters.json').read_text()) if not report['chapters'].get(x)]
  if not 400000<=report['total']<=600000:problems.append('body outside 400k–600k: '+str(report['total']))
  for prefix in 'hcra':
   count=sum(n for key,n in report['chapters'].items() if key.startswith(prefix))
   if count<90000:problems.append(f'route {prefix} incomplete: {count} (<90k)')
  for path in sorted(referenced):
   if not (G/path).is_file():problems.append('missing asset '+path)
  music=json.loads((G/'data/music.json').read_text())
  if len(music)!=16:problems.append('music manifest must contain 16 tracks')
  for row in music:
   if not (R/row['file']).is_file():problems.append('missing music '+row['file'])
  if static:
   report['problems']=problems
   (R/'docs/body-statistics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
   if problems:raise SystemExit('\n'.join(problems))
   print(json.dumps({'characters':report['total'],'chapters':report['chapter_count'],'scenes':len(scenes),'problems':problems}))
   return assets,referenced
  evidence=R/'docs/playthrough-coverage.json'
  if not evidence.exists():problems.append('native playthrough evidence missing')
  else:
   coverage=json.loads(evidence.read_text())
   if coverage.get('story_sha256')!=story_digest():problems.append('native playthrough evidence belongs to a different story revision')
   if coverage.get('runtime_sha256')!=runtime_digest():problems.append('native playthrough evidence belongs to a different runtime/UI/data revision')
   if coverage.get('errors')!=[]:problems.append('native playthrough evidence contains capture errors')
   if not 400000<=coverage.get('total_characters',0)<=600000:problems.append('native reachable body outside 400k–600k')
   if set(coverage.get('completed_routes',[]))!={'haruka','chinatsu','rin','akari'}:problems.append('four native route completions required')
   if coverage.get('uncovered_story_lines')!=[]:problems.append('uncovered story pages remain')
 report['problems']=problems
 (R/'docs/body-statistics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'characters':report['total'],'chapters':report['chapter_count'],'scenes':len(scenes),'problems':problems},ensure_ascii=False,indent=2))
 if problems:raise SystemExit(1)
 return assets,referenced

def stage():
 assets,used=check(False);out=WORK/'staging'/PACKAGE
 if out.exists():shutil.rmtree(out)
 out.mkdir(parents=True)
 shutil.copytree(G,out/'game',ignore=shutil.ignore_patterns('saves','cache','log.txt','errors.txt','traceback.txt','screenshots','__pycache__','*.rpyb'))
 for p in (out/'game').glob('author_*'):
  if p.is_file():p.unlink()
 (out/'game/_release_build').write_text(VERSION+'\n')
 (out/'README.md').write_text('''# 观测结束以后 1.1

全年龄高中天文社恋爱视觉小说，四条独立路线。

## 开始游玩

请先完整解压整个发行包，再从解压后的文件夹启动游戏：

- 64位Windows：双击 `AfterObserving-1.1.exe`。
- Linux：在图形桌面环境运行 `AfterObserving-1.1.sh`。

游戏包含所需运行库、图像、音乐和字体，不需要另装Ren’Py、Python，也不需要另一个发行包。请保留同一目录内的 `game`、`lib` 等文件和文件夹；只单独拷贝启动文件无法游玩。

## 阅读与存档

点击、空格或Enter继续；右键或Esc打开菜单；滚轮向上回退。自动播放和快进会等待你选择选项。

共通篇末会明确选择下一次想单独见面的人，四条路线均可首次游玩，没有隐藏好感或顺序锁。章节连续衔接，章首会留下自动备份；也可随时手动存档、命名、读取或删除。结局可以重选另一条路线。回想使用实际已读前情，结束回放后恢复主线进度。

1.1及其维护版本共用存档目录，升级后可直接继续读取已有存档与鉴赏记录；不读取1.0的旧存档。

## 素材署名与许可

音乐、字体及引擎与其第三方组件的许可文件在 `LICENSES` 文件夹。游戏内“制作与素材署名”提供曲目和来源说明。
'''.replace('AfterObserving-1.1',PACKAGE).replace('# 观测结束以后 1.1','# 观测结束以后 '+VERSION),encoding='utf-8')
 # Keep all registered public/private photo props used by scripts, but no obsolete sprite revisions.
 used.update('images/release/'+p.name for p in (G/'images/release').glob('photo_*.png'))
 for p in (out/'game/images').rglob('*'):
  if p.is_file() and p.relative_to(out/'game').as_posix() not in used:p.unlink()
 licenses=out/'LICENSES';licenses.mkdir(exist_ok=True)
 shutil.copy2(out/'game/audio/release/LICENSES.txt',licenses/'Music-and-Sound.txt');shutil.copy2(out/'game/fonts/LICENSE.txt',licenses/'Noto-OFL.txt')
 shutil.copy2(SDK/'LICENSE.txt',licenses/'RenPy-and-Third-Party.txt')
 manifest=[]
 for p in sorted((out/'game').rglob('*')):
  if p.is_file() and p.suffix not in ('.rpyc','.rpyb') and 'cache' not in p.parts:manifest.append({'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)})
 (licenses/'Resource-Manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 return out

def lint(path):
 log=WORK/'qa/lint.log';log.parent.mkdir(exist_ok=True,parents=True)
 with log.open('w') as f:subprocess.run([str(SDK/'renpy.sh'),str(path),'lint'],env=__import__('os').environ,stdout=f,stderr=subprocess.STDOUT,check=True)
 print(log.read_text())
 if 'could not be loaded' in log.read_text().lower():raise SystemExit('lint resource failure')

def build():
 out=stage();lint(out);DEST.mkdir(exist_ok=True,parents=True)
 with (WORK/'qa/build.log').open('w') as f:subprocess.run([str(SDK/'renpy.sh'),'launcher','--savedir',str(WORK/'qa/launcher-saves'),'distribute',str(out),'--package','win','--package','linux','--destination',str(DEST)],cwd=SDK,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Built',DEST)

def verify():
 """Read every packaged byte, check archive safety and the resource manifest."""
 reports=[]
 for path in sorted(DEST.glob(PACKAGE+'-*')):
  if not(path.name.endswith('.zip') or path.name.endswith('.tar.bz2')):continue
  if path.suffix=='.zip':
   archive=zipfile.ZipFile(path);names=archive.namelist()
   bad=archive.testzip()
   if bad:raise SystemExit('CRC failure: '+bad)
   read=archive.read
  else:
   archive=tarfile.open(path);names=archive.getnames()
   def read(key):
    f=archive.extractfile(key)
    if f is None:raise SystemExit('not a regular file: '+key)
    return f.read()
  for key in names:
   if key.startswith('/') or '..' in key.split('/'):raise SystemExit('unsafe archive path: '+key)
  forbidden=[x for x in names if '/game/author_' in x or '/game/saves/' in x or x.endswith(('traceback.txt','errors.txt','log.txt'))]
  if forbidden:raise SystemExit('development artifacts packaged: '+str(forbidden))
  roots={x.split('/')[0] for x in names};assert len(roots)==1,roots
  root=next(iter(roots))
  manifest=json.loads(read(root+'/LICENSES/Resource-Manifest.json'))
  # Image/audio entries reside in assets.rpa. Read its native index and offsets.
  rpa=read(root+'/game/assets.rpa');header=rpa[:40].decode('ascii').strip().split()
  assert header[0]=='RPA-3.0',header
  offset=int(header[1],16);xor=int(header[2],16)
  import pickle,zlib
  index=pickle.loads(zlib.decompress(rpa[offset:]))
  for row in manifest:
   key=root+'/'+row['path']
   if key in names:data=read(key)
   else:
    rel=row['path'].removeprefix('game/');entry=index.get(rel,index.get(rel.encode()))
    if not entry:raise SystemExit('missing resource in package: '+rel)
    chunks=[]
    for piece in entry:
     start,length,*prefix=piece;start^=xor;length^=xor
     leading = prefix[0] if prefix else b''
     if isinstance(leading,str):leading=leading.encode('latin1')
     chunks.append(leading+rpa[start:start+length])
    data=b''.join(chunks)
   if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise SystemExit('resource differs: '+key)
  needed=['/'+PACKAGE+'.exe','/lib/py3-windows-x86_64/python.exe'] if path.suffix=='.zip' else ['/'+PACKAGE+'.sh','/lib/py3-linux-aarch64/python','/lib/py3-linux-x86_64/python']
  for ending in needed:
   if not any(x.endswith(ending) for x in names):raise SystemExit('missing standalone runtime: '+ending)
  reports.append({'file':path.name,'bytes':path.stat().st_size,'sha256':digest(path),'entries':len(names),'resources_verified':len(manifest),'archive_integrity':'pass','standalone_runtime':'pass'})
  archive.close()
 if len(reports)!=2:raise SystemExit('expected one Windows ZIP and one Linux archive')
 (R/'docs/package-verification.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(reports,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['check','lint','stage','build','verify']);p.add_argument('--draft',action='store_true');p.add_argument('--static',action='store_true');a=p.parse_args()
 if a.command=='check':check(a.draft,a.static)
 elif a.command=='lint':lint(R)
 elif a.command=='stage':print(stage())
 elif a.command=='build':build()
 else:verify()
