"""Install the verified review option beside preserved v10 HD."""
from pathlib import Path
import json,hashlib,shutil,os,datetime
R=Path(__file__).resolve().parents[1];C=R/'candidates/review-unlock-v1'
BASE='body-ui-20261023-v10-hd';LABEL='body-ui-20261023-v11-review'
B=R/'builds'/BASE;S=R/('runtime-'+BASE);O=R/'builds'/LABEL;T=R/('runtime-'+LABEL)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text('utf-8-sig'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8')
assert not Path(r'C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json').exists()
proof=load(C/'verification.json');assert proof['pass'] and proof['dll_sha256']==sha(C/'native/ReconquistaHD.dll')
old=(R/'Start-Korean.ps1').read_text('utf-8-sig');assert BASE in old
assert not O.exists() and not T.exists(),'Do not overwrite existing installation'
basehash={n:sha(B/n) for n in ['manifest.json','レコンキスタ.exe','ReconquistaHD.dll']}
base=load(B/'manifest.json');assert sha(S/'ReconquistaHD.dll')==base['outputs']['ReconquistaHD.dll']
assert proof['exe_sha256']==base['exe_sha256']
O.mkdir();T.mkdir();saves=[]
skip={'manifest.json','installation.json','BUILD-IDENTITY.json','한국어화-상태.md','ReconquistaHD.dll','hires-runtime.log','review-unlock.enabled'}
for origin,dest in [(B,O),(S,T)]:
 for p in origin.rglob('*'):
  rel=p.relative_to(origin);q=dest/rel
  if p.is_dir():q.mkdir(exist_ok=True)
  elif len(rel.parts)==1 and p.name in skip:continue
  elif origin==S and rel.parts[0]=='savedata':
   shutil.copy2(p,q);assert sha(p)==sha(q);saves.append({'file':rel.as_posix(),'sha256':sha(q),'independent_copy':True})
  else:os.link(p,q)
 shutil.copy2(C/'native/ReconquistaHD.dll',dest/'ReconquistaHD.dll')
D=O/'delta-inputs/review-unlock-v1';D.mkdir(parents=True)
for n in ['ReconquistaHD.cpp','hooks.inc','hooks.json','Build.cmd']:shutil.copy2(C/'native'/n,D/n)
for n in ['design.json','verification.json','probe-core-pass.log','probe-final.log','review.json']:shutil.copy2(C/n,D/n)
shutil.copy2(Path(__file__),D/'build_review_unlock.py')
shutil.copy2(R/'reports/review-unlock-native-evidence.json',D/'native-evidence.json')
m=base.copy();m.update(label=LABEL,parent_build=str(B),parent_manifest_sha256=basehash['manifest.json'],installed_runtime=str(T),status='review_option_installed_hidden_runtime_pass',savedata_copied_from=str(S/'savedata'),save_copy_hashes=saves,runtime_verified=False)
m['outputs']=dict(base['outputs']);m['outputs']['ReconquistaHD.dll']=sha(T/'ReconquistaHD.dll')
m['review_unlock']={**load(C/'design.json'),'default_enabled':False,'proof':'delta-inputs/review-unlock-v1/verification.json','native_review':'delta-inputs/review-unlock-v1/review.json','persistence':'runtime-local review-unlock.enabled; unset by default','existing_v10_preserved':True,'all_read_marks_or_story_skip_claimed':False,'actual_visible_gameplay_verified':False}
m['high_resolution']=dict(base['high_resolution']);m['high_resolution']['verification_reused_from']=str(B/'delta-inputs/hires-v1/verification.json')
dump(O/'manifest.json',m);dump(T/'BUILD-IDENTITY.json',m)
(R/'Start-Korean-v10.ps1').write_text(old,'utf-8-sig')
cmd='@echo off\r\npushd "%~dp0"\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0{script}"\r\nif errorlevel 1 pause\r\npopd\r\n'
(R/'Start-Korean-v10.cmd').write_bytes(cmd.format(script='Start-Korean-v10.ps1').encode('ascii'))
new=old.replace(BASE,LABEL).replace('Remove-Item Env:RECON_HD_PROBE -ErrorAction SilentlyContinue','Remove-Item Env:RECON_HD_PROBE -ErrorAction SilentlyContinue\nRemove-Item Env:RECON_REVIEW_PROBE -ErrorAction SilentlyContinue')
for n in ['Start-Korean.ps1','Start-Korean-4K.ps1']:(R/n).write_text(new,'utf-8-sig')
guide=(R/'한국어화-실행안내.md').read_text('utf-8').replace('# 레콘키스타 한국어판 v10 HD','# 레콘키스타 한국어판 v11 HD · 검수 옵션')
addition="""
검수용 전체 개방: 창 모드에서 상단 ‘파일/설정 → 검수용 모든 콘텐츠 개방’을 체크합니다. 전체 화면에서도 Ctrl+F10으로 켜거나 끌 수 있습니다. 처음에는 꺼져 있습니다. 같은 항목을 다시 누르면 개방을 취소합니다.

CG 열람·회상 7개·음악·추가 메뉴·클리어 후 선택지를 임시로 개방합니다. 변경 뒤에는 타이틀로 돌아가거나 추가 메뉴에 다시 들어가세요. 진행 중인 장면을 자동으로 재시작하지 않습니다.

실제 달성·CG 해금 테이블은 유지하고 검수 중의 해금 판정만 바꿉니다. 검수 중 얻은 해당 달성·CG 기록도 원래 테이블에 쓰지 않습니다. 일반 저장 슬롯과 설정은 평소처럼 저장됩니다. 옵션 상태는 이 실행본의 review-unlock.enabled 파일에만 저장됩니다. 읽음 기록 전체를 채우거나 본문 진행 위치를 변경하는 기능은 아닙니다.

숨김 실행 검증에서 개방·취소, 메뉴 이벤트, Ctrl+F10 및 반복 입력, VM 반환값, 원래 달성·CG 테이블 보존을 확인했습니다. 실제 화면의 갤러리 탐색과 회상 재생은 사용자가 검수합니다.

옵션 추가 전 v10 HD는 Start-Korean-v10.cmd로 실행합니다. v10과 v9는 그대로 보존했고 v11 저장 파일은 독립 복사했습니다. 버전 간 저장 데이터는 자동 동기화되지 않습니다.

"""
guide=guide.replace('\n\n','\n\n'+addition,1)
(R/'한국어화-실행안내.md').write_text(guide,'utf-8');(T/'한국어화-상태.md').write_text(guide,'utf-8')
g=load(R/'progress.json');g.update(runtime=str(T),updated_at=datetime.datetime.now().astimezone().isoformat(),next='User runs default launcher and toggles File/settings review unlock or Ctrl+F10. Onscreen gallery/gameplay review user-deferred.');g['body_ui_integration'].update(label=LABEL,build=str(O),runtime=str(T));g['translation']['build']=str(O)
g['review_unlock_checkpoint']={'status':'installed_hidden_runtime_pass_user_visual_review_pending','candidate':str(C),'build':str(O),'runtime':str(T),'verification':str(D/'verification.json'),'default_enabled':False,'shortcut':'Ctrl+F10','fallback':'Start-Korean-v10.cmd','source_record_tables_unchanged':True,'next':'User gallery and scene review; toggle off to return original unlock state.'}
dump(R/'progress.json',g);dump(R/'reports/latest-combined-build.json',{'path':str(O),'runtime':str(T),'label':LABEL,'manifest_sha256':sha(O/'manifest.json')})
assert all(sha(B/n)==h for n,h in basehash.items())
assert not(T/'review-unlock.enabled').exists()
dump(D/'installation-verification.json',{'pass':True,'v10_critical_files_unchanged':basehash,'v10_savedata_independently_copied':saves,'hd_assets_hardlinked':True,'default_off':True,'new_dll_sha256':sha(T/'ReconquistaHD.dll'),'launcher_prepare_pending':True})
print(json.dumps({'installed':True,'runtime':str(T),'fallback':'Start-Korean-v10.cmd','default_unlock':False},ensure_ascii=False))
