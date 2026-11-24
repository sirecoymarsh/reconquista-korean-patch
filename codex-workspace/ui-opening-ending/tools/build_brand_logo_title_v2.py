from pathlib import Path
import json,shutil,hashlib,numpy as np
from PIL import Image,ImageFilter
from raster_codec import raw_image,encode_array
U=Path.cwd();V1=U/'candidates/brand-logo-ko-v1';O=U/'candidates/brand-logo-ko-v2'
for d in ['master','payloads','preview','layers','masks']:(O/d).mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
gen=Path('P:/AI/Codex/generated_images/01a162df-720c-77d2-96ed-6429e90b3333/exec-9b1adfdc-25e6-4d6d-a817-7bdfbd9e40e6.png')
old=Image.open(V1/'master/reconquista-ko.png').convert('RGBA');edit=Image.open(gen).convert('RGBA');assert old.size==edit.size
# Deterministic placement of the imagegen edit. Only its first rising stroke is
# imported. Every other glyph pixel is retained from the accepted v1 master.
a=np.asarray(old).copy();b=np.asarray(edit);w=np.zeros(a.shape[:2],np.float32);w[:500,:245]=1
for y in range(500,550):w[y,:245]=(550-y)/50
for x in range(225,245):w[:,x]*=(245-x)/20
alpha=np.rint(a[:,:,3]*(1-w)+b[:,:,3]*w).astype('uint8');a[:,:,3]=alpha
# RGB is immaterial at zero alpha; retain the original accepted crimson color.
changed=w>0;a[changed,:3]=[206,21,60]
master=Image.fromarray(a);master.save(O/'master/reconquista-ko.png');shutil.copy2(gen,O/'master/imagegen-local-edit-source.png')
assert np.array_equal(a[~changed],np.asarray(old)[~changed])
bbox=old.getchannel('A').getbbox();logo=master.crop(bbox).resize((390,round((bbox[3]-bbox[1])*390/(bbox[2]-bbox[0]))),Image.Resampling.LANCZOS)
prev=json.loads((V1/'manifest.json').read_text(encoding='utf-8'));rows=[]
for row in prev['entries']:
 name=row['entry'];v=int(name[5]);sx,sy=(332,-82) if v==3 else (0,0);x,y=51+sx,82+sy
 oldlayer=np.asarray(Image.open(V1/'layers'/(name+'.png')).convert('RGBA'));layer=Image.new('RGBA',(800,600))
 al=logo.getchannel('A');solid=Image.new('RGBA',logo.size,(206,21,60,0));solid.putalpha(al)
 sa=Image.new('L',(800,600));sa.paste(al,(x+2,y+3));sa=sa.filter(ImageFilter.GaussianBlur(.65));shadow=Image.new('RGBA',(800,600),(40,25,34,0));shadow.putalpha(sa.point(lambda n:round(n*.65)));layer=Image.alpha_composite(layer,shadow);layer.alpha_composite(solid,(x,y))
 # Reuse verified quotation pixels verbatim. Its rows do not overlap the logo.
 la=np.asarray(layer).copy();la[338+sy:397+sy]=oldlayer[338+sy:397+sy];layer=Image.fromarray(la)
 clean=Image.open(V1/'clean'/(name+'.png')).convert('RGBA');final=np.asarray(Image.alpha_composite(clean,layer).convert('RGB'))
 prior,pre,c=raw_image((V1/'payloads'/name).read_bytes());delta=np.any(final!=prior,2);yy,xx=np.nonzero(delta)
 assert xx.min()>=x-3 and xx.max()<x+65 and yy.min()>=y and yy.max()<y+140,(name,[xx.min(),yy.min(),xx.max(),yy.max()])
 encoded=encode_array(final,pre,c);(O/'payloads'/name).write_bytes(encoded);decoded,p2,c2=raw_image(encoded);assert np.array_equal(decoded,final);assert encode_array(final,pre,c)==encoded;assert p2[:16]==pre[:16] and p2[20:]==pre[20:]
 assert not np.all(final==[255,0,0],2).any()
 Image.fromarray(final).save(O/'preview'/(name+'.png'));layer.save(O/'layers'/(name+'.png'));Image.fromarray((delta*255).astype('uint8')).save(O/'masks'/(name+'.revision.png'))
 r=dict(row);r.update(base_candidate_sha256=sha(V1/'payloads'/name),output_sha256=sha(O/'payloads'/name),base_candidate='brand-logo-ko-v1',revision_changed_pixels=int(delta.sum()),revision_bounds=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],outside_revision_region_diff_count=0,source_donor_evidence_reused='../brand-logo-ko-v1/manifest.json',visual_pass=False);rows.append(r)
for v in [1,2,3]:
 im1=Image.open(V1/'preview'/f'title{v}_off.rct.png');im2=Image.open(O/'preview'/f'title{v}_off.rct.png');pair=Image.new('RGB',(1600,600));pair.paste(im1);pair.paste(im2,(800,0));pair.save(O/'preview'/f'title{v}-before-after.png')
prov={'translator_model':'Codex internal','task_id':prev['task_id'],'exact_text':'레콘키스타','renderer':'built-in image_gen; deterministic local layer integration','imagegen_source':str(gen),'source_sha256':sha(gen),'accepted_master_base':str(V1/'master/reconquista-ko.png'),'base_sha256':sha(V1/'master/reconquista-ko.png'),'local_edit_master_bounds':[0,0,245,550],'blend_transition_y':[500,550],'all_pixels_outside_local_edit_identical':True,'crop_bbox_reused':list(bbox),'user_revision':'Reduce initial 레 rising stroke; preserve other syllables and central 키 focal ascender.'}
(O/'master/provenance.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
m=dict(prev);m.update(status='structural_pass_visual_review_pending',master_sha256=sha(O/'master/reconquista-ko.png'),entries=rows,ready_for_integration=False,frozen=False,revision='v2: shorten only initial 레 upward stroke',semantic_fields_added=0,replaces_candidate='brand-logo-ko-v1',visual_review='pending changed-stroke inspection; prior menu/quote/donor proofs reused');(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'candidate':str(O),'entries':len(rows),'bounds':[(r['entry'],r['revision_bounds']) for r in rows]},ensure_ascii=False))
