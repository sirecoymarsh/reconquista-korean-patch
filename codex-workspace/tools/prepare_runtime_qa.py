"""Separate, non-release native-engine display QA profiles. No narrative approval implied."""
from pathlib import Path
import sys,os,json,shutil,struct
from build_trial import decode,rewrite,string_ins,op,ROOT
from inspect_majiro import Arc,sha,dump
base=ROOT/'builds/integrated-reviewed-001';a=Arc(base/'scenario.arc');payloads={}
with a.path.open('rb') as f:
 for e in a.entries:f.seek(e['offset']);payloads[e['name']]=f.read(e['size'])
s,_=decode(payloads['start.mjo']);assert s.instructions[1642].string=='00_レコンキスタ_start';assert s.instructions[1643].hash==0x718ef651
for route in ['kureha_06','last_kako01','maho_14']:
 out=ROOT/'runtime-qa'/route;out.mkdir(parents=True,exist_ok=False)
 pp=payloads.copy();pp['start.mjo'],startreport=rewrite(pp['start.mjo'],{1642:string_ins('ldstr',route)})
 report={'profile':route,'release_build':'integrated-reviewed-001','purpose':'Native-engine font, wrapping, and display consumer QA only; route state/audio/playthrough are not verified','start_redirect':startreport}
 if route=='last_kako01':
  original=pp[route+'.mjo'];s,_=decode(original);assert s.instructions[27].opcode.mnemonic=='text' and s.instructions[321].opcode.mnemonic=='text'
  delta=s.instructions[321].offset-s.instructions[27].offset
  pp[route+'.mjo'],report['qa_jump']=rewrite(original,insertions={27:op('br')+struct.pack('<i',delta)})
  ns,_=decode(pp[route+'.mjo']);j=ns.instructions[27];assert j.opcode.mnemonic=='br';dest=j.offset+j.size+j.jump_offset
  actual=next(x for x in ns.instructions if x.offset==dest);assert actual.string==s.instructions[321].string
  report['qa_unit']='last_kako01.mjo::u0019';report['skipped_audio_and_intermediate_scenes']=True
 (out/'scenario.arc').write_bytes(a.rebuild(pp));shutil.copy2(base/'fastdata.arc',out/'fastdata.arc');shutil.copytree(base/'font',out/'font')
 for n in ['data.arc','data1.arc','data2.arc','slowdata.arc','stream.arc','voice.arc']:os.link(ROOT/'research/disc'/n,out/n)
 shutil.copy2(ROOT/'research/disc/bin/レコンキスタ.exe',out/'レコンキスタ.exe')
 for source in (ROOT/'research/disc/movie').rglob('*'):
  if source.is_file():
   target=out/'movie'/source.relative_to(ROOT/'research/disc/movie');target.parent.mkdir(parents=True,exist_ok=True);os.link(source,target)
 report['scenario_sha256']=sha((out/'scenario.arc').read_bytes());dump(out/'QA-ONLY.json',report)
 print(str(out))
