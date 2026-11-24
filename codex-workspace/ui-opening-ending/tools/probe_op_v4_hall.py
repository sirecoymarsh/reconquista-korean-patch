from pathlib import Path
import sys,json,re,cv2,numpy as np
from PIL import Image
U=Path.cwd();O=U/'candidates/opening-video-ko-v4';sys.path.insert(0,'tools');from op_v3_source_art import SourceArt;from op_v4_english import read,REG,CLIP,X,Y;from op_v3_restoration import register,warp,global_tone
S=SourceArt()
for name in ['bg_060a.rct','bg_030a.rct','bg_040a.rct']:
 a=S.decode(name);Image.fromarray(a).save(O/'build-source/donors'/(name+'.png'))
 for n in ([1230] if name.startswith('bg_060') else [1281]):
  ex=~CLIP|((X<310)&(Y>330))
  if n==1281:ex|=X<420
  h,k=register(a,read(n),exclude=ex);print(name,n,k,h.tolist() if h is not None else None)
a=read(1281);rows=[]
for name in [n for n in S.idx if re.match(r'b_sina_.*_01.rct$',n)]:
 ar=S.decode(name);h,k=register(ar,a,exclude=(X>440)|(Y>340)|~CLIP)
 if h is None or k<15:continue
 maskname=name[:-4]+'_.rc8'
 if maskname not in S.idx:continue
 al=S.decode(maskname);al=warp(255-al,h)/255.;p=warp(ar,h);valid=(al>.99)&CLIP&~REG['music']&(Y>210)
 if valid.sum()<500:continue
 c=global_tone(p,a,valid);pp=p.astype(float)@c[:3]+c[3];err=float(np.mean(np.abs(pp[valid]-a[valid])));rows.append(dict(name=name,error=err,k=k,H=h.tolist(),pixels=int(valid.sum())))
rows.sort(key=lambda x:x['error']);print('body',rows[:5]);(O/'evidence/sound-hall-body-match.json').write_text(json.dumps(rows,indent=2))
for r in rows[:2]:
 name=r['name'];Image.fromarray(S.decode(name)).save(O/'build-source/donors'/(name+'.png'));Image.fromarray(S.decode(name[:-4]+'_.rc8')).save(O/'build-source/donors'/(name+'.alpha.png'))
