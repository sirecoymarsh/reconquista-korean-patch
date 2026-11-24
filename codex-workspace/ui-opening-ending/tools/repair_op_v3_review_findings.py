from pathlib import Path
import sys,json,numpy as np,cv2
from PIL import Image
sys.path.insert(0,'tools')
from op_v3_restoration import *
from op_v3_compositor import Compositor
from op_v3_typeset import paint
V=O/'preview/review-repair';D=O/'build-source/review-repair';V.mkdir(exist_ok=True);D.mkdir(exist_ok=True)
CITY=(X>5)&(X<220)&(Y>100)&(Y<510);PROF=(X>18)&(X<210)&(Y>180)&(Y<430)
def clone(a,p,m):
 ys,xs=np.where(m);center=((int(xs.min())+int(xs.max()))//2,(int(ys.min())+int(ys.max()))//2);out=cv2.seamlessClone(np.clip(p,0,255).astype('uint8'),a,m.astype('uint8')*255,center,cv2.NORMAL_CLONE);out[~m]=a[~m];assert np.array_equal(out[~m],a[~m]);return out

def fit(src,target,valid):
 c=global_tone(src,target,valid);return src.astype('float32')@c[:3]+c[3]
class Repair:
 def __init__(self):
  self.c=Compositor();self.art=[load(R/'extra-source-art'/f'last{k}.rct.png') for k in [2,3]];self.closed={};self.lastopen=None
  for n in [2135,2142]:
   h,c=register(self.art[0],read(n),exclude=PROF|~CLIP|(X>410));assert h is not None;self.closed[n]=h
  self.c.aligned('city',read(1998),mask('cast-main'),1998)
 def one(self,n):
  a=read(n);m=CITY if n<2100 else PROF;rec=dict(frame=n,owned_pixels=int(m.sum()),protected_pixel_changes=0)
  if n<2100:
   k='bridge' if n>=2047 else 'city';ss,cc,sm=self.c.aligned(k,a,mask('cast-main'),n);p=toned(ss,cc,a,m,source_mask=sm,local=False);rec.update(kind=k,method='registered masked donor; continuous Poisson boundary instead of independent color strip')
  elif n>=2162:
   p=poly_background(a,m,245);rec.update(kind='cameo-tomoko',method='source-only smooth red background')
  else:
   h=self.closed[2135]+(self.closed[2142]-self.closed[2135])*((n-2135)/7);w=warp(self.art[0],h);valid=CLIP&~m&(X<410);p=fit(w,a,valid);red=np.median(a[:,8:22,0].astype(float)-a[:,8:22,2],axis=1)>5;red&=(np.arange(600)>=72)&(np.arange(600)<525)
   if red.any():red[np.where(red)[0].min():np.where(red)[0].max()+1]=True
   if red.sum()>20:
    rmask=np.broadcast_to(red[:,None],(600,800));hh,count=register(self.art[1],a,exclude=m|~rmask|(X>540))
    if hh is not None and count>=12:self.lastopen=hh
    if self.lastopen is not None:
     ww=warp(self.art[1],self.lastopen);p2=fit(ww,a,rmask&~m&(X<540));p[rmask]=p2[rmask];rec['open_matrix']=self.lastopen.tolist();rec['open_inliers']=count
   rec.update(kind='profile',method='original last2/last3 artwork with separate expanding red-band pose and continuous Poisson boundary',closed_matrix=h.tolist(),red_rows=np.where(red)[0].tolist())
  out=clone(a,p,m)
  if 2146<=n<=2161:
   # Reapply the source's narrow additive red scan line, estimated from the
   # untouched x=4..18 strip where no credit glyph is present.
   upper=a[294:297,4:18].mean((0,1));lower=a[304:307,4:18].mean((0,1))
   for yy in range(297,304):
    bg=upper+(lower-upper)*((yy-295.5)/10);obs=a[yy,4:18].mean(0);al=np.clip((obs-bg)/np.maximum(1,255-bg),0,1)
    if al[0]>.012:
     xx=np.where(m[yy])[0];out[yy,xx]=np.clip(out[yy,xx]+(255-out[yy,xx].astype(float))*al,0,255).astype('uint8')
   rec['red_scanline']='source-derived screen blend restored at y297..303'
  return out,rec
if __name__=='__main__':
 rr=Repair();rows=[];ns=list(range(1989,2048))+list(range(2135,2164)) if '--all' in sys.argv else [2142,2149,2155]
 if '--laser-only' in sys.argv:ns=list(range(2146,2161))
 for n in ns:
  out,r=rr.one(n);rows.append(r);Image.fromarray(out).save(D/f'{n:04d}.png')
  if '--all' not in sys.argv or n in [1989,1993,2024,2046,2047,2142,2146,2149,2155,2160,2161,2163]:Image.fromarray(out).save(V/f'{n}-final-clean.png');Image.fromarray(paint(out,n)).save(V/f'{n}-final.png')
  if n%10==0:print(n,flush=True)
 old=json.loads((D/'repairs.json').read_text()) if (D/'repairs.json').exists() else [];allrows={r['frame']:r for r in old};allrows.update({r['frame']:r for r in rows});(D/'repairs.json').write_text(json.dumps(sorted(allrows.values(),key=lambda r:r['frame']),indent=2)+'\n');print('repair frames',len(rows),flush=True)
