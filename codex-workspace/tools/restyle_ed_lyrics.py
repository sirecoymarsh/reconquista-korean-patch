"""Render only the changed ED lyric typography using the user's selected subtitle family."""
from pathlib import Path
import sys,json,os,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'tools'),str(R/'ui-opening-ending/tools')]
from inspect_majiro import dump,sha
from raster_codec import raw_image,encode_array
A=R/'builds/ed-lyrics-overlay-v2';C=R/'builds/ed-lyrics-overlay-v3';assert not C.exists();C.mkdir()
for d in ['payloads','preview','evidence']:(C/d).mkdir()
for name in ['semantic-inputs.json','payloads/staffroll.mjo','evidence/staffroll-patched.mjil','evidence/control-flow-review.json']:os.link(A/name,C/name)
m=json.loads((A/'manifest.json').read_text(encoding='utf-8'));rows=json.loads((A/'semantic-inputs.json').read_text(encoding='utf-8'))['records']
fontpath=R/'ui-opening-ending/research/typography/fonts/Eulyoo1945-SemiBold.otf';assert sha(fontpath.read_bytes())=='1f2b498cae74bac4c37ce616ab6ac0ced85e33b6c666f95e67c9a9e01dc82928';cmap=TTFont(fontpath).getBestCmap();assert all(ord(c) in cmap for r in rows for c in r['target']);font=ImageFont.truetype(str(fontpath),30)
_,cp,_=raw_image((A/'payloads/kr_ed_001.rct').read_bytes());_,mp,_=raw_image((A/'payloads/kr_ed_001_.rc8').read_bytes());palette=np.frombuffer(mp[20:788],dtype='uint8').reshape(256,3);inv=np.empty(256,dtype='uint8');inv[palette[:,0]]=np.arange(256,dtype='uint8');W,H=800,38;assets=[];stats=[];images=[]
for j,row in enumerate(rows,1):
 im=Image.new('RGBA',(W,H));dr=ImageDraw.Draw(im);box=dr.textbbox((0,0),row['target'],font=font,stroke_width=1);tw,th=box[2]-box[0],box[3]-box[1];assert tw<=760 and th<=34,(row['id'],tw,th)
 dr.text(((W-tw)//2-box[0],(H-th)//2-box[1]),row['target'],font=font,fill=(255,255,255,255),stroke_width=1,stroke_fill=(0,0,0,255));ar=np.asarray(im);yy,xx=np.nonzero(ar[:,:,3]);assert xx.min()>0 and xx.max()<799 and yy.min()>0 and yy.max()<37
 base=f'kr_ed_{j:03d}'
 for n,arr,prefix,ch in [(base+'.rct',ar[:,:,:3].copy(),cp,3),(base+'_.rc8',inv[255-ar[:,:,3]],mp,1)]:
  enc=encode_array(arr,prefix,ch);(C/'payloads'/n).write_bytes(enc);out,_,_=raw_image(enc);assert np.array_equal(out,arr);assets.append({'entry':n,'sha256':sha(enc),'size':[W,H]})
 im.save(C/'preview'/(base+'.png'));images.append(im);stats.append({'id':row['id'],'target':row['target'],'start_ms':round(row['start']*1000),'end_ms':round(row['end']*1000),'asset':base,'ink_bbox':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'placement':[0,8,W,H],'font_px':30,'stroke_px':1,'target_containment_pass':True})
for group in range(4):
 sheet=Image.new('RGBA',(800,8*48),(35,40,50,255));dr=ImageDraw.Draw(sheet)
 for k,im in enumerate(images[group*8:(group+1)*8]):sheet.alpha_composite(im,(0,k*48+5));dr.line((0,k*48+47,799,k*48+47),fill=(90,95,105,255))
 sheet.convert('RGB').save(C/'preview'/f'contact-{group+1}.png')
plate=Image.open(R/'ui-opening-ending/candidates/ending-credits-raster-v1/preview/staffrollb_001.rct.png').convert('RGBA');plate.alpha_composite(images[13],(0,8));plate.convert('RGB').save(C/'preview/credits-overlay-layout.png')
m['assets']=assets;m['typography']={'family':'Eulyoo1945 SemiBold','source':str(fontpath),'font_sha256':sha(fontpath.read_bytes()),'font_px':30,'stroke_px':1,'all_target_codepoints_present':True,'user_preference':'Matches subtitle font selection in UI/OP/ED thread on 2026-10-23; source font unmodified, only baked raster distributed'};m['script_verification_reused_from']=str(A);m['visual_review']=False;m['layout_containment_pass']=True;dump(C/'evidence/layout.json',stats);dump(C/'manifest.json',m);print(json.dumps({'candidate':str(C),'family':m['typography']['family'],'script_unchanged':m['script']['output_sha256'],'assets':64,'max_ink_width':max(r['ink_bbox'][2]-r['ink_bbox'][0] for r in stats)},ensure_ascii=False))