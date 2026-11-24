"""Lossless literal RCT/RC8 export; original metadata and palette preserved."""
import struct,numpy as np
from PIL import Image
from decode_ui import unpack
def raw_image(blob):
 w,h=struct.unpack_from('<II',blob,8);sig=blob[4:8]
 if sig in (b'TC00',b'TC01'):
  pos=20 if sig==b'TC00' else 22+struct.unpack_from('<H',blob,20)[0];channels=3
  data,end=unpack(blob,pos,w,h,channels);im=Image.frombytes('RGB',(w,h),data,'raw','BGR')
 elif sig==b'8_00':
  pos=788;channels=1;data,end=unpack(blob,pos,w,h,1);im=Image.frombytes('P',(w,h),data);im.putpalette(blob[20:788])
 else:raise ValueError(sig)
 assert end==len(blob)
 return np.asarray(im).copy(),blob[:pos],channels
def encode_array(array,prefix,channels):
 h,w=array.shape[:2];assert struct.unpack_from('<II',prefix,8)==(w,h)
 data=Image.fromarray(array,'RGB').tobytes('raw','BGR') if channels==3 else array.astype('uint8').tobytes()
 out=bytearray(data[:channels]);i=channels
 while i<len(data):
  n=min((len(data)-i)//channels,65663)
  if n<128:out.append(n-1)
  else:out.append(127);out.extend(struct.pack('<H',n-128))
  out.extend(data[i:i+n*channels]);i+=n*channels
 header=bytearray(prefix);struct.pack_into('<I',header,16,len(out));return bytes(header)+out
