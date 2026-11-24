"""Package image_gen's revised center glyph without changing surrounding approved art."""
from pathlib import Path
import sys,json,hashlib,shutil,numpy as np
from PIL import Image,ImageDraw,ImageFilter
R=Path(__file__).resolve().parents[1];U=R/'ui-opening-ending';V1=U/'candidates/brand-logo-ko-v1';V2=U/'candidates/brand-logo-ko-v2';O=U/'candidates/brand-logo-ko-v3'
sys.path.insert(0,str(U/'tools'))
from raster_codec import raw_image,encode_array
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n','utf-8')
assert not O.exists(),'New revision only'
for n in ['master','payloads','preview','layers','masks','hd/assets','hd/title/final']:(O/n).mkdir(parents=True,exist_ok=True)
gen=Path('P:/AI/Codex/generated_images/01a16283-b393-7dc0-8c83-d3e23a2a2f41/exec-29ef5180-9b7a-4e60-a68d-3f5f70247630.png')
old=Image.open(V1/'master/reconquista-ko.png').convert('RGBA');edit=Image.open(gen).convert('RGBA');assert old.size==edit.size==(1619,971)
# Import only the generated central glyph. The contour follows the blank gutters
# between neighboring glyphs, including removal of the former extra small upright.
polygon=[(585,0),(975,0),(975,350),(950,350),(950,530),(942,580),(923,600),(901,620),(888,640),(882,660),(882,720),(920,950),(720,950),(720,700),(608,700),(608,663),(680,620),(716,584),(741,553),(712,558),(665,541),(631,526),(625,498),(680,480),(738,452),(736,445),(663,456),(630,432),(605,405),(585,350)]
mask=Image.new('L',old.size);ImageDraw.Draw(mask).polygon(polygon,fill=255);m=np.asarray(mask)>0
a=np.asarray(old).copy();b=np.asarray(edit)
a[m,3]=b[m,3];a[m,:3]=[206,21,60]
a[m&(a[:,:,3]==0),:3]=0
assert np.array_equal(a[~m],np.asarray(old)[~m])
master=Image.fromarray(a);master.save(O/'master/reconquista-ko.png');mask.save(O/'masks/master-edit-region.png');shutil.copy2(gen,O/'master/imagegen-source.png')
bbox=old.getchannel('A').getbbox();logo=master.crop(bbox).resize((390,round((bbox[3]-bbox[1])*390/(bbox[2]-bbox[0]))),Image.Resampling.LANCZOS)
prev=json.loads((V1/'manifest.json').read_text('utf-8'));rows=[]
for row in prev['entries']:
 name=row['entry'];v=int(name[5]);sx,sy=(332,-82) if v==3 else (0,0);x,y=51+sx,82+sy
 oldlayer=np.asarray(Image.open(V1/'layers'/(name+'.png')).convert('RGBA'));layer=Image.new('RGBA',(800,600))
 al=logo.getchannel('A');solid=Image.new('RGBA',logo.size,(206,21,60,0));solid.putalpha(al)
 sa=Image.new('L',(800,600));sa.paste(al,(x+2,y+3));sa=sa.filter(ImageFilter.GaussianBlur(.65));shadow=Image.new('RGBA',(800,600),(40,25,34,0));shadow.putalpha(sa.point(lambda n:round(n*.65)));layer=Image.alpha_composite(layer,shadow);layer.alpha_composite(solid,(x,y))
 la=np.asarray(layer).copy();la[338+sy:397+sy]=oldlayer[338+sy:397+sy];layer=Image.fromarray(la)
 clean=Image.open(V1/'clean'/(name+'.png')).convert('RGBA');final=np.asarray(Image.alpha_composite(clean,layer).convert('RGB'))
 prior,pre,c=raw_image((V2/'payloads'/name).read_bytes());delta=np.any(final!=prior,2);yy,xx=np.nonzero(delta)
 assert xx.min()>=x-8 and xx.max()<x+250 and yy.min()>=y-5 and yy.max()<y+240,(name,[xx.min(),yy.min(),xx.max(),yy.max()])
 encoded=encode_array(final,pre,c);(O/'payloads'/name).write_bytes(encoded);decoded,p2,c2=raw_image(encoded)
 assert np.array_equal(decoded,final);assert encode_array(final,pre,c)==encoded;assert p2[:16]==pre[:16] and p2[20:]==pre[20:]
 Image.fromarray(final).save(O/'preview'/(name+'.png'));layer.save(O/'layers'/(name+'.png'))
 r=dict(row);r.update(base_candidate_sha256=sha(V2/'payloads'/name),output_sha256=sha(O/'payloads'/name),base_candidate='brand-logo-ko-v2',revision_changed_pixels=int(delta.sum()),revision_bounds=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],metadata_preserved=True,deterministic_encoding=True,visual_pass=False,runtime_review='user_pending');rows.append(r)
prov={'translator_model':'Codex internal','task_id':'01a16283-b393-7dc0-8c83-d3e23a2a2f41','exact_text':'레콘키스타','renderer':'built-in image_gen; deterministic bounded alpha integration','imagegen_source':str(gen),'source_sha256':sha(gen),'base':str(V1/'master/reconquista-ko.png'),'base_sha256':sha(V1/'master/reconquista-ko.png'),'edit_polygon':polygon,'outside_polygon_identical_to_v1':True,'crop_bbox_reused':list(bbox),'user_revision':'Remove small extra upright; move large cross pillar right; attach both lower left-reaching arms to the pillar; restore pointed initial 레 flourish.','prompt':'Preserve latest connected center cross design, clean floating speckles, restore source other letters and initial pointed flourish. Transparent 1619x971 solid crimson.'}
dump(O/'master/provenance.json',prov)
mfest=dict(prev);mfest.update(status='structural_pass_visual_review_pending',master_sha256=sha(O/'master/reconquista-ko.png'),entries=rows,ready_for_integration=False,frozen=False,revision='v3 connected central strokes and restored initial flourish',replaces_candidate='brand-logo-ko-v2')
dump(O/'manifest.json',mfest)
# Use the established high-resolution compositor, changing only its input master
# and output location; proven upscaled backgrounds are reused without re-upscaling.
source=(R/'tools/hires_title.py').read_text('utf-8')
start=source.index("font=ImageFont")
tail=source[start:].replace("brand-logo-ko-v2/master","brand-logo-ko-v3/master")
tail=tail.replace("T/'background'","H/'title/background'")
tail=tail.replace("'logo_master_reused':'brand-logo-ko-v2'","'logo_master_reused':'brand-logo-ko-v3'")
env=dict(R=R,U=U,O=O/'hd',T=O/'hd/title',H=R/'candidates/hires-v1')
exec("import json,hashlib,zlib\nfrom PIL import Image,ImageDraw,ImageFont,ImageFilter\n"+
     "source_manifest=json.loads((U/'candidates/title-menu-v1/manifest.json').read_text('utf-8'));byname={x['entry']:x for x in source_manifest['entries']}\n"+tail,env)
hd=json.loads((O/'hd/title/manifest.json').read_text('utf-8'))
for row in hd['entries']:
 n=row['name'];v=int(n[5]);sx,sy=(332,-82) if v==3 else (0,0);x,y=(51+sx)*4,(82+sy)*4
 new=np.asarray(Image.open(O/'hd/assets'/row['file']));prior=np.asarray(Image.open(R/'candidates/hires-v1/assets'/row['file']))
 delta=np.any(new!=prior,2);yy,xx=np.nonzero(delta)
 assert xx.min()>=x-32 and xx.max()<x+1000 and yy.min()>=y-20 and yy.max()<y+960,(n,[xx.min(),yy.min(),xx.max(),yy.max()])
 row.update(bytes=(O/'hd/assets'/row['file']).stat().st_size,changed_pixels=int(delta.sum()),change_bounds=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],unchanged_menu_quote_background=True)
dump(O/'hd/title/manifest.json',hd)
print(json.dumps({'candidate':str(O),'master_sha256':sha(O/'master/reconquista-ko.png'),'lowres':len(rows),'hires':len(hd['entries']),'pixel_invariants_pass':True},ensure_ascii=False))

