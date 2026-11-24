from pathlib import Path
import json,sys,shutil
U=Path('P:/AI/Codex/projects/reconquista-ko/ui-opening-ending').resolve();B=U.parent
sys.path.insert(0,str(B/'tools'));from inspect_majiro import Arc,sha
base=U/'candidates/ui-trial-v4';out=U/'candidates/ui-trial-v5';out.mkdir(exist_ok=True)
shutil.copy2(base/'scenario.arc',out/'scenario.arc');shutil.copytree(base/'font',out/'font',dirs_exist_ok=True);shutil.copytree(base/'payloads',out/'payloads',dirs_exist_ok=True)
a=Arc(base/'fastdata.arc');raw=a.path.read_bytes();payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries}
sources=[U/'candidates/modal-raster-v1',U/'candidates/text-raster-v1'];new=[]
for folder in sources:
 for p in (folder/'payloads').iterdir():
  assert p.name in payload and p.name not in new;data=p.read_bytes();payload[p.name]=data;new.append(p.name);(out/'payloads/fastdata.arc'/p.name).write_bytes(data)
blob=a.rebuild(payload);(out/'fastdata.arc').write_bytes(blob);read=Arc(out/'fastdata.arc')
assert [e['name'] for e in read.entries]==[e['name'] for e in a.entries]
assert all(blob[e['offset']:e['offset']+e['size']]==payload[e['name']] for e in read.entries)
changed_vs_parent={e['name'] for e in a.entries if raw[e['offset']:e['offset']+e['size']]!=payload[e['name']]}
assert changed_vs_parent==set(new) and len(new)==51
orig=Arc(B/'research/disc/fastdata.arc');ob=orig.path.read_bytes();op={e['name']:ob[e['offset']:e['offset']+e['size']] for e in orig.entries}
m=json.loads((base/'manifest.json').read_text(encoding='utf-8'));m['inherits_static_evidence']='../ui-trial-v4/manifest.json';m['raster_manifests']=['../title-menu-v1/manifest.json','../modal-raster-v1/manifest.json','../text-raster-v1/manifest.json'];m['raster_entries']=35;m['raster_mask_entries_changed']=25;m['raster_semantic_labels']=76;m['status']='partial_ui_static_pass_user_final_runtime_review_pending';m['remaining']=['Remaining raster UI: config, save/load, menu/console, chronicle, names, chapters and extra screens','Timeline CSV and dynamic-name audit','Installer/uninstaller/native remaining surface audit','OP/ED authoring after UI production gate','User final combined runtime review']
for rec in m['archives']:
 if rec['archive']=='fastdata.arc':
  rec['output_sha256']=sha(blob);rec['changed']=[{'entry':name,'source_sha256':sha(op[name]),'output_sha256':sha(data)} for name,data in payload.items() if data!=op[name]]
(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'out':str(out),'added_payloads':len(new),'fastdata_total_changed':len(next(x for x in m['archives'] if x['archive']=='fastdata.arc')['changed']),'raster_images_localized':35,'fastdata_sha256':sha(blob)},ensure_ascii=False))
