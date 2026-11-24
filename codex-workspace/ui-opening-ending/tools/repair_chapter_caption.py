"""Remove the original Chapter Select p descender missed below the prior source mask."""
from pathlib import Path
import json,numpy as np
from PIL import Image
from decode_ui import ROOT,SRC,decode,sha
from raster_codec import raw_image,encode_array
old=ROOT/'candidates/chapter-raster-v1';out=ROOT/'candidates/chapter-caption-repair-v1';assert not out.exists()
for d in ['payloads','preview','clean','masks']:(out/d).mkdir(parents=True,exist_ok=True)
prior=json.loads((old/'manifest.json').read_text(encoding='utf-8'));finals={};records=[];hashes={}
for rec in prior['entries']:
 name=rec['entry'];source=np.asarray(decode(name)[0]);current=np.asarray(Image.open(old/'preview'/f'{name}.png').convert('RGB'));layer=np.asarray(Image.open(old/'layers'/f'{name}.png'))
 assert not layer[570:580,558:730,3].any(),'Repair must not touch accepted Korean ink'
 # The rule is constant across this local run. Two unlettered sides agree exactly.
 donor=source[571,601].copy();assert np.array_equal(donor,[82,84,113])
 assert np.all(source[571,600:606]==donor) and np.all(source[571,609:614]==donor)
 background=np.zeros((5,14,3),dtype='uint8');background[1]=donor
 region=source[570:575,600:614];erased=np.any(region!=background,axis=2)
 assert int(erased.sum())==23,(name,int(erased.sum()))
 assert np.array_equal(current[570:575,600:614],region)
 final=current.copy();final[570:575,600:614][erased]=background[erased]
 owned=np.zeros((600,800),bool);owned[570:575,600:614]=erased
 assert np.array_equal(final[~owned],current[~owned]);assert not final[570,558:730].any() and not final[572:580,558:730].any()
 assert np.all(final[571,600:614]==donor)
 alpha=255-np.asarray(decode(name[:-4]+'_.rc8')[0].convert('RGB')).astype('uint16').mean(2).astype('uint8');assert np.all(alpha[owned]==255)
 blob0=(old/'payloads'/name).read_bytes();assert sha(blob0)==rec['output_sha256'];raw,prefix,channels=raw_image(blob0);raw[owned]=final[owned]
 if blob0[4:8]==b'TC01':
  base=prefix[22:].rstrip(b'\0').decode('cp932');base=base if base.endswith('.rct') else base+'.rct';bg=finals.get(base,np.asarray(decode(base)[0]));cancel=np.all(raw==[255,0,0],2)&np.any(bg!=final,2);raw[cancel]=final[cancel]
 blob=encode_array(raw,prefix,channels);(out/'payloads'/name).write_bytes(blob);check,pr,ch=raw_image((out/'payloads'/name).read_bytes());assert pr==prefix and ch==channels
 if blob[4:8]==b'TC01':
  skip=np.all(check==[255,0,0],2);check[skip]=bg[skip]
 assert np.array_equal(check,final);finals[name]=final
 Image.fromarray(final).save(out/'preview'/f'{name}.png');Image.fromarray(background).save(out/'clean'/f'{name}.strip.png');Image.fromarray(owned.astype('uint8')*255).save(out/'masks'/f'{name}.source.png')
 hashes[name]=sha(blob);records.append({'entry':name,'previous_sha256':sha(blob0),'output_sha256':sha(blob),'removed_source_pixels':23,'repair_source_region':[600,570,14,5],'background':'original black field and exact same-state uniform rule run at y=571, RGB 82/84/113; matching donors x600:606 and x609:614','outside_repair_diff_pixels':0,'accepted_Korean_ink_changed':False,'alpha_mask_unchanged':True,'metadata_preserved':True,'persisted_effective_decode_equal':True})
# Inspection-only composite; every state has the identical corrected caption region.
n=records[0]['entry'];panels=[np.asarray(Image.open(old/'preview'/f'{n}.png').convert('RGB'))[538:583,550:735],finals[n][538:583,550:735]]
Image.fromarray(np.concatenate(panels,axis=1)).resize((1480,180),Image.Resampling.NEAREST).save(out/'preview/caption-before-after-4x.png')
assert all(np.array_equal(finals[n][538:583,550:735],finals[records[0]['entry']][538:583,550:735]) for n in finals)
m={'translator_model':'Codex internal','task_id':prior['task_id'],'purpose':'Correction only: original English p descender remained below the old source-erasure bounds and crossed the preserved underline','entries':records,'output_hashes':hashes,'semantic_labels':0,'repaired_label_instances':4,'structural_pass':True,'visual_pass':False,'runtime_review':'pending','reuses':{'accepted_translation_and_fonts':'chapter-raster-v1, unchanged','all_other_pixels':'chapter-raster-v1, byte-level image equality outside 23-pixel repair per state'},'detected_by':'evidence/background-runtime/bg-v8-load-restored.json'}
(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'entries':4,'pixels_per_entry':23,'new_semantic_labels':0,'output':str(out)},ensure_ascii=False))
