from pathlib import Path
import subprocess,json,wave,numpy as np
from PIL import Image,ImageDraw
U=Path.cwd();FF=Path(r'F:\DOWN\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe');E=U/'evidence/op-ed-source';movie=U.parent/'research/disc/movie/Recon_OP800_H.mpg';times=[3,7,9,12,14,17,31,37,40,42,43,44,45,46,47,48,49,51,52,53,54,56,57,58,59,61,62,63,64,66,68,71,73,74,76,77,78,81,83,87,89,92,94,96,98]
for t in times:
 p=E/f'op-{t:03d}.png'
 if not p.exists():subprocess.run([str(FF),'-hide_banner','-loglevel','error','-ss',str(t),'-i',str(movie),'-frames:v','1',str(p)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
for part,start in enumerate(range(0,len(times),15)):
 tt=times[start:start+15];im=Image.new('RGB',(1200,320*((len(tt)+2)//3)),(35,35,38));d=ImageDraw.Draw(im)
 for i,t in enumerate(tt):tile=Image.open(E/f'op-{t:03d}.png').resize((400,300));x=i%3*400;y=i//3*320;im.paste(tile,(x,y));d.text((x+5,y+302),f'{t}s',fill='white')
 im.save(E/f'op-detail-contact-{part+1}.png')
for name in ['op-movie-large','ed-isolated-large']:
 r=json.loads((U/'transcription_work'/f'{name}.json').read_text(encoding='utf-8'));print(name)
 for s in r['segments']:print(f'{s["id"]}: '+' | '.join(f'{w["word"]}({w["start"]:.2f}-{w["end"]:.2f})' for w in s['words']))
