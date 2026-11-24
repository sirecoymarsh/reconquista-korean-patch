from pathlib import Path
import json,subprocess
from PIL import Image,ImageDraw
U=Path.cwd();R=U/'research/op-all-japanese-v3';D=R/'dense-frames';D.mkdir(exist_ok=True)
ranges=[(36.9,39.5),(42.9,45.5),(48.7,51.1),(53.4,58.9),(62.1,66.5),(66.4,76.1),(77.5,81.9),(86.4,90.8)]
indices={n for lo,hi in ranges for n in range(round(lo*30),round(hi*30)+1)}
FF='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';src=U.parent/'research/disc/movie/Recon_OP800_H.mpg'
p=subprocess.Popen([FF,'-v','error','-threads','2','-i',str(src),'-map','0:v:0','-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
n=0
while True:
 b=p.stdout.read(800*600*3)
 if not b:break
 assert len(b)==800*600*3
 if n in indices:
  f=D/f'{n:04d}.png'
  if not f.exists():Image.frombytes('RGB',(800,600),b).save(f)
 n+=1
assert p.wait()==0 and n==3037
for key,lo,hi in [('mahoko',37.0,37.6),('shiina',43.0,43.6),('masaki',48.8,49.4),('momiji',53.5,54.1),('kureha',62.2,62.8),('question',65.1,66.5)]:
 ns=list(range(round(lo*30),round(hi*30)+1,2));im=Image.new('RGB',(1600,215*((len(ns)+3)//4)),(26,26,26));d=ImageDraw.Draw(im)
 for j,k in enumerate(ns):
  q=Image.open(D/f'{k:04d}.png').crop((0,72,800,526)).resize((400,195));x=j%4*400;y=j//4*215;im.paste(q,(x,y));d.text((x+4,y+197),f'{k} / {k/30:.3f}',fill='white')
 im.save(R/f'{key}-onset.png')
print(json.dumps({'dense_frames':len(indices),'ranges':ranges}))