"""Verify only the changed appended callback; reuse unchanged font/name evidence."""
import sys,json,struct
from pathlib import Path
import build_trial as b
from inspect_majiro import Arc,sha,dump
O=b.ROOT/'candidates/large-text-v1';p=O/'payloads/scenario.arc';a=Arc(p);data=p.read_bytes();e=next(x for x in a.entries if x['name']=='console.mjo');s,raw=b.decode(data[e['offset']:e['offset']+e['size']]);f=s.functions[-1];new=[x for x in s.instructions if x.offset>=f.offset];bounds={x.offset for x in s.instructions}|{len(raw)}
for x in s.instructions:
 if x.opcode.encoding=='j':assert x.offset+x.size+x.jump_offset in bounds
used=[]
for e in a.entries:
 if not e['name'].endswith('.mjo'):continue
 d=data[e['offset']:e['offset']+e['size']];n=struct.unpack_from('<I',d,24)[0]
 for j in range(n):
  h,o=struct.unpack_from('<II',d,28+j*8)
  if h==f.name_hash:used.append([e['name'],o])
assert len(used)==1
paths=[]
for history in [0,1]:
 for force in [0,1]:
  by={x.offset:x for x in new};pc=f.offset;stack=[];calls=[];stores=[];events=[]
  while True:
   x=by[pc];pc+=x.size;op=x.opcode.mnemonic
   if op in ['argcheck','alloca']:pass
   elif op=='call':assert x.hash==0x3561da56;stack.append(history)
   elif op=='ld':assert x.hash==0x47c73c5d;stack.append(force)
   elif op=='brfalse':
    if not stack.pop():pc+=x.jump_offset
   elif op=='br':pc+=x.jump_offset
   elif op=='callp':calls.append(x.hash)
   elif op=='ldc.i':stack.append(x.int_value)
   elif op=='ldstr':stack.append(x.string)
   elif op=='syscallp':assert x.hash==0x76ee6c90;events.append(stack.pop())
   elif op=='st.i':stores.append([x.hash,stack[-1]])
   elif op=='pop':stack.pop()
   elif op=='ret':assert stack==[0];break
   else:raise AssertionError(op)
  if history:assert events==['CONSOLE_CLS'] and not calls and not stores
  else:assert not events and calls==[0x1fd318c6 if force else 0x0a4e49ab,0xa324ac31,181607865] and stores==[[0x5e297ec7,0]]
  paths.append({'history':history,'force_play':force,'calls':[hex(c) for c in calls],'events':events,'stores':stores})
old=json.loads((O/'callback-verification.json').read_text('utf-8'));report={k:v for k,v in old.items() if k not in ['source_sha256','callback_paths','scope']}
report.update(source_sha256=sha(data),callback_paths=paths,scope='Static bytecode interpreter of final appended wrapper, not engine VM execution; unchanged GDI name measurement reused',name_measurement_reused=True)
dump(O/'callback-verification.json',report);print(json.dumps(report,ensure_ascii=False))
