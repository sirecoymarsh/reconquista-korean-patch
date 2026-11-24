"""Merge session-1 accepted snapshot and audited tail choices without re-reviewing old batches."""
from pathlib import Path
import json, hashlib, datetime, collections, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'body-parallel/session-1'
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 stage=S/'session-translation.json';digest=sha(stage);label='session1-'+digest[:8]+'-widthqa-v1';out=ROOT/'translation/integration'/label
 assert not out.exists(),out
 d=load(ROOT/'translation/integration/reviewed-002/targets.json');prior=load(ROOT/'translation/integration/reviewed-001/integrated-targets.json');new=load(stage);ledger=load(S/'semantic-review.json')['batches']
 expected=load(S/'coordinator-progress.json')['execution_checkpoint']['final_artifacts']['session-translation.json']['sha256'];assert digest==expected
 old_records={r['id']:r for r in d['records']};old_inline={r['id']:r for r in d['inline_records']};base_records=json.loads(json.dumps(old_records));base_inline=json.loads(json.dumps(old_inline));accepted=[];deferred=[]
 for b in new['batches']:
  p=S/b['path'];h=sha(p);v=load(p.parent.parent/'validation.json')['batches'];vr=v.get(p.relative_to(p.parent.parent).as_posix(),v.get(str(p.relative_to(p.parent.parent))))
  assert h==b['sha256']==ledger[b['path']]['sha256']==vr['sha256'] and ledger[b['path']]['status']=='accepted' and vr['structural_pass']
  payload=load(p);deferred.extend(r['unit'] for r in payload.get('deferred',[]));d['source_files'][b['source_script']]=b['source_sha256']
  for u in b['records']:
   for f in u['fields']:
    if f['id'] in old_records: assert old_records[f['id']]['source']==f['source']
    old_records[f['id']]={**f,'unit':u['unit'],'source_sha256':b['source_sha256'],'context':u['context'],'translator_model':'Codex internal','origin':str(p.relative_to(ROOT)),'origin_sha256':h,'provenance':{'coordinator_thread_id':new['coordinator_thread_id'],'agent_id':b['agent_id']}}
  for f in b['inline_records']:
   if f['id'] in old_inline: assert old_inline[f['id']]['source']==f['source']
   old_inline[f['id']]={**f,'opcode':'ldstr','index':int(f['id'].rsplit('::',1)[1]),'source_sha256':b['source_sha256'],'translator_model':'Codex internal','origin':str(p.relative_to(ROOT)),'origin_sha256':h}
  accepted.append({'path':str(p.relative_to(ROOT)),'sha256':h,'units':len(b['records']),'structural_evidence':str((p.parent.parent/'validation.json').relative_to(ROOT)),'semantic_evidence':'body-parallel/session-1/semantic-review.json','verification':'reused_exact_hash'})
 tail=load(S/'tail-choice-review.json');assert tail['status']=='semantic_accepted_consumer_verified_integration_pending';assert tail['source_sha256']==d['source_files'][tail['source_script']]
 for f in tail['records']:
  assert f['id'] not in old_records and f['id'] not in old_inline
  old_inline[f['id']]={**f,'unit':None,'scope':'script_tail','opcode':'ldstr','index':int(f['id'].rsplit('::',1)[1]),'source_sha256':tail['source_sha256'],'origin':'body-parallel/session-1/tail-choice-review.json','origin_sha256':sha(S/'tail-choice-review.json')}
 allrows={**old_records,**old_inline};changes=[]
 def fix(r,target,reason):
  if r['target']!=target:changes.append({'id':r['id'],'before':r['target'],'after':target,'reason':reason});r['target']=target;r['integration_editor']='Codex internal /root';r['integration_review']=reason
 # Existing central canonical decisions, applied to the newly merged scope only.
 for r in allrows.values():
  fix(r,r['target'].replace('카미조','가미조').replace('미션 스쿨','미션스쿨'),'Reuse prior central canonical 上条=가미조 and ミッションスクール=미션스쿨')
 for change in prior['root_review']['changes']:
  r=allrows.get(change['id'])
  if r and r['target']==change['before']:fix(r,change['after'],'Reuse prior exact-field integration review: '+change['reason'])
 # Preserve the repeated onset of the same canonical surname.
 for r in allrows.values():
  if 'カ、上条' in r['source'] or 'か、上条' in r['source']:fix(r,r['target'].replace('카, 가미조','가, 가미조'),'Match stutter onset to the existing central canonical surname')
 units={r['unit'] for r in old_records.values()};d.update(label=label,records=list(old_records.values()),inline_records=list(old_inline.values()),units=len(units),text_fields=len(old_records),inline_fields=len(old_inline),runtime_verified=False,stage='session1 integrated; 81 warning fields pending actual native-engine review')
 d['coverage']={s:sorted(int(u.rsplit('u',1)[1]) for u in units if u.startswith(s+'::')) for s in d['source_files']}
 d['root_review']={'translator_model':'Codex internal','reused_prior_root_review':'translation/integration/reviewed-001/integrated-targets.json','reused_semantic_and_structural':accepted,'session1_stage_sha256':digest,'tail_choice_sha256':sha(S/'tail-choice-review.json'),'canonical_terms':prior['root_review']['canonical_terms'],'changes':changes,'runtime_pending':True}
 for k,v in base_records.items():
  if 'session-1' not in v.get('origin','') and k in old_records:assert old_records[k]['source']==v['source']
 assert len(new['batches'])==166 and sum(len(b['records']) for b in new['batches'])==16755
 assert len(deferred)==52 and not (set(deferred)&units)
 warnings=[]
 for n in range(1,4):
  for w in load(S/f'lane-{n}/validation.json')['warnings']:
   r=old_records[w['id']];warnings.append({**w,'unit':r['unit'],'target':r['target'],'origin':r['origin'],'status':'runtime_pending'})
 assert len(warnings)==81 and len({w['id'] for w in warnings})==81
 out.mkdir(parents=True);prov=out/'provenance';prov.mkdir()
 for f in [stage,S/'semantic-review.json',S/'tail-choice-review.json',S/'term-decisions.json',S/'validator-adjustment.json']:shutil.copy2(f,prov/f.name)
 dump(out/'targets.json',d);dump(out/'integrated-targets.json',d)
 now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
 report={'translator_model':'Codex internal','updated_at':now,'status':'central_integrated_runtime_review_pending','authorization':'User explicitly requested central integration including two tail choices and native-game review/fixes for81 width warnings, reusing passed verification.','label':label,'baseline':'translation/integration/reviewed-002/targets.json','session1_units':16755,'session1_inline':184,'tail_choices':2,'central_units':len(units),'central_text_fields':len(old_records),'central_inline_fields':len(old_inline),'reused_batches':166,'central_term_adjustments':len(changes),'deferred_unit_ids':deferred,'warnings':warnings,'runtime_verified':False,'next_step':'Build frozen central snapshot; prepare native-engine warning-unit replay and capture all81 warning fields.'}
 dump(out/'runtime-review.json',report)
 root_progress=load(ROOT/'progress.json');root_progress['session1_runtime_integration']={'status':report['status'],'label':label,'progress':str((out/'runtime-review.json').relative_to(ROOT)),'latest_authorization':report['authorization']};dump(ROOT/'progress.json',root_progress)
 print(json.dumps({k:report[k] for k in ['status','label','session1_units','central_units','central_text_fields','central_inline_fields','reused_batches','central_term_adjustments']},ensure_ascii=False))
if __name__=='__main__':main()
