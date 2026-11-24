"""Same observed logo motion/color, bounded float32 row compositing for 4K."""
import cv2,numpy as np
import op_v3_logo as reference
cv2.setNumThreads(2)
TILE=128

def resized_rows(src,y0,y1,w,s):
 # Exact center-aligned linear interpolation; no full-resolution RGB buffer.
 if s==1:return src[y0:y1]
 xx=(np.arange(w,dtype=np.float32)+np.float32(.5))/np.float32(s)-np.float32(.5)
 yy=(np.arange(y0,y1,dtype=np.float32)+np.float32(.5))/np.float32(s)-np.float32(.5)
 ix=np.floor(xx).astype(np.int32);iy=np.floor(yy).astype(np.int32)
 fx=xx-ix;fy=yy-iy
 x0=np.clip(ix,0,src.shape[1]-1);x1=np.clip(ix+1,0,src.shape[1]-1)
 ya=np.clip(iy,0,src.shape[0]-1);yb=np.clip(iy+1,0,src.shape[0]-1)
 fx=fx.astype(np.float32)[None,:];fy=fy.astype(np.float32)[:,None]
 if src.ndim==3:fx=fx[:,:,None];fy=fy[:,:,None]
 upper=src[ya[:,None],x0[None,:]].copy();upper*=1-fx;upper+=src[ya[:,None],x1[None,:]]*fx
 lower=src[yb[:,None],x0[None,:]].copy();lower*=1-fx;lower+=src[yb[:,None],x1[None,:]]*fx
 upper*=1-fy;upper+=lower*fy
 return upper

def draw(bg,n,rows,op,star=None,s=1):
 t=n/30.;base=reference.alpha(s);h,w=base.shape
 col=np.repeat(np.asarray(rows,dtype=np.float32)[:,None,:],800,axis=1)
 if 29.7<=t<=30.66:
  motion=reference.old.profiles(t);mx,my=reference.old.maps(motion['logo_angle'],motion['logo_radius'])
  col=cv2.remap(col,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
  a=np.empty_like(base)
  for y in range(0,h,TILE):
   end=min(y+TILE,h);rx=resized_rows(mx,y,end,w,s);ry=resized_rows(my,y,end,w,s)
   if s!=1:rx+=.5;rx*=s;rx-=.5;ry+=.5;ry*=s;ry-=.5
   a[y:end]=cv2.remap(base,rx,ry,cv2.INTER_LINEAR)
  del mx,my,rx,ry
 else:a=base.copy()
 a*=np.float32(op)
 if star is not None and star.any():
  if s!=1:star=cv2.resize(star.astype('uint8'),(w,h),interpolation=cv2.INTER_NEAREST)>0
  a[star]=0
 glow=cv2.GaussianBlur(a,(0,0),1.7*s);glow*=np.float32(.10 if t<22 or 90.23<=t<93 else .025)
 offset=round(75*s) if s!=1 else 0
 out=bg.copy()
 for y in range(0,bg.shape[0],TILE):
  end=min(y+TILE,bg.shape[0]);sl=slice(y+offset,end+offset)
  c=resized_rows(col,y+offset,end+offset,w,s)
  f=bg[y:end].astype(np.float32);f+=glow[sl,:,None]*c;np.clip(f,0,255,out=f)
  al=a[sl,:,None];f*=1-al;f+=c*al;np.rint(f,out=f);np.clip(f,0,255,out=f)
  out[y:end]=f.astype(np.uint8)
 return out
