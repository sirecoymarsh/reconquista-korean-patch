"""Native-resolution Korean typography for game and 4K OP. Codex internal wording."""
from pathlib import Path
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import numpy as np,cv2,math
U=Path(__file__).resolve().parents[1];O=U/'candidates/opening-video-ko-v3';FONT=O/'fonts/Eulyoo1945-SemiBold.otf'
CHARS={
 'mahoko':dict(surname='하토리',given='마호코',voice='마키 이즈미',side='left',color=(30,126,215),start=1116,settle=1129,end=1183),
 'shiina':dict(surname='가스가이',given='시이나',voice='시바하라 노조미',side='right',color=(30,126,215),start=1288,settle=1301,end=1356),
 'masaki':dict(surname='요시모리',given='마사키',voice='하자와 쓰키노',side='left',color=(198,34,48),start=1462,settle=1475,end=1529),
 'momiji':dict(surname='마키노',given='모미지',voice='호쿠토 미나미',side='right',color=(198,34,48),start=1607,settle=1620,end=1672),
 'kureha':dict(surname='아키즈키',given='쿠레하',voice='호쿠토 미나미',side='left',color=(158,40,205),start=1864,settle=1877,end=1931)}
@lru_cache(150)
def font(size,scale):return ImageFont.truetype(str(FONT),round(size*scale))
def frame_dims(s):return (round(800*s),round(600*s))
class Writer:
 def __init__(self,s):self.s=s;self.im=Image.new('RGBA',frame_dims(s));self.d=ImageDraw.Draw(self.im);self.bounds=[]
 def line(self,text,x,y,size,color=(255,255,255),anchor='left',outline=.65):
  f=font(size,self.s);width=self.d.textlength(text,font=f)/self.s
  if anchor=='center':x-=width/2
  if anchor=='right':x-=width
  assert x>=-1 and x+width<=801,(text,x,width)
  pos=(round(x*self.s),round(y*self.s));self.d.text(pos,text,font=f,fill=(*color,255),stroke_width=round(outline*self.s),stroke_fill=(20,13,22,165),anchor='lt');self.bounds.append((text,x,y,width,size));return width
@lru_cache(64)
def base_layer(kind,s=1):
 w=Writer(s)
 if kind in CHARS:
  d=CHARS[kind];right=d['side']=='right';x=770 if right else 34;anchor='right' if right else 'left';w.line(d['surname'],x,275,50,anchor=anchor,outline=.5)
  text=d['given'];size=88;ft=font(size,s);total=w.d.textlength(text,font=ft)/s;xx=x-total if right else x
  ww=w.line(text[0],xx,348,size,d['color'],outline=.6);w.line(text[1:],xx+ww,348,size,outline=.6)
  w.line('성우  '+d['voice'],x,(450 if s>3 else 477),24,anchor=anchor,outline=.6)
 elif kind=='theme':
  for text,y,size in [('주제가',99,18),('Reconquista',125,28),('노래',174,15),('페이란',196,25),('작곡',234,15),('아게마쓰 노리야스',254,22),('Elements Garden',282,14),('작사',311,15),('우나토미 하지메',331,22),('편곡',367,15),('기쿠타 다이스케',387,22),('Elements Garden',415,14),('기타  가노 노조무',448,19),('바이올린  모리 다쿠야',481,19)]:w.line(text,166,(y-16 if s>3 and y>=448 else y),size,anchor='center',outline=.65)
 elif kind=='cast-main':
  w.line('성우',111,115,20,anchor='center')
  rows=[('아키즈키 쿠레하','호쿠토 미나미'),('하토리 마호코','마키 이즈미'),('마키노 모미지','호쿠토 미나미'),('가스가이 시이나','시바하라 노조미'),('요시모리 마사키','하자와 쓰키노')]
  for i,(name,voice) in enumerate(rows):w.line(name,111,156+i*68,17,anchor='center');w.line(voice,111,181+i*68,22,anchor='center',outline=.8)
 elif kind=='cast-support':
  w.line('성우',113,191,19,anchor='center')
  for i,(name,voice) in enumerate([('다무라 나나코','아오야마 유카리'),('하토리 도모코','기사라기 아오이'),('야시마 미도리','잇시키 히카루')]):w.line(name,113,227+i*77,17,anchor='center');w.line(voice,113,251+i*77,21,anchor='center',outline=.8)
 elif kind=='yue':
  w.line('성우',111,256,18,anchor='center');w.line('시오미 유에',111,288,22,anchor='center');w.line('마쓰다 리사',111,322,25,anchor='center',outline=.8)
 elif kind=='movie':
  w.line('영상 제작',38,438,18);w.line('간즈키 야시로',38,466,25);w.line('[Mju:z]',203,471,19)
 elif kind=='director':
  w.line('디렉터',34,88,18);w.line('우나토미 하지메',34,115,25)
 elif kind=='question':
  pieces=[('…이유가 있으면 사람을 ',(255,255,255),27),('죽여도',(234,30,46),30),(' 되는 거야?',(255,255,255),27)]
  widths=[w.d.textlength(t,font=font(fs,s))/s for t,c,fs in pieces];x=400-sum(widths)/2
  for (text,col,fs),ww in zip(pieces,widths):w.line(text,x,287 if fs==27 else 284,fs,col,outline=.7);x+=ww
 else:raise KeyError(kind)
 # Native frame clipping is the original movie's active picture, not added padding.
 a=np.array(w.im);a[:round(72*s),:,3]=0;a[round(526*s):,:,3]=0
 return a,w.bounds

def overlays(n,s=1):
 layers=[]
 for k,d in CHARS.items():
  if d['start']<=n<d['end']:
   p=np.clip((n-d['start'])/(d['settle']-d['start']),0,1);scale=1+2.2*(1-p)**3;op=min(1,p*3)
   if k=='momiji':op*=np.clip((1672-n)/24,0,1)
   a,_=base_layer(k,s);a=a.copy()
   if scale>1.001:
    cx=(650 if d['side']=='right' else 155)*s;cy=420*s;H=np.array([[scale,0,cx*(1-scale)],[0,scale,cy*(1-scale)]],np.float32);a=cv2.warpAffine(a,H,frame_dims(s),flags=cv2.INTER_LINEAR);a=cv2.GaussianBlur(a,(0,0),max(.1,(scale-1)*1.2*s))
   a[:,:,3]=(a[:,:,3].astype(float)*op).astype('uint8');a[:round(72*s),:,3]=0;a[round(526*s):,:,3]=0;layers.append((k,a))
 for kind,lo,hi,fadein,fadeout in [('theme',1648,1759,22,0),('question',1956,1989,7,7),('cast-main',1989,2102,24,4),('cast-support',2107,2219,10,0),('yue',2225,2279,9,12),('movie',2331,2449,18,0),('director',2599,2723,14,11)]:
  if lo<=n<hi:
   op=min(1,(n-lo+1)/max(1,fadein))
   if fadeout:op*=min(1,(hi-n)/fadeout)
   a,_=base_layer(kind,s);a=a.copy()
   if kind=='question' and n<1964:
    z=1+1.5*(1-(n-1956)/8)**3;H=np.array([[z,0,400*s*(1-z)],[0,z,300*s*(1-z)]],np.float32);a=cv2.warpAffine(a,H,frame_dims(s));a=cv2.GaussianBlur(a,(0,0),max(.1,(z-1)*s))
   a[:,:,3]=(a[:,:,3].astype(float)*op).astype('uint8');a[:round(72*s),:,3]=0;a[round(526*s):,:,3]=0;layers.append((kind,a))
 return layers

def paint(a,n,s=1,crop_4k=False):
 out=a.astype('float32')
 for _,layer in overlays(n,s):
  if crop_4k:layer=layer[360:2520] # 75..525 at scale 4.8 = exact 16:9.
  al=layer[:,:,3:4].astype('float32')/255;out=out*(1-al)+layer[:,:,:3]*al
 return np.clip(np.rint(out),0,255).astype('uint8')
if __name__=='__main__':
 P=O/'preview/typography';P.mkdir(parents=True,exist_ok=True);rep=[]
 for kind in [*CHARS,'theme','cast-main','cast-support','yue','movie','director','question']:
  ar,bounds=base_layer(kind,2);Image.fromarray(ar).resize((800,600),Image.Resampling.LANCZOS).save(P/(kind+'.png'));rep.append({'id':kind,'bounds':bounds})
 import json
 (O/'evidence/typography.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('typography layers',len(rep))