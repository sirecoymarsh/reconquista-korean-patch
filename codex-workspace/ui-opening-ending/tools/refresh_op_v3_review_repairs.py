from pathlib import Path
import sys,json,subprocess,shutil
from PIL import Image,ImageDraw
U=Path.cwd();O=U/'candidates/opening-video-ko-v3';E=O/'evidence';four='--4k' in sys.argv;kind='4k' if four else 'native';report=E/('4k-encoded-review.json' if four else 'encoded-review.json');j=json.loads(report.read_text(encoding='utf-8'));video=O/('viewing/Reconquista_OP_KO_4K.mp4' if four else 'payloads/movie/Recon_OP800_H.mpg');d=O/'preview'/('encoded4k' if four else 'encoded');tmp=O/'preview'/('repair-encoded-'+kind);tmp.mkdir(exist_ok=True)
updated=[r for r in j['frames'] if 1943<=r['frame']<=2184];extra=[1942,1943,1944,1989,1993,2046,2047,2146,2149,2155,2160,2161,2163,2184,2185,2186];ns=sorted(set([r['frame'] for r in updated]+extra));expr='+'.join('eq(n,%d)'%n for n in ns);ff='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';args=[ff,'-v','error','-xerror','-threads','4','-i',str(video),'-vf',f'select={repr(expr)}','-fps_mode','vfr','-frames:v',str(len(ns)),'-start_number','0',str(tmp/'%03d.png')];p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS);assert p.returncode==0 and not p.stderr,p.stderr
for r in updated:shutil.copy2(tmp/f'{ns.index(r["frame"]):03d}.png',r['path'])
ph=225 if four else 300
for start in range(0,len(j['frames']),12):
 sub=j['frames'][start:start+12]
 if not any(r in updated for r in sub):continue
 im=Image.new('RGB',(1600,(ph+24)*((len(sub)+3)//4)),(23,23,23));draw=ImageDraw.Draw(im)
 for i,r in enumerate(sub):
  x=i%4*400;y=i//4*(ph+24);im.paste(Image.open(r['path']).resize((400,ph)),(x,y+24));draw.text((x+4,y+4),f"{r['index']:02} | n{r['frame']} | {r['time']:.2f}s",fill='white')
 im.save(d/f'contact-{start//12+1}.jpg',quality=94)
for start in range(0,len(ns),12):
 sub=ns[start:start+12];im=Image.new('RGB',(1600,(ph+24)*((len(sub)+3)//4)),(23,23,23));draw=ImageDraw.Draw(im)
 for i,n in enumerate(sub):
  x=i%4*400;y=i//4*(ph+24);im.paste(Image.open(tmp/f'{ns.index(n):03d}.png').resize((400,ph)),(x,y+24));draw.text((x+4,y+4),f'n{n} | {n/30:.2f}s',fill='white')
 im.save(tmp/f'contact-{start//12+1}.jpg',quality=94)
j['refreshed_after_review_repair']=[r['frame'] for r in updated];j['unchanged_prior_review_reused']=len(j['frames'])-len(updated);report.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');q=dict(status='visual_review_pending',video=str(video),frames=[dict(frame=n,path=str(tmp/f'{i:03d}.png')) for i,n in enumerate(ns)],refreshed_main_gallery_frames=len(updated),unchanged_main_gallery_samples_reused=len(j['frames'])-len(updated));(E/f'{kind}-repair-encoded-review.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(kind=kind,samples=len(ns),updated=len(updated))),flush=True)
