"""Prepare a user-run, native-console replay of the final v2 additions and geometry samples."""
from pathlib import Path
import json,os,struct,shutil,collections
import build_trial as b
from inspect_majiro import Arc,sha,dump
ROOT=b.ROOT;LABEL='recovery-full-20261023-v2';F=ROOT/'translation/integration'/LABEL;B=ROOT/'builds'/('integrated-'+LABEL)
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def h(p):return sha(p.read_bytes())
m=load(B/'manifest.json');d=load(F/'integrated-targets.json');assert h(F/'integrated-targets.json')==m['snapshot_sha256']
rec=load(ROOT/'translation/recovery-20261023-review2/recovered-targets.json')
selection=['kureha_06.mjo::u0005',*rec['units'],'kureha_06.mjo::u0206','sub_kure02.mjo::u0046'];assert len(selection)==len(set(selection))==25
units={u['unit']:u for p in (ROOT/'body-parallel/source').glob('*.json') for u in load(p)['units'] if u['unit'] in selection}
targets={r['id']:r['target'] for r in d['records']+d['inline_records']};arc=Arc(B/'scenario.arc');assert h(arc.path)==m['outputs']['scenario.arc'];payloads={}
with arc.path.open('rb') as f:
 for e in arc.entries:f.seek(e['offset']);payloads[e['name']]=f.read(e['size'])
mode_script,mode_raw=b.decode(payloads['sub_kure02.mjo']);mode_ins=next(x for x in mode_script.instructions if x.opcode.mnemonic=='callp' and x.hash==0x35395c9f);mode_call=mode_raw[mode_ins.offset:mode_ins.offset+mode_ins.size]
init,sraw=b.decode(payloads['kureha_06.mjo']);assert len(init.functions)==1 and init.main_offset==0 and init.bytecode_offset==40
code=bytearray(sraw[:init.instructions[8].offset]+sraw[init.instructions[11].offset:init.instructions[13].offset]);plan=[];cache={}
for num,uid in enumerate(selection,1):
 name=uid.split('::')[0]
 if name not in cache:cache[name]=b.decode(payloads[name])
 s,raw=cache[name];orig,_=b.decode((ROOT/'research/extracted/scenario'/name).read_bytes());assert len(s.instructions)==len(orig.instructions)
 u=units[uid];lo=min(x['index'] for x in u['fields']);last=max(x['index'] for x in u['fields']);hi=next(i+1 for i in range(last,len(s.instructions)) if s.instructions[i].opcode.mnemonic=='ctrl' and s.instructions[i].string=='w')
 assert not any(x.is_syscall and x.hash==0x06b3c8ac for x in orig.instructions[:lo]),uid
 modes=[i for i,x in enumerate(orig.instructions[:lo]) if x.opcode.mnemonic=='callp' and x.hash==0x35395c9f]
 if modes:assert orig.instructions[modes[-1]-1].opcode.mnemonic=='ldc.i'
 mode=orig.instructions[modes[-1]-1].int_value if modes else 0;assert mode in [0,2,4]
 code.extend(b.op('ldc.i')+struct.pack('<i',mode)+mode_call);block=bytearray();omitted=[];i=lo
 while i<hi:
  x=s.instructions[i];mn=x.opcode.mnemonic
  if mn=='ldstr':
   nextins=s.instructions[i+1];assert nextins.opcode.mnemonic in ['callp','syscallp'] and nextins.hash in [0x90d5298a,0x812afdf0]
   omitted.append({'index':i,'reason':'audio-only call, no display change'});i+=2;continue
  assert mn in ['text','proc','ctrl','line'],(uid,i,mn)
  if mn=='ctrl':assert x.string in ['p','n','w'],(uid,i,x.string)
  block.extend(raw[x.offset:x.offset+x.size]);i+=1
 plan.append({'number':num,'unit':uid,'console_mode':mode,'source_instruction_range':[lo,hi-1],'built_script_sha256':sha(payloads[name]),'console_block_sha256':sha(bytes(block)),'qa_code_offset':len(code),'fields':[{'id':f['id'],'role':f['role'],'target':targets.get(f['id'],f['source'])} for f in u['fields']],'controls':[x.string for x in s.instructions[lo:hi] if x.opcode.mnemonic=='ctrl'],'omitted_voice':omitted,'visual_status':'user_pending'})
 code.extend(block)
code.extend(b.op('ldc.i')+struct.pack('<i',0)+mode_call);choice,craw=b.decode(payloads['shinya_kyoutu.mjo']);assert choice.instructions[6411].hash==0x0238c9e1;code.extend(craw[choice.instructions[6409].offset:choice.instructions[6412].offset]);code.extend(b.op('pop'));code.extend(sraw[init.instructions[-2].offset:])
header=bytearray(payloads['kureha_06.mjo'][:40]);struct.pack_into('<I',header,36,len(code));fixture=bytes(header)+b.crypt32(bytes(code));parsed,decoded=b.decode(fixture);assert decoded==bytes(code) and parsed.instructions[-1].opcode.mnemonic=='ret'
pp=payloads.copy();pp['kureha_06.mjo']=fixture;start,_=b.decode(pp['start.mjo']);assert start.instructions[1642].string=='00_レコンキスタ_start' and start.instructions[1643].hash==0x718ef651
pp['start.mjo'],start_report=b.rewrite(pp['start.mjo'],{1642:b.string_ins('ldstr','kureha_06')})
out=ROOT/'runtime-qa'/('final-v2-review25-'+m['outputs']['scenario.arc'][:8]);assert not out.exists();out.mkdir(parents=True)
(out/'scenario.arc').write_bytes(arc.rebuild(pp));shutil.copy2(B/'fastdata.arc',out/'fastdata.arc');shutil.copytree(B/'font',out/'font')
# Validate only the new QA archive and its copied display blocks, not previous release checks.
afterarc=Arc(out/'scenario.arc')
with afterarc.path.open('rb') as f:
 for e in afterarc.entries:f.seek(e['offset']);assert f.read(e['size'])==pp[e['name']]
for u in plan:
 n=u['qa_code_offset'];rawlen=0
 name=u['unit'].split('::')[0];s,raw=cache[name]
 for i in range(u['source_instruction_range'][0],u['source_instruction_range'][1]+1):
  x=s.instructions[i]
  if x.opcode.mnemonic in ['text','proc','ctrl','line']:rawlen+=x.size
 assert sha(decoded[n:n+rawlen])==u['console_block_sha256']
for n in ['data.arc','data1.arc','data2.arc','slowdata.arc','stream.arc','voice.arc']:os.link(ROOT/'research/disc'/n,out/n)
shutil.copy2(ROOT/'research/disc/bin/レコンキスタ.exe',out/'レコンキスタ.exe')
for p in (ROOT/'research/disc/movie').rglob('*'):
 if p.is_file():q=out/'movie'/p.relative_to(ROOT/'research/disc/movie');q.parent.mkdir(parents=True,exist_ok=True);os.link(p,q)
proof={'profile':'User-run native-console replay, QA ONLY','release_build':str(B),'release_scenario_sha256':m['outputs']['scenario.arc'],'release_snapshot_sha256':m['snapshot_sha256'],'qa_scenario_sha256':h(out/'scenario.arc'),'original_exe_sha256':m['original_exe_sha256'],'start_redirect':start_report,'units':25,'newly_accepted_units':22,'console_modes':[0,2,4],'tail_choices':[{'id':'shinya_kyoutu.mjo::006409','target':targets['shinya_kyoutu.mjo::006409']},{'id':'shinya_kyoutu.mjo::006410','target':targets['shinya_kyoutu.mjo::006410']}],'static_validation':'PASS: exact compiled display blocks and controls, source mode restored; archive payload equality','native_visual_verified':False,'limitations':['Diagnostic black background; audio and story state not replayed.','Do not use QA saves for normal gameplay.','Manual ruby positions and full route graphics still require normal-game review.']};dump(out/'QA-ONLY.json',proof);dump(out/'review-plan.json',plan)
identity={'original_exe_sha256':m['original_exe_sha256'],'font':m['font'],'serif_font':m['serif_font'],'outputs':{'scenario.arc':h(out/'scenario.arc'),'fastdata.arc':h(out/'fastdata.arc')},'qa_only':True};dump(out/'BUILD-IDENTITY.json',identity)
s=(ROOT/'Start-Korean-Recovery.ps1').read_text(encoding='utf-8-sig');s=s.replace('runtime-recovery-full-20261023-v2',str(out.relative_to(ROOT)));s=s.replace('builds\\integrated-recovery-full-20261023-v2\\manifest.json',str((out/'BUILD-IDENTITY.json').relative_to(ROOT)));(ROOT/'Start-Korean-Review.ps1').write_text(s,encoding='utf-8-sig')
lines=['# 최종 본문 표시 확인용 사본','', '이 사본은 최신 v2의 번역과 실제 게임 대사창을 사용해 확인 대상을 연속 표시합니다. 정상 플레이용 사본과 분리되어 있습니다.','', '1. 실행 중인 레콘퀴스타를 저장하고 종료합니다.','2. 프로젝트 루트의 Start-Korean-Review.ps1을 실행하고 START를 누릅니다.','3. 글자가 모두 표시된 뒤 클릭이나 Enter로 다음 대사를 확인합니다. 내부 페이지 나눔 때문에 한 구간에 여러 번 입력할 수 있습니다.','4. 끝의 선택지까지 확인하면 종료합니다. 여기 만든 세이브는 정상 플레이에 사용하지 않습니다.','', '확인 항목: 네모·엉뚱한 한자·빈 글자, 대사창 바깥으로 나감, 마지막 줄·화자 이름 잘림, 페이지 전환 후 잔상.','검은 배경과 음성 생략은 검사용 설정입니다. 본편의 배경 합성·전체 루트·수동 루비 검증을 대신하지 않습니다.','', '| 순서 | 구간 | 표시 모드 | 확인 상태 |','|---|---|---|---|']
for u in plan:lines.append(f"| {u['number']} | {u['unit']} | {u['console_mode']} | 사용자 확인 전 |")
lines+=['','마지막에 한국어 선택지 2개가 표시됩니다. 정상 플레이는 Start-Korean-Recovery.ps1을 사용합니다.']
(out/'검증안내.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');dump(F/'manual-visual-profile.json',{'path':str(out),'launcher':str(ROOT/'Start-Korean-Review.ps1'),'proof_sha256':h(out/'QA-ONLY.json'),'status':'prepared_static_pass_user_visual_pending'})
print(json.dumps({'path':str(out),'units':25,'modes':[0,2,4],'launcher':str(ROOT/'Start-Korean-Review.ps1'),'actual_game_visual_verified':False},ensure_ascii=False))
