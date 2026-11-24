from pathlib import Path
import sys,json,subprocess,time,hashlib,numpy as np
from PIL import Image
from op_v3_typeset import paint
import op_v3_logo as logo
U=Path.cwd();O=U/'candidates/opening-video-ko-v3';E=O/'evidence';src=U.parent/'research/disc/movie/Recon_OP800_H.mpg';bgfile=O/'build-source/opening-clean-background.ffv1.mkv';dest=O/'viewing/Reconquista_OP_KO_4K.mp4';dest.parent.mkdir(exist_ok=True);ff='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS
assert (E/'build-native.json').exists();cache=dict(np.load(O/'build-source/logo-observed-color-motion.npz'));index={int(n):i for i,n in enumerate(cache['frames'])}
base=[ff,'-hide_banner','-loglevel','warning','-y'];encoder=['-c:v','h264_nvenc','-preset','p7','-tune','hq','-rc','vbr','-cq','16','-b:v','0','-maxrate','100M','-bufsize','200M','-multipass','fullres','-spatial-aq','1','-temporal-aq','1','-aq-strength','8','-rc-lookahead','32','-bf','3','-g','60','-profile:v','high']
test=subprocess.run(base+['-f','lavfi','-i','color=c=black:s=3840x2160:r=30','-frames:v','1']+encoder+['-pix_fmt','yuv420p','-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,creationflags=flags)
if test.returncode:
 (E/'4k-nvenc-unavailable.log').write_bytes(test.stderr);encoder=['-c:v','libx264','-preset','medium','-crf','17','-profile:v','high','-g','60','-bf','3','-threads','6']
filters='crop=800:450:0:75,hqdn3d=0.7:0.5:1.4:1.0,scale=3840:2160:flags=lanczos,unsharp=5:5:0.2:3:3:0,format=rgb24'
dargs=base+['-threads','4','-filter_threads','4','-i',str(bgfile),'-vf',filters,'-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','pipe:1'];eargs=base+['-f','rawvideo','-pix_fmt','rgb24','-s','3840x2160','-r','30','-i','pipe:0','-i',str(src),'-map','0:v:0','-map','1:a:0','-vf','ass=subtitles/opening-ko-4k.ass:fontsdir=fonts,scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p']+encoder+['-color_range','tv','-colorspace','bt709','-color_trc','bt709','-color_primaries','bt709','-c:a','aac','-b:a','320k','-ar','44100','-movflags','+faststart','-map_metadata','-1','-metadata','title=Reconquista Korean Opening — 4K Remaster','-metadata','comment=Original SD picture restored and upscaled; Korean type and approved logo composited at 4K. Translator: Codex internal.',str(dest)]
logs=[(E/f).open('wb') for f in ['4k-upscale-decode.log','4k-encode.log']];dec=subprocess.Popen(dargs,stdout=subprocess.PIPE,stderr=logs[0],creationflags=flags);enc=subprocess.Popen(eargs,cwd=O,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=logs[1],creationflags=flags);n=0;start=time.monotonic()
try:
 while True:
  b=dec.stdout.read(3840*2160*3)
  if not b:break
  assert len(b)==3840*2160*3;a=np.frombuffer(b,np.uint8).reshape(2160,3840,3)
  if n in index:
   i=index[n];star=np.unpackbits(cache['star'][i]).reshape(600,800).astype(bool);a=logo.draw(a,n,cache['colors'][i],float(cache['opacity'][i]),star,s=4.8)
  a=paint(a,n,s=4.8,crop_4k=True);enc.stdin.write(a.tobytes());n+=1
  if n%150==0:
   p=dict(frames=n,elapsed_seconds=round(time.monotonic()-start,1));(E/'4k-build-progress.json').write_text(json.dumps(p)+'\n');print(json.dumps(p),flush=True)
 assert n==3037;dec.stdout.close();assert dec.wait()==0;enc.stdin.close();assert enc.wait()==0
except BaseException:
 dec.kill();enc.kill();raise
finally:
 for h in logs:h.close()
rep=dict(status='encoded_validation_pending',output=str(dest),frames=n,size=[3840,2160],crop=[0,75,800,450],source_size=[800,600],layout='16:9 fill, captions repositioned inside picture',enhancement='mild spatiotemporal MPEG noise reduction, Lanczos upscale, restrained luma sharpening; no synthetic motion interpolation',korean_type='rendered directly at 4.8x; 4K lyric/credit ASS; character CV and final theme rows raised for subtitle clearance',logo_master=str(logo.MASTER),logo_sha256=logo.SHA,audio='source MP2 decoded and encoded as AAC 320 kbps for MP4 compatibility',encoder=eargs,upscale_command=dargs,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),bytes=dest.stat().st_size,elapsed_seconds=round(time.monotonic()-start,1));(E/'build-4k.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(rep,ensure_ascii=False),flush=True)