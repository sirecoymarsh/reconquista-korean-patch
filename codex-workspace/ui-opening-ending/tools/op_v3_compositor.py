"""Full OP source lettering removal; every reconstruction stays inside recorded masks."""
from pathlib import Path
from functools import lru_cache
import json,sys,numpy as np,cv2
from PIL import Image,ImageDraw
from op_v3_restoration import *
from op_v3_typeset import CHARS,paint
ID=np.array([[1.,0,0],[0,1.,0]],np.float32)
PRE={'mahoko':(1114,1126),'shiina':(1287,1299),'masaki':(1461,1472),'momiji':(1605,1616),'kureha':(1863,1875)}
@lru_cache(32)
def donor(k):
 if k.startswith('pre-'):
  n=PRE[k[4:]][0];a=read(n);return a,a,np.zeros((600,800),bool)
 if k=='question-pre':a=read(1955);return a,a,np.zeros((600,800),bool)
 if k=='movie-pre':a=read(2330);return a,a,np.zeros((600,800),bool)
 rec=next(r for r in json.loads((P/'donors.json').read_text(encoding='utf-8')) if r['key']==k)
 return load(P/(k+'-source.png')),load(P/(k+'-clean.png')),mask(rec['mask'])

def dilate(m,n):return cv2.dilate(m.astype('uint8'),np.ones((n,n),np.uint8)).astype(bool)&CLIP

def observed_letter_color(a,col=None):
 z=a.astype('float32');r,g,b=z[:,:,0],z[:,:,1],z[:,:,2];white=(np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b])<40)&(np.minimum.reduce([r,g,b])>45)
 if col=='blue':accent=(b>70)&(b>r*1.65)&(g<.75*b)
 elif col=='purple':accent=(r>70)&(b>80)&(g<r*.55)&(g<b*.45)
 else:accent=(r>65)&(g<r*.35)&(b<r*.55)
 return (white|accent)&CLIP
class Compositor:
 def __init__(self):self.last={};self.report=[];self.frame_events=[]
 def aligned(self,k,a,m,n):
  src,clean,sm=donor(k);ex=m|~CLIP
  if k.startswith('pre-'):ex=~CLIP
  if k=='profile':ex|=X>400
  H,c=register(src,a,ex,sm|~CLIP);fallback=False
  if H is not None and (not .6<np.linalg.det(H[:,:2])<2.5 or np.max(abs(H[:,2]))>400):H=None
  if H is None:
   H=self.last.get(k,ID);fallback=True
  else:self.last[k]=H
  self.frame_events.append(dict(key=k,inliers=c,fallback=fallback,matrix=H.tolist()))
  src=cv2.copyMakeBorder(src[75:525],75,75,0,0,cv2.BORDER_REFLECT_101);clean=cv2.copyMakeBorder(clean[75:525],75,75,0,0,cv2.BORDER_REFLECT_101)
  return warp(src,H),warp(clean,H),warp(sm.astype('uint8'),H,True)>0
 def predict(self,k,a,m,n,local=True):
  src,clean,sm=self.aligned(k,a,m,n)
  if not local:
   valid=(CLIP&~sm) if k.startswith('pre-') else (CLIP&~m&~sm);pred=np.empty(a.shape,np.float32)
   for ch in range(3):
    xx=src[:,:,ch][valid].astype('float32');yy=a[:,:,ch][valid].astype('float32');keep=(xx>12)&(xx<245)
    for _ in range(4):
     if keep.sum()<10:gain,off=0.,float(np.median(yy));break
     gain,off=np.linalg.lstsq(np.c_[xx[keep],np.ones(keep.sum())],yy[keep],rcond=None)[0];err=abs(xx*gain+off-yy);keep=err<max(2,np.quantile(err,.7))
    gain=np.clip(gain,0,1.8);off=np.clip(off,-25,25);pred[:,:,ch]=clean[:,:,ch]*gain+off
   return np.clip(pred,0,255)
  return toned(src,clean,a,m,source_mask=sm,local=local)
 def mix(self,k1,k2,a,m,n,q):
  s1,c1,m1=self.aligned(k1,a,m,n);s2,c2,m2=self.aligned(k2,a,m,n);valid=CLIP&~m&~m1&~m2
  # Estimate the observed dissolve where the two plates differ clearly.
  delta=s2.astype('float32')-s1;ok=valid[:,:,None]&(abs(delta)>45);ratio=((a.astype('float32')-s1)/np.where(abs(delta)>1,delta,1))[ok]
  if len(ratio)>1000:q=float(np.clip(np.median(ratio),max(0,q-.22),min(1,q+.22)))
  src=s1*(1-q)+s2*q;clean=c1*(1-q)+c2*q
  return toned(src,clean,a,m,source_mask=m1|m2,local=False)
 def compose(self,a,n):
  correction=O/'build-source/review-repair'/f'{n:04d}.png'
  if correction.exists():
   m=((X>5)&(X<220)&(Y>100)&(Y<510)) if n<2100 else ((X>18)&(X<210)&(Y>180)&(Y<430));out=load(correction);assert np.array_equal(out[~m],a[~m]);rep=dict(frame=n,kind='review-repaired-city' if n<2100 else 'review-repaired-profile',owned_pixels=int(m.sum()),protected_pixel_changes=0,correction=str(correction));self.report.append(rep);return out,m,rep
  self.frame_events=[];m=np.zeros((600,800),bool);pred=None;kind=None
  for k,d in CHARS.items():
   if d['start']<=n<min(d['end'],1648 if k=='momiji' else d['end']):
    kind=k;early=n<PRE[k][1];col='blue' if k in ('mahoko','shiina') else 'purple' if k=='kureha' else 'red'
    if early:
     guess=dilate(observed_letter_color(a,col),31);pred=self.predict('pre-'+k,a,guess,n,local=False);m=CLIP.copy()
    else:
     m=mask(k);pred=self.predict(k,a,m,n)
     # Opening glyphs remain larger for a few frames after the portrait appears.
     if n<d['settle']+5:
      dif=(a.astype('float32')-pred).max(2)>8;dyn=observed_letter_color(a,col)&dif;m|=dilate(dyn,23);pred=self.predict(k,a,m,n,local=False);m=CLIP.copy()
    break
  if 1648<=n<1672:
   kind='momiji-theme-dissolve';m=mask('momiji')|mask('theme');pred=self.mix('momiji','theme',a,m,n,(n-1648)/24)
  elif 1672<=n<1759:
   kind='theme';m=mask('theme');pred=self.predict('theme',a,m,n)
  elif 1956<=n<1989:
   kind='question'
   if n<1979:
    guess=(Y>140)&(Y<440);pred=self.predict('question-pre',a,guess,n);dif=(a.astype('float32')-pred).max(2)>8;m=dilate(observed_letter_color(a,'red')&dif,13)&guess
    if n>=1963:m|=(X>160)&(X<652)&(Y>269)&(Y<328)
   else:
    m=(X>=155)&(X<670)&(Y>=266)&(Y<333);pred=np.roll(a,80,axis=0).astype('float32')
    valid=CLIP&~m;delta=np.median((a.astype('float32')-pred)[valid],axis=0);pred+=delta
  elif 1997<=n<2102:
   kind='cast-main';m=mask(kind)
   if n<2048:pred=self.predict('city',a,m,n,local=False)
   elif n<2064:pred=self.predict('bridge',a,m,n)
   elif n<2100:pred=self.predict('sky',a,m,n)
   else:
    pred=a.astype('float32').copy()
    for yy in range(72,526):
     xx=np.where(m[yy])[0]
     if len(xx):
      left=max(0,int(xx.min())-1);right=min(799,int(xx.max())+1);t=(xx-left)/max(1,right-left);pred[yy,xx]=a[yy,left]*(1-t[:,None])+a[yy,right]*t[:,None]
  elif 2107<=n<2219:
   kind='cast-support';m=mask(kind)
   if n<2135:pred=self.predict('legs',a,m,n)
   elif n<2164:
    pred=self.predict('profile',a,m,n)
    if n>2151:
     # Retain the source's horizontal light scan over the restored hair.
     valid=(X>215)&(X<380)&CLIP;row=np.median((a.astype('float32')-pred)[:,215:380,:],axis=1);row-=cv2.GaussianBlur(row,(1,0),2);pred+=row[:,None,:]
   elif n<2178:pred=poly_background(a,m,235)
   elif n<2187:pred=self.predict('cameo-nana',a,m,n)
   else:pred=self.predict('maho-event',a,m,n)
  elif 2225<=n<2279:
   kind='yue';m=mask(kind);pred=self.predict('yue',a,m,n)
  elif 2331<=n<2449:
   kind='movie';m=mask(kind)
   if n<2340:pred=self.predict('movie-pre',a,m,n)
   elif n<2353:pred=self.mix('movie-pre','movie-maho',a,m,n,(n-2339)/14)
   elif n<2397:pred=self.predict('movie-maho',a,m,n)
   elif n<2410:pred=self.mix('movie-maho','movie-kure',a,m,n,(n-2396)/14)
   else:pred=self.predict('movie-kure',a,m,n)
  elif 2599<=n<2723:
   kind='director';m=mask(kind)
   if n<2635:pred=self.predict('director-early',a,m,n)
   elif n<2655:pred=self.mix('director-early','director-late',a,m,n,(n-2634)/21)
   else:pred=self.predict('director-late',a,m,n)
  if pred is None:return a,None,None
  m&=CLIP;out=merge(a,pred,m,4);rep=dict(frame=n,kind=kind,owned_pixels=int(m.sum()),protected_pixel_changes=0,registrations=self.frame_events);self.report.append(rep)
  return out,m,rep

def ensure_nana():
 if (P/'cameo-nana-clean.png').exists():return
 import shutil
 gen=Path('P:/AI/Codex/generated_images/01a162df-720c-77d2-96ed-6429e90b3333/exec-5f46c6ba-243a-4469-ba4a-f7d2863b8b37.png');shutil.copy2(gen,P/'cameo-nana-generated-original.png');g=np.array(Image.open(gen).convert('RGB').resize((800,600),Image.Resampling.LANCZOS));a=read(2183);m=mask('cast-support');p=toned(g,g,a,m);Image.fromarray(a).save(P/'cameo-nana-source.png');Image.fromarray(merge(a,p,m)).save(P/'cameo-nana-clean.png');rr=json.loads((P/'donors.json').read_text(encoding='utf-8'));rr.append(dict(key='cameo-nana',frame=2183,mask='cast-support',method='masked imagegen restoration of source hand hidden by text',generated_source=str(gen)));(P/'donors.json').write_text(json.dumps(rr,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':
 ensure_nana();c=Compositor();dest=O/'preview/motion-review';dest.mkdir(parents=True,exist_ok=True)
 ns=[1116,1122,1125,1128,1135,1164,1182,1291,1295,1299,1305,1350,1466,1470,1472,1480,1500,1610,1614,1617,1630,1648,1654,1660,1666,1672,1730,1872,1876,1882,1920,1958,1964,1974,1979,1988,2000,2030,2058,2082,2101,2124,2142,2155,2166,2173,2178,2183,2205,2226,2250,2278,2334,2344,2352,2370,2398,2405,2430,2603,2630,2640,2650,2670,2700,2722]
 for i,n in enumerate(ns):
  a=read(n);out,m,r=c.compose(a,n);ko=paint(out,n);Image.fromarray(ko).save(dest/f'{n:04d}.png');Image.fromarray(out).save(dest/f'{n:04d}-clean.png')
  if i%12==0:print('sample',i,n,flush=True)
 for i in range(0,len(ns),9):
  im=Image.new('RGB',(1200,322*((len(ns[i:i+9])+2)//3)),(22,22,22));d=ImageDraw.Draw(im)
  for j,n in enumerate(ns[i:i+9]):x=j%3*400;y=j//3*322;d.text((x+3,y+2),str(n),fill='white');im.paste(Image.open(dest/f'{n:04d}.png').resize((400,300)),(x,y+22))
  im.save(dest/f'contact-{i//9+1}.jpg')
 (O/'evidence/motion-review.json').write_text(json.dumps(c.report,indent=2)+'\n');print('review frames',len(ns),flush=True)