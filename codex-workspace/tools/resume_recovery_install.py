from pathlib import Path
import json,os,shutil,datetime
from inspect_majiro import sha,dump
import build_trial as b
ROOT=b.ROOT;LABEL='recovery-full-20261023-v1';F=ROOT/'translation/integration'/LABEL;B=ROOT/'builds'/('integrated-'+LABEL)
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
d=load(F/'integrated-targets.json');m=load(B/'manifest.json');report=load(F/'integration-report.json');verification=load(F/'verification.json');mp=load(B/'font-map.json')['mapping']
assert sha((F/'integrated-targets.json').read_bytes())==report['snapshot_sha256']==verification['snapshot_sha256']
assert sha((B/'scenario.arc').read_bytes())==verification['scenario_sha256']
m['post_build_review_delta']={'prior_scenario_sha256':m['outputs']['scenario.arc'],'change':d['root_review']['changes'][-1],'validation':'Exact-field b.rewrite control-flow/retargeting checks and archive payload comparisons completed before existing verification.json was written; results reused after an installation-only Path/hash type error.'}
m.update(snapshot_sha256=verification['snapshot_sha256'],root_review=d['root_review']);m['outputs']['scenario.arc']=verification['scenario_sha256']
for key,filename,reportname in [('font','ReconquistaKR.otf','recovery-full-gdi-sans.json'),('serif_font','ReconquistaKRSerif.otf','recovery-full-gdi-serif.json')]:
 evidence=load(ROOT/'reports'/reportname);assert evidence['pass'] and evidence['font_sha256']==sha((B/'font'/filename).read_bytes());m[key]['runtime_gdi_verified']=True
fieldmax=verification['max_recovered_field_advance_px'];namemax=verification['max_name_advance_px']
out=ROOT/('runtime-'+LABEL);out.mkdir(exist_ok=True);assert set(p.name for p in out.iterdir())<={'scenario.arc'},'Only prior interrupted installer payload is accepted';assert not (out/'scenario.arc').exists() or sha((out/'scenario.arc').read_bytes())==m['outputs']['scenario.arc']
for n in ['scenario.arc','fastdata.arc']:shutil.copy2(B/n,out/n);assert sha((out/n).read_bytes())==m['outputs'][n]
shutil.copytree(B/'font',out/'font')
for key,filename in [('font','ReconquistaKR.otf'),('serif_font','ReconquistaKRSerif.otf')]:assert sha((out/'font'/filename).read_bytes())==m[key]['output_sha256']
for n in ['data.arc','data1.arc','data2.arc','slowdata.arc','stream.arc','voice.arc']:os.link(ROOT/'research/disc'/n,out/n)
shutil.copy2(ROOT/'research/disc/bin/レコンキスタ.exe',out/'レコンキスタ.exe');assert sha((out/'レコンキスタ.exe').read_bytes())==m['original_exe_sha256']
for p in (ROOT/'research/disc/movie').rglob('*'):
 if p.is_file():q=out/'movie'/p.relative_to(ROOT/'research/disc/movie');q.parent.mkdir(parents=True,exist_ok=True);os.link(p,q)
m['status']='integrated_installed_static_gdi_pass_visual_pending';m['runtime_path']=str(out);m['verification_report']=str(F/'verification.json');m['runtime']['visual_blocker']=verification['native_game_blocker'];m['runtime']['actual_game_screen']=False
for p in [B/'manifest.json',out/'BUILD-IDENTITY.json']:dump(p,m)
dump(ROOT/'reports/latest-recovery-build.json',{'path':str(B),**m})
report.update(status=m['status'],runtime=str(out),verification=str(F/'verification.json'));dump(F/'integration-report.json',report)
latest={'snapshot':LABEL,'snapshot_path':str(F/'integrated-targets.json'),'snapshot_sha256':m['snapshot_sha256'],'build':str(B),'normal_runtime':str(out),'status':m['status'],'units':46913,'text_fields':73314,'inline_fields':625,'verification':str(F/'verification.json'),'body_units_remaining':38};dump(ROOT/'translation/integration/latest.json',latest)
progress=load(ROOT/'progress.json');progress['recovery_20261023']={**latest,'content_reviewed':57,'content_restored':20,'technical_resolved':5,'content_remaining':{'direct_context':33,'boundary_action':4},'other_semantic_pending':'st_gin.mjo::u0068','next':'Resolve remaining ordinary meaning questions where evidence permits; UI work remains in separate session; actual new-build visual QA pending because Computer Use initialization failed.'};progress['updated_at']=datetime.datetime.now().astimezone().isoformat();dump(ROOT/'progress.json',progress)
readme='''# 레콘키스타 한국어 본문 통합본\n\n본문 46,913구간 / 일반 필드 73,314개 / 인라인 625개를 적용했습니다.\n이번 보류 재검토에서 일반 대사·서술 20구간을 복구했고, 기술 보류 5구간을 해결했습니다.\n\n- 일반 실행 파일: `レコンキスタ.exe` (원본 실행 파일, 변경 없음)\n- 제품 디스크: `P:\\GAME\\Reqonquist Novel H\\Reconquista.iso`를 읽기 전용으로 연결해야 합니다.\n- 루트의 `Start-Korean-Recovery.ps1`은 디스크와 패치 해시를 확인한 뒤 이 사본을 실행합니다.\n- 게임 본체와 새 글꼴은 P:의 별도 실행 사본에 설치되어 있습니다. 기존 사본과 원본은 보존했습니다.\n\n글꼴 1,398글자의 CP932 표시·Unicode 표시 일치 검사와 새 교체 필드의 컴파일 결과 검사를 통과했습니다.\n화면 제어 도구 초기화 실패로 이 빌드의 실제 게임 화면 검증은 아직 완료하지 못했습니다. 수동 루비의 위치, 화자 이름, 장문 줄바꿈은 실제 화면에서 추가 확인이 필요합니다.\n\n본문 보류 37구간과 의미 미확정 1구간은 원문을 유지했습니다. UI·오프닝·엔딩은 별도 세션의 작업이며 이 본문 통합본의 완료 범위에 포함되지 않습니다.\n선택지 문자열이 바뀌면서 이전 선택지 읽음 표시 일부가 이어지지 않을 수 있습니다. 전체 루트·세이브 호환성 검증은 미완료입니다.\n'''
(out/'한국어화-상태.md').write_text(readme,encoding='utf-8');(F/'완료보고.md').write_text(readme,encoding='utf-8')
print(json.dumps({'runtime':str(out),'units':46913,'recovered_general':20,'technical':5,'glyphs':len(mp),'max_new_field_px':fieldmax,'max_name_px':namemax,'native_game_visual_verified':False},ensure_ascii=False))
