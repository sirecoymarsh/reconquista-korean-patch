"""Record exact translation coverage/context and repeated complete-unit QA."""
from pathlib import Path
import json,hashlib,unicodedata,re,collections
from translation_context import context
ROOT=Path(__file__).resolve().parents[1]
def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def ranges(ids):
 out=[]
 for n in sorted(ids):
  if out and out[-1][1]+1==n:out[-1][1]=n
  else:out.append([n,n])
 return out

def main():
 repeated=collections.defaultdict(list);summaries={};contexts=[];allrecords=[]
 for prefix in ['opening','chapter02']:
  data=json.loads((ROOT/f'translation/{prefix}-source.json').read_text(encoding='utf-8'));units=data['units'];script=units[0]['unit'].split('::')[0]
  inline=json.loads((ROOT/f'translation/{prefix}-inline-ko.json').read_text(encoding='utf-8'))['records']
  chosen={};records=[];width=[]
  for p in sorted((ROOT/'translation').glob(f'{prefix}-ko-*.tsv')):
   for line in p.read_text(encoding='utf-8').splitlines():
    if not line.strip():continue
    number,target=line.split('\t',1);n=int(number);assert n not in chosen;chosen[n]=target
    u=units[n-1];fields=[f for f in u['fields'] if f['role']=='text'];parts=target.split(' || ');assert len(fields)==len(parts),(prefix,n)
    c=context(prefix,n,u);contexts.append({'unit':u['unit'],**c})
    for f,t in zip(fields,parts):
     assert t.strip() and '\x00' not in t
     assert not re.search('[ぁ-ヺ]',t),(f['id'],t)
     w=sum(.5 if ord(x)<128 else 1 for x in t)
     if w>31:width.append({'id':f['id'],'cells':w})
     records.append({'id':f['id'],'unit':u['unit'],'source':f['source'],'target':t,'speaker':u['speaker'],'context':c,'translator_model':'Codex internal','provenance':'primary task 01a16283-b393-7dc0-8c83-d3e23a2a2f41; 2026-10-22','status':'context_reviewed_static_checked_runtime_pending'})
    assembled=[(f['index'],f['source'],t) for f,t in zip(fields,parts)]
    assembled += [(r['index'],r['source'],r['target']) for r in inline if r['unit']==n and r['role'] in ['ruby_body','emphasis_body']]
    assembled.sort();source=''.join(x[1] for x in assembled);whole_target=''.join(x[2] for x in assembled)
    key=re.sub(r'\s+','',unicodedata.normalize('NFKC',source));repeated[key].append({'unit':u['unit'],'target':re.sub(r'\s+','',whole_target)})
  inline=json.loads((ROOT/f'translation/{prefix}-inline-ko.json').read_text(encoding='utf-8'))['records']
  assert all(x['unit'] in chosen for x in inline)
  skipped=[[91,100],[210,269]] if prefix=='chapter02' else []
  # These are pending gaps, not an automatic prohibition based on student status.
  skipped=ranges({n for a,b in skipped for n in range(a,b+1)}-set(chosen))
  dump(ROOT/f'translation/{prefix}-target.json',{'translator_model':'Codex internal','source_sha256':sha(ROOT/'research/extracted/scenario'/script),'completed_units':sorted(chosen),'records':records,'inline_records':inline})
  summaries[script]={'total_units':len(units),'covered_ranges':ranges(chosen),'covered_units':len(chosen),'text_fields':len(records),'inline_fields':len(inline),'deferred_untranslated_ranges':skipped,'remaining_untranslated_ranges':ranges(set(range(1,len(units)+1))-set(chosen)),'line_width_warnings':width}
  allrecords+=records
 variants=[{'source_normalized':s,'occurrences':o} for s,o in repeated.items() if len(o)>1 and len({x['target'] for x in o})>1]
 assert not variants,variants
 dump(ROOT/'translation/unit-context.json',{'translator_model':'Codex internal','scope':'only covered IDs; source tokens are kept separate from inferred identity','units':contexts})
 groups=[{'source_normalized':s,'occurrences':o} for s,o in repeated.items() if len(o)>1]
 dump(ROOT/'reports/repeated-unit-review.json',{'scope':'complete text plus inline body/emphasis in original instruction order among authored opening/chapter02 ranges; ruby readings checked separately; normalized by Unicode NFKC and whitespace; no field-fragment synonym approval','groups':groups,'unintended_variants':variants,'word_lemma_audit':'not complete; a full-corpus all-word occurrence inventory and semantic audit are still required before final approval'})
 terms={'霊園':['공원묘지'],'墓':['무덤'],'再生':['재생'],'人工島':['인공섬'],'海上ニュータウン':['해상 뉴타운'],'マンション':['아파트'],'動く歩道':['무빙워크','움직이는 보도(어린이에게 설명)'],'非常勤講師':['시간강사'],'現国':['현대국어'],'管理人':['관리인','관리인분'],'大家':['집주인'],'仕送り':['생활비'],'甲斐性なし':['무능력자'],'カイショーナシ':['무능력자'],'ジンギスカン':['징기스칸']}
 occurrences={term:[] for term in terms}
 target={x['id']:x for x in allrecords}
 with (ROOT/'localization/catalog/catalog.jsonl').open(encoding='utf-8') as f:
  for line in f:
   r=json.loads(line)
   for term in terms:
    if term in r['source']:
     occurrences[term].append({'id':r['id'],'opcode':r['opcode'],'count':r['source'].count(term),'authored_target':target.get(r['id'],{}).get('target'),'semantic_review':'pending_global_sense_and_referent_audit'})
 dump(ROOT/'translation/term-occurrences.json',{'translator_model':'Codex internal','scope':'all catalog occurrences of current glossary words only; NOT exhaustive all-word approval','terms':{t:{'canonical_lemmas':terms[t],'occurrences':occurrences[t]} for t in terms}})
 out={'translator_model':'Codex internal','source_and_field_parity':True,'protected_script_control':'See latest-build script_validation; original branch targets and unchanged instructions preserved','coverage':summaries,'total_units':len(contexts),'text_fields':len(allrecords),'inline_fields':sum(x['inline_fields'] for x in summaries.values()),'repeated_complete_unit_groups':len(groups),'unintended_repeated_unit_variants':0,'runtime_status':'Current new build has not been traversed in game; prior first-line screenshot is reused evidence only','next':'00_レコンキスタ_start_2.mjo::u0374 onward; keep all unresolved age/context gaps explicit'}
 dump(ROOT/'reports/translation-batch-check.json',out)
 print(json.dumps({k:v for k,v in out.items() if k!='coverage'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
