from pathlib import Path
import numpy as np,cv2,json
from PIL import Image
# Import helpers without executing prototype batch.
s=Path('tools/probe_op_polar_geometry.py').read_text(encoding='utf-8-sig');exec(s.split('stats=[]')[0])

def joint(source,target,sv,tv,limit=100,rlimit=15):
 s=polar(source);t=polar(target);ms=(polar(sv)>.98).astype('float32');mt=(polar(tv)>.98).astype('float32');t*=mt
 ti=[np.fft.rfft(z,axis=0).conj() for z in [mt,t,t*t]];bestq=np.ones(NR)*-3;bestshift=np.zeros(NR);bestr=np.zeros(NR);shifts=np.arange(-limit,limit+1)
 for dr in range(-rlimit,rlimit+1):
  ss=np.roll(s,-dr,axis=1);mm=np.roll(ms,-dr,axis=1);ss*=mm;sf=[np.fft.rfft(z,axis=0) for z in [mm,ss,ss*ss]]
  def cc(i,j):return np.fft.irfft(ti[i]*sf[j],n=N,axis=0).real
  n=cc(0,0);su=cc(0,1);tu=cc(1,0);num=cc(1,1)-su*tu/np.maximum(n,1);sd=cc(0,2)-su*su/np.maximum(n,1);td=cc(2,0)-tu*tu/np.maximum(n,1);q=num/np.sqrt(np.maximum(sd*td,1));q[n<40]=-3
  vals=q[shifts%N];idx=np.argmax(vals,axis=0);score=vals[idx,np.arange(NR)];wins=score>bestq;bestq[wins]=score[wins];bestshift[wins]=shifts[idx][wins];bestr[wins]=dr
 good=(bestq>.5)&(np.arange(NR)>10)&(np.arange(NR)<360)
 for z in [bestshift,bestr]:
  z[:]=np.interp(np.arange(NR),np.where(good)[0],z[good]);z[:]=cv2.GaussianBlur(z.astype('float32').reshape(-1,1),(1,0),.7).ravel()
 return bestshift,bestr,bestq

def mapper(sh,dr):
 ang=theta+np.interp(rad,np.arange(NR),sh)*2*np.pi/N;r=rad+np.interp(rad,np.arange(NR),dr);return (400+r*np.cos(ang)).astype('float32'),(300+r*np.sin(ang)).astype('float32')

def tone(bg,a,mask):
 valid=(clip&~mask).astype('float32');valid[374:426,240:455]=0
 den=cv2.GaussianBlur(valid,(0,0),12);den=np.maximum(den,.0001);out=np.empty_like(bg)
 for c in range(3):
  b=bg[:,:,c];t=a[:,:,c];mb=cv2.GaussianBlur(b*valid,(0,0),12)/den;mt=cv2.GaussianBlur(t*valid,(0,0),12)/den;vb=cv2.GaussianBlur(b*b*valid,(0,0),12)/den-mb*mb;ct=cv2.GaussianBlur(t*b*valid,(0,0),12)/den-mt*mb;gain=np.clip(ct/np.maximum(vb,5),.2,2);out[:,:,c]=b*gain+mt-mb*gain
 return np.clip(out,0,255)
for time in [27.0,28.4,29.4,30.0,30.3]:
 a=F[time].astype('float32');excess=np.maximum(a[:,:,0]-np.maximum(a[:,:,1],a[:,:,2])-30,0);red=(excess>30)&(X>150)&(X<660)&(Y>90)&(Y<480);tv=clip&~cv2.dilate(red.astype('uint8'),np.ones((13,13),np.uint8)).astype(bool)
 sh,dr,co=joint(signal,(a[:,:,1]+a[:,:,2])/2,sv,tv);mx,my=mapper(sh,dr);bg=cv2.remap(clean27,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
 if time>=29.7:
  ls,ld,lc=joint(sourceLogo,excess,clip,clip,rlimit=4);lx,ly=mapper(ls,ld);mask=cv2.remap(old.astype('float32'),lx,ly,cv2.INTER_LINEAR)>.01;ka=cv2.remap(K,lx,ly,cv2.INTER_LINEAR)
 else:mask=old.copy();ka=K.copy()
 mask|=cv2.dilate(red.astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);mask &=clip;bg=tone(bg,a,mask);clean=a.copy();clean[mask]=bg[mask];out=clean*(1-ka[:,:,None])+np.array([206,21,60])*ka[:,:,None]
 Image.fromarray(out.astype('uint8')).save(O/f'joint-final-{time:04.1f}.png');Image.fromarray(clean.astype('uint8')).save(O/f'joint-clean-{time:04.1f}.png');np.savez_compressed(O/f'joint-{time:04.1f}.npz',background_angle=sh,background_radius=dr)
 print(time,'median correlation',np.median(co[20:300]),'radius range',dr[:300].min(),dr[:300].max(),flush=True)
