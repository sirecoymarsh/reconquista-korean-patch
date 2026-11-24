"""Read-only preflight plus a bounded execution list for approved retired runtimes."""
from pathlib import Path
import json,hashlib,os
R=Path(__file__).resolve().parents[1].resolve();O=R/'reports/version-cleanup-20261023';plan=json.loads((O/'plan.json').read_text('utf-8'));mapping=json.loads((O/'restore-map.json').read_text('utf-8'))
assert str(R)==plan['workspace']==mapping['workspace']
assert not Path(r'C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json').exists()
backup=O/'saves-and-evidence.zip';assert backup.is_file() and backup.stat().st_size==plan['archive_bytes']
roots=[(R/x).resolve() for x in plan['candidate_runtime_directories']+plan['candidate_prototype_directories']]
assert len(roots)==14 and all(p!=R and p.is_relative_to(R) for p in roots)
protos={(R/x).resolve() for x in plan['candidate_prototype_directories']}
records={str(R/x['path']):x for x in mapping['records']};delete=[];keep=[];cache={};observed=set();dirs=[]
def sha(p):
 s=p.stat();k=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
 if k not in cache:cache[k]=hashlib.sha256(p.read_bytes()).hexdigest()
 return cache[k]
for root in roots:
 assert root.is_dir() and not (getattr(root.stat(follow_symlinks=False),'st_file_attributes',0)&0x400)
 for base,subdirs,files in os.walk(root,followlinks=False):
  for name in list(subdirs):
   p=Path(base,name)
   if getattr(p.stat(follow_symlinks=False),'st_file_attributes',0)&0x400:subdirs.remove(name);continue
  dirs.append(str(Path(base)))
  for name in files:
   p=Path(base,name);assert str(p) in records,('new unexpected file',str(p));observed.add(str(p));x=records[str(p)];s=p.stat(follow_symlinks=False)
   assert not getattr(s,'st_file_attributes',0)&0x400
   assert s.st_size==x['bytes']
   if x['kind']=='retained_hardlink':
    src=R/x['source'];ss=src.stat();assert ss.st_ino==s.st_ino and ss.st_dev==s.st_dev and str(ss.st_ino)==x['file_id'] and ss.st_mtime_ns==x['mtime_ns'];assert all(not src.is_relative_to(t) for t in roots)
   elif x['kind']=='retained_equal_bytes':
    src=R/x['source'];assert all(not src.is_relative_to(t) for t in roots);assert sha(src)==x['sha256']==sha(p)
   elif x['kind']=='archive':assert sha(p)==x['sha256']
   else:raise AssertionError(x)
   row={'path':str(p),'bytes':s.st_size,'file_id':str(s.st_ino),'links':s.st_nlink}
   if root in protos and p.parent==root and p.suffix.lower() in ['.exe','.dll']:keep.append(row)
   else:delete.append(row)
assert observed==set(records)
linkrows=[]
for row in plan['links_not_followed']:
 p=R/row['path'];assert getattr(p.stat(follow_symlinks=False),'st_file_attributes',0)&0x400
 assert str(p.resolve())==row['resolved_target'] and all(not p.resolve().is_relative_to(t) for t in roots)
 linkrows.append({'path':str(p),'target':str(p.resolve())})
launch=[]
for name in plan['old_launchers']:
 p=R/name;assert p.parent==R and sha(p)==sha(O/'launchers'/name);launch.append(str(p))
unique={}
for row in delete:
 q=unique.setdefault(row['file_id'],{'count':0,'links':row['links'],'bytes':row['bytes']});q['count']+=1
estimate=sum(x['bytes'] for x in unique.values() if x['count']==x['links'])
result={'workspace':str(R),'delete_files':delete,'keep_native':keep,'remove_junction_nodes':linkrows,'remove_empty_directories':sorted(dirs,key=len,reverse=True),'keep_root_directories':[str(p) for p in protos],'old_launchers':launch,'estimated_freed_bytes':estimate,'free_bytes_before':__import__('shutil').disk_usage(R).free,'backup_size_verified':backup.stat().st_size,'backup_integrity_proof_reused':plan['archive_verification'],'restore_mapping_complete':True}
(O/'execution-plan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps({'files':len(delete),'native_files_retained':len(keep),'junction_nodes':len(linkrows),'launchers':len(launch),'estimated_freed_GiB':round(estimate/2**30,3)},ensure_ascii=False))
