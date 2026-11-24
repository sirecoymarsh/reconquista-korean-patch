"""Stage the tested HD delta beside v9; install launchers only with --install.
All image integrity/shape checks already performed by hires_assets/hires_title are reused.
"""
from pathlib import Path
import os,sys,json,hashlib,shutil,datetime,struct,re,argparse,math
import pefile
R=Path(__file__).resolve().parents[1];C=R/'candidates/hires-v1';BASE='body-ui-20261023-v9';LABEL='body-ui-20261023-v10-hd';B=R/'builds'/BASE;S=R/('runtime-'+BASE);O=R/'builds'/LABEL;T=R/('runtime-'+LABEL)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text('utf-8-sig'))
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf-8')
assert not Path(r'C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json').exists()
ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');args=ap.parse_args()
assert sha(B/'manifest.json')=='cf92175e3ad9e7882bc91d13ff3892faab56d875292036382cbb4acc6f25d9cb'
assert sha(B/'レコンキスタ.exe')=='c1ffd2ef88222492dcdd9b08e0d6757a8ac92fa4110150671a163b979331f266'
# Deterministic PE bootstrap; existing native code sections are never relocated.
def build_exe():
 source=B/'レコンキスタ.exe';pe=pefile.PE(str(source));b=bytearray(source.read_bytes());last=pe.sections[-1];align=lambda v,a:(v+a-1)//a*a
 va=align(last.VirtualAddress+max(last.Misc_VirtualSize,last.SizeOfRawData),pe.OPTIONAL_HEADER.SectionAlignment);raw=align(len(b),pe.OPTIONAL_HEADER.FileAlignment);b.extend(b'\0'*(raw-len(b)))
 imports={i.name:i.address for d in pe.DIRECTORY_ENTRY_IMPORT for i in d.imports if i.name};nameva=0x400000+va+128
 code=b'\x9c\x60\x68'+struct.pack('<I',nameva)+b'\xff\x15'+struct.pack('<I',imports[b'LoadLibraryA'])+b'\x85\xc0\x75\x08\x6a\x48\xff\x15'+struct.pack('<I',imports[b'ExitProcess'])+b'\x61\x9d'
 code+=b'\xe9'+struct.pack('<i',(0x400000+pe.OPTIONAL_HEADER.AddressOfEntryPoint)-(0x400000+va+len(code)+5));section=code.ljust(128,b'\0')+b'ReconquistaHD.dll\0';section=section.ljust(align(len(section),pe.OPTIONAL_HEADER.FileAlignment),b'\0');b.extend(section)
 header=last.get_file_offset()+40;assert header+40<=pe.OPTIONAL_HEADER.SizeOfHeaders and not any(b[header:header+40]);struct.pack_into('<8sIIIIIIHHI',b,header,b'.hd\0\0\0\0\0',len(section),va,len(section),raw,0,0,0,0,0x60000020)
 struct.pack_into('<H',b,pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),pe.FILE_HEADER.NumberOfSections+1);struct.pack_into('<I',b,pe.OPTIONAL_HEADER.get_field_absolute_offset('AddressOfEntryPoint'),va);struct.pack_into('<I',b,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),align(va+len(section),pe.OPTIONAL_HEADER.SectionAlignment));struct.pack_into('<H',b,pe.FILE_HEADER.get_field_absolute_offset('Characteristics'),pe.FILE_HEADER.Characteristics|0x20)
 assert pe.OPTIONAL_HEADER.ImageBase==0x400000 and not(pe.OPTIONAL_HEADER.DllCharacteristics&0x40)
 d=load(C/'dpi-manifest.json');at=d['resource_offset'];size=d['resource_size'];assert bytes(b[at:at+size]).decode()==d['source_xml'];b[at:at+size]=d['output_xml'].encode().ljust(size,b' ')
 assert bytes(b)==(C/'runtime-prototype/レコンキスタ.exe').read_bytes(),'tested candidate must match reproducible build'
 for sec in pe.sections:
  if sec.Name.rstrip(b'\0')!=b'.rsrc':assert bytes(b[sec.PointerToRawData:sec.PointerToRawData+sec.SizeOfRawData])==sec.get_data()
 return bytes(b)
exe=build_exe();cg=load(C/'assets.json');menu=load(C/'title/manifest.json');trans=load(C/'title/transitions.json');assert cg['status']=='complete' and cg['completed']==cg['total']==1758
entries=list(cg['entries'].values())+menu['entries']+trans['entries'];assert len(entries)==1771 and len({e['key'] for e in entries})==1771
assert len(menu['entries'])==9 and sum(len(e['labels']) for e in menu['entries'])==45
for e in entries:
 p=C/'assets'/e['file'];assert p.is_file();e['bytes']=p.stat().st_size
# Exhaustive coordinate identity over several real and awkward noninteger viewport widths.
geometry=[]
for w in [800,806,880,1280,1600,1920,2880,3200]:
 h=w*3//4
 for x in range(800):assert math.floor(math.ceil(x*w/800)*800/w)==x
 for y in range(600):assert math.floor(math.ceil(y*h/600)*600/h)==y
 geometry.append({'viewport':[w,h],'axis_samples':1400,'roundtrip_failures':0})
for e in menu['entries']:
 for label in e['labels']:
  x,y,w,h=label['logical_hitbox'];bb=label['bbox'];assert x*4<=bb[0]<bb[2]<=(x+w)*4 and y*4<=bb[1]<bb[3]<=(y+h)*4
assetman={'model':'high-fidelity-4x','scale':4,'selection':'Four local model sample comparison; preserved original soft contour, face shape, and painting texture best. No generative restyling.','model_sha256':cg['model_sha256'],'cg_background_assets':1758,'menu_states':9,'transition_backgrounds':4,'total':1771,'bytes':sum(e['bytes'] for e in entries),'integrity_proof_reused':['candidates/hires-v1/assets.json','candidates/hires-v1/title/manifest.json','candidates/hires-v1/title/transitions.json'],'coverage':'Full-size RCT images >=400x400 in data/data1/data2, plus all13 title assets; thumbnails, slowdata character animations/masks, other UI and movies retain their existing source resolution.','translator_model':'Codex internal','accepted_text_unchanged':True,'entries':entries}
if not O.exists():
 assert not T.exists();O.mkdir();T.mkdir();savehash=[]
 for origin,dest in [(B,O),(S,T)]:
  for p in origin.rglob('*'):
   rel=p.relative_to(origin);q=dest/rel
   if p.is_dir():q.mkdir(exist_ok=True)
   elif p.name not in ['レコンキスタ.exe','manifest.json','installation.json','BUILD-IDENTITY.json','한국어화-상태.md']:
    if origin==S and rel.parts[0]=='savedata':shutil.copy2(p,q);assert sha(p)==sha(q);savehash.append({'file':rel.as_posix(),'sha256':sha(q)})
    else:os.link(p,q)
  (dest/'レコンキスタ.exe').write_bytes(exe);shutil.copy2(C/'native/ReconquistaHD.dll',dest/'ReconquistaHD.dll');dump(dest/'hires-manifest.json',assetman);(dest/'hires').mkdir()
  for e in entries:os.link(C/'assets'/e['file'],dest/'hires'/e['file'])
 D=O/'delta-inputs/hires-v1';D.mkdir(parents=True)
 for n in ['ReconquistaHD.cpp','hooks.inc','hooks.json','Build.cmd']:shutil.copy2(C/'native'/n,D/n)
 for n in ['assets.json','dpi-manifest.json']:shutil.copy2(C/n,D/n)
 for n in ['manifest.json','transitions.json']:shutil.copy2(C/'title'/n,D/('title-'+n))
 for n in ['build_hires_runtime.py','hires_assets.py','hires_title.py']:shutil.copy2(R/'tools'/n,D/n)
 m=load(B/'manifest.json');m.update(label=LABEL,parent_build=str(B),parent_manifest_sha256=sha(B/'manifest.json'),installed_runtime=str(T),status='hires_staged',savedata_copied_from=str(S/'savedata'),save_copy_hashes=savehash,runtime_verified=False)
 for n in ['レコンキスタ.exe','ReconquistaHD.dll','hires-manifest.json']:m['outputs'][n]=sha(T/n)
 m['exe_sha256']=m['outputs']['レコンキスタ.exe'];m['high_resolution']={'asset_manifest':'hires-manifest.json','native_source':'delta-inputs/hires-v1','logical_canvas':[800,600],'backing_canvas':[3200,2400],'aspect_ratio':'4:3 letterboxed','viewport_3840x2160':[480,0,2880,2160],'viewport_4096x2160':[608,0,2880,2160],'window_client':[1600,1200],'dpi_aware':'system','engine_scaling':'Offline assets composited by native copy/alpha/mask/swap/transform at4x, with source-coordinate logic retained. Untracked effects fall back to faithful logical pixels.','memory_budget_mb':768,'allocation_ceiling_mb':1400,'previous_v9_preserved':True,'performance_stutter_fix_claimed':False,'actual_onscreen_gameplay_verified':False}
 dump(O/'manifest.json',m);dump(T/'BUILD-IDENTITY.json',m);dump(D/'geometry-verification.json',{'pass':True,'coordinate_cases':geometry,'menu_label_fits':45,'upscaler_and_menu_integrity_results_reused':True,'pe_code_sections_identical_to_v9':True,'bootstrap_matches_tested_executable':True})
else:
 m=load(O/'manifest.json');assert sha(T/'レコンキスタ.exe')==hashlib.sha256(exe).hexdigest();assert sha(T/'ReconquistaHD.dll')==sha(C/'native/ReconquistaHD.dll')
if args.install:
 proof=load(C/'verification.json');assert proof['pass'] and proof['exe_sha256']==m['exe_sha256'] and proof['dll_sha256']==m['outputs']['ReconquistaHD.dll']
 shutil.copy2(C/'verification.json',O/'delta-inputs/hires-v1/verification.json');shutil.copy2(C/'native-mode-probe-final.log',O/'delta-inputs/hires-v1/native-mode-probe-final.log')
 old=(R/'Start-Korean.ps1').read_text('utf-8-sig');assert BASE in old
 (R/'Start-Korean-v9.ps1').write_text(old,'utf-8-sig');cmd='@echo off\r\npushd "%~dp0"\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0{script}"\r\nif errorlevel 1 pause\r\npopd\r\n';(R/'Start-Korean-v9.cmd').write_bytes(cmd.format(script='Start-Korean-v9.ps1').encode('ascii'))
 new=old.replace(BASE,LABEL).replace('param([switch]$PrepareOnly)','param([switch]$PrepareOnly,[switch]$VerifyAssets)')
 check='''$assetManifest = Get-Content -LiteralPath (Join-Path $runtimeDir 'hires-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($asset in $assetManifest.entries) {
    $assetPath = Join-Path $runtimeDir ('hires\\' + $asset.file)
    if (-not (Test-Path -LiteralPath $assetPath) -or (Get-Item -LiteralPath $assetPath).Length -ne $asset.bytes) { throw ('고해상도 파일 누락 또는 크기 불일치: ' + $asset.name) }
    if ($VerifyAssets -and (Get-FileHash -LiteralPath $assetPath -Algorithm SHA256).Hash -ne $asset.sha256) { throw ('고해상도 파일 해시 불일치: ' + $asset.name) }
}
Remove-Item Env:RECON_HD_PROBE -ErrorAction SilentlyContinue
$env:RECON_HD_START_FULLSCREEN = '1'
'''
 new=new.replace('$acp = ',check+'$acp = ')
 for n in ['Start-Korean.ps1','Start-Korean-4K.ps1']:(R/n).write_text(new,'utf-8-sig')
 (R/'Start-Korean-4K.cmd').write_bytes(cmd.format(script='Start-Korean-4K.ps1').encode('ascii'))
 m.update(status='hires_installed_hidden_runtime_pass_user_gameplay_pending');m['high_resolution']['hidden_runtime_proof']='delta-inputs/hires-v1/verification.json';dump(O/'manifest.json',m);dump(T/'BUILD-IDENTITY.json',m)
 guide='''# 레콘키스타 한국어판 v10 HD

`Start-Korean-4K.cmd` 또는 `Start-Korean.cmd`로 실행합니다. 최초 메뉴 초기화가 끝나면 모니터 해상도의 전체 화면으로 시작합니다. F4는 전체 화면, Alt+Enter는 큰 창입니다. Windows 디스플레이 해상도를 변경하지 않습니다.

원본의 4:3 비율을 유지합니다. 3840×2160에서는 게임 영역 2880×2160과 좌우480픽셀 여백, 4096×2160에서는 좌우608픽셀 여백입니다. 내부 고해상도 그림은3200×2400이며, 창 모드의 기본 게임 영역은1600×1200입니다. 버튼 판정은 원래800×600 좌표로 역변환합니다.

메인 메뉴9상태·45문구를88픽셀 글꼴로 다시 그렸습니다. 기존 승인된 한국어 문구와 로고 원본을 재사용했습니다. CG·배경1758장과 메뉴 전환 배경4장을 로컬 High Fidelity4×로 확대했습니다. 비교한4모델 중 원래 선의 부드러움·얼굴 형태·채색 보존이 가장 나았습니다. AI 확대는 원본에 없던 세부가 정확히 복원됐음을 뜻하지 않습니다.

작업은 미리 끝낸 PNG를 읽는 방식입니다. 게임 실행 중 AI 추론을 하지 않습니다. 고해상도 그림 캐시는768MiB, 할당 상한은1400MiB입니다. 이식하지 않은 일부 효과·동영상·서 있는 인물의 애니메이션과 작은 UI는 기존 해상도를 사용합니다. 대사 글꼴은v9의 큰 글꼴을 유지합니다. 실제 장시간 플레이의 버벅임 개선을 확정한 버전은 아닙니다.

검증: 전체 자산의 생성 시 크기·PNG 무결성·SHA256, 메뉴 영역45개, PE 코드 보존, 숨김 게임에서 고해상도 복사13종과 출력/좌표 변환을 확인했습니다. 실제 화면의 클릭·대사 잘림·전환 효과와 장시간 플레이는 사용자 확인이 남아 있습니다.

기존 버전은 `Start-Korean-v9.cmd`로 실행합니다. v9 파일을 수정하지 않았고 저장 데이터는 v10에 독립 복사했습니다. 이후 두 버전의 저장 내용은 자동 동기화되지 않습니다. 문제 발생 시v9로 바로 돌아갈 수 있습니다.

실행기는 주요 패치 파일 해시 및 고해상도 자산의 개수/크기를 확인합니다. 고해상도 파일 전체 SHA256 재검사는 필요할 때 `powershell -NoProfile -ExecutionPolicy Bypass -File .\\Start-Korean-4K.ps1 -PrepareOnly -VerifyAssets`로 실행할 수 있습니다.
'''
 (R/'한국어화-실행안내.md').write_text(guide,'utf-8');(T/'한국어화-상태.md').write_text(guide,'utf-8')
 g=load(R/'progress.json');g.update(runtime=str(T),updated_at=datetime.datetime.now().astimezone().isoformat(),next='User runs Start-Korean-4K.cmd and checks real screen/gameplay. v9 preserved via Start-Korean-v9.cmd. No pending asset generation or integration in HD scope.');g['body_ui_integration'].update(label=LABEL,build=str(O),runtime=str(T));g['translation']['build']=str(O)
 g['hires_v10_checkpoint'].update(status='installed_hidden_runtime_pass_user_gameplay_pending',build=str(O),runtime=str(T),cg_complete=1758,menu_states=9,transition_backgrounds=4,model='high-fidelity-4x',verification=str(O/'delta-inputs/hires-v1/verification.json'),default_launcher='Start-Korean.cmd',explicit_launcher='Start-Korean-4K.cmd',fallback_launcher='Start-Korean-v9.cmd',native_unverified=['actual onscreen gameplay and transitions'],next='User runtime review only; HD build integration complete')
 g['menu_upscale_followup'].update(status='v10_hd_integrated',model='high-fidelity-4x',game_modified=True);dump(R/'progress.json',g);dump(R/'reports/latest-combined-build.json',{'path':str(O),'runtime':str(T),'label':LABEL,'manifest_sha256':sha(O/'manifest.json')})
print(json.dumps({'runtime':str(T),'assets':1771,'asset_gib':round(assetman['bytes']/1024**3,2),'installed':args.install},ensure_ascii=False))
