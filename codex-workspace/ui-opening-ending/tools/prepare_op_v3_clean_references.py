from pathlib import Path
import json,sys,cv2,numpy as np,shutil
from PIL import Image,ImageDraw
U=Path.cwd();R=U/'research/op-all-japanese-v3';D=R/'dense-frames';O=U/'candidates/opening-video-ko-v3';P=O/'build-source/restoration';cv2.setNumThreads(2)
p=Path('P:/AI/Codex/generated_images/01a162df-720c-77d2-96ed-6429e90b3333/exec-659a92d8-9645-46d7-bdaa-44cfec8844a8.png');shutil.copy2(p,P/'kureha-generated-original.png');Image.open(p).convert('RGB').resize((800,600),Image.Resampling.LANCZOS).save(P/'kureha-donor.png')
Y,X=np.mgrid[:600,:800];clip=(Y>=72)&(Y<526)
def read(n):return np.array(Image.open(D/f'{n:04d}.png'))
def roi(box):
 x1,y1,x2,y2=box;return (X>=x1)&(X<x2)&(Y>=y1)&(Y<y2)
# Masks derive from source frames; all white/color cores and source glow are owned.
configs={'mahoko':(1164,(5,235,450,518),'blue'),'shiina':(1350,(463,155,800,525),'blue'),'masaki':(1500,(15,240,347,519),'red'),'momiji':(1644,(408,260,798,525),'red'),'kureha':(1920,(22,245,340,520),'purple')}
for k,(n,box,col) in configs.items():
 a=read(n);z=a.astype('float32');reg=roi(box);white=z.min(2)>210
 if col=='blue':color=(z[:,:,1]>35)&(z[:,:,2]>110)&(z[:,:,0]<z[:,:,1]*.65)
 elif col=='purple':color=(z[:,:,0]>100)&(z[:,:,2]>125)&(z[:,:,1]<50)
 else:color=(z[:,:,0]>110)&(z[:,:,1]<30)&(z[:,:,2]<45)
 # Accent glyphs have known source slots, unlike the illuminated gradient.
 if k=='masaki':color&=roi((110,315,245,478))
 if k=='momiji':color&=roi((407,335,510,485))
 if k=='kureha':color&=roi((108,315,228,477))
 core=(white|color)&reg;m=cv2.dilate(core.astype('uint8'),np.ones((17,17),np.uint8)).astype(bool)&clip
 if k=='masaki':
  # The source text lies exclusively on this smooth original red background.
  safe=(X<335)&clip&~cv2.dilate(m.astype('uint8'),np.ones((15,15),np.uint8)).astype(bool);x=(X-170)/170;y=(Y-300)/300;terms=np.stack([x**i*y**j for i in range(5) for j in range(5-i)],2);model=np.linalg.lstsq(terms[safe][::3],a[safe][::3],rcond=None)[0];donor=np.clip(terms@model,0,255);Image.fromarray(donor.astype('uint8')).save(P/(k+'-donor.png'))
 else:donor=np.array(Image.open(P/(k+'-donor.png'))).astype('float32')
 # Use low-frequency ring correction to align the donor to untouched source tone.
 outside=clip&~m;weight=outside.astype('float32');den=np.maximum(cv2.GaussianBlur(weight,(0,0),15),1e-6);corrected=donor.copy()
 for c in range(3):corrected[:,:,c]+=cv2.GaussianBlur((a[:,:,c]-donor[:,:,c])*weight,(0,0),15)/den
 dist=cv2.distanceTransform(m.astype('uint8'),cv2.DIST_L2,3);w=np.clip(dist/4,0,1);out=np.clip(a*(1-w[:,:,None])+corrected*w[:,:,None],0,255).astype('uint8');assert np.array_equal(out[~m],a[~m]);Image.fromarray(a).save(P/(k+'-source.png'));Image.fromarray(m.astype('uint8')*255).save(P/(k+'-mask.png'));Image.fromarray(out).save(P/(k+'-clean.png'))
# Text-only source masks, shared across each credit's changing backgrounds.
small={'theme':(1680,(25,88,294,518),175),'cast-main':(2010,(25,94,199,510),170),'cast-support':(2124,(25,215,210,430),170),'yue':(2250,(25,352,205,445),190),'director':(2630,(22,80,199,164),160)}
for k,(n,box,th) in small.items():
 a=read(n);reg=roi(box);core=(a.min(2)>th)&reg
 if k in ('theme','cast-main','cast-support','director'):core|=((a[:,:,0]>90)&(a[:,:,1]<50)&(a[:,:,2]<55)&reg)
 m=cv2.dilate(core.astype('uint8'),np.ones((9,9),np.uint8)).astype(bool)&clip;Image.fromarray(m.astype('uint8')*255).save(P/(k+'-mask.png'))
# Movie lettering remains fixed while both CGs pan beneath it.
arr=np.stack([read(n) for n in [2358,2370,2385,2397,2415,2430,2445]]);core=(np.mean(arr.min(3)>195,axis=0)>.85)&roi((25,427,260,510));m=cv2.dilate(core.astype('uint8'),np.ones((11,11),np.uint8)).astype(bool)&clip;Image.fromarray(m.astype('uint8')*255).save(P/'movie-mask.png')
# Source-only donor candidates and scene partitions for temporal recovery.
scenes=[('theme',1668,1763,1698),('city',1997,2047,2020),('bridge',2048,2063,2058),('sky',2064,2099,2082),('legs',2107,2134,2124),('profile',2135,2163,2142),('maho-event',2187,2218,2205),('yue',2224,2278,2250),('movie-maho',2353,2396,2370),('movie-kure',2410,2451,2430),('director-early',2598,2636,2615),('director-late',2655,2722,2700)]
si=cv2.SIFT_create(nfeatures=2000,contrastThreshold=.012);bf=cv2.BFMatcher()
def norm(a):return cv2.createCLAHE(2,(8,8)).apply(cv2.cvtColor(a,cv2.COLOR_RGB2GRAY))
def feat(a,mask):return si.detectAndCompute(norm(a),(clip&~mask).astype('uint8')*255)
reports=[]
for name,lo,hi,nref in scenes:
 mk='cast-main' if name in ('city','bridge','sky') else 'cast-support' if name in ('legs','profile','maho-event') else 'movie' if name.startswith('movie-') else 'director' if name.startswith('director-') else name
 m=np.array(Image.open(P/(mk+'-mask.png')))>0;ref=read(nref);kp,ds=feat(ref,m);acc=np.zeros(ref.shape,np.float32);ws=np.zeros(m.shape,np.float32);goodrows=[]
 for n in range(lo,hi+1,2):
  a=read(n);ka,da=feat(a,m)
  if da is None or ds is None:continue
  good=[x for x,y in bf.knnMatch(da,ds,k=2) if x.distance<.73*y.distance]
  if len(good)<6:continue
  H,inl=cv2.estimateAffine2D(np.float32([ka[x.queryIdx].pt for x in good]),np.float32([kp[x.trainIdx].pt for x in good]),method=cv2.RANSAC,ransacReprojThreshold=1.8)
  if H is None or inl.sum()<8 or not .3<np.linalg.det(H[:,:2])<3:continue
  w=cv2.warpAffine(a.astype('float32'),H,(800,600),flags=cv2.INTER_LINEAR);wm=cv2.warpAffine(m.astype('uint8'),H,(800,600),flags=cv2.INTER_NEAREST,borderValue=1)>0;valid=clip&~m&~wm
  # Local illumination with a normalized masked residual field, preserving donor detail.
  vv=valid.astype('float32');den=np.maximum(cv2.GaussianBlur(vv,(0,0),12),1e-5);pred=w.copy()
  for c in range(3):pred[:,:,c]+=cv2.GaussianBlur((ref[:,:,c]-w[:,:,c])*vv,(0,0),12)/den
  err=np.median(np.abs(pred[valid]-ref[valid]));dt=cv2.distanceTransform((~wm).astype('uint8'),cv2.DIST_L2,3);wt=np.clip(dt/3,0,1)*m/(1+abs(n-nref)*.03+err);acc+=pred*wt[:,:,None];ws+=wt;goodrows.append({'n':n,'matrix':H.tolist(),'inliers':int(inl.sum()),'error':float(err)})
 holes=m&(ws<.001);out=ref.copy();out[m&~holes]=np.clip(acc[m&~holes]/ws[m&~holes,None],0,255).astype('uint8');Image.fromarray(out).save(P/(name+'-temporal.png'));hh=out.copy();hh[holes]=[255,0,255];Image.fromarray(hh).save(P/(name+'-holes.png'));Image.fromarray(holes.astype('uint8')*255).save(P/(name+'-uncovered.png'));rep={'scene':name,'lo':lo,'hi':hi,'ref':nref,'mask':mk,'owned_pixels':int(m.sum()),'uncovered_pixels':int(holes.sum()),'source_frames':goodrows};reports.append(rep);print(name,'holes',int(holes.sum()),'of',int(m.sum()),'donors',len(goodrows),flush=True)
(P/'temporal-restoration.json').write_text(json.dumps(reports,indent=2)+'\n')