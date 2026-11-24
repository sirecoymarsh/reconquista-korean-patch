"""Apply only the second review's 36 new fields to the verified v1 archive."""
from pathlib import Path
import json,shutil,os,collections,datetime,math,ctypes as C,ctypes.wintypes as W
import build_trial as b
import check_recovery_gdi as g
from inspect_majiro import Arc,sha,dump
ROOT=b.ROOT;BASE='recovery-full-20261023-v1';LABEL='recovery-full-20261023-v2'
F=ROOT/'translation/integration'/LABEL;B=ROOT/'builds'/('integrated-'+LABEL)
PF=ROOT/'translation/integration'/BASE;PB=ROOT/'builds'/('integrated-'+BASE)
R=ROOT/'translation/recovery-20261023-review2'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def h(p):return sha(p.read_bytes())
assert not F.exists() and not B.exists()
d=load(PF/'integrated-targets.json');m=load(PB/'manifest.json');v=load(PF/'verification.json');rec=load(R/'recovered-targets.json');review=load(R/'review.json')
assert h(PF/'integrated-targets.json')==m['snapshot_sha256']==v['snapshot_sha256']
assert h(PB/'scenario.arc')==m['outputs']['scenario.arc']==v['scenario_sha256']
mp=load(PB/'font-map.json')['mapping'];inv={v:k for k,v in mp.items()}
def encode(t):
 s=''.join(mp.get(c,c) for c in t);assert s.encode('cp932').decode('cp932')==s;assert ''.join(inv.get(c,c) for c in s)==t;return s
for r in rec['records']:encode(r['target'])
existing={r['id'] for r in d['records']+d['inline_records']};assert not existing&{r['id'] for r in rec['records']}
packets=[load(p) for p in (ROOT/'body-parallel/source').glob('*.json')];pu={u['unit']:u for p in packets for u in p['units']}
for uid in rec['units']:
 expected={x['id'] for x in pu[uid]['fields'] if x['role']=='text'}
 assert expected=={x['id'] for x in rec['records'] if x['unit']==uid},uid
for n,s in rec['source_files'].items():assert h(ROOT/'research/extracted/scenario'/n)==s==d['source_files'][n]
for r in rec['records']:d['records'].append({**r,'origin':str((R/'recovered-targets.json').relative_to(ROOT)),'origin_sha256':h(R/'recovered-targets.json')})
d['records'].sort(key=lambda x:x['id']);d['units']=len({r['unit'] for r in d['records']});d['text_fields']=len(d['records']);assert (d['units'],d['text_fields'],d['inline_fields'])==(46935,73350,625)
for uid in rec['units']:
 n,k=uid.split('::u');assert int(k) not in d['coverage'][n];d['coverage'][n]=sorted([*d['coverage'][n],int(k)])
pending=[x['unit'] for x in review['decisions'] if x['decision']=='retain_original'];assert len(pending)==16
assert not set(pending)&{r['unit'] for r in d['records']}
d['pending_at_snapshot']={'body_units':16,'original_content_holds':16,'held_unit_ids':pending,'semantic_pending':[],'ui_owned_units_separate':70,'full_route_runtime':True}
d.update(label=LABEL,runtime_verified=False,stage='second source/context recovery integrated')
d['root_review']['recovery_review2']={'path':str(R/'review.json'),'sha256':h(R/'review.json'),'restored_general':21,'semantic_resolved':1,'independent_review':['review_opening_early','review_opening_late','review_cumulative_integration'],'referent_correction':'masa_10 u0178: woman refers to adult Yoshimori; 여자아이 corrected to 여자'}
F.mkdir();B.mkdir();(F/'provenance').mkdir()
for p in [R/'review.json',R/'recovered-targets.json']:shutil.copy2(p,F/'provenance'/p.name)
for n in ['names.json']:shutil.copy2(PF/n,F/n)
for n in ['targets.json','integrated-targets.json']:dump(F/n,d)
shutil.copy2(PB/'font-map.json',F/'fontmap-seed.json');shutil.copy2(PB/'font-map.json',B/'font-map.json');shutil.copytree(PB/'font',B/'font');shutil.copy2(PB/'fastdata.arc',B/'fastdata.arc')
a=Arc(PB/'scenario.arc');payloads={}
with a.path.open('rb') as f:
 for e in a.entries:f.seek(e['offset']);payloads[e['name']]=f.read(e['size'])
base_hashes={n:sha(raw) for n,raw in payloads.items()};groups=collections.defaultdict(list)
for r in rec['records']:groups[r['id'].split('::')[0]].append(r)
delta={};verified=[]
for name,rows in groups.items():
 source,_=b.decode(payloads[name]);original,_=b.decode((ROOT/'research/extracted/scenario'/name).read_bytes());assert len(source.instructions)==len(original.instructions)
 replace={}
 for r in rows:
  i=int(r['id'].split('::')[1]);assert source.instructions[i].opcode.mnemonic==original.instructions[i].opcode.mnemonic=='text';assert source.instructions[i].string==original.instructions[i].string==r['source'];replace[i]=b.string_ins('text',encode(r['target']))
 payloads[name],delta[name]=b.rewrite(payloads[name],replace)
 result,_=b.decode(payloads[name])
 for r in rows:
  i=int(r['id'].split('::')[1]);assert result.instructions[i].opcode.mnemonic=='text';assert ''.join(inv.get(c,c) for c in result.instructions[i].string)==r['target'];verified.append(r['id'])
 m['script_validation'][name]['output_sha256']=sha(payloads[name]);m['script_validation'][name]['replacement_indices']=sorted(set(m['script_validation'][name]['replacement_indices'])|set(replace));m['script_validation'][name]['review2_delta']=delta[name]
assert sorted(n for n,p in payloads.items() if sha(p)!=base_hashes[n])==sorted(groups)
(B/'scenario.arc').write_bytes(a.rebuild(payloads));rebuilt=Arc(B/'scenario.arc')
with rebuilt.path.open('rb') as f:
 for e in rebuilt.entries:f.seek(e['offset']);assert f.read(e['size'])==payloads[e['name']]
# Exact unchanged fonts reuse prior GDI proof; no full-font retest.
for key,n,rpt in [('font','ReconquistaKR.otf','recovery-full-gdi-sans.json'),('serif_font','ReconquistaKRSerif.otf','recovery-full-gdi-serif.json')]:
 evidence=load(ROOT/'reports'/rpt);assert evidence['pass'] and evidence['font_sha256']==h(B/'font'/n)==m[key]['output_sha256']
assert h(B/'font-map.json')==m['font_map_sha256'];assert h(B/'fastdata.arc')==m['outputs']['fastdata.arc']
# New fields only: offscreen engine-equivalent GDI advances, not game screenshots.
class SIZE(C.Structure):_fields_=[('cx',W.LONG),('cy',W.LONG)]
g.G.GetTextExtentPoint32A.argtypes=[W.HDC,C.c_char_p,C.c_int,C.POINTER(SIZE)];g.G.GetTextExtentPoint32A.restype=W.BOOL
fontpath=B/'font/ReconquistaKR.otf';assert g.G.AddFontResourceExW(str(fontpath),0x10,None)>0
widths={}
try:
 for scale in [1,4]:
  dc=g.G.CreateCompatibleDC(None);font=g.G.CreateFontW(23*scale,11*scale+scale//2,0,0,400,0,0,0,1,0,0,3,0,m['font']['family']);old=g.G.SelectObject(dc,font);glyphs={}
  try:
   for r in rec['records']:
    width=0
    for c in r['target']:
     if c not in glyphs:
      raw=mp.get(c,c).encode('cp932');sz=SIZE();assert g.G.GetTextExtentPoint32A(dc,raw,len(raw),C.byref(sz));glyphs[c]=math.ceil(sz.cx/scale)
     width+=glyphs[c]
    widths.setdefault(r['id'],{})[str(scale)]=width
  finally:g.G.SelectObject(dc,old);g.G.DeleteObject(font);g.G.DeleteDC(dc)
finally:g.G.RemoveFontResourceExW(str(fontpath),0x10,None)
maxwidth=max(max(w.values()) for w in widths.values());assert maxwidth+25<=692
m.update(snapshot=LABEL,snapshot_sha256=h(F/'integrated-targets.json'),translated_units=d['units'],translated_text_fields=d['text_fields'],coverage=d['coverage'],body_pending=d['pending_at_snapshot'],root_review=d['root_review'])
m['outputs']['scenario.arc']=h(B/'scenario.arc');m['review2_delta']={'baseline_manifest':str(PB/'manifest.json'),'baseline_manifest_sha256':h(PB/'manifest.json'),'changed_scripts':sorted(groups),'new_units':22,'new_fields':36,'control_flow_checks':delta,'unchanged_assets':'Byte-identical other archive entries, fastdata, fonts and font map; verified prior proofs reused.'}
verify={'translator_model':'Codex internal','snapshot_sha256':m['snapshot_sha256'],'scenario_sha256':m['outputs']['scenario.arc'],'compiled_new_fields':verified,'static_pass':True,'new_field_widths':widths,'max_new_field_px':maxwidth,'normal_console_width_px':692,'font_map_sha256':m['font_map_sha256'],'reused_verification':{'path':str(PF/'verification.json'),'sha256':h(PF/'verification.json'),'font_reports':v['font_reports'],'scope':'Unchanged font files, encoding map, preexisting names/manual-ruby and81 width results; no new screenshot claim.'},'native_game_visual_verified':False,'native_game_blocker':'Computer Use node_repl cannot initialize: failed to write kernel assets, os error3. Repair in progress.'}
dump(F/'verification.json',verify)
out=ROOT/('runtime-'+LABEL);assert not out.exists();out.mkdir()
for n in ['scenario.arc','fastdata.arc']:shutil.copy2(B/n,out/n);assert h(out/n)==m['outputs'][n]
shutil.copytree(B/'font',out/'font')
for n in ['data.arc','data1.arc','data2.arc','slowdata.arc','stream.arc','voice.arc']:os.link(ROOT/'research/disc'/n,out/n)
shutil.copy2(ROOT/'research/disc/bin/レコンキスタ.exe',out/'レコンキスタ.exe');assert h(out/'レコンキスタ.exe')==m['original_exe_sha256']
for p in (ROOT/'research/disc/movie').rglob('*'):
 if p.is_file():q=out/'movie'/p.relative_to(ROOT/'research/disc/movie');q.parent.mkdir(parents=True,exist_ok=True);os.link(p,q)
m['status']='integrated_installed_static_gdi_pass_visual_pending';m['runtime_path']=str(out);m['verification_report']=str(F/'verification.json');m['runtime']['visual_blocker']=verify['native_game_blocker'];m['runtime']['actual_game_screen']=False
for p in [B/'manifest.json',out/'BUILD-IDENTITY.json']:dump(p,m)
dump(ROOT/'reports/latest-recovery-build.json',{'path':str(B),**m})
report={'status':m['status'],'label':LABEL,'translator_model':'Codex internal','created_at':datetime.datetime.now().astimezone().isoformat(),'units':d['units'],'ordinary_fields':d['text_fields'],'inline_fields':625,'new_recovery_units':22,'content_recovered':21,'semantic_resolved':1,'names':117,'pending':d['pending_at_snapshot'],'reused_baseline_sha256':h(PF/'integrated-targets.json'),'snapshot_sha256':m['snapshot_sha256'],'runtime':str(out),'verification':str(F/'verification.json')};dump(F/'integration-report.json',report)
latest={'snapshot':LABEL,'snapshot_path':str(F/'integrated-targets.json'),'snapshot_sha256':m['snapshot_sha256'],'build':str(B),'normal_runtime':str(out),'status':m['status'],'units':46935,'text_fields':73350,'inline_fields':625,'verification':str(F/'verification.json'),'body_units_remaining':16};dump(ROOT/'translation/integration/latest.json',latest)
progress=load(ROOT/'progress.json');progress['recovery_review2_20261023']={**latest,'reviewed':37,'restored_general':21,'semantic_resolved':['st_gin.mjo::u0068'],'held_unit_ids':pending,'per_id_report':str(R/'구간별-재검토.md'),'next':'Repair Computer Use kernel initialization, then actual normal-game and selected new-unit screen QA.'};progress['updated_at']=datetime.datetime.now().astimezone().isoformat();progress['usage_checkpoint']={'used_percent':13,'remaining_percent':87,'limit_id':'codex','stop_marker_present':False};progress['next']=progress['recovery_review2_20261023']['next'];dump(ROOT/'progress.json',progress)
launch=ROOT/'Start-Korean-Recovery.ps1';s=launch.read_text(encoding='utf-8-sig');assert BASE in s;shutil.copy2(launch,ROOT/'Start-Korean-Recovery.v1.ps1');launch.write_text(s.replace(BASE,LABEL),encoding='utf-8-sig')
text='''# 레콘키스타 본문 재검토 통합 v2\n\n본문 46,935구간, 일반 필드 73,350개, 인라인625개를 적용했습니다.\n이번37구간 재검토로 일반 대사·서술21구간을 복구하고 의미 미확정1구간을 해결했습니다. 보류16구간은 원문을 유지했습니다.\n\n- 일반 실행: 프로젝트 루트 Start-Korean-Recovery.ps1\n- 실행 사본: runtime-recovery-full-20261023-v2\n- 각37구간 근거: translation/recovery-20261023-review2/구간별-재검토.md\n- 새36필드 컴파일 결과, 제어 흐름, 재포장 일치 검사를 통과했습니다.\n- 새 필드의 GDI 폭 검사를 통과했습니다. 동일한 글꼴1398자의 기존 검사 결과를 재사용했습니다.\n- 실제 게임 화면 검증은 화면 제어 도구 초기화 오류로 아직 미완료입니다. 이 상태를 글자 깨짐·잘림 없음으로 해석하면 안 됩니다.\n- UI·오프닝·엔딩은 별도 세션 범위이며 전체 루트와 세이브 호환성 검증은 미완료입니다.\n'''
for p in [out/'한국어화-상태.md',F/'완료보고.md']:p.write_text(text,encoding='utf-8')
print(json.dumps({'label':LABEL,'units':46935,'new_units':22,'new_fields':36,'remaining':16,'changed_scripts':sorted(groups),'max_new_field_px':maxwidth,'runtime':str(out)},ensure_ascii=False))
