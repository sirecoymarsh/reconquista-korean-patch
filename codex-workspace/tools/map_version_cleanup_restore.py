"""Record retained-file or backup-object restoration sources without deleting files."""
from pathlib import Path
import json,os,hashlib,zipfile
R=Path(__file__).resolve().parents[1];O=R/'reports/version-cleanup-20261023';plan=json.loads((O/'plan.json').read_text('utf-8'))
with zipfile.ZipFile(O/'saves-and-evidence.zip') as z:idx=json.loads(z.read('index.json'))
archived={x['path'].replace('\\','/'):x for x in idx['files']};roots=plan['candidate_runtime_directories']+plan['candidate_prototype_directories']
bykey={};byname={}
retained=list((R/'builds').iterdir())+[R/x for x in ['runtime','runtime-body-ui-20261023-v9','runtime-body-ui-20261023-v12-input-logo','runtime-body-ui-20261023-v13-config']]
for root in retained:
 for base,dirs,files in os.walk(root,followlinks=False):
  dirs[:]=[d for d in dirs if not (getattr(Path(base,d).stat(follow_symlinks=False),'st_file_attributes',0)&0x400)]
  for n in files:
   p=Path(base,n);s=p.stat(follow_symlinks=False);bykey.setdefault((s.st_dev,s.st_ino),p);byname.setdefault((n.lower(),s.st_size),[]).append(p)
hashes={}
def sha(p):
 s=p.stat();key=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
 if key not in hashes:hashes[key]=hashlib.sha256(p.read_bytes()).hexdigest()
 return hashes[key]
rows=[];missing=[]
for name in roots:
 for base,dirs,files in os.walk(R/name,followlinks=False):
  dirs[:]=[d for d in dirs if not (getattr(Path(base,d).stat(follow_symlinks=False),'st_file_attributes',0)&0x400)]
  for n in files:
   p=Path(base,n);rel=p.relative_to(R).as_posix();s=p.stat(follow_symlinks=False);row={'path':rel,'bytes':s.st_size}
   if rel in archived:
    a=archived[rel];row.update(kind='archive',archive_entry=a['archive_entry'],sha256=a['sha256'])
   elif (s.st_dev,s.st_ino) in bykey:
    source=bykey[(s.st_dev,s.st_ino)];ss=source.stat();row.update(kind='retained_hardlink',source=source.relative_to(R).as_posix(),file_id=str(ss.st_ino),mtime_ns=ss.st_mtime_ns,verification='same NTFS file identity; reuse existing asset verification')
   else:
    expected=sha(p);same=next((q for q in byname.get((n.lower(),s.st_size),[]) if sha(q)==expected),None)
    if same:row.update(kind='retained_equal_bytes',source=same.relative_to(R).as_posix(),sha256=expected)
    else:missing.append(rel);continue
   rows.append(row)
assert not missing,missing
(O/'restore-map.json').write_text(json.dumps({'workspace':str(R.resolve()),'archive':'saves-and-evidence.zip','records':rows,'junctions':plan['links_not_followed'],'instruction':'Recreate only selected original paths from the saved archive objects or named retained source files; preserve savedata as independent copies. Match recorded SHA or unchanged NTFS identity/size/mtime before restoring. Never overwrite a differing existing file.'},ensure_ascii=False,indent=2)+'\n','utf-8')
launchers=[R/f'Start-Korean-v{v}.{ext}' for v in [8,10,11] for ext in ['cmd','ps1']];(O/'launchers').mkdir(exist_ok=True)
for p in launchers:(O/'launchers'/p.name).write_bytes(p.read_bytes())
plan.update(needs_final_review=False,restore_map='restore-map.json',restorable_files=len(rows),unmapped_files=[],old_launchers=[p.name for p in launchers],review_findings_resolved=['All retired runtime files mapped to retained exact bytes or verified backup object','Native prototype executable/DLL stays at original path','QA references resolvable via backup index','Retired launchers and current run guide scheduled for cleanup together'])
(O/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf-8')
text='''# 레콘키스타 구버전 정리안\n\n아직 삭제한 파일은 없습니다.\n\n- 보존: 현재 v13, 직전 v12, HD 적용 전 v9, 원본 runtime, builds 전체, 번역·소스·작업 중 UI/오프닝 자료.\n- 정리 후보: v1–v8, v10, v11 실행 사본 10개 및 완료된 prototype 4개의 복제 실행 데이터. prototype의 검증된 EXE/DLL은 원래 경로에 남깁니다.\n- 구버전 v8/v10/v11 실행기 6개도 함께 정리하고, 현재 실행 안내의 과거 fallback 안내를 갱신합니다.\n- 저장 데이터·로그·검증 그림·네이티브 바이너리는 saves-and-evidence.zip에 보존했습니다. 서로 다른 저장 내용은 합치거나 덮어쓰지 않았습니다.\n- 하드링크와 보존 백업을 고려한 확보 예상량은 약 1.6 GiB입니다. 폴더 표시 용량 약 91.8 GiB 전체가 확보되는 것은 아닙니다.\n- restore-map.json은 모든 후보 파일의 보존 위치를 기록합니다. 과거 builder가 v8/v10/v11을 요구하면 해당 실행 사본을 먼저 복원할 수 있습니다.\n- hires junction의 연결 대상에는 삭제를 수행하지 않습니다.\n\n구버전 삭제 범위가 사용자에게 확정된 다음에만 정리를 실행합니다.\n'''
(O/'정리안.md').write_text(text,'utf-8')
print(json.dumps({'mapped_files':len(rows),'unmapped':len(missing),'logical_byte_hash_comparisons':len(hashes),'old_launchers':len(launchers),'deleted':0},ensure_ascii=False))
