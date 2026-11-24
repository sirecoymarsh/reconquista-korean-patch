from pathlib import Path
import subprocess,json,hashlib,numpy as np
U=Path.cwd();O=U/'candidates/opening-video-ko-v3';E=O/'evidence';D=O/'build-source/review-repair';p=O/'payloads/movie/Recon_OP800_H.mpg';backup=D/'native-before-final-timestamp-remux.mpg';p.replace(backup);B=Path('F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin');flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS

def call(a):
 r=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags);assert r.returncode==0,r.stderr.decode(errors='replace');return r.stdout

def frames(x):return json.loads(call([str(B/'ffprobe.exe'),'-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(x)]))['frames']

def eh(x,sel):return call([str(B/'ffmpeg.exe'),'-v','error','-i',str(x),'-map',sel,'-c','copy','-f','hash','-hash','sha256','-']).decode().strip().split('=')[-1]
tries=[]
for size in [128,64,48,32]:
 q=D/f'native-final-remux-{size}.mpg';cmd=[str(B/'ffmpeg.exe'),'-v','warning','-y','-i',str(backup),'-map','0:v:0','-map','0:a:0','-c','copy','-bsf:v',"setts=pts='if(eq(N,3034),DTS+0.1/TB,PTS)'",'-packetsize',str(size),'-f','mpeg',str(q)];call(cmd);f=frames(q);missing=[i for i,x in enumerate(f) if 'best_effort_timestamp_time' not in x];tries.append(dict(packet_size=size,frames=len(f),missing_pts=missing));print(tries[-1],flush=True)
 if missing or len(f)!=3037:continue
 pts=np.array([float(x['best_effort_timestamp_time']) for x in f]);assert max(abs(pts-pts[0]-np.arange(3037)/30))<2/90000
 vh1=eh(backup,'0:v:0');vh2=eh(q,'0:v:0');ah1=eh(backup,'0:a:0');ah2=eh(q,'0:a:0');assert vh1==vh2 and ah1==ah2;q.replace(p)
 rep=dict(status='pass',previous_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),final_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,frames=len(f),video_elementary_sha256=vh2,audio_elementary_sha256=ah2,compressed_video_and_audio_unchanged=True,attempts=tries,command=cmd);(E/'native-final-timestamp-remux.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps(rep),flush=True);break
else:backup.replace(p);raise RuntimeError('All tested mux packet sizes lacked final timestamp')
