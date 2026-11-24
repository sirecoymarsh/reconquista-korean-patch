"""Shared v3 master rendered at the delivery resolution; source-observed logo motion."""
from functools import lru_cache
from pathlib import Path
import json,hashlib,numpy as np,cv2
from PIL import Image
import render_op_logo_v2 as old
U=Path(__file__).resolve().parents[1];O=U/'candidates/opening-video-ko-v3';MASTER=U/'candidates/brand-logo-ko-v3/master/reconquista-ko.png';SHA='81e8e88a31f70f84ab6bafbe33cfad19787b7e5079206c05f094d82eaa2f51ef';assert hashlib.sha256(MASTER.read_bytes()).hexdigest()==SHA
BBOX=json.loads((MASTER.parent/'provenance.json').read_text(encoding='utf-8'))['crop_bbox_reused'];old.K[:]=0

def metadata(a,t):
 op=1.;ref=a
 if t<19.9:op=float(np.clip((t-19.66)/.17,0,1));ref=old.F[20.4]
 if 29.85<=t<=30.66:op=float(np.clip((30.66-t)/.81,0,1));ref=old.F[29.6]
 if 90.23<=t<90.85:op=float(np.clip((t-90.23)/.62,0,1));ref=old.F[91.0]
 if t>=98.55:op=float(np.clip((100-t)/1.45,0,1));ref=old.F[98.4]
 star=np.zeros((600,800),bool)
 if 30.25<=t<=30.66:
  z=a.astype('float32');star=(abs(z[:,:,0]-z[:,:,1])<20)&(abs(z[:,:,2]-z[:,:,1])<20)&(z.min(2)>55)&(old.X>=320)&(old.X<485)&(old.Y>=240)&(old.Y<355);star=cv2.dilate(star.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)
 return old.colors(ref)[:,0,:].copy(),op,star
@lru_cache(2)
def alpha(s):
 im=Image.open(MASTER).convert('RGBA').crop(BBOX);w=round(400*s);h=round(im.height*w/im.width);im=im.resize((w,h),Image.Resampling.LANCZOS);a=np.zeros((round(600*s),round(800*s)),np.float32);x=round(201*s);y=round(124*s);a[y:y+h,x:x+w]=np.array(im)[:,:,3]/255
 return a

def draw(bg,n,rows,op,star=None,s=1):
 t=n/30.;a=alpha(s).copy()*op;h,w=a.shape;col=np.repeat(rows[:,None,:],800,axis=1)
 if 29.7<=t<=30.66:
  motion=old.profiles(t);mx,my=old.maps(motion['logo_angle'],motion['logo_radius']);col=cv2.remap(col,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
  if s!=1:mx=(cv2.resize(mx,(w,h),interpolation=cv2.INTER_LINEAR)+.5)*s-.5;my=(cv2.resize(my,(w,h),interpolation=cv2.INTER_LINEAR)+.5)*s-.5
  a=cv2.remap(a,mx,my,cv2.INTER_LINEAR)
 if s!=1:col=cv2.resize(col,(w,h),interpolation=cv2.INTER_LINEAR)
 if star is not None and star.any():
  if s!=1:star=cv2.resize(star.astype('uint8'),(w,h),interpolation=cv2.INTER_NEAREST)>0
  a[star]=0
 glow=cv2.GaussianBlur(a,(0,0),1.7*s)*(.10 if t<22 or 90.23<=t<93 else .025)
 if s!=1:a=a[round(75*s):round(525*s)];col=col[round(75*s):round(525*s)];glow=glow[round(75*s):round(525*s)]
 f=bg.astype('float32');f=np.clip(f+glow[:,:,None]*col,0,255);f=f*(1-a[:,:,None])+col*a[:,:,None];return np.clip(np.rint(f),0,255).astype('uint8')