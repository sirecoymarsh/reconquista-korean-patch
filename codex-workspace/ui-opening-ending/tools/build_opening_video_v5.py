"""Build v5 without re-encoding unchanged v4 4K GOPs; no application playback."""
from pathlib import Path
import sys,subprocess,json,hashlib,time,numpy as np
from PIL import Image
from op_v4_typeset import paint as paint_v4
import op_v5_quotes as quote
import op_v3_logo as logo
import gc
logo.old.F.clear();logo.old.legacy.frames.clear();gc.collect()
U=Path(__file__).resolve().parents[1];O=U/'candidates/opening-video-ko-v5';V=U/'candidates/opening-video-ko-v3';E=O/'evidence';D=O/'build-source';B=Path('F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin');ff=str(B/'ffmpeg.exe');probe=str(B/'ffprobe.exe');flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS;base=[ff,'-v','warning','-y'];source=U.parent/'research/disc/movie/Recon_OP800_H.mpg';background=V/'build-source/opening-clean-background.ffv1.mkv';V4=U/'candidates/opening-video-ko-v4';prior=V4/'viewing/Reconquista_OP_KO_4K.mp4';start=time.monotonic()
assert not (O/'manifest.json').exists(), 'Use a new version after freeze'
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags);assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(name,r):(E/name).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def plan():
 p=E/'4k-segment-plan.json'
 if p.exists():return json.loads(p.read_text(encoding='utf-8'))
 keys=json.loads(run([probe,'-v','error','-skip_frame','nokey','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(prior)]))['frames'];kn=sorted({round(float(x['best_effort_timestamp_time'])*30) for x in keys}|{3037});ranges=[]
 for a,b in [(604,921),(1047,1160),(2745,3000)]:ranges.append([max(k for k in kn if k<=a),min(k for k in kn if k>b)])
 j=dict(source=str(prior),ranges=ranges,frame_count=3037,reason='Upper logo quote captions removed; small paragraph translated in place in both scenes; in darkness retained in Korean lyric');save(p.name,j);print(j,flush=True);return j
cache=dict(np.load(V/'build-source/logo-observed-color-motion.npz'));idx={int(n):i for i,n in enumerate(cache['frames'])}
def logo_paint(a,n,s):
 if n not in idx:return a
 i=idx[n];star=np.unpackbits(cache['star'][i]).reshape(600,800).astype(bool)
 if 908<=n<954:star[:]=False
 return logo.draw(a,n,cache['colors'][i],float(cache['opacity'][i]),star,s=s)
QC=D/'quote-clean-final';QC.mkdir(exist_ok=True)
QPATH=E/'quote-restoration.json'
Q={int(r['frame']):r for r in json.loads(QPATH.read_text(encoding='utf-8'))['frames']} if QPATH.exists() else {}
def paint(a,n,s=1,crop_4k=False):
 a=paint_v4(a,n,s=s,crop_4k=crop_4k)
 return quote.draw(a,n,Q.get(n,{}).get('opacity',0),s=s)
def clean(a,n):
 p=V4/'build-source/english-clean'/f'{n:04d}.png'
 if p.exists():a=np.array(Image.open(p).convert('RGB'))
 else:
  p=V/'build-source/review-repair'/f'{n:04d}.png'
  if p.exists():a=np.array(Image.open(p).convert('RGB'))
 if quote.active(n) and (QC/f'{n:04d}.json').exists():
  rep=json.loads((QC/f'{n:04d}.json').read_text());Q[n]=rep;return np.array(Image.open(QC/f'{n:04d}.png').convert('RGB'))
 a,rep=quote.clean(a,n)
 if rep is not None:
  Q[n]=rep;Image.fromarray(a).save(QC/f'{n:04d}.png');(QC/f'{n:04d}.json').write_text(json.dumps(rep))
 return a

def native():
 assert not (O/'game-manifest.json').exists(), 'Native output frozen; use a new version'
 ranges=[] if '--native-only' in sys.argv else plan()['ranges'];out=O/'payloads/movie/Recon_OP800_H.mpg';raw=['-f','rawvideo','-pix_fmt','rgb24','-s','800x600','-r','30','-i','pipe:0'];da=base+['-threads','3','-i',str(background),'-pix_fmt','rgb24','-fps_mode','passthrough','-f','rawvideo','pipe:1'];ea=base+raw+['-i',str(source),'-map','0:v:0','-map','1:a:0','-vf','ass=subtitles/opening-ko.ass:fontsdir=fonts','-c:v','mpeg1video','-pix_fmt','yuv420p','-q:v','2','-b:v','8000k','-maxrate','9200k','-bufsize','1835008','-g','15','-bf','2','-r','30','-aspect','4:3','-c:a','copy','-map_metadata','-1','-threads','4','-bsf:v',"setts=pts='if(eq(N,3034),DTS+0.1/TB,PTS)'",'-packetsize','128','-f','mpeg',str(out)]
 with (E/'native-build.log').open('wb') as log:
  dec=subprocess.Popen(da,stdout=subprocess.PIPE,stderr=log,creationflags=flags);enc=subprocess.Popen(ea,cwd=O,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=flags);senc=None;n=0
  try:
   while True:
    bb=dec.stdout.read(800*600*3)
    if not bb:break
    assert len(bb)==800*600*3;a=clean(np.frombuffer(bb,np.uint8).reshape(600,800,3),n)
    for j,(lo,hi) in enumerate(ranges):
     if n==lo:
      ba=base+raw+['-an','-c:v','ffv1','-level','3','-g','1','-pix_fmt','bgr0','-threads','3',str(D/f'4k-clean-{j}.ffv1.mkv')];senc=subprocess.Popen(ba,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=flags)
     if lo<=n<hi:senc.stdin.write(a.tobytes())
     if n==hi-1:senc.stdin.close();assert senc.wait()==0;senc=None
    a=paint(logo_paint(a,n,1),n);enc.stdin.write(a.tobytes());n+=1
    if n%100==0:
     gc.collect();print('native',n,flush=True)
   dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0 and n==3037
  except BaseException:
   dec.kill();enc.kill()
   if senc:senc.kill()
   raise
 save('quote-restoration.json',dict(frames=list(Q.values()),source_owned_regions_only=True,quote_layout=quote.layer(1)[1],foreign_span='in darkness'));save('build-native.json',dict(frames=n,sha256=digest(out),bytes=out.stat().st_size,encoder=ea,elapsed_seconds=round(time.monotonic()-start,1),caption_cues=32,caption_pairs=16));print('native done',flush=True)

def four():
 ranges=plan()['ranges'];config=json.loads((V/'evidence/build-4k.json').read_text(encoding='utf-8'));oldargs=config['encoder'];params=oldargs[oldargs.index('-c:v'):oldargs.index('-c:a')];parts=[];cursor=0;stats=[]
 for j,(lo,hi) in enumerate(ranges):
  count=hi-lo
  if lo>cursor:
   cp=D/f'4k-copy-{cursor}-{lo}.mp4';run(base+['-ss',f'{cursor/30:.9f}','-i',str(prior),'-map','0:v:0','-frames:v',str(lo-cursor),'-c','copy',str(cp)]);parts.append((cp,lo-cursor))
  out=D/f'4k-render-{j}.mp4';filters='crop=800:450:0:75,hqdn3d=0.7:0.5:1.4:1.0,scale=3840:2160:flags=lanczos,unsharp=5:5:0.2:3:3:0,format=rgb24';da=base+['-threads','3','-filter_threads','4','-i',str(D/f'4k-clean-{j}.ffv1.mkv'),'-vf',filters,'-pix_fmt','rgb24','-fps_mode','passthrough','-f','rawvideo','pipe:1'];ea=base+['-f','rawvideo','-pix_fmt','rgb24','-s','3840x2160','-r','30','-i','pipe:0','-an','-vf',f'setpts=PTS+{lo}/30/TB,ass=subtitles/opening-ko-4k.ass:fontsdir=fonts,setpts=PTS-STARTPTS,scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p']+params+['-movflags','+faststart',str(out)]
  with (E/f'4k-segment-{j}.log').open('wb') as log:
   dec=subprocess.Popen(da,stdout=subprocess.PIPE,stderr=log,creationflags=flags);enc=subprocess.Popen(ea,cwd=O,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=flags)
   try:
    for n in range(lo,hi):
     bb=dec.stdout.read(3840*2160*3);assert len(bb)==3840*2160*3;a=np.frombuffer(bb,np.uint8).reshape(2160,3840,3);a=paint(logo_paint(a,n,4.8),n,s=4.8,crop_4k=True);enc.stdin.write(a.tobytes())
     if (n-lo)%120==0:print('4K',j,n-lo,'/',count,flush=True)
    dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0
   except BaseException:dec.kill();enc.kill();raise
  parts.append((out,count));stats.append(dict(range=[lo,hi-1],encoder=ea,sha256=digest(out)));cursor=hi
 if cursor<3037:
  cp=D/f'4k-copy-{cursor}-3037.mp4';run(base+['-ss',f'{cursor/30:.9f}','-i',str(prior),'-map','0:v:0','-frames:v',str(3037-cursor),'-c','copy',str(cp)]);parts.append((cp,3037-cursor))
 cat=D/'4k-concat.txt';cat.write_text('ffconcat version 1.0\n'+''.join(f"file '{p.as_posix()}'\nduration {c/30:.12f}\n" for p,c in parts),encoding='utf-8');out=O/'viewing/Reconquista_OP_KO_4K.mp4';args=base+['-f','concat','-safe','0','-i',str(cat),'-i',str(prior),'-map','0:v:0','-map','1:a:0','-c','copy','-map_metadata','1','-movflags','+faststart',str(out)];run(args);save('build-4k.json',dict(frames=3037,segments=stats,copy_spans=[dict(path=str(p),frames=c) for p,c in parts if 'copy-' in p.name],sha256=digest(out),bytes=out.stat().st_size,audio='V4 verified AAC compressed packets copied unchanged',elapsed_seconds=round(time.monotonic()-start,1),concat=args));print('4K done',flush=True)
if __name__=='__main__':native() if '--native' in sys.argv or '--native-only' in sys.argv else four()
