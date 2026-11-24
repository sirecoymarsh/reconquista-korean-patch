"""Recover a misassigned dialogue script from the verified identical flashback."""
from pathlib import Path
import sys,json,shutil,os,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));import build_trial as b
from inspect_majiro import Arc,sha,dump
OLD='body-ui-20261023-v2';NEW='body-ui-20261023-v3';A=R/'builds'/OLD;O=R/'builds'/NEW;F=R/'translation/integration/ui-owned-subevent-recovery-20261023';assert not O.exists() and not F.exists();O.mkdir();F.mkdir()
manifest=json.loads((A/'manifest.json').read_text(encoding='utf-8'));mapping=json.loads((A/'font-map.json').read_text(encoding='utf-8'))['mapping'];inv={v:k for k,v in mapping.items()}
def enc(t):
 s=''.join(mapping.get(c,c) for c in t);assert s.encode('cp932').decode('cp932')==s;assert ''.join(inv.get(c,c) for c in s)==t;return s
bodyfile=R/'translation/integration/recovery-full-20261023-v2/integrated-targets.json';body=json.loads(bodyfile.read_text(encoding='utf-8'));assert sha(bodyfile.read_bytes())==manifest['body_snapshot_sha256'];memory={r['id']:r for r in body['records']+body['inline_records']}
owned=json.loads((R/'body-parallel/ownership.json').read_text(encoding='utf-8'));entry='サブイベント.mjo';row=next(r for r in owned['files'] if r['script']==entry);packet=json.loads((R/'body-parallel'/row['packet']).read_text(encoding='utf-8'))
source=(R/'research/extracted/scenario'/entry).read_bytes();assert sha(source)==row['source_sha256'];original,_=b.decode(source)
kure=next(r for r in owned['files'] if r['script']=='kureha_09.mjo');kp=json.loads((R/'body-parallel'/kure['packet']).read_text(encoding='utf-8'));units={u['unit'].rsplit('u',1)[1]:u for u in kp['units']}
records=[];replacements={};altered=[]
for u in packet['units']:
 ref=units[u['unit'].rsplit('u',1)[1]];assert u.get('speaker')==ref.get('speaker');fields=[f for f in u['fields'] if f['role']=='text'];oldfields=[f for f in ref['fields'] if f['role']=='text'];assert len(fields)==len(oldfields)
 for field,oldfield in zip(fields,oldfields):
  prior=memory[oldfield['id']];assert oldfield['source']==prior['source'];target=prior['target'];note='Same scene, speaker, unit order and exact Japanese source; accepted Codex text reused.'
  if field['source']!=oldfield['source']:
   assert field['index'] in [228,293]
   if field['index']==228:
    assert oldfield['source']==field['source']+'。';target='밖에 떠올릴 수 없었으니까';note='Primary Codex: preserve source absence of final punctuation; preceding emphasized 그 이름 remains separate.'
   else:
    assert field['source']=='何故かいつも不安な気持ちにさせられた。' and oldfield['source']=='何故かいつも不安な気持ちにさせられる。';target='어쩐지 늘 불안해지곤 했다.';note='Primary Codex: source changes present habitual narration to past habitual narration.'
   altered.append(field['id'])
  assert original.instructions[field['index']].string==field['source'] and original.instructions[field['index']].opcode.mnemonic=='text'
  rec={'unit':u['unit'],'id':field['id'],'source':field['source'],'target':target,'source_sha256':sha(source),'translator_model':'Codex internal','reused_from_id':prior['id'],'reused_snapshot_sha256':sha(bodyfile.read_bytes()),'context':prior['context'],'review_note':note};records.append(rec);replacements[field['index']]=b.string_ins('text',enc(target))
assert len(records)==53 and len(altered)==2
inline_source=original.instructions[226];assert inline_source.string=='あの名前' and inline_source.opcode.mnemonic=='ldstr' and original.instructions[227].hash==0x2f93f26a
prior=memory['kureha_09.mjo::000225'];inline={'id':entry+'::000226','unit':entry+'::u0022','source':inline_source.string,'target':prior['target'],'opcode':'ldstr','translator_model':'Codex internal','reused_from_id':prior['id'],'consumer':'same following callp 0x2f93f26a; display emphasis'};assert inline['target']=='그 이름';replacements[226]=b.string_ins('ldstr',enc(inline['target']))
new,validation=b.rewrite(source,replacements);decoded,_=b.decode(new)
for r in records+[inline]:assert ''.join(inv.get(c,c) for c in decoded.instructions[int(r['id'].split('::')[1])].string)==r['target']
# Preserve the one UI-owned nonlinguistic dot marker.
yaz,_=b.decode((R/'research/extracted/scenario/yazlib.mjo').read_bytes());assert yaz.instructions[3728].opcode.mnemonic=='text' and yaz.instructions[3728].string=='・'
audit={'translator_model':'Codex internal','source_script':entry,'source_sha256':sha(source),'provenance':'primary root integration from verified Codex-authored kureha_09 flashback','records':records,'inline_records':[inline],'units':33,'text_fields':53,'inline_fields':1,'exact_source_and_context_reused_fields':52,'primary_source_difference_adjusted_ids':altered,'validation':validation,'source_authority_body_snapshot':str(bodyfile),'source_authority_sha256':sha(bodyfile.read_bytes()),'ui_owned_unit_accounting':{'total':70,'c_setumei_translated_units':36,'subevent_recovered_units':33,'yazlib_nonlinguistic_marker_preserved_units':1,'unaccounted_units':0},'reachability':'Source script translated; runtime call reachability has not been newly verified.','runtime_verified':False};dump(F/'targets.json',audit)
arc=Arc(A/'scenario.arc');raw=arc.path.read_bytes();payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in arc.entries};assert payload[entry]==source;payload[entry]=new;blob=arc.rebuild(payload);(O/'scenario.arc').write_bytes(blob);parsed=Arc(O/'scenario.arc');assert [e['name'] for e in parsed.entries]==[e['name'] for e in arc.entries]
for e in parsed.entries:assert blob[e['offset']:e['offset']+e['size']]==payload[e['name']]
for name in ['fastdata.arc','レコンキスタ.exe','font-map.json','gdi-subset-map.json']:os.link(A/name,O/name)
shutil.copytree(A/'font',O/'font',copy_function=os.link);shutil.copytree(A/'inputs',O/'inputs',copy_function=os.link)
manifest.update(label=NEW,parent_build=str(A),parent_manifest_sha256=sha((A/'manifest.json').read_bytes()),body_units=46968,body_text_fields=73403,body_inline_fields=626,ui_owned_subevent_recovery={'path':str(F/'targets.json'),'sha256':sha((F/'targets.json').read_bytes()),'units':33,'text_fields':53,'inline_fields':1},ui_owned_unit_accounting=audit['ui_owned_unit_accounting'])
manifest['outputs']['scenario.arc']=sha(blob);manifest['script_validation'][entry]=validation
manifest['body_entries_identical_to_v2'].remove(entry);manifest['body_entries_changed_from_v2'].append(entry)
for row in manifest['archives']:
 if row['archive']=='scenario.arc':row['output_sha256']=sha(blob);row['changed'].append({'entry':entry,'source_sha256':sha(source),'output_sha256':sha(new)})
T=R/('runtime-'+NEW);S=R/('runtime-'+OLD);assert not T.exists();T.mkdir()
for p in S.rglob('*'):
 rel=p.relative_to(S);q=T/rel
 if p.is_dir():q.mkdir(exist_ok=True)
 elif p.name not in ['BUILD-IDENTITY.json','한국어화-상태.md'] and rel!=Path('scenario.arc'):
  if rel.parts[0]=='savedata':shutil.copy2(p,q)
  else:os.link(p,q)
shutil.copy2(O/'scenario.arc',T/'scenario.arc');assert sha((T/'scenario.arc').read_bytes())==sha(blob);manifest.update(installed_runtime=str(T),savedata_copied_from=str(S/'savedata'))
dump(O/'manifest.json',manifest);dump(T/'BUILD-IDENTITY.json',manifest)
launcher=R/'Start-Korean.ps1';text=launcher.read_text(encoding='utf-8-sig');assert OLD in text;launcher.write_text(text.replace(OLD,NEW),encoding='utf-8-sig')
state=json.loads((R/'progress.json').read_text(encoding='utf-8'));state['runtime']=str(T);state['updated_at']=datetime.datetime.now().astimezone().isoformat();state['body_ui_integration'].update(label=NEW,runtime=str(T),build=str(O),body_units=46968,body_text_fields=73403,body_inline_fields=626,ui_owned_unit_accounting=audit['ui_owned_unit_accounting'],subevent_recovery=str(F/'targets.json'));state['counts'].update(translated=73403,translated_units=46968,translated_inline_fields=626,ui_owned_units_separate=0);dump(R/'progress.json',state)
dump(R/'reports/latest-combined-build.json',{'path':str(O),'runtime':str(T),'manifest_sha256':sha((O/'manifest.json').read_bytes()),'label':NEW})
doc=R/'한국어화-실행안내.md';text=doc.read_text(encoding='utf-8').replace('본문46,935구간(대사73,350필드·인라인625필드','본문46,968구간(대사73,403필드·인라인626필드');text+='\nUI 담당으로 분류됐던70구간은 설명문36구간 번역·서브이벤트33구간 복구·비언어 기호1구간 원형 보존으로 모두 확인했습니다. 서브이벤트는 같은 회상의 검증된 번역을 재사용하고 원문의 시제·문장부호 차이2필드만 별도 반영했습니다.\n';doc.write_text(text,encoding='utf-8');(T/'한국어화-상태.md').write_text(text,encoding='utf-8')
print(json.dumps({'runtime':str(T),'body_units':46968,'ordinary_fields':73403,'inline_fields':626,'recovered_subevent_units':33,'ui_owned_unaccounted':0,'scenario_sha256':sha(blob)},ensure_ascii=False))
