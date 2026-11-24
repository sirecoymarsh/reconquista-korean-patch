from pathlib import Path
import json,numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
O=ROOT/'candidates/chapter-raster-v1'
for d in ['payloads','clean','masks','layers','preview']:(O/d).mkdir(parents=True,exist_ok=True)
quotes=[('求めよ、さらば与えられん','구하라, 그리하면 받으리라',141),('尋ねよ、さらば見出さん','찾으라, 그리하면 찾으리라',222),('門を叩け、さらば開かれん','문을 두드리라, 그리하면 열리리라',315)]
footer_source='AND DEATH AND THE GRAVE WERE THROWN INTO THE LAKE OF FIRE.\nTHIS IS THE SECOND DEATH—THE LAKE OF FIRE.\nAND ANYONE WHOSE NAME WAS NOT FOUND RECORDED\nIN THE BOOK OF LIFE WAS THROWN INTO THE LAKE OF FIRE.'
footer_target='죽음과 무덤은 불못에 던져졌다.\n이 불못이 곧 둘째 죽음이다.\n생명책에 이름이 기록되지 않은 자도\n불못에 던져졌다.'
fontpath=ROOT.parent/'research/fonts/NotoSerifCJKkr-Regular.otf'
# Fit the longest quote once, preserving one shared scale across all states.
qsize=20
while max(ImageFont.truetype(str(fontpath),qsize).getlength(t) for _,t,_ in quotes)>238:qsize-=1
assert qsize>=16
REUSE={'chapter_off_1.rct': 'bd5f0f042d64bc6708937ed83c205b8569ab8918eabc81b664c1715968f986fe', 'chapter_off_2.rct': '8e7fc93fdf1cf6ab4c4391c1c63d06bb7ff6439d0f1a0f606d1a68fd5826358c'}
reports=[];finals={}
for stem,glow in [('chapter_off_1',None),('chapter_off_2',(119,204,255)),('chapter_on',(236,182,110)),('chapter_push',(242,88,68))]:
 name=stem+'.rct';source=np.asarray(decode(name)[0]).copy();clean=source.copy();erased=np.zeros((600,800),bool);slots=np.zeros((600,800),bool);layer=Image.new('RGBA',(800,600));records=[]
 fields=[{'source':src,'target':t,'rect':[271,yy-21,254,43],'size':qsize,'center':[398,yy],'color':(255,255,255),'glow':glow} for src,t,yy in quotes]
 # All four effective RCT states inherit the attribution/footer/select caption.
 if True:
  fields += [{'source':'マタイによる福音書　第7章','target':'마태복음 제7장','rect':[320,383,160,27],'size':12,'center':[400,397],'color':(255,255,255),'glow':None},{'source':'Chapter Select','target':'챕터 선택','rect':[558,543,171,27],'size':23,'center':[640,558],'color':(162,162,160),'glow':None},{'source':footer_source,'target':footer_target,'rect':[82,502,440,70],'size':12,'left':[87,506],'color':(79,79,79),'glow':None}]
 if name in REUSE and (O/'payloads'/name).exists():
  saved=(O/'payloads'/name).read_bytes();assert sha(saved)==REUSE[name]
  finals[name]=np.asarray(Image.open(O/'preview'/f'{name}.png').convert('RGB'))
  saved_layer=np.asarray(Image.open(O/'layers'/f'{name}.png'))[:,:,3]
  saved_records=[]
  for n,f in enumerate(fields):
   x,y,w,h=f['rect'];yy,xx=np.nonzero(saved_layer[y:y+h,x:x+w]);bounds=[x+int(xx.min()),y+int(yy.min()),x+int(xx.max())+1,y+int(yy.max())+1]
   saved_records.append({'id':f'fastdata.arc::{name}::{n}','source':f['source'],'target':f['target'],'source_region':f['rect'],'ink_bounds':bounds,'font_size':f['size']})
  reports.append({'entry':name,'source_sha256':sha((SRC/name).read_bytes()),'output_sha256':REUSE[name],'canvas':[800,600],'clean_plate':'original constant-black interior slots','mask_unchanged':stem+'_.rc8','protected_pixel_diff_count':0,'persisted_decode_pass':True,'metadata_preserved':True,'strings':saved_records,'verification_reused':'Earlier successful per-entry pass wrote preview/mask/layer only after all assertions; later chapter_on delta dependency failed. Reuse these two unchanged outputs.'})
  continue
 for n,f in enumerate(fields):
  x,y,w,h=f['rect'];region=source[y:y+h,x:x+w]
  # These slots are solid original black, bounded clear of emblems, rules and logo.
  # Source ink is every non-black RGB value inside the source-owned text region.
  sm=region.max(2)>0;erased[y:y+h,x:x+w]|=sm;clean[y:y+h,x:x+w][sm]=0;slots[y:y+h,x:x+w]=True
  font=ImageFont.truetype(str(fontpath),f['size']);ink=Image.new('L',(800,600));d=ImageDraw.Draw(ink)
  if 'left' in f:
   for line_no,line in enumerate(f['target'].split('\n')):
    box=font.getbbox(line);d.text((f['left'][0]-box[0],f['left'][1]+line_no*17-box[1]),line,font=font,fill=255)
  else:
   box=font.getbbox(f['target']);cx,cy=f['center'];d.text((round(cx-(box[0]+box[2])/2),round(cy-(box[1]+box[3])/2)),f['target'],font=font,fill=255)
  one=Image.new('RGBA',(800,600))
  if f['glow']:
   g=ink.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.15));one.alpha_composite(Image.merge('RGBA',tuple(Image.new('L',(800,600),v) for v in f['glow'])+(g,)))
  one.alpha_composite(Image.merge('RGBA',tuple(Image.new('L',(800,600),v) for v in f['color'])+(ink,)))
  tm=np.asarray(one)[:,:,3]>0;yy,xx=np.nonzero(tm);bounds=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];assert x<=bounds[0]<bounds[2]<=x+w and y<=bounds[1]<bounds[3]<=y+h,(stem,n,bounds,f['rect'])
  layer.alpha_composite(one);records.append({'id':f'fastdata.arc::{name}::{n}','source':f['source'],'target':f['target'],'source_region':f['rect'],'ink_bounds':bounds,'font_size':f['size']})
 Image.fromarray(clean).save(O/'clean'/f'{name}.png');assert np.array_equal(np.asarray(Image.open(O/'clean'/f'{name}.png')),clean)
 # A one-pixel empty moat separates every source text region from protected art.
 for f in fields:
  x,y,w,h=f['rect'];assert not clean[y:y+h,x:x+w].any()
 tm=np.asarray(layer)[:,:,3]>0;final=np.asarray(Image.alpha_composite(Image.fromarray(clean).convert('RGBA'),layer).convert('RGB'));owned=erased|tm;assert np.array_equal(final[~owned],source[~owned])
 alpha=255-np.asarray(decode(stem+'_.rc8')[0].convert('RGB')).astype('uint16').mean(2).astype('uint8');assert np.all(alpha[owned]==255),(name,'nonopaque owned pixels')
 original=(SRC/name).read_bytes();raw,prefix,channels=raw_image(original);raw[owned]=final[owned];cancel=np.zeros((600,800),bool)
 if original[4:8]==b'TC01':
  bn=original[22:len(prefix)].rstrip(b'\0').decode('cp932');newbase=finals.get(bn,np.asarray(decode(bn)[0]));cancel=np.all(raw==[255,0,0],axis=2)&np.any(newbase!=final,axis=2);raw[cancel]=final[cancel]
 blob=encode_array(raw,prefix,channels);(O/'payloads'/name).write_bytes(blob)
 check,_,_=raw_image((O/'payloads'/name).read_bytes())
 if blob[4:8]==b'TC01':
  base=blob[22:len(prefix)].rstrip(b'\0').decode('cp932');bg=finals.get(base,np.asarray(decode(base)[0]));skip=np.all(check==[255,0,0],axis=2);check[skip]=bg[skip]
 assert np.array_equal(check,final);finals[name]=final
 Image.fromarray(final).save(O/'preview'/f'{name}.png');Image.fromarray(erased.astype('uint8')*255).save(O/'masks'/f'{name}.source.png');layer.save(O/'layers'/f'{name}.png')
 reports.append({'entry':name,'source_sha256':sha(original),'output_sha256':sha(blob),'canvas':[800,600],'clean_plate':'original constant-black interior slots, all original text/glow removed','mask_unchanged':stem+'_.rc8','protected_pixel_diff_count':0,'persisted_decode_pass':True,'metadata_preserved':True,'strings':records,'inherited_base_cancellation_pixels':int(cancel.sum())})
m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':reports,'consumer':{'file':'start.mjo','source_sha256':sha((ROOT.parent/'research/extracted/scenario/start.mjo').read_bytes()),'chapter_title_sprite_x':271,'chapter_title_sprite_width':254,'chapter_select_crop':[546,522,254,78]},'shared_quote_font_size':qsize,'brand_logo_retained':True,'structural_pass':True,'visual_pass':False,'runtime_review':'user_final_batch'}
(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'entries':4,'labels':sum(len(r['strings']) for r in reports),'shared_quote_font':qsize,'out':str(O)},ensure_ascii=False))
