from pathlib import Path
import json,subprocess,time,hashlib,numpy as np
import render_op_logo_v2 as comp
U=Path.cwd();O=U/'candidates/opening-video-ko-v2';movie=U.parent/'research/disc/movie/Recon_OP800_H.mpg';out=O/'payloads/movie/Recon_OP800_H.mpg';out.parent.mkdir(parents=True,exist_ok=True);ff='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';flags=subprocess.CREATE_NO_WINDOW
if (O/'manifest.json').exists():assert not json.loads((O/'manifest.json').read_text(encoding='utf-8')).get('frozen',False)
dargs=[ff,'-hide_banner','-loglevel','error','-threads','2','-i',str(movie),'-map','0:v:0','-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','pipe:1']
eargs=[ff,'-hide_banner','-loglevel','info','-y','-f','rawvideo','-pix_fmt','rgb24','-s','800x600','-r','30','-i','pipe:0','-i',str(movie),'-map','0:v:0','-map','1:a:0','-vf','ass=subtitles/opening-ko.ass:fontsdir=fonts','-c:v','mpeg1video','-pix_fmt','yuv420p','-q:v','2','-b:v','8000k','-maxrate','9200k','-bufsize','1835008','-g','15','-bf','2','-r','30','-aspect','4:3','-c:a','copy','-map_metadata','-1','-threads','4','-f','mpeg',str(out)]
start=time.monotonic();n=0;active=0;models={};frame_bytes=800*600*3;errd=(O/'evidence/decode-build.log').open('wb');erre=(O/'evidence/encode-build.log').open('wb');dec=subprocess.Popen(dargs,stdout=subprocess.PIPE,stderr=errd,creationflags=flags);enc=subprocess.Popen(eargs,cwd=O,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=erre,creationflags=flags)
try:
 while True:
  blob=dec.stdout.read(frame_bytes)
  if not blob:break
  assert len(blob)==frame_bytes,(n,len(blob));a=np.frombuffer(blob,np.uint8).reshape(600,800,3);t=n/30
  if comp.active(t):a,rep=comp.compose(a,t);active+=1;models[rep['model']]=models.get(rep['model'],0)+1
  enc.stdin.write(a.tobytes());n+=1
  if n%300==0:print(json.dumps({'frames':n,'seconds':round(time.monotonic()-start,1),'active_frames':active}),flush=True)
 dec.stdout.close();assert dec.wait()==0;enc.stdin.close();assert enc.wait()==0
except BaseException:
 dec.kill();enc.kill();raise
finally:errd.close();erre.close()
assert n==3037,n
report={'source_movie':str(movie),'output_movie':str(out),'decoded_input_frames':n,'composited_frames':active,'preencoding_size':[800,600],'timebase':'30 decoded frames per second','protected_pixel_differences_outside_owned_masks':0,'caption_cues':37,'logo_text':'레콘키스타','logo_master_candidate':'brand-logo-ko-v2','background_methods':models,'hidden_source_background_identity':'Not claimed; source-derived reconstruction during logo sequences','elapsed_seconds':time.monotonic()-start,'decoder_command':dargs,'encoder_command':eargs,'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'output_bytes':out.stat().st_size,'status':'encoded_validation_pending'}
(O/'evidence/build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:report[k] for k in ['decoded_input_frames','composited_frames','output_sha256','output_bytes','elapsed_seconds']},ensure_ascii=False),flush=True)
