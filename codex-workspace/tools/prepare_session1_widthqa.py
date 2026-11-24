"""Replay complete width-warning units through the unchanged native game console."""
from pathlib import Path
import json,sys,os,struct,shutil,collections
import build_trial as b
from inspect_majiro import Arc,sha,dump
ROOT=b.ROOT
LABEL='session1-04fc30b0-widthqa-v1'
folder=ROOT/'translation/integration'/LABEL
review=json.loads((folder/'runtime-review.json').read_text(encoding='utf-8'))
base=ROOT/'builds'/('integrated-'+LABEL)
manifest=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
arc=Arc(base/'scenario.arc');payloads={}
with arc.path.open('rb') as f:
 for e in arc.entries:
  f.seek(e['offset']);payloads[e['name']]=f.read(e['size'])
byunit=collections.OrderedDict()
for w in review['warnings']:byunit.setdefault(w['unit'],[]).append(w['id'])
units={}
for p in (ROOT/'body-parallel/source').glob('script-*.json'):
 d=json.loads(p.read_text(encoding='utf-8'))
 units.update({u['unit']:u for u in d['units'] if u['unit'] in byunit})
target=json.loads((folder/'integrated-targets.json').read_text(encoding='utf-8'))
targets={r['id']:r['target'] for r in target['records']+target['inline_records']}
mode_script,mode_raw=b.decode(payloads['sub_kure02.mjo'])
mode_ins=next(x for x in mode_script.instructions if x.opcode.mnemonic=='callp' and x.hash==0x35395c9f)
mode_call=mode_raw[mode_ins.offset:mode_ins.offset+mode_ins.size]
init,sraw=b.decode(payloads['kureha_06.mjo']);assert len(init.functions)==1 and init.main_offset==0 and init.bytecode_offset==40
code=bytearray(sraw[:init.instructions[8].offset]+sraw[init.instructions[11].offset:init.instructions[13].offset])
plan=[];cache={}
for number,(uid,wids) in enumerate(byunit.items(),1):
 name=uid.split('::')[0]
 if name not in cache:cache[name]=b.decode(payloads[name])
 s,raw=cache[name];orig,_=b.decode((ROOT/'research/extracted/scenario'/name).read_bytes());assert len(s.instructions)==len(orig.instructions)
 u=units[uid];lo=min(x['index'] for x in u['fields']);last=max(x['index'] for x in u['fields'])
 hi=next(i+1 for i in range(last,len(s.instructions)) if s.instructions[i].opcode.mnemonic=='ctrl' and s.instructions[i].string=='w')
 assert not any(x.is_syscall and x.hash==0x06b3c8ac for x in orig.instructions[:lo]),uid
 modes=[i for i,x in enumerate(orig.instructions[:lo]) if x.opcode.mnemonic=='callp' and x.hash==0x35395c9f]
 if modes:assert orig.instructions[modes[-1]-1].opcode.mnemonic=='ldc.i'
 mode=orig.instructions[modes[-1]-1].int_value if modes else 0
 assert mode in [0,2,4],(uid,mode)
 code.extend(b.op('ldc.i')+struct.pack('<i',mode)+mode_call)
 block=bytearray();omitted=[];i=lo
 while i<hi:
  x=s.instructions[i];mn=x.opcode.mnemonic
  if mn=='ldstr':
   following=s.instructions[i+1]
   assert following.opcode.mnemonic in ['callp','syscallp'] and following.hash in [0x90d5298a,0x812afdf0]
   omitted.append({'index':i,'voice':x.string,'reason':'audio only; no display change'});i+=2;continue
  assert mn in ['text','proc','ctrl','line'],(uid,i,mn)
  if mn=='ctrl':assert x.string in ['p','n','w']
  block.extend(raw[x.offset:x.offset+x.size]);i+=1
 plan.append({'number':number,'console_mode':mode,'mode_source_index':modes[-1] if modes else None,'unit':uid,'warning_ids':wids,'source_instruction_range':[lo,hi-1],'built_script_sha256':sha(payloads[name]),'console_block_sha256':sha(bytes(block)),'qa_code_offset':len(code),'fields':[{'id':f['id'],'role':f['role'],'source':f['source'],'target':targets.get(f['id'],f['source'])} for f in u['fields']],'controls':[x.string for x in s.instructions[lo:hi] if x.opcode.mnemonic=='ctrl'],'omitted_voice':omitted,'status':'pending'})
 code.extend(block)
code.extend(b.op('ldc.i')+struct.pack('<i',0)+mode_call)
choice,craw=b.decode(payloads['shinya_kyoutu.mjo'])
assert choice.instructions[6411].hash==0x0238c9e1
code.extend(craw[choice.instructions[6409].offset:choice.instructions[6412].offset]);code.extend(b.op('pop'))
code.extend(sraw[init.instructions[-2].offset:])
header=bytearray(payloads['kureha_06.mjo'][:40]);struct.pack_into('<I',header,36,len(code))
fixture=bytes(header)+b.crypt32(bytes(code))
parsed,decoded=b.decode(fixture);assert decoded==bytes(code) and parsed.instructions[-1].opcode.mnemonic=='ret'
pp=payloads.copy();pp['kureha_06.mjo']=fixture
start,_=b.decode(pp['start.mjo']);assert start.instructions[1642].string=='00_レコンキスタ_start' and start.instructions[1643].hash==0x718ef651
pp['start.mjo'],start_report=b.rewrite(pp['start.mjo'],{1642:b.string_ins('ldstr','kureha_06')})
out=ROOT/'runtime-qa'/('session1-width81-'+manifest['outputs']['scenario.arc'][:8]+'-modes');out.mkdir(parents=True,exist_ok=False)
(out/'scenario.arc').write_bytes(arc.rebuild(pp));shutil.copy2(base/'fastdata.arc',out/'fastdata.arc');shutil.copytree(base/'font',out/'font')
for n in ['data.arc','data1.arc','data2.arc','slowdata.arc','stream.arc','voice.arc']:os.link(ROOT/'research/disc'/n,out/n)
shutil.copy2(ROOT/'research/disc/bin/レコンキスタ.exe',out/'レコンキスタ.exe')
for source in (ROOT/'research/disc/movie').rglob('*'):
 if source.is_file():
  dest=out/'movie'/source.relative_to(ROOT/'research/disc/movie');dest.parent.mkdir(parents=True,exist_ok=True);os.link(source,dest)
proof={'profile':'native whole-dialogue-unit width replay','release_build':str(base),'release_scenario_sha256':manifest['outputs']['scenario.arc'],'qa_scenario_sha256':sha((out/'scenario.arc').read_bytes()),'exe_sha256':sha((out/'レコンキスタ.exe').read_bytes()),'start_redirect':start_report,'units':len(plan),'warnings':len(review['warnings']),'font_context':'All80 source units have no preceding direct console_font override; explicitly restore each source console_mode0/2/4, which also restores the corresponding font and geometry; exact text and controls preserved','tail_choices':[{'id':'shinya_kyoutu.mjo::006409','target':targets['shinya_kyoutu.mjo::006409']},{'id':'shinya_kyoutu.mjo::006410','target':targets['shinya_kyoutu.mjo::006410']}],'limitations':['Diagnostic navigation and black background; exact compiled text and full native controls preserved.','Two audio pairs omitted. Full route states, audio, gameplay and branch traversal not asserted.','QA-only archive must not be distributed as a release.']}
dump(out/'QA-ONLY.json',proof);dump(out/'review-plan.json',plan)
(out/'evidence').mkdir()
review['runtime_profile']=str(out);review['build']=str(base);review['build_scenario_sha256']=manifest['outputs']['scenario.arc'];review['next_step']='User performs final visual check using normal runtime or manual80-unit replay; headless results reused.'
dump(folder/'runtime-review.json',review)
print(json.dumps({'runtime':str(out),'units':len(plan),'warnings':len(review['warnings']),'extra_p_units':[p['unit'] for p in plan if p['controls'].count('p')>1]},ensure_ascii=False))
