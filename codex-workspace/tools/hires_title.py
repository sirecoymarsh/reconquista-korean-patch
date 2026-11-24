"""Rebuild accepted title wording and wordmark at 4x, from proven clean plates."""
from pathlib import Path
import json,hashlib,zlib,subprocess,os
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import numpy as np
R=Path(__file__).resolve().parents[1];U=R/'ui-opening-ending';O=R/'candidates/hires-v1';T=O/'title'
for n in ['clean','background','final']:(T/n).mkdir(parents=True,exist_ok=True)
labels=[('START','처음부터',328),('LOAD','불러오기',369),('CONFIG','설정',410),('EXTRA','추가 메뉴',450),('EXIT','종료',494)]
source_manifest=json.loads((U/'candidates/title-menu-v1/manifest.json').read_text('utf-8'));byname={x['entry']:x for x in source_manifest['entries']}
for v in [1,2,3]:
 arr=[]
 for state in ['off','on','push']:
  n=f'title{v}_{state}.rct';im=Image.open(U/'candidates/brand-logo-ko-v1/clean'/f'{n}.png').convert('RGB');donor=Image.open(U/'candidates/title-menu-v1/clean'/f'{n}.png')
  for _,_,y in labels:im.paste(donor.crop((565,y,708,y+41)),(565,y))
  arr.append(np.asarray(im))
 assert all(np.array_equal(arr[0],a) for a in arr[1:])
 Image.fromarray(arr[0]).save(T/'clean'/f'title{v}.png')
root=Path('P:/AI/Codex/projects/image-upscaling-tools/apps/Upscayl-2.15.0/resources')
with (T/'upscale.log').open('w') as log:
 subprocess.run([str(root/'bin/upscayl-bin.exe'),'-i',str(T/'clean'),'-o',str(T/'background'),'-n','high-fidelity-4x','-m',str(root/'models'),'-s','4','-t','256','-j','1:1:1','-f','png'],stdout=log,stderr=log,check=True,creationflags=0x08000000,cwd=O)
font=ImageFont.truetype('C:/Windows/Fonts/batang.ttc',88,index=0);small=ImageFont.truetype('C:/Windows/Fonts/batang.ttc',22,index=0)
qfont=ImageFont.truetype(str(U/'research/typography/fonts/Eulyoo1945-SemiBold.otf'),44)
quotes=['죽음과 무덤도 불못에 던져졌다.','이 불못이 곧 둘째 죽음이다.','생명책에 이름이 기록되지 않은 사람은','누구든 불못에 던져졌다.']
master=Image.open(U/'candidates/brand-logo-ko-v2/master/reconquista-ko.png').convert('RGBA');old=Image.open(U/'candidates/brand-logo-ko-v1/master/reconquista-ko.png').convert('RGBA');bbox=old.getchannel('A').getbbox();logo=master.crop(bbox).resize((1560,round((bbox[3]-bbox[1])*1560/(bbox[2]-bbox[0]))),Image.Resampling.LANCZOS);rows=[]
for v in [1,2,3]:
 sx,sy=(332,-82) if v==3 else (0,0);base=Image.open(T/'background'/f'title{v}.png').convert('RGBA');al=logo.getchannel('A');x,y=(51+sx)*4,(82+sy)*4
 shadow=Image.new('L',base.size);shadow.paste(al,(x+8,y+12));shadow=shadow.filter(ImageFilter.GaussianBlur(2.6));layer=Image.new('RGBA',base.size,(40,25,34,0));layer.putalpha(shadow.point(lambda n:round(n*.65)));base.alpha_composite(layer);solid=Image.new('RGBA',logo.size,(206,21,60,0));solid.putalpha(al);base.alpha_composite(solid,(x,y));qd=ImageDraw.Draw(base)
 for i,line in enumerate(quotes):
  b=qfont.getbbox(line);px=(101+sx)*4-b[0];py=(341+sy+i*12)*4-b[1];qd.text((px+4,py+4),line,font=qfont,fill=(14,15,25,210));qd.text((px,py),line,font=qfont,fill='white')
 for state in ['off','on','push']:
  n=f'title{v}_{state}.rct';ink=Image.new('L',base.size);d=ImageDraw.Draw(ink);proof=[]
  for row in byname[n]['strings']:
   text=row['target'];b=small.getbbox(text);target=row['target_ink_bbox'];px=(target[0]-b[0])*4;py=(target[1]-b[1])*4;d.text((px,py),text,font=font,fill=255);big=font.getbbox(text);bb=[px+big[0],py+big[1],px+big[2],py+big[3]];cx,cy,cw,ch=row['consumer_crop'];assert bb[0]>=cx*4 and bb[1]>=cy*4 and bb[2]<=(cx+cw)*4 and bb[3]<=(cy+ch)*4;proof.append({'target':text,'bbox':bb,'logical_hitbox':row['consumer_crop']})
  lay=Image.new('RGBA',base.size)
  if state=='on':glow=ink.filter(ImageFilter.GaussianBlur(9.2));color=(255,139,161)
  else:glow=Image.new('L',base.size);glow.paste(ink,(4,4));glow=glow.filter(ImageFilter.GaussianBlur(2));color=(65,77,105)
  gl=Image.new('RGBA',base.size,(*color,0));gl.putalpha(glow);lay.alpha_composite(gl);fg=Image.new('RGBA',base.size,((245,183,74) if state=='push' else (255,255,255))+(0,));fg.putalpha(ink);lay.alpha_composite(fg);out=Image.alpha_composite(base,lay).convert('RGB');key=f'{zlib.crc32(n.encode("cp932")):08x}';fn=O/'assets'/f'{key}.png';out.save(fn);out.save(T/'final'/f'{n}.png');rows.append({'name':n,'key':key,'file':fn.name,'size':[800,600],'output_size':list(out.size),'sha256':hashlib.sha256(fn.read_bytes()).hexdigest(),'labels':proof})
(T/'manifest.json').write_text(json.dumps({'translator_model':'Codex internal','existing_approved_wording_unchanged':True,'font':'Batang88','scale':4,'entries':rows,'clean_plate_proofs_reused':['title-menu-v1','brand-logo-ko-v1'],'logo_master_reused':'brand-logo-ko-v2','button_geometry_unchanged_in_logical_coordinates':True},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'menu_assets':len(rows),'labels':sum(len(r['labels']) for r in rows),'size':[3200,2400]}))
