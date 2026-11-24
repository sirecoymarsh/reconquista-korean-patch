from pathlib import Path
import subprocess,json,hashlib,numpy as np
U=Path.cwd();O=U/'candidates/opening-video-ko-v3';E=O/'evidence';D=O/'build-source/review-repair';out=O/'viewing/Reconquista_OP_KO_4K.mp4';B=Path('F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin');flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS

def call(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,creationflags=flags);assert not p.stderr,p.stderr.decode(errors='replace');return p.stdout
j=json.loads((E/'4k-technical-validation.json').read_text());prior_sha=j['sha256'];repair=json.loads((E/'4k-review-repair.json').read_text());q=json.loads(call([str(B/'ffprobe.exe'),'-v','error','-show_streams','-show_format','-show_packets','-show_entries','packet=stream_index,pts_time,duration_time','-of','json',str(out)]));v=next(r for r in q['streams'] if r['codec_type']=='video');a=next(r for r in q['streams'] if r['codec_type']=='audio');pts=sorted(float(r['pts_time']) for r in q['packets'] if r['stream_index']==v['index']);assert len(pts)==3037 and max(abs(np.array(pts)-np.arange(3037)/30))<1e-6

def ah(p):return call([str(B/'ffmpeg.exe'),'-v','error','-i',str(p),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-']).decode().strip().split('=')[-1]
initial=ah(D/'4k-before-review-repair.mp4');final=ah(out);assert initial==final
j.update(sha256=repair['sha256'],bytes=repair['bytes'],final_packet_count=3037,final_video_packet_pts_error_seconds=float(max(abs(np.array(pts)-np.arange(3037)/30))),audio_pcm_evidence_reused_from_sha256=prior_sha,audio_aac_elementary_sha256=final,audio_unchanged_from_tested_encode=True,final_audio_start=float(a.get('start_time',0)),final_video_start=float(v.get('start_time',0)),format_duration=q['format']['duration'],last_change='one corrected source-art frame n2161 inside existing repaired segment; all verified audio and unchanged frame evidence reused')
assert j['final_audio_start']==j['final_video_start']==0;assert (v['width'],v['height'])==(3840,2160);(E/'4k-technical-validation.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
# Decode the affected last frame from each final file. The other reviewed frames
# and all earlier technical evidence remain unchanged and are reused.
for kind,video in [('native',O/'payloads/movie/Recon_OP800_H.mpg'),('4k',out)]:
 r=json.loads((E/f'{kind}-repair-encoded-review.json').read_text());dest=next(x['path'] for x in r['frames'] if x['frame']==2161);call([str(B/'ffmpeg.exe'),'-v','error','-xerror','-y','-threads','4','-i',str(video),'-vf',"select='eq(n,2161)'",'-frames:v','1','-fps_mode','vfr',dest]);print('final encoded frame refreshed',kind,dest,flush=True)
