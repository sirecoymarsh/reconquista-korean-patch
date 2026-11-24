from pathlib import Path
import subprocess,json,sys,numpy as np
from build_opening_video_v4 import O,V,E,D,ff,probe,base,flags,run,digest,clean,logo_paint,save
from op_v4_typeset import paint
R=D/'visual-repair';R.mkdir(exist_ok=True);out=O/'viewing/Reconquista_OP_KO_4K.mp4';lo,hi=850,1030;raw=['-f','rawvideo','-pix_fmt','rgb24','-s','800x600','-r','30','-i','pipe:0'];lp=R/'clean.ffv1.mkv'
with (E/'4k-visual-repair.log').open('wb') as log:
 dec=subprocess.Popen(base+['-threads','3','-i',str(V/'build-source/opening-clean-background.ffv1.mkv'),'-vf',f'trim=start_frame={lo}:end_frame={hi},setpts=PTS-STARTPTS','-pix_fmt','rgb24','-fps_mode','passthrough','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=log,creationflags=flags);enc=subprocess.Popen(base+raw+['-an','-c:v','ffv1','-level','3','-g','1','-pix_fmt','bgr0','-threads','3',str(lp)],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=flags)
 for n in range(lo,hi):
  bb=dec.stdout.read(800*600*3);assert len(bb)==800*600*3;enc.stdin.write(clean(np.frombuffer(bb,np.uint8).reshape(600,800,3),n).tobytes())
 dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0
 conf=json.loads((V/'evidence/build-4k.json').read_text(encoding='utf-8'));oa=conf['encoder'];params=oa[oa.index('-c:v'):oa.index('-c:a')];vf='crop=800:450:0:75,hqdn3d=0.7:0.5:1.4:1.0,scale=3840:2160:flags=lanczos,unsharp=5:5:0.2:3:3:0,format=rgb24';seg=R/'render.mp4';ea=base+['-f','rawvideo','-pix_fmt','rgb24','-s','3840x2160','-r','30','-i','pipe:0','-an','-vf',f'setpts=PTS+{lo}/30/TB,ass=subtitles/opening-ko-4k.ass:fontsdir=fonts,setpts=PTS-STARTPTS,scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p']+params+['-movflags','+faststart',str(seg)]
 dec=subprocess.Popen(base+['-threads','3','-filter_threads','4','-i',str(lp),'-vf',vf,'-pix_fmt','rgb24','-fps_mode','passthrough','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=log,creationflags=flags);enc=subprocess.Popen(ea,cwd=O,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=flags)
 for n in range(lo,hi):
  bb=dec.stdout.read(3840*2160*3);assert len(bb)==3840*2160*3;a=paint(logo_paint(np.frombuffer(bb,np.uint8).reshape(2160,3840,3),n,4.8),n,s=4.8,crop_4k=True);enc.stdin.write(a.tobytes())
  if n%30==0:print('4K repair',n,flush=True)
 dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0
pre=R/'prefix.mp4';post=R/'suffix.mp4';run(base+['-i',str(out),'-map','0:v:0','-frames:v',str(lo),'-c','copy',str(pre)]);run(base+['-ss',f'{hi/30:.12f}','-i',str(out),'-map','0:v:0','-frames:v',str(3037-hi),'-c','copy',str(post)]);cat=R/'concat.txt';cat.write_text('ffconcat version 1.0\n'+''.join(f"file '{p.as_posix()}'\nduration {c/30:.12f}\n" for p,c in [(pre,lo),(seg,hi-lo),(post,3037-hi)]),encoding='utf-8');tmp=R/'final.mp4';run(base+['-f','concat','-safe','0','-i',str(cat),'-i',str(out),'-map','0:v:0','-map','1:a:0','-c','copy','-map_metadata','1','-movflags','+faststart',str(tmp)])
q=json.loads(run([probe,'-v','error','-select_streams','v:0','-show_packets','-show_entries','packet=pts_time','-of','json',str(tmp)]));pts=sorted(float(x['pts_time']) for x in q['packets']);assert len(pts)==3037 and max(abs(np.array(pts)-np.arange(3037)/30))<1e-6
previous=digest(out);out.replace(R/'before-repair.mp4');tmp.replace(out);save('4k-visual-repair.json',dict(status='encoded_delta_complete',range=[lo,hi-1],source_changed_range=[908,1012],previous_sha256=previous,sha256=digest(out),bytes=out.stat().st_size,encoder=ea,unchanged_compressed_frames=3037-(hi-lo)));print('4K visual repair complete',flush=True)
