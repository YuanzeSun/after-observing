from pathlib import Path
import ast,re,json,hashlib,collections,argparse
ROOT=Path(__file__).resolve().parents[1];GAME=ROOT/'game'
SAY=re.compile(r'^\s*(?:(?P<who>[A-Za-z_][\w.]*|"(?:[^"\\]|\\.)*")\s+)?(?P<text>"(?:[^"\\]|\\.)*")\s*(?:#.*)?$')
def scan():
 chapters=json.loads((GAME/'data/chapters.json').read_text());scenes={};counts=collections.Counter();labels={};menus=collections.Counter();missing=[];rows=[]
 for p in sorted((GAME/'story').glob('*.rpy')):
  label=None
  for n,line in enumerate(p.read_text().splitlines(),1):
   m=re.match(r'^label (\w+):',line)
   if m:
    label=m[1]
    assert label not in labels,('duplicate chapter label',label)
    labels[label]=str(p.relative_to(GAME));continue
   if line.strip().startswith('$ enter_scene('):
    call=ast.parse(line.strip()[2:]).body[0].value
    args=[ast.literal_eval(x) for x in call.args];kwargs={x.arg:ast.literal_eval(x.value) for x in call.keywords}
    key,title,bg,date,period,actors,*music=args
    assert key not in scenes,('duplicate scene',key)
    scenes[key]={'title':title,'background':bg,'date':date,'period':period,'actors':actors,'music':music[0] if music else None,'chapter':label,'source':str(p.relative_to(GAME)),'line':n,**kwargs}
   if line.strip()=='menu:':menus[label]+=1
   m=SAY.match(line)
   if m:
    text=ast.literal_eval(m['text']);speaker=m['who'] or ''
    # Option captions are followed by a colon and never match SAY.
    counts[label]+=len(text);rows.append({'chapter':label,'source':str(p.relative_to(GAME)),'line':n,'speaker':speaker,'text':text})
 for key in chapters:
  if key not in labels:missing.append(key)
 unexpected=sorted(set(labels)-set(chapters))
 counts=collections.Counter({key:n for key,n in counts.items() if key in chapters})
 rows=[row for row in rows if row['chapter'] in chapters]
 report={'chapters':dict(counts),'total':sum(counts.values()),'chapter_count':len(counts),'unexpected_labels':unexpected,'missing_chapters':missing,'menus':dict(menus),'scenes':len(scenes),'measurement':'仅正式章节的源脚本Say预检计数，含互斥分支；发布还必须核对真实原生运行覆盖与当前稿摘要，不计菜单、代码、注释或未注册标签。'}
 return scenes,report,rows
if __name__=='__main__':
 scenes,report,rows=scan();(GAME/'data/scenes.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2)+'\n');(ROOT/'docs/body-statistics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
