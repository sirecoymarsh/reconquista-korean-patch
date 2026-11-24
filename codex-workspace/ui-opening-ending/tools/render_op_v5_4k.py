"""Resumable, low-memory 4K revision; frozen game MPEG is never written."""
from pathlib import Path
import json,subprocess,time,gc,hashlib,sys,numpy as np
import build_opening_video_v5 as b
import op_v5_logo_lowmem as low
D=b.D;E=b.E;O=b.O;K=D/'4k-chunks';K.mkdir(exist_ok=True)
stop=Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json')

def checkpoint_allowed():
 assert not stop.exists(),'Included usage stop marker exists; checkpointed render stopped'

def frame_count(p):
 r=json.loads(b.run([b.probe,'-v','error','-select_streams','v:0','-count_packets','-show_entries','stream=nb_read_packets,width,height,codec_name','-of','json',str(p)]))['streams'][0]
 assert r['width']==3840 and r['height']==2160 and r['codec_name']=='h264',r
 return int(r['nb_read_packets'])

def lp(a,n):
 if n not in b.idx:return a
 i=b.idx[n];star=np.unpackbits(b.cache['star'][i]).reshape(600,800).astype(bool)
 if 908<=n<954:star[:]=False
 return low.draw(a,n,b.cache['colors'][i],float(b.cache['opacity'][i]),star,s=4.8)

def main():
 checkpoint_allowed();ranges=b.plan()['ranges'];config=json.loads((b.V/'evidence/build-4k.json').read_text(encoding='utf-8'));oldargs=config['encoder'];params=oldargs[oldargs.index('-c:v'):oldargs.index('-c:a')]
 keyfiles=[Path(__file__).with_name('op_v5_logo_lowmem.py'),Path(__file__).with_name('op_v5_quotes.py'),Path(__file__).with_name('op_v4_typeset.py'),O/'subtitles/opening-ko-4k.ass',E/'quote-restoration.json']
 key=hashlib.sha256((''.join(b.digest(p) for p in keyfiles)+json.dumps(params)).encode()).hexdigest()
 parts=[];stats=[];copies=[];cursor=0;completed=0;started=time.monotonic()
 def cp(lo,hi):
  checkpoint_allowed();out=D/f'4k-copy-{lo}-{hi}.mp4';meta=out.with_suffix('.json')
  if not meta.exists():
   if not out.exists() or frame_count(out)!=hi-lo:
    b.run(b.base+['-ss',f'{lo/30:.9f}','-i',str(b.prior),'-map','0:v:0','-frames:v',str(hi-lo),'-c','copy',str(out)])
   assert frame_count(out)==hi-lo
   meta.write_text(json.dumps(dict(path=str(out),frames=hi-lo,range=[lo,hi],sha256=b.digest(out),source='frozen v4 compressed video packets'))+'\n',encoding='utf-8')
  info=json.loads(meta.read_text());assert info['frames']==hi-lo and b.digest(out)==info['sha256']
  parts.append((out,hi-lo));copies.append(info)
 for j,(lo,hi) in enumerate(ranges):
  if lo>cursor:cp(cursor,lo)
  filters='crop=800:450:0:75,hqdn3d=0.7:0.5:1.4:1.0,scale=3840:2160:flags=lanczos,unsharp=5:5:0.2:3:3:0,format=rgb24'
  da=b.base+['-threads','2','-filter_threads','2','-i',str(D/f'4k-clean-{j}.ffv1.mkv'),'-vf',filters,'-pix_fmt','rgb24','-fps_mode','passthrough','-f','rawvideo','pipe:1']
  # One decoder for each complete span preserves temporal denoising continuity.
  with (E/f'4k-lowmem-span-{j}.log').open('ab') as log:
   dec=subprocess.Popen(da,stdout=subprocess.PIPE,stderr=log,creationflags=b.flags);enc=None
   try:
    for cl in range(lo,hi,60):
     checkpoint_allowed();ch=min(cl+60,hi);count=ch-cl;out=K/f'{cl:04d}-{ch:04d}.mp4';meta=out.with_suffix('.json');reuse=False
     if meta.exists() and out.exists():
      m=json.loads(meta.read_text());reuse=m.get('render_key')==key and m.get('frames')==count and m.get('sha256')==b.digest(out)
     if not reuse:
      tmp=out.with_suffix('.partial.mp4');ea=b.base+['-filter_threads','2','-f','rawvideo','-pix_fmt','rgb24','-s','3840x2160','-r','30','-i','pipe:0','-an','-vf',f'setpts=PTS+{cl}/30/TB,ass=subtitles/opening-ko-4k.ass:fontsdir=fonts,setpts=PTS-STARTPTS,scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p']+params+['-movflags','+faststart',str(tmp)]
      enc=subprocess.Popen(ea,cwd=O,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=b.flags)
     for n in range(cl,ch):
      bb=dec.stdout.read(3840*2160*3);assert len(bb)==3840*2160*3,(n,len(bb))
      if not reuse:
       a=np.frombuffer(bb,np.uint8).reshape(2160,3840,3);a=b.paint(lp(a,n),n,s=4.8,crop_4k=True);enc.stdin.write(a.tobytes());del a
      del bb
     if not reuse:
      enc.stdin.close();assert enc.wait()==0;enc=None;assert frame_count(tmp)==count;tmp.replace(out)
      m=dict(path=str(out),range=[cl,ch-1],frames=count,sha256=b.digest(out),bytes=out.stat().st_size,render_key=key,encoder=ea);meta.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
     parts.append((out,count));stats.append(m);completed+=count;gc.collect()
     b.save('4k-render-progress.json',dict(state='rendering',completed_new_frames=completed,total_new_frames=937,last_complete_range=[cl,ch-1],render_key=key,elapsed_seconds=round(time.monotonic()-started,1)))
     print('4K checkpoint',completed,'/ 937',cl,ch,'reused' if reuse else 'rendered',flush=True)
    dec.stdout.close();assert dec.wait()==0
   except BaseException:
    if dec.poll() is None:dec.kill();dec.wait()
    if enc is not None and enc.poll() is None:enc.kill();enc.wait()
    raise
  cursor=hi
 if cursor<3037:cp(cursor,3037)
 checkpoint_allowed();assert sum(c for p,c in parts)==3037
 cat=D/'4k-concat-lowmem.txt';cat.write_text('ffconcat version 1.0\n'+''.join(f"file '{p.as_posix()}'\nduration {c/30:.12f}\n" for p,c in parts),encoding='utf-8')
 out=O/'viewing/Reconquista_OP_KO_4K.mp4';args=b.base+['-f','concat','-safe','0','-i',str(cat),'-i',str(b.prior),'-map','0:v:0','-map','1:a:0','-c','copy','-map_metadata','1','-movflags','+faststart',str(out)];b.run(args)
 b.save('build-4k.json',dict(frames=3037,segments=stats,copy_spans=copies,sha256=b.digest(out),bytes=out.stat().st_size,audio='V4 verified AAC compressed packets copied unchanged',elapsed_seconds=round(time.monotonic()-started,1),concat=args,memory_strategy='128-row float32 logo compositing; 60-frame resumable encodes; one temporal decoder per master span',render_key=key))
 b.save('4k-render-progress.json',dict(state='output_complete_verification_pending',completed_new_frames=937,total_new_frames=937,render_key=key))
 print('4K output complete',flush=True)
if __name__=='__main__':main()
