"""Localize two Staffroom titles and the history footer using exact original row templates."""
from pathlib import Path
import sys,json,datetime,numpy as np
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
U=ROOT;sys.path.insert(0,str(U.parent/'tools'));from inspect_majiro import Arc
O=U/'candidates/staff-history-raster-v1';assert not O.exists()
a=Arc(U/'candidates/ui-trial-v14/fastdata.arc');blob=a.path.read_bytes();assert sha(blob)=='0770acd3b2582ddbeee9938ed9fff090f7342c3d200ce08501a13b2914d43a47';payload={e['name']:blob[e['offset']:e['offset']+e['size']] for e in a.entries}
serif=U.parent/'research/fonts/NotoSerifCJKkr-Regular.otf';sans=U.parent/'research/fonts/NotoSansCJKkr-Regular.otf'
quote_source='And death and the grave were thrown into the lake of fire.\nThis is the second death—the lake of fire.\nAnd anyone whose name was not found recorded\nin the Book of Life was thrown into the lake of fire.'
quote_target='죽음과 무덤도 불못에 던져졌다.\n이 불못이 곧 둘째 죽음이다.\n생명책에 이름이 기록되지 않은 사람은\n누구든 불못에 던져졌다.'
for fp,txt in [(serif,'스태프룸'),(sans,quote_target)]:
 cm=TTFont(fp).getBestCmap();assert all(ord(c) in cm for c in txt if not c.isspace())
for d in ['payloads','clean','layers','masks','preview']:(O/d).mkdir(parents=True,exist_ok=True)
records=[];hashes={};finals={}
for stem in ['staffroom_off','staffroom_on','バックログ画面']:
 n=stem+'.rct';source_rgb=np.asarray(decode(n)[0]);assert sha((SRC/n).read_bytes())==sha(payload[n]);maskn=stem+'_.rc8';hasmask=maskn in payload
 alpha=255-np.asarray(decode(maskn)[0].convert('RGB'))[:,:,0] if hasmask else np.full((600,800),255,dtype='uint8');source=np.dstack([source_rgb,alpha]);clean=source.copy();layer=Image.new('RGBA',(800,600));d=ImageDraw.Draw(layer)
 if stem.startswith('staffroom'):
  assert not hasmask;x,y,w,h=16,3,262,55;refs=source[y:y+h,[540,550,560]];assert np.all(refs==refs[:,:1]);bg=np.repeat(refs[:,1:2],w,1);source_text='Staffroom';target='스태프룸';font=ImageFont.truetype(str(serif),44);stroke=1;box=font.getbbox(target,stroke_width=stroke);px=26-box[0];py=12-box[1]
  redpx=source_rgb[y:y+h,x:x+w];redmask=(redpx[:,:,0]>100)&(redpx[:,:,1]<30)&(redpx[:,:,2]<100);red=tuple(np.median(redpx[redmask],axis=0).round().astype(int).tolist());d.text((px,py),target[0],font=font,fill=red+(255,),stroke_width=stroke,stroke_fill=red+(255,));d.text((px+font.getlength(target[0]),py),target[1:],font=font,fill=(255,255,255,255),stroke_width=stroke,stroke_fill=(255,255,255,255));tag='panel-title';expected=4381;donor={'reference_xs':[540,550,560],'same_row_pixels_identical':True,'striped_header_original_rows':bg[:,0,:].tolist()}
 else:
  assert hasmask;x,y,w,h=28,500,550,73;refs=source[y:y+h,[580,600,620]];assert np.all(refs==refs[:,:1]) and np.all(refs==[0,0,0,165]);bg=np.repeat(refs[:,1:2],w,1);source_text=quote_source;target=quote_target;font=ImageFont.truetype(str(sans),12)
  for row,line in enumerate(target.splitlines()):
   b=font.getbbox(line);d.text((41-b[0],505+16*row-b[1]),line,font=font,fill=(145,145,145,108))
  tag='decorative-quote';expected=9002;donor={'reference_xs':[580,600,620],'same_row_pixels_identical':True,'rgba':[0,0,0,165],'glyph_style':'Foreground145/alpha108 composites onto original background to RGB77/alpha203, matching source peak.'}
 glyph=np.any(source[y:y+h,x:x+w]!=bg,2);assert int(glyph.sum())==expected;assert not any([glyph[0].any(),glyph[-1].any(),glyph[:,0].any(),glyph[:,-1].any()]);clean[y:y+h,x:x+w][glyph]=bg[glyph];Image.fromarray(clean).save(O/'clean'/f'{stem}.png');assert np.array_equal(np.array(Image.open(O/'clean'/f'{stem}.png'))[y:y+h,x:x+w],bg)
 ink=np.asarray(layer)[:,:,3]>0;yy,xx=np.nonzero(ink);ib=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];assert x<=ib[0] and ib[2]<=x+w and y<=ib[1] and ib[3]<=y+h,(stem,ib)
 owned=ink.copy();owned[y:y+h,x:x+w]|=glyph;final=np.asarray(Image.alpha_composite(Image.fromarray(clean),layer));assert np.array_equal(final[~owned],source[~owned]);assert not np.any(np.all(final[:,:,:3]==[255,0,0],2));_,p,c=raw_image(payload[n]);data=encode_array(final[:,:,:3],p,c);(O/'payloads'/n).write_bytes(data);check,_,_=raw_image((O/'payloads'/n).read_bytes());assert np.array_equal(check,final[:,:,:3]);hashes[n]=sha(data)
 if hasmask:
  old,mp,mc=raw_image(payload[maskn]);pal=np.frombuffer(mp[20:788],dtype='uint8').reshape(256,3);assert np.all(pal[:,0]==pal[:,1]) and np.all(pal[:,0]==pal[:,2]);lookup={int(v):i for i,v in enumerate(pal[:,0])};assert len(lookup)==256;idx=np.array([lookup[int(v)] for v in (255-final[:,:,3]).ravel()],dtype='uint8').reshape(old.shape);b=encode_array(idx,mp,mc);(O/'payloads'/maskn).write_bytes(b);ri,rp,rc=raw_image((O/'payloads'/maskn).read_bytes());assert np.array_equal(255-pal[ri,0],final[:,:,3]) and rp[20:788]==mp[20:788];hashes[maskn]=sha(b)
 layer.save(O/'layers'/f'{stem}.png');Image.fromarray((owned*255).astype('uint8')).save(O/'masks'/f'{stem}.owned.png');Image.fromarray((glyph*255).astype('uint8')).save(O/'masks'/f'{stem}.source-local.png');Image.fromarray(final).save(O/'preview'/f'{stem}.png');Image.alpha_composite(Image.new('RGBA',(800,600),(24,27,34,255)),Image.fromarray(final)).convert('RGB').save(O/'preview'/f'{stem}.on-dark.png');finals[stem]=final
 comparison=np.concatenate([source[y:y+h,x:x+w],clean[y:y+h,x:x+w],final[y:y+h,x:x+w]],0);Image.fromarray(comparison).resize((w*3,h*9),Image.Resampling.NEAREST).save(O/'preview'/f'{stem}.source-clean-final-3x.png')
 records.append({'entry':n,'mask_entry':maskn if hasmask else None,'source_sha256':sha(payload[n]),'source_mask_sha256':sha(payload[maskn]) if hasmask else None,'source_size':[800,600],'source_region':[x,y,w,h],'source_glyph_pixels':expected,'target_ink_bounds':ib,'donor':donor,'protected_pixel_diff_count':0,'persisted_rgba_exact':True,'palette_preserved':True,'strings':[{'id':f'fastdata.arc::{n}::{tag}','source':source_text,'target':target,'translator_model':'Codex internal'}],'other_text_in_asset':'pending; title or decorative quote only'})
assert np.array_equal(finals['staffroom_off'][3:58,16:278],finals['staffroom_on'][3:58,16:278])
cons={}
for folder,names in [(U.parent/'research/extracted/scenario',['staffroom.mjo','history.mjo']),(SRC,['history.cfg','staffroom.cfg'])]:
 for n in names:
  if (folder/n).exists():cons[str(folder/n)]=sha((folder/n).read_bytes())
m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':records,'output_hashes':hashes,'semantic_labels':3,'structural_pass':True,'visual_pass':False,'runtime_pass':False,'consumers':cons,'font_hashes':{p.name:sha(p.read_bytes()) for p in [serif,sans]},'style_note':'First title syllable retains the original red initial; footer retains quiet gray and alpha. Original game logo preserved.'};(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(U/'translation/staff-history-ko.json').write_text(json.dumps({'translator_model':'Codex internal','records':[s for r in records for s in r['strings']]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'entries':len(records),'payloads':len(hashes),'labels':3,'bounds':{r['entry']:r['target_ink_bounds'] for r in records}},ensure_ascii=False))
