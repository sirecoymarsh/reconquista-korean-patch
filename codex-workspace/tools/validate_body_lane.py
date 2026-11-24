"""Validate new/changed lane batches, reusing hash-matched prior structural checks."""
from pathlib import Path
import json,hashlib,re,argparse,collections
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'body-parallel'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--lane',required=True);x=a.parse_args();assert re.fullmatch(r'session-[1-3]/lane-[1-3]',x.lane)
 dest=BASE/x.lane;assignment=json.loads((dest/'assignment.json').read_text(encoding='utf-8'))
 sources={};units={};owned={};fields={};bounds={}
 controls=collections.defaultdict(list)
 assigned_scripts={f['script'] for f in assignment['files']}
 for line in (ROOT/'localization/catalog/catalog.jsonl').open(encoding='utf-8'):
  r=json.loads(line)
  if r['file'] in assigned_scripts and r['opcode']=='ctrl' and r['source']=='w':controls[r['file']].append(r['instruction_index'])
 for f in assignment['files']:
  p=BASE/f['packet'];assert sha(p)==f['packet_sha256'];d=json.loads(p.read_text(encoding='utf-8'));sources[f['script']]=d
  allowed={n for lo,hi in f['owned_ranges'] for n in range(lo,hi+1)}
  previous_end=-1
  for u in d['units']:
   last=max(z['index'] for z in u['fields']);end=next((i for i in controls[f['script']] if i>last),last)
   bounds[u['unit']]=(previous_end+1,end);previous_end=end
   units[u['unit']]=u
   if int(u['unit'].rsplit('u',1)[1]) in allowed:owned[u['unit']]=u
   for z in u['fields']:fields[z['id']]=z
 oldpath=dest/'validation.json';old=json.loads(oldpath.read_text(encoding='utf-8')) if oldpath.exists() else {};prior=old.get('batches',{})
 batches={};completed={};deferred={};inline_ids=set();errors=[];warnings=[];reviewed=0;reused=0
 for p in sorted((dest/'batches').glob('*.json')):
  key=str(p.relative_to(dest));digest=sha(p);d=json.loads(p.read_text(encoding='utf-8'));records=d.get('records',[])
  cached=old.get('validator_sha256')==sha(Path(__file__)) and prior.get(key,{}).get('sha256')==digest and prior.get(key,{}).get('structural_pass') is True
  warning_start=len(warnings)
  if cached:warnings.extend(prior[key].get('warnings',[]))
  try:
   assert d['owner']==x.lane and d['translator_model']=='Codex internal'
   assert d.get('coordinator_thread_id') and d.get('agent_id')
   script=d['source_script'];assert script in sources and d['source_sha256']==sources[script]['source_sha256']
   for r in records:
    uid=r['unit'];assert uid in owned and uid.startswith(script+'::') and uid not in completed,uid
    completed[uid]=key
    if cached:continue
    expected=[f for f in owned[uid]['fields'] if f['role']=='text'];got=r['fields'];assert len(got)==len(expected),(uid,'field count')
    assert [g['id'] for g in got]==[f['id'] for f in expected],(uid,'field IDs/order')
    for f,g in zip(expected,got):
     assert g['source']==f['source'],(g['id'],'source mutated')
     assert isinstance(g['target'],str) and g['target'].strip() and '\x00' not in g['target'],g['id']
     if re.search('[ぁ-ヺ]',g['target']):warnings.append({'id':g['id'],'reason':'Japanese kana remains; explicit semantic/quotation explanation required'})
     if sum(.5 if ord(c)<128 else 1 for c in g['target'])>31:warnings.append({'id':g['id'],'reason':'Estimated >31 cells; review wrapping, do not omit meaning'})
    assert all(k in r['context'] for k in ['speaker_identity','addressees','relationship','story_phase','voice']),(uid,'context missing')
   for r in d.get('deferred',[]):
    uid=r['unit'];assert uid in owned and r.get('reason') and r.get('evidence');assert uid not in deferred;deferred[uid]=r
   for r in d.get('inline_records',[]):
    assert r.get('id') and r.get('source') is not None and r.get('target') is not None and r.get('consumer') and r.get('evidence')
    assert r['id'].startswith(script+'::')
    assert r.get('unit') in owned and r['unit'].startswith(script+'::'),(r['id'],'inline unit is not owned')
    index=int(r['id'].rsplit('::',1)[1]);lo,hi=bounds[r['unit']]
    assert lo<=index<=hi,(r['id'],'inline outside its source unit')
    assert r['id'] not in inline_ids,(r['id'],'duplicate inline ID');inline_ids.add(r['id'])
    candidates={z['id']:z for z in sources[script]['display_literal_candidates']}
    assert r['id'] in candidates and candidates[r['id']]['source']==r['source'],r['id']
   batches[key]={'sha256':digest,'structural_pass':True,'verification_reused':cached,'records':len(records),'warnings':warnings[warning_start:]}
   if cached:reused+=1
   else:reviewed+=1
  except (AssertionError,KeyError,TypeError) as e:errors.append({'file':key,'error':str(e)});batches[key]={'sha256':digest,'structural_pass':False}
 overlap=set(completed)&set(deferred)
 if overlap:errors.append({'error':'Both completed and deferred','units':sorted(overlap)})
 result={'validator_sha256':sha(Path(__file__)),'owner':x.lane,'translator_model':'Codex internal','status':'structural_pass_semantic_and_runtime_not_implied' if not errors else 'failed','batches':batches,'new_or_changed_batches_checked':reviewed,'unchanged_batch_checks_reused':reused,'completed_units':len(completed),'deferred_units':len(deferred),'owned_units':len(owned),'remaining_units':len(set(owned)-set(completed)-set(deferred)),'errors':errors,'warnings':warnings,'runtime_verified':False}
 oldpath.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='batches'},ensure_ascii=False,indent=2))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
