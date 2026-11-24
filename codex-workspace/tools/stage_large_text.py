"""Stage/install the reviewed large-text delta without modifying the v8 runtime."""
from pathlib import Path
import sys,json,os,shutil,datetime,argparse
from inspect_majiro import sha,dump
R=Path(__file__).resolve().parents[1];B=R/'builds/body-ui-20261023-v8';S=R/'runtime-body-ui-20261023-v8';C=R/'candidates/large-text-v1';LABEL='body-ui-20261023-v9';O=R/'builds'/LABEL;T=R/('runtime-'+LABEL)
ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');args=ap.parse_args()
load=lambda p:json.loads(p.read_text('utf-8'))
cm=load(C/'manifest.json');vm=load(C/'verification.json');cv=load(C/'callback-verification.json');assert vm['pass'] and cv['pass'] and cm['semantic_text_unchanged'] and cm['original_control_codes_unchanged']
assert cm['parent_manifest_sha256']==sha((B/'manifest.json').read_bytes());assert cv['source_sha256']==sha((C/'payloads/scenario.arc').read_bytes())
assert cm['script_changes']['console.mjo']['force_play_guard'];assert cm['native_patch']['output_sha256']==sha((C/'payloads/レコンキスタ.exe').read_bytes())
assert not O.exists() and not T.exists()
changed={'scenario.arc':C/'payloads/scenario.arc','fastdata.arc':C/'payloads/fastdata.arc','レコンキスタ.exe':C/'payloads/レコンキスタ.exe','font/ReconquistaKRLarge.otf':C/'font/ReconquistaKR.otf','font/ReconquistaKRSerifLarge.otf':C/'font/ReconquistaKRSerif.otf'}
O.mkdir();T.mkdir();savehash=[]
for origin,dest in [(B,O),(S,T)]:
 for p in origin.rglob('*'):
  rel=p.relative_to(origin);key=rel.as_posix();q=dest/rel
  if p.is_dir():q.mkdir(exist_ok=True)
  elif key not in changed and p.name not in ['manifest.json','installation.json','BUILD-IDENTITY.json','한국어화-상태.md']:
   if origin==S and rel.parts[0]=='savedata':
    shutil.copy2(p,q);h=sha(p.read_bytes());assert sha(q.read_bytes())==h;savehash.append({'file':rel.as_posix(),'sha256':h})
   else:os.link(p,q)
 for name,p in changed.items():
  q=dest/name;q.parent.mkdir(exist_ok=True);shutil.copy2(p,q);assert sha(q.read_bytes())==sha(p.read_bytes())
  if (origin/name).exists():assert not os.path.samefile(q,origin/name)
D=O/'delta-inputs/large-text-v1';D.mkdir(parents=True)
for n in ['manifest.json','font-candidate.json','verification.json','callback-verification.json','central-review.json','font-comparison.png']:
 assert (C/n).is_file(),n;shutil.copy2(C/n,D/n)
for n in ['build_large_text.py','verify_large_text.py','verify_large_callback.py','stage_large_text.py']:shutil.copy2(R/'tools'/n,D/n)
verification=load(C/'central-review.json');assert verification['technical_review_pass'] and verification['candidate_manifest_sha256']==sha((C/'manifest.json').read_bytes())
m=load(B/'manifest.json');m.update(label=LABEL,parent_build=str(B),parent_manifest_sha256=sha((B/'manifest.json').read_bytes()),installed_runtime=str(T),savedata_copied_from=str(S/'savedata'),save_copy_hashes=savehash,runtime_verified=False,status='large_text_static_gdi_security_pass_user_runtime_pending')
m['outputs'].update({n:sha(p.read_bytes()) for n,p in changed.items()});m['exe_sha256']=m['outputs']['レコンキスタ.exe'];m['large_text']={'candidate':'delta-inputs/large-text-v1','candidate_manifest_sha256':sha((C/'manifest.json').read_bytes()),'body_family':'Reconquista KR Large1','serif_family':'Reconquista KR Large Serif1','raster_and_explicit_ui_fonts_retained':True,'shared_font_consumers':['body','speaker names','history body','config font-name/sample display'],'fullscreen_startup':True,'original_canvas':[800,600],'text_and_original_controls_unchanged':True,'overflow_page_wait_added':True,'normal_page_wait_creates_no_save_point':True,'force_play_preserves_existing_timed_wait':True,'body_ink_sample_before_after':vm['comparison'],'new_fonts':{n:sha(p.read_bytes()) for n,p in changed.items() if n.startswith('font/')},'runtime_verified':False,'performance_stutter_fix_claimed':False}
for item in m.get('archives',[]):
 if item.get('archive') in changed:item['output_sha256']=m['outputs'][item['archive']];item['latest_delta']='delta-inputs/large-text-v1/manifest.json'
m['installed_hash_verification_scope']={'newly_verified':list(changed)+['fresh savedata copy'],'unchanged_payloads':'Preserved hardlinks to v8; existing proof reused'}
dump(O/'manifest.json',m);dump(T/'BUILD-IDENTITY.json',m)
# Four font hashes are verified: original two by existing loop, large pair by outputs map.
old=(R/'Start-Korean.ps1').read_text('utf-8-sig');assert 'body-ui-20261023-v8' in old
(R/'Start-Korean-v8.ps1').write_text(old,encoding='utf-8-sig')
cmd='@echo off\r\npushd "%~dp0"\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0{script}"\r\nif errorlevel 1 pause\r\npopd\r\n'
(R/'Start-Korean-v8.cmd').write_bytes(cmd.format(script='Start-Korean-v8.ps1').encode('ascii'))
new=old.replace('body-ui-20261023-v8',LABEL);(R/'Start-Korean-4K.ps1').write_text(new,encoding='utf-8-sig');(R/'Start-Korean-4K.cmd').write_bytes(cmd.format(script='Start-Korean-4K.ps1').encode('ascii'))
if args.install:(R/'Start-Korean.ps1').write_text(new,encoding='utf-8-sig')
guide=(R/'한국어화-실행안내.md').read_text('utf-8').replace('**body-ui-20261023-v8**','**body-ui-20261023-v9**',1)
oldpara=next(x for x in guide.split('\n\n') if x.startswith('작은 창이 너무'))
newpara='4K 모니터용 큰 글꼴 버전입니다. **Start-Korean-4K.cmd** 또는 기본 **Start-Korean.cmd**로 실행하면 게임의 전체 화면 모드로 시작하도록 설정했습니다. 본문·이름은 한글 높이가 약 31% 커지고, 기존에 가늘게 눌렸던 가로 폭도 넓어졌습니다. 원본 논리 화면 800×600과 UI 배치는 유지하며, 네이티브 4K 해상도로 배경 그림을 다시 만든 버전은 아닙니다. **F4**는 전체 화면, **Alt+Enter**는 창 모드입니다. 실제 전체 화면 표시 비율과 프레임 안정성은 사용자 확인이 남아 있습니다. 버벅임 원인은 아직 확정하지 않았습니다.\n\n긴 대사가 창을 넘으면 추가 페이지 대기를 거칩니다. 평상시에는 새 저장 지점을 만들지 않는 기존 입력 대기를 사용하며, 자동·스킵·강제 진행의 별도 처리도 보존했습니다. 이 추가 대기 중에는 일반 대사 끝에서 제공되는 저장 메뉴 대신 넘김만 사용합니다. 문장 끝의 원래 대기에서는 기존 메뉴가 유지됩니다. 실제 엔진의 페이지 넘김·백로그·저장/불러오기 확인은 사용자 검증 항목입니다.\n\n기존 **v8**은 **Start-Korean-v8.cmd**로 실행할 수 있습니다. 저장 데이터는 v8의 최신 파일을 독립 복사했으며 두 버전의 이후 저장 내용은 자동 동기화하지 않습니다.'
guide=guide.replace(oldpara,newpara)
guide+='\n\nv9 추가 검증: 한글 1,400자의 ANSI 매핑과 Unicode 표시가 일치했고, 19/23 크기·1×/4× 렌더에서 누락/셀 경계 접촉이 없었습니다. 이름 117개의 최대 폭은 161.75/198입니다. 네이티브 overflow 분기는 경계 6사례를 모의 실행했고, 추가 콜백의 일반/강제 진행 분기를 정적으로 확인했습니다. 게임 플레이 검증 결과로 해석하면 안 됩니다.\n'
(R/'한국어화-실행안내.md').write_text(guide,encoding='utf-8');(T/'한국어화-상태.md').write_text(guide,encoding='utf-8')
if args.install:
 p=R/'progress.json';g=load(p);g.update(runtime=str(T),updated_at=datetime.datetime.now().astimezone().isoformat());g['body_ui_integration'].update(label=LABEL,build=str(O),runtime=str(T));g['translation']['build']=str(O);g['translation']['native_title_screen_verified']=False
 g['display_performance_followup'].update(status='large_text_v9_installed_user_runtime_pending',build=LABEL,candidate=str(C),static_verification=str(D),default_launcher='Start-Korean.cmd',explicit_launcher='Start-Korean-4K.cmd',fallback_launcher='Start-Korean-v8.cmd',runtime_verified=False,stutter_cause_confirmed=False)
 g['next']='User performs actual 4K fullscreen and larger-body text/page flow check. No further automated runtime verification requested.';dump(p,g)
 dump(R/'reports/latest-combined-build.json',{'path':str(O),'runtime':str(T),'manifest_sha256':sha((O/'manifest.json').read_bytes()),'label':LABEL})
print(json.dumps({'label':LABEL,'runtime':str(T),'installed_as_default':args.install,'new_payload_hashes':{n:m['outputs'][n] for n in changed},'savedata_files_copied':len(savehash),'game_executed':False},ensure_ascii=False))

