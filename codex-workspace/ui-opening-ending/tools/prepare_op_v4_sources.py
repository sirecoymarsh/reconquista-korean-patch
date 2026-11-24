from pathlib import Path
import json,sys,subprocess,re,cv2,numpy as np
from PIL import Image,ImageDraw
U=Path.cwd();O=U/'candidates/opening-video-ko-v4';sys.path.insert(0,str(U/'tools'));from op_v3_source_art import SourceArt
from op_v3_restoration import register
S=SourceArt();print('special', [n for n in S.idx if re.match(r'(last|op|movie|opening|img)',n) and n.endswith('.rct')],flush=True)
F=O/'build-source/source-frames';ranges=[(0,490),(900,1105),(1170,1290)];indices={n for lo,hi in ranges for n in range(lo,hi+1)}
ff='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';source=U.parent/'research/disc/movie/Recon_OP800_H.mpg'
p=subprocess.Popen([ff,'-v','error','-threads','2','-i',str(source),'-frames:v','1291','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
for n in range(1291):
 b=p.stdout.read(800*600*3);assert len(b)==800*600*3
 if n in indices and not (F/f'{n:04d}.png').exists():Image.frombytes('RGB',(800,600),b).save(F/f'{n:04d}.png')
assert p.wait()==0;print('source frames',len(indices),flush=True)
# Match full original artwork to only previously unlocalized English-credit shots.
names=[x['name'] for x in json.loads((U/'research/op-all-japanese-v3/art-index.json').read_text())]+[n for n in S.idx if re.match('last.*rct$',n)]
T={n:np.array(Image.open(F/f'{n:04d}.png')) for n in [120,300,420,990,1020,1230]};rows={n:[] for n in T};Y,X=np.mgrid[:600,:800]
for i,name in enumerate(dict.fromkeys(names)):
 a=S.decode(name)
 for n,t in T.items():
  ex=(Y<75)|(Y>524)
  if n==120:ex|=(Y>260)&(Y<340)&(X>180)&(X<620)
  elif n in (300,420):ex|=(Y>350)&(X>545)
  else:ex|=(Y>325)&(X<315)
  h,k=register(a,t,exclude=ex)
  if h is not None and k>=8:rows[n].append(dict(name=name,inliers=k,matrix=h.tolist()))
 S.cache.clear()
for n,r in rows.items():
 r.sort(key=lambda x:x['inliers'],reverse=True);rows[n]=r[:4];print(n,r[:2],flush=True)
 for x in r[:2]:Image.fromarray(S.decode(x['name'])).save(O/'build-source/donors'/(x['name']+'.png'))
(O/'evidence/english-source-matching.json').write_text(json.dumps(rows,indent=2)+'\n')
