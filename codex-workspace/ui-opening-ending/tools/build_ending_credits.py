from pathlib import Path
import json,sys,numpy as np
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
U=ROOT;out=U/'candidates/ending-credits-raster-v1';assert not out.exists();auth=json.loads((U/'translation/ending-credits-ko.json').read_text(encoding='utf-8'));fontpath=U.parent/'research/fonts/NotoSansCJKkr-Regular.otf';cmap=TTFont(fontpath).getBestCmap();texts=''.join(r['target'] for r in auth['records']);assert all(ord(c) in cmap for c in texts if c not in '\n\r');base=np.asarray(Image.open(U/'evidence/op-ed-source/staffrollb-proven-clean.png'));proof=json.loads((U/'research/op-ed/staffrollb-blank-donor-study.json').read_text(encoding='utf-8'));assert not proof['uncovered_pixels'] and not any(proof['blank_disagreement_pixels_per_source'])
for d in ['payloads','clean','layers','masks','preview']:(out/d).mkdir(parents=True,exist_ok=True)
entries=[];hashes={};semantic=[]
def rgba(rgb,alpha):
 im=Image.fromarray(rgb).convert('RGBA');im.putalpha(Image.fromarray(alpha.astype('uint8'),'L'));return im
def render(rows,size):
 layer=Image.new('RGBA',size);d=ImageDraw.Draw(layer);stats=[]
 for row in rows:
  f=ImageFont.truetype(str(fontpath),row['font_size']);ls=row['target'].split('\n');slot=row['target_slot'];x0,y0,x1,y1=slot;line_h=row['font_size']+5;total=line_h*len(ls)-5;start=(y0+y1-total)/2
  lr=Image.new('RGBA',size);dr=ImageDraw.Draw(lr)
  for k,t in enumerate(ls):
   box=f.getbbox(t);width=box[2]-box[0];height=box[3]-box[1];assert width+2<=x1-x0,(row['id'],width,slot);x=round(408-width/2-box[0]);y=round(start+k*line_h+(row['font_size']-height)/2-box[1]);color=(255,0,0,255) if row['color']=='red' else (255,255,255,255);dr.text((x+1,y+1),t,font=f,fill=(0,0,0,255));dr.text((x,y),t,font=f,fill=color)
  ink=np.asarray(lr)[:,:,3]>0;yy,xx=np.nonzero(ink);assert xx.min()>=x0 and xx.max()<x1 and yy.min()>=y0 and yy.max()<y1,(row['id'],[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())],slot);assert xx.min()>0 and xx.max()<size[0]-1 and yy.min()>0 and yy.max()<size[1]-1;layer=Image.alpha_composite(layer,lr);stats.append(row|{'target_ink_bbox':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'target_containment_pass':True})
 return layer,stats
for n in sorted(set(r['asset'] for r in auth['records'])):
 rows=[r for r in auth['records'] if r['asset']==n];srcblob=(SRC/n).read_bytes();raw,prefix,c=raw_image(srcblob);source=np.asarray(decode(n)[0]);assert c==3;h,w=source.shape[:2];is_a=n=='staffrolla.rct';clean=source.copy();erased=np.zeros((h,w),bool)
 if is_a:
  assert srcblob[4:8]==b'TC00';mn='staffrolla_.rc8';mb=(SRC/mn).read_bytes();mi,mp,mc=raw_image(mb);assert mc==1;palette=np.frombuffer(mp[20:788],dtype='uint8').reshape(256,3);assert np.all(palette[:,0]==palette[:,1]) and np.all(palette[:,1]==palette[:,2]) and len(set(palette[:,0].tolist()))==256;to_index=np.empty(256,dtype='uint8');to_index[palette[:,0]]=np.arange(256,dtype='uint8');alpha=255-palette[mi,0];clean_alpha=alpha.copy()
 for r in rows:
  y0,y1=r['source_y'];region=np.zeros((h,w),bool);region[y0:y1,:]=True
  if is_a:g=region&(alpha>0);clean[g]=0;clean_alpha[g]=0
  else:g=region&np.any(source!=base,2);clean[g]=base[g]
  assert g.any();erased|=g;r['source_glyph_pixels']=int(g.sum())
 assert np.array_equal(clean[~erased],source[~erased]);cleanim=rgba(clean,clean_alpha) if is_a else Image.fromarray(clean);cleanim.save(out/'clean'/(n+'.png'));reopened=np.asarray(Image.open(out/'clean'/(n+'.png')));assert np.array_equal(reopened,np.asarray(cleanim))
 for r in rows:
  y0,y1=r['source_y'];assert (not clean_alpha[y0:y1].any()) if is_a else np.array_equal(clean[y0:y1],base[y0:y1]),r['id']
 layer,stats=render(rows,(w,h));la=np.asarray(layer);ink=la[:,:,3]>0;owned=erased|ink
 if is_a:
  final=clean.copy();final[ink]=la[:,:,:3][ink];final_alpha=clean_alpha.copy();final_alpha[ink]=la[:,:,3][ink];newmi=mi.copy();newmi[owned]=to_index[255-final_alpha[owned]];encm=encode_array(newmi,mp,mc);(out/'payloads'/mn).write_bytes(encm);rm,rmp,rc=raw_image((out/'payloads'/mn).read_bytes());assert np.array_equal(rm,newmi) and rmp[:16]==mp[:16] and rmp[20:]==mp[20:];assert np.array_equal(newmi[~owned],mi[~owned]);hashes[mn]=sha(encm);entries.append({'archive':'fastdata.arc','entry':mn,'source_sha256':sha(mb),'output_sha256':sha(encm),'source_size':[w,h],'output_size':[w,h],'palette_identity':True,'mask_changed_only_in_owned_glyphs':True,'protected_pixel_diff_count':0,'persisted_pixels_exact':True});finalim=rgba(final,final_alpha)
 else:final=np.asarray(Image.alpha_composite(Image.fromarray(clean).convert('RGBA'),layer).convert('RGB'));finalim=Image.fromarray(final)
 assert np.array_equal(final[~owned],source[~owned]);encoded=encode_array(final,prefix,c);(out/'payloads'/n).write_bytes(encoded);persist,pp,pc=raw_image((out/'payloads'/n).read_bytes());assert np.array_equal(persist,final);assert pp[:16]==prefix[:16] and pp[20:]==prefix[20:];assert encode_array(final,prefix,c)==encoded;hashes[n]=sha(encoded);layer.save(out/'layers'/(n+'.png'));Image.fromarray((erased*255).astype('uint8')).save(out/'masks'/(n+'.source-glyphs.png'));Image.fromarray((owned*255).astype('uint8')).save(out/'masks'/(n+'.owned.png'));finalim.save(out/'preview'/(n+'.png'));semantic.extend(stats)
 entries.append({'archive':'fastdata.arc','entry':n,'source_sha256':sha(srcblob),'output_sha256':sha(encoded),'source_size':[w,h],'output_size':[w,h],'source_glyph_pixels':int(erased.sum()),'protected_pixel_diff_count':0,'source_glyph_residue_pixels':0,'clean_plate_reopened':True,'persisted_pixels_exact':True,'nonpixel_metadata_preserved':True,'target_ink_bounds':[r['target_ink_bbox'] for r in stats],'strings':stats,'font_size_by_id':{r['id']:r['font_size'] for r in rows},'deterministic_encoding':True})
 if is_a:
  for label,im in [('source',rgba(source,alpha)),('clean',cleanim),('final',finalim)]:
   bg=Image.new('RGBA',(w,h),(20,20,23,255));bg=Image.alpha_composite(bg,im).convert('RGB');bg.save(out/'preview'/f'staffrolla-{label}-black.png')
  for y0 in range(0,h,900):
   parts=[Image.open(out/'preview'/f'staffrolla-{label}-black.png').crop((180,y0,640,min(h,y0+900))) for label in ['source','clean','final']];sheet=Image.new('RGB',(1380,parts[0].height));
   for j,part in enumerate(parts):sheet.paste(part,(j*460,0))
   sheet.save(out/'preview'/f'staffrolla-{y0:04d}-source-clean-final.png')
 else:
  pair=Image.new('RGB',(2400,600));pair.paste(Image.fromarray(source),(0,0));pair.paste(Image.fromarray(clean),(800,0));pair.paste(finalim,(1600,0));pair.save(out/'preview'/(n+'.comparison.png'))
bs=[out/'preview'/f'staffrollb_{i:03d}.rct.png' for i in range(1,12)];contact=Image.new('RGB',(1200,1280),(32,32,36));dd=ImageDraw.Draw(contact)
for i,p in enumerate(bs):im=Image.open(p);im=im.resize((400,300),Image.Resampling.LANCZOS);x=i%3*400;y=i//3*320;contact.paste(im,(x,y));dd.text((x+4,y+302),p.name,fill='white')
contact.save(out/'preview/staffrollb-contact.png')
m={'translator_model':'Codex internal','task_id':auth['task_id'],'archive':'fastdata.arc','entries':entries,'output_hashes':hashes,'semantic_labels':len(semantic),'raster_entries':12,'raster_masks':1,'semantic_source':'translation/ending-credits-ko.json','policy':auth['policy'],'font_path':str(fontpath),'font_sha256':sha(fontpath.read_bytes()),'structural_pass':True,'visual_pass':False,'runtime_review':'user_final_review_pending','release_pass':False,'closure':{'scroll':'staffrolla.rct + original-dimension RC8; canvas800x4664; original script and timing unchanged','slides':'all11 staffrollb_001..011; canvas800x600; original script and timing unchanged'},'clean_plate_evidence':['research/op-ed/staffrollb-blank-donor-study.json','evidence/op-ed-source/staffrollb-proven-clean.png'],'consumers':[{'file':'staffroll.mjo','sha256':sha((U.parent/'research/extracted/scenario/staffroll.mjo').read_bytes())},{'file':'last_ep.mjo','sha256':sha((U.parent/'research/extracted/scenario/last_ep.mjo').read_bytes())},{'file':'kosihata.mjo','sha256':sha((U.parent/'research/extracted/scenario/kosihata.mjo').read_bytes())}]};(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(out/'semantic-delta.json').write_text(json.dumps({'translator_model':'Codex internal','records':semantic},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'candidate':str(out),'rct':12,'rc8':1,'labels':len(semantic),'structural_pass':True,'visual_pass':False},ensure_ascii=False))
