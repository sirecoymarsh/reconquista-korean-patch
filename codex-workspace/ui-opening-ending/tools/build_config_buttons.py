"""Localize seven config buttons while retaining their exact original plates and masks."""
from pathlib import Path
import sys,json,numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
sys.path.insert(0,str(ROOT.parent/'tools'));from inspect_majiro import Arc
U=ROOT;base=U/'candidates/ui-trial-v20';out=U/'candidates/config-buttons-raster-v1';assert not out.exists()
a=Arc(base/'fastdata.arc');raw=a.path.read_bytes();assert sha(raw)=='2fd4836e1fdb68c8f255299294cbf1b5e4cdb849f80a4f71e9199bc8e96d7832';payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries};cache={}
def effective(n):
 if n not in cache:
  im,p,c=raw_image(payload[n]);assert c==3
  if payload[n][4:8]==b'TC01':
   bn=p[22:].rstrip(b'\0').decode('cp932');bn=bn if bn.endswith('.rct') else bn+'.rct';im=im.copy();sentinel=np.all(im==[255,0,0],2);im[sentinel]=effective(bn)[sentinel]
  cache[n]=im
 return cache[n]
buttons=[('window',202,102,'ウィンドウ','창 모드'),('fullscreen',288,102,'フルスクリーン','전체 화면'),('read-only',202,133,'既読のみ','읽은 글만'),('all',288,133,'すべて','모두'),('font-select',522,102,'選択する','선택'),('choice-color',522,133,'色を変える','색상 변경'),('choice-keep',609,133,'そのまま','유지')]
fontpath=U.parent/'research/fonts/NotoSansCJKkr-Regular.otf';font=ImageFont.truetype(str(fontpath),14);cmap=TTFont(fontpath).getBestCmap();assert all(ord(c) in cmap for row in buttons for c in row[4]);records=[];hashes={};state_masks={};state_inks={}
for d in ['payloads','clean','layers','masks','preview']:(out/d).mkdir(parents=True,exist_ok=True)
for st,color in [('off',(161,150,145,255)),('on',(226,214,206,255)),('push',(236,216,210,255))]:
 n=f'config_{st}.rct';source=np.asarray(decode(n)[0]);current=effective(n);canonical=np.asarray(Image.open(U/f'evidence/config-button-template-v2/{st}-canonical-clean.png').convert('RGB'));alpha=255-np.asarray(decode(f'config_{st}_.rc8')[0].convert('RGB')).astype('uint16').mean(2).astype('uint8');clean=current.copy();erased=np.zeros((600,800),bool);bs=[];patches=[];source_masks=[]
 for bid,x,y,ja,ko in buttons:
  src=source[y:y+24,x:x+75];assert np.array_equal(src,current[y:y+24,x:x+75])
  if bid=='all':
   plate=src.copy();region=src[4:20,17:59];rows=src[4:20,17:18];assert np.array_equal(src[4:20,17],src[4:20,58]);rep=np.repeat(rows,42,axis=1);gm=np.any(region!=rep,2);assert int(gm.sum())==174;assert not gm[0].any() and not gm[-1].any() and not gm[:,0].any() and not gm[:,-1].any();plate[4:20,17:59][gm]=rep[gm];g=np.zeros((24,75),bool);g[4:20,17:59]=gm;method='Exact per-row original blank references x17/x58, including push-state row5 gradient boundary; only glyph pixels replaced.';proof={'row_references':[17,58],'region':[17,4,42,16]}
  else:
   delta=src.astype('int16')-canonical.astype('int16');g=delta[:,:,1]>4;yy,xx=np.nonzero(g);assert yy.min()>=5 and yy.max()<19 and xx.min()>=5 and xx.max()<72
   # Difference outside the source glyphs belongs to the original rounded frame and remains untouched.
   ring=np.asarray(Image.fromarray((g*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)))>0;roi=np.zeros((24,75),bool);roi[4:20,3:72]=True;res=np.any(delta,2)&~g&roi;assert not np.any(res&ring);assert np.all(delta[g]>=0);assert delta[:,:,1][g].min()>=8
   plate=src.copy();plate[g]=canonical[g];method='Same-phase canonical button from six original labels; all observed background values agree exactly. Twenty occluded pixels lie inside separately proven uniform row plateaus. Original frame differences outside glyph neighborhoods retained.';proof={'template':f'evidence/config-button-template-v2/{st}-canonical-clean.png','template_sha256':sha((U/f'evidence/config-button-template-v2/{st}-canonical-clean.png').read_bytes()),'audit':'reports/config-button-exact-glyph-audit.json','source_min_green_delta':int(delta[:,:,1][g].min()),'rounded_frame_pixels_retained':int(res.sum()),'frame_difference_in_glyph_neighborhood':0}
  source_masks.append(g);clean[y:y+24,x:x+75][g]=plate[g];erased[y:y+24,x:x+75]|=g;assert np.array_equal(plate[~g],src[~g]);yy,xx=np.nonzero(g);bs.append({'id':f'fastdata.arc::{n}::{bid}','source':ja,'target':ko,'translator_model':'Codex internal','button_origin':[x,y],'source_glyph_bbox':[int(xx.min()+x),int(yy.min()+y),int(xx.max()+x+1),int(yy.max()+y+1)],'source_glyph_pixels':int(g.sum()),'restoration_method':method,'background_proof':proof,'original_alpha_values':np.unique(alpha[y:y+24,x:x+75][g]).tolist()});patches.append((src.copy(),plate.copy()))
 state_masks[st]=np.stack(source_masks);assert np.array_equal(clean[~erased],current[~erased]);Image.fromarray(clean).save(out/f'clean/config_{st}.png');assert np.array_equal(np.asarray(Image.open(out/f'clean/config_{st}.png')),clean)
 layer=Image.new('RGBA',(800,600));draw=ImageDraw.Draw(layer);allink=np.zeros((600,800),bool)
 for row,record in zip(buttons,bs):
  bid,x,y,ja,ko=row;local=Image.new('RGBA',(75,24));ld=ImageDraw.Draw(local);box=font.getbbox(ko);ld.text((round(37.5-(box[0]+box[2])/2),round(12-(box[1]+box[3])/2)),ko,font=font,fill=color);ink=np.asarray(local)[:,:,3]>0;yy,xx=np.nonzero(ink);assert xx.min()>=5 and xx.max()<70 and yy.min()>=4 and yy.max()<20;record['target_ink_bbox']=[int(xx.min()+x),int(yy.min()+y),int(xx.max()+x+1),int(yy.max()+y+1)];layer.alpha_composite(local,(x,y));allink[y:y+24,x:x+75]|=ink
 state_inks[st]=allink;final=np.asarray(Image.alpha_composite(Image.fromarray(clean).convert('RGBA'),layer).convert('RGB'));owned=erased|allink;assert np.array_equal(final[~owned],current[~owned]);assert not np.any(np.all(final==[255,0,0],2));_,prefix,channels=raw_image(payload[n]);encoded=encode_array(final,prefix,channels);(out/'payloads'/n).write_bytes(encoded);persisted,_,_=raw_image((out/'payloads'/n).read_bytes());assert np.array_equal(persisted,final)
 Image.fromarray(final).save(out/f'preview/config_{st}.png');layer.save(out/f'layers/config_{st}.png');Image.fromarray((erased*255).astype('uint8')).save(out/f'masks/config_{st}.source-glyphs.png');Image.fromarray((owned*255).astype('uint8')).save(out/f'masks/config_{st}.owned.png');strips=[]
 for row,(src,plate) in zip(buttons,patches):
  _,x,y,_,_=row;strips.append(np.concatenate([src,plate,final[y:y+24,x:x+75]],1))
 Image.fromarray(np.concatenate(strips,0)).resize((675,504),Image.Resampling.NEAREST).save(out/f'preview/{st}-source-clean-final-3x.png');hashes[n]=sha(encoded);records.append({'entry':n,'source_sha256':sha((SRC/n).read_bytes()),'prior_payload_sha256':sha(payload[n]),'output_sha256':sha(encoded),'strings':bs,'protected_pixel_diff_count':0,'original_mask_preserved':True,'source_size':[800,600],'source_glyph_pixels':int(erased.sum()),'persisted_rgb_exact':True})
assert all(np.array_equal(state_masks['off'],m) for m in state_masks.values());assert all(np.array_equal(state_inks['off'],m) for m in state_inks.values())
m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':records,'output_hashes':hashes,'semantic_labels':21,'font_sha256':sha(fontpath.read_bytes()),'font_size':14,'structural_pass':True,'visual_pass':False,'runtime_review':'pending','asset_completion':'partial config; seven small red option buttons complete across off/on/push; other setting labels and navigation still pending','evidence':['reports/config-button-coherent-template.json','reports/config-button-template-v2-push.json','reports/config-button-exact-glyph-audit.json'],'state_glyph_geometry_equal':True,'target_ink_geometry_equal':True}
(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(U/'translation/config-buttons-ko.json').write_text(json.dumps({'translator_model':'Codex internal','task_id':m['task_id'],'records':[{'id':f'config-button::{bid}','source':ja,'target':ko,'origin':[x,y]} for bid,x,y,ja,ko in buttons]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'entries':3,'semantic_labels':21,'source_glyph_pixels_per_state':records[0]['source_glyph_pixels'],'output_hashes':hashes,'visual_review_pending':True},ensure_ascii=False))
