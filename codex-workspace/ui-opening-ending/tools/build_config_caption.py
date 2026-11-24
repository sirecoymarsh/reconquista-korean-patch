"""Translate Config caption with an exact phase/alpha-matched original blank donor."""
from pathlib import Path
import sys,json,numpy as np
from PIL import Image,ImageFont,ImageDraw
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
sys.path.insert(0,str(ROOT.parent/'tools'));from inspect_majiro import Arc
base=ROOT/'candidates/ui-trial-v9';out=ROOT/'candidates/config-caption-raster-v1';assert not out.exists()
a=Arc(base/'fastdata.arc');raw=a.path.read_bytes();assert sha(raw)=='994dcf555ec68c30b6b51e82593fecb4f9a47bf24cc155163d736ed39c7a455b';payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries};cache={}
def effective(n):
 if n not in cache:
  image,p,c=raw_image(payload[n]);assert c==3
  if payload[n][4:8]==b'TC01':
   bn=p[22:].rstrip(b'\0').decode('cp932');bn=bn if bn.endswith('.rct') else bn+'.rct';image=image.copy();s=np.all(image==[255,0,0],2);image[s]=effective(bn)[s]
  cache[n]=image
 return cache[n]
fontpath=ROOT.parent/'research/fonts/NotoSerifCJKkr-Regular.otf';cmap=TTFont(fontpath).getBestCmap();assert all(ord(c) in cmap for c in '설정');font=ImageFont.truetype(str(fontpath),23);donor=np.asarray(decode('選択肢台.rct')[0])[81:120,356:450];x,y,w,h=64,33,94,39;records=[];hashes={}
for d in ['payloads','clean','masks','layers','preview']:(out/d).mkdir(parents=True,exist_ok=True)
for stem in ['config_off','config_on','config_push']:
 name=stem+'.rct';source=np.asarray(decode(name)[0]);current=effective(name);region=source[y:y+h,x:x+w];assert np.array_equal(current[y:y+h,x:x+w],region)
 glyph=np.any(region!=donor,axis=2);assert int(glyph.sum())==962;assert not glyph[0].any() and not glyph[-1].any() and not glyph[:,0].any() and not glyph[:,-1].any()
 alpha=255-np.asarray(decode(stem+'_.rc8')[0].convert('RGB')).astype('uint16').mean(2).astype('uint8');da=255-np.asarray(decode('選択肢台_.rc8')[0].convert('RGB')).astype('uint16').mean(2).astype('uint8');assert np.all(alpha[y:y+h,x:x+w]==255) and np.all(da[81:120,356:450]==255)
 clean=current.copy();clean[y:y+h,x:x+w][glyph]=donor[glyph];Image.fromarray(clean).save(out/'clean'/f'{stem}.png');assert np.array_equal(np.array(Image.open(out/'clean'/f'{stem}.png'))[y:y+h,x:x+w],donor)
 layer=Image.new('RGBA',(800,600));d=ImageDraw.Draw(layer);box=font.getbbox('설정',stroke_width=1);center=(107.5,53.5);d.text((round(center[0]-(box[0]+box[2])/2),round(center[1]-(box[1]+box[3])/2)),'설정',font=font,fill=(246,225,209,255),stroke_width=1,stroke_fill=(47,20,20,255))
 ink=np.array(layer)[:,:,3]>0;iy,ix=np.nonzero(ink);bounds=[int(ix.min()),int(iy.min()),int(ix.max())+1,int(iy.max())+1];assert x<=bounds[0] and bounds[2]<=x+w and y<=bounds[1] and bounds[3]<=y+h
 final=np.asarray(Image.alpha_composite(Image.fromarray(clean).convert('RGBA'),layer).convert('RGB'));owned=ink.copy();owned[y:y+h,x:x+w]|=glyph;assert np.array_equal(final[~owned],current[~owned]);assert not np.any(np.all(final==[255,0,0],2))
 _,prefix,channels=raw_image(payload[name]);b=encode_array(final,prefix,channels);(out/'payloads'/name).write_bytes(b);persisted,_,_=raw_image((out/'payloads'/name).read_bytes());assert np.array_equal(persisted,final)
 Image.fromarray(final).save(out/'preview'/f'{stem}.png');layer.save(out/'layers'/f'{stem}.png');Image.fromarray((owned*255).astype('uint8')).save(out/'masks'/f'{stem}.owned.png');Image.fromarray((glyph*255).astype('uint8')).save(out/'masks'/f'{stem}.source-local.png');hashes[name]=sha(b)
 records.append({'entry':name,'source_sha256':sha((SRC/name).read_bytes()),'prior_payload_sha256':sha(payload[name]),'output_sha256':sha(b),'strings':[{'id':f'fastdata.arc::{name}::panel-title','source':'Config','target':'설정','translator_model':'Codex internal'}],'source_region':[x,y,w,h],'source_glyph_pixels':962,'source_glyph_derivation':'Exact difference against original blank same-phase texture; known background perimeter identical and caption shadow/descender fully enclosed','clean_donor':{'entry':'選択肢台.rct','sha256':sha((SRC/'選択肢台.rct').read_bytes()),'region':[356,81,94,39],'matched_background_and_alpha':True},'protected_pixel_diff_count':0,'target_ink_bounds':bounds,'original_mask_preserved':True,'source_caption_alpha':255,'persisted_rgb_exact':True,'source_size':[800,600],'scope':'Only panel title; previously translated header and all other pixels retained'})
regions=[np.asarray(Image.open(out/'preview'/f'{s}.png'))[33:72,64:158] for s in ['config_off','config_on','config_push']];assert all(np.array_equal(regions[0],r) for r in regions[1:])
Image.fromarray(np.concatenate([source[25:77,28:205],clean[25:77,28:205],final[25:77,28:205]],axis=1)).resize((1593,156),Image.Resampling.NEAREST).save(out/'preview/source-clean-final-3x.png')
m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':records,'output_hashes':hashes,'semantic_labels':3,'font_sha256':sha(fontpath.read_bytes()),'structural_pass':True,'visual_pass':False,'runtime_review':'pending','asset_completion':'partial; all other setting labels/buttons remain pending','reused_evidence':'slot-header-raster-v1 header translation and alpha unchanged; common caption state pixels identical'};(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(ROOT/'translation/config-caption-ko.json').write_text(json.dumps({'translator_model':'Codex internal','records':[s for r in records for s in r['strings']]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'entries':3,'labels':3,'source_erased_pixels_each':962,'target_bounds':bounds},ensure_ascii=False))
