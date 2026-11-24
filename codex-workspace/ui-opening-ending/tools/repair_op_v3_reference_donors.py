from pathlib import Path
import sys,json,re,numpy as np,cv2
from PIL import Image
sys.path.insert(0,'tools');from op_v3_restoration import *
from op_v3_source_art import SourceArt
S=SourceArt();records=json.loads((P/'donors.json').read_text(encoding='utf-8'))
# All rows share this fully observed source credit region. The earlier mask omitted faint strokes.
m=mask('cast-main')|((X>=24)&(X<205)&(Y>=97)&(Y<514));m=cv2.dilate(m.astype('uint8'),np.ones((7,7),np.uint8)).astype(bool)&CLIP;Image.fromarray(m.astype('uint8')*255).save(P/'cast-main-mask.png')
for k in ['city','bridge','sky']:
 a=load(P/(k+'-source.png'));g=np.array(Image.open(P/(k+'-generated-original.png')).convert('RGB').resize((800,600),Image.Resampling.LANCZOS));pred=toned(g,g,a,m);Image.fromarray(merge(a,pred,m,6)).save(P/(k+'-clean.png'))
# Background and foreground move separately. Match the foreground for this credit's hair region.
a=read(2142);m=mask('cast-support');ar=S.decode('last2.rct');H,c=register(ar,a,exclude=m|~CLIP|(X>400));assert H is not None and c>25
w=warp(ar,H);valid=(X>50)&(X<400)&CLIP&~m;coef=global_tone(w,a,valid);pred=w.astype('float32')@coef[:3]+coef[3];vv=valid.astype('float32');den=np.maximum(cv2.GaussianBlur(vv,(0,0),12),1e-5)
for ch in range(3):pred[:,:,ch]+=cv2.GaussianBlur((a[:,:,ch]-pred[:,:,ch])*vv,(0,0),12)/den
Image.fromarray(merge(a,np.clip(pred,0,255),m)).save(P/'profile-clean.png')
for r in records:
 if r['key']=='profile':r.update(matrix=H.tolist(),inliers=c,method='original last2 foreground-only registration; separate moon motion excluded')
# Rapid supporting-character shots use original sprites; inspect only TC00 bases.
targets={2166:('cameo-tomo','b_tomo'),2173:('cameo-mido','b_mido'),2183:('cameo-nana','b_nana')};best={}
for n,(key,prefix) in targets.items():
 a=read(n);m=mask('cast-support');names=[]
 for name,(fn,e) in S.idx.items():
  if not name.startswith(prefix) or not name.endswith('.rct'):continue
  with S.arcs[fn].path.open('rb') as f:f.seek(e['offset']+4);magic=f.read(4)
  if magic==b'TC00':names.append(name)
 print(key,'bases',len(names),flush=True)
 for name in names:
  ar=S.decode(name);H,c=register(ar,a,exclude=m|~CLIP)
  if H is not None and (n not in best or c>best[n][0]):best[n]=(c,name,H.copy())
  S.cache.clear()
 if n not in best:print(key,'NO MATCH',flush=True);continue
 c,name,H=best[n];print(key,name,c,flush=True)
 ar=S.decode(name);w=warp(ar,H);mat=name[:-4]+'_.rc8';assert mat in S.idx
 fn,e=S.idx[mat]
 with S.arcs[fn].path.open('rb') as f:f.seek(e['offset']);b=f.read(e['size'])
 from raster_codec import raw_image
 ix,_,_=raw_image(b);pal=np.frombuffer(b[20:788],np.uint8).reshape(256,3);wa=warp((255-np.mean(pal[ix],axis=2)).astype('float32')/255,H);bg=poly_background(a,m,235)
 valid=CLIP&~m&(wa>.97);coef=global_tone(w,a,valid);fg=w.astype('float32')@coef[:3]+coef[3];pred=fg*wa[:,:,None]+bg*(1-wa[:,:,None]);pred=toned(pred,pred,a,m)
 Image.fromarray(a).save(P/(key+'-source.png'));Image.fromarray(merge(a,pred,m)).save(P/(key+'-clean.png'));records.append(dict(key=key,frame=n,mask='cast-support',method='registered original sprite plus original alpha and observed background',source=name,inliers=c,matrix=H.tolist()))
(P/'donors.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=U/'progress.json';j=json.loads(p.read_text(encoding='utf-8'));v=j['active_user_revision']['all_op_japanese_v3'];v.update(next='compose and review motion-aware Korean video frames',reference_donors=str(P/'donors.json'),logo_master_pending='Coordinator is revising 키: remove duplicate small ㅣ, shift cross pillar right, join left ㅋ strokes; restore leading 레 flourish. Await finalized shared master; v2 remains frozen.');p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('updated donors',len(records),flush=True)