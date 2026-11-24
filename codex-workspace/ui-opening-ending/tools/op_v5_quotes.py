"""Restore the source-owned logo paragraph and typeset compact Korean at output scale."""
from pathlib import Path
from functools import lru_cache
import json,cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
import render_op_logo_v2 as geom
U=Path(__file__).resolve().parents[1];O=U/'candidates/opening-video-ko-v5';FONT=O/'fonts/Eulyoo1945-SemiBold.otf'
LINES=json.loads((O/'revision-policy.json').read_text(encoding='utf-8'))['quote_lines']
Y,X=np.mgrid[:600,:800].astype('float32');BASE=np.zeros((600,800),np.float32);BASE[391:426,247:438]=1

def active(n):return 638<=n<=920 or 2745<=n<3000

def maps(n):
 if 891<=n<=920:
  p=geom.profiles(n/30);return geom.maps(p['logo_angle'],p['logo_radius'])
 return None

def ownership(n):
 m=BASE.copy();mp=maps(n)
 if mp is not None:m=cv2.remap(m,*mp,cv2.INTER_LINEAR)
 m=cv2.dilate((m>.001).astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)
 if 891<=n<=920:m[354:454,229:466]=True
 return m

def gradient(a,m):
 # Same-frame surface from the surrounding unlettered dark backdrop.
 valid=(X>=231)&(X<458)&(Y>=389)&(Y<449)&~m
 valid &= (a.min(2)<80)
 xx=(X-345)/110;yy=(Y-410)/40
 poly=np.stack([np.ones_like(X),xx,yy,xx*xx,xx*yy,yy*yy,xx**3,xx*xx*yy,xx*yy*yy,yy**3],2)
 aa=poly[valid];bb=a[valid].astype('float32');weights=np.ones(len(aa),np.float32)
 for _ in range(3):
  coef=np.linalg.lstsq(aa*weights[:,None],bb*weights[:,None],rcond=1e-5)[0];err=np.max(abs(aa@coef-bb),1);weights=np.minimum(1,3/np.maximum(err,1))
 return np.clip(poly@coef,0,255)

def clean(a,n):
 if not active(n):return a,None
 m=ownership(n);z=a.astype('float32')
 # Measure source quote visibility, independent of the new glyph mask.
 measure=BASE.copy();mp=maps(n)
 if mp is not None:measure=cv2.remap(measure,*mp,cv2.INTER_LINEAR)
 strength=float(np.clip(np.percentile(a.min(2)[measure>.5],99.5)/220,0,1))
 if 747<=n<=920:
  exclude=m.copy();exclude[372:429,242:452]=True
  if n<834:
   pred,_=geom.legacy.city_bg(a,exclude,n/30)
  else:pred=geom.dense_bg(a,exclude,geom.profiles(n/30))
  pred=geom.tone(pred,a,exclude,24 if 891<=n<=920 else 9);model='registered original city artwork with source-observed radial motion and local tone'
 else:pred=gradient(a,m);model='same-frame dark background color surface from surrounding non-text pixels'
 dist=cv2.distanceTransform(m.astype('uint8'),cv2.DIST_L2,3);w=np.clip(dist/2.4,0,1)
 out=np.clip(np.rint(z*(1-w[:,:,None])+pred*w[:,:,None]),0,255).astype('uint8')
 if 891<=n<=920:
  bx,by,bw,bh=cv2.boundingRect(m.astype('uint8'));cl=cv2.seamlessClone(np.clip(np.rint(pred),0,255).astype('uint8'),a,m.astype('uint8')*255,(bx+bw//2,by+bh//2),cv2.NORMAL_CLONE);out[m]=cl[m]
  model+='; source donor gradients joined to surrounding frame with Poisson boundary matching'
 assert np.array_equal(out[~m],a[~m])
 return out,dict(frame=n,opacity=strength,mask_pixels=int(m.sum()),protected_pixel_diff=0,model=model)

@lru_cache(2)
def roman(s):
 ref=np.array(Image.open(O/'build-source/quote-probes/n2850.png').convert('RGB'));a=np.zeros((600,800),np.float32)
 q=np.maximum(ref[374:391,247:440].min(2).astype('float32')-5,0);q/=max(float(q.max()),1);a[374:391,247:440]=q
 if s!=1:a=np.clip(cv2.resize(a,(round(800*s),round(600*s)),interpolation=cv2.INTER_LANCZOS4),0,1)
 return a

@lru_cache(2)
def layer(s):
 # Supersample the game version; 4K uses a separate native-size rasterization.
 ss=4 if s==1 else s
 im=Image.new('RGBA',(round(800*ss),round(600*ss)));d=ImageDraw.Draw(im);f=ImageFont.truetype(str(FONT),round(9*ss));bounds=[]
 for i,t in enumerate(LINES):
  x=253;y=393.3+i*10.0;ww=d.textlength(t,font=f)/ss;assert ww<190,(t,ww)
  d.text((round(x*ss),round(y*ss)),t,font=f,fill=(255,255,255,255),anchor='lt',stroke_width=round(.22*ss),stroke_fill=(8,6,9,190));bounds.append([t,x,y,ww,9])
 if s==1:im=im.resize((800,600),Image.Resampling.LANCZOS)
 return np.array(im),bounds

def draw(a,n,op,s=1):
 if not active(n) or op<.003:return a
 p,_=layer(s);p=p.copy();mp=maps(n)
 if mp is not None:
  rr=roman(s);p[rr>0,:3]=255;p[:,:,3]=np.maximum(p[:,:,3],np.rint(rr*255).astype('uint8'))
  mx,my=mp
  if s!=1:
   wh=(round(800*s),round(600*s));mx=(cv2.resize(mx,wh,interpolation=cv2.INTER_LINEAR)+.5)*s-.5;my=(cv2.resize(my,wh,interpolation=cv2.INTER_LINEAR)+.5)*s-.5
  p=cv2.remap(p,mx,my,cv2.INTER_LINEAR)
 if s!=1:p=p[round(75*s):round(525*s)]
 x,y,w,h=cv2.boundingRect(p[:,:,3]);out=a.copy()
 if w:
  q=p[y:y+h,x:x+w];al=q[:,:,3:4].astype('float32')/255*op
  out[y:y+h,x:x+w]=np.clip(np.rint(out[y:y+h,x:x+w]*(1-al)+q[:,:,:3]*al),0,255).astype('uint8')
 return out

if __name__=='__main__':
 import op_v3_logo as logo
 cc=dict(np.load(U/'candidates/opening-video-ko-v3/build-source/logo-observed-color-motion.npz'));ii={int(n):i for i,n in enumerate(cc['frames'])}
 rows=json.loads((O/'evidence/quote-probe-frames.json').read_text());dest=O/'preview/quote-layout';dest.mkdir(exist_ok=True);reports=[]
 for r in rows:
  n=r['frame']
  if not 891<=n<=920:continue
  vp=U/'candidates/opening-video-ko-v4/build-source/english-clean'/f'{n:04d}.png'
  a=np.array(Image.open(vp if vp.exists() else r['path']).convert('RGB'));bg,rep=clean(a,n)
  if rep is None:continue
  if n in ii:
   k=ii[n];star=np.unpackbits(cc['star'][k]).reshape(600,800).astype(bool);star[:]=False
   bg=logo.draw(bg,n,cc['colors'][k],float(cc['opacity'][k]),star)
  from op_v4_typeset import paint as paint_v4
  final=draw(paint_v4(bg,n),n,rep['opacity']);Image.fromarray(final).save(dest/f'{n:04d}.png');Image.fromarray(bg).save(dest/f'{n:04d}-clean.png');reports.append(rep)
 im=Image.new('RGB',(1200,150*((len(reports)+3)//4)),(22,22,22));d=ImageDraw.Draw(im)
 for i,r in enumerate(reports):
  n=r['frame'];a=Image.open(dest/f'{n:04d}.png');x=i%4*300;y=i//4*150;im.paste(a.crop((238,369,454,438)).resize((300,96)),(x,y+25));d.text((x+4,y+4),f"n{n} opacity {r['opacity']:.2f}",fill='white')
 im.save(O/'preview/quote-transition-review.png');(O/'evidence/quote-transition-probe.json').write_text(json.dumps({'frames':reports,'layout':layer(1)[1]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('quote layout samples',len(reports))
