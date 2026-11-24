"""First 18 music buttons across normal/hover/pressed; original crop graph unchanged."""
from pathlib import Path
import sys,json,io,numpy as np
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
U=ROOT;sys.path.insert(0,str(U.parent/'tools'));from inspect_majiro import Arc,MjoScript
O=U/'candidates/music-tracks-a-v1';assert not O.exists();assert not Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists()
a=Arc(U/'candidates/ui-trial-v16/fastdata.arc');blob=a.path.read_bytes();assert sha(blob)=='f7d8af1b433ce8f7d6d1a56bd377a613c26848b54e1bf3bdfeecf372cd6c152b';payload={e['name']:blob[e['offset']:e['offset']+e['size']] for e in a.entries}
rows=[185,231,278,324,372];xs=[45,193,352];lefts=[68,223,374];source_groups=[['Port Island','やわらかな日々','子鹿のステップ','Sunset city','suspicion'],['歩く速さで','朝陽のまどろみ','プロムナード','せめて良い夢を','振り返れば'],['Terror','Night Town','rainy blue','touching','結婚行進曲']];targets=[['포트 아일랜드','포근한 나날','아기 사슴의 발걸음','노을 지는 도시','의혹'],['걷는 속도로','아침 햇살 속 선잠','산책','꿈만은 좋기를','돌아보면'],['공포','밤의 거리','비 오는 날의 우울','감동','결혼 행진곡']]
tracks=[]
for col in range(3):
 for row in range(5):tracks.append({'track_id':col*8+row+1,'source':source_groups[col][row],'target':targets[col][row],'crop':[xs[col],rows[row],151,46],'left':lefts[col]})
for row,(tid,note,ko) in enumerate([(24,'shortver','짧은 버전'),(25,'fullver','전체 버전'),(26,'instrumental','연주곡')],1):tracks.append({'track_id':tid,'source':'Reconquista\n('+note+')','target':'레콘퀴스타\n('+ko+')','crop':[522,rows[row],214,46],'left':533})
# Recover actual button_set constants rather than assuming a regular grid.
sp=U.parent/'research/extracted/scenario/music.mjo';script=MjoScript.disassemble_script(io.BytesIO(sp.read_bytes()));crops={}
for i,ins in enumerate(script.instructions):
 if ins.opcode.mnemonic=='callp' and ins.format_instruction().find('ffc5bc91')>=0:
  prior=script.instructions[i-5:i]
  if all(v.opcode.mnemonic=='ldc.i' for v in prior):
   vals=[int(v.int_value) for v in prior];h,w,y,x,tid=vals;crops[tid]=[x,y,w,h]
assert all(crops[t['track_id']]==t['crop'] for t in tracks),(crops,tracks)
fp=U.parent/'research/fonts/NotoSerifCJKkr-Regular.otf';cm=TTFont(fp).getBestCmap();assert all(ord(c) in cm for t in tracks for c in t['target'] if not c.isspace())
for t in tracks:
 text=t['target'].splitlines()[0];x,y,w,h=t['crop']
 for size in range(18,13,-1):
  f=ImageFont.truetype(str(fp),size);b=f.getbbox(text,stroke_width=2)
  if b[2]-b[0]<=x+w-3-t['left']:break
 else:raise AssertionError(('Target cannot fit',t))
 t['font_size']=size
for k in ['payloads','clean','layers','masks','preview']:(O/k).mkdir(parents=True,exist_ok=True)
records=[];hashes={};finals={};sources={};cleans={};all_labels=[];positions={}
for state in ['off','on','push']:
 stem='サウンドモード_'+state;n=stem+'.rct';mn=stem+'_.rc8';rgb,p,c=raw_image(payload[n]);assert c==3 and payload[n][4:8]==b'TC00';mi,mp,mc=raw_image(payload[mn]);pal=np.frombuffer(mp[20:788],np.uint8).reshape(256,3);assert np.all(pal[:,0]==pal[:,1]) and np.all(pal[:,0]==pal[:,2]);alpha=255-pal[mi,0];source=np.dstack([rgb,alpha]);clean=source.copy();layer=Image.new('RGBA',(800,600));owned=np.zeros((600,800),bool);rec=[];per=[]
 for t in tracks:
  x,y,w,h=t['crop'];q=source[y:y+h,x:x+w]
  if state=='off':
   bg=np.array([0,0,0,102],dtype='uint8');glyph=np.any(q!=bg,2);assert np.all(q[0]==bg) and np.all(q[-1]==bg) and np.all(q[:,0]==bg) and np.all(q[:,-1]==bg);clean[y:y+h,x:x+w][glyph]=bg
  else:
   glyph=q[:,:,3]>0;assert not glyph[0].any() and not glyph[-1].any() and not glyph[:,0].any() and not glyph[:,-1].any();clean[y:y+h,x:x+w][glyph]=[0,0,0,0]
  owned[y:y+h,x:x+w]|=glyph;Image.fromarray((glyph*255).astype('uint8')).save(O/'masks'/f'{state}-track-{t["track_id"]:02}.source-local.png');assert glyph.any();fragment=Image.new('RGBA',(800,600));d=ImageDraw.Draw(fragment)
  fill,edge,glow={'off':((255,238,221,255),(58,36,25,230),(58,36,25,80)),'on':((232,193,148,255),(79,51,31,255),(244,165,54,220)),'push':((218,168,113,255),(137,93,46,255),(244,165,54,240))}[state]
  for li,text in enumerate(t['target'].splitlines()):
   sz=t['font_size'] if li==0 else 11;f=ImageFont.truetype(str(fp),sz);b=f.getbbox(text,stroke_width=2);cy=y+(21.5 if '\n' not in t['target'] else (17.5 if li==0 else 34));pos=(t['left']-b[0],round(cy-(b[1]+b[3])/2));key=(t['track_id'],li)
   if state=='off':positions[key]=pos
   else:assert positions[key]==pos
   d.text(pos,text,font=f,fill=fill,stroke_width=2,stroke_fill=glow);d.text(pos,text,font=f,fill=fill,stroke_width=1,stroke_fill=edge)
  im=np.asarray(fragment)[:,:,3]>0;yy,xx=np.nonzero(im);ib=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];assert x<ib[0] and ib[2]<x+w and y<ib[1] and ib[3]<y+h,(state,t,ib);owned|=im;layer.alpha_composite(fragment);v={'id':f'fastdata.arc::{n}::track-{t["track_id"]:02}','source':t['source'],'target':t['target'],'translator_model':'Codex internal','track_id':t['track_id'],'consumer_crop':t['crop'],'font_size':t['font_size'],'target_ink_bounds':ib};rec.append(v);all_labels.append(v);per.append({'track_id':t['track_id'],'source_glyph_pixels':int(glyph.sum()),'clean_bg_rgba':[0,0,0,102] if state=='off' else [0,0,0,0],'outside_glyph_hidden_rgb_preserved':True})
 Image.fromarray(clean).save(O/'clean'/f'{stem}.png');assert np.array_equal(np.array(Image.open(O/'clean'/f'{stem}.png')),clean)
 for t in tracks:
  x,y,w,h=t['crop'];q=clean[y:y+h,x:x+w];assert np.all(q==[0,0,0,102]) if state=='off' else not q[:,:,3].any()
 final=np.asarray(Image.alpha_composite(Image.fromarray(clean),layer));assert np.array_equal(final[~owned],source[~owned]);b=encode_array(final[:,:,:3],p,c);(O/'payloads'/n).write_bytes(b);rr,_,_=raw_image((O/'payloads'/n).read_bytes());assert np.array_equal(rr,final[:,:,:3]);hashes[n]=sha(b);lookup={int(v):i for i,v in enumerate(pal[:,0])};assert len(lookup)==256;idx=np.array([lookup[int(v)] for v in (255-final[:,:,3]).ravel()],dtype='uint8').reshape(mi.shape);b=encode_array(idx,mp,mc);(O/'payloads'/mn).write_bytes(b);ri,rp,_=raw_image((O/'payloads'/mn).read_bytes());assert np.array_equal(255-pal[ri,0],final[:,:,3]) and rp[20:788]==mp[20:788];hashes[mn]=sha(b);Image.fromarray(final).save(O/'preview'/f'{stem}.png');layer.save(O/'layers'/f'{stem}.png');Image.fromarray((owned*255).astype('uint8')).save(O/'masks'/f'{stem}.owned.png');finals[state]=final;sources[state]=source;cleans[state]=clean;records.append({'entry':n,'mask_entry':mn,'prior_payload_sha256':sha(payload[n]),'source_original_sha256':sha((SRC/n).read_bytes()),'source_size':[800,600],'restoration':per,'strings':rec,'protected_pixel_diff_count':0,'persisted_rgba_exact':True,'palette_preserved':True})
background=Image.fromarray(np.asarray(decode('サウンドモード_背景_off.rct')[0])).convert('RGBA');base=Image.alpha_composite(background,Image.fromarray(finals['off']));base.convert('RGB').save(O/'preview/music-native-normal.png');sheet=Image.new('RGB',(800*3,600));sheet.paste(base.convert('RGB'),(0,0))
for col,state in enumerate(['on','push'],1):
 comp=base.copy()
 for t in tracks:
  x,y,w,h=t['crop'];crop=Image.fromarray(finals[state]).crop((x,y,x+w,y+h));comp.alpha_composite(crop,(x,y))
 comp.convert('RGB').save(O/'preview'/f'music-native-{state}.png');sheet.paste(comp.convert('RGB'),(col*800,0))
sheet.save(O/'preview/music-three-states.png')
for state in ['off','on','push']:
 parts=[Image.fromarray(v).crop((45,185,503,418)) for v in [sources[state],cleans[state],finals[state]]];s=Image.new('RGBA',(458*3,233))
 for i,im in enumerate(parts):s.paste(im,(458*i,0))
 s.resize((2748,466),Image.Resampling.NEAREST).save(O/'preview'/f'{state}-source-clean-final-2x.png')
remaining=[6,7,8,14,15,16,22,23,27,28];m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':records,'output_hashes':hashes,'semantic_labels':54,'unique_tracks':18,'track_ids':[t['track_id'] for t in tracks],'remaining_track_ids':remaining,'structural_pass':True,'visual_pass':False,'runtime_pass':False,'font_sha256':sha(fp.read_bytes()),'consumer':{'entry':'music.mjo','source_sha256':sha(sp.read_bytes()),'buttonmenu_set_hash':'0xffc5bc91','selected_crop_function':'0x6514f86e','actual_crops_verified':True,'script_and_audio_file_tokens_unchanged':True},'state_style':'Shared baseline/scale; normal warm white, hover outlined gold, pressed darker gold. Original palette and protected source artwork retained.','scope':'18/28 tracks only; 10 lower tracks, decorative quote, navigation button remain pending.'};(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(U/'translation/music-tracks-a-ko.json').write_text(json.dumps({'translator_model':'Codex internal','task_id':m['task_id'],'tracks':tracks,'remaining_track_ids':remaining,'terminology':'Reconquista→레콘퀴스타 per shared glossary. Port Island retained as phonetic place/title; no unverified story location asserted.','records':all_labels},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'tracks':18,'labels':54,'payloads':6,'font_sizes':{t['track_id']:t['font_size'] for t in tracks}},ensure_ascii=False))
