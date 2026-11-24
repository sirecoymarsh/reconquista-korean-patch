"""Korean tooltip atlas: 12 original 150x20 cells; 11 semantic rows, last blank."""
from pathlib import Path
import json,numpy as np,datetime
from PIL import Image,ImageFont,ImageDraw
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
O=ROOT/'candidates/tooltip-raster-v1'
for d in ['payloads','clean','masks','layers','preview']:(O/d).mkdir(parents=True,exist_ok=True)
rows=[('ゲームデータをセーブします','게임을 저장합니다'),('ゲームデータをロードします','게임을 불러옵니다'),('メッセージを自動クリックします','대사를 자동으로 넘깁니다'),('メッセージをスキップします','대사를 빠르게 넘깁니다'),('システムメニューを呼び出します','시스템 메뉴를 엽니다'),('画面上の文字を消します','화면의 글자를 숨깁니다'),('バックログを表示します','지난 대사를 표시합니다'),('各種設定を行ないます','설정 화면을 엽니다'),('クイックセーブします','빠른 저장을 합니다'),('クイックロードします','빠른 불러오기를 합니다'),('年表を表示します','연표를 표시합니다')]
fontpath=ROOT.parent/'research/fonts/NotoSansCJKkr-Regular.otf';cmap=TTFont(fontpath).getBestCmap();assert all(ord(c) in cmap for _,t in rows for c in t if not c.isspace())
size=13
while True:
 font=ImageFont.truetype(str(fontpath),size);boxes=[font.getbbox(t,stroke_width=2) for _,t in rows]
 if all(b[2]-b[0]<=146 and b[3]-b[1]<=18 for b in boxes):break
 size-=1;assert size>=11
name='ボタン説明.rct';maskname='ボタン説明_.rc8';rgb=np.asarray(decode(name)[0]);mrgb=np.asarray(decode(maskname)[0].convert('RGB')).astype('uint16');alpha=255-(mrgb.sum(2)//3).astype('uint8');assert rgb.shape==(240,150,3)
old=alpha>0;cleanrgb=rgb.copy();cleanrgb[old]=255;cleana=np.zeros_like(alpha);clean=Image.fromarray(cleanrgb).convert('RGBA');clean.putalpha(Image.fromarray(cleana));clean.save(O/'clean/tooltip.png');assert not np.asarray(Image.open(O/'clean/tooltip.png'))[:,:,3].any()
layer=Image.new('RGBA',(150,240));entries=[]
for i,((src,target),box) in enumerate(zip(rows,boxes)):
 one=Image.new('RGBA',(150,240));d=ImageDraw.Draw(one);px=2-box[0];py=round(i*20+10-(box[1]+box[3])/2);d.text((px,py),target,font=font,fill=(255,255,255,255),stroke_width=2,stroke_fill=(35,31,32,255));la=np.asarray(one);ys,xs=np.nonzero(la[:,:,3]);bounds=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1];assert 0<=bounds[0]<bounds[2]<=150 and i*20<=bounds[1]<bounds[3]<=(i+1)*20
 layer.alpha_composite(one);entries.append({'id':f'fastdata.arc::ボタン説明::{i:02d}','source':src,'target':target,'consumer_crop':[0,i*20,150,20],'target_ink_bounds':bounds,'font_size':size})
la=np.asarray(layer);new=la[:,:,3]>0;owned=old|new;finalrgb=cleanrgb.copy();finalrgb[new]=la[new,:3];finalalpha=cleana.copy();finalalpha[new]=la[new,3];assert not finalalpha[220:].any();assert np.array_equal(finalrgb[~owned],rgb[~owned]) and np.array_equal(finalalpha[~owned],alpha[~owned])
rb=(SRC/name).read_bytes();mb=(SRC/maskname).read_bytes();rr,rp,rc=raw_image(rb);mi,mp,mc=raw_image(mb);assert rb[4:8]==b'TC00' and rc==3 and mc==1
pal=np.frombuffer(mp[20:788],dtype='uint8').reshape(256,3);assert np.all(pal[:,0]==pal[:,1]) and np.all(pal[:,0]==pal[:,2]);lookup={int(v):i for i,v in enumerate(pal[:,0])};assert len(lookup)==256
rr[owned]=finalrgb[owned];mi[owned]=np.array([lookup[int(v)] for v in (255-finalalpha)[owned]],dtype='uint8');outputs={name:encode_array(rr,rp,rc),maskname:encode_array(mi,mp,mc)}
for n,b in outputs.items():(O/'payloads'/n).write_bytes(b)
rcheck,_,_=raw_image((O/'payloads'/name).read_bytes());mcheck,checkprefix,_=raw_image((O/'payloads'/maskname).read_bytes());assert checkprefix[20:788]==mp[20:788];assert np.array_equal(rcheck,finalrgb) and np.array_equal(255-pal[mcheck,0],finalalpha)
preview=Image.fromarray(rcheck).convert('RGBA');preview.putalpha(Image.fromarray(finalalpha));preview.save(O/'preview/tooltip.png');layer.save(O/'layers/tooltip.png');Image.fromarray(old.astype('uint8')*255).save(O/'masks/tooltip.source.png')
m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'entries':entries,'semantic_labels':11,'source_hashes':{name:sha(rb),maskname:sha(mb)},'output_hashes':{n:sha(b) for n,b in outputs.items()},'canvas':[150,240],'consumer':{'script':'console.mjo','file_key':'sysdata.cfg SETUMEI_FILE','sprite_definition':'page_len_y / 12; page_len_x; 0; 0','crop':[150,20],'source_script_sha256':sha((ROOT.parent/'research/extracted/scenario/console.mjo').read_bytes())},'clean_plate':'all source text-only alpha removed including outline and fringe; no background art','protected_pixel_diff_count':0,'last_blank_cell_preserved':True,'palette_bytes_identical':True,'persisted_rgb_alpha_exact':True,'font_glyph_coverage_pass':True,'font_sha256':sha(fontpath.read_bytes()),'structural_pass':True,'visual_pass':False,'runtime_review':'pending'}
(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(ROOT/'translation/tooltip-ko.json').write_text(json.dumps({'translator_model':'Codex internal','task_id':m['task_id'],'records':entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'labels':11,'font_size':size,'payloads':2,'preview':str(O/'preview/tooltip.png')},ensure_ascii=False))
