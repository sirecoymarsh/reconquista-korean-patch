from pathlib import Path
import sys,json,subprocess
from PIL import Image,ImageDraw
U=Path.cwd();O=U/'candidates/opening-video-ko-v4';four='--4k' in sys.argv;dest=O/'preview'/('encoded4k' if four else 'encoded');dest.mkdir(exist_ok=True);video=O/('viewing/Reconquista_OP_KO_4K.mp4' if four else 'payloads/movie/Recon_OP800_H.mpg');ff='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS

def tm(s):
 h,m,x=s.split(':');return float(h)*3600+float(m)*60+float(x)
cues=[]
for l in (O/'subtitles/opening-ko.ass').read_text(encoding='utf-8').splitlines():
 if l.startswith('Dialogue:'):
  r=l.split(',',9);cues.append(dict(id=r[4],start=tm(r[1]),end=tm(r[2]),frame=round((tm(r[1])+tm(r[2]))*15)))
scenes=[120,188,240,285,300,345,369,390,420,465,930,975,990,1020,1080,1090,1185,1230,1260,1281,1290,1305,1490,1680,2030,2142,2250,2370,2630];logos=[];trans=[]
ns=sorted(set([c['frame'] for c in cues]+scenes+logos+([] if four else trans)));expr='+'.join(f'eq(n,{n})' for n in ns);args=[ff,'-v','error','-xerror','-threads','4','-i',str(video),'-vf',f'select={repr(expr)}','-fps_mode','vfr','-start_number','0',str(dest/'%03d.png')];p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags);assert p.returncode==0,p.stderr.decode();paths=[dest/f'{i:03d}.png' for i in range(len(ns))];assert all(p.exists() for p in paths)
rows=[]
for i,(n,p) in enumerate(zip(ns,paths)):rows.append(dict(index=i,frame=n,time=n/30,path=str(p),active_caption_ids=[c['id'] for c in cues if c['start']<=n/30<c['end']]))
for start in range(0,len(ns),12):
 sub=rows[start:start+12];ph=225 if four else 300;im=Image.new('RGB',(1600,(ph+24)*((len(sub)+3)//4)),(23,23,23));d=ImageDraw.Draw(im)
 for j,r in enumerate(sub):
  x=j%4*400;y=j//4*(ph+24);a=Image.open(r['path']).convert('RGB');assert a.size==((3840,2160) if four else (800,600));im.paste(a.resize((400,ph)),(x,y+24));d.text((x+4,y+4),f"{r['index']:02} | n{r['frame']} | {r['time']:.2f}s",fill='white')
 im.save(dest/f'contact-{start//12+1}.jpg',quality=94)
report=dict(status='visual_review_pending',video=str(video),frames=rows,covered_caption_ids=sorted({id for r in rows for id in r['active_caption_ids']}),expected_caption_cues=36,in_picture_scene_frames=scenes,logo_frames=logos);assert len(report['covered_caption_ids'])==36;(O/'evidence'/('4k-encoded-review.json' if four else 'encoded-review.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(samples=len(ns),cues=len(report['covered_caption_ids']),output=str(dest)),ensure_ascii=False))