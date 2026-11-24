from pathlib import Path
import numpy as np,cv2,json
from PIL import Image,ImageDraw
U=Path.cwd();R=U/'research/op-all-japanese-v3';D=R/'dense-frames';O=R/'temporal-probe';O.mkdir(exist_ok=True);cv2.setNumThreads(2)
Y,X=np.mgrid[:600,:800];clip=(Y>=72)&(Y<526)
def read(n):return np.array(Image.open(D/f'{n:04d}.png'))
def mask(a,roi):
 z=a.astype('float32');core=((z.min(2)>214)|((z[:,:,2]>85)&(z[:,:,1]>32)&(z[:,:,0]<z[:,:,1]*.65)))&roi
 return cv2.dilate(core.astype('uint8'),np.ones((11,11),np.uint8)).astype(bool)&clip
ref=read(1164);roi=(X<490)&(Y>220)&clip;m=mask(ref,roi);valid=(X>470)&(X<790)&(Y>85)&(Y<500)
sift=cv2.SIFT_create(nfeatures=2000,contrastThreshold=.012);bf=cv2.BFMatcher()
def gray(a):
 g=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY);return cv2.createCLAHE(2,(8,8)).apply(g)
kp,ds=sift.detectAndCompute(gray(ref),valid.astype('uint8')*255)
fill=ref.astype('float32').copy();score=np.ones((600,800),np.float32)*1e5;score[~m]=0;rows=[]
for n in range(1125,1181):
 a=read(n);ka,da=sift.detectAndCompute(gray(a),valid.astype('uint8')*255)
 if da is None:continue
 good=[x for x,y in bf.knnMatch(da,ds,k=2) if x.distance<.8*y.distance]
 if len(good)<4:continue
 H,inl=cv2.estimateAffinePartial2D(np.float32([ka[x.queryIdx].pt for x in good]),np.float32([kp[x.trainIdx].pt for x in good]),method=cv2.RANSAC,ransacReprojThreshold=2)
 if H is None or inl.sum()<4:continue
 wa=cv2.warpAffine(a.astype('float32'),H,(800,600));wm=cv2.warpAffine(mask(a,clip).astype('uint8'),H,(800,600),flags=cv2.INTER_NEAREST,borderValue=1).astype(bool)
 vm=valid&~wm;coef=[];pred=np.zeros_like(wa)
 for c in range(3):
  av=wa[:,:,c][vm];rv=ref[:,:,c][vm];cc=np.polyfit(av,rv,1);coef.append(cc.tolist());pred[:,:,c]=wa[:,:,c]*cc[0]+cc[1]
 err=np.mean(np.abs(pred[vm]-ref[vm]));sc=err+np.mean(np.abs(np.array(coef)[:,0]-1))*5;take=m&~wm&(sc<score);fill[take]=pred[take];score[take]=sc;rows.append({'n':n,'inliers':int(inl.sum()),'matrix':H.tolist(),'coef':coef,'error':float(err),'pixels':int(take.sum())})
Image.fromarray(m.astype('uint8')*255).save(O/'mahoko-mask.png');Image.fromarray(np.clip(fill,0,255).astype('uint8')).save(O/'mahoko-fill.png');holes=m&(score>1e4);a=np.clip(fill,0,255).astype('uint8');a[holes]=[255,0,255];Image.fromarray(a).save(O/'mahoko-holes.png');(O/'mahoko-registration.json').write_text(json.dumps(rows,indent=2));print(json.dumps({'mask':int(m.sum()),'holes':int(holes.sum()),'frames_used':len(rows),'rows':rows[:5]}))