"""Six transparent extra-menu states, preserving footer and original button crops."""
from pathlib import Path
import json,collections,numpy as np
from PIL import Image,ImageFont,ImageDraw
from fontTools.ttLib import TTFont
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
O=ROOT/'candidates/extra-raster-v1'
for d in ['payloads','clean','masks','layers','preview']:(O/d).mkdir(parents=True,exist_ok=True)
fontpath=ROOT.parent/'research/fonts/NotoSerifCJKkr-Regular.otf';font=ImageFont.truetype(str(fontpath),22);cmap=TTFont(fontpath).getBestCmap()
standard=[('年表','연표'),('サウンドモード','음악 감상'),('CGモード','CG 감상'),('回想モード','장면 회상')];reports=[];outputs={}
for prefix,ys,labels in [('extra',[328,369,410,450,494],standard+[('前の画面に戻る','뒤로')]),('extra2',[308,349,390,430,474,512],standard+[('スタッフルーム','스태프룸'),('前の画面に戻る','뒤로')])]:
 for state in ['off','on','push']:
  stem=prefix+'_'+state;name=stem+'.rct';maskname=stem+'_.rc8';rgb=np.asarray(decode(name)[0]);mrgb=np.asarray(decode(maskname)[0].convert('RGB')).astype('uint16');alpha=255-(mrgb.sum(2)//3).astype('uint8');slots=np.zeros((600,800),bool)
  for y in ys:slots[y:y+40,547:780]=True
  old=(alpha>0)&slots;cleanrgb=rgb.copy();cleanrgb[old]=255;cleana=alpha.copy();cleana[old]=0;assert not cleana[slots].any()
  clean=Image.fromarray(cleanrgb).convert('RGBA');clean.putalpha(Image.fromarray(cleana));clean.save(O/'clean'/f'{stem}.png')
  outline=old&(alpha<200)&(rgb.mean(2)<210)&(rgb.mean(2)>40);assert outline.any();color=tuple(np.median(rgb[outline],axis=0).round().astype(int).tolist());opacity=int(np.quantile(alpha[outline],.9).round());layer=Image.new('RGBA',(800,600));strings=[]
  for (src,target),y in zip(labels,ys):
   assert all(ord(c) in cmap for c in target if not c.isspace());sub=(alpha[y:y+40,547:780]>0);iy,ix=np.nonzero(sub);center=y+(int(iy.min())+int(iy.max()))/2;box=font.getbbox(target,stroke_width=2);one=Image.new('RGBA',(800,600));draw=ImageDraw.Draw(one);draw.text((594-box[0],round(center-(box[1]+box[3])/2)),target,font=font,fill=(255,255,255,255),stroke_width=2,stroke_fill=(*color,opacity));draw.text((594-box[0],round(center-(box[1]+box[3])/2)),target,font=font,fill=(255,255,255,255),stroke_width=1,stroke_fill=(255,255,255,255));yy,xx=np.nonzero(np.asarray(one)[:,:,3]);bounds=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];assert 547<=bounds[0]<bounds[2]<=780 and y<=bounds[1]<bounds[3]<=y+40;layer.alpha_composite(one);strings.append({'id':f'fastdata.arc::{name}::{src}','source':src,'target':target,'consumer_crop':[547,y,233,40],'ink_bounds':bounds})
  la=np.asarray(layer);new=la[:,:,3]>0;owned=old|new;frgb=cleanrgb.copy();frgb[new]=la[new,:3];fa=cleana.copy();fa[new]=la[new,3];assert np.array_equal(frgb[~owned],rgb[~owned]) and np.array_equal(fa[~owned],alpha[~owned]);assert not np.any(np.all(frgb==[255,0,0],axis=2))
  rb=(SRC/name).read_bytes();mb=(SRC/maskname).read_bytes();_,rp,rc=raw_image(rb);mi,mp,mc=raw_image(mb);pal=np.frombuffer(mp[20:788],dtype='uint8').reshape(256,3);assert np.all(pal[:,0]==pal[:,1]) and np.all(pal[:,0]==pal[:,2]);look={int(v):i for i,v in enumerate(pal[:,0])};assert len(look)==256;mi[owned]=np.array([look[int(v)] for v in (255-fa)[owned]],dtype='uint8');ob=encode_array(frgb,rp,rc);om=encode_array(mi,mp,mc)
  for n,b in [(name,ob),(maskname,om)]:(O/'payloads'/n).write_bytes(b);outputs[n]=sha(b)
  ri,_,_=raw_image((O/'payloads'/name).read_bytes());ma,mp2,_=raw_image((O/'payloads'/maskname).read_bytes());assert np.array_equal(ri,frgb) and np.array_equal(255-pal[ma,0],fa) and mp2[20:788]==mp[20:788]
  preview=Image.fromarray(ri).convert('RGBA');preview.putalpha(Image.fromarray(fa));preview.save(O/'preview'/f'{stem}.png');Image.alpha_composite(Image.new('RGBA',(800,600),(36,42,63,255)),preview).convert('RGB').save(O/'preview'/f'{stem}.on-dark.png');layer.save(O/'layers'/f'{stem}.png');Image.fromarray(old.astype('uint8')*255).save(O/'masks'/f'{stem}.source.png')
  reports.append({'entry':name,'mask_entry':maskname,'source_hashes':{name:sha(rb),maskname:sha(mb)},'output_hashes':{name:sha(ob),maskname:sha(om)},'strings':strings,'state':state,'outline_color_from_source_median':color,'outline_alpha_from_source_90th_percentile':opacity,'clean_plate':'transparent original menu text layer; existing copyright/footer alpha retained exactly','protected_pixel_diff_count':0,'persisted_decode_pass':True,'palette_preserved':True,'header_metadata_preserved':True})
m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','entries':reports,'output_hashes':outputs,'semantic_labels':33,'source_consumer':'start.mjo, $buttonmenu_set@BUTONMENU, 0x1ddf..0x1eaf and 0x2477..0x2575','font_glyph_coverage_pass':True,'font_sha256':sha(fontpath.read_bytes()),'structural_pass':True,'visual_pass':False,'runtime_review':'pending'};(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(ROOT/'translation/extra-menu-ko.json').write_text(json.dumps({'translator_model':'Codex internal','task_id':m['task_id'],'records':[s for r in reports for s in r['strings']]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Review the tooltip with alpha actually composited, keeping production pixels untouched.
t=ROOT/'candidates/tooltip-raster-v1/preview/tooltip.png';im=Image.open(t).convert('RGBA');Image.alpha_composite(Image.new('RGBA',im.size,(52,54,67,255)),im).convert('RGB').save(t.with_name('tooltip-on-dark.png'))
print(json.dumps({'states':6,'labels':33,'payloads':len(outputs),'colors':{r['entry']:[r['outline_color_from_source_median'],r['outline_alpha_from_source_90th_percentile']] for r in reports}},ensure_ascii=False))
