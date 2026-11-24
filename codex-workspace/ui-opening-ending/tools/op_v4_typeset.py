"""Native-resolution Korean typography for game and 4K OP. Codex internal wording."""
from pathlib import Path
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import numpy as np,cv2,math
U=Path(__file__).resolve().parents[1];O=U/'candidates/opening-video-ko-v4';FONT=O/'fonts/Eulyoo1945-SemiBold.otf'
CHARS={
 'mahoko':dict(surname='하토리',given='마호코',voice='마키 이즈미',side='left',color=(30,126,215),start=1116,settle=1129,end=1183),
 'shiina':dict(surname='카스가이',given='시이나',voice='시바하라 노조미',side='right',color=(30,126,215),start=1288,settle=1301,end=1356),
 'masaki':dict(surname='요시모리',given='마사키',voice='하자와 츠키노',side='left',color=(198,34,48),start=1462,settle=1475,end=1529),
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
def legacy_base_layer(kind,s=1):
 w=Writer(s)
 if kind in CHARS:
  d=CHARS[kind];right=d['side']=='right';x=770 if right else 34;anchor='right' if right else 'left';w.line(d['surname'],x,275,50,anchor=anchor,outline=.5)
  text=d['given'];size=88;ft=font(size,s);total=w.d.textlength(text,font=ft)/s;xx=x-total if right else x
  ww=w.line(text[0],xx,348,size,d['color'],outline=.6);w.line(text[1:],xx+ww,348,size,outline=.6)
  w.line('성우  '+d['voice'],x,(450 if s>3 else 477),24,anchor=anchor,outline=.6)
 elif kind=='theme':
  for text,y,size in [('주제가',99,18),('레콘키스타',125,28),('노래',174,15),('페이란',196,25),('작곡',234,15),('아게마츠 노리야스',254,22),('엘리먼츠 가든',282,14),('작사',311,15),('우나토미 하지메',331,22),('편곡',367,15),('키쿠타 다이스케',387,22),('엘리먼츠 가든',415,14),('기타  카노 노조무',448,19),('바이올린  모리 타쿠야',481,19)]:w.line(text,166,(y-16 if s>3 and y>=448 else y),size,anchor='center',outline=.65)
 elif kind=='cast-main':
  w.line('성우',111,115,20,anchor='center')
  rows=[('아키즈키 쿠레하','호쿠토 미나미'),('하토리 마호코','마키 이즈미'),('마키노 모미지','호쿠토 미나미'),('카스가이 시이나','시바하라 노조미'),('요시모리 마사키','하자와 츠키노')]
  for i,(name,voice) in enumerate(rows):w.line(name,111,156+i*68,17,anchor='center');w.line(voice,111,181+i*68,22,anchor='center',outline=.8)
 elif kind=='cast-support':
  w.line('성우',113,191,19,anchor='center')
  for i,(name,voice) in enumerate([('타무라 나나코','아오야마 유카리'),('하토리 토모코','키사라기 아오이'),('야시마 미도리','잇시키 히카루')]):w.line(name,113,227+i*77,17,anchor='center');w.line(voice,113,251+i*77,21,anchor='center',outline=.8)
 elif kind=='yue':
  w.line('성우',111,256,18,anchor='center');w.line('시오미 유에',111,288,22,anchor='center');w.line('마츠다 리사',111,322,25,anchor='center',outline=.8)
 elif kind=='movie':
  w.line('영상 제작',38,438,18);w.line('칸즈키 야시로',38,466,25);w.line('[뮤즈]',203,471,19)
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

def legacy_overlays(n,s=1):
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

# v4 English credits, in the original lower corner / center slots.
EARLY={
 'company':(21,213,55,38), 'illustration':(172,349,38,28),
 'scenario':(361,474,32,0), 'starring':(908,954,12,0),
 'graphics':(954,1095,28,25), 'music':(1183,1300,30,20)}
@lru_cache(64)
def base_layer(kind,s=1):
 if kind not in EARLY:return legacy_base_layer(kind,s)
 w=Writer(s)
 def accent(t,x,y,fs,red=True):
  total=w.d.textlength(t,font=font(fs,s))/s;x-=total/2
  if red and t:
   ww=w.line(t[0],x,y,fs,(180,25,35),outline=.65);w.line(t[1:],x+ww,y,fs,outline=.65)
  else:w.line(t,x,y,fs,outline=.65)
 if kind=='company':
  t='코튼소프트 두 번째 작품';accent(t,400,288,25,False)
 elif kind=='illustration':
  for t,y,fs in [('캐릭터 디자인·원화',419,18),('앙코로모치',451,28),('사사이 사지',487,28)]:accent(t,681,y,fs)
 elif kind=='scenario':
  for t,y,fs in [('시나리오',377,19),('우나토미 하지메',409,25),('아키츠 타마키',447,25),('오츠키 유스케',485,25)]:accent(t,679,y,fs)
 elif kind=='starring':
  accent('레콘키스타',400,269,18,False);accent('등장인물',400,297,28,False)
 elif kind=='graphics':
  for t,y,fs in [('그래픽 제작',334,18),('하루친',361,23),('피카이치',389,23),('신이치로 외',418,23),('프로그래밍',470,18),('코시하타 세이타',496,22)]:accent(t,111,y,fs)
 elif kind=='music':
  for t,y,fs in [('음악',347,18),('엘리먼츠 가든',372,22),('바바리안 온 더 그루브',397,19),('센티브',422,22),('443',445,22),('이데 쿄코',468,22),('타테우치 외',492,22)]:accent(t,150,y,fs)
 a=np.array(w.im);a[:round(72*s),:,3]=0;a[round(526*s):,:,3]=0
 return a,w.bounds

def overlays(n,s=1):
 layers=legacy_overlays(n,s)
 for k,(lo,hi,fi,fo) in EARLY.items():
  if lo<=n<hi:
   op=min(1,(n-lo+1)/fi)
   if fo:op*=min(1,(hi-n)/fo)
   a,_=base_layer(k,s);a=a.copy()
   if k=='company' and n<72:
    sigma=max(.1,(72-n)*.13*s);a=cv2.GaussianBlur(a,(0,0),sigma)
   if k=='starring' and n<920:
    z=1+.5*(1-(n-908)/12)**2;h=np.array([[z,0,400*s*(1-z)],[0,z,300*s*(1-z)]],np.float32);a=cv2.warpAffine(a,h,frame_dims(s));a=cv2.GaussianBlur(a,(0,0),max(.1,(z-1)*4*s))
   a[:,:,3]=(a[:,:,3].astype(float)*op).astype('uint8');layers.append((k,a))
 return layers


def paint(a,n,s=1,crop_4k=False):
 layers=overlays(n,s)
 if not layers:return a
 out=a.copy()
 for _,layer in layers:
  if crop_4k:layer=layer[360:2520]
  x,y,w,h=cv2.boundingRect(layer[:,:,3])
  if w==0 or h==0:continue
  p=layer[y:y+h,x:x+w];al=p[:,:,3:4].astype('float32')/255
  v=out[y:y+h,x:x+w].astype('float32')*(1-al)+p[:,:,:3]*al
  out[y:y+h,x:x+w]=np.clip(np.rint(v),0,255).astype('uint8')
 return out
