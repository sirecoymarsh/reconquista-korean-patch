"""Prepare a lossless safety archive and explicit cleanup plan; never deletes anything."""
from pathlib import Path
import os,json,hashlib,zipfile,datetime
R=Path(__file__).resolve().parents[1];physical=R.resolve();O=R/'reports/version-cleanup-20261023';O.mkdir(exist_ok=True)
targets=[f'runtime-body-ui-20261023-v{i}' for i in range(1,9)]+['runtime-body-ui-20261023-v10-hd','runtime-body-ui-20261023-v11-review']+[f'candidates/{x}/runtime-prototype' for x in ['config-completion-v1','hires-v1','input-fix-v1','review-unlock-v1']]
keep=['runtime-body-ui-20261023-v13-config','runtime-body-ui-20261023-v12-input-logo','runtime-body-ui-20261023-v9','runtime','builds','translation','research','ui-opening-ending','runtime-qa','runtime-recovery-full-20261023-v2']
archive=O/'saves-and-evidence.zip';assert not archive.exists(),'Do not overwrite a prior safety archive'
index=[];seen=set();links=[];count=0
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name in targets:
  p=R/name;assert p.resolve().is_relative_to(physical)
  for base,dirs,files in os.walk(p,followlinks=False):
   for d in list(dirs):
    q=Path(base,d);st=q.stat(follow_symlinks=False)
    if getattr(st,'st_file_attributes',0)&0x400:dirs.remove(d);links.append({'path':str(q.relative_to(R)),'resolved_target':str(q.resolve()),'followed':False})
   for file in files:
    q=Path(base,file);rel=q.relative_to(p)
    # Preserve user data, native binaries needed by old proof/build references, and diagnostic evidence.
    if not ('savedata' in rel.parts or 'qa' in rel.parts or (len(rel.parts)==1 and q.suffix.lower() in ['.json','.md','.log','.pid','.exe','.dll'])):continue
    data=q.read_bytes();h=hashlib.sha256(data).hexdigest();entry='objects/'+h
    if h not in seen:z.writestr(entry,data);seen.add(h)
    index.append({'path':str(q.relative_to(R)),'bytes':len(data),'sha256':h,'archive_entry':entry});count+=len(data)
 z.writestr('index.json',json.dumps({'workspace':str(physical),'files':index,'links_not_followed':links},ensure_ascii=False,indent=2).encode('utf-8'))
with zipfile.ZipFile(archive) as z:
 for h in seen:assert hashlib.sha256(z.read('objects/'+h)).hexdigest()==h
plan={'status':'prepared_no_deletions','workspace':str(physical),'current':'body-ui-20261023-v13-config','preserve':keep,'candidate_runtime_directories':targets[:10],'candidate_prototype_directories':targets[10:],'prototype_rule':'Retain tested EXE and DLL at their current paths; archive the rest before removing stale replicated runtime data. Never traverse the hires junction.','archive':str(archive),'archive_bytes':archive.stat().st_size,'archived_files':len(index),'unique_archived_objects':len(seen),'archive_verification':'Every stored object SHA-256 re-read and matched','links_not_followed':links,'estimated_reclaim_before_safety_archive_GiB':1.834,'estimated_net_reclaim_GiB':round(1.834-archive.stat().st_size/2**30,3),'deletion_authorized':False,'needs_final_review':True,'deletion_method':'To be bounded by exact manifest and resolved physical paths; no deletion performed.'}
(O/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps({k:plan[k] for k in ['status','archived_files','unique_archived_objects','archive_bytes','estimated_net_reclaim_GiB']},ensure_ascii=False))
