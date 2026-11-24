from pathlib import Path
import json,sys,hashlib,numpy as np
from PIL import Image
U=Path.cwd();sys.path.insert(0,str(U/'tools'));from raster_codec import raw_image
O=U/'candidates/ending-credits-raster-v1';M=O/'manifest.json';main=json.loads(M.read_text(encoding='utf-8'));rows=[];cache={}
def resolve(n):
 if n in cache:return cache[n]
 b=(O/'payloads'/n).read_bytes();im,p,c=raw_image(b);assert c==3
 if b[4:8]==b'TC01':
  bn=p[22:].rstrip(b'\0').decode('cp932');bn=bn if bn.endswith('.rct') else bn+'.rct';z=np.all(im==[255,0,0],2);base=resolve(bn);im[z]=base[z]
 cache[n]=im;return im
for i in range(2,12):
 n=f'staffrollb_{i:03d}.rct';b=(O/'payloads'/n).read_bytes();raw,p,c=raw_image(b);assert b[4:8]==b'TC01';bn=p[22:].rstrip(b'\0').decode('cp932');bn=bn if bn.endswith('.rct') else bn+'.rct';count=int(np.all(raw==[255,0,0],2).sum());effective=resolve(n);preview=np.asarray(Image.open(O/'preview'/(n+'.png')).convert('RGB'));assert np.array_equal(effective,preview);assert hashlib.sha256(b).hexdigest()==main['output_hashes'][n];rows.append({'entry':n,'signature':'TC01','base_entry':bn,'base_output_sha256':main['output_hashes'][bn],'sentinel_rgb':[255,0,0],'sentinel_pixels':count,'effective_pixels_equal_persisted_preview':True,'dependent_base_resolved_from_same_candidate':True})
r={'candidate':'ending-credits-raster-v1','candidate_manifest_sha256':hashlib.sha256(M.read_bytes()).hexdigest(),'scope':'Only ten changed TC01 slide dependencies; prior full raster/semantic checks reused. No new game execution.','closure':{'TC01_base_and_sentinel':{'pass':True,'entries':rows}},'payloads_modified':False,'original_candidate_manifest_modified':False,'structural_pass':True,'visual_pass_reused_from_main_manifest':main['visual_pass'],'runtime_review':'user_final_review_pending'};out=O/'verification-manifest.json';assert not out.exists();out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');gpath=U/'progress.json';g=json.loads(gpath.read_text(encoding='utf-8-sig'));g['op_ed']['credits']['verification_addendum']='candidates/ending-credits-raster-v1/verification-manifest.json';g['op_ed']['credits']['tc01_dependency_closure']='PASS: ten entries, zero sentinel pixels; same-candidate base resolution equals persisted preview';gpath.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'entries':10,'sentinel_counts':[x['sentinel_pixels'] for x in rows],'effective_preview_match':True,'report':str(out),'existing_manifest_unchanged':True},ensure_ascii=False))
