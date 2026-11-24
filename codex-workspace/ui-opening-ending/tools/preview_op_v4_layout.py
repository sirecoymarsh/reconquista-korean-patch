from pathlib import Path
import subprocess,sys,json,numpy as np
from PIL import Image
from build_opening_video_v4 import O,V,E,D,ff,base,flags,run,clean,logo_paint
from op_v4_typeset import paint
ns=[120,240,285,300,369,390,420,930,975,1020,1080,1230,1281,1290,1305,1490,1680,2030,2142,2250,2370,2630]
bd=D/'layout-base';bd.mkdir(exist_ok=True)
missing=[n for n in ns if not (bd/f'{n:04d}.png').exists()]
if missing:
 sel='+'.join(f'eq(n,{n})' for n in missing)
 run(base+['-threads','3','-i',str(V/'build-source/opening-clean-background.ffv1.mkv'),'-vf',"select='"+sel+"'",'-fps_mode','vfr',str(bd/'extract-%03d.png')])
 for i,n in enumerate(missing,1):(bd/f'extract-{i:03d}.png').rename(bd/f'{n:04d}.png')
for kind in ['native','4k']:(O/'preview'/('layout-'+kind)).mkdir(exist_ok=True)
for n in ns:
 a=clean(np.array(Image.open(bd/f'{n:04d}.png').convert('RGB')),n)
 for kind in ['native','4k']:
  if kind=='4k':
   vf='crop=800:450:0:75,scale=3840:2160:flags=lanczos,unsharp=5:5:0.2:3:3:0,format=rgb24'
   bb=subprocess.run(base+['-f','rawvideo','-pix_fmt','rgb24','-s','800x600','-i','pipe:0','-vf',vf,'-frames:v','1','-f','rawvideo','pipe:1'],input=a.tobytes(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,creationflags=flags).stdout
   z=paint(logo_paint(np.frombuffer(bb,np.uint8).reshape(2160,3840,3),n,4.8),n,s=4.8,crop_4k=True);size='3840x2160';ass='opening-ko-4k.ass'
  else:z=paint(logo_paint(a,n,1),n);size='800x600';ass='opening-ko.ass'
  out=O/'preview'/('layout-'+kind)/f'{n:04d}.png';args=base+['-f','rawvideo','-pix_fmt','rgb24','-s',size,'-r','30','-i','pipe:0','-vf',f'setpts=PTS+{n}/30/TB,ass=subtitles/{ass}:fontsdir=fonts','-frames:v','1','-fps_mode','vfr',str(out)]
  p=subprocess.run(args,cwd=O,input=z.tobytes(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags);assert p.returncode==0,p.stderr
 print('layout',n,flush=True)
