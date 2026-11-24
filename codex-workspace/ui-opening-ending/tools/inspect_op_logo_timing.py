from pathlib import Path
import sys,json,re,subprocess,struct
from PIL import Image,ImageDraw
import numpy as np
U=Path.cwd();O=U/'research/op-logo';O.mkdir(exist_ok=True);F=O/'frames';F.mkdir(exist_ok=True)
FF=Path('F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe');movie=U.parent/'research/disc/movie/Recon_OP800_H.mpg'
if not (O/'frames.json').exists():
 p=subprocess.run([str(FF),'-hide_banner','-loglevel','info','-i',str(movie),'-vf',r'fps=5,select=between(t\,16\,30)+between(t\,90\,100),showinfo','-fps_mode','vfr',str(F/'%03d.png')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 times=[float(x) for x in re.findall(r'pts_time:([0-9.]+)',p.stderr.decode('utf-8','replace'))];rows=[{'frame':i+1,'time':t,'path':str(F/f'{i+1:03d}.png')} for i,t in enumerate(times)];(O/'frames.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
else:rows=json.loads((O/'frames.json').read_text())
for group,(a,b) in enumerate([(16,22),(22.2,30),(90,94),(94.2,100)],1):
 rs=[r for r in rows if a<=r['time']<=b];sheet=Image.new('RGB',(1280,180*((len(rs)+4)//5)),(28,28,31));d=ImageDraw.Draw(sheet)
 for i,r in enumerate(rs):
  im=Image.open(r['path']);im=im.crop((0,72,800,526)).resize((256,145));x=i%5*256;y=i//5*180;sheet.paste(im,(x,y+20));d.text((x+5,y+3),str(r['time']),fill='white')
 sheet.save(O/f'timing-{group}.png')
print('OP timing samples:',len(rows))
