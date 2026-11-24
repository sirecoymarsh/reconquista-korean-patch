"""Build-bound, offscreen Windows GDI layout audit; never launches a game window."""
from pathlib import Path
import json,sys,os,math,ctypes as C,ctypes.wintypes as W,collections,shutil,html,datetime
import build_trial as b
import check_gdi_font as g
from inspect_majiro import Arc,sha,dump
ROOT=b.ROOT;LABEL='session1-04fc30b0-widthqa-v1';FOLDER=ROOT/'translation/integration'/LABEL;BASE=ROOT/'builds'/('integrated-'+LABEL)
manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
review=json.loads((FOLDER/'runtime-review.json').read_text(encoding='utf-8'))
plan=json.loads((Path(review['runtime_profile'])/'review-plan.json').read_text(encoding='utf-8'))
target=json.loads((FOLDER/'integrated-targets.json').read_text(encoding='utf-8'))
byid={r['id']:r for r in target['records']+target['inline_records']}
mp=json.loads((BASE/'font-map.json').read_text(encoding='utf-8'))['mapping'];inverse={v:k for k,v in mp.items()}
assert all(w['target']==byid[w['id']]['target'] for w in review['warnings'])
arc=Arc(BASE/'scenario.arc');payloads={}
with arc.path.open('rb') as f:
 for e in arc.entries:
  f.seek(e['offset']);payloads[e['name']]=f.read(e['size'])
class SIZE(C.Structure):_fields_=[('cx',W.LONG),('cy',W.LONG)]
g.G.GetTextExtentPoint32A.argtypes=[W.HDC,C.c_char_p,C.c_int,C.POINTER(SIZE)];g.G.GetTextExtentPoint32A.restype=W.BOOL
fp=BASE/'font/ReconquistaKR.otf';assert g.G.AddFontResourceExW(str(fp),0x10,None)>0
geometry={0:{'width':692,'height':94,'font_y':23,'font_x':11,'step':33},2:{'width':692,'height':528,'font_y':23,'font_x':11,'step':33},4:{'width':690,'height':88,'font_y':19,'font_x':9,'step':23}}
fonts={};glyphs={};decoded={};results=[];fieldmetrics={};exact=0
try:
 for mode in sorted({p['console_mode'] for p in plan}):
  cfg=geometry[mode]
  for scale in [1,4]:
   dc=g.G.CreateCompatibleDC(None);font=g.G.CreateFontW(cfg['font_y']*scale,cfg['font_x']*scale+(scale//2 if cfg['font_y']%2 else 0),0,0,400,0,0,0,1,0,0,3,0,manifest['font']['family']);assert font
   prev=g.G.SelectObject(dc,font);face=C.create_unicode_buffer(128);g.G.GetTextFaceW(dc,128,face);assert face.value==manifest['font']['family']
   fonts[(mode,scale)]=(dc,font,prev)
 def measure(text,mode,scale):
  value=0;dc=fonts[(mode,scale)][0]
  for c in text:
   encoded=mp.get(c,c).encode('cp932');key=(mode,scale,encoded)
   if key not in glyphs:
    sz=SIZE();assert g.G.GetTextExtentPoint32A(dc,encoded,len(encoded),C.byref(sz));glyphs[key]=math.ceil(sz.cx/scale)
   value+=glyphs[key]
  return value
 for p in plan:
  name=p['unit'].split('::')[0]
  if name not in decoded:decoded[name]=b.decode(payloads[name])[0]
  script=decoded[name];lo,hi=p['source_instruction_range'];roles={int(f['id'].split('::')[1]):f for f in p['fields']};mode=p['console_mode'];cfg=geometry[mode]
  events=[]
  for i in range(lo,hi+1):
   ins=script.instructions[i]
   if ins.opcode.mnemonic=='text':
    f=roles[i]
    if f['role']=='speaker_token':continue
    rid=f['id'];actual=''.join(inverse.get(c,c) for c in ins.string);assert actual==byid[rid]['target'],rid
    events.append(('text',rid,actual));exact+=1
   elif ins.opcode.mnemonic=='ctrl':events.append((ins.string,None,None))
  variants=[]
  for scale in [1,4]:
   x=0;y=0;row=1;maxx=0;maxbottom=0;rows=1;wraps=0
   for event,rid,text in events:
    if event=='text':
     extent=measure(text,mode,scale);fieldmetrics.setdefault(rid,{})[str(scale)]=extent
     # All audited rows are below the boundary. No kinsoku branch or auto-wrap is needed.
     if x+extent>cfg['width']:wraps+=1
     assert x+extent<=cfg['width'],(p['unit'],rid,x,extent,cfg)
     x+=extent;maxx=max(maxx,x);maxbottom=max(maxbottom,y+cfg['font_y']);rows=max(rows,row)
    elif event=='n':x=0;y+=cfg['step'];row+=1
    elif event=='w':x=0;y=0;row=1
   # Reserve an extra full-width character for quote indentation and3px for outline.
   safe_right=maxx+2*cfg['font_x']+3
   safe_bottom=maxbottom+(cfg['step']-cfg['font_y'])//2+2
   assert safe_right<=cfg['width'] and safe_bottom<=cfg['height'],(p['unit'],safe_right,safe_bottom,cfg)
   variants.append({'scale':scale,'rows':rows,'auto_wraps_needed':wraps,'max_row_advance_px':maxx,'right_with_indent_outline_margin_px':safe_right,'bottom_with_line_outline_margin_px':safe_bottom,'pass':True})
  results.append({'number':p['number'],'unit':p['unit'],'console_mode':mode,'source_mode_call_index':p['mode_source_index'],'geometry':cfg,'controls':p['controls'],'fields':p['fields'],'warning_ids':p['warning_ids'],'variants':variants,'compiled_text_exact':True,'status':'headless_pass_final_visual_by_user'})
 choices=[]
 s=b.decode(payloads['shinya_kyoutu.mjo'])[0]
 for idx in [6409,6410]:
  rid=f'shinya_kyoutu.mjo::{idx:06d}';assert s.instructions[idx].opcode.mnemonic=='ldstr'
  actual=''.join(inverse.get(c,c) for c in s.instructions[idx].string);assert actual==byid[rid]['target']
  choices.append({'id':rid,'target':actual,'compiled_exact':True,'shared_console_font_advance_px':{str(z):measure(actual,0,z) for z in [1,4]},'final_menu_visual_by_user':True})
 assert s.instructions[6411].hash==0x0238c9e1
finally:
 for dc,font,prev in fonts.values():g.G.SelectObject(dc,prev);g.G.DeleteObject(font);g.G.DeleteDC(dc)
 g.G.RemoveFontResourceExW(str(fp),0x10,None)
assert len(results)==80 and sum(len(x['warning_ids']) for x in results)==81
corpus=[{'id':w['id'],'target':w['target']} for w in review['warnings']]
proof={'translator_model':'Codex internal','recorded_at':datetime.datetime.now().astimezone().isoformat(timespec='seconds'),'status':'headless_pass_final_visual_by_user','snapshot':LABEL,'snapshot_sha256':manifest['snapshot_sha256'],'scenario_sha256':manifest['outputs']['scenario.arc'],'font_sha256':manifest['font']['sha256'] if 'sha256' in manifest['font'] else sha(fp.read_bytes()),'font_map_sha256':manifest['font_map_sha256'],'warning_corpus_sha256':sha(json.dumps(corpus,ensure_ascii=False,sort_keys=True).encode()),'warnings_checked':81,'units_checked':80,'compiled_body_fields_checked':exact,'width_or_height_overflows':0,'semantic_text_changes_for_width':0,'mode_counts':dict(collections.Counter(str(p['console_mode']) for p in plan)),'native_evidence':'reports/session1-width-native-evidence-20261023.json','native_text_function':'0x4161f0','native_font_setup_reused':'0x413890 / reports/native-evidence-20261022.json','controls_evidence':'0x414900: n advances line; p waits; w clears','earlier_individual_width_probe_reused':review['headless_width_measurement'],'font_gdi_reports_reused':['reports/font-gdi-body-sans.json','reports/font-gdi-body-serif.json'],'semantic_batches_reused':166,'scope':'Offscreen Windows GDI metrics plus compiled text/control-flow replay; no game window executed or visually accepted. No wrapping required for these80 units under source mode0/2/4.','limits':['Mode0 is the normal story-entry assumption when no preceding console_mode call exists. Explicit source mode2/4 is restored in manual replay.','Exact final raster compositing, actual choices interaction, route execution, save/load and visual typography remain the user final check.'],'units':results,'tail_choices':choices}
dump(FOLDER/'headless-width-81.json',proof)
for w in review['warnings']:
 w['status']='headless_pass_final_visual_by_user';w['measured_advance_px']=fieldmetrics[w['id']];w['resolution']='31-cell estimate was conservative; native GDI advances fit the source console. Target unchanged.'
review['status']='integrated_headless_pass_final_visual_by_user';review['runtime_verified']=False;review['headless_report']=str(FOLDER/'headless-width-81.json');review['headless_overflows']=0;review['final_visual_owner']='user';review['width_target_edits']=0
review['technical_adjustments'].append({'issue':'8 additional direct Mincho font setters in opening3','resolution':'Exact allowlisted console_font consumers use mapped Korean serif family','instruction_indices':[16776,16801,16898,16926,16973,17403,17415,17427]})
normal=ROOT/('runtime-integration-session1-'+manifest['outputs']['scenario.arc'][:8]);assert not normal.exists();normal.mkdir()
for n in ['scenario.arc','fastdata.arc']:shutil.copy2(BASE/n,normal/n);assert sha((normal/n).read_bytes())==manifest['outputs'][n]
shutil.copytree(BASE/'font',normal/'font')
for n in ['ReconquistaKR.otf','ReconquistaKRSerif.otf']:assert sha((normal/'font'/n).read_bytes())==sha((BASE/'font'/n).read_bytes())
shutil.copy2(ROOT/'research/disc/bin/レコンキスタ.exe',normal/'レコンキスタ.exe');assert sha((normal/'レコンキスタ.exe').read_bytes())==manifest['original_exe_sha256']
for n in ['data.arc','data1.arc','data2.arc','slowdata.arc','stream.arc','voice.arc']:os.link(ROOT/'research/disc'/n,normal/n)
for source in (ROOT/'research/disc/movie').rglob('*'):
 if source.is_file():
  dest=normal/'movie'/source.relative_to(ROOT/'research/disc/movie');dest.parent.mkdir(parents=True,exist_ok=True);os.link(source,dest)
manual=Path(review['runtime_profile']);review['normal_runtime']=str(normal);review['next_step']='User final in-game visual verification; no autonomous GUI run.'
manifest['status']='headless_pass_final_visual_by_user';manifest['headless']={k:proof[k] for k in ['warnings_checked','units_checked','compiled_body_fields_checked','width_or_height_overflows','semantic_text_changes_for_width','semantic_batches_reused']};manifest['headless']['report']=str(FOLDER/'headless-width-81.json');manifest['runtime']['final_visual_owner']='user'
dump(BASE/'manifest.json',manifest);dump(ROOT/'reports/latest-build.json',{'path':str(BASE),**manifest});dump(FOLDER/'runtime-review.json',review)
dump(ROOT/'translation/integration/latest.json',{'snapshot':LABEL,'snapshot_path':str(FOLDER/'integrated-targets.json'),'snapshot_sha256':manifest['snapshot_sha256'],'build':str(BASE),'normal_runtime':str(normal),'manual_warning_replay':str(manual),'status':review['status'],'units':19406,'text_fields':30723,'inline_fields':210,'tail_choices_included':2,'headless_report':str(FOLDER/'headless-width-81.json')})
rootprogress=json.loads((ROOT/'progress.json').read_text(encoding='utf-8'));rootprogress['session1_runtime_integration'].update({'status':review['status'],'normal_runtime':str(normal),'manual_warning_replay':str(manual),'headless_report':str(FOLDER/'headless-width-81.json'),'warnings_checked':81,'overflow':0,'final_visual_owner':'user'});dump(ROOT/'progress.json',rootprogress)
for dest in [normal,manual]:
 dump(dest/'BUILD-IDENTITY.json',{'snapshot':LABEL,'normal_runtime':str(normal),'manual_warning_replay':str(manual),'release_scenario_sha256':manifest['outputs']['scenario.arc'],'exe_sha256':manifest['original_exe_sha256'],'headless_report':str(FOLDER/'headless-width-81.json'),'final_visual_owner':'user'})
 shutil.copy2(FOLDER/'headless-width-81.json',dest/'HEADLESS-RESULTS.json')
rows=[]
for u in results:
 for rid in u['warning_ids']:
  r=byid[rid];widths=fieldmetrics[rid];rows.append('<tr><td>'+str(u['number'])+'</td><td>'+html.escape(rid)+'</td><td>'+html.escape(r['target'])+'</td><td>'+str(u['console_mode'])+'</td><td>'+str(widths['1'])+' / '+str(widths['4'])+'</td><td>헤드리스 통과 · 화면 확인 대기</td></tr>')
page='''<!doctype html><meta charset="utf-8"><title>레콘키스타 중앙 통합 검증</title><style>body{font:16px/1.6 system-ui;max-width:1500px;margin:32px auto;padding:0 24px;color:#172638;background:#f6f8fa}h1{font-size:28px}table{border-collapse:collapse;width:100%;background:white}td,th{padding:10px;border:1px solid #ccd5df;text-align:left}td:nth-child(2){font:12px monospace;word-break:break-all}td:nth-child(3){min-width:300px}input{padding:10px;width:70%;margin:15px 0}.note{background:#e8f0f8;padding:16px;border-radius:8px}</style><h1>중앙 통합본 · 최종 확인 자료</h1><p>19,406구간 / 일반 필드30,723개 / 인라인210개(별도 선택지2개 포함)</p><p class="note">폭 경고81건, 전체 대사80구간: 헤드리스 폭·높이 초과0건. 문장 축약0건. 기존166배치 검증 재사용. 실제 게임 화면의 최종 확인은 사용자 담당입니다.</p><p>측정은 엔진의1배·4배 GDI 글꼴 생성과 문자별 올림 폭 계산을 따릅니다. 표시 모드0=일반 대사창,2=전체 화면,4=작은 글꼴 창. 게임 캡처나 전체 루트 통과 결과는 아닙니다.</p><p>일반 실행 사본: <code>'''+html.escape(str(normal))+'''</code><br>경고 구간 재생 사본: <code>'''+html.escape(str(manual))+'''</code><br>각 폴더의 レコンキスタ.exe를 직접 실행하세요. 재생 사본에서 새 게임을 시작하면 아래80구간 이후 선택지2개가 나옵니다. 이 사본은 검증 전용입니다.</p><p>글꼴 수정: CP932 밖의 가운데점(·) 매핑, 추가 명조 글꼴 호출8곳의 한글 연결.</p><input placeholder="문장이나 안정 ID로 찾기" oninput="document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase()))"><table><thead><tr><th>구간</th><th>안정 ID</th><th>번역</th><th>모드</th><th>폭px(1배 / 4배)</th><th>상태</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table><p>별도 선택지: 마호코의 제안을 거절한다 / 마호코의 제안을 받아들인다</p>'''
(FOLDER/'CHECK-RESULTS.html').write_text(page,encoding='utf-8')
for dest in [normal,manual]:shutil.copy2(FOLDER/'CHECK-RESULTS.html',dest/'CHECK-RESULTS.html')
old=ROOT/'runtime-qa/session1-width81-3a72a9ff/QA-ONLY.json';oldreport=json.loads(old.read_text(encoding='utf-8'));oldreport['status']='superseded_before_runtime_launch';oldreport['replacement']=str(manual);oldreport['reason']='Replacement restores source console_mode0/2/4';dump(old,oldreport)
print(json.dumps({'normal_runtime':str(normal),'manual_qa':str(manual),'warnings':81,'units':80,'compiled_fields':exact,'overflows':0,'mode_counts':proof['mode_counts'],'max_warning_width_px':max(v for w in review['warnings'] for v in w['measured_advance_px'].values()),'report':str(FOLDER/'CHECK-RESULTS.html')},ensure_ascii=False))
