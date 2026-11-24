"""Freeze coordinator-accepted, source/hash-matched targets for root integration."""
from pathlib import Path
import json,hashlib,sys,collections
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 label=sys.argv[1];out=ROOT/'translation/integration'/label;assert not out.exists()
 records=[];inline=[];accepted=[];pending=[];unit_meta={};ids=set();units=set()
 for prefix in ['opening','chapter02']:
  p=ROOT/f'translation/{prefix}-target.json';d=load(p);script=d['records'][0]['id'].split('::')[0]
  for r in d['records']:
   assert r['id'] not in ids;ids.add(r['id']);units.add(r['unit']);records.append({**r,'source_sha256':d['source_sha256'],'origin':str(p.relative_to(ROOT)),'origin_sha256':sha(p.read_bytes())})
  for r in d['inline_records']:
   inline.append({**r,'id':f"{script}::{r['index']:06d}",'unit':f"{script}::u{r['unit']:04d}",'opcode':'ldstr'})
  accepted.append({'kind':'root','path':str(p.relative_to(ROOT)),'sha256':sha(p.read_bytes()),'units':len(d['completed_units']),'review_evidence':'reports/opening-guideline-review.json; reports/chapter02-language-review.json; reports/chapter02-through-0373-review.json; reports/deferred-70-restored-review.json'})
 for n in range(1,4):
  session=ROOT/f'body-parallel/session-{n}';ledger=session/('semantic-review.json' if n==1 else 'coordinator-review.json');d=load(ledger);rows=d.get('batches',d.get('reviews',[]));rows=[{'batch':k,**v} for k,v in rows.items()] if isinstance(rows,dict) else rows
  eligible={}
  for r in rows:
   if r.get('status','').startswith('accepted') or r.get('status')=='reviewed_corrections_verified':eligible[r['batch']]=r
  for p in sorted(session.glob('lane-*/batches/*.json')):
   rel=p.relative_to(session).as_posix();raw=p.read_bytes();digest=sha(raw);r=eligible.get(rel);batch=json.loads(raw)
   v=load(p.parent.parent/'validation.json');vr=v.get('batches',{}).get(str(p.relative_to(p.parent.parent)),v.get('batches',{}).get(p.relative_to(p.parent.parent).as_posix(),{}))
   if not r or r.get('sha256')!=digest or vr.get('sha256')!=digest or not vr.get('structural_pass'):
    pending.append({'path':str(p.relative_to(ROOT)),'sha256':digest,'reason':'coordinator semantic acceptance and structural PASS must both match current hash'});continue
   frozen=out/f'accepted/session-{n}'/rel;frozen.parent.mkdir(parents=True,exist_ok=True);frozen.write_bytes(raw)
   for u in batch['records']:
    assert u['unit'] not in units,u['unit'];units.add(u['unit']);unit_meta[u['unit']]=u['context']
    for f in u['fields']:
     assert f['id'] not in ids;ids.add(f['id']);records.append({**f,'unit':u['unit'],'source_sha256':batch['source_sha256'],'context':u['context'],'translator_model':'Codex internal','origin':str(p.relative_to(ROOT)),'origin_sha256':digest,'provenance':{'coordinator_thread_id':batch['coordinator_thread_id'],'agent_id':batch['agent_id']}})
   for f in batch.get('inline_records',[]):inline.append({**f,'opcode':'ldstr','index':int(f['id'].rsplit('::',1)[1]),'origin_sha256':digest})
   accepted.append({'kind':'parallel','path':str(p.relative_to(ROOT)),'frozen_path':str(frozen.relative_to(ROOT)),'sha256':digest,'units':len(batch['records']),'fields':sum(len(x['fields']) for x in batch['records']),'inline':len(batch.get('inline_records',[])),'review_evidence':str(ledger.relative_to(ROOT)),'review':r,'structural_evidence':str((p.parent.parent/'validation.json').relative_to(ROOT))})
 for r in inline:assert r['id'] not in ids,r['id'];ids.add(r['id'])
 source_files={}
 for r in records:
  script=r['id'].split('::')[0];source_files[script]=r['source_sha256']
 counts=collections.Counter(u.split('::')[0] for u in units)
 data={'translator_model':'Codex internal','label':label,'source_files':source_files,'records':records,'inline_records':inline,'accepted':accepted,'pending_at_snapshot':pending,'coverage':{s:sorted(int(u.rsplit('u',1)[1]) for u in units if u.startswith(s+'::')) for s in source_files},'units':len(units),'text_fields':len(records),'inline_fields':len(inline),'runtime_verified':False,'stage':'coordinator-reviewed snapshot; root cross-batch consistency and build pending'}
 dump(out/'targets.json',data)
 print(json.dumps({'path':str(out),'units':len(units),'text_fields':len(records),'inline':len(inline),'accepted_batches':len(accepted)-2,'by_script':dict(counts),'pending_batches':len(pending)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
