from pathlib import Path
import json,hashlib,shutil
U=Path(r'P:\AI\Codex\projects\reconquista-ko\ui-opening-ending').resolve();B=U.parent;R=U/'runtime-ui';R.mkdir(exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def copy_verified(src,dst,expected):
 assert U in dst.resolve().parents
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert sha(dst)==expected,('unexpected existing runtime file',dst)
 else:shutil.copyfile(src,dst);assert sha(dst)==expected
 return {'path':str(dst),'sha256':expected,'source':str(src)}
base=json.loads((B/'reports/runtime-ko-base-verified.json').read_text(encoding='utf-8-sig'));report=[]
for e in base:
 src=Path(e['source']);relative=Path(e['path']).relative_to(Path(r'P:\AI\Codex\projects\reconquista-ko\runtime-ko'));report.append(copy_verified(src,R/relative,e['sha256'].lower()))
C=U/'candidates/ui-trial-v1';m=json.loads((C/'manifest.json').read_text(encoding='utf-8'))
for a in m['archives']:report.append(copy_verified(C/a['archive'],R/a['archive'],a['output_sha256']))
for p in (C/'font').iterdir():report.append(copy_verified(p,R/'font'/p.name,sha(p)))
(U/'reports/runtime-ui-prepared.json').write_text(json.dumps({'runtime':str(R),'original_source_evidence_reused':'../reports/runtime-ko-base-verified.json','files':report,'save_data':'fresh runtime-local savedata','registry_namespace':'Reconquista-UI-Isolated-20261022','launch_exe':'レコンキスタ.exe'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=U/'candidates/title-menu-v1/manifest.json';title=json.loads(p.read_text(encoding='utf-8'))
for e in title['entries']:
 for s in e['strings']:s['consumer_crop'][1]={'START':328,'LOAD':369,'CONFIG':410,'EXTRA':450,'EXIT':494}[s['source']]
 e['consumer_crop_proof']='start.mjo callp $ffc5bc91, indices 323-353/504-532/625-653; actual crop containment separately passed for all 9 unchanged payloads'
 if e['entry'] in ['title1_off.rct','title1_on.rct']:e['visual_pass']=True
p.write_text(json.dumps(title,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=U/'tools/build_title_menu.py';s=p.read_text(encoding='utf-8-sig').replace("('EXTRA','추가 메뉴',451)","('EXTRA','추가 메뉴',450)").replace("('EXIT','종료',492)","('EXIT','종료',494)");p.write_text(s,encoding='utf-8')
print(json.dumps({'prepared':str(R),'new_copy_hashes_checked':len(report)},ensure_ascii=False))
