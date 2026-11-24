from pathlib import Path
import os,json,shutil,datetime,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));from inspect_majiro import sha,dump
LABEL='body-ui-20261023-v1';B=R/'builds'/LABEL;T=R/('runtime-'+LABEL);OLD=R/'runtime-recovery-full-20261023-v2';U=R/'ui-opening-ending'
assert not T.exists();T.mkdir();manifest=json.loads((B/'manifest.json').read_text(encoding='utf-8'));assert manifest['status']=='combined_static_gdi_security_pass_user_runtime_deferred'
installed=[]
for name in ['data.arc','data1.arc','data2.arc','slowdata.arc','stream.arc','voice.arc']:
 os.link(OLD/name,T/name);assert os.path.samefile(OLD/name,T/name);installed.append({'file':name,'method':'hardlink_unchanged_original','source':str(OLD/name)})
for p in (OLD/'movie').rglob('*'):
 q=T/'movie'/p.relative_to(OLD/'movie')
 if p.is_dir():q.mkdir(parents=True,exist_ok=True)
 else:q.parent.mkdir(parents=True,exist_ok=True);os.link(p,q);assert os.path.samefile(p,q)
for name,expected in manifest['outputs'].items():
 shutil.copy2(B/name,T/name);assert sha((T/name).read_bytes())==expected;installed.append({'file':name,'sha256':expected,'method':'verified_copy'})
shutil.copytree(B/'font',T/'font')
for name,key in [('ReconquistaKR.otf','font'),('ReconquistaKRSerif.otf','serif_font')]:assert sha((T/'font'/name).read_bytes())==manifest[key]['output_sha256']
shutil.copytree(OLD/'savedata',T/'savedata');savefiles=[]
for p in (OLD/'savedata').rglob('*'):
 if p.is_file():
  relative=p.relative_to(OLD/'savedata');assert sha(p.read_bytes())==sha((T/'savedata'/relative).read_bytes());savefiles.append({'file':str(relative),'sha256':sha(p.read_bytes())})
manifest.update(installed_runtime=str(T),installed_copy_hashes_pass=True,savedata_copied_from=str(OLD/'savedata'),save_copy_hashes=savefiles)
dump(B/'manifest.json',manifest);dump(T/'BUILD-IDENTITY.json',manifest);dump(B/'installation.json',{'files':installed,'savedata_preserved':savefiles,'game_executed':False,'visual_owner':'user'})
# The installer display payload is delivered separately. It is not a new patch installer.
D=R/'deliverables/installer-ui-20261023-v1';D.mkdir(parents=True,exist_ok=False);P=D/'payloads';P.mkdir();files=[]
for name,source,expected in [
 ('setup.exe',U/'candidates/installer-ui-v4/setup.exe','546f64b7d0128521d0fc163da7d9190a44cbe0fec2bf429f0a6666c058fbbc4d'),
 ('install.exe',U/'candidates/installer-ui-v4/install.exe','cc99b036927fe5aee9517aebeb95ec994f52a7058f082acba68e460163a4ce8c'),
 ('readme.txt',U/'candidates/installer-readme-v1/payloads/readme.txt','11855ae54b41419296aa037898cb1bdac8374a011eb6a99bdf7899e653e128ec')]:
 assert sha(source.read_bytes())==expected;shutil.copy2(source,P/name);assert sha((P/name).read_bytes())==expected;files.append({'file':'payloads/'+name,'source':str(source),'sha256':expected})
dump(D/'manifest.json',{'translator_model':'Codex internal','status':'reviewed_original_installer_ui_payloads','installer_fields':88,'readme_fields':10,'files':files,'exact_existing_security_and_display_proofs_reused':['ui-opening-ending/reports/installer-ui-v4-defender-scan.json','ui-opening-ending/reports/installer-ui-v3-defender-scan.json','ui-opening-ending/candidates/installer-ui-v4/manifest.json','ui-opening-ending/candidates/installer-readme-v1/manifest.json'],'installer_executed':False,'standalone_installer':False,'required_windows_acp':949})
(D/'안내.md').write_text('원본 설치 화면의 한국어화 파일 3개를 모은 검토본입니다. setup.exe·install.exe 88필드와 readme.txt 10필드를 포함합니다. 원본 설치 미디어의 나머지 파일이 필요하며, 이 폴더만으로 설치할 수 없습니다. 실제 설치·삭제·안내문 열기는 아직 실행 검증하지 않았습니다.\n\n게임 실행은 프로젝트의 Start-Korean.ps1을 사용하세요. 이 설치 화면 파일은 본문 패치를 적용하는 설치기가 아닙니다.\n',encoding='utf-8')
# New launcher verifies patched game separately from the original DVD binary.
launcher=(R/'Start-Korean-Recovery.ps1').read_text(encoding='utf-8-sig').replace('runtime-recovery-full-20261023-v2','runtime-'+LABEL).replace('builds\\integrated-recovery-full-20261023-v2\\manifest.json','builds\\'+LABEL+'\\manifest.json')
launcher=launcher.replace("$manifest.original_exe_sha256) { throw '실행 파일이 검증된 원본과 다릅니다.' }","$manifest.exe_sha256) { throw '실행 파일이 검증된 통합본과 다릅니다.' }")
assert "$discExe -Algorithm SHA256).Hash -ne $manifest.original_exe_sha256" in launcher
marker="$disk = Get-DiskImage -ImagePath $iso"
launcher=launcher.replace(marker,"$acp = (Get-ItemProperty -LiteralPath 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Nls\\CodePage' -Name ACP).ACP\nif ($acp -ne '949') { throw '이 통합본의 네이티브 한국어 창은 Windows 비유니코드 프로그램 언어가 한국어(ACP 949)인 환경을 사용합니다. 현재 ACP: ' + $acp }\n"+marker)
(R/'Start-Korean.ps1').write_text(launcher,encoding='utf-8-sig')
(R/'Start-Korean-Integrated.ps1').write_text("param([switch]$PrepareOnly)\n& (Join-Path $PSScriptRoot 'Start-Korean.ps1') -PrepareOnly:$PrepareOnly\n",encoding='utf-8-sig')
now=datetime.datetime.now().astimezone().isoformat();state=json.loads((R/'progress.json').read_text(encoding='utf-8'));state.update(updated_at=now,status='body_and_completed_ui_integrated_remaining_ui_op_ed_active',runtime=str(T),next='Continue remaining UI/OP/ED in existing dedicated thread; integrate subsequent immutable candidates. Actual native-game screen QA deferred to user.')
state['body_ui_integration']={'label':LABEL,'runtime':str(T),'build':str(B),'launcher':'Start-Korean.ps1','body_units':46935,'ui_script_fields':143,'raster_label_instances':419,'timeline_cells':352,'timeline_source_retained_ids':manifest['timeline_original_retained_ids'],'native_resource_fields':147,'installer_fields':88,'installer_readme_fields':10,'static_pass':True,'new_font_gdi_pass':True,'exe_security_exact_prior_proof_reused':True,'user_actual_visual_pending':True,'installer_payloads':str(D),'op_ed_integrated':False}
state['usage_checkpoint']={'at':now,'limit_id':'codex','used_percent':18,'remaining_percent':82,'stop_marker_present':False,'ordinary_usage_allowed':True};dump(R/'progress.json',state);dump(R/'reports/latest-combined-build.json',{'path':str(B),'runtime':str(T),'manifest_sha256':sha((B/'manifest.json').read_bytes()),'label':LABEL})
text='''# 레콘퀴스타 한국어화 통합본

실행: 프로젝트의 **Start-Korean.ps1**. 기존 Start-Korean-Integrated.ps1도 같은 통합본을 실행합니다. 본문만 포함한 이전 Start-Korean-Recovery.ps1은 별도로 보존했습니다.

현재 통합: 본문46,935구간(대사73,350필드·인라인625필드·이름117개), UI 스크립트143필드, 래스터 문구419개, 연표352셀, 실행 파일 리소스147필드 및 네이티브 표시/오류문. 연표의 잠정 인명3셀과 본문16구간은 원문입니다.

UI의 나머지 이미지 문구와 오프닝·엔딩은 별도 세션에서 계속 작업 중입니다. 현재 통합본에는 아직 들어가지 않았습니다. 원본 설치 화면88필드와 안내문10필드는 deliverables/installer-ui-20261023-v1에 검토 파일로 보관했습니다.

본문·UI의 서로 다른 한글 매핑을 통합해 기존1,398개 슬롯을 보존하고2글자를 추가했습니다. 바뀐 스크립트의 분기·함수, 아카이브 재추출, 연표 구조·줄바꿈, 새 글꼴의 화면 밖 GDI 비교를 통과했습니다. 원본과 이전 통합본은 보존했습니다.

실제 게임 대사·이름·루비·백로그·선택지·설정 상태의 글자 깨짐 및 잘림, 전체 화면, 저장/불러오기와 OP/ED 동기는 사용자가 나중에 확인할 항목입니다. 이번 통합본의 실제 게임 화면 검증은 하지 않았습니다. 기존 증거의 재사용은 새 게임 실행 검사로 표시하지 않았습니다.

실행기는 통합 파일과 원본 DVD를 각각 검증합니다. 제품 ISO가 필요하며 실행 파일 이름은 レコンキスタ.exe를 유지해야 합니다. 네이티브 표시문은 Windows ACP949 환경용입니다. 시스템 설정을 자동으로 바꾸지 않습니다.

저장 데이터는 이전 본문 통합본의 savedata에서 해시 확인 후 복사했습니다. 이후 두 버전에서 플레이하면 저장 데이터는 각각 별도로 바뀝니다.
'''
(R/'한국어화-실행안내.md').write_text(text,encoding='utf-8');(T/'한국어화-상태.md').write_text(text,encoding='utf-8')
print(json.dumps({'runtime':str(T),'installer_payloads':str(D),'launcher':'Start-Korean.ps1','installed_hashes_pass':True,'game_executed':False},ensure_ascii=False))
