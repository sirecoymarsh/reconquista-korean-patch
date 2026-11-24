from pathlib import Path
import sys,json,subprocess,time,hashlib,numpy as np
from PIL import Image
from op_v3_compositor import Compositor,ensure_nana
from op_v3_typeset import paint
import op_v3_logo as logo
U=Path.cwd();O=U/'candidates/opening-video-ko-v3';E=O/'evidence';src=U.parent/'research/disc/movie/Recon_OP800_H.mpg';dest=O/'payloads/movie/Recon_OP800_H.mpg';bgfile=O/'build-source/opening-clean-background.ffv1.mkv';dest.parent.mkdir(parents=True,exist_ok=True);E.mkdir(exist_ok=True);flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS;ff='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';ensure_nana()
assert not (O/'manifest.json').exists() or not json.loads((O/'manifest.json').read_text()).get('frozen')
base=[ff,'-hide_banner','-loglevel','warning','-y'];raw=['-f','rawvideo','-pix_fmt','rgb24','-s','800x600','-r','30','-i','pipe:0'];dargs=base+['-threads','2','-i',str(src),'-map','0:v:0','-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','pipe:1'];bargs=base+raw+['-an','-c:v','ffv1','-level','3','-coder','1','-context','1','-g','1','-slices','16','-slicecrc','1','-pix_fmt','bgr0','-threads','4',str(bgfile)];eargs=base+raw+['-i',str(src),'-map','0:v:0','-map','1:a:0','-vf','ass=subtitles/opening-ko.ass:fontsdir=fonts','-c:v','mpeg1video','-pix_fmt','yuv420p','-q:v','2','-b:v','8000k','-maxrate','9200k','-bufsize','1835008','-g','15','-bf','2','-r','30','-aspect','4:3','-c:a','copy','-map_metadata','-1','-threads','4','-f','mpeg',str(dest)]
logs=[(E/f).open('wb') for f in ['decode-v3.log','clean-background-encode.log','native-encode.log']];dec=subprocess.Popen(dargs,stdout=subprocess.PIPE,stderr=logs[0],creationflags=flags);bgenc=subprocess.Popen(bargs,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=logs[1],creationflags=flags);enc=subprocess.Popen(eargs,cwd=O,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=logs[2],creationflags=flags)
c=Compositor();n=0;ln=[];lr=[];lo=[];ls=[];proof=O/'preview/native-preencode';proof.mkdir(exist_ok=True);start=time.monotonic();models={};sample=set([600,660,780,894,909,2709,2730,2880,2970])
try:
 while True:
  b=dec.stdout.read(800*600*3)
  if not b:break
  assert len(b)==800*600*3;n0=n;a=np.frombuffer(b,np.uint8).reshape(600,800,3);clean,m,r=c.compose(a,n);t=n/30
  meta=None
  if logo.old.active(t):
   clean,rep=logo.old.compose(clean,t);rows,op,star=logo.metadata(a,t);ln.append(n);lr.append(rows);lo.append(op);ls.append(np.packbits(star));meta=(rows,op,star);models[rep['model']]=models.get(rep['model'],0)+1
  bgenc.stdin.write(clean.tobytes());out=clean
  if meta is not None:out=logo.draw(out,n,*meta,s=1)
  out=paint(out,n);enc.stdin.write(out.tobytes())
  if n in sample or (r is not None and n%3==0):Image.fromarray(out).save(proof/f'{n:04d}.png')
  n+=1
  if n%150==0:
   p=dict(frames=n,elapsed_seconds=round(time.monotonic()-start,1),text_frames=len(c.report),logo_frames=len(ln));(E/'build-progress.json').write_text(json.dumps(p)+'\n');print(json.dumps(p),flush=True)
 assert n==3037;dec.stdout.close();assert dec.wait()==0;bgenc.stdin.close();enc.stdin.close();assert bgenc.wait()==0;assert enc.wait()==0
except BaseException:
 dec.kill();bgenc.kill();enc.kill();raise
finally:
 for h in logs:h.close()
np.savez_compressed(O/'build-source/logo-observed-color-motion.npz',frames=np.array(ln),colors=np.array(lr),opacity=np.array(lo),star=np.array(ls));(E/'frame-restoration.json').write_text(json.dumps(c.report,indent=2)+'\n');rep=dict(status='encoded_validation_pending',source=str(src),native_output=str(dest),clean_background=str(bgfile),frames=n,text_restoration_frames=len(c.report),logo_frames=len(ln),logo_master=str(logo.MASTER),logo_sha256=logo.SHA,caption_cues=26,translator_model='Codex internal',protected_pixel_changes_outside_owned_masks=0,background_methods=models,native_encoder=eargs,background_encoder=bargs,elapsed_seconds=round(time.monotonic()-start,1),native_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),native_bytes=dest.stat().st_size);(E/'build-native.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(rep,ensure_ascii=False),flush=True)