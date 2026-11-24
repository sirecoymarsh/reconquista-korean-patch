from pathlib import Path
import sys,io,json,hashlib,collections
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research/vendor/majiro-py/src'))
from mjotool import MjoScript

def packet(name):
 s=MjoScript.disassemble_script(io.BytesIO((ROOT/'research/extracted/scenario'/name).read_bytes()))
 units=[]; fields=[]; voice=None; bg=None; last_literal=None
 for i,ins in enumerate(s.instructions):
  if ins.opcode.mnemonic=='ldstr': last_literal=ins.string
  if ins.hash==0x812afdf0 and ins.is_call: voice=last_literal
  if ins.hash==0xa4eb1e4c and ins.is_call: bg=last_literal
  if ins.opcode.mnemonic=='text':
   following=next((q for q in s.instructions[i+1:] if q.opcode.mnemonic!='line'),None)
   is_name=following is not None and following.opcode.mnemonic=='text'
   fields.append({'id':f'{name}::{i:06d}','index':i,'source':ins.string,'role':'speaker_token' if is_name else 'text'})
  if ins.opcode.mnemonic=='ctrl' and ins.string=='w' and fields:
   units.append({'unit':f'{name}::u{len(units)+1:04d}','fields':fields,'voice':voice,'background':bg,'speaker':next((f['source'] for f in fields if f['role']=='speaker_token'),None),'addressee':'unresolved','phase':'opening'});fields=[];voice=None
 if fields: units.append({'unit':f'{name}::u{len(units)+1:04d}','fields':fields,'voice':voice,'background':bg,'speaker':None,'addressee':'unresolved','phase':'opening'})
 return units
def main():
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--script',default='00_レコンキスタ_start.mjo');a.add_argument('--output',default='translation/opening-source.json');a.add_argument('--preview',type=int,default=0);args=a.parse_args()
 source=ROOT/'research/extracted/scenario'/args.script
 out=(ROOT/args.output).resolve();assert out.is_relative_to(ROOT.resolve())
 units=packet(args.script)
 for u in units:u['phase']=args.script
 data={'translator_model':'Codex internal','source_language':'ja','target_language':'ko','source_script':args.script,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'units':units}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 for i,u in enumerate(units[:args.preview],1):print(i,u['speaker'],[f['source'] for f in u['fields'] if f['role']=='text'])
 print(json.dumps({'path':str(out),'units':len(units),'text_fields':sum(f['role']=='text' for u in units for f in u['fields'])},ensure_ascii=False))
if __name__=='__main__':main()
