"""User-authorized local reconstruction of 19 configuration labels, with preserved control geometry."""
from pathlib import Path
import sys,json,hashlib,shutil,numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
R=Path(__file__).resolve().parents[1];U=R/'ui-opening-ending';O=R/'candidates/config-completion-v1';B=R/'builds/body-ui-20261023-v12-input-logo'
sys.path[:0]=[str(R/'tools'),str(U/'tools')]
from inspect_majiro import Arc
from raster_codec import raw_image,encode_array
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n','utf-8')
for sub in ['payloads','clean','layers','masks','preview','source','hd','native']:(O/sub).mkdir(parents=True,exist_ok=True)
gen=Path('P:/AI/Codex/generated_images/01a16283-b393-7dc0-8c83-d3e23a2a2f41/exec-b149d6b0-d5c5-41e7-9500-92d7d4c0fef0.png')
shutil.copy2(gen,O/'source/imagegen-clean-proposal.png')
rest=np.asarray(Image.open(gen).convert('RGB').resize((800,600),Image.Resampling.LANCZOS))
# Regions derive from complete Japanese text and its effects in the source, never Korean target length.
rows=[
('back','前の画面に戻る','이전 화면으로',[612,18,126,24],15,'center'),
('reset','初期設定に戻す','설정 초기화',[612,50,126,24],15,'center'),
('display-group','画面設定','화면설정',[54,116,29,96],20,'vertical'),
('screen-size','画面サイズ','화면 크기',[103,103,94,22],15,'left'),
('skip','スキップ','건너뛰기',[103,134,94,22],15,'left'),
('text-speed','文字表示速度','글자 표시 속도',[103,171,111,27],15,'left'),
('auto-speed','オートモード速度','자동 진행 속도',[103,208,111,27],15,'left'),
('font','使用フォント','사용 글꼴',[390,102,122,24],15,'left'),
('selected-choice','選択済み選択肢','선택한 선택지',[390,133,122,24],15,'left'),
('sound-group','音声設定','음향설정',[54,292,30,103],20,'vertical'),
('bgm-volume','BGM音量','배경음 음량',[106,283,85,25],15,'left'),
('voice-volume','ボイス音量','음성 음량',[106,329,85,25],15,'left'),
('se-volume','効果音音量','효과음 음량',[106,375,85,25],15,'left'),
('kureha','暮葉','쿠레하',[55,430,64,27],18,'left'),
('momiji','もみじ','모미지',[55,477,64,27],18,'left'),
('mahoko','真帆子','마호코',[55,524,64,27],18,'left'),
('shiina','詩菜','시이나',[410,430,64,27],18,'left'),
('masaki','麻咲','마사키',[410,477,64,27],18,'left'),
('others','その他','기타',[410,524,64,27],18,'left')]
assert len(rows)==19
def smooth_fill(src,mask):
 a=src.astype(float).copy();a[mask]=np.median(a[~mask])
 for _ in range(450):
  p=np.pad(a,1,mode='edge');avg=(p[:-2,1:-1]+p[2:,1:-1]+p[1:-1,:-2]+p[1:-1,2:])*0.25;a[mask]=avg[mask]
 return a
fontpath=R/'research/fonts/NotoSerifCJKkr-Regular.otf'
a=Arc(B/'fastdata.arc');blob=a.path.read_bytes();payload={e['name']:blob[e['offset']:e['offset']+e['size']] for e in a.entries}
records=[];semantic=[]
for st in ['off','on','push']:
 n=f'config_{st}.rct';mn=f'config_{st}_.rc8';rgb,cp,c=raw_image(payload[n]);mi,mp,mc=raw_image(payload[mn])
 assert rgb.shape==(600,800,3) and mi.shape==(600,800)
 pal=np.frombuffer(mp[20:788],dtype='uint8').reshape(256,3);assert np.all(pal[:,0]==pal[:,1]) and np.all(pal[:,1]==pal[:,2]);inv=np.empty(256,dtype='uint8');inv[pal[:,0]]=np.arange(256,dtype='uint8')
 matte=pal[mi,0].copy();clean=rgb.copy();cm=matte.copy();owned=np.zeros((600,800),bool);targets=[]
 for key,ja,ko,(x,y,w,h),size,align in rows:
  # Only full source-label interiors are reconstructed. Outside RGB and original mask are untouched.
  roi=rgb[y:y+h,x:x+w];base=rest[y:y+h,x:x+w].copy()
  # State-dependent navigation chrome is retained; only inner label surface is reconstructed.
  if key in ('back','reset') and st!='off':
   # Original hover has a brighter text/frame but same mosaic hue. Its center is locally reconstructed.
   base=rest[y:y+h,x:x+w].copy()
  # Source text is bright against the dark mosaic; include its fringes and detached shadow.
  core=np.min(roi,axis=2)>76
  mask=Image.fromarray(core.astype('uint8')*255).filter(ImageFilter.MaxFilter(7))
  hard=np.asarray(mask)>0
  soft=np.asarray(mask.filter(ImageFilter.GaussianBlur(0.75)),dtype=float)/255
  soft[hard]=1
  # Match the generated clean texture locally; retain every source pixel beyond the source-owned erasure.
  ring=(np.asarray(mask.filter(ImageFilter.MaxFilter(5)))>0)&~hard
  for ch in range(3):
   delta=np.median(roi[:,:,ch][ring].astype(float)-base[:,:,ch][ring]) if ring.any() else 0
   base[:,:,ch]=np.clip(base[:,:,ch].astype(float)+delta,0,255)
  clean[y:y+h,x:x+w]=np.rint(base*soft[:,:,None]+roi*(1-soft[:,:,None])).astype('uint8')
  am=matte[y:y+h,x:x+w];filled=smooth_fill(am,soft>0)
  cm[y:y+h,x:x+w]=np.rint(filled*soft+am*(1-soft)).astype('uint8')
  owned[y:y+h,x:x+w]=True
  # Each row gets a source-sized Korean layer; all semantics authored here by Codex internal.
  layer=Image.new('RGBA',(800,600));d=ImageDraw.Draw(layer);font=ImageFont.truetype(str(fontpath),size)
  col=(246,230,215,255) if key in ('back','reset') else (238,229,216,255)
  if key in ('back','reset') and st=='on':col=(255,245,227,255)
  if key in ('back','reset') and st=='push':col=(242,199,142,255)
  if align=='vertical':
   step=min(size+2,h//len(ko));total=(len(ko)-1)*step+size
   for j,ch in enumerate(ko):
    bb=font.getbbox(ch);px=x+(w-(bb[2]-bb[0]))//2-bb[0];py=y+(h-total)//2+j*step-bb[1]
    d.text((px+1,py+1),ch,font=font,fill=(12,12,15,230));d.text((px,py),ch,font=font,fill=col)
  else:
   bb=font.getbbox(ko);tw=bb[2]-bb[0];th=bb[3]-bb[1];assert tw+2<w,(key,tw,w)
   px=x+(w-tw)//2-bb[0] if align=='center' else x+1-bb[0];py=y+(h-th)//2-bb[1]
   d.text((px+1,py+1),ko,font=font,fill=(12,12,15,230));d.text((px,py),ko,font=font,fill=col)
  ar=np.asarray(layer);ink=ar[:,:,3]>0;yy,xx=np.nonzero(ink);bb=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
  assert x<=bb[0] and bb[2]<=x+w and y<=bb[1] and bb[3]<=y+h,(key,bb)
  targets.append((layer,ink,ar[:,:,3]))
  if st=='off':semantic.append({'id':'config-static::'+key,'source':ja,'target':ko,'source_region':[x,y,w,h],'font_px':size,'layout':align,'ink_bbox':bb,'translator_model':'Codex internal'})
 Image.fromarray(clean).save(O/'clean'/f'{st}.png');Image.fromarray(cm).save(O/'clean'/f'{st}-matte.png')
 result=Image.fromarray(clean).convert('RGBA');fa=255-cm.astype(np.uint16)
 combined=Image.new('RGBA',(800,600))
 for layer,ink,alpha in targets:
  result=Image.alpha_composite(result,layer);combined=Image.alpha_composite(combined,layer)
  fa=np.rint(alpha.astype(float)+(255-alpha.astype(float))*fa/255).astype(np.uint16)
 final=np.asarray(result.convert('RGB'));newmi=inv[255-fa.astype('uint8')]
 assert np.array_equal(final[~owned],rgb[~owned]);assert np.array_equal(newmi[~owned],mi[~owned])
 for name,arr,prefix,ch in [(n,final,cp,3),(mn,newmi,mp,1)]:
  encoded=encode_array(arr,prefix,ch);(O/'payloads'/name).write_bytes(encoded);decoded,p2,c2=raw_image(encoded);assert np.array_equal(decoded,arr);assert p2[:16]==prefix[:16] and p2[20:]==prefix[20:]
 combined.save(O/'layers'/f'{st}.png');Image.fromarray((owned*255).astype('uint8')).save(O/'masks'/f'{st}-owned.png')
 Image.fromarray(final).save(O/'preview'/f'config_{st}.png')
 # Preview on an explicit background demonstrates that the old Japanese alpha is removed too.
 rgba=Image.fromarray(final).convert('RGBA');rgba.putalpha(Image.fromarray(fa.astype('uint8')));bg=Image.new('RGBA',(800,600),(36,39,49,255));Image.alpha_composite(bg,rgba).convert('RGB').save(O/'preview'/f'config_{st}-composite.png')
 records.append({'entry':n,'mask_entry':mn,'base_rgb_sha256':hashlib.sha256(payload[n]).hexdigest(),'base_mask_sha256':hashlib.sha256(payload[mn]).hexdigest(),'output_sha256':sha(O/'payloads'/n),'mask_output_sha256':sha(O/'payloads'/mn),'canvas':[800,600],'owned_pixels':int(owned.sum()),'outside_owned_rgb_diff':0,'outside_owned_mask_diff':0,'mask_metadata_palette_preserved':True,'labels':19})
dump(O/'semantic-map.json',{'translator_model':'Codex internal','task_id':'01a16283-b393-7dc0-8c83-d3e23a2a2f41','records':semantic})
dump(O/'manifest.json',{'status':'candidate_visual_review_pending','translator_model':'Codex internal','user_authorized_exception':'2026-10-23 user approved 원본풍 부분 복원 허용 (권장), replacing unavailable exact background with local reconstruction. This is approximate, not original donor recovery.','source_build':str(B),'source_manifest_sha256':sha(B/'manifest.json'),'imagegen_source_sha256':sha(gen),'font_sha256':sha(fontpath),'entries':records,'static_label_instances':57,'semantic_labels':19,'original_control_rectangles_and_pixels_preserved':True,'clean_plate_kind':'user-approved approximate local background and alpha reconstruction','geometry_preserved':True,'ready_for_integration':False})
print(json.dumps({'labels':19,'instances':57,'payloads':6,'candidate':str(O)},ensure_ascii=False))

