from pathlib import Path
import json,struct,hashlib,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from fontTools.ttLib import TTFont
from decode_ui import decode,unpack,ROOT,SRC,sha
OUT=ROOT/'candidates/title-menu-v1';OUT.mkdir(exist_ok=True)
for d in ['payloads','clean','masks','layers','preview']:(OUT/d).mkdir(exist_ok=True)
fontpath=Path(r'C:\Windows\Fonts\batang.ttc');font=ImageFont.truetype(str(fontpath),22,index=0)
ft=TTFont(fontpath,fontNumber=0);cm=ft.getBestCmap()
labels=[('START','처음부터',328),('LOAD','불러오기',369),('CONFIG','설정',410),('EXTRA','추가 메뉴',450),('EXIT','종료',494)]
assert all(cm.get(ord(c)) not in [None,'.notdef'] for _,t,_ in labels for c in t)
def raw_rct(b):
 w,h=struct.unpack_from('<II',b,8);pos=20 if b[4:8]==b'TC00' else 22+struct.unpack_from('<H',b,20)[0]
 raw,end=unpack(b,pos,w,h,3);assert end==len(b)
 return np.asarray(Image.frombytes('RGB',(w,h),raw,'raw','BGR')).copy(),pos

def pack_literal(rgb,prefix):
 b=Image.fromarray(rgb,'RGB').tobytes('raw','BGR');data=bytearray(b[:3]);i=3
 while i<len(b):
  n=min((len(b)-i)//3,65663)
  if n<128:data.append(n-1)
  else:data.append(127);data.extend(struct.pack('<H',n-128))
  data.extend(b[i:i+n*3]);i+=n*3
 head=bytearray(prefix);struct.pack_into('<I',head,16,len(data));return bytes(head)+data
reports=[]
for variant in [1,2,3]:
 donorname='title2_null2.rct' if variant==2 else 'title1_null2.rct'
 donor=np.asarray(decode(donorname)[0])
 ref=np.asarray(decode(f'title{variant}_off.rct')[0])
 # The donor is trusted only where the three state family differences lie.
 # For title 3 this proves the exact moon-background donor at original menu positions.
 textregions=np.zeros(ref.shape[:2],bool)
 for _,_,y in labels:textregions[y:y+41,565:708]=True
 base_diff=np.any(ref!=donor,axis=2)&textregions
 compare_ref=np.asarray(decode('title1_off.rct' if variant!=2 else 'title2_off.rct')[0])
 compare_donor=np.asarray(decode('title1_null2.rct' if variant!=2 else 'title2_null2.rct')[0])
 known_ink=np.any(compare_ref!=compare_donor,axis=2)&textregions
 assert not np.any(base_diff&~known_ink),('donor_background_mismatch',variant)
 for state in ['off','on','push']:
  name=f'title{variant}_{state}.rct';original=SRC/name;source=np.asarray(decode(name)[0]);clean=source.copy()
  mask=np.any(source!=donor,axis=2)&textregions
  # All differences in each original menu cell are text/glow; retain unrelated art.
  clean[mask]=donor[mask]
  assert np.array_equal(clean[textregions],donor[textregions])
  Image.fromarray((mask*255).astype('uint8'),'L').save(OUT/'masks'/f'{name}.source-mask.png')
  Image.fromarray(clean).save(OUT/'clean'/f'{name}.png')
  reopened=np.asarray(Image.open(OUT/'clean'/f'{name}.png'));assert np.array_equal(reopened,clean)
  layer=Image.new('RGBA',(800,600));ink=Image.new('L',(800,600));draw=ImageDraw.Draw(ink)
  texts=[]
  for source_text,target,y in labels:
   region=mask[y:y+41,565:708];ys,xs=np.nonzero(region)
   assert len(xs);bbox=font.getbbox(target,stroke_width=0)
   center_y=y+(int(ys.min())+int(ys.max()))/2
   px=595;py=round(center_y-(bbox[1]+bbox[3])/2)
   draw.text((px,py),target,font=font,fill=255,stroke_width=0)
   texts.append({'id':f'fastdata.arc::{name}::button:{source_text}','source':source_text,'target':target,'consumer':'start.mjo $buttonmenu_set@BUTONMENU','consumer_crop':[565,y,143,41],'target_ink_bbox':[px+bbox[0],py+bbox[1],px+bbox[2],py+bbox[3]]})
  if state=='on':
   glow=ink.filter(ImageFilter.GaussianBlur(2.3));layer.alpha_composite(Image.merge('RGBA',(*[Image.new('L',(800,600),v) for v in (255,139,161)],glow)))
  else:
   shadow=Image.new('L',(800,600));shadow.paste(ink,(1,1));shadow=shadow.filter(ImageFilter.GaussianBlur(1.1))
   layer.alpha_composite(Image.merge('RGBA',(*[Image.new('L',(800,600),v) for v in (65,77,105)],shadow)))
  fill=(255,255,255) if state!='push' else (245,183,74)
  layer.alpha_composite(Image.merge('RGBA',(*[Image.new('L',(800,600),v) for v in fill],ink)))
  layer.save(OUT/'layers'/f'{name}.png')
  targetmask=np.asarray(layer)[:,:,3]>0;assert not np.any(targetmask&~textregions)
  final=np.asarray(Image.alpha_composite(Image.fromarray(clean).convert('RGBA'),layer).convert('RGB'))
  owned=mask|targetmask;assert np.array_equal(final[~owned],source[~owned])
  raw,pos=raw_rct(original.read_bytes());raw[owned]=final[owned]
  # Keep TC00/TC01 signature and exact baseline-name metadata; literal encoding is lossless.
  blob=pack_literal(raw,original.read_bytes()[:pos]);pp=OUT/'payloads'/name;pp.write_bytes(blob)
  decoded,_=raw_rct(pp.read_bytes());assert np.array_equal(decoded,raw)
  if blob[4:8]==b'TC01':
   basename=blob[22:pos].rstrip(b'\0').decode('cp932');base=np.asarray(decode(basename)[0]);skip=np.all(decoded==[255,0,0],axis=2);decoded[skip]=base[skip]
  assert np.array_equal(decoded,final)
  Image.fromarray(decoded).save(OUT/'preview'/f'{name}.png')
  reports.append({'entry':name,'source_sha256':sha(original.read_bytes()),'output_sha256':sha(blob),'source_geometry':[800,600],'output_geometry':[800,600],'donor':donorname,'donor_sha256':sha((SRC/donorname).read_bytes()),'source_erasure_pixels':int(mask.sum()),'outside_owned_diff_pixels':int(np.any(final[~owned]!=source[~owned],axis=1).sum()),'source_residue_test':'menu cells equal exact original text-free donor before typesetting','header_metadata_preserved':True,'persisted_decode_equals_target':True,'structural_pass':True,'visual_pass':False,'runtime_pass':False,'strings':texts})
manifest={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','status':'static_pass_visual_runtime_pending','raster_font':{'path':str(fontpath),'sha256':sha(fontpath.read_bytes()),'index':0,'size':22,'all_target_glyphs_present':True,'font_redistributed':False},'entries':reports}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'payloads':len(reports),'strings':sum(len(x['strings']) for x in reports),'static_pass':True,'path':str(OUT)},ensure_ascii=False))
