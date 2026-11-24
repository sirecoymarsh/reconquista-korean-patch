from pathlib import Path
import sys,json,subprocess,hashlib,time,numpy as np
from PIL import Image
from op_v3_typeset import paint
import op_v3_logo as logo
U=Path.cwd();O=U/'candidates/opening-video-ko-v3';E=O/'evidence';D=O/'build-source/review-repair';B=Path('F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin');ff=str(B/'ffmpeg.exe');probe=str(B/'ffprobe.exe');flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS
assert not (O/'manifest.json').exists() or not json.loads((O/'manifest.json').read_text(encoding='utf-8')).get('frozen'), 'Frozen candidate: use a new version for further edits'
source=U.parent/'research/disc/movie/Recon_OP800_H.mpg';background=O/'build-source/opening-clean-background.ffv1.mkv';base=[ff,'-v','warning','-y'];start=time.monotonic()
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags);assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def override(a,n):
 p=D/f'{n:04d}.png'
 return np.array(Image.open(p).convert('RGB')) if p.exists() else a

def meta(p):return json.loads(run([probe,'-v','error','-show_streams','-show_format','-of','json',str(p)]))

def native():
 out=O/'payloads/movie/Recon_OP800_H.mpg';prior=D/'native-before-review-repair.mpg'
 if not prior.exists():out.replace(prior)
 temp=D/'native-repaired.mpg';cache=dict(np.load(O/'build-source/logo-observed-color-motion.npz'));index={int(n):i for i,n in enumerate(cache['frames'])}
 da=base+['-threads','3','-i',str(background),'-pix_fmt','rgb24','-f','rawvideo','pipe:1']
 ea=base+['-f','rawvideo','-pix_fmt','rgb24','-s','800x600','-r','30','-i','pipe:0','-i',str(source),'-map','0:v:0','-map','1:a:0','-vf','ass=subtitles/opening-ko.ass:fontsdir=fonts','-c:v','mpeg1video','-pix_fmt','yuv420p','-q:v','2','-b:v','8000k','-maxrate','9200k','-bufsize','1835008','-g','15','-bf','2','-r','30','-aspect','4:3','-c:a','copy','-map_metadata','-1','-threads','4','-bsf:v',"setts=pts='if(eq(N,3034),DTS+0.1/TB,PTS)'",'-packetsize','128','-f','mpeg',str(temp)]
 with (E/'native-review-repair.log').open('wb') as log:
  dec=subprocess.Popen(da,stdout=subprocess.PIPE,stderr=log,creationflags=flags);enc=subprocess.Popen(ea,cwd=O,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=flags);n=0
  try:
   while True:
    b=dec.stdout.read(800*600*3)
    if not b:break
    assert len(b)==800*600*3;a=override(np.frombuffer(b,np.uint8).reshape(600,800,3),n)
    if n in index:
     i=index[n];star=np.unpackbits(cache['star'][i]).reshape(600,800).astype(bool);a=logo.draw(a,n,cache['colors'][i],float(cache['opacity'][i]),star,s=1)
    a=paint(a,n);enc.stdin.write(a.tobytes());n+=1
    if n%600==0:print('native',n,flush=True)
   dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0 and n==3037
  except BaseException:dec.kill();enc.kill();raise
 temp.replace(out);rep=dict(status='encoded_validation_pending',previous_sha256=digest(prior),sha256=digest(out),bytes=out.stat().st_size,command=ea,frames=n,repair_frames=88,background_base_reused=str(background),elapsed_seconds=round(time.monotonic()-start,1));(E/'native-review-repair.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps(rep),flush=True)

def four():
 out=O/'viewing/Reconquista_OP_KO_4K.mp4';prior=D/'4k-before-review-repair.mp4'
 if not prior.exists():out.replace(prior)
 keys=json.loads(run([probe,'-v','error','-skip_frame','nokey','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(prior)]))['frames'];kn=[round(float(x['best_effort_timestamp_time'])*30) for x in keys];lo=max(n for n in kn if n<=1989);hi=min(n for n in kn if n>2163);count=hi-lo;segment=D/'4k-clean-segment.ffv1.mkv';size=800*600*3
 da=base+['-threads','3','-i',str(background),'-vf',f'select=between(n\\,{lo}\\,{hi-1})','-fps_mode','passthrough','-frames:v',str(count),'-pix_fmt','rgb24','-f','rawvideo','pipe:1'];ba=base+['-f','rawvideo','-pix_fmt','rgb24','-s','800x600','-r','30','-i','pipe:0','-an','-c:v','ffv1','-level','3','-g','1','-pix_fmt','bgr0','-threads','3',str(segment)]
 with (E/'4k-review-repair.log').open('wb') as log:
  dec=subprocess.Popen(da,stdout=subprocess.PIPE,stderr=log,creationflags=flags);enc=subprocess.Popen(ba,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=flags)
  try:
   for n in range(lo,hi):
    b=dec.stdout.read(size);assert len(b)==size;a=override(np.frombuffer(b,np.uint8).reshape(600,800,3),n);enc.stdin.write(a.tobytes())
   dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0
  except BaseException:dec.kill();enc.kill();raise
  config=json.loads((E/'build-4k.json').read_text(encoding='utf-8'));oldargs=config['encoder'];encparams=oldargs[oldargs.index('-c:v'):oldargs.index('-c:a')];filters='crop=800:450:0:75,hqdn3d=0.7:0.5:1.4:1.0,scale=3840:2160:flags=lanczos,unsharp=5:5:0.2:3:3:0,format=rgb24';middle=D/'4k-middle.mp4'
  da=base+['-threads','3','-filter_threads','4','-i',str(segment),'-vf',filters,'-pix_fmt','rgb24','-f','rawvideo','pipe:1'];ea=base+['-f','rawvideo','-pix_fmt','rgb24','-s','3840x2160','-r','30','-i','pipe:0','-an','-vf',f'setpts=PTS+{lo}/30/TB,ass=subtitles/opening-ko-4k.ass:fontsdir=fonts,setpts=PTS-STARTPTS,scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p']+encparams+['-movflags','+faststart',str(middle)]
  dec=subprocess.Popen(da,stdout=subprocess.PIPE,stderr=log,creationflags=flags);enc=subprocess.Popen(ea,cwd=O,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=flags)
  try:
   for n in range(lo,hi):
    b=dec.stdout.read(3840*2160*3);assert len(b)==3840*2160*3;a=np.frombuffer(b,np.uint8).reshape(2160,3840,3);a=paint(a,n,s=4.8,crop_4k=True);enc.stdin.write(a.tobytes())
    if (n-lo)%60==0:print('4K segment',n-lo,'/',count,flush=True)
   dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0
  except BaseException:dec.kill();enc.kill();raise
 before=D/'4k-before.mp4';after=D/'4k-after.mp4'
 run(base+['-i',str(prior),'-map','0:v:0','-c','copy','-frames:v',str(lo),str(before)])
 run(base+['-ss',f'{hi/30:.9f}','-i',str(prior),'-map','0:v:0','-c','copy',str(after)])
 cat=D/'4k-concat.txt';cat.write_text("ffconcat version 1.0\n"+f"file '{before.as_posix()}'\nduration {lo/30:.12f}\nfile '{middle.as_posix()}'\nduration {count/30:.12f}\nfile '{after.as_posix()}'\n",encoding='utf-8')
 final=base+['-f','concat','-safe','0','-i',str(cat),'-i',str(prior),'-map','0:v:0','-map','1:a:0','-c','copy','-map_metadata','1','-movflags','+faststart',str(out)];run(final)
 rep=dict(status='encoded_validation_pending',previous_sha256=digest(prior),sha256=digest(out),bytes=out.stat().st_size,repair_frames=88,rerendered_frame_range=[lo,hi-1],rerendered_frames=count,unchanged_video_regions='compressed packets copied; no re-encode outside affected GOP span',audio='AAC packets copied from first 4K encode',segment_encoder=ea,concat_command=final,elapsed_seconds=round(time.monotonic()-start,1));(E/'4k-review-repair.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps(rep),flush=True)
if __name__=='__main__':native() if '--native' in sys.argv else four()
