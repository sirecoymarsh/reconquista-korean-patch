from pathlib import Path
import json,subprocess
from PIL import Image,ImageDraw
U=Path.cwd();O=U/'candidates/opening-video-ko-v4';E=O/'evidence';D=O/'build-source';ff='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS

def run(a):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags);assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout

def md5(path):
 s=run([ff,'-v','error','-threads','3','-i',str(path),'-map','0:v:0','-an','-f','framemd5','-']).decode();return [l.rsplit(',',1)[1].strip() for l in s.splitlines() if l and not l.startswith('#')]
a=md5(D/'native-before-visual-repair.mpg');b=md5(O/'payloads/movie/Recon_OP800_H.mpg');assert len(a)==len(b)==3037;changed=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
j=json.loads((E/'encoded-review.json').read_text(encoding='utf-8'));refresh=[r for r in j['frames'] if r['frame'] in changed];extra=[849,850,907,908,912,918,930,951,953,954,957,969,975,983,990,1002,1012,1013,1020,1029,1030];ns=sorted(set(extra+[r['frame'] for r in refresh]));dest=O/'preview/repair-native';dest.mkdir(exist_ok=True);sel='+'.join(f'eq(n,{n})' for n in ns);run([ff,'-v','error','-xerror','-y','-threads','3','-i',str(O/'payloads/movie/Recon_OP800_H.mpg'),'-vf',"select='"+sel+"'",'-frames:v',str(len(ns)),'-fps_mode','vfr',str(dest/'extract-%03d.png')])
rows=[]
for i,n in enumerate(ns,1):
 p=dest/f'{n:04d}.png';(dest/f'extract-{i:03d}.png').replace(p);rows.append(dict(frame=n,path=str(p)))
 for r in refresh:
  if r['frame']==n:Image.open(p).save(r['path'])
for start in range(0,len(ns),12):
 sub=rows[start:start+12];im=Image.new('RGB',(1600,324*((len(sub)+3)//4)),(23,23,23));dd=ImageDraw.Draw(im)
 for k,r in enumerate(sub):x=k%4*400;y=k//4*324;im.paste(Image.open(r['path']).resize((400,300)),(x,y+24));dd.text((x+4,y+4),f"n{r['frame']}",fill='white')
 im.save(dest/f'contact-{start//12+1}.jpg',quality=94)
# Refresh only contact-sheet thumbnails that actually changed.
for r in refresh:
 i=r['index'];p=O/'preview/encoded'/f'contact-{i//12+1}.jpg';im=Image.open(p).convert('RGB');k=i%12;im.paste(Image.open(r['path']).resize((400,300)),(k%4*400,k//4*324+24));im.save(p,quality=94)
j.update(status='changed_samples_review_pending',unchanged_sample_decoded_hashes_reused=len(j['frames'])-len(refresh),refreshed_frames=[r['frame'] for r in refresh]);(E/'encoded-review.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');report=dict(status='review_pending',decoded_changed_frames=changed,decoded_unchanged_frames=3037-len(changed),unchanged_existing_samples=len(j['frames'])-len(refresh),refreshed_existing_samples=[r['frame'] for r in refresh],frames=rows);(E/'native-repair-encoded-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(decoded_changed_count=len(changed),changed_range=[min(changed),max(changed)],refreshed=report['refreshed_existing_samples'],extra_samples=len(ns))))
