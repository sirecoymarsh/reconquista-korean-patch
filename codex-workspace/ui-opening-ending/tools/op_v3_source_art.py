from pathlib import Path
import sys,struct,json,re
import numpy as np
from PIL import Image,ImageDraw
U=Path(__file__).resolve().parents[1];sys.path.insert(0,str(U.parent/'tools'));sys.path.insert(0,str(U/'tools'))
from inspect_majiro import Arc
from raster_codec import raw_image
class SourceArt:
 def __init__(self):
  self.arcs={n:Arc(U.parent/'research/disc'/n) for n in ['data.arc','data1.arc','data2.arc','slowdata.arc']};self.idx={}
  for fn,a in self.arcs.items():
   for e in a.entries:self.idx.setdefault(e['name'],(fn,e))
  self.cache={}
 def decode(self,n):
  if n in self.cache:return self.cache[n]
  fn,e=self.idx[n]
  with self.arcs[fn].path.open('rb') as h:h.seek(e['offset']);b=h.read(e['size'])
  a,_,_=raw_image(b)
  if b[4:8]==b'TC01':
   k=struct.unpack_from('<H',b,20)[0];base=b[22:22+k].rstrip(b'\0').decode('cp932');base+=('' if base.endswith('.rct') else '.rct');m=np.all(a==[255,0,0],axis=2);a[m]=self.decode(base)[m]
  self.cache[n]=a;return a
if __name__=='__main__':
 S=SourceArt();R=U/'research/op-all-japanese-v3/extra-source-art';names=[n for n in S.idx if n.endswith('.rct') and re.match(r'(c_\d+|maho_tui|v_|kyalme|catch|route_)',n)];print(names)
 sh=Image.new('RGB',(1200,175*((len(names)+5)//6)),(33,33,33));d=ImageDraw.Draw(sh)
 for i,n in enumerate(sorted(names)):
  ar=S.decode(n);im=Image.fromarray(ar);im.save(R/(n+'.png'));im.thumbnail((200,150));x=i%6*200;y=i//6*175;sh.paste(im,(x,y));d.text((x+2,y+153),n,fill='white')
 sh.save(R/'special-art-contact.png')