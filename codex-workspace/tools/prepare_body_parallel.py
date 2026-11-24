"""Build immutable source-bound ownership packets for three explicitly requested chats."""
from pathlib import Path
import sys,json,hashlib,collections,re,shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from make_packets import packet
BASE=ROOT/'body-parallel'
def dump(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ranges(xs):
 out=[]
 for x in sorted(xs):
  if out and out[-1][1]+1==x:out[-1][1]=x
  else:out.append([x,x])
 return out

def lane(name):
 if name=='00_レコンキスタ_start.mjo':return 'root'
 if name in ['00_レコンキスタ_start_2.mjo','00_レコンキスタ_start_3.mjo','makino_kyoutu.mjo','shinya_kyoutu.mjo']:return 'session-1/lane-1'
 if name.startswith(('kureha_','sub_kure')):return 'session-1/lane-2'
 if name.startswith(('masa_','sub_masa')):return 'session-1/lane-3'
 if name.startswith('maho_'):
  m=re.match(r'maho_(\d+)',name)
  return 'session-2/lane-1' if m and int(m[1])<=13 else 'session-2/lane-2'
 if name.startswith('sina_') and 'ここで' not in name:
  m=re.match(r'sina_(\d+)',name)
  return 'session-2/lane-1' if m and int(m[1])<=6 else 'session-2/lane-2' if m and int(m[1])<=9 else 'session-2/lane-3'
 if name.startswith('last_kako'):return 'session-3/lane-1'
 if name.startswith('last_gendai') or name=='last_ep.mjo':return 'session-3/lane-2'
 if name.startswith(('sub_last','st_')) or name in ['kosihata.mjo','ありもと.mjo','あんころもちスタッフルーム.mjo','きおなち.mjo','きゃるみぃ.mjo','さかっきー.mjo','ハルちん.mjo','コピー (2) ～ sina_19_2.mjo','sina_19_2　ここでテキスト作業します.mjo','1test.mjo','test.mjo','テスト用.mjo','スクリプト素体.mjo','スタッフルーム素体.mjo']:return 'session-3/lane-3'
 return 'ui-opening-ending'

def main():
 assert not (BASE/'ownership.json').exists(),'Do not overwrite an active dispatch.'
 catalog=collections.defaultdict(list)
 for l in (ROOT/'localization/catalog/catalog.jsonl').open(encoding='utf-8'):
  r=json.loads(l);catalog[r['file']].append(r)
 approved=[]
 for prefix in ['opening','chapter02']:
  d=json.loads((ROOT/f'translation/{prefix}-target.json').read_text(encoding='utf-8'));approved+=d['records']
 approved_ids={r['id'] for r in approved};approved_units={r['unit'] for r in approved}
 frozen={}
 for rel in ['translation/LOCALIZATION_GUIDELINES.md','translation/glossary-and-voice.md','translation/age-context-review.json']:
  src=ROOT/rel;dest=BASE/'shared'/src.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest);frozen[str(dest.relative_to(BASE))]=sha(dest)
 authority=Path(r'P:\AI\Codex\skills\contextual-game-localization\references\translation-quality.md')
 frozen['shared_authority']={'path':str(authority),'sha256':sha(authority)}
 dump(BASE/'shared/approved-memory.json',{'translator_model':'Codex internal','status':'context reviewed, no runtime approval implied','records':approved})
 frozen['shared/approved-memory.json']=sha(BASE/'shared/approved-memory.json')
 files=[];totals=collections.defaultdict(collections.Counter);owners={};field_owner={}
 for k,src in enumerate(sorted((ROOT/'research/extracted/scenario').glob('*.mjo')),1):
  name=src.name;own=lane(name);units=packet(name);owned=[];exceptions=[]
  for u in units:
   n=int(u['unit'].rsplit('u',1)[1]);u['phase']=name
   this_owner='root' if name=='00_レコンキスタ_start_2.mjo' and n<=373 else own
   assert u['unit'] not in owners;owners[u['unit']]=this_owner
   if this_owner==own:owned.append(n)
   else:exceptions.append(n)
   for f in u['fields']:
    assert f['id'] not in field_owner;field_owner[f['id']]=this_owner
    totals[this_owner]['ordinary_text_fields' if f['role']=='text' else 'protected_speaker_tokens']+=1
   totals[this_owner]['units']+=1
  visible_candidates=[r for r in catalog[name] if r['opcode']=='ldstr' and r['has_japanese']]
  candidates=[{**r,'translation_permission':'consumer review required; never translate a resource/internal key'} for r in visible_candidates]
  output=f'source/script-{k:03d}.json'
  d={'translator_model':'Codex internal','source_language':'ja','target_language':'ko','source_script':name,'source_sha256':sha(src),'source_mjo':str(src),'disassembly':str(ROOT/'research/disassembly'/(name+'.mjil')),'owner':own,'owned_ranges':ranges(owned),'root_owned_ranges':ranges(exceptions),'units':units,'display_literal_candidates':candidates,'extraction_note':'Speaker token and voice metadata are heuristics. Verify against neighboring source, actual display consumers and scene. Every source ID remains immutable; no silent dropping of candidates.'}
  dump(BASE/output,d)
  files.append({'script':name,'source_sha256':d['source_sha256'],'packet':output,'packet_sha256':sha(BASE/output),'owner':own,'owned_ranges':ranges(owned),'root_owned_ranges':ranges(exceptions),'units':len(units),'owned_units':len(owned),'ordinary_text_fields':sum(f['role']=='text' for u in units for f in u['fields']),'display_literal_candidates':len(candidates),'source_text_commands':sum(r['opcode']=='text' for r in catalog[name]),'reachability':'audit_required' if own=='session-3/lane-3' else 'source_script_assignment_not_runtime_proof'})
 assert len(field_owner)==sum(r['opcode']=='text' for rs in catalog.values() for r in rs)
 assert approved_ids<=set(field_owner)
 assert all(owners[u]=='root' for u in approved_units)
 for session in range(1,4):
  for ln in range(1,4):
   owner=f'session-{session}/lane-{ln}';dest=BASE/owner;dest.mkdir(parents=True,exist_ok=True)
   assigned=[x for x in files if x['owner']==owner]
   dump(dest/'assignment.json',{'translator_model':'Codex internal','owner':owner,'frozen_contract':'../../shared/contract.json','counts':dict(totals[owner]),'files':assigned,'write_scope':str(dest),'first_batch':'Read complete local scene and at least 10 neighboring units, author 100-150 owned units ending at a semantic boundary; checkpoint and continue next batch after usage/stop check.','status':'not_started'})
   dump(dest/'progress.json',{'owner':owner,'translator_model':'Codex internal','status':'not_started','completed_unit_ids':[],'pending_context_unit_ids':[],'artifacts':[]})
 contract={'translator_model':'Codex internal','created':'2026-10-22','root_thread':'01a16283-b393-7dc0-8c83-d3e23a2a2f41','user_authorization':'그 후 3개 세션에서 서브에이전트를 3개씩 굴려서 분할 번역해','authorization_scope':'User explicitly authorizes semantic translation by three Codex internal subagents in each of three new project chats, overriding the usual review-only restriction for this task only. No external translation model is authorized.','frozen_files':frozen,'owned_write_scope':'Coordinator writes only own session folder; each subagent only own lane. Immutable source/shared/ownership; central translation, glyph map, builds, runtime and UI session are root/UI-owned.','field_contract':'Copy source_script/source_sha256 and source IDs exactly. Preserve original text field count. Never translate speaker_token, voice/bg/file keys, control commands. For inline/ruby/choice strings, record exact instruction ID and proven consumer separately.','target_schema':{'translator_model':'Codex internal','owner':'session-N/lane-N','coordinator_thread_id':'actual ID','agent_id':'actual ID','source_script':'original file','source_sha256':'original SHA','records':[{'unit':'file::uNNNN','fields':[{'id':'file::NNNNNN','source':'exact original text','target':'Codex-authored Korean'}],'context':{'speaker_identity':'resolved or explicit unknown','addressees':['actual recipients'],'relationship':'source supported','story_phase':'route and scene','voice':'directed voice'},'status':'context_reviewed_static_checked_runtime_pending'}],'deferred':[{'unit':'stable ID','reason':'concrete context/technical reason, no silent omission','evidence':['source ID']}],'term_proposals':[],'inline_records':[]},'runtime_status':'All new targets are staged semantic artifacts. No claim of in-game validation.','usage_policy':'Before substantial work, new agent dispatch, and bounded batches read included usage and shared stop marker; 0% remaining stops all owned work immediately. Never purchased credits/reset/automatic restart. Missing usage values do not prove allowance.','stop_marker':r'C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json','age_context':'Read shared/age-context-review.json. Do not infer minority from school alone or invent adulthood. Root owns the 68 pending early units. Continue nonsexual scenes. If a later sexual scene has minor/uncertain ages, preserve IDs and exact reason without translating the sexual content; do not rephrase it into a different scene. Clearly adult supplied material may be translated faithfully. No whole-route exclusion.'}
 dump(BASE/'shared/contract.json',contract)
 dump(BASE/'ownership.json',{'translator_model':'Codex internal','files':files,'owner_totals':{k:dict(v) for k,v in totals.items()},'unit_count':len(owners),'source_text_commands':len(field_owner),'approved_root_units':len(approved_units),'coverage_validation':'Every source text instruction assigned exactly once; all current approved units root-owned; every MJO assigned to root/body lane/existing UI; no blank filename exclusions.','unit_owners':owners})
 print(json.dumps({'files':len(files),'source_text_commands':len(field_owner),'unit_count':len(owners),'owner_totals':{k:dict(v) for k,v in totals.items()}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
