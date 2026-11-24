from pathlib import Path
import json,numpy as np
from PIL import Image
import build_opening_video_v5 as b
import op_v5_logo_lowmem as low
results=[]
for n in [660,897,2920]:
 a=np.array(Image.open(b.QC/f'{n:04d}.png').convert('RGB'));i=b.idx[n];star=np.unpackbits(b.cache['star'][i]).reshape(600,800).astype(bool)
 expected=b.logo.draw(a,n,b.cache['colors'][i],float(b.cache['opacity'][i]),star,s=1)
 got=low.draw(a,n,b.cache['colors'][i],float(b.cache['opacity'][i]),star,s=1)
 d=np.abs(expected.astype(np.int16)-got.astype(np.int16));r=dict(frame=n,max_rgb_error=int(d.max()),changed_channels=int(np.count_nonzero(d)));assert r['max_rgb_error']<=1,r;results.append(r)
b.save('4k-lowmem-equivalence.json',dict(status='pass',scope='Three representative native-resolution static/motion frames; float32 arithmetic differs at most 1 code value. New 4K geometry/encoded output requires visual review.',samples=results))
p=b.U/'tools/build_opening_video_v5.py';s=p.read_text(encoding='utf-8');s=s.replace('def native():\n ranges=',"def native():\n assert not (O/'game-manifest.json').exists(), 'Native output frozen; use a new version'\n ranges=");p.write_text(s,encoding='utf-8')
print(json.dumps(results))
