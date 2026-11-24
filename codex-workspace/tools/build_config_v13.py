"""Install the reviewed config translation and reversible in-game review control alongside v12."""
from pathlib import Path
import json,hashlib,shutil,os,datetime,sys
from inspect_majiro import Arc
R=Path(__file__).resolve().parents[1];C=R/'candidates/config-completion-v1';BASE='body-ui-20261023-v12-input-logo';LABEL='body-ui-20261023-v13-config'
B=R/'builds'/BASE;S=R/('runtime-'+BASE);O=R/'builds'/LABEL;T=R/('runtime-'+LABEL)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text('utf-8-sig'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8')
assert not Path(r'C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json').exists()
proof=load(C/'verification.json');cm=load(C/'manifest.json');sp=load(C/'config-script-proof.json');binding=load(C/'source-binding.json')
assert proof['pass'] and proof['dll_sha256']==sha(C/'native/ReconquistaHD.dll')
assert cm['ready_for_integration'] and binding['pass']
assert sp['output_sha256']==sha(C/'payloads/config.mjo')
old=(R/'Start-Korean.ps1').read_text('utf-8-sig');assert BASE in old
assert not O.exists() and not T.exists(),'Never overwrite a prior build'
base=load(B/'manifest.json');critical=['manifest.json','ReconquistaHD.dll','scenario.arc','fastdata.arc'];basehash={n:sha(B/n) for n in critical}
assert cm['source_manifest_sha256']==basehash['manifest.json']
for name in ['ReconquistaHD.dll','scenario.arc','fastdata.arc']:assert sha(S/name)==base['outputs'][name]
# Candidate hashes must correspond to the persisted payloads reviewed above.
replacements={'scenario.arc':{'config.mjo':(C/'payloads/config.mjo').read_bytes()},'fastdata.arc':{}}
for row in cm['entries']:
 for name,expected in [(row['entry'],row['output_sha256']),(row['mask_entry'],row['mask_output_sha256'])]:
  assert sha(C/'payloads'/name)==expected;replacements['fastdata.arc'][name]=(C/'payloads'/name).read_bytes()
O.mkdir();T.mkdir();saves=[]
skip={'manifest.json','installation.json','BUILD-IDENTITY.json','한국어화-상태.md','ReconquistaHD.dll','scenario.arc','fastdata.arc','hires-runtime.log'}
for origin,dest in [(B,O),(S,T)]:
 for p in origin.rglob('*'):
  rel=p.relative_to(origin);q=dest/rel
  if rel.parts[0]=='qa':continue
  if p.is_dir():q.mkdir(exist_ok=True)
  elif len(rel.parts)==1 and p.name in skip:continue
  elif origin==S and (rel.parts[0]=='savedata' or p.name=='review-unlock.enabled'):
   shutil.copy2(p,q);assert sha(p)==sha(q);saves.append({'file':rel.as_posix(),'sha256':sha(q),'independent_copy':True})
  else:os.link(p,q)
 shutil.copy2(C/'native/ReconquistaHD.dll',dest/'ReconquistaHD.dll')
archiveproof=[]
for arc,changed in replacements.items():
 a=Arc(B/arc);raw=a.path.read_bytes();payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries};before={k:hashlib.sha256(v).hexdigest() for k,v in payload.items()}
 assert changed.keys()<=payload.keys()
 if arc=='scenario.arc':assert before['config.mjo']==sp['source_sha256']
 else:
  for row in cm['entries']:assert before[row['entry']]==row['base_rgb_sha256'] and before[row['mask_entry']]==row['base_mask_sha256']
 payload.update(changed);(O/arc).write_bytes(a.rebuild(payload));os.link(O/arc,T/arc)
 a2=Arc(O/arc);rr=a2.path.read_bytes();diff=[]
 for e in a2.entries:
  data=rr[e['offset']:e['offset']+e['size']];assert data==payload[e['name']]
  if hashlib.sha256(data).hexdigest()!=before[e['name']]:diff.append(e['name'])
 assert set(diff)==set(changed)
 archiveproof.append({'archive':arc,'parent_sha256':basehash[arc],'output_sha256':sha(O/arc),'only_requested_entries_changed':True,'entry_order_and_payload_readback_exact':True,'changed':[{'entry':n,'source_sha256':before[n],'output_sha256':hashlib.sha256(payload[n]).hexdigest()} for n in diff]})
D=O/'delta-inputs/config-completion-v1';D.mkdir(parents=True)
for folder in ['payloads','clean','layers','masks','preview','source']:
 shutil.copytree(C/folder,D/folder)
(D/'native').mkdir()
for n in ['ReconquistaHD.cpp','hooks.inc','hooks.json','Build.cmd']:shutil.copy2(C/'native'/n,D/'native'/n)
for n in ['manifest.json','semantic-map.json','verification.json','review.json','config-script-proof.json','source-binding.json','button-design.json','probe-final.log']:
 shutil.copy2(C/n,D/n)
for n in ['build_config_completion_v1.py','prepare_config_button.py','verify_config_delta.py',Path(__file__).name]:shutil.copy2(R/'tools'/n,D/n)
m=json.loads(json.dumps(base));m.update(label=LABEL,parent_build=str(B),parent_manifest_sha256=basehash['manifest.json'],installed_runtime=str(T),status='config_translation_and_in_game_review_button_installed',savedata_copied_from=str(S/'savedata'),save_copy_hashes=saves,runtime_verified=False)
for n in ['ReconquistaHD.dll','scenario.arc','fastdata.arc']:m['outputs'][n]=sha(T/n)
for ar in m['archives']:
 if ar['archive'] in replacements:
  changes=replacements[ar['archive']];ar['output_sha256']=m['outputs'][ar['archive']];ar['latest_delta']='delta-inputs/config-completion-v1/manifest.json'
  prior={x['entry']:x for x in ar['changed']}
  evidence=next(x for x in archiveproof if x['archive']==ar['archive'])
  for e in evidence['changed']:
   if e['entry'] in prior:
    row=prior[e['entry']];row.setdefault('cumulative_deltas',[]).append({'scope':'config_completion_v13','prior_output_sha256':row['output_sha256'],'actual_parent_entry_sha256':e['source_sha256']});row['output_sha256']=e['output_sha256']
   else:ar['changed'].append(e)
sv=m['script_validation']['config.mjo'];sv['prior_validation_before_config_button']=dict(sv);sv.update(sp['relocation']);sv['latest_delta']='delta-inputs/config-completion-v1/config-script-proof.json'
nd=m['native_diagnostic_validation']['config.mjo'];nd['prior_structural_rewrite']=nd.pop('structural_rewrite',None);nd['prior_outside_string_ranges_unchanged']=nd.pop('outside_string_ranges_unchanged',None);nd['native_cp949_payload_bytes_unchanged']=binding['native_cp949_payload_bytes_unchanged'];nd['output_sha256']=sp['output_sha256'];nd['records']=binding['native_diagnostic_records'];nd['latest_relocation']=sp['relocation']
m['integrated_raster_deltas'].append({'candidate':str(C),'candidate_manifest_sha256':sha(C/'manifest.json'),'frozen_manifest':'delta-inputs/config-completion-v1/manifest.json','scope':'19_config_static_labels','semantic_labels':19,'state_instances':57,'validation':archiveproof,'background_reconstruction':cm['user_authorized_exception']})
m['ui_raster_label_instances']+=57
m['source_unit_accounting']['raster_labels_integrated']=m['ui_raster_label_instances']
m['high_resolution']['native_source']='delta-inputs/config-completion-v1/native'
m['review_unlock']['in_game_config_button']={**load(C/'button-design.json'),'verification':'delta-inputs/config-completion-v1/verification.json','actual_user_screen_verified':False}
m['config_completion']={'labels':19,'states':['off','on','push'],'instances':57,'candidate':str(C),'verification':'delta-inputs/config-completion-v1/verification.json','user_screen_verification_pending':True,'other_ui_surfaces_not_completed_by_this_delta':True}
dump(O/'manifest.json',m);dump(T/'BUILD-IDENTITY.json',m)
assert all(sha(T/n)==h for n,h in m['outputs'].items())
assert all(sha(B/n)==h for n,h in basehash.items())
(R/'Start-Korean-v12.ps1').write_text(old,'utf-8-sig')
cmd='@echo off\r\npushd "%~dp0"\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Korean-v12.ps1"\r\nif errorlevel 1 pause\r\npopd\r\n';(R/'Start-Korean-v12.cmd').write_bytes(cmd.encode('ascii'))
new=old.replace(BASE,LABEL).replace('Remove-Item Env:RECON_INPUT_PROBE -ErrorAction SilentlyContinue','Remove-Item Env:RECON_INPUT_PROBE -ErrorAction SilentlyContinue\nRemove-Item Env:RECON_CONFIG_PROBE -ErrorAction SilentlyContinue')
for n in ['Start-Korean.ps1','Start-Korean-4K.ps1']:(R/n).write_text(new,'utf-8-sig')
guide=(R/'한국어화-실행안내.md').read_text('utf-8');lines=guide.splitlines();lines[0]='# 레콘키스타 한국어판 v13 · 설정 화면과 콘텐츠 개방 버튼';guide='\n'.join(lines)+'\n'
addition='''
v13에서 설정 화면에 남아 있던 일본어 고정 문구 19개를 일반·선택·누름 상태 57곳에 반영했습니다. 글자 아래 배경은 사용자 허용에 따라 원본풍으로 부분 복원했습니다. 버튼·슬라이더 좌표와 기능은 유지했습니다.

설정 화면 상단의 **모든 콘텐츠 개방 · 현재 꺼짐**을 누르면 검수용 개방이 켜지고, **개방 취소 · 현재 켜짐**을 다시 누르면 해제됩니다. 기존 Ctrl+F10도 사용할 수 있습니다. 실제 클리어 기록은 덮어쓰지 않습니다.

이전 버전은 **Start-Korean-v12.cmd**로 실행할 수 있습니다. 저장 파일은 v12에서 별도 복사했으며 버전 사이에 자동 동기화하지 않습니다. 전체 화면의 사용자 확인은 아직 남아 있고, 다른 미완료 UI 화면은 이번 설정 수정에 포함되지 않습니다.

'''
guide=guide.replace('\n\n','\n\n'+addition,1);(R/'한국어화-실행안내.md').write_text(guide,'utf-8');(T/'한국어화-상태.md').write_text(guide,'utf-8')
g=load(R/'progress.json');g.update(runtime=str(T),updated_at=datetime.datetime.now().astimezone().isoformat(),next='User checks v13 config labels and all-content unlock/cancel button; other remaining UI and separate OP work retain existing scope.')
g['body_ui_integration'].update(label=LABEL,build=str(O),runtime=str(T));g['translation']['build']=str(O)
g['config_completion_checkpoint']={'status':'installed_controlled_runtime_verified_user_screen_pending','build':str(O),'runtime':str(T),'candidate':str(C),'labels':19,'instances':57,'fallback':'Start-Korean-v12.cmd','verification':str(D/'verification.json'),'background_restore_exception':'User approved original-style local reconstruction'}
g['usage_checkpoint']={'used_percent':60,'remaining_percent':40,'shared_stop_marker_present':False,'observed_at_note':'Account snapshot at batch start, not a billing lock'}
handoff=load(R/'reports/remaining-ui-handoff.json')
completed=[x for x in handoff['remaining_ui'] if x['id']=='config-static'];handoff['remaining_ui']=[x for x in handoff['remaining_ui'] if x['id']!='config-static']
handoff.setdefault('completed_since_audit',[]).append({'id':'config-static','build':LABEL,'semantic_labels':19,'state_instances':57,'native_review_button':True,'evidence':'candidates/config-completion-v1/manifest.json','historical_blocker':completed,'actual_user_screen_verified':False})
handoff['current_ui_raster_labels']=m['ui_raster_label_instances'];handoff['updated_at']=datetime.datetime.now().astimezone().isoformat();dump(R/'reports/remaining-ui-handoff.json',handoff)
dump(R/'progress.json',g);dump(R/'reports/latest-combined-build.json',{'path':str(O),'runtime':str(T),'label':LABEL,'manifest_sha256':sha(O/'manifest.json')})
dump(D/'installation-verification.json',{'pass':True,'v12_critical_files_unchanged':basehash,'savedata_independent_copy':saves,'archives':archiveproof,'hires_assets_unchanged_reused_prior_proof':True,'launcher_prepare_pending':True})
print(json.dumps({'installed':True,'runtime':str(T),'fallback':'Start-Korean-v12.cmd','labels':19,'new_button':True},ensure_ascii=False))
