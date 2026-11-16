"""Select genuinely demanding dialogue pages for native font measurement."""
import json
from catalog import scan,ROOT
_,_,rows=scan()
def width(row):
    return sum(1 if ord(c)>255 else .55 for c in row['text'])
selected=sorted(rows,key=width,reverse=True)[:256]
(ROOT/'docs/layout-rows.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n')
print(len(selected),'demanding dialogue pages selected')
