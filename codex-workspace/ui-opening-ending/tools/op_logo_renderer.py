"""Source-derived OP logo localization prototype. Never touches original movie.
Static source background / source-only temporal donors; all restoration is restricted
to a source-derived original-logo mask. Gradient intervals retain a separately
reported source-fitted reconstruction gate rather than claiming original pixels.
"""
from pathlib import Path
import json,cv2,numpy as np
from PIL import Image
def gaussian_filter(a,sigma):return cv2.GaussianBlur(a,(0,0),sigma)
def distance_transform_edt(mask,return_distances=False,return_indices=True):
 _,labels=cv2.distanceTransformWithLabels(mask.astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
 coords=np.argwhere(~mask);nearest=coords[labels-1];return np.stack([nearest[:,:,0],nearest[:,:,1]])
U=Path(__file__).resolve().parents[1];R=U/'research/op-logo';O=R/'logo-probe';O.mkdir(exist_ok=True)
cv2.setNumThreads(2)
rows=json.loads((R/'frames.json').read_text());frames={r['time']:np.asarray(Image.open(r['path']).convert('RGB')).copy() for r in rows}
Y,X=np.mgrid[0:600,0:800].astype('float32');xx=(X-400)/400;yy=(Y-300)/300;clip=(Y>=72)&(Y<526)
poly=np.stack([xx**i*yy**j for d in range(6) for i in range(d+1) for j in [d-i]],2).astype('float32')
ref=frames[95.0];v=ref.astype('float32');seed=(v[:,:,0]>72)&(v[:,:,0]-v[:,:,1]>52)&(v[:,:,0]-v[:,:,2]>42);seed &= (X>180)&(X<625)&(Y>110)&(Y<455)
static_mask=cv2.dilate(seed.astype('uint8'),np.ones((13,13),np.uint8)).astype(bool)
roman=(X>=244)&(X<449)&(Y>=374)&(Y<425)&(v[:,:,1]>38)&(v[:,:,2]>32)&(v[:,:,0]-v[:,:,1]<75);roman=cv2.dilate(roman.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)
master=Image.open(U/'candidates/brand-logo-ko-v1/master/reconquista-ko.png').convert('RGBA');master=master.crop(master.getchannel('A').getbbox());master=master.resize((400,round(master.height*400/master.width)),Image.Resampling.LANCZOS);K=np.zeros((600,800),np.float32);K[124:124+master.height,201:601]=np.asarray(master)[:,:,3]/255
city=np.asarray(Image.open(R/'bg_020c.png').convert('RGB'));sift=cv2.SIFT_create(nfeatures=4000);kc,dc=sift.detectAndCompute(cv2.cvtColor(city,cv2.COLOR_RGB2GRAY),None);H0=np.array(json.loads((R/'city-registration.json').read_text())['H']);base27=cv2.warpPerspective(city,H0,(800,600)).astype('float32');fit=(clip&~static_mask&~roman)[::4,::4];A=np.concatenate([base27,np.ones((600,800,1),np.float32)],2);B=frames[27.0].astype('float32');C=np.linalg.lstsq(A[::4,::4][fit],B[::4,::4][fit],rcond=None)[0]

def mask_for(a,t):
 v=a.astype('float32');dyn=(v[:,:,0]>85)&(v[:,:,0]-v[:,:,1]>55)&(v[:,:,0]-v[:,:,2]>45)&(X>160)&(X<650)&(Y>95)&(Y<470)
 m=static_mask|cv2.dilate(dyn.astype('uint8'),np.ones((17,17),np.uint8)).astype(bool)
 m &= clip; m &= ~roman
 return m

def gradient(a,m):
 # Overdetermined low-order color surface; keep holdout error for acceptance.
 valid=clip&~m&~roman;valid &= ~((a[:,:,0].astype('int16')-a[:,:,1])>100)
 ys,xs=np.nonzero(valid[::5,::5]);sy=ys*5;sx=xs*5;aa=poly[sy,sx];bb=a[sy,sx].astype('float32');w=np.ones(len(aa),np.float32)
 for _ in range(3):
  coef=np.linalg.lstsq(aa*w[:,None],bb*w[:,None],rcond=1e-5)[0];err=np.max(np.abs(aa@coef-bb),1);w=np.minimum(1,4/np.maximum(err,1))
 pred=np.clip(poly@coef,0,255);val=valid & ((X.astype(int)+2*Y.astype(int))%13==0);e=np.abs(pred[val]-a[val]);return pred,{'model':'same-frame total-degree5 color surface','holdout_mean_abs_rgb_error':float(e.mean()),'holdout_p95_abs_rgb_error':float(np.percentile(e,95))}

def gray(a):return cv2.cvtColor(np.clip(a,0,255).astype('uint8'),cv2.COLOR_RGB2GRAY)

def source_flow(source,a,m):
 # Dense backward registration, then extrapolate only the geometric displacement
 # through old text occlusions; RGB donors themselves always come from source.
 gs=gray(source);ga=gray(a);ms=cv2.resize(m.astype('uint8'),(400,300),interpolation=cv2.INTER_NEAREST).astype(bool);ss=cv2.resize(gs,(400,300));tt=cv2.resize(ga,(400,300));tt[ms]=ss[ms]
 flow=cv2.calcOpticalFlowFarneback(tt,ss,None,.5,4,25,5,7,1.5,0)
 validmask=cv2.dilate(ms.astype('uint8'),np.ones((5,5),np.uint8))>0
 indices=distance_transform_edt(validmask,return_distances=False,return_indices=True)
 for c in range(2):
  z=flow[:,:,c];fill=z[tuple(indices)];fill=gaussian_filter(fill,2);z[validmask]=fill[validmask]
 flow=cv2.resize(flow,(800,600))*2
 warped=cv2.remap(source.astype('float32'),X+flow[:,:,0],Y+flow[:,:,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
 return warped,flow

def temporal(a,m,t):
 donor=frames[19.6] if t<22 else frames[90.2]
 pred,flow=source_flow(donor,a,m);valid=clip&~m&~roman;aa=pred[::5,::5][valid[::5,::5]];bb=a[::5,::5][valid[::5,::5]].astype('float32');mat=np.concatenate([aa,np.ones((len(aa),1))],1);coef=np.linalg.lstsq(mat,bb,rcond=None)[0];pred=np.clip(np.concatenate([pred,np.ones((600,800,1))],2)@coef,0,255)
 e=np.abs(pred[valid]-a[valid]);return pred,{'model':'registered coherent source-only logo-free video frame','donor_time':19.6 if t<22 else 90.2,'unoccluded_mean_abs_rgb_error':float(e.mean())}

def city_bg(a,m,t):
 mask=(clip&~m&~roman).astype('uint8')*255;kt,dt=sift.detectAndCompute(gray(a),mask);H=H0;count=0
 if dt is not None:
  ms=cv2.BFMatcher().knnMatch(dc,dt,k=2);good=[p for p,q in ms if p.distance<.72*q.distance]
  if len(good)>12:
   hh,ins=cv2.findHomography(np.float32([kc[p.queryIdx].pt for p in good]),np.float32([kt[p.trainIdx].pt for p in good]),cv2.RANSAC,2)
   if hh is not None and ins.sum()>10:H=hh;count=int(ins.sum())
 pred=cv2.warpPerspective(city,H,(800,600)).astype('float32');pred=np.clip(np.concatenate([pred,np.ones((600,800,1),np.float32)],2)@C,0,255)
 if t>=27.8:pred,flow=source_flow(pred,a,m)
 # Blue/green carry the reveal alpha; the red vignette has negligible G/B.
 num=(a[:,:,1:].astype('float32')*pred[:,:,1:]).sum(2);den=(pred[:,:,1:]**2).sum(2);valid=(clip&~m&~roman&(den>150)).astype('float32')
 sigma=12 if t>=26 else 22;num=gaussian_filter(num*valid,sigma);den=gaussian_filter(den*valid,sigma);alpha=np.clip(num/np.maximum(den,1),0,1.15)
 clean=pred*alpha[:,:,None]
 if t<26:
  redvalid=clip&~m&~roman&(alpha<.22);shade=np.zeros((600,800,3),np.float32)
  if redvalid.sum()>2000:
   aa=poly[::6,::6][redvalid[::6,::6]];bb=a[::6,::6][redvalid[::6,::6]].astype('float32');coef=np.linalg.lstsq(aa,bb,rcond=1e-4)[0];shade=np.clip(poly@coef,0,60)
  clean+=shade*(1-np.clip(alpha,0,1))[:,:,None]
 valid2=clip&~m&~roman;e=np.abs(clean[valid2]-a[valid2]);return np.clip(clean,0,255),{'model':'original bg_020c.rct registered and photometrically matched to video','feature_inliers':count,'unoccluded_mean_abs_rgb_error':float(e.mean()),'homography':H.tolist()}

def compose(a,t):
 m=mask_for(a,t)
 if 19.6<=t<21.45 or 90.25<=t<90.8:pred,report=temporal(a,m,t)
 elif 24.5<=t<=30.6:pred,report=city_bg(a,m,t)
 else:pred,report=gradient(a,m)
 # Feather only the source-owned restoration edge (not a rectangle and not a blur plate).
 weight=cv2.GaussianBlur(m.astype('float32'),(0,0),.7);weight[~m]=0;weight[m & (cv2.erode(m.astype('uint8'),np.ones((3,3),np.uint8))>0)]=1
 clean=a.astype('float32')*(1-weight[:,:,None])+pred*weight[:,:,None]
 clean=np.clip(np.rint(clean),0,255).astype('uint8');assert np.array_equal(clean[~m],a[~m])
 # Match the original logo's crimson-to-pink illumination and vertical falloff.
 rgb=a.astype('float32');core=(rgb[:,:,0]-rgb[:,:,1]>65)&(rgb[:,:,0]-rgb[:,:,2]>50)&(rgb[:,:,0]>100)&seed
 colors=[];ys=[]
 for y in range(120,440,12):
  v=rgb[y:y+12][core[y:y+12]]
  if len(v)>15:colors.append(np.percentile(v,60,axis=0));ys.append(y+6)
 color=np.ones((600,3),np.float32)*[206,21,60]
 if len(colors)>2:
  for c in range(3):color[:,c]=cv2.GaussianBlur(np.interp(np.arange(600),ys,np.array(colors)[:,c]).astype('float32').reshape(-1,1),(1,0),18).ravel()
 alpha=K.copy();opacity=1.0
 if 19.6<=t<19.95:opacity=float(np.clip((t-19.68)/.14,0,1))
 if 90.25<=t<90.8:opacity=float(np.clip((t-90.28)/.42,0,1))
 if t>98.55:opacity=float(np.clip((99.95-t)/1.4,0,1))
 alpha*=opacity
 glow=gaussian_filter(alpha,2.2)*(.25 if t<22 or 90.25<t<93 else .05)
 out=clean.astype('float32');out=np.clip(out+glow[:,:,None]*color[:,None,:],0,255);out=out*(1-alpha[:,:,None])+color[:,None,:]*alpha[:,:,None];out=np.clip(np.rint(out),0,255).astype('uint8')
 target=(alpha>0)|(glow>0);owned=m|target;assert np.array_equal(out[~owned],a[~owned])
 report.update({'time':t,'source_erase_pixels':int(m.sum()),'protected_pixel_diff_count':0,'preencoding_source_geometry':[800,600],'status':'prototype_visual_review_pending; not a lossless original clean-plate claim'})
 return clean,out,m,report

if __name__=='__main__':
 reports=[]
 for t in [20.0,21.0,22.6,24.0,25.0,26.0,27.0,28.4,29.4,30.0,90.4,92.0,95.0,99.0]:
  a=frames[t];cl,out,m,rep=compose(a,t);Image.fromarray(cl).save(O/f'clean-{t:04.1f}.png');Image.fromarray(out).save(O/f'final-{t:04.1f}.png');Image.fromarray((m*255).astype('uint8')).save(O/f'mask-{t:04.1f}.png');reports.append(rep)
 (O/'report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps([{k:r[k] for k in ['time','model','protected_pixel_diff_count']} for r in reports],ensure_ascii=False))
