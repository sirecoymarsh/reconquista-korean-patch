from pathlib import Path
import json,sys,subprocess,re,hashlib,collections
import numpy as np
from PIL import Image,ImageDraw
U=Path.cwd();R=U/'research/op-all-japanese-v3';R.mkdir(parents=True,exist_ok=True);F=R/'source-frames';F.mkdir(exist_ok=True)
p=U/'progress.json';j=json.loads(p.read_text(encoding='utf-8'));j['active_user_revision']['all_op_japanese_v3']={'state':'active: full image-baked Japanese replacement','request':'오프닝 일본어들 모조리 다 한국어화','candidate':'candidates/opening-video-ko-v3','frozen_v2_unchanged':True,'scope':'OP only; no game or GUI execution; coordinator integration remains separate','next':'inventory all temporal text surfaces; source-derived restoration; Korean name mapping'};p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (U/'HANDOFF.md').open('a',encoding='utf-8') as f:f.write('\n\n## 2026-10-23 사용자 추가 요청 — OP v3\n\n오프닝에 남은 일본어 전체 교체 작업을 새 v3에서 시작했습니다. v2 고정본은 유지합니다. 인물 소개, 성우, 주제가, 영상·디렉터 표기 및 상단 자막의 일본어 이름을 대상으로 하며, 새 후보는 아직 통합 불가입니다. 게임·GUI 실행 없이 파일로 검증합니다.\n')
# A single sequential decoder, no playback or foreground window.
ranges=[(36,38.8),(42.3,45),(48.2,51),(53.2,59.5),(62.5,65.3),(66.5,76.2),(77.4,82.5),(86.3,91)]
indices=set(range(0,3037,15))
for lo,hi in ranges:indices.update(range(round(lo*30),round(hi*30)+1,3))
FF='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';src=U.parent/'research/disc/movie/Recon_OP800_H.mpg'
proc=subprocess.Popen([FF,'-v','error','-threads','2','-i',str(src),'-map','0:v:0','-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
rows=[];n=0
while True:
 b=proc.stdout.read(800*600*3)
 if not b:break
 assert len(b)==800*600*3
 if n in indices:
  q=F/f'{n:04d}.png'
  if not q.exists():Image.frombytes('RGB',(800,600),b).save(q)
  rows.append({'frame':n,'time':n/30,'path':str(q)})
 n+=1
assert proc.wait()==0 and n==3037
(R/'frames.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
for k,(lo,hi) in enumerate(ranges):
 a=[r for r in rows if lo<=r['time']<=hi and r['frame']%6==0];im=Image.new('RGB',(1600,212*((len(a)+4)//5)),(25,25,25));d=ImageDraw.Draw(im)
 for i,r in enumerate(a):
  x=i%5*320;y=i//5*212;p=Image.open(r['path']).crop((0,72,800,526)).resize((320,182));im.paste(p,(x,y));d.text((x+3,y+185),f'{r["frame"]} / {r["time"]:.2f}',fill='white')
 im.save(R/f'text-timing-{k+1}.png')
# Thumbnail only one representative per event CG family; source imagery, not generated art.
sys.path.insert(0,str(U.parent/'tools'));from inspect_majiro import Arc
sys.path.insert(0,str(U/'tools'));from raster_codec import raw_image
D=R/'art-thumbnails';D.mkdir(exist_ok=True);arts=[];seen=set()
for fn in ['data.arc','data1.arc','data2.arc']:
 arc=Arc(U.parent/'research/disc'/fn)
 with arc.path.open('rb') as fh:
  for e in sorted(arc.entries,key=lambda x:x['name']):
   name=e['name'];mt=re.match(r'(ev_?\d+|last\d+|img\d+)',name)
   if not mt or not name.endswith('.rct') or mt[1] in seen:continue
   fh.seek(e['offset']);b=fh.read(e['size'])
   if b[4:8]!=b'TC00':continue
   arr,_,_=raw_image(b);p=D/(name+'.png');im=Image.fromarray(arr);im.thumbnail((160,120));im.save(p);seen.add(mt[1]);arts.append({'name':name,'archive':fn,'path':str(p),'size':[arr.shape[1],arr.shape[0]]})
for k in range((len(arts)+79)//80):
 im=Image.new('RGB',(1600,8*138),(25,25,25));d=ImageDraw.Draw(im)
 for i,r in enumerate(arts[k*80:(k+1)*80]):
  x=i%10*160;y=i//10*138;im.paste(Image.open(r['path']),(x,y));d.text((x+2,y+121),r['name'],fill='white')
 im.save(R/f'art-contact-{k+1}.png')
(R/'art-index.json').write_text(json.dumps(arts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_frames':len(rows),'source_art_families':len(arts),'directory':str(R)}),flush=True)