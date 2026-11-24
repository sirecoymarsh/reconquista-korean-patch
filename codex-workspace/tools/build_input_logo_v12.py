"""Install bounded input and title-logo revisions alongside unchanged v11."""
from pathlib import Path
import json,hashlib,shutil,os,datetime
from inspect_majiro import Arc
R=Path(__file__).resolve().parents[1];C=R/'candidates/input-fix-v1';L=R/'ui-opening-ending/candidates/brand-logo-ko-v3'
BASE='body-ui-20261023-v11-review';LABEL='body-ui-20261023-v12-input-logo'
B=R/'builds'/BASE;S=R/('runtime-'+BASE);O=R/'builds'/LABEL;T=R/('runtime-'+LABEL)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text('utf-8-sig'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8')
assert not Path(r'C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json').exists()
proof=load(C/'verification.json');assert proof['pass'] and proof['dll_sha256']==sha(C/'native/ReconquistaHD.dll')
logo=load(L/'manifest.json');assert logo['ready_for_integration'] and logo['master_sha256']==sha(L/'master/reconquista-ko.png')
hdrows=load(L/'hd/title/manifest.json')['entries'];changed={r['file']:r for r in hdrows}
old=(R/'Start-Korean.ps1').read_text('utf-8-sig');assert BASE in old
assert not O.exists() and not T.exists(),'Do not overwrite existing version'
basehash={n:sha(B/n) for n in ['manifest.json','レコンキスタ.exe','ReconquistaHD.dll','fastdata.arc','hires-manifest.json']}
oldassets={n:sha(S/'hires'/n) for n in changed}
base=load(B/'manifest.json');assert sha(S/'ReconquistaHD.dll')==base['outputs']['ReconquistaHD.dll'];assert proof['exe_sha256']==base['exe_sha256']
O.mkdir();T.mkdir();saves=[]
skip={'manifest.json','installation.json','BUILD-IDENTITY.json','한국어화-상태.md','ReconquistaHD.dll','fastdata.arc','hires-manifest.json','hires-runtime.log'}
for origin,dest in [(B,O),(S,T)]:
 for p in origin.rglob('*'):
  rel=p.relative_to(origin);q=dest/rel
  if p.is_dir():q.mkdir(exist_ok=True)
  elif len(rel.parts)==1 and p.name in skip:continue
  elif len(rel.parts)==2 and rel.parts[0]=='hires' and p.name in changed:continue
  elif origin==S and (rel.parts[0]=='savedata' or p.name=='review-unlock.enabled'):
   shutil.copy2(p,q);assert sha(p)==sha(q);saves.append({'file':rel.as_posix(),'sha256':sha(q),'independent_copy':True})
  else:os.link(p,q)
 shutil.copy2(C/'native/ReconquistaHD.dll',dest/'ReconquistaHD.dll')
 for n in changed:shutil.copy2(L/'hd/assets'/n,dest/'hires'/n)
# Only the nine named title entries may differ in fastdata.arc.
a=Arc(B/'fastdata.arc');raw=a.path.read_bytes();payloads={e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries};original_hashes={n:hashlib.sha256(b).hexdigest() for n,b in payloads.items()}
newpayloads={r['entry']:(L/'payloads'/r['entry']).read_bytes() for r in logo['entries']}
assert len(newpayloads)==9 and newpayloads.keys()<=payloads.keys()
assert all(original_hashes[row["entry"]]==row["base_candidate_sha256"] for row in logo["entries"])
assert all(hashlib.sha256(newpayloads[row["entry"]]).hexdigest()==row["output_sha256"] for row in logo["entries"])
payloads.update(newpayloads);(O/'fastdata.arc').write_bytes(a.rebuild(payloads));os.link(O/'fastdata.arc',T/'fastdata.arc')
a2=Arc(O/'fastdata.arc');newraw=a2.path.read_bytes();diff=[]
for e in a2.entries:
 data=newraw[e['offset']:e['offset']+e['size']];assert data==payloads[e['name']]
 if hashlib.sha256(data).hexdigest()!=original_hashes[e['name']]:diff.append(e['name'])
assert set(diff)==set(newpayloads)
hm=load(S/'hires-manifest.json');previous_hm=load(S/'hires-manifest.json')
for row in hm['entries']:
 if row['file'] in changed:
  z=changed[row['file']];row.update(sha256=z['sha256'],bytes=z['bytes']);row['revision_source']='brand-logo-ko-v3'
assert sum(x!=y for x,y in zip(hm['entries'],previous_hm['entries']))==9
hm['bytes']=sum(e['bytes'] for e in hm['entries']);hm['integrity_proof_reused'].append('ui-opening-ending/candidates/brand-logo-ko-v3/hd/title/manifest.json');hm['title_logo_master_sha256']=logo['master_sha256']
for d in [O,T]:dump(d/'hires-manifest.json',hm)
D=O/'delta-inputs/input-fix-v1';D.mkdir(parents=True)
for n in ['ReconquistaHD.cpp','hooks.inc','hooks.json','Build.cmd']:shutil.copy2(C/'native'/n,D/n)
for n in ['design.json','verification.json','probe-final.log','review.json','input-callback-assembly.json']:shutil.copy2(C/n,D/n)
shutil.copy2(Path(__file__),D/'build_input_logo_v12.py')
DL=O/'delta-inputs/brand-logo-ko-v3';shutil.copytree(L,DL)
shutil.copy2(R/'tools/build_brand_logo_v3.py',DL/'build_brand_logo_v3.py')
m=base.copy();m.update(label=LABEL,parent_build=str(B),parent_manifest_sha256=basehash['manifest.json'],installed_runtime=str(T),status='input_logo_installed_hidden_input_pass',savedata_copied_from=str(S/'savedata'),save_copy_hashes=saves,runtime_verified=False)
m['outputs']=dict(base['outputs'])
for n in ['ReconquistaHD.dll','fastdata.arc','hires-manifest.json']:m['outputs'][n]=sha(T/n)
m['archives']=json.loads(json.dumps(base['archives']))
for ar in m['archives']:
 if ar['archive']=='fastdata.arc':
  ar['output_sha256']=m['outputs']['fastdata.arc'];ar['latest_delta']='delta-inputs/brand-logo-ko-v3/manifest.json'
  for row in ar['changed']:
   if row['entry'] in newpayloads:
    row.setdefault('cumulative_deltas',[]).append({'scope':'brand_logo_v3','prior_output_sha256':row['output_sha256']})
    row['output_sha256']=hashlib.sha256(newpayloads[row['entry']]).hexdigest()
m['integrated_raster_deltas']=list(base.get('integrated_raster_deltas',[]))+[{'candidate':str(L),'candidate_manifest_sha256':sha(L/'manifest.json'),'frozen_manifest':'delta-inputs/brand-logo-ko-v3/manifest.json','scope':'brand_logo_v3','semantic_labels':0,'validation':[{'archive':'fastdata.arc','parent_sha256':basehash['fastdata.arc'],'output_sha256':m['outputs']['fastdata.arc'],'entries':logo['entries'],'only_requested_entries_changed':True,'entry_order_and_payload_readback_exact':True}]}]
m['input_fix']={**load(C/'design.json'),'verification':'delta-inputs/input-fix-v1/verification.json','review':'delta-inputs/input-fix-v1/review.json','actual_onscreen_gameplay_verified':False}
m['brand_logo']=dict(base['brand_logo']);m['brand_logo'].update(revision='v3',master_sha256=logo['master_sha256'],title_states=9,hd_title_states=9,opening_logo_integrated=False,opening_logo_revision='v2; v3 handoff pending separate OP session',runtime_verified=False)
m['high_resolution']=dict(base['high_resolution']);m['high_resolution']['native_source']='delta-inputs/input-fix-v1';m['high_resolution']['input_proof']='delta-inputs/input-fix-v1/verification.json'
dump(O/'manifest.json',m);dump(T/'BUILD-IDENTITY.json',m)
# Commit the launcher switch only after payload verification.
assert all(sha(T/n)==h for n,h in m['outputs'].items())
for row in hdrows:assert sha(T/'hires'/row['file'])==row['sha256']
(R/'Start-Korean-v11.ps1').write_text(old,'utf-8-sig')
cmd='@echo off\r\npushd "%~dp0"\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0{script}"\r\nif errorlevel 1 pause\r\npopd\r\n'
(R/'Start-Korean-v11.cmd').write_bytes(cmd.format(script='Start-Korean-v11.ps1').encode('ascii'))
new=old.replace(BASE,LABEL).replace('Remove-Item Env:RECON_REVIEW_PROBE -ErrorAction SilentlyContinue','Remove-Item Env:RECON_REVIEW_PROBE -ErrorAction SilentlyContinue\nRemove-Item Env:RECON_INPUT_PROBE -ErrorAction SilentlyContinue')
for n in ['Start-Korean.ps1','Start-Korean-4K.ps1']:(R/n).write_text(new,'utf-8-sig')
guide=(R/'한국어화-실행안내.md').read_text('utf-8').replace('# 레콘키스타 한국어판 v11 HD · 검수 옵션','# 레콘키스타 한국어판 v12 HD · 입력 수정 및 로고')
addition="""
v12에서는 확대 화면의 WM_MOUSEMOVE 좌표를 원래 게임의 800×600 좌표로 변환합니다. 창 모드와 전체 화면에서 마우스 이동 및 버튼 눌림/해제 신호 검증 9개를 통과했습니다. 실제 화면에서 메뉴를 선택하는 최종 확인은 아직 하지 않았습니다.

타이틀 로고의 작은 세로획을 없애고, 큰 십자가 기둥을 오른쪽으로 옮겨 아래 두 획과 연결했습니다. 첫 레의 뾰족한 장식은 복원했습니다. 타이틀 9개 상태의 일반/HD 이미지에 적용했으며 버튼 좌표는 유지했습니다. 오프닝 영상의 로고 교체는 별도 세션에서 진행합니다.

이전 v11은 Start-Korean-v11.cmd로 실행합니다. 저장 파일과 검수 개방 설정은 v11에서 독립 복사했으며 자동 동기화하지 않습니다.

"""
guide=guide.replace('\n\n','\n\n'+addition,1);(R/'한국어화-실행안내.md').write_text(guide,'utf-8');(T/'한국어화-상태.md').write_text(guide,'utf-8')
g=load(R/'progress.json');g.update(runtime=str(T),updated_at=datetime.datetime.now().astimezone().isoformat(),next='User checks title mouse interaction using default launcher. Opening session receives common v3 logo master for ongoing OP revision.')
g['body_ui_integration'].update(label=LABEL,build=str(O),runtime=str(T));g['body_ui_integration']['brand_logo']=m['brand_logo'];g['translation']['build']=str(O)
g['input_logo_checkpoint']={'status':'installed_hidden_input_pass_user_screen_pending','candidate':str(C),'logo_candidate':str(L),'build':str(O),'runtime':str(T),'input_verification':str(D/'verification.json'),'logo_verification':str(DL/'central-review.json'),'fallback':'Start-Korean-v11.cmd','opening_new_logo_integrated':False}
g['usage_checkpoint']={'used_percent':54,'remaining_percent':46,'shared_stop_marker_present':False,'observed_at_note':'This batch start; account snapshot, not billing lock'}
dump(R/'progress.json',g);dump(R/'reports/latest-combined-build.json',{'path':str(O),'runtime':str(T),'label':LABEL,'manifest_sha256':sha(O/'manifest.json')})
assert all(sha(B/n)==h for n,h in basehash.items());assert all(sha(S/'hires'/n)==h for n,h in oldassets.items())
dump(D/'installation-verification.json',{'pass':True,'v11_critical_files_unchanged':basehash,'v11_old_title_assets_unchanged':oldassets,'savedata_independent_copy':saves,'review_unlock_enabled_copied':(T/'review-unlock.enabled').exists(),'archive_changed_entries':diff,'hd_changed_entries':[r['name'] for r in hdrows],'unchanged_hd_asset_count':len(hm['entries'])-9,'launcher_prepare_pending':True})
print(json.dumps({'installed':True,'runtime':str(T),'fallback':'Start-Korean-v11.cmd','changed_fastdata_entries':len(diff),'changed_hires_assets':len(hdrows)},ensure_ascii=False))

