"""Re-encode only the delivery stream from verified compositing data, with a final I frame."""
from pathlib import Path
import json,subprocess,time,hashlib,numpy as np
from op_v3_typeset import paint
import op_v3_logo as logo
U=Path.cwd();O=U/'candidates/opening-video-ko-v3';E=O/'evidence';bg=O/'build-source/opening-clean-background.ffv1.mkv';src=U.parent/'research/disc/movie/Recon_OP800_H.mpg';out=O/'build-source/native-final-I.mpg';B=Path('F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin');ff=str(B/'ffmpeg.exe');flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS;cache=dict(np.load(O/'build-source/logo-observed-color-motion.npz'));ind={int(n):i for i,n in enumerate(cache['frames'])};args=[ff,'-hide_banner','-loglevel','warning','-y','-f','rawvideo','-pix_fmt','rgb24','-s','800x600','-r','30','-i','pipe:0','-i',str(src),'-map','0:v:0','-map','1:a:0','-vf','ass=subtitles/opening-ko.ass:fontsdir=fonts','-c:v','mpeg1video','-pix_fmt','yuv420p','-q:v','2','-b:v','8000k','-maxrate','9200k','-bufsize','1835008','-g','15','-bf','2','-r','30','-force_key_frames','101.2','-aspect','4:3','-c:a','copy','-map_metadata','-1','-threads','4','-f','mpeg',str(out)]
l=(E/'native-final-I.log').open('wb');d=subprocess.Popen([ff,'-v','error','-threads','2','-i',str(bg),'-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=l,creationflags=flags);e=subprocess.Popen(args,cwd=O,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=l,creationflags=flags);n=0;start=time.monotonic()
try:
 while True:
  blob=d.stdout.read(800*600*3)
  if not blob:break
  a=np.frombuffer(blob,np.uint8).reshape(600,800,3)
  if n in ind:
   i=ind[n];star=np.unpackbits(cache['star'][i]).reshape(600,800).astype(bool);a=logo.draw(a,n,cache['colors'][i],float(cache['opacity'][i]),star,s=1)
  a=paint(a,n);e.stdin.write(a.tobytes());n+=1
  if n%600==0:print(n,round(time.monotonic()-start,1),flush=True)
 assert n==3037;d.stdout.close();assert d.wait()==0;e.stdin.close();assert e.wait()==0
except BaseException:d.kill();e.kill();raise
finally:l.close()
r=subprocess.run([str(B/'ffprobe.exe'),'-v','error','-select_streams','v:0','-show_frames','-show_streams','-show_entries','frame=best_effort_timestamp_time,pict_type','-of','json',str(out)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,creationflags=flags);probe=json.loads(r.stdout);bad=[i for i,x in enumerate(probe['frames']) if 'best_effort_timestamp_time' not in x];print('missing',bad,'duration',probe['streams'][0].get('duration'),'tail',probe['frames'][-2:],flush=True);(E/'native-final-I-probe.json').write_bytes(r.stdout);assert not bad and len(probe['frames'])==3037
final=O/'payloads/movie/Recon_OP800_H.mpg';backup=O/'build-source/native-initial-mux.mpg';assert not backup.exists();assert final.resolve().is_relative_to(O.resolve()) and backup.resolve().is_relative_to(O.resolve()) and out.resolve().is_relative_to(O.resolve());final.replace(backup);out.replace(final);p=E/'build-native.json';j=json.loads(p.read_text(encoding='utf-8'));j['initial_mux_sha256']=j['native_sha256'];j['native_sha256']=hashlib.sha256(final.read_bytes()).hexdigest();j['native_bytes']=final.stat().st_size;j['native_encoder']=args;j['final_I_frame_fix']='Final frame n3036 forced to I so MPEG-PS exposes its timestamp; artwork restoration and typography reused from lossless intermediate. Previous mux retained internally.';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('accepted',j['native_sha256'],flush=True)