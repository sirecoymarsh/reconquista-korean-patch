"""Source-backed chronicle caption and transparent weekday atlas localization."""
from pathlib import Path
import sys,json,numpy as np
from PIL import Image,ImageFont,ImageDraw
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
U=ROOT;O=U/'candidates/chronicle-calendar-raster-v1';assert not O.exists()
for d in ['payloads','clean','layers','masks','preview']:(O/d).mkdir(parents=True,exist_ok=True)
records=[];hashes={};labels=[];serif=U.parent/'research/fonts/NotoSerifCJKkr-Regular.otf';sans=U.parent/'research/fonts/NotoSansCJKkr-Regular.otf'
assert all(ord(c) in TTFont(serif).getBestCmap() for c in '연표');assert all(ord(c) in TTFont(sans).getBestCmap() for c in '일월화수목금토')
def bbox(mask):
 y,x=np.nonzero(mask);return [int(x.min()),int(y.min()),int(x.max())+1,int(y.max())+1]
def put_payload(name,arr):
 _,p,c=raw_image((SRC/name).read_bytes());blob=encode_array(arr,p,c);dest=O/'payloads'/name;dest.write_bytes(blob);q,qpre,qc=raw_image(dest.read_bytes());assert np.array_equal(arr,q) and qpre==p[:16]+qpre[16:20]+p[20:] and c==qc;hashes[name]=sha(blob)
font=ImageFont.truetype(str(serif),21)
for stem in ['クロニクル枠_null','クロニクル枠_off','クロニクル枠_on']:
 n=stem+'.rct';source=np.asarray(decode(n)[0]);alpha=255-np.asarray(decode(stem+'_.rc8')[0].convert('RGB'))[:,:,0];roi=source[31:58,148:301];glyph=np.any(roi!=0,2);assert int(glyph.sum())==1031 and not any([glyph[0].any(),glyph[-1].any(),glyph[:,0].any(),glyph[:,-1].any()]);assert np.all(alpha[31:58,148:301]==255)
 owned=np.zeros((600,800),bool);owned[31:58,148:301]=glyph;clean=source.copy();clean[owned]=0;assert not clean[31:58,148:301].any();Image.fromarray(clean).save(O/'clean'/f'{stem}.png');layer=Image.new('RGBA',(800,600));draw=ImageDraw.Draw(layer);b=font.getbbox('연표');draw.text((round(225-(b[0]+b[2])/2),round(44-(b[1]+b[3])/2)),'연표',font=font,fill=(255,255,255,255));ink=np.array(layer)[:,:,3]>0;ib=bbox(ink);assert 148<=ib[0] and ib[2]<=301 and 31<=ib[1] and ib[3]<=58;owned|=ink;final=np.asarray(Image.alpha_composite(Image.fromarray(clean).convert('RGBA'),layer).convert('RGB'));assert np.array_equal(final[~owned],source[~owned]);assert not np.any(np.all(final==[255,0,0],2));put_payload(n,final);layer.save(O/'layers'/f'{stem}.png');Image.fromarray((owned*255).astype('uint8')).save(O/'masks'/f'{stem}.png');Image.fromarray(final).save(O/'preview'/f'{stem}.png');record={'id':f'fastdata.arc::{n}::caption','source':'CHRONICLE','target':'연표','translator_model':'Codex internal'};labels.append(record);records.append({'entry':n,'source_sha256':sha((SRC/n).read_bytes()),'output_sha256':hashes[n],'source_region':[148,31,153,27],'source_glyph_pixels':1031,'source_ink_bounds':[152,35,298,53],'target_ink_bounds':ib,'clean_plate':'Uniform original black opaque background, verified empty perimeter; exact glyph mask excludes ivy and rules','protected_pixel_diff_count':0,'mask_payload_unchanged':True,'strings':[record]})
Image.fromarray(np.concatenate([source[25:62,140:310],clean[25:62,140:310],final[25:62,140:310]],1)).resize((1530,111),Image.Resampling.NEAREST).save(O/'preview/chronicle-source-clean-final-3x.png')
# Both atlas rows use the same geometry. Preserve all digits, punctuation and every unrelated pixel.
stem='小カレンダーフォント';n=stem+'.rct';mn=stem+'_.rc8';rgb=np.asarray(decode(n)[0]);mask,p,c=raw_image((SRC/mn).read_bytes());assert c==1 and np.array_equal(np.frombuffer(p[20:788],np.uint8).reshape(256,3),np.repeat(np.arange(256,dtype=np.uint8)[:,None],3,axis=1));alpha=255-mask;cleanrgb=rgb.copy();cleana=alpha.copy();sourceink=np.zeros(alpha.shape,bool)
for y in [2,65]:sourceink[y:y+28,:288]=alpha[y:y+28,:288]>0
assert int(sourceink.sum())==3912;cleanrgb[sourceink]=255;cleana[sourceink]=0;assert not cleana[2:30,:288].any() and not cleana[65:93,:288].any()
Image.fromarray(cleanrgb).save(O/'clean'/f'{stem}.rgb.png');Image.fromarray(cleana).save(O/'clean'/f'{stem}.alpha.png');font=ImageFont.truetype(str(sans),19);fa=cleana.copy();fr=cleanrgb.copy();targetink=np.zeros(alpha.shape,bool);layer=Image.new('RGBA',(800,600));bounds=[];centers=[22,66,107,148.5,190.5,227,264.5];sources=['SUN','MON','TUE','WED','THU','FRI','SAT'];targets=list('일월화수목금토')
for row,(y,color) in enumerate([(2,(252,27,27)),(65,(225,239,245))]):
 region=rgb[y:y+28,:288];aa=alpha[y:y+28,:288];assert np.all(region[aa>0]==color)
 for day,(cx,jp,ko) in enumerate(zip(centers,sources,targets)):
  al=Image.new('L',(800,600));dr=ImageDraw.Draw(al);b=font.getbbox(ko);dr.text((round(cx-(b[0]+b[2])/2),round(y+14-(b[1]+b[3])/2)),ko,font=font,fill=255);a=(np.round(np.asarray(al).astype('float32')/17)*17).astype('uint8');im=a>0;ib=bbox(im);assert y<=ib[1] and ib[3]<=y+28;fr[im]=color;fa[im]=a[im];targetink|=im;paint=Image.new('RGBA',(800,600),color+(0,));paint.putalpha(Image.fromarray(a));layer=Image.alpha_composite(layer,paint)
  if day>=3:
   cropx=[129,171,208,244][day-3];assert cropx<=ib[0] and ib[2]<=cropx+40
  record={'id':f'fastdata.arc::{n}::palette{row}::{jp}','source':jp,'target':ko,'translator_model':'Codex internal','target_ink_bounds':ib};labels.append(record);bounds.append(record)
owned=sourceink|targetink;assert np.array_equal(fr[~owned],rgb[~owned]) and np.array_equal(fa[~owned],alpha[~owned]);put_payload(n,fr);put_payload(mn,255-fa);layer.save(O/'layers'/f'{stem}.png');Image.fromarray((sourceink*255).astype('uint8')).save(O/'masks'/f'{stem}.source.png');Image.fromarray((owned*255).astype('uint8')).save(O/'masks'/f'{stem}.owned.png')
def preview(rr,aa):
 im=Image.fromarray(rr).convert('RGBA');im.putalpha(Image.fromarray(aa));return Image.alpha_composite(Image.new('RGBA',(800,600),(35,41,50,255)),im).convert('RGB')
preview(fr,fa).save(O/'preview'/f'{stem}.png');sheet=Image.new('RGB',(288*3,134*9));
for k,(rr,aa) in enumerate([(rgb,alpha),(cleanrgb,cleana),(fr,fa)]):sheet.paste(preview(rr,aa).crop((0,0,288,134)).resize((864,402),Image.Resampling.NEAREST),(0,402*k))
sheet.save(O/'preview/calendar-source-clean-final.png')
records.append({'entry':n,'mask_entry':mn,'source_sha256':sha((SRC/n).read_bytes()),'source_mask_sha256':sha((SRC/mn).read_bytes()),'output_sha256':hashes[n],'output_mask_sha256':hashes[mn],'source_glyph_pixels':3912,'source_regions':[[0,2,288,28],[0,65,288,28]],'clean_plate':'Original transparent text-only atlas: restore alpha0 and neutral white RGB only at complete source glyph mask; hidden original pixels elsewhere preserved','palette_preserved':True,'alpha_quantization':17,'protected_pixel_diff_count':0,'digit_rows_unchanged':True,'consumer':{'script':'sightchange.mjo','sheet_crop':[0,0,288,134],'weekday_slots_x':[129,171,208,244],'weekday_rows_y':[2,65],'weekday_crop_size':[40,28],'instruction_indices':[1984,1986,1988,1990,1996,1998,2005,2006,2010,2173,2174,2177,2178],'first_three_weekdays':'Original atlas words translated in their native slots; not found in current day1–4 consumer switch'},'strings':bounds})
m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':records,'output_hashes':hashes,'semantic_labels':17,'structural_pass':True,'visual_pass':False,'runtime_pass':False,'remaining_surface_scope':'Other chronicle raster buttons, nameplates and date/name corner labels remain untranslated; day badges remain pending.'};(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(U/'translation/chronicle-calendar-ko.json').write_text(json.dumps({'translator_model':'Codex internal','records':labels},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'rct':4,'rc8':1,'labels':17,'source_caption_pixels':1031,'calendar_erased_pixels':3912},ensure_ascii=False))
