from pathlib import Path
import json,hashlib,numpy as np,cv2
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
O=ROOT/'candidates/modal-raster-v1'
for d in ['payloads','clean','masks','layers','preview']:(O/d).mkdir(parents=True,exist_ok=True)
name='askyesno_base.rct';source=np.asarray(decode(name)[0]);donor=np.asarray(decode('選択肢台.rct')[0]);clean=source.copy();records=[];maskall=np.zeros((600,800),bool);slots=np.zeros((600,800),bool);restores=[]
for state,y,dx,dy in [('normal',294,5,-211),('hover',364,5,-182),('selected',434,18,-153)]:
 pairs=[];lut={};scalar={}
 for x in [255,429]:
  q=source[y:y+33,x:x+116];xx=x+dx-(174 if x==429 else 0);zz=y+dy;c=donor[zz:zz+33,xx:xx+116]
  exclusion=cv2.dilate((q.min(2)>90).astype('uint8'),np.ones((9,9),np.uint8)).astype(bool)
  for rgb,val in zip(c[~exclusion],q[~exclusion]):
   key=tuple(map(int,rgb));v=tuple(map(int,val))
   assert key not in lut or lut[key]==v
   lut[key]=v
   if state=='hover':
    for k,vv in zip(rgb,val):
     k=int(k);vv=int(vv);assert k not in scalar or scalar[k]==vv;scalar[k]=vv
  pairs.append((x,c,q,exclusion,xx,zz))
 for x,c,q,exclusion,xx,zz in pairs:
  if state=='normal':restored=c.copy()
  elif state=='hover':
   assert set(map(int,c.flatten()))<=set(scalar)
   restored=np.array([scalar[int(v)] for v in c.flatten()],dtype='uint8').reshape(c.shape)
  else:
   assert {tuple(map(int,p)) for p in c.reshape(-1,3)}<=set(lut)
   restored=np.array([lut[tuple(map(int,p))] for p in c.reshape(-1,3)],dtype='uint8').reshape(c.shape)
  assert np.array_equal(restored[~exclusion],q[~exclusion])
  ink=np.any(restored!=q,axis=2);assert not np.any(ink&~exclusion)
  clean[y:y+33,x:x+116][ink]=restored[ink];maskall[y:y+33,x:x+116]|=ink;slots[y:y+33,x:x+116]=True
  restores.append({'state':state,'slot':[x,y,116,33],'donor_region':[xx,zz,116,33],'color_transfer':'identity' if state=='normal' else 'exact shared scalar LUT' if state=='hover' else 'exact RGB LUT','known_pixels':int((~exclusion).sum()),'known_pixel_diff':0,'unseen_donor_values':0,'color_conflicts':0,'source_ink_pixels':int(ink.sum()),'table':None if state=='normal' else {str(k):v for k,v in (scalar if state=='hover' else lut).items()}})
Image.fromarray(clean).save(O/'clean'/f'{name}.png')
assert np.array_equal(np.asarray(Image.open(O/'clean'/f'{name}.png')),clean)
fontpath=ROOT.parent/'research/fonts/NotoSansCJKkr-Regular.otf';font=ImageFont.truetype(str(fontpath),22)
ink=Image.new('L',(800,600));draw=ImageDraw.Draw(ink)
for state,y in [('normal',294),('hover',364),('selected',434)]:
 for x,src,target in [(255,'はい','예'),(429,'いいえ','아니요')]:
  bbox=font.getbbox(target);px=round(x+58-(bbox[0]+bbox[2])/2);py=round(y+16-(bbox[1]+bbox[3])/2);draw.text((px,py),target,font=font,fill=255)
  records.append({'id':f'fastdata.arc::{name}::{state}:{src}','source':src,'target':target,'state':state,'target_slot':[x,y,116,33],'ink_bounds':[px+bbox[0],py+bbox[1],px+bbox[2],py+bbox[3]]})
layer=Image.new('RGBA',(800,600));shadow=Image.new('L',(800,600));shadow.paste(ink,(1,1));shadow=shadow.filter(ImageFilter.GaussianBlur(.6));layer.alpha_composite(Image.merge('RGBA',(Image.new('L',(800,600),0),)*3+(shadow,)));layer.alpha_composite(Image.merge('RGBA',(Image.new('L',(800,600),250),)*3+(ink,)))
tm=np.asarray(layer)[:,:,3]>0;assert not np.any(tm&~slots)
final=np.asarray(Image.alpha_composite(Image.fromarray(clean).convert('RGBA'),layer).convert('RGB'));owned=maskall|tm;assert np.array_equal(final[~owned],source[~owned])
mask=np.asarray(decode('askyesno_base_.rc8')[0].convert('RGB'));assert np.all(mask[owned]==0),'Original mask must be opaque in edited text pixels'
blob=(SRC/name).read_bytes();raw,prefix,channels=raw_image(blob);raw[owned]=final[owned];encoded=encode_array(raw,prefix,channels);(O/'payloads'/name).write_bytes(encoded);reopened,_,_=raw_image((O/'payloads'/name).read_bytes());assert np.array_equal(reopened,final)
Image.fromarray(maskall.astype('uint8')*255).save(O/'masks'/f'{name}.source.png');Image.fromarray(owned.astype('uint8')*255).save(O/'masks'/f'{name}.owned.png');layer.save(O/'layers'/f'{name}.png');Image.fromarray(final).save(O/'preview'/f'{name}.png')
m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entry':name,'source_sha256':sha(blob),'output_sha256':sha(encoded),'canvas':[800,600],'metadata_preserved':True,'mask_entry_unchanged':'askyesno_base_.rc8','donor':'選択肢台.rct','donor_sha256':sha((SRC/'選択肢台.rct').read_bytes()),'restoration':restores,'consumer':{'file':'message_box.mjo','source_sha256':sha((ROOT.parent/'research/extracted/scenario/message_box.mjo').read_bytes()),'crop_start_bytecode_offsets':['0x12d7','0x1401','0x152b'],'state_crops':[[231,284,338,55],[231,354,338,55],[231,424,338,55]]},'strings':records,'structural_pass':True,'protected_pixel_diff_count':0,'persisted_decode_pass':True,'state_closure':'normal/hover/selected, 2 labels each','visual_pass':False,'runtime_review':'user_final_batch'}
(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'out':str(O),'labels':len(records),'source_ink_pixels':int(maskall.sum()),'owned_pixels':int(owned.sum()),'sha256':sha(encoded)},ensure_ascii=False))
