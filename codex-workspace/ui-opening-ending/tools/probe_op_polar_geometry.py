from pathlib import Path
import numpy as np,cv2,json
from PIL import Image
U=Path.cwd();R=U/'research/op-logo';O=R/'polar-probe';cv2.setNumThreads(2)
rs=json.loads((R/'frames.json').read_text());rs+=json.loads((R/'late-transition/frames.json').read_text());F={r['time']:np.array(Image.open(r['path']).convert('RGB')) for r in rs}
Y,X=np.mgrid[:600,:800].astype('float32');clip=(Y>=72)&(Y<526);rad=np.hypot(X-400,Y-300);theta=np.arctan2(Y-300,X-400);old=np.load(O/'old-logo-mask.npy');N=1024;NR=510

def polar(a):return cv2.warpPolar(a.astype('float32'),(NR,N),(400,300),NR,cv2.WARP_POLAR_LINEAR|cv2.WARP_FILL_OUTLIERS|cv2.INTER_LINEAR)
def corr(a,b):return np.fft.irfft(np.conj(np.fft.rfft(a,axis=0))*np.fft.rfft(b,axis=0),n=N,axis=0).real

def angular_shift(source,target,sv,tv,limit=100):
 s=polar(source);t=polar(target);ms=polar(sv)>.98;mt=polar(tv)>.98;s*=ms;t*=mt;n=corr(mt,ms);su=corr(mt,s);tu=corr(t,ms);num=corr(t,s)-su*tu/np.maximum(n,1);sd=corr(mt,s*s)-su*su/np.maximum(n,1);td=corr(t*t,ms)-tu*tu/np.maximum(n,1);q=num/np.sqrt(np.maximum(sd*td,1));q[n<30]=-2
 shifts=np.arange(-limit,limit+1);vals=q[shifts%N];idx=np.argmax(vals,axis=0);best=shifts[idx].astype('float32');confidence=vals[idx,np.arange(NR)]
 mm=q[(best.astype(int)-1)%N,np.arange(NR)];pp=q[(best.astype(int)+1)%N,np.arange(NR)];zero=q[best.astype(int)%N,np.arange(NR)];best+=np.clip(.5*(mm-pp)/(mm-2*zero+pp+1e-8),-.5,.5)
 good=(confidence>.3)&(np.arange(NR)>8)&(np.arange(NR)<470)
 if good.sum()<5:return np.zeros(NR,np.float32),confidence
 best=np.interp(np.arange(NR),np.where(good)[0],best[good]).astype('float32');best=cv2.GaussianBlur(best.reshape(-1,1),(1,0),.7).ravel();return best,confidence

def remap(a,sh):
 ang=theta+np.interp(rad,np.arange(NR),sh)*2*np.pi/N;return cv2.remap(a.astype('float32'),(400+rad*np.cos(ang)).astype("float32"),(300+rad*np.sin(ang)).astype("float32"),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)

city=np.array(Image.open(R/'city-donor-registered.png')).astype('float32');m=old;valid=clip&~m
xx=(X-400)/400;yy=(Y-300)/300;features=np.concatenate([city/255,city*xx[:,:,None]/255,city*yy[:,:,None]/255,np.ones((600,800,1)),xx[:,:,None],yy[:,:,None],xx[:,:,None]**2,yy[:,:,None]**2,(xx*yy)[:,:,None]],2);coef=np.linalg.lstsq(features[::3,::3][valid[::3,::3]],F[27.0][::3,::3][valid[::3,::3]],rcond=1e-6)[0];clean27=np.clip(features@coef,0,255).astype('float32');Image.fromarray(np.uint8(clean27)).save(O/'clean-city27-full.png')
ref=F[27.0].astype('float32');sv=clip&~old;signal=(ref[:,:,1]+ref[:,:,2])/2;sourceLogo=np.maximum(F[95.0][:,:,0].astype('float32')-np.maximum(F[95.0][:,:,1],F[95.0][:,:,2])-30,0)*old
master=Image.open(U/'candidates/brand-logo-ko-v2/master/reconquista-ko.png').convert('RGBA');bbox=Image.open(U/'candidates/brand-logo-ko-v1/master/reconquista-ko.png').getchannel('A').getbbox();master=master.crop(bbox);master=master.resize((400,round(master.height*400/master.width)),Image.Resampling.LANCZOS);K=np.zeros((600,800),np.float32);K[124:124+master.height,201:601]=np.array(master)[:,:,3]/255
stats=[]
for time in [27.0,28.0,28.4,29.4,29.8,30.0,30.2,30.3,30.4,30.5]:
 a=F[time].astype('float32');excess=np.maximum(a[:,:,0]-np.maximum(a[:,:,1],a[:,:,2])-30,0);currentred=(excess>30)&(X>160)&(X<650)&(Y>95)&(Y<460);tv=clip&~cv2.dilate(currentred.astype('uint8'),np.ones((13,13),np.uint8)).astype(bool)
 sh,conf=angular_shift(signal,(a[:,:,1]+a[:,:,2])/2,sv,tv,100);bg=remap(clean27,sh)
 if time>=29.7:
  ls,lc=angular_shift(sourceLogo,excess,clip,clip,100);mask=remap(old.astype('float32'),ls)>.01;ka=remap(K,ls)
 else:ls=np.zeros(NR);mask=old;ka=K
 mask|=cv2.dilate(currentred.astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);mask &= clip
 # Photometric matching is smooth; geometry is observed from each radial ring.
 val=clip&~mask;feat=np.concatenate([bg/255,np.ones((600,800,1)),xx[:,:,None],yy[:,:,None],(xx*yy)[:,:,None],xx[:,:,None]**2,yy[:,:,None]**2],2);co=np.linalg.lstsq(feat[::4,::4][val[::4,::4]],a[::4,::4][val[::4,::4]],rcond=1e-6)[0];bg=np.clip(feat@co,0,255)
 clean=a.copy();clean[mask]=bg[mask];out=clean*(1-ka[:,:,None])+np.array([206,21,60])*ka[:,:,None]
 for tag,img in [('clean',clean),('final',out)]:Image.fromarray(np.uint8(np.clip(img,0,255))).save(O/f'{tag}-{time:04.1f}.png')
 np.savez_compressed(O/f'shifts-{time:04.1f}.npz',background=sh,logo=ls)
 e=np.abs(bg[val]-a[val]);stats.append({'time':time,'bg_abs_error':float(e.mean()),'bg_correlation':float(np.median(conf[20:330])),'shift_range':[float(sh.min()),float(sh.max())]})
(O/'report.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats,indent=2))

