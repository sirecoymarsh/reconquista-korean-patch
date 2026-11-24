"""OP frame compositor. Source-derived backgrounds, observed motion, v2 Korean logo.
Interior background is a reconstruction, not a claim of original hidden RGB identity.
"""
from pathlib import Path
import numpy as np,cv2,json
from PIL import Image
import op_logo_renderer as legacy
U=Path(__file__).resolve().parents[1];R=U/'research/op-logo';O=U/'candidates/opening-video-ko-v2';cv2.setNumThreads(2)
Y,X=np.mgrid[:600,:800].astype('float32');xx=(X-400)/400;yy=(Y-300)/300;clip=(Y>=72)&(Y<526);rad=np.hypot(X-400,Y-300);theta=np.arctan2(Y-300,X-400);NR=510;N=1024
old=np.load(R/'polar-probe/old-logo-mask.npy');static=cv2.dilate(old.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)
rows=json.loads((R/'frames.json').read_text());rows+=json.loads((R/'late-transition/frames.json').read_text());F={r['time']:np.array(Image.open(r['path']).convert('RGB')) for r in rows}
cache={float(p.stem):dict(np.load(p)) for p in (R/'motion-cache').glob('*.npz')};ts=np.array(sorted(cache))
master=Image.open(U/'candidates/brand-logo-ko-v2/master/reconquista-ko.png').convert('RGBA');bbox=Image.open(U/'candidates/brand-logo-ko-v1/master/reconquista-ko.png').getchannel('A').getbbox();master=master.crop(bbox);master=master.resize((400,round(master.height*400/master.width)),Image.Resampling.LANCZOS);K=np.zeros((600,800),np.float32);K[124:124+master.height,201:601]=np.array(master)[:,:,3]/255
n,labels,st,cen=cv2.connectedComponentsWithStats((K>0).astype('uint8'),8);keep=np.zeros(n,bool);keep[1:]=st[1:,cv2.CC_STAT_AREA]>=5;K[~keep[labels]]=0
city27=np.array(Image.open(R/'polar-probe/clean-city27-full.png')).astype('float32')
def active(t):return 19.66<=t<=30.66 or 90.23<=t<=100.0

def profiles(t):
 i=int(np.searchsorted(ts,t));lo=ts[max(0,i-1)];hi=ts[min(len(ts)-1,i)];q=0 if hi==lo else (t-lo)/(hi-lo);return {k:cache[lo][k]*(1-q)+cache[hi][k]*q for k in cache[lo]}

def maps(sh,dr):
 ang=theta+np.interp(rad,np.arange(NR),sh)*2*np.pi/N;rr=rad+np.interp(rad,np.arange(NR),dr);return (400+rr*np.cos(ang)).astype('float32'),(300+rr*np.sin(ang)).astype('float32')

def tone(bg,a,mask,sigma=12):
 valid=(clip&~mask).astype('float32');valid[374:426,240:455]=0;den=np.maximum(cv2.GaussianBlur(valid,(0,0),sigma),.00001);out=np.empty_like(bg)
 for c in range(3):
  b=bg[:,:,c].astype('float32');t=a[:,:,c].astype('float32');mb=cv2.GaussianBlur(b*valid,(0,0),sigma)/den;mt=cv2.GaussianBlur(t*valid,(0,0),sigma)/den;vb=cv2.GaussianBlur(b*b*valid,(0,0),sigma)/den-mb*mb;ct=cv2.GaussianBlur(t*b*valid,(0,0),sigma)/den-mt*mb;gain=np.clip(ct/np.maximum(vb,5),.15,2);out[:,:,c]=b*gain+mt-mb*gain
 return np.clip(out,0,255)

def dense_bg(a,m,motion):
 bx,by=maps(motion['background_angle'],motion['background_radius']);init=np.stack([bx-X,by-Y],2).astype('float32')
 def graynorm(a):
  g=cv2.cvtColor(np.clip(a,0,255).astype('uint8'),cv2.COLOR_RGB2GRAY).astype('float32');mu=cv2.GaussianBlur(g,(0,0),9);return np.clip((g-mu)*3+128,0,255).astype('uint8')
 gs=graynorm(city27);gt=graynorm(a);fm=m.copy();fm[374:426,244:449]=True
 predicted=cv2.remap(gs,bx,by,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101);gt[fm]=predicted[fm]
 dis=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM);dis.setVariationalRefinementIterations(6);flow=dis.calc(gt,gs,init)
 for c in range(2):flow[:,:,c]=cv2.inpaint(flow[:,:,c].copy(),fm.astype('uint8')*255,12,cv2.INPAINT_NS)
 return cv2.remap(city27,X+flow[:,:,0],Y+flow[:,:,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)

def colors(a):
 rgb=a.astype('float32');core=(rgb[:,:,0]-rgb[:,:,1]>60)&(rgb[:,:,0]-rgb[:,:,2]>40)&(rgb[:,:,0]>90)&(rgb[:,:,2]-rgb[:,:,1]>8)&old;vals=[];ys=[]
 for y in range(120,440,12):
  vv=rgb[y:y+12][core[y:y+12]]
  if len(vv)>10:vals.append(np.percentile(vv,65,axis=0));ys.append(y+6)
 out=np.ones((600,3),np.float32)*[206,21,60]
 if len(vals)>2:
  for c in range(3):out[:,c]=cv2.GaussianBlur(np.interp(np.arange(600),ys,np.array(vals)[:,c]).astype('float32').reshape(-1,1),(1,0),16).ravel()
 return out[:,None,:]*np.ones((1,800,1),np.float32)

def compose(a,t):
 if not active(t):return a,{'active':False}
 rgb=a.astype('float32');ka=K.copy();m=static.copy();model='';motion=None
 if 29.7<=t<=30.66:
  motion=profiles(t);lx,ly=maps(motion['logo_angle'],motion['logo_radius']);m=cv2.remap(static.astype('float32'),lx,ly,cv2.INTER_LINEAR)>.001;ka=cv2.remap(K,lx,ly,cv2.INTER_LINEAR)
 dyn=(rgb[:,:,0]>70)&(rgb[:,:,0]-rgb[:,:,1]>25)&(rgb[:,:,0]-rgb[:,:,2]>15)&(rgb[:,:,2]-rgb[:,:,1]>5)&(X>150)&(X<660)&(Y>90)&(Y<480)
 dyn &= cv2.dilate(m.astype('uint8'),np.ones((61,61),np.uint8)).astype(bool)
 m|=cv2.dilate(dyn.astype('uint8'),np.ones((9,9),np.uint8)).astype(bool)
 if t<21.45 or 90.75<=t<=92.6:
  points=cv2.findNonZero(m.astype('uint8'));hull=cv2.convexHull(points);filled=np.zeros((600,800),np.uint8);cv2.fillConvexPoly(filled,hull,1);m=cv2.dilate(filled,np.ones((65,65),np.uint8)).astype(bool)
 m&=clip
 roman=np.zeros((600,800),np.float32);roman[376:422,251:433]=1
 if motion is not None and t>=29.7:roman=cv2.remap(roman,lx,ly,cv2.INTER_LINEAR)
 if t>=21.3:m &= ~(roman>.001)
 starring=np.zeros((600,800),bool)
 if 30.25<=t<=30.66:
  starring=(np.abs(rgb[:,:,0]-rgb[:,:,1])<20)&(np.abs(rgb[:,:,2]-rgb[:,:,1])<20)&(np.min(rgb,2)>55)&(X>=320)&(X<485)&(Y>=240)&(Y<355);starring=cv2.dilate(starring.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool);m &=~starring
 if t<21.45 or 90.23<=t<90.85:
  donor=F[19.6] if t<22 else F[90.2];pred,trep=legacy.temporal(a,m,t);model='source-only temporal donor with observed registration and local illumination'
 elif 24.45<=t<27.8:
  pred,rep=legacy.city_bg(a,m,t);pred=tone(pred.astype('float32'),a,m,12);model='original bg_020c source with feature registration and reveal illumination'
 elif 27.8<=t<=30.66:
  if motion is None:motion=profiles(t)
  pred=dense_bg(a,m,motion);pred=tone(pred,a,m,12);model='original city donor with observed radial motion and local illumination'
 else:pred,rep=legacy.gradient(a,m);model=rep['model']
 # Feather only at source-owned mask boundary. Protected pixels remain identical.
 dist=cv2.distanceTransform(m.astype('uint8'),cv2.DIST_L2,3);w=np.clip(dist/(14 if t<21.45 else 2.5),0,1);clean=rgb*(1-w[:,:,None])+pred*w[:,:,None]
 opacity=1.;color_source=a
 if t<19.9:opacity=float(np.clip((t-19.66)/.17,0,1));color_source=F[20.4]
 if 29.85<=t<=30.66:opacity=float(np.clip((30.66-t)/.81,0,1));color_source=F[29.6]
 if 90.23<=t<90.85:opacity=float(np.clip((t-90.23)/.62,0,1));color_source=F[91.0]
 if t>=98.55:opacity=float(np.clip((100-t)/1.45,0,1));color_source=F[98.4]
 color=colors(color_source)
 if motion is not None and t>=29.7:color=cv2.remap(color,lx,ly,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
 ka*=opacity;glow=cv2.GaussianBlur(ka,(0,0),1.7)*(.10 if t<22 or 90.23<=t<93 else .025);out=np.clip(clean+glow[:,:,None]*color,0,255);out=out*(1-ka[:,:,None])+color*ka[:,:,None];out=np.clip(np.rint(out),0,255).astype('uint8');out[starring]=a[starring];owned=m|(ka>0)|(glow>0);assert np.array_equal(out[~owned],a[~owned])
 return out,{'active':True,'model':model,'mask_pixels':int(m.sum()),'protected_pixel_diff_count':0,'opacity':opacity,'background_provenance':'source-derived reconstruction; hidden original RGB not provable'}

if __name__=='__main__':
 P=O/'preview/logo-frames';P.mkdir(parents=True,exist_ok=True);rr=[]
 for t in [19.8,20.,21.,22.6,24.,25.,26.,27.,28.4,29.4,29.8,30.,30.3,30.5,90.4,91.,95.,99.]:
  a=F[t];out,r=compose(a,t);Image.fromarray(out).save(P/f'{t:05.1f}.png');rr.append({'time':t,**r})
 (O/'evidence/logo-frame-review.json').write_text(json.dumps({'status':'visual_review_pending','samples':rr},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('samples',len(rr))
