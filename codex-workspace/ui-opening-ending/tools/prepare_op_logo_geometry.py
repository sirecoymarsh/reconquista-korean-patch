from pathlib import Path
import json,numpy as np,cv2
from PIL import Image
U=Path.cwd();R=U/'research/op-logo';O=R/'polar-probe';O.mkdir(exist_ok=True)
rs=json.loads((R/'frames.json').read_text());rs+=json.loads((R/'late-transition/frames.json').read_text());frames={r['time']:np.array(Image.open(r['path'])) for r in rs}
a=np.array(Image.open(U/'source/decoded/title1_off.rct.png'));b=np.array(Image.open(U/'source/decoded/title1_null2.rct.png'));d=np.any(a!=b,2);d[400:]=False;d[:,480:]=False
red=(a[:,:,0].astype('int16')-a[:,:,1]>55)&(a[:,:,0].astype('int16')-a[:,:,2]>35)&d
n,l,st,c=cv2.connectedComponentsWithStats(d.astype('uint8'),8);ids=[int(k) for k in np.unique(l[red]) if k];print('components',[(k,st[k].tolist()) for k in ids]);native=np.isin(l,ids).astype('float32');srcred=red.astype('float32')
H=np.array([[1.03,0,150],[0,1.03,41.5]],np.float32);rough=cv2.warpAffine(srcred,H,(800,600));v=frames[95.0].astype('float32');tr=(v[:,:,0]-v[:,:,1]>45)&(v[:,:,0]-v[:,:,2]>35)&(v[:,:,0]>65);tr[:90]=0
cc,W=cv2.findTransformECC(tr.astype('float32'),rough,np.eye(2,3,dtype='float32'),cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,100,1e-6),None,3)
warp=cv2.warpAffine(cv2.warpAffine(native,H,(800,600)),W,(800,600),flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP);mask=cv2.dilate((warp>.001).astype('uint8'),np.ones((7,7),np.uint8));Image.fromarray(mask*255).save(O/'old-logo-mask.png');np.save(O/'old-logo-mask.npy',mask.astype(bool));(O/'registration.json').write_text(json.dumps({'native_components':ids,'initial_affine':H.tolist(),'ecc':float(cc),'adjustment':W.tolist()},indent=2));print('ECC',cc,W.tolist(),'mask',mask.sum())
