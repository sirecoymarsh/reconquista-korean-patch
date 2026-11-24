from pathlib import Path
import json,sys,struct,hashlib,urllib.request,re,concurrent.futures
import numpy as np
from PIL import Image,ImageDraw
U=Path.cwd();R=U/'research/op-all-japanese-v3';sys.path.insert(0,str(U.parent/'tools'));sys.path.insert(0,str(U/'tools'))
from inspect_majiro import Arc
from raster_codec import raw_image
A={n:Arc(U.parent/'research/disc'/n) for n in ['data.arc','data1.arc','data2.arc','slowdata.arc']};idx={n:{e['name']:e for e in a.entries} for n,a in A.items()};cache={}
def decode(n):
 if n in cache:return cache[n]
 fn=next(f for f in A if n in idx[f]);e=idx[fn][n]
 with A[fn].path.open('rb') as h:h.seek(e['offset']);b=h.read(e['size'])
 ar,_,_=raw_image(b)
 if b[4:8]==b'TC01':
  z=struct.unpack_from('<H',b,20)[0];base=b[22:22+z].rstrip(b'\0').decode('cp932');base+=('' if base.endswith('.rct') else '.rct');mask=np.all(ar==[255,0,0],axis=2);ar[mask]=decode(base)[mask]
 cache[n]=ar;return ar
D=R/'extra-source-art';D.mkdir(exist_ok=True)
for n in ['last1.rct','last2.rct','last3.rct','last4.rct','last5.rct','bg_010_04.rct','bg_340a.rct','bg_260c.rct','bg_270c.rct','ev301a1_01.rct','ev106_01.rct']:
 try:Image.fromarray(decode(n)).save(D/(n+'.png'))
 except Exception as e:print(n,str(e))
for fn in A:
 names=[n for n in idx[fn] if n.endswith('.rct') and not re.match(r'(b_|m_|s_|ev|bg_|[0-9])',n)]
 print(fn,len(idx[fn]),names[:400])
base='https://web.archive.org/web/20160716153107id_/http://cotton-soft.com/gameproducts/02_recon/'
def fetch(n):
 p=R/'official-reference'/n
 if p.exists():b=p.read_bytes();url='cached'
 else:
  try:
   with urllib.request.urlopen(base+n,timeout=20) as r:b=r.read();url=r.url
   p.write_bytes(b)
  except Exception as e:return {'path':n,'error':str(e)}
 s=b.decode('cp932','replace');links=re.findall(r'(?:src|href)=[\"\']([^\"\']+)',s,re.I);return {'path':n,'url':url,'links':list(dict.fromkeys(links))}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:print(json.dumps(list(ex.map(fetch,['download.htm','dl_mo.htm'])),ensure_ascii=False))