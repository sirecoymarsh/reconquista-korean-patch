from pathlib import Path
import json,numpy as np,cv2
from PIL import Image
U=Path.cwd();R=U/'research/op-logo';O=R/'motion-cache';O.mkdir(exist_ok=True)
source=Path('tools/probe_op_joint_geometry.py').read_text(encoding='utf-8-sig');exec(source.split('for time in [27.0')[0])
O=R/'motion-cache';O.mkdir(exist_ok=True)
times=sorted(t for t in F if 27.8<=t<=30.6);rows=[]
for time in times:
 dest=O/f'{time:05.2f}.npz'
 if dest.exists():continue
 a=F[time].astype('float32');excess=np.maximum(a[:,:,0]-np.maximum(a[:,:,1],a[:,:,2])-30,0);red=(excess>30)&(X>150)&(X<660)&(Y>90)&(Y<480);tv=clip&~cv2.dilate(red.astype('uint8'),np.ones((13,13),np.uint8)).astype(bool)
 sh,dr,co=joint(signal,(a[:,:,1]+a[:,:,2])/2,sv,tv)
 if time>=29.7:ls,ld,lc=joint(sourceLogo,excess,clip,clip,rlimit=4)
 else:ls=np.zeros(NR);ld=np.zeros(NR)
 np.savez_compressed(dest,background_angle=sh,background_radius=dr,logo_angle=ls,logo_radius=ld);rows.append({'time':time,'bg_correlation':float(np.median(co[20:300]))});print('motion',time,flush=True)
(O/'report.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
