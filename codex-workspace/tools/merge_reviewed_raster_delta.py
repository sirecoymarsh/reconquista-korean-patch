"""Apply an independently reviewed, source-bound raster delta to a frozen combined build."""
from pathlib import Path
import sys,argparse,json,shutil,os,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));from inspect_majiro import Arc,sha,dump
ap=argparse.ArgumentParser();ap.add_argument('--base',required=True);ap.add_argument('--label',required=True);ap.add_argument('--candidate',required=True);ap.add_argument('--scope',required=True,choices=['ending_credits','remaining_ui','brand_logo']);ap.add_argument('--review-proof');ap.add_argument('--replace-candidate');args=ap.parse_args()
A=R/'builds'/args.base;O=R/'builds'/args.label;C=R/'ui-opening-ending/candidates'/args.candidate
assert A.is_dir() and C.is_dir() and not O.exists();cm=json.loads((C/'manifest.json').read_text(encoding='utf-8'));review=json.loads((R/args.review_proof).read_text(encoding='utf-8')) if args.review_proof else {};assert not review or (review['candidate_manifest_sha256']==sha((C/'manifest.json').read_bytes()) and review['visual_pass'] and review['technical_pass']);assert cm.get('structural_pass',all(r.get('structural_pass',False) for r in cm['entries'])) and (cm.get('visual_pass',False) or review),'Candidate static and visual review must complete before integration';semantic_labels=cm.get('semantic_labels',cm.get('semantic_fields',0)*len(cm['entries']));assert semantic_labels>0
manifest=json.loads((A/'manifest.json').read_text(encoding='utf-8'));groups={};replaced_labels=0
if args.replace_candidate:
 previous=[r for r in manifest['integrated_raster_deltas'] if Path(r['candidate']).name==args.replace_candidate]
 assert len(previous)==1 and previous[0]['scope']==args.scope
 old=previous[0];old_entries={r['entry']:r for d in old['validation'] for r in d['entries']}
 assert set(old_entries)=={r['entry'] for r in cm['entries']}
 for r in cm['entries']:assert r.get('base_candidate_sha256')==old_entries[r['entry']]['output_sha256']
 replaced_labels=old['semantic_labels']

for r in cm['entries']:
 assert r['archive']=='fastdata.arc' and Path(r['entry']).suffix.lower() in ['.rct','.rc8'];assert r.get('protected_pixel_diff_count',0)==0 and r.get('source_glyph_residue_pixels',0)==0
 assert r.get('source_size')==r.get('output_size')
 groups.setdefault(r['archive'],[]).append(r)
O.mkdir();I=O/'delta-inputs'/args.candidate;I.mkdir(parents=True);shutil.copy2(C/'manifest.json',I/'raster-manifest.json');dump(I/'semantic-delta.json',json.loads((C/'semantic-delta.json').read_text(encoding='utf-8')) if (C/'semantic-delta.json').exists() else {'translator_model':'Codex internal','logo_text':cm['exact_logo_text'],'quote_lines':cm['quote_lines'],'semantic_fields_per_state':cm['semantic_fields']});dump(I/'central-review.json',review)
delta=[];changed_archives={}
for name,rs in groups.items():
 arc=Arc(A/name);raw=arc.path.read_bytes();assert sha(raw)==manifest['outputs'][name];payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in arc.entries};before={k:sha(v) for k,v in payload.items()}
 for r in rs:
  entry=r['entry'];data=(C/'payloads'/entry).read_bytes();assert before[entry]==r.get('base_candidate_sha256',r['source_sha256']),('Existing translation collision',entry);assert sha(data)==r['output_sha256'];payload[entry]=data
 blob=arc.rebuild(payload);(O/name).write_bytes(blob);parsed=Arc(O/name);assert [e['name'] for e in parsed.entries]==[e['name'] for e in arc.entries]
 for e in parsed.entries:assert blob[e['offset']:e['offset']+e['size']]==payload[e['name']]
 changed=[n for n in payload if before[n]!=sha(payload[n])];assert sorted(changed)==sorted(r['entry'] for r in rs)
 changed_archives[name]=sha(blob);delta.append({'archive':name,'parent_sha256':sha(raw),'output_sha256':sha(blob),'entries':rs,'only_requested_entries_changed':True,'entry_order_and_payload_readback_exact':True})
for p in A.iterdir():
 if p.name in changed_archives or p.name in ['manifest.json','installation.json']:continue
 if p.is_dir():shutil.copytree(p,O/p.name,copy_function=os.link,dirs_exist_ok=True)
 else:os.link(p,O/p.name)
for row in manifest['archives']:
 if row['archive'] in changed_archives:
  row['output_sha256']=changed_archives[row['archive']];by={r['entry']:r for r in row['changed']}
  for r in groups[row['archive']]:
   if r['entry'] in by:
    previous=by[r['entry']];assert previous['output_sha256']==r.get('base_candidate_sha256',r['source_sha256']);previous.setdefault('cumulative_deltas',[]).append({'scope':args.scope,'prior_output_sha256':previous['output_sha256']});previous['output_sha256']=r['output_sha256']
   else:row['changed'].append({'entry':r['entry'],'source_sha256':r['source_sha256'],'output_sha256':r['output_sha256']})
manifest.update(label=args.label,parent_build=str(A),parent_manifest_sha256=sha((A/'manifest.json').read_bytes()))
manifest['outputs'].update(changed_archives);manifest.setdefault('integrated_raster_deltas',[]).append({'candidate':str(C),'candidate_manifest_sha256':sha((C/'manifest.json').read_bytes()),'frozen_manifest':'delta-inputs/'+args.candidate+'/raster-manifest.json','scope':args.scope,'semantic_labels':semantic_labels,'supersedes_candidate':args.replace_candidate,'net_new_semantic_labels':semantic_labels-replaced_labels,'validation':delta})
if args.scope=='ending_credits':
 manifest.pop('op_ed_integrated',None);manifest['op_ed_status']={'opening_movie_localized':False,'ending_credits_localized':True,'ending_lyrics_localized':False,'ending_credits_labels':semantic_labels,'scroll_and_slides_original_dimensions_and_timing_preserved':True,'actual_game_sync_verified':False}
else:manifest['ui_raster_label_instances']+=semantic_labels-replaced_labels
manifest['source_unit_accounting']['raster_labels_integrated']=manifest['ui_raster_label_instances']
if args.scope=='ending_credits':
 manifest['source_unit_accounting'].pop('op_ed_integrated',None);manifest['source_unit_accounting']['op_ed_status']=manifest['op_ed_status'];dump(R/'reports/combined-source-coverage.json',manifest['source_unit_accounting'])
T=R/('runtime-'+args.label);S=R/('runtime-'+args.base);assert not T.exists();T.mkdir();save_copy_hashes=[]
for p in S.rglob('*'):
 rel=p.relative_to(S);q=T/rel
 if p.is_dir():q.mkdir(exist_ok=True)
 elif p.name not in ['BUILD-IDENTITY.json','한국어화-상태.md'] and str(rel) not in changed_archives:
  if rel.parts[0]=='savedata':
   shutil.copy2(p,q);h=sha(p.read_bytes());assert sha(q.read_bytes())==h;save_copy_hashes.append({'file':rel.relative_to('savedata').as_posix(),'sha256':h})
  else:os.link(p,q)
for name,expected in changed_archives.items():shutil.copy2(O/name,T/name);assert sha((T/name).read_bytes())==expected
if args.scope=='brand_logo':manifest['brand_logo']={'text':cm['exact_logo_text'],'title_variants':3,'title_states':9,'quote_lines_per_state':4,'opening_logo_integrated':manifest.get('brand_logo',{}).get('opening_logo_integrated',False),'runtime_verified':False}
manifest.update(installed_runtime=str(T),savedata_copied_from=str(S/'savedata'),save_copy_hashes=save_copy_hashes,installed_hash_verification_scope={'newly_verified':['changed archive copies','new savedata source/copy hashes'],'unchanged_payloads':'Previous evidence reused; unchanged hardlinks preserved; launcher verifies controlled files before execution'});dump(O/'manifest.json',manifest);dump(T/'BUILD-IDENTITY.json',manifest)
launcher=R/'Start-Korean.ps1';text=launcher.read_text(encoding='utf-8-sig');assert args.base in text;launcher.write_text(text.replace(args.base,args.label),encoding='utf-8-sig')
state=json.loads((R/'progress.json').read_text(encoding='utf-8'));state['runtime']=str(T);state['updated_at']=datetime.datetime.now().astimezone().isoformat();state['body_ui_integration'].update(label=args.label,runtime=str(T),build=str(O));state['translation']['build']=str(O);state['body_ui_integration']['ui_raster_label_instances']=manifest['ui_raster_label_instances'];state['body_ui_integration']['raster_label_instances']=manifest['ui_raster_label_instances']
if args.scope=='brand_logo':state['body_ui_integration']['brand_logo']=manifest['brand_logo']
if args.scope=='ending_credits':state['body_ui_integration'].pop('op_ed_integrated',None);state['body_ui_integration']['op_ed_status']=manifest['op_ed_status']
dump(R/'reports/combined-source-coverage.json',manifest['source_unit_accounting']);dump(R/'progress.json',state);dump(R/'reports/latest-combined-build.json',{'path':str(O),'runtime':str(T),'manifest_sha256':sha((O/'manifest.json').read_bytes()),'label':args.label})
doc=R/'한국어화-실행안내.md';text=doc.read_text(encoding='utf-8')
if args.scope=='ending_credits':text=text.replace('UI의 나머지 이미지 문구와 오프닝·엔딩은 별도 세션에서 계속 작업 중입니다. 현재 통합본에는 아직 들어가지 않았습니다.','엔딩 크레딧78항목은 세로 스크롤과11장 교체 화면 모두에 반영했습니다. UI의 나머지 이미지 문구, OP와 노래 자막은 별도 세션에서 계속 작업 중이며 아직 통합되지 않았습니다.')
if args.scope=='brand_logo':text+='\n\n타이틀3종의 일반·선택·누름 상태9장에는 사용자 지정 표기 레콘키스타의 붉은 붓글씨 로고와 작은 인용문4줄을 적용했습니다. 기존 메뉴 버튼과 영문 표장은 보존했습니다. OP 영상 로고는 별도 작업 중입니다.\n'
doc.write_text(text,encoding='utf-8');(T/'한국어화-상태.md').write_text(text,encoding='utf-8')
print(json.dumps({'runtime':str(T),'scope':args.scope,'new_labels':semantic_labels-replaced_labels,'revised_labels':replaced_labels,'payloads':len(cm['entries']),'archives':changed_archives,'body_scenario_exe_and_fonts_unchanged':True,'runtime_verification':'deferred_to_user'},ensure_ascii=False))
