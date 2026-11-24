# v20(runtime-final-20261028) scenario.arc 의 text 명령을 원본 명령 번호 id 로 꺼내 json 으로 저장 (argon_vs_final.py 와 같은 방식)
from pathlib import Path
import json,sys
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
R=Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024');C=Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타')
sys.path.insert(0,str(C/'tools'));sys.path.insert(0,str(R/'tools'))
import build_trial as b
from inspect_majiro import Arc
load=lambda p:json.loads(p.read_text('utf-8-sig'))
def payload(p):
 a=Arc(p);raw=p.read_bytes();return {e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries}
mp=load(C/'builds/body-ui-20261025-v20-nuance/font-map.json')['mapping'];inv={v:k for k,v in mp.items()};decode=lambda s:''.join(inv.get(x,x) for x in s)
orig=payload(C/'research/disc/scenario.arc');now=payload(R/'runtime-final-20261028/scenario.arc')
cur={};orig_text={};ops={};skipped=[]
for name,raw in orig.items():
 if not name.endswith('.mjo'):continue
 os_,_=b.decode(raw)
 for i,x in enumerate(os_.instructions):
  ops[f'{name}::{i:06d}']=x.opcode.mnemonic
 try: ns,_=b.decode(now[name])
 except Exception as e: skipped.append(name);continue
 ot=[i for i,x in enumerate(os_.instructions) if x.opcode.mnemonic=='text'];nt=[x for x in ns.instructions if x.opcode.mnemonic=='text']
 if len(ot)!=len(nt): skipped.append(name+':count');continue
 for oi,nx in zip(ot,nt): cur[f'{name}::{oi:06d}']=decode(nx.string)
out=Path(sys.argv[1])
out.write_text(json.dumps({'v20':cur,'ops':ops,'skipped':skipped},ensure_ascii=False),encoding='utf-8')
print(len(cur),len(ops),skipped)
