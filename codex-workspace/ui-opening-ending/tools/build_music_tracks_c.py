"""Five music titles and shared quote; preserve original logo pixels exactly."""
from pathlib import Path
import sys,json,io,collections,cv2,numpy as np
from PIL import Image,ImageFont,ImageDraw
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
U=ROOT;O=U/'candidates/music-tracks-c-v1';assert not O.exists();assert not Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists();sys.path.insert(0,str(U.parent/'tools'));from inspect_majiro import Arc,MjoScript
base=U/'candidates/ui-trial-v18';arc=Arc(base/'fastdata.arc');blob=arc.path.read_bytes();assert sha(blob)=='26d9b28fa3b03a02f5960f87a6c94af267b0225145441387ad663025fa909e70';payload={e['name']:blob[e['offset']:e['offset']+e['size']] for e in arc.entries}
tracks=[{'track_id':7,'source':'ambivalent','target':'엇갈린 마음','crop':[45,465,151,46],'left':68,'top':476,'size':18},{'track_id':8,'source':'散りゆく紅葉','target':'흩날리는 단풍','crop':[45,512,151,46],'left':68,'top':517,'size':18},{'track_id':15,'source':'葬送曲','target':'장송곡','crop':[193,465,151,46],'left':222,'top':476,'size':18},{'track_id':16,'source':'都市伝説','target':'도시전설','crop':[193,512,151,46],'left':222,'top':517,'size':18},{'track_id':23,'source':'忘れえぬ情景','target':'잊지 못할 풍경','crop':[352,465,151,46],'left':374,'top':476,'size':18}]
qdoc=json.loads((U/'translation/staff-history-ko.json').read_text(encoding='utf-8'));quote=next(r for r in qdoc['records'] if r['id'].endswith('decorative-quote'));serif=U.parent/'research/fonts/NotoSerifCJKkr-Regular.otf';sans=U.parent/'research/fonts/NotoSansCJKkr-Regular.otf'
for fp,txt in [(serif,''.join(t['target'] for t in tracks)),(sans,quote['target'])]:
 cm=TTFont(fp).getBestCmap();assert all(ord(ch) in cm for ch in txt if not ch.isspace())
sp=U.parent/'research/extracted/scenario/music.mjo';script=MjoScript.disassemble_script(io.BytesIO(sp.read_bytes()));crops={}
for i,ins in enumerate(script.instructions):
 if ins.opcode.mnemonic=='callp' and 'ffc5bc91' in ins.format_instruction() and all(v.opcode.mnemonic=='ldc.i' for v in script.instructions[i-5:i]):
  h,w,y,x,tid=[v.int_value for v in script.instructions[i-5:i]];crops[tid]=[x,y,w,h]
assert all(crops[t['track_id']]==t['crop'] for t in tracks)
def rgba(stem):
 rgb=np.asarray(decode(stem+'.rct')[0]);a=255-np.asarray(decode(stem+'_.rc8')[0].convert('RGB'))[:,:,0];return np.dstack([rgb,a])
history=rgba('バックログ画面');original_off=rgba('サウンドモード_off');hlogo=history[460:500,35:520];logo_mask=np.zeros((600,800),bool);logo_mask[441:481,52:537]=np.any(hlogo[:,:,:3]>0,2)
# Alignment is independently exact between original history and chapter logo supports.
chapter=rgba('chapter_off_1');assert np.array_equal(np.any(hlogo[:,:,:3]>0,2),np.any(chapter[24:64,78:563,:3]>0,2))
covered=((rgba('サウンドモード_on')[:,:,3]>0)|(rgba('サウンドモード_push')[:,:,3]>0)).astype('uint8');known=cv2.dilate(covered,np.ones((5,5),np.uint8))[441:481,52:537]==0;lut=collections.defaultdict(set)
for a,b in zip(hlogo[known],original_off[441:481,52:537][known]):lut[tuple(a)].add(tuple(b))
roi=[52,472,448,84];x,y,w,h=roi;protected_tail=logo_mask[y:y+h,x:x+w];assert int(protected_tail.sum())==41
for yy,xx in zip(*np.nonzero(protected_tail)):
 gx=x+xx;gy=y+yy;assert tuple(original_off[gy,gx]) in lut[tuple(history[gy+19,gx-17])],(gx,gy)
# Only original logo pixels are retained inside the joint erasure region. No inferred logo values are written.
for d in ['payloads','clean','layers','masks','preview']:(O/d).mkdir(parents=True,exist_ok=True)
records=[];hashes={};labels=[];finals={};positions={}
for state in ['off','on','push']:
 stem='サウンドモード_'+state;n=stem+'.rct';mn=stem+'_.rc8';rgb,rp,rc=raw_image(payload[n]);mi,mp,mc=raw_image(payload[mn]);pal=np.frombuffer(mp[20:788],np.uint8).reshape(256,3);assert np.all(pal[:,0]==pal[:,1]) and np.all(pal[:,0]==pal[:,2]);source=np.dstack([rgb,255-pal[mi,0]]);clean=source.copy();owned=np.zeros((600,800),bool);layer=Image.new('RGBA',(800,600));local=[];proof=[]
 if state=='off':
  assert np.array_equal(source[y:y+h,x:x+w],original_off[y:y+h,x:x+w]);glyph=np.any(source[y:y+h,x:x+w]!=[0,0,0,102],2)&~protected_tail
  assert not glyph[-1].any() and not glyph[:,0].any() and not glyph[:,-1].any();clean[y:y+h,x:x+w][glyph]=[0,0,0,102];owned[y:y+h,x:x+w]|=glyph
  assert np.all(clean[y:y+h,x:x+w][~protected_tail]==[0,0,0,102]);assert np.array_equal(clean[logo_mask],source[logo_mask]);Image.fromarray((glyph*255).astype('uint8')).save(O/'masks/off-joint-source-local.png')
  qlayer=Image.new('RGBA',(800,600));qd=ImageDraw.Draw(qlayer);font=ImageFont.truetype(str(sans),12)
  for row,line in enumerate(quote['target'].splitlines()):
   b=font.getbbox(line);qd.text((58-b[0],486+17*row-b[1]),line,font=font,fill=(255,255,255,26))
  qink=np.asarray(qlayer)[:,:,3]>0;yy,xx=np.nonzero(qink);qb=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];assert qb[0]>=52 and qb[2]<=500 and qb[1]>=476 and qb[3]<=556;layer.alpha_composite(qlayer);owned|=qink
  qrec={'id':f'fastdata.arc::{n}::decorative-quote','source':quote['source'],'target':quote['target'],'translator_model':'Codex internal','target_ink_bounds':qb,'reused_translation':'translation/staff-history-ko.json'};local.append(qrec);labels.append(qrec)
  proof.append({'joint_source_region':roi,'source_glyph_pixels':int(glyph.sum()),'source_owned_content':'5 track titles plus entire English quote; grayscale logo support excluded','uniform_background_rgba':[0,0,0,102],'preserved_logo_tail_pixels':41,'retained_tail_matches_observed_template_codes':True,'logo_pixels_reconstructed':0,'quote_composite_peak_rgba':list(Image.alpha_composite(Image.new('RGBA',(1,1),(0,0,0,102)),Image.new('RGBA',(1,1),(255,255,255,26))).getpixel((0,0)))})
 for t in tracks:
  tx,ty,tw,th=t['crop']
  if state!='off':
   a=source[ty:ty+th,tx:tx+tw];glyph=a[:,:,3]>0;assert glyph.any() and not any([glyph[0].any(),glyph[-1].any(),glyph[:,0].any(),glyph[:,-1].any()]);clean[ty:ty+th,tx:tx+tw][glyph]=[0,0,0,0];owned[ty:ty+th,tx:tx+tw]|=glyph;assert not clean[ty:ty+th,tx:tx+tw,3].any();Image.fromarray((glyph*255).astype('uint8')).save(O/'masks'/f'{state}-{t["track_id"]}.source-local.png');proof.append({'track_id':t['track_id'],'source_glyph_pixels':int(glyph.sum()),'alpha_background':0})
  fragment=Image.new('RGBA',(800,600));d=ImageDraw.Draw(fragment);fill,edge,glow={'off':((255,238,221,255),(58,36,25,230),(58,36,25,80)),'on':((232,193,148,255),(79,51,31,255),(244,165,54,220)),'push':((218,168,113,255),(137,93,46,255),(244,165,54,240))}[state];font=ImageFont.truetype(str(serif),t['size']);b=font.getbbox(t['target'],stroke_width=2);pos=(t['left']-b[0],t['top']-b[1])
  if state=='off':positions[t['track_id']]=pos
  else:assert pos==positions[t['track_id']]
  d.text(pos,t['target'],font=font,fill=fill,stroke_width=2,stroke_fill=glow);d.text(pos,t['target'],font=font,fill=fill,stroke_width=1,stroke_fill=edge);ink=np.asarray(fragment)[:,:,3]>0;yy,xx=np.nonzero(ink);ib=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];assert tx<ib[0] and ib[2]<tx+tw and ty<ib[1] and ib[3]<ty+th,(t,ib);assert not np.any(ink&logo_mask);layer.alpha_composite(fragment);owned|=ink
  rec={'id':f'fastdata.arc::{n}::track-{t["track_id"]:02}','track_id':t['track_id'],'source':t['source'],'target':t['target'],'translator_model':'Codex internal','consumer_crop':t['crop'],'target_ink_bounds':ib};local.append(rec);labels.append(rec)
 Image.fromarray(clean).save(O/'clean'/f'{stem}.png');assert np.array_equal(np.array(Image.open(O/'clean'/f'{stem}.png')),clean);final=np.asarray(Image.alpha_composite(Image.fromarray(clean),layer));assert np.array_equal(final[~owned],source[~owned]);assert state!='off' or np.array_equal(final[logo_mask],source[logo_mask]);rb=encode_array(final[:,:,:3],rp,rc);(O/'payloads'/n).write_bytes(rb);a,p,c=raw_image((O/'payloads'/n).read_bytes());assert np.array_equal(a,final[:,:,:3]) and p==rp;hashes[n]=sha(rb);lookup={int(v):i for i,v in enumerate(pal[:,0])};assert len(lookup)==256;idx=np.array([lookup[int(v)] for v in (255-final[:,:,3]).ravel()],dtype='uint8').reshape(mi.shape);mb=encode_array(idx,mp,mc);(O/'payloads'/mn).write_bytes(mb);a,p,c=raw_image((O/'payloads'/mn).read_bytes());assert np.array_equal(255-pal[a,0],final[:,:,3]) and p[20:788]==mp[20:788];hashes[mn]=sha(mb);Image.fromarray(final).save(O/'preview'/f'{stem}.png');layer.save(O/'layers'/f'{stem}.png');Image.fromarray((owned*255).astype('uint8')).save(O/'masks'/f'{stem}.owned.png');finals[state]=final
 comp=np.concatenate([source[465:558,45:503],clean[465:558,45:503],final[465:558,45:503]],0);Image.fromarray(comp).resize((916,558),Image.Resampling.NEAREST).save(O/'preview'/f'{state}-source-clean-final-2x.png')
 records.append({'entry':n,'mask_entry':mn,'prior_payload_sha256':sha(payload[n]),'prior_mask_sha256':sha(payload[mn]),'source_size':[800,600],'strings':local,'restoration':proof,'protected_pixel_diff_count':0,'logo_diff_count':0 if state=='off' else None,'logo_scope':'Original logo is in normal base only; on/push are transparent text overlays','persisted_rgba_exact':True,'palette_preserved':True})
bg=Image.fromarray(np.asarray(decode('サウンドモード_背景_off.rct')[0])).convert('RGBA');normal=Image.alpha_composite(bg,Image.fromarray(finals['off']));normal.convert('RGB').save(O/'preview/music-native-normal.png')
for state in ['on','push']:
 comp=normal.copy()
 for t in tracks:
  x,y,w,h=t['crop'];comp.alpha_composite(Image.fromarray(finals[state]).crop((x,y,x+w,y+h)),(x,y))
 comp.convert('RGB').save(O/'preview'/f'music-native-{state}.png')
m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':records,'output_hashes':hashes,'semantic_labels':16,'unique_tracks':5,'track_ids':[7,8,15,16,23],'remaining_track_ids':[14,22],'structural_pass':True,'visual_pass':False,'runtime_pass':False,'font_hashes':{p.name:sha(p.read_bytes()) for p in [serif,sans]},'consumer_sha256':sha(sp.read_bytes()),'actual_crops_verified':True,'script_audio_tokens_unchanged':True,'scope':'26/28 music buttons cumulatively. Complete quote localized using earlier approved wording. Original logo preserved byte-for-byte; no ambiguous logo reconstruction applied. Two original titles14/22 and navigation pending.'};(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(U/'translation/music-tracks-c-ko.json').write_text(json.dumps({'translator_model':'Codex internal','tracks':tracks,'records':labels,'remaining_track_ids':[14,22]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'tracks':5,'labels':16,'bounds':{r['entry']:[v['target_ink_bounds'] for v in r['strings']] for r in records}},ensure_ascii=False))
