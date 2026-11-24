from pathlib import Path
import json,subprocess,hashlib,numpy as np
U=Path.cwd();O=U/'candidates/opening-video-ko-v5';E=O/'evidence';V=U/'candidates/opening-video-ko-v3';out=O/'viewing/Reconquista_OP_KO_4K.mp4';B=Path('F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin');flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS

def run(a):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags);assert p.returncode==0,p.stderr.decode(errors='replace');assert not p.stderr,p.stderr.decode(errors='replace');return p.stdout
prior=json.loads((V/'evidence/4k-technical-validation.json').read_text());q=json.loads(run([str(B/'ffprobe.exe'),'-v','error','-show_streams','-show_format','-show_packets','-show_entries','packet=stream_index,pts_time,duration_time','-of','json',str(out)]));v=next(r for r in q['streams'] if r['codec_type']=='video');a=next(r for r in q['streams'] if r['codec_type']=='audio');pts=sorted(float(r['pts_time']) for r in q['packets'] if r['stream_index']==v['index']);err=float(max(abs(np.array(pts)-np.arange(3037)/30)));assert len(pts)==3037 and err<1e-6
ah=run([str(B/'ffmpeg.exe'),'-v','error','-i',str(out),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-']).decode().strip().split('=')[-1];assert ah==prior['audio_aac_elementary_sha256'];assert (v['width'],v['height'])==(3840,2160) and v['codec_name']=='h264' and v['pix_fmt']=='yuv420p';assert v['color_space']=='bt709' and v['color_range']=='tv';assert float(a.get('start_time',0))==float(v.get('start_time',0))==0
h=hashlib.sha256()
with out.open('rb') as f:
 for z in iter(lambda:f.read(8*1024*1024),b''):h.update(z)
j=dict(status='technical_pass',sha256=h.hexdigest(),bytes=out.stat().st_size,size=[3840,2160],video_frames=len(pts),frame_rate=v['avg_frame_rate'],video_packet_pts_max_error_seconds=err,video_start=0,audio_start=0,color_space=v['color_space'],color_range=v['color_range'],audio_codec=a['codec_name'],audio_aac_elementary_sha256=ah,audio_unchanged_from_tested_v3=True,audio_pcm_evidence_reused=str(V/'evidence/4k-technical-validation.json'),audio_pcm_zero_lag_checks=prior['audio_pcm_zero_lag_checks'],format_duration=q['format']['duration'],runtime_game='not run',audio_playback='not run')
(E/'4k-technical-validation.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
