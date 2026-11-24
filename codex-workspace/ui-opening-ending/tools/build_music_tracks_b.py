"""Three lower music tracks with disjoint source glyph regions; preserve original logo/quote."""
from pathlib import Path
import sys,json,io,numpy as np
from PIL import Image,ImageFont,ImageDraw
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
U=ROOT;O=U/'candidates/music-tracks-b-v1';assert not O.exists();assert not Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists();sys.path.insert(0,str(U.parent/'tools'));from inspect_majiro import Arc,MjoScript
base=U/'candidates/ui-trial-v17';arc=Arc(base/'fastdata.arc');blob=arc.path.read_bytes();assert sha(blob)=='a13ce9c4c4b17cebfc1ca0c20faaddbf1a91bd2880a9effb1824a63f50ccf093';payload={e['name']:blob[e['offset']:e['offset']+e['size']] for e in arc.entries}
tracks=[{'track_id':6,'source':'distortion','target':'왜곡','crop':[45,416,151,46],'left':68,'size':18},{'track_id':27,'source':'声が聴こえる〜Calling you〜','target':'목소리가 들려\n~널 부르며~','crop':[522,416,214,46],'left':533,'size':17},{'track_id':28,'source':'声が聴こえる〜Calling you〜\n(instrumental)','target':'목소리가 들려\n~널 부르며~ (연주곡)','crop':[522,465,214,46],'left':533,'size':17}]
fp=U.parent/'research/fonts/NotoSerifCJKkr-Regular.otf';cm=TTFont(fp).getBestCmap();assert all(ord(c) in cm for t in tracks for c in t['target'] if not c.isspace());sp=U.parent/'research/extracted/scenario/music.mjo';script=MjoScript.disassemble_script(io.BytesIO(sp.read_bytes()));crops={}
for i,ins in enumerate(script.instructions):
 if ins.opcode.mnemonic=='callp' and 'ffc5bc91' in ins.format_instruction() and all(v.opcode.mnemonic=='ldc.i' for v in script.instructions[i-5:i]):
  h,w,y,x,tid=[v.int_value for v in script.instructions[i-5:i]];crops[tid]=[x,y,w,h]
assert all(crops[t['track_id']]==t['crop'] for t in tracks)
for d in ['payloads','clean','layers','masks','preview']:(O/d).mkdir(parents=True,exist_ok=True)
records=[];labels=[];hashes={};finals={};positions={}
for state in ['off','on','push']:
 stem='サウンドモード_'+state;n=stem+'.rct';mn=stem+'_.rc8';rgb,rp,rc=raw_image(payload[n]);mi,mp,mc=raw_image(payload[mn]);pal=np.frombuffer(mp[20:788],np.uint8).reshape(256,3);assert np.all(pal[:,0]==pal[:,1]) and np.all(pal[:,0]==pal[:,2]);source=np.dstack([rgb,255-pal[mi,0]]);clean=source.copy();layer=Image.new('RGBA',(800,600));owned=np.zeros((600,800),bool);local=[];proof=[]
 for t in tracks:
  x,y,w,h=t['crop'];erase=[60,423,133,24] if t['track_id']==6 and state=='off' else t['crop'];ex,ey,ew,eh=erase;q=source[ey:ey+eh,ex:ex+ew];glyph=np.any(q!=[0,0,0,102],2) if state=='off' else q[:,:,3]>0;assert glyph.any() and not any([glyph[0].any(),glyph[-1].any(),glyph[:,0].any(),glyph[:,-1].any()]),(state,t['track_id'],int(glyph.sum()));clean[ey:ey+eh,ex:ex+ew][glyph]=[0,0,0,102] if state=='off' else [0,0,0,0];owned[ey:ey+eh,ex:ex+ew]|=glyph;Image.fromarray((glyph*255).astype('uint8')).save(O/'masks'/f'{state}-{t["track_id"]}.source-local.png');assert np.all(clean[ey:ey+eh,ex:ex+ew]==[0,0,0,102]) if state=='off' else not clean[ey:ey+eh,ex:ex+ew,3].any()
  fragment=Image.new('RGBA',(800,600));d=ImageDraw.Draw(fragment);fill,edge,glow={'off':((255,238,221,255),(58,36,25,230),(58,36,25,80)),'on':((232,193,148,255),(79,51,31,255),(244,165,54,220)),'push':((218,168,113,255),(137,93,46,255),(244,165,54,240))}[state]
  for li,txt in enumerate(t['target'].splitlines()):
   f=ImageFont.truetype(str(fp),t['size'] if li==0 else 11);b=f.getbbox(txt,stroke_width=2);cy=435 if t['track_id']==6 else y+(16 if li==0 else 35);pos=(t['left']-b[0],round(cy-(b[1]+b[3])/2));key=(t['track_id'],li)
   if state=='off':positions[key]=pos
   else:assert positions[key]==pos
   d.text(pos,txt,font=f,fill=fill,stroke_width=2,stroke_fill=glow);d.text(pos,txt,font=f,fill=fill,stroke_width=1,stroke_fill=edge)
  ink=np.asarray(fragment)[:,:,3]>0;yy,xx=np.nonzero(ink);ib=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];assert x<ib[0] and ib[2]<x+w and y<ib[1] and ib[3]<y+h,(state,t,ib)
  if t['track_id']==6:assert ib[3]<=447
  owned|=ink;layer.alpha_composite(fragment);v={'id':f'fastdata.arc::{n}::track-{t["track_id"]:02}','track_id':t['track_id'],'source':t['source'],'target':t['target'],'translator_model':'Codex internal','consumer_crop':t['crop'],'source_region':erase,'target_ink_bounds':ib};local.append(v);labels.append(v);proof.append({'track_id':t['track_id'],'source_glyph_pixels':int(glyph.sum()),'original_logo_and_quote_excluded':True,'off_background':[0,0,0,102],'hover_pressed_background_alpha':0})
 Image.fromarray(clean).save(O/'clean'/f'{stem}.png');assert np.array_equal(np.array(Image.open(O/'clean'/f'{stem}.png')),clean);final=np.asarray(Image.alpha_composite(Image.fromarray(clean),layer));assert np.array_equal(final[~owned],source[~owned]);rb=encode_array(final[:,:,:3],rp,rc);(O/'payloads'/n).write_bytes(rb);q,_,_=raw_image((O/'payloads'/n).read_bytes());assert np.array_equal(q,final[:,:,:3]);hashes[n]=sha(rb);lookup={int(v):i for i,v in enumerate(pal[:,0])};assert len(lookup)==256;idx=np.array([lookup[int(v)] for v in (255-final[:,:,3]).ravel()],dtype='uint8').reshape(mi.shape);mb=encode_array(idx,mp,mc);(O/'payloads'/mn).write_bytes(mb);q,p,_=raw_image((O/'payloads'/mn).read_bytes());assert np.array_equal(255-pal[q,0],final[:,:,3]) and p[20:788]==mp[20:788];hashes[mn]=sha(mb);Image.fromarray(final).save(O/'preview'/f'{stem}.png');layer.save(O/'layers'/f'{stem}.png');Image.fromarray((owned*255).astype('uint8')).save(O/'masks'/f'{stem}.owned.png');finals[state]=final;records.append({'entry':n,'mask_entry':mn,'prior_payload_sha256':sha(payload[n]),'prior_mask_sha256':sha(payload[mn]),'source_size':[800,600],'strings':local,'restoration':proof,'protected_pixel_diff_count':0,'persisted_rgba_exact':True,'palette_preserved':True})
 # Compare each changed button separately to avoid hiding the unmodified artwork between them.
 sheet=Image.new('RGBA',(214*3,46*3))
 for row,t in enumerate(tracks):
  x,y,w,h=t['crop']
  for col,v in enumerate([source,clean,final]):sheet.paste(Image.fromarray(v).crop((x,y,x+w,y+h)),(col*214,row*46))
 sheet.resize((1284,276),Image.Resampling.NEAREST).save(O/'preview'/f'{state}-source-clean-final-2x.png')
bg=Image.fromarray(np.asarray(decode('サウンドモード_背景_off.rct')[0])).convert('RGBA');normal=Image.alpha_composite(bg,Image.fromarray(finals['off']));normal.convert('RGB').save(O/'preview/music-native-normal.png')
for st in ['on','push']:
 comp=normal.copy()
 for t in tracks:
  x,y,w,h=t['crop'];comp.alpha_composite(Image.fromarray(finals[st]).crop((x,y,x+w,y+h)),(x,y))
 comp.convert('RGB').save(O/'preview'/f'music-native-{st}.png')
remaining=[7,8,14,15,16,22,23];m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':records,'output_hashes':hashes,'semantic_labels':9,'unique_tracks':3,'track_ids':[6,27,28],'remaining_track_ids':remaining,'structural_pass':True,'visual_pass':False,'runtime_pass':False,'font_sha256':sha(fp.read_bytes()),'consumer_sha256':sha(sp.read_bytes()),'actual_crops_verified':True,'script_audio_tokens_unchanged':True,'scope':'21/28 music buttons authored cumulatively. Seven source glyphs overlap protected logo/quote; navigation and quote remain pending.'};(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(U/'translation/music-tracks-b-ko.json').write_text(json.dumps({'translator_model':'Codex internal','tracks':tracks,'records':labels,'remaining_track_ids':remaining},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'tracks':3,'labels':9,'glyph_counts':{r['entry']:{v['track_id']:v['source_glyph_pixels'] for v in r['restoration']} for r in records}},ensure_ascii=False))
