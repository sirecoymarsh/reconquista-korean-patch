"""Apply the one final review delta, validate new artifacts, and install a fresh P: game copy."""
from pathlib import Path
import json,sys,os,shutil,math,ctypes as C,ctypes.wintypes as W,datetime
import build_trial as b
import check_recovery_gdi as g
from inspect_majiro import Arc,sha,dump
ROOT=b.ROOT;LABEL='recovery-full-20261023-v1';F=ROOT/'translation/integration'/LABEL;B=ROOT/'builds'/('integrated-'+LABEL)
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
d=load(F/'integrated-targets.json');m=load(B/'manifest.json');assert sha((F/'integrated-targets.json').read_bytes())==m['snapshot_sha256']
mp=load(B/'font-map.json')['mapping'];inv={v:k for k,v in mp.items()}
row=next(x for x in d['records'] if x['id']=='maho_14.mjo::000259');assert row['target']=='똑똑,'
change={'id':row['id'],'before':'똑똑,','after':'똑똑.','reason':'Reuse prior approved central knocking punctuation; source batch merge had reverted it'}
row['target']=change['after'];row['integration_editor']='Codex internal /root';row['integration_review']=change['reason'];d['root_review']['changes'].append(change)
a=Arc(B/'scenario.arc');payloads={}
with a.path.open('rb') as f:
 for e in a.entries:f.seek(e['offset']);payloads[e['name']]=f.read(e['size'])
script,_=b.decode(payloads['maho_14.mjo']);assert ''.join(inv.get(c,c) for c in script.instructions[259].string)==change['before']
previous_scenario_sha=sha((B/'scenario.arc').read_bytes());payloads['maho_14.mjo'],delta=b.rewrite(payloads['maho_14.mjo'],{259:b.string_ins('text',''.join(mp.get(c,c) for c in row['target']))})
(B/'scenario.arc').write_bytes(a.rebuild(payloads));ar=Arc(B/'scenario.arc')
with ar.path.open('rb') as f:
 for e in ar.entries:f.seek(e['offset']);assert f.read(e['size'])==payloads[e['name']]
for filename in ['targets.json','integrated-targets.json']:dump(F/filename,d)
report=load(F/'integration-report.json');report['canonical_edits'].append(change);report['snapshot_sha256']=sha((F/'integrated-targets.json').read_bytes());dump(F/'integration-report.json',report)
m.update(snapshot_sha256=report['snapshot_sha256'],root_review=d['root_review']);m['outputs']['scenario.arc']=sha((B/'scenario.arc').read_bytes());m['script_validation']['maho_14.mjo']['output_sha256']=sha(payloads['maho_14.mjo']);m['post_build_review_delta']={'prior_scenario_sha256':previous_scenario_sha,'change':change,'rewrite_validation':delta}
# New fonts are tested against their own frozen map, never the shared registry.
g.run(B/'font/ReconquistaKR.otf',m['font']['family'],'recovery-full-gdi-sans.json',B/'font-map.json')
g.run(B/'font/ReconquistaKRSerif.otf',m['serif_font']['family'],'recovery-full-gdi-serif.json',B/'font-map.json')
for key in ['font','serif_font']:m[key]['runtime_gdi_verified']=True
# Verify actual compiled source/target fields for the changed recovery and all exact blank exceptions.
rec=load(ROOT/'translation/recovery-20261023/recovered-targets.json');byid={r['id']:r for r in d['records']+d['inline_records']};cache={};verified=[]
for rid in dict.fromkeys([r['id'] for r in rec['records']+rec['inline_records']]+[r['id'] for r in d['root_review']['exact_whitespace_exceptions']]):
 r=byid[rid];name,idx=rid.split('::')
 if name not in cache:cache[name]=b.decode(payloads[name])[0]
 ins=cache[name].instructions[int(idx)];assert ins.opcode.mnemonic==('ldstr' if rid in {x['id'] for x in rec['inline_records']} else 'text')
 assert ''.join(inv.get(c,c) for c in ins.string)==r['target'],rid
 verified.append(rid)
# Measure only the new recovered fields and new name display mapping; whole-route rendering remains pending.
class SIZE(C.Structure):_fields_=[('cx',W.LONG),('cy',W.LONG)]
g.G.GetTextExtentPoint32A.argtypes=[W.HDC,C.c_char_p,C.c_int,C.POINTER(SIZE)];g.G.GetTextExtentPoint32A.restype=W.BOOL
fp=B/'font/ReconquistaKR.otf';assert g.G.AddFontResourceExW(str(fp),0x10,None)>0
widths={};names=load(F/'names.json')['mapping'];samples={r['id']:r['target'] for r in rec['records']};samples.update({'speaker:'+k:v for k,v in names.items()})
try:
 for scale in [1,4]:
  dc=g.G.CreateCompatibleDC(None);font=g.G.CreateFontW(23*scale,11*scale+scale//2,0,0,400,0,0,0,1,0,0,3,0,m['font']['family']);prev=g.G.SelectObject(dc,font);glyphs={}
  try:
   for rid,t in samples.items():
    n=0
    for c in t:
     if c not in glyphs:
      raw=mp.get(c,c).encode('cp932');sz=SIZE();assert g.G.GetTextExtentPoint32A(dc,raw,len(raw),C.byref(sz));glyphs[c]=math.ceil(sz.cx/scale)
     n+=glyphs[c]
    widths.setdefault(rid,{})[str(scale)]=n
  finally:g.G.SelectObject(dc,prev);g.G.DeleteObject(font);g.G.DeleteDC(dc)
finally:g.G.RemoveFontResourceExW(str(fp),0x10,None)
fieldmax=max(max(v.values()) for k,v in widths.items() if not k.startswith('speaker:'));namemax=max(max(v.values()) for k,v in widths.items() if k.startswith('speaker:'));assert fieldmax+25<=692
verification={'translator_model':'Codex internal','snapshot_sha256':m['snapshot_sha256'],'scenario_sha256':m['outputs']['scenario.arc'],'compiled_recovery_and_exception_fields':verified,'font_map_sha256':m['font_map_sha256'],'glyphs':len(mp),'font_reports':['reports/recovery-full-gdi-sans.json','reports/recovery-full-gdi-serif.json'],'new_recovery_fields':45,'max_recovered_field_advance_px':fieldmax,'normal_console_width_px':692,'max_name_advance_px':namemax,'measured_widths':widths,'static_pass':True,'native_game_visual_verified':False,'native_game_blocker':'Computer Use kernel initialization failed twice with failed to write kernel assets: path not found (os error3), including one reset. No alternative UI automation attempted.','scope':'Compiled replacement exactness and offscreen GDI glyph/field advance only; not complete unit layout, manual ruby placement, or game screenshot. Existing81 width checks reused, not rerun.'}
dump(F/'verification.json',verification)
out=ROOT/('runtime-'+LABEL);assert not out.exists();out.mkdir()
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
