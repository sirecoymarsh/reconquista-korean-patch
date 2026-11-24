from pathlib import Path
import sys,json,hashlib,subprocess
from PIL import Image,ImageDraw
U=Path.cwd();sys.path.insert(0,str(U.parent/'tools'))
from inspect_majiro import Arc
FF=Path(r'F:\DOWN\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe');FP=FF.with_name('ffprobe.exe')
S=U/'source/op-ed';E=U/'evidence/op-ed-source';R=U/'research/op-ed'
for p in (S,E,R,U/'transcription_work'):p.mkdir(parents=True,exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def run(args):return subprocess.run([str(x) for x in args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
def probe(p):return json.loads(run([FP,'-v','error','-show_format','-show_streams','-of','json',p]).stdout)
a=Arc(U.parent/'research/disc/stream.arc');wanted={'recon_op_full.ogg','recon_op_inst.ogg','recon_op_1c.ogg','recon_ed.ogg','recon_ed_inst.ogg'};rows=[]
with a.path.open('rb') as f:
 for e in a.entries:
  if e['name'] not in wanted:continue
  f.seek(e['offset']);b=f.read(e['size']);p=S/e['name']
  if p.exists():assert p.read_bytes()==b
  else:p.write_bytes(b)
  metadata=probe(p);rows.append({'id':'stream::'+e['name'],'source_archive':str(a.path),'offset':e['offset'],'bytes':len(b),'sha256':sha(b),'metadata':metadata})
  w=U/'transcription_work'/(p.stem+'-mono16k.wav')
  if not w.exists():run([FF,'-hide_banner','-loglevel','error','-i',p,'-ac','1','-ar','16000','-c:a','pcm_s16le',w])
movie=U.parent/'research/disc/movie/Recon_OP800_H.mpg';meta=probe(movie)
rows.append({'id':'movie::Recon_OP800_H.mpg','path':str(movie),'bytes':movie.stat().st_size,'sha256':sha(movie.read_bytes()),'metadata':meta})
w=U/'transcription_work/Recon_OP800_H-mono16k.wav'
if not w.exists():run([FF,'-hide_banner','-loglevel','error','-i',movie,'-map','0:a:0','-ac','1','-ar','16000','-c:a','pcm_s16le',w])
frames=[]
for t in range(0,101,5):
 p=E/f'op-{t:03d}.png'
 if not p.exists():run([FF,'-hide_banner','-loglevel','error','-ss',str(t),'-i',movie,'-frames:v','1',p])
 frames.append((f'{t}s',p))
def sheet(items,out):
 im=Image.new('RGB',(1200,320*((len(items)+2)//3)),(35,35,38));d=ImageDraw.Draw(im)
 for i,(label,p) in enumerate(items):
  tile=Image.open(p).convert('RGB');tile.thumbnail((400,300));x=(i%3)*400;y=(i//3)*320
  im.paste(tile,(x,y));d.text((x+4,y+302),label,fill='white')
 im.save(out)
sheet(frames,E/'op-contact.png')
bs=sorted((U/'source/decoded').glob('staffrollb_*.rct.png'));sheet([(p.name,p) for p in bs],E/'staffrollb-contact.png')
for p in [U/'source/decoded/staffrolla.rct.png',U/'source/decoded/staffrolla_.rc8.png']:
 im=Image.open(p);rows.append({'id':'fastdata::'+p.name[:-4],'decoded_mode':im.mode,'decoded_size':list(im.size),'extrema':im.getextrema()})
report={'translator_model':'Codex internal','stage':'source_inventory_only_no_semantic_draft','sources':rows,'op_frames':'evidence/op-ed-source/op-contact.png','ed_b_frames':'evidence/op-ed-source/staffrollb-contact.png','runtime':'user_final_review_pending'}
(R/'source-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'audio_sources':[{'id':r['id'],'duration':r['metadata']['format'].get('duration'),'tags':r['metadata']['format'].get('tags',{})} for r in rows if r['id'].startswith('stream::')],'movie_duration':meta['format']['duration'],'op_frames':len(frames),'staffrollb_frames':len(bs),'report':'research/op-ed/source-inventory.json'},ensure_ascii=False))
