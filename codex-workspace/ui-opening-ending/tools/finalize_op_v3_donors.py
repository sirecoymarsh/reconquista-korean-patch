from pathlib import Path
import sys,json,shutil,numpy as np,cv2
from PIL import Image
sys.path.insert(0,'tools');from op_v3_restoration import *
from op_v3_source_art import SourceArt
S=SourceArt();G=Path('P:/AI/Codex/generated_images/01a162df-720c-77d2-96ed-6429e90b3333')
gens={'bridge':('exec-a68b53f6-d513-4429-9296-d7db4599a919.png',2058,'cast-main'),'sky':('exec-7e11845f-d5ca-4b45-bb3d-56850046d8f8.png',2082,'cast-main'),'theme':('exec-69748f18-f931-481e-bd98-cf9134a8372f.png',1698,'theme'),'city':('exec-a514e9a5-071c-42f6-9dbd-3cc881c6c202.png',2010,'cast-main'),'legs':('exec-156cc5de-0c28-4861-a51d-c85f91fb78ae.png',2124,'cast-support')}
# Complete source masks including headings and the noisy Yue name.
a=read(2124);reg=(X>=25)&(X<210)&(Y>=178)&(Y<430);core=((a.min(2)>160)|((a[:,:,0]>90)&(a[:,:,1]<60)&(a[:,:,2]<60)))&reg;m=cv2.dilate(core.astype('uint8'),np.ones((19,19),np.uint8)).astype(bool)&CLIP;Image.fromarray(m.astype('uint8')*255).save(P/'cast-support-mask.png')
a=read(2250);core=(a.min(2)>160)&(X>=25)&(X<200)&(Y>=248)&(Y<355);m=cv2.dilate(core.astype('uint8'),np.ones((19,19),np.uint8)).astype(bool)&CLIP;m|=(X>=42)&(X<157)&(Y>=279)&(Y<319);Image.fromarray(m.astype('uint8')*255).save(P/'yue-mask.png')
m=cv2.dilate(mask('movie').astype('uint8'),np.ones((9,9),np.uint8)).astype(bool)&CLIP;Image.fromarray(m.astype('uint8')*255).save(P/'movie-mask.png')
records=[]
for k,(file,n,mk) in gens.items():
 shutil.copy2(G/file,P/(k+'-generated-original.png'));don=np.array(Image.open(G/file).convert('RGB').resize((800,600),Image.Resampling.LANCZOS));a=read(n);m=mask(mk)
 # Global geometry is preserved by using generated material only inside source-owned masks.
 donor=toned(don,don,a,m,local=True);clean=merge(a,donor,m,4);Image.fromarray(clean).save(P/(k+'-clean.png'));Image.fromarray(a).save(P/(k+'-source.png'));records.append({'key':k,'frame':n,'mask':mk,'method':'masked imagegen restoration from exact source frame; original pixels outside source mask retained','generated_source':file})
# Originals whose background textures and hair are present in the game archives.
for k,n,mk,names in [('profile',2142,'cast-support',['last2.rct']),('movie-maho',2370,'movie',['ev301a1_01.rct']),('movie-kure',2430,'movie',['ev106_01.rct']),('maho-event',2205,'cast-support',['ev_304.rct','ev_309_01.rct','ev_303a1a1a.rct'])]:
 a=read(n);m=mask(mk);best=None
 for name in names:
  if name not in S.idx:continue
  ar=S.decode(name);H,c=register(ar,a,exclude=m|~CLIP)
  if H is not None and (best is None or c>best[0]):best=(c,name,ar,H)
 assert best is not None,(k,'no registered original');c,name,ar,H=best;w=warp(ar,H);pred=toned(w,w,a,m);clean=merge(a,pred,m);Image.fromarray(clean).save(P/(k+'-clean.png'));Image.fromarray(a).save(P/(k+'-source.png'));records.append({'key':k,'frame':n,'mask':mk,'method':'registered original game art with local observed lighting','source':name,'inliers':c,'matrix':H.tolist()});print(k,name,c,flush=True)
# Yue's original sprite: preserve RGB and use its separate matte for the red background.
k='yue';n=2250;a=read(n);m=mask('yue');ar=S.decode('b_yue_1_2_01.rct');H,c=register(ar,a,exclude=m|~CLIP);assert H is not None and c>20
fn,e=S.idx['b_yue_1_2_01_.rc8']
with S.arcs[fn].path.open('rb') as f:f.seek(e['offset']);b=f.read(e['size'])
from raster_codec import raw_image
ix,_,_=raw_image(b);pal=np.frombuffer(b[20:788],np.uint8).reshape(256,3);alpha=255-np.mean(pal[ix],axis=2);wa=warp(alpha.astype('float32')/255,H);wr=warp(ar,H);bg=poly_background(a,m,240);valid=CLIP&~m&(wa>.96);co=global_tone(wr,a,valid);fg=np.clip(wr.astype('float32')@co[:3]+co[3],0,255);pred=fg*wa[:,:,None]+bg*(1-wa[:,:,None]);pred=toned(pred,pred,a,m);clean=merge(a,pred,m);Image.fromarray(clean).save(P/'yue-clean.png');Image.fromarray(a).save(P/'yue-source.png');records.append({'key':'yue','frame':2250,'mask':'yue','method':'original b_yue sprite plus original RC8 alpha, observed red background/lighting','source':'slowdata.arc::b_yue_1_2_01.rct + b_yue_1_2_01_.rc8','inliers':c,'matrix':H.tolist()})
# Director text starts after the clean original source sample.
Image.fromarray(read(2598)).save(P/'director-early-clean.png');Image.fromarray(read(2598)).save(P/'director-early-source.png');records.append({'key':'director-early','frame':2598,'mask':'director','method':'untouched original frame before credit appears'})
a=read(2700);m=mask('director');tem=load(P/'director-late-temporal.png');clean=merge(a,tem,m,3);Image.fromarray(clean).save(P/'director-late-clean.png');Image.fromarray(a).save(P/'director-late-source.png');records.append({'key':'director-late','frame':2700,'mask':'director','method':'registered source-only temporal donors; zero uncovered glyph pixels'})
for k,n in [('mahoko',1164),('shiina',1350),('masaki',1500),('momiji',1644),('kureha',1920)]:records.append({'key':k,'frame':n,'mask':k,'method':'source gradient fit' if k=='masaki' else 'source-constrained masked imagegen repair of occluded illustration'})
(P/'donors.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('ready donors',len(records))