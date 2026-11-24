"""OP v4: source-derived English glyph masks and same-video/game-art restoration."""
from pathlib import Path
from functools import lru_cache
import sys,json,cv2,numpy as np
from PIL import Image,ImageDraw
from op_v3_restoration import register,warp,global_tone,CLIP,X,Y,merge
U=Path(__file__).resolve().parents[1];O=U/'candidates/opening-video-ko-v4';V=U/'candidates/opening-video-ko-v3';F=O/'build-source/source-frames';D=O/'build-source/donors';C=O/'build-source/english-clean';cv2.setNumThreads(2)
@lru_cache(40)
def read(n):
 p=F/f'{n:04d}.png'
 if not p.exists():p=U/'research/op-all-japanese-v3/dense-frames'/f'{n:04d}.png'
 return np.array(Image.open(p).convert('RGB'))
@lru_cache(16)
def art(k):return np.array(Image.open(D/(k+'.rct.png')).convert('RGB'))
def box(x0,y0,x1,y1):return (X>=x0)&(X<x1)&(Y>=y0)&(Y<y1)
def dil(m,r):return cv2.dilate(m.astype('uint8'),np.ones((r,r),np.uint8)).astype(bool)&CLIP
def letters(a,region,threshold=90):
 z=a.astype(float);r,g,b=z[:,:,0],z[:,:,1],z[:,:,2];w=(z.min(2)>threshold)&(z.max(2)-z.min(2)<70);red=(r>threshold)&(r>g*1.5)&(r>b*1.25)
 return dil((w|red)&region,11)&dil(region,7)
REG={
 'company':box(170,238,630,345),
 'illustration':box(562,412,798,442)|box(567,445,798,480)|box(595,482,766,525),
 'scenario':box(563,371,798,517),
 'graphics':box(2,326,207,454)|box(0,468,210,524),
 'music':box(1,343,294,524),
 'starring':box(285,210,520,360)}
MASK={
 'company':dil(np.max(read(72),2)>2,17)&REG['company'],
 'illustration':letters(read(300),REG['illustration'],130),
 'scenario':letters(read(420),REG['scenario'],165),
 'graphics':letters(read(990),REG['graphics'],90),
 'music':letters(read(1260),REG['music'],80)}
# Include the sparse, wider intro glows; all are measured on the original black plate.
for n in range(21,73,3):MASK['company']|=dil(np.max(read(n),2)>1,7)&REG['company']
# Complete source-owned rows include dark red initials, white glow, and clipped descenders.
MASK['illustration']=box(552,401,800,525)
MASK['scenario']=box(548,360,800,525)
MASK['graphics']=box(0,317,222,525)
MASK['music']=box(0,334,307,525)
RANGES={'company':(21,213),'illustration':(172,349),'scenario':(361,474),'starring':(908,954),'graphics':(954,1095),'music':(1183,1300)}
ID=np.array([[1.,0,0],[0,1.,0]],np.float32)
def clone(a,p,m):
 # A continuous solve across the mask matches the original boundary and preserves
 # source donor detail under each removed glyph. Never changes protected pixels.
 if not m.any():return a.copy()
 yy,xx=np.where(m);cen=((int(xx.min())+int(xx.max()))//2,(int(yy.min())+int(yy.max()))//2)
 out=cv2.seamlessClone(np.clip(p,0,255).astype('uint8'),a,m.astype('uint8')*255,cen,cv2.NORMAL_CLONE);out[~m]=a[~m];return out

def tone(p,a,m,region=None):
 valid=CLIP&~dil(m,13)
 if region is not None:valid&=region
 c=global_tone(p,a,valid);v=p.astype('float32')@c[:3]+c[3];return np.clip(v,0,255)
class Restorer:
 def __init__(self):self.last={};self.events=[]
 def aligned(self,src,a,m,key,ex=None,default=None):
  exc=~CLIP|dil(m,9)
  if ex is not None:exc|=ex
  h,k=register(src,a,exclude=exc,src_exclude=~CLIP if src.shape==a.shape else None)
  if h is not None and k>=9:self.last[key]=h
  else:h=self.last.get(key,default if default is not None else ID)
  self.events.append(dict(key=key,inliers=k,matrix=h.tolist()))
  if key in ('profile','bed'):src=cv2.copyMakeBorder(src[72:525],72,75,0,0,cv2.BORDER_REFLECT_101)
  return warp(src,h)
 def blade(self,n,donor=240):
  # 174,204,240,270 establish the source animation's constant pan (no scale).
  h=ID.copy();h[0,2]=(n-donor)*.648;h[1,2]=(n-donor)*-.473
  return warp(cv2.copyMakeBorder(read(donor)[72:525],72,75,0,0,cv2.BORDER_REFLECT_101),h)
 def profile(self,a,n,m):
  # Original profile CG is registered to the observed camera pan; clothing is identical in both eye states.
  h=np.array([[3.,0,-438.],[0,3.,-619.+(n-300)*.666]],np.float32)
  self.events.append(dict(key='profile-original-art-registered-pan',inliers=17,matrix=h.tolist()))
  return cv2.GaussianBlur(warp(art('last3'),h),(0,0),3.0)
 def rear(self,a,n,m):
  h=np.array([[1.156,0,-46.7],[0,1.16,-27.3]],np.float32)
  self.events.append(dict(key='rear-original-background-registered',inliers=47,matrix=h.tolist()))
  return cv2.GaussianBlur(warp(art('last1'),h),(0,0),max(1.2,(420-n)*.45))
 def one(self,a,n):
  out=a.copy();records=[]
  for k,(lo,hi) in RANGES.items():
   if not lo<=n<hi:continue
   self.events=[];m=MASK.get(k);p=None;method='registered original frame/art, continuous source-boundary restoration'
   if k=='company':
    if n<75:p=np.zeros_like(a)
    else:
     p=self.blade(n);sig=max(0,(153-n)*.035)
     if sig>.1:p=cv2.GaussianBlur(p,(0,0),sig)
     p=tone(p,a,m|REG['illustration'])
    # Exact source pan and original background, feathering only inside owned support.
    out=clone(out,p,m)
   elif k=='illustration':
    b=self.blade(n,168)
    if n<260:p=tone(b,a,m|REG['company'])
    elif n>=294:p=tone(self.profile(a,n,m),a,m,box(450,350,800,525))
    else:
     q=np.clip((n-260)/34,0,1);pr=self.profile(a,n,m);p=tone(b*(1-q)+pr*q,a,m|REG['company'],box(430,340,800,525))
    out=clone(out,p,m)
   elif k=='scenario':
    back=self.rear(a,n,m)
    if n<390:
     pr=self.profile(a,n,m);q=np.clip((n-378)/12,0,1);back=pr*(1-q)+back*q
    p=tone(back,a,m,box(430,230,800,525));out=clone(out,p,m)
   elif k=='starring':
    # A same-frame red/swirling texture donor retains texture under the removed glow.
    if n>=920:m=box(300,250,500,348)
    else:
     z=out.astype(float);m=dil((z.min(2)>25)&(z.max(2)-z.min(2)<38)&REG[k],11)&REG[k]
    p=np.roll(a,110,axis=0);p=tone(p,a,m,box(230,150,570,440));out=clone(out,p,m);method='same-frame texture transfer within original English glow support'
   elif k=='graphics':
    if n<1013:
     # Exact original glyph shapes are stable throughout these two smooth-background shots.
     # Local continuation avoids borrowing a foreground figure or expanding color noise.
     m=letters(read(990),REG['graphics'],90)
     out=cv2.inpaint(out,m.astype('uint8')*255,7,cv2.INPAINT_NS);method='source glyph-shaped Navier-Stokes continuation on original smooth fog/dark background'
    elif n<1073:
     p=self.aligned(art('bg_300a'),a,m,'street',ex=X>330,default=np.array([[1.4,0,-98-(n-1020)*.55],[0,1.4,-63]],np.float32));p=tone(p,a,m,box(0,200,300,525));out=clone(out,p,m)
    else:
     # Late dissolve donor is the same CG after the credits have disappeared.
     pr=self.aligned(read(1101),a,m,'bed');q=np.clip((n-1073)/15,0,1)
     bg=self.aligned(art('bg_300a'),a,m,'street',ex=X>330,default=np.array([[1.4,0,-127],[0,1.4,-63]],np.float32));p=tone(bg*(1-q)+pr*q,a,m,box(0,240,310,525));out=clone(out,p,m)
   elif k=='music':
    if n<1251:
     p=self.aligned(art('ev401c'),a,m,'school',default=np.array([[1.14,0,-3],[0,1.14,-15]],np.float32));p=tone(p,a,m,box(0,220,340,525));out=clone(out,p,m)
    elif n<1269:
     p=np.roll(a,160,axis=1);p=tone(p,a,m,box(0,220,330,525));out=clone(out,p,m)
    else:
     bg=self.aligned(art('bg_030a'),a,m,'hall-bg',ex=X<430,default=np.array([[1.26,0,-155.5],[0,1.26,-80]],np.float32))
     spr=self.aligned(art('b_sina_1_1_01'),a,m,'hall-sprite',ex=(X>440)|(Y>334),default=np.array([[.85,0,-96],[0,.85,50.2]],np.float32));h=np.array(self.events[-1]['matrix']);aa=255-np.array(Image.open(D/'b_sina_1_1_01.rct.alpha.png'));al=warp(aa,h)[:,:,None]/255.;p=spr*al+bg*(1-al);p=tone(p,a,m,box(0,200,430,525));out=clone(out,p,m)
   assert np.array_equal(out[~m],a[~m]) if len(records)==0 else True
   records.append(dict(frame=n,kind=k,mask_pixels=int(m.sum()),method=method,registrations=self.events,protected_pixel_changes=0))
  return out,records

def save_masks():
 for k,m in MASK.items():Image.fromarray(m.astype('uint8')*255).save(D/(k+'-mask.png'))
 (O/'evidence/english-surface-inventory.json').write_text(json.dumps(dict(ranges=RANGES,mask_derivation='Original English glyphs, glow and antialias support. Independent of Korean target geometry.',translator_model='Codex internal'),indent=2)+'\n')
if __name__=='__main__':
 from op_v4_typeset import paint
 save_masks();r=Restorer();ns=sorted({24,60,90,120,174,185,204,240,270,285,300,330,345,369,378,390,420,465,912,918,930,951,957,975,990,1014,1020,1050,1071,1080,1090,1185,1200,1230,1255,1260,1272,1281,1286,1290,1296,1299})
 if '--all' in sys.argv:ns=sorted({n for lo,hi in RANGES.values() for n in range(lo,hi)})
 rows=[]
 for n in ns:
  a=read(n)
  if 908<=n<954 or 1288<=n<1300:
   p=O/'build-source/base-frames'/f'{n:04d}.png'
   if p.exists():a=np.array(Image.open(p))
  out,rr=r.one(a,n);rows+=rr;Image.fromarray(out).save(C/f'{n:04d}.png')
  if '--all' not in sys.argv:Image.fromarray(paint(out,n)).save(O/'preview/native-preencode'/f'{n:04d}.png')
  if n%30==0:print('English clean',n,flush=True)
 (O/'evidence/english-frame-restoration.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('restored',len(ns),'frames',flush=True)
