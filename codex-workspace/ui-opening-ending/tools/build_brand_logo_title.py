from pathlib import Path
import json,numpy as np,cv2
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from fontTools.ttLib import TTFont
from decode_ui import decode,SRC,sha
from raster_codec import raw_image,encode_array
U=Path.cwd();O=U/'candidates/brand-logo-ko-v1';D=U/'source/decoded'
master=Image.open(O/'master/reconquista-ko.png').convert('RGBA');bbox=master.getchannel('A').getbbox();master=master.crop(bbox)
fontp=U/'research/typography/fonts/Eulyoo1945-SemiBold.otf';font=ImageFont.truetype(str(fontp),11)
quote=['죽음과 무덤도 불못에 던져졌다.','이 불못이 곧 둘째 죽음이다.','생명책에 이름이 기록되지 않은 사람은','누구든 불못에 던져졌다.']
assert all(ord(ch) in TTFont(fontp).getBestCmap() for line in quote for ch in line)
ref=np.asarray(decode('title1_off.rct')[0]);base=np.asarray(decode('title1_null2.rct')[0]);seed=np.any(ref!=base,2);seed[400:]=False;seed[:,500:]=False
rows=[]
for v in [1,2,3]:
 donorname='title2_null2.rct' if v==2 else ('title1_null.rct' if v==3 else 'title1_null2.rct');donor=np.asarray(decode(donorname)[0]);source=np.asarray(decode(f'title{v}_off.rct')[0]);delta=np.any(source!=donor,2)
 if v<3:
  roi=np.zeros((600,800),bool);roi[70:400,40:480]=True;mask=delta&roi
  assert not (delta&cv2.dilate(roi.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)&~roi).any()
  shiftx,shifty=0,0
 else:
  shifted=np.zeros((600,800),bool);shifted[:518,332:]=seed[82:,:468]
  n,lab,stats,cen=cv2.connectedComponentsWithStats(delta.astype('uint8'),8);ids=[int(k) for k in np.unique(lab[shifted&delta]) if k]
  assert all(stats[k,0]>=380 and stats[k,0]+stats[k,2]<=780 and stats[k,1]+stats[k,3]<=310 for k in ids),[(k,stats[k].tolist()) for k in ids]
  mask=np.isin(lab,ids);shiftx,shifty=332,-82
  assert int(mask.sum())>30000
 # Preserve the credited Roman identity strip from original source, but replace the full old Japanese lettering and tiny English verse.
 roman=np.zeros((600,800),bool);roman[322+shifty:338+shifty,98+shiftx:278+shiftx]=True;roman &= mask
 # Base layer is exact original donor plus every protected pixel of the prior Korean menu candidate.
 layer=Image.new('RGBA',(800,600));logo=master.resize((390,round(master.height*390/master.width)),Image.Resampling.LANCZOS)
 x,y=51+shiftx,82+shifty
 # Consistent source crimson and only original-like restrained lower-right shadow.
 alpha=logo.getchannel('A');solid=Image.new('RGBA',logo.size,(206,21,60,0));solid.putalpha(alpha)
 shadow=Image.new('RGBA',(800,600));shadowalpha=Image.new('L',(800,600));shadowalpha.paste(alpha,(x+2,y+3));shadowalpha=shadowalpha.filter(ImageFilter.GaussianBlur(.65));shadow=Image.new('RGBA',(800,600),(40,25,34,0));shadow.putalpha(shadowalpha.point(lambda n:round(n*.65)));layer=Image.alpha_composite(layer,shadow);layer.alpha_composite(solid,(x,y))
 qlayer=Image.new('RGBA',(800,600));qd=ImageDraw.Draw(qlayer)
 for i,line in enumerate(quote):
  b=font.getbbox(line);px=101+shiftx-b[0];py=341+shifty+i*12-b[1];qd.text((px+1,py+1),line,font=font,fill=(14,15,25,210));qd.text((px,py),line,font=font,fill=(255,255,255,255),stroke_width=0)
 layer=Image.alpha_composite(layer,qlayer);ink=np.asarray(layer)[:,:,3]>0
 slot=np.zeros((600,800),bool);slot[max(0,78+shifty):397+shifty,46+shiftx:449+shiftx]=True;assert not (ink&~slot).any()
 for state in ['off','on','push']:
  name=f'title{v}_{state}.rct';prior=U/'candidates/title-menu-v1/payloads'/name;pb=prior.read_bytes();priorarr,pre,c=raw_image(pb);assert c==3
  if pb[4:8]==b'TC01':
   base_name=pre[22:].rstrip(b'\0').decode('cp932');fallback=np.asarray(decode(base_name if base_name.endswith('.rct') else base_name+'.rct')[0]);skip=np.all(priorarr==[255,0,0],2);priorarr[skip]=fallback[skip]
  assert np.array_equal(priorarr,np.asarray(Image.open(U/'candidates/title-menu-v1/preview'/(name+'.png'))))
  orig=np.asarray(decode(name)[0]);assert np.array_equal(orig[mask],source[mask]);clean=priorarr.copy();erase=mask&~roman;clean[erase]=donor[erase]
  assert np.array_equal(clean[erase],donor[erase]);assert np.array_equal(clean[roman],orig[roman])
  final=np.asarray(Image.alpha_composite(Image.fromarray(clean).convert('RGBA'),layer).convert('RGB'));owned=erase|ink;assert np.array_equal(final[~owned],priorarr[~owned])
  # Original Roman subline must remain untouched by the new wordmark.
  assert not (ink&roman).any();assert np.array_equal(final[roman],orig[roman])
  cleanim=Image.fromarray(clean);cleanim.save(O/'clean'/(name+'.png'));assert np.array_equal(np.asarray(Image.open(O/'clean'/(name+'.png'))),clean)
  Image.fromarray((erase*255).astype('uint8')).save(O/'masks'/(name+'.source-glyphs.png'));Image.fromarray((owned*255).astype('uint8')).save(O/'masks'/(name+'.owned.png'));layer.save(O/'layers'/(name+'.png'))
  encoded=encode_array(final,pre,c);(O/'payloads'/name).write_bytes(encoded);persist,pr,pc=raw_image((O/'payloads'/name).read_bytes());assert np.array_equal(persist,final);assert pr[:16]==pre[:16] and pr[20:]==pre[20:];assert encode_array(final,pre,c)==encoded
  Image.fromarray(persist).save(O/'preview'/(name+'.png'))
  yy,xx=np.nonzero(ink);rows.append({'archive':'fastdata.arc','entry':name,'source_sha256':sha((SRC/name).read_bytes()),'base_candidate_sha256':sha(pb),'output_sha256':sha(encoded),'donor':donorname,'donor_sha256':sha((SRC/donorname).read_bytes()),'source_size':[800,600],'output_size':[800,600],'source_erase_pixels':int(erase.sum()),'preserved_roman_pixels':int(roman.sum()),'protected_pixel_diff_count':0,'source_logo_residue_pixels':0,'target_ink_bounds':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'structural_pass':True,'visual_pass':False,'runtime_review':'user_pending','metadata_preserved':True,'deterministic_encoding':True})
 # Native source-clean-final contact of logo area only, preview margins never enter payloads.
 if v in [1,3]:
  rect=(40+shiftx,max(0,74+shifty),470+shiftx,403+shifty);parts=[Image.fromarray(source).crop(rect),Image.open(O/'clean'/f'title{v}_off.rct.png').crop(rect),Image.open(O/'preview'/f'title{v}_off.rct.png').crop(rect)];contact=Image.new('RGB',(parts[0].width*3,parts[0].height))
  for j,part in enumerate(parts):contact.paste(part,(j*part.width,0))
  contact.save(O/'preview'/f'title{v}-source-clean-final.png')
manifest={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','status':'structural_pass_visual_review_pending','exact_logo_text':'레콘키스타','semantic_fields':5,'quote_lines':quote,'original_roman_identity_preserved':True,'master':'master/reconquista-ko.png','master_sha256':sha((O/'master/reconquista-ko.png').read_bytes()),'entries':rows,'font_file':str(fontp),'font_sha256':sha(fontp.read_bytes()),'font_redistributed':False,'retains_prior_title_menu_Korean':True,'state_closure':'All3 title designs x off/on/push =9 entries; logo and quote invariant by hover state.','runtime_review':'user_pending','opening_video':'separate candidate in progress'}
(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'entries':len(rows),'candidate':str(O),'status':manifest['status']},ensure_ascii=False))
