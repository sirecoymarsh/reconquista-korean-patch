from pathlib import Path
import sys,json,struct
import numpy as np
from PIL import Image,ImageDraw
U=Path.cwd();sys.path.insert(0,str(U.parent/'tools'));from inspect_majiro import Arc
from raster_codec import raw_image
O=U/'research/op-logo/backgrounds';O.mkdir(parents=True,exist_ok=True);rows=[]
for fn in ['data.arc','data1.arc']:
 arc=Arc(U.parent/'research/disc'/fn);es=[e for e in arc.entries if e['name'].lower().startswith('bg') and e['name'].endswith('.rct')]
 with arc.path.open('rb') as f:
  for e in es:
   f.seek(e['offset']);b=f.read(e['size'])
   if b[4:8]!=b'TC00':continue
   p=O/(e['name']+'.png')
   if not p.exists():
    a,_,_=raw_image(b);im=Image.fromarray(a);im.thumbnail((160,120));im.save(p)
   rows.append({'name':e['name'],'archive':fn,'path':str(p)})
rows.sort(key=lambda r:r['name'])
for pnum in range((len(rows)+79)//80):
 sheet=Image.new('RGB',(1600,8*138),(27,27,30));d=ImageDraw.Draw(sheet)
 for i,r in enumerate(rows[pnum*80:(pnum+1)*80]):
  x=i%10*160;y=i//10*138;sheet.paste(Image.open(r['path']),(x,y));d.text((x+3,y+121),r['name'],fill='white')
 sheet.save(O/f'contact-{pnum+1}.png')
(O/'inventory.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print('Source background thumbnails:',len(rows))
