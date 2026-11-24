"""Localize text-only RCT/RC8 pairs without changing canvas or consumer crop."""
from pathlib import Path
import json,numpy as np,hashlib,collections
from PIL import Image,ImageFont,ImageDraw,ImageFilter
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
O=ROOT/'candidates/text-raster-v1'
for d in ['payloads','clean','masks','layers','preview']:(O/d).mkdir(parents=True,exist_ok=True)
fontpath=ROOT.parent/'research/fonts/NotoSerifCJKkr-Regular.otf'
views=[
('その他','ETC. View','기타 시점'),
('もみじ','Momiji View','모미지의 시점'),
('上条','KamijoView','가미조의 시점'),
('信哉','Shinya View','신야의 시점'),
('暮葉','Kureha View','쿠레하의 시점'),
('槙野','Makino View','마키노의 시점'),
('汐見トオル','ToruView','도루의 시점'),
('汐見牧師','Shiomi View','시오미의 시점'),
('真帆子','Mahoko View','마호코의 시점'),
('詩菜','Shina View','시이나의 시점'),
('麻咲','Masaki View','마사키의 시점')]
credits=[
('作曲：上松範康 (Elements Garden)　編曲：菊田大介 (Elements Garden)　歌手：飛蘭','작곡: 上松範康 (Elements Garden)  편곡: 菊田大介 (Elements Garden)  노래: 飛蘭'),
('作曲：上松範康 (Elements Garden)　編曲：菊田大介 (Elements Garden)','작곡: 上松範康 (Elements Garden)  편곡: 菊田大介 (Elements Garden)'),
('作曲：上松範康 (Elements Garden)','작곡: 上松範康 (Elements Garden)'),
('作曲：ANZE HIJIRI','작곡: ANZE HIJIRI'),
('作曲：ANZE HIJIRI　歌手：YURIA','작곡: ANZE HIJIRI  노래: YURIA'),
('作曲：Barbarian on the groove　編曲：館内','작곡: Barbarian on the groove  편곡: 館内'),
('作曲：Barbarian on the groove','작곡: Barbarian on the groove'),
('作曲：館内','작곡: 館内'),
('作曲：井出 今日子','작곡: 井出 今日子'),
('作曲：Sentive','작곡: Sentive'),
('作曲：443','작곡: 443'),
('作曲：児島 空','작곡: 児島 空'),
('作曲：Elements Garden　編曲：館内','작곡: Elements Garden  편곡: 館内'),
('作曲：Elements Garden','작곡: Elements Garden')]
reports=[]
def render_pair(stem,source_text,target,kind):
 rgb=np.asarray(decode(stem+'.rct')[0]).copy();maskname=stem+'_.rc8';maskim,_=decode(maskname);maskrgb=np.asarray(maskim.convert('RGB')).astype('uint16');alpha=255-(maskrgb.sum(2)//3).astype('uint8');h,w=alpha.shape
 oldmask=alpha>0;ys,xs=np.nonzero(oldmask);sourcebbox=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
 if kind=='view':
  assert (w,h)==(800,600);slot=[302,394,260,76];size=32
 else:
  assert (w,h)==(636,38);slot=[8,3,620,32];size=17
 x,y,sw,sh=slot
 while True:
  font=ImageFont.truetype(str(fontpath),size);bbox=font.getbbox(target,stroke_width=0)
  if bbox[2]-bbox[0]+8<=sw and bbox[3]-bbox[1]+8<=sh:break
  size-=1;assert size>=14
 ink=Image.new('L',(w,h));draw=ImageDraw.Draw(ink)
 if kind=='view':
  # Preserve the source's left anchoring and original 292,384,275,93 consumer window.
  px=326-bbox[0];py=round(430-(bbox[1]+bbox[3])/2)
  assert px+bbox[2]+4<=567
 else:px=round(w/2-(bbox[0]+bbox[2])/2);py=round(18-(bbox[1]+bbox[3])/2)
 draw.text((px,py),target,font=font,fill=255)
 layer=Image.new('RGBA',(w,h))
 if kind=='view':
  crop=rgb[sourcebbox[1]:sourcebbox[3],sourcebbox[0]:sourcebbox[2]];acrop=alpha[sourcebbox[1]:sourcebbox[3],sourcebbox[0]:sourcebbox[2]];samples=crop[acrop<230]
  color=collections.Counter(map(tuple,samples)).most_common(1)[0][0];color=tuple(map(int,color))
  glow=ink.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.1));glow=glow.point(lambda v:round(v*.8))
  layer.alpha_composite(Image.merge('RGBA',tuple(Image.new('L',(w,h),v) for v in color)+(glow,)))
  layer.alpha_composite(Image.merge('RGBA',(Image.new('L',(w,h),255),)*3+(ink,)))
 else:
  color=(49,32,21);stroke=Image.new('RGBA',(w,h));d=ImageDraw.Draw(stroke);d.text((px,py),target,font=font,fill=(222,202,179,255),stroke_width=2,stroke_fill=(*color,255));layer=stroke
 la=np.asarray(layer);newmask=la[:,:,3]>0;owned=oldmask|newmask
 # Clean plate is fully transparent; no background art exists in these text-only pairs.
 cleanrgb=rgb.copy();cleanrgb[oldmask]=255;cleanalpha=alpha.copy();cleanalpha[oldmask]=0
 assert not cleanalpha.any()
 clean=Image.fromarray(cleanrgb).convert('RGBA');clean.putalpha(Image.fromarray(cleanalpha));clean.save(O/'clean'/f'{stem}.png');assert not np.asarray(Image.open(O/'clean'/f'{stem}.png'))[:,:,3].any()
 finalrgb=cleanrgb.copy();finalrgb[newmask]=la[newmask,:3];finalalpha=cleanalpha.copy();finalalpha[newmask]=la[newmask,3]
 assert np.array_equal(finalrgb[~owned],rgb[~owned]) and np.array_equal(finalalpha[~owned],alpha[~owned])
 # The source palettes contain all 256 exact grayscale mask values.
 mb=(SRC/maskname).read_bytes();mr,mp,mc=raw_image(mb);palette=np.frombuffer(mp[20:788],dtype='uint8').reshape(256,3);assert np.all(palette[:,0]==palette[:,1]) and np.all(palette[:,0]==palette[:,2]);lookup={int(v):i for i,v in enumerate(palette[:,0])};assert len(lookup)==256
 newindices=mr.copy();inv=255-finalalpha;newindices[owned]=np.array([lookup[int(v)] for v in inv[owned]],dtype='uint8')
 rb=(SRC/(stem+'.rct')).read_bytes();rr,rp,rc=raw_image(rb);assert rc==3 and rb[4:8]==b'TC00';rr[owned]=finalrgb[owned]
 outbytes=encode_array(rr,rp,rc);outmask=encode_array(newindices,mp,mc)
 (O/'payloads'/(stem+'.rct')).write_bytes(outbytes);(O/'payloads'/maskname).write_bytes(outmask)
 ri,_,_=raw_image((O/'payloads'/(stem+'.rct')).read_bytes());mi,_,_=raw_image((O/'payloads'/maskname).read_bytes());ra=255-palette[mi,0];assert np.array_equal(ri,finalrgb) and np.array_equal(ra,finalalpha)
 out=Image.fromarray(ri).convert('RGBA');out.putalpha(Image.fromarray(ra));out.save(O/'preview'/f'{stem}.png');layer.save(O/'layers'/f'{stem}.png');Image.fromarray(oldmask.astype('uint8')*255).save(O/'masks'/f'{stem}.source.png')
 yy,xx=np.nonzero(newmask);inkbounds=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];assert x<=inkbounds[0]<inkbounds[2]<=x+sw and y<=inkbounds[1]<inkbounds[3]<=y+sh,(stem,inkbounds,slot)
 reports.append({'id':f'fastdata.arc::{stem}','source':source_text,'target':target,'kind':kind,'source_bbox':sourcebbox,'target_slot':slot,'target_ink_bounds':inkbounds,'font_size':size,'color_provenance':color,'geometry':[w,h],'rgb_entry':stem+'.rct','mask_entry':maskname,'source_hashes':{stem+'.rct':sha(rb),maskname:sha(mb)},'output_hashes':{stem+'.rct':sha(outbytes),maskname:sha(outmask)},'outside_owned_diff_pixels':0,'palette_bytes_identical':True,'reopened_rgb_alpha_exact':True,'clean_plate':'fully transparent text-only surface; old visible pixels erased including fringe','consumer':{'file':'sightchange.mjo','crop':[292,384,275,93]} if kind=='view' else {'file':'music.mjo','draw_xy':[37,116],'canvas':[636,38]},'runtime_review':'user_final_batch'})
for name,src,target in views:render_pair(name+'_view',src,target,'view')
for i,(src,target) in enumerate(credits,1):render_pair('作曲_クレジット_'+str(i),src,target,'credit')
manifest={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':reports,'source_review':['evidence/contact-sheets/view-labels-source.png','evidence/contact-sheets/music-credits-source.png'],'font_path':str(fontpath),'font_sha256':sha(fontpath.read_bytes()),'font_redistributed':False,'names_policy':'Known character names follow shared glossary; contributor names and organizations retained in original spelling; roles translated','new_name_proposals':{'上条':'가미조 (source raster KamijoView)','汐見トオル':'도루 (source filename トオル and raster ToruView)','汐見牧師':'시오미 (source raster Shiomi View)'},'structural_pass':True,'visual_pass':False,'runtime_review':'user_final_batch'}
(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'translation/text-raster-ko.json').write_text(json.dumps({'translator_model':'Codex internal','task_id':manifest['task_id'],'records':[{'id':r['id'],'source':r['source'],'target':r['target']} for r in reports]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pairs':len(reports),'payloads':len(reports)*2,'out':str(O)},ensure_ascii=False))
