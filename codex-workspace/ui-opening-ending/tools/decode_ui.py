"""Majiro TC00/TC01 and 8_00 extraction, based on GARbro MIT format reference.
Source references and original copyright/license are preserved in source/GARbro-Image*.cs.
This tool decodes original pixels; it does not translate or alter game assets.
"""
from pathlib import Path
import struct,json,hashlib
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT.parent/'research/extracted/fastdata'
SH24=[-16,-32,-48,-64,-80,-96,49,33,17,1,-15,-31,-47,50,34,18,2,-14,-30,-46,51,35,19,3,-13,-29,-45,36,20,4,-12,-28]
SH8=[-16,-32,-48,-64,49,33,17,1,-15,-31,-47,34,18,2,-14,-30]
def sha(b):return hashlib.sha256(b).hexdigest()
def unpack(b,p,w,h,channels):
 out=bytearray();total=w*h*channels;literal=1
 while len(out)<total:
  size=literal*channels;assert len(out)+size<=total and p+size<=len(b)
  out.extend(b[p:p+size]);p+=size
  while len(out)<total:
   v=b[p];p+=1
   if v<128:
    literal=v+1
    if v==127:literal+=struct.unpack_from('<H',b,p)[0];p+=2
    break
   bits=2 if channels==3 else 3;mask=(1<<bits)-1;n=v&mask
   if n==mask:n+=struct.unpack_from('<H',b,p)[0];p+=2
   count=(n+(1 if channels==3 else 3))*channels
   shift=(SH24 if channels==3 else SH8)[(v>>bits)&(31 if channels==3 else 15)]
   delta=((shift>>4)-(shift&15)*w)*channels
   assert delta<0 and len(out)+delta>=0 and len(out)+count<=total
   span=out[len(out)+delta:]
   out.extend((span*((count+len(span)-1)//len(span)))[:count])
 return bytes(out),p
cache={}
def decode(name,stack=()):
 if name in cache:return cache[name]
 assert name not in stack
 p=SRC/name;b=p.read_bytes();assert b[:4]==bytes.fromhex('985a929a')
 sig=b[4:8];w,h=struct.unpack_from('<II',b,8);base=None
 if sig in [b'TC00',b'TC01']:
  pos=20
  if sig==b'TC01':
   n=struct.unpack_from('<H',b,20)[0];pos=22+n
   base=b[22:pos].rstrip(b'\0').decode('cp932')
  raw,end=unpack(b,pos,w,h,3);im=Image.frombytes('RGB',(w,h),raw,'raw','BGR')
  if base:
   baseim=decode(base if base.endswith('.rct') else base+'.rct',stack+(name,))[0]
   assert baseim.size==im.size
   import numpy as np
   a=np.asarray(im).copy();z=np.all(a==[255,0,0],axis=2);a[z]=np.asarray(baseim)[z];im=Image.fromarray(a,'RGB')
 elif sig==b'8_00':
  raw,end=unpack(b,788,w,h,1);im=Image.frombytes('P',(w,h),raw);im.putpalette(b[20:788])
 else:raise ValueError(sig)
 meta={'file':name,'sha256':sha(b),'signature':sig.decode(),'width':w,'height':h,'base':base,'decoded_bytes':len(raw),'end':end,'file_bytes':len(b),'trailing_bytes':len(b)-end,'decoded_sha256':sha(raw)}
 assert end==len(b),(name,end,len(b))
 cache[name]=(im,meta);return im,meta
if __name__=='__main__':
 out=ROOT/'source/decoded';out.mkdir(exist_ok=True);rows=[]
 for p in sorted(SRC.glob('*')):
  if p.suffix not in ['.rct','.rc8']:continue
  im,meta=decode(p.name);im.save(out/(p.name+'.png'))
  if p.suffix=='.rct':
   maskname=p.stem+'_.rc8'
   if (SRC/maskname).exists():
    import numpy as np
    mask=np.asarray(decode(maskname)[0].convert('RGB')).astype('uint16');alpha=255-(mask.sum(2)//3).astype('uint8')
    im=im.convert('RGBA');im.putalpha(Image.fromarray(alpha,'L'));im.save(out/(p.stem+'.composite.png'))
    meta['mask']=maskname;meta['alpha_range']=[int(alpha.min()),int(alpha.max())]
  rows.append(meta)
 (ROOT/'reports/raster-decode.json').write_text(json.dumps({'format_reference':'GARbro ImageRCT.cs/ImageRC8.cs, MIT','files':rows,'count':len(rows)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 font=ImageFont.truetype(str(ROOT.parent/'research/fonts/NotoSansCJKkr-Regular.otf'),15)
 names=[p.name for p in sorted(SRC.glob('*.rct'))]
 sheetdir=ROOT/'evidence/contact-sheets';sheetdir.mkdir(exist_ok=True)
 for start in range(0,len(names),12):
  sheet=Image.new('RGB',(1200,4*255),(45,45,49));d=ImageDraw.Draw(sheet)
  for j,n in enumerate(names[start:start+12]):
   im=decode(n)[0].copy();im.thumbnail((396,226));x=(j%3)*400;y=(j//3)*255
   sheet.paste(im,(x+(400-im.width)//2,y));d.text((x+4,y+230),n,font=font,fill='white')
  sheet.save(sheetdir/f'original-{start//12+1:02d}.jpg',quality=92)
 print(json.dumps({'decoded':len(rows),'rct':len(names),'base_overlays':sum(bool(r['base']) for r in rows),'mask_pairs':sum('mask' in r for r in rows),'contact_sheets':(len(names)+11)//12},ensure_ascii=False))
