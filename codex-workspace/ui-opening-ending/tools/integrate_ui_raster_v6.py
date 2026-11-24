from pathlib import Path
import json,sys,shutil,datetime
from fontTools.ttLib import TTFont
from PIL import Image
import numpy as np
U=Path('P:/AI/Codex/projects/reconquista-ko/ui-opening-ending').resolve();B=U.parent
sys.path.insert(0,str(B/'tools'));from inspect_majiro import Arc,sha
base=U/'candidates/ui-trial-v5';out=U/'candidates/ui-trial-v6';folder=U/'candidates/chapter-raster-v1'
assert not out.exists(), 'Do not overwrite an existing candidate'
chapter=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
font=TTFont(B/'research/fonts/NotoSerifCJKkr-Regular.otf');cmap=font.getBestCmap();targets=[s['target'] for r in chapter['entries'] for s in r['strings']];assert all(ord(c) in cmap for t in targets for c in t if not c.isspace())
a0=np.asarray(Image.open(folder/'preview/chapter_off_2.rct.png').convert('RGB'));regions={'attribution':[320,383,480,410],'footer':[82,502,522,572],'chapter_label':[558,543,729,570]};same={}
for n in ['chapter_on.rct.png','chapter_push.rct.png']:
 arr=np.asarray(Image.open(folder/'preview'/n).convert('RGB'));same[n]={}
 for k,(x,y,X,Y) in regions.items():
  eq=bool(np.array_equal(a0[y:Y,x:X],arr[y:Y,x:X]));assert eq;(same[n])[k]={'equal_to_visually_reviewed_off_2':eq,'nonblack_pixels':int(np.any(arr[y:Y,x:X]>0,axis=2).sum())}
chapter.update(visual_pass=True,target_font_glyph_coverage_pass=True,visual_review={'off_1':'earlier direct full-image review reused','off_2':'direct full-image review passed','on_push':'colored quote states reviewed directly; identical static footer/attribution/label regions reuse off_2 inspection','static_region_identity':same},runtime_review='not_run_for_chapter; user_final_batch_or_future_private_desktop')
(folder/'manifest.json').write_text(json.dumps(chapter,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
a=Arc(base/'fastdata.arc');raw=a.path.read_bytes();before={e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries};payload=dict(before);new=[]
for r in chapter['entries']:
 n=r['entry'];data=(folder/'payloads'/n).read_bytes();assert sha(data)==r['output_sha256'];assert n in payload and n not in new;payload[n]=data;new.append(n)
assert len(new)==4 and {n for n in payload if payload[n]!=before[n]}==set(new)
out.mkdir();shutil.copy2(base/'scenario.arc',out/'scenario.arc');shutil.copytree(base/'font',out/'font');shutil.copytree(base/'payloads',out/'payloads')
blob=a.rebuild(payload);(out/'fastdata.arc').write_bytes(blob);check=Arc(out/'fastdata.arc');assert [e['name'] for e in check.entries]==[e['name'] for e in a.entries];assert all(blob[e['offset']:e['offset']+e['size']]==payload[e['name']] for e in check.entries)
for n in new:(out/'payloads/fastdata.arc'/n).write_bytes(payload[n])
m=json.loads((base/'manifest.json').read_text(encoding='utf-8'));m['inherits_static_evidence']='../ui-trial-v5/manifest.json';m['raster_manifests'].append('../chapter-raster-v1/manifest.json');m['raster_entries']=39;m['raster_semantic_labels']=100;m['new_payloads_exactly']=new;m['unchanged_v5_payloads_reused']=True
fast_rec=next(r for r in m['archives'] if r['archive']=='fastdata.arc');old_names={r['entry'] for r in fast_rec['changed']};assert not old_names.intersection(new)
fast_rec['output_sha256']=sha(blob);fast_rec['changed'] += [{'entry':r['entry'],'source_sha256':r['source_sha256'],'output_sha256':r['output_sha256']} for r in chapter['entries']]
assert sha((out/'scenario.arc').read_bytes())==next(r['output_sha256'] for r in m['archives'] if r['archive']=='scenario.arc')
m['remaining']=['Remaining raster UI: config, save/load, menu/console, tooltip, chronicle, names and extra screens','Timeline CSV and dynamic-name audit','Installer/uninstaller/native remaining surface audit','OP/ED authoring after UI production gate','Remaining private-desktop state coverage and user final combined runtime review'];(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=U/'progress.json';g=json.loads(p.read_text(encoding='utf-8'));g['updated_local']=datetime.datetime.now().astimezone().isoformat();g['completed'].append('Chapter 4 states / 24 labels visual and glyph coverage passed; integrated exactly 4 new payloads into ui-trial-v6');g['current_integrated_candidate']='candidates/ui-trial-v6';g['current_counts'].update(raster_entries_integrated=39,raster_labels_integrated=100,chapter_entries_pending_integration=0,chapter_labels_pending_integration=0);g['usage_checkpoint'].update(remaining_percent=2,checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());g['artifacts'].append('candidates/ui-trial-v6/manifest.json');g['next_action']='Check included allowance and stop marker first; build 11-row tooltip atlas (150x240, consumer rows 150x20), integrate into next candidate, then remaining UI. Private-desktop v5 modal validation is complete; chapter runtime pending.';p.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'candidate':str(out),'new_payloads':len(new),'raster_entries':39,'raster_labels':100,'fastdata_sha256':sha(blob)},ensure_ascii=False))
