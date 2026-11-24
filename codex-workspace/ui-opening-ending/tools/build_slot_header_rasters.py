"""Partial save/config UI: text over proven uniform rows; preserve all other art."""
from pathlib import Path
import json,numpy as np
from PIL import Image,ImageFont,ImageDraw,ImageFilter
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
O=ROOT/'candidates/slot-header-raster-v1'
for d in ['payloads','clean','masks','layers','preview']:(O/d).mkdir(parents=True,exist_ok=True)
fontpath=ROOT.parent/'research/fonts/NotoSerifCJKkr-Regular.otf';cmap=TTFont(fontpath).getBestCmap();items=[];finals={};alphas={};outputs={}
headers={'sl_save':('ゲームデータをセーブ（書き込み）します。','게임 데이터를 저장합니다.'),'sl_load':('ゲームデータをロード（読み込み）します。','저장한 게임 데이터를 불러옵니다.'),'config':('プレイ環境の各種設定を行います','게임 환경을 설정합니다.')}
for stem in ['sl_save_n','sl_save_f','sl_load_n','sl_load_f','config_off','config_on','config_push']:
 name=stem+'.rct';maskname=stem+'_.rc8';rgb=np.asarray(decode(name)[0]);mrgb=np.asarray(decode(maskname)[0].convert('RGB')).astype('uint16');alpha=255-(mrgb.sum(2)//3).astype('uint8');source=np.dstack([rgb,alpha]);clean=source.copy();layer=Image.new('RGBA',(800,600));owned=np.zeros((600,800),bool);slots=np.zeros_like(owned);records=[];proofs=[]
 def field(tag,source_text,target,rect,kind,reference_x=None):
  x,y,w,h=rect;q=source[y:y+h,x:x+w];slot=[x,y-3,w,h+6] if kind=='number' else rect
  if kind=='header':
   # Both blank ends are original same-state black; row alpha is preserved.
   left=source[y:y+h,x];right=source[y:y+h,x+w-1];assert np.array_equal(left,right),(name,tag,'header blank ends');assert not left[:,:3].any();bg=np.repeat(left[:,None,:],w,axis=1);size=18;fill=(246,222,199,255);donor={'left_x':x,'right_x':x+w-1,'known_end_pixels_identical':True}
  else:
   refs=source[y:y+h,[reference_x-4,reference_x,reference_x+4]];assert np.all(refs==refs[:,:1]),(name,tag,'row references');bg=np.repeat(refs[:,1:2,:],w,axis=1);size=10 if kind=='number' else 17;different=np.any(q!=bg,axis=2);lum=q[:,:,:3].astype('uint16').sum(2);v=q[different&(lum>=np.quantile(lum[different],.94))];fill=tuple(np.median(v,axis=0).round().astype(int).tolist());donor={'reference_xs':[reference_x-4,reference_x,reference_x+4],'all_reference_columns_identical':True,'row_varying_original_rgba':bg[:,0,:].tolist()}
  erase=np.any(q!=bg,axis=2);yy,xx=np.nonzero(erase);assert len(xx)>0;bounds=[int(xx.min()+x),int(yy.min()+y),int(xx.max()+x+1),int(yy.max()+y+1)];assert bounds[0]>x and bounds[2]<x+w and bounds[1]>=y and bounds[3]<=y+h,(name,tag,bounds,rect)
  clean[y:y+h,x:x+w][erase]=bg[erase];owned[y:y+h,x:x+w]|=erase;slots[slot[1]:slot[1]+slot[3],slot[0]:slot[0]+slot[2]]=True;assert np.array_equal(clean[y:y+h,x:x+w],bg)
  assert all(ord(c) in cmap for c in target if not c.isspace());font=ImageFont.truetype(str(fontpath),size);stroke=1 if kind=='header' else 0;box=font.getbbox(target,stroke_width=stroke);cx=(bounds[0]+bounds[2])/2;cy=(bounds[1]+bounds[3])/2
  if kind=='header':cx=400
  ink=Image.new('RGBA',(800,600));d=ImageDraw.Draw(ink);d.text((round(cx-(box[0]+box[2])/2),round(cy-(box[1]+box[3])/2)),target,font=font,fill=fill,stroke_width=stroke,stroke_fill=(85,40,36,220));ia=np.asarray(ink)[:,:,3];iy,ix=np.nonzero(ia);ib=[int(ix.min()),int(iy.min()),int(ix.max())+1,int(iy.max())+1];assert slot[0]<=ib[0]<ib[2]<=slot[0]+slot[2] and slot[1]<=ib[1]<ib[3]<=slot[1]+slot[3],(name,tag,'target bounds',ib,rect);layer.alpha_composite(ink)
  records.append({'id':f'fastdata.arc::{name}::{tag}','source':source_text,'target':target,'source_region':rect,'target_slot':slot,'source_ink_bounds':bounds,'target_ink_bounds':ib,'font_size':size,'fill_from_source':list(fill)});proofs.append({'id':tag,'donor':donor,'source_erased_pixels':int(erase.sum()),'clean_plate_equals_original_row_template':True})
 key='config' if stem.startswith('config') else stem.rsplit('_',1)[0];field('header',*headers[key],[228,20,354,34],'header')
 if stem.startswith('sl_'):
  for row,y0 in enumerate([87,249,411]):
   for col,x0 in enumerate([40,281,523]):
    index=row*3+col+1;q=source[y0+4:y0+32,x0+20:x0+76];ref=source[y0+4:y0+32,x0+91:x0+92];active=np.any(q!=ref,axis=(1,2));edges=np.diff(np.r_[False,active,False].astype('int8'));starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1);assert len(starts)>0,(name,index,'missing number label');ny=y0+4+int(starts[0])-1;nh=int(ends[0]-starts[0])+2;field(f'slot-{index}-number','Save No.','저장 번호',[x0+10,ny,67,nh],'number',x0+91);field(f'slot-{index}-empty','-No Date-' if index==1 else '-No Data-','비어 있음',[x0+106,y0+48,120,35],'empty',x0+91)
 Image.fromarray(clean,'RGBA').save(O/'clean'/f'{stem}.png');assert np.array_equal(np.asarray(Image.open(O/'clean'/f'{stem}.png')),clean)
 new=np.asarray(layer)[:,:,3]>0;assert not np.any(new&~slots);final=np.asarray(Image.alpha_composite(Image.fromarray(clean,'RGBA'),layer));owned|=new;assert np.array_equal(final[~owned],source[~owned]);finals[name]=final[:,:,:3];alphas[maskname]=final[:,:,3];layer.save(O/'layers'/f'{stem}.png');Image.fromarray((owned*255).astype('uint8')).save(O/'masks'/f'{stem}.owned.png');Image.fromarray(final,'RGBA').save(O/'preview'/f'{stem}.png');Image.alpha_composite(Image.new('RGBA',(800,600),(24,27,34,255)),Image.fromarray(final,'RGBA')).convert('RGB').save(O/'preview'/f'{stem}.on-dark.png')
 items.append({'entry':name,'mask_entry':maskname,'strings':records,'restoration':proofs,'source_hashes':{name:sha((SRC/name).read_bytes()),maskname:sha((SRC/maskname).read_bytes())},'protected_pixel_diff_count':0,'remaining_in_asset':['Panel title and top-right buttons','Other labels and decorative English footer'] if stem.startswith('sl_') else ['Panel title, all setting labels, buttons and character labels'],'scope':'only listed labels completed; asset as a whole remains partial'})
for rec in items:
 name=rec['entry'];maskname=rec['mask_entry'];rb=(SRC/name).read_bytes();mb=(SRC/maskname).read_bytes();_,rp,rc=raw_image(rb);mi,mp,mc=raw_image(mb);im=finals[name]
 if rb[4:8]==b'TC01':
  bn=rp[22:].rstrip(b'\0').decode('cp932');bn=bn if bn.endswith('.rct') else bn+'.rct';base=finals.get(bn,np.asarray(decode(bn)[0]));red=np.all(im==[255,0,0],axis=2);assert np.all(base[red]==[255,0,0])
 pal=np.frombuffer(mp[20:788],dtype='uint8').reshape(256,3);assert np.all(pal[:,0]==pal[:,1]) and np.all(pal[:,0]==pal[:,2]);lookup={int(v):i for i,v in enumerate(pal[:,0])};assert len(lookup)==256;idx=np.array([lookup[int(v)] for v in (255-alphas[maskname]).ravel()],dtype='uint8').reshape(mi.shape);ob=encode_array(im,rp,rc);om=encode_array(idx,mp,mc)
 for n,b in [(name,ob),(maskname,om)]:(O/'payloads'/n).write_bytes(b);outputs[n]=sha(b)
 reread,_,_=raw_image((O/'payloads'/name).read_bytes())
 if rb[4:8]==b'TC01':reread[red]=base[red]
 maskread,prefixcheck,_=raw_image((O/'payloads'/maskname).read_bytes());assert np.array_equal(reread,im) and np.array_equal(255-pal[maskread,0],alphas[maskname]) and prefixcheck[20:788]==mp[20:788];rec.update(output_hashes={name:sha(ob),maskname:sha(om)},persisted_rgba_exact=True,palette_preserved=True)
m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':items,'output_hashes':outputs,'semantic_labels':sum(len(r['strings']) for r in items),'font_glyph_coverage_pass':True,'font_sha256':sha(fontpath.read_bytes()),'structural_pass':True,'visual_pass':False,'asset_completion':'partial; do not count whole settings/save-load surfaces complete','runtime_review':'pending','consumer_hashes':{n:sha((SRC/n).read_bytes()) for n in ['config.cfg','loadsave.cfg','savethumb.cfg']}}
(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(ROOT/'translation/slot-header-ko.json').write_text(json.dumps({'translator_model':'Codex internal','task_id':m['task_id'],'records':[s for r in items for s in r['strings']]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'entries':len(items),'labels':m['semantic_labels'],'payloads':len(outputs)},ensure_ascii=False))
