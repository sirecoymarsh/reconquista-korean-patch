"""Bounded control-flow/stack audit and deterministic syscall model for new ED worker only.
This is not execution in the native Majiro engine and does not establish runtime synchronization.
"""
from pathlib import Path
import sys,json,collections
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));import build_trial as b
from inspect_majiro import dump,sha
C=R/'builds'/(sys.argv[1] if len(sys.argv)>1 else 'ed-lyrics-overlay-v2');m=json.loads((C/'manifest.json').read_text(encoding='utf-8'));data=(C/'payloads/staffroll.mjo').read_bytes();assert sha(data)==m['script']['output_sha256'];s,raw=b.decode(data);lookup={x.offset:x for x in s.instructions};funcs={f.name_hash:f.offset for f in s.functions};worker=funcs[int(m['script']['new_functions']['worker'],16)];stop=funcs[int(m['script']['new_functions']['stop'],16)];tid=int(m['script']['thread_global'],16);rows=json.loads((C/'evidence/layout.json').read_text(encoding='utf-8'))
# CFG audit independent of builder's branches. Both conditional edges must agree on stack depth.
def stackcheck(start,end):
 states={start:0};pending=[start];returns=0
 while pending:
  pc=pending.pop();depth=states[pc];x=lookup[pc];op=x.opcode.mnemonic;out=depth;nexts=[pc+x.size]
  if op in ['ld','ldstr','ldc.i']:out+=1
  elif op in ['sub.i','cne.i','cge.i','ceq.s']:out-=1;assert depth>=2
  elif op=='pop':out-=1
  elif op in ['syscall','syscallp']:out-=x.argument_count;out+=int(op=='syscall')
  elif op=='st.i':assert depth>=1
  elif op in ['argcheck','alloca','bsel.clr']:pass
  elif op=='bsel.5':nexts.append(pc+x.size+x.jump_offset)
  elif op in ['brtrue','brfalse']:out-=1;nexts.append(pc+x.size+x.jump_offset)
  elif op=='br':nexts=[pc+x.size+x.jump_offset]
  elif op=='ret':assert depth==1,(pc,depth);returns+=1;nexts=[]
  else:raise AssertionError(op)
  assert out>=0,(pc,op,depth)
  for dst in nexts:
   assert start<=dst<end,(pc,dst)
   if dst in states:assert states[dst]==out,(pc,dst,out,states[dst])
   else:states[dst]=out;pending.append(dst)
 return {'reachable_instructions':len(states),'return_paths':returns,'stack_depth_merge_pass':True,'scope':'both branch outcomes; destructor edge registered at empty stack'}
workerstack=stackcheck(worker,stop);stopstack=stackcheck(stop,s.bytecode_size)
# Execute the compiled worker with a modeled 60Hz scheduler, real decoded offsets and stack operands.
def simulate(name,initial_elapsed=0,cancel_at=None,reset_at=None,failed_images=False):
 pc=worker;stack=[];local={-2:100000};glob={0x451d3082:100000,tid:77};now=100000+initial_elapsed;destructor=None;active={};shown=[];released=[];created=0;steps=0;cancelled=False;reset=False
 while True:
  steps+=1;assert steps<1000000
  if cancel_at is not None and now-100000>=cancel_at and not cancelled and destructor is not None:
   assert destructor is not None;pc=destructor;cancelled=True
  if reset_at is not None and now-100000>=reset_at and not reset:glob[0x451d3082]=0;reset=True
  x=lookup[pc];pc+=x.size;op=x.opcode.mnemonic
  if op=='ldc.i':stack.append(x.int_value)
  elif op=='ldstr':stack.append(x.string)
  elif op in ['argcheck','alloca']:pass
  elif op in ['ld','st.i']:
   scope=int(x.flags.scope);table=local if scope==3 else glob;key=x.var_offset if scope==3 else x.hash
   if op=='ld':stack.append(table.get(key,0))
   else:table[key]=stack[-1]
  elif op=='pop':stack.pop()
  elif op in ['sub.i','cne.i','cge.i']:
   right=stack.pop();left=stack.pop();stack.append(left-right if op=='sub.i' else int(left!=right) if op=='cne.i' else int(left>=right))
  elif op=='bsel.5':destructor=pc+x.jump_offset
  elif op=='bsel.clr':destructor=None
  elif op=='br':pc+=x.jump_offset
  elif op in ['brtrue','brfalse']:
   v=bool(stack.pop())
   if v==(op=='brtrue'):pc+=x.jump_offset
  elif op in ['syscall','syscallp']:
   args=[stack.pop() for _ in range(x.argument_count)];ret=None
   if x.hash==0x6584f13e:ret=now
   elif x.hash==0xcf35f0e3:assert args==[-2];now+=17
   elif x.hash==0xc2c3c4f4:
    created+=1;ret=0 if failed_images else created
    if ret:active[ret]=args[0];shown.append({'asset':args[0],'elapsed':now-100000})
   elif x.hash==0x58b31737:
    assert args[0] in active,('release invalid sprite',args);released.append(active.pop(args[0]))
   elif x.hash in [0xe119d5ba,0xff7c52e6,0x4a02d664]:assert args[0] in active,(hex(x.hash),args)
   else:raise AssertionError(hex(x.hash))
   if op=='syscall':assert ret is not None;stack.append(ret)
  elif op=='ret':assert stack==[0];assert not active and glob[tid]==0 and destructor is None;break
  else:raise AssertionError(op)
 assert len(released)==len(shown)
 for row in shown:
  src=next(r for r in rows if r['asset']==row['asset']);assert src['start_ms']<=row['elapsed']<src['end_ms']
 if initial_elapsed==0 and cancel_at is None and reset_at is None and not failed_images:assert [r['asset'] for r in shown]==[r['asset'] for r in rows]
 return {'name':name,'shown':len(shown),'released':len(released),'final_elapsed':now-100000,'steps':steps,'no_expired_lines_shown':True,'no_live_sprites_or_thread_handle_after_return':True,'cancelled':cancelled,'song_timer_reset':reset}
cases=[simulate('natural'),simulate('late worker scheduling',initial_elapsed=61000),simulate('failed asset loads',failed_images=True)]
for at in [0,4998,5000,15000,60000,211000,220000]:cases.append(simulate('thread-end at '+str(at),cancel_at=at))
for at in [5000,61000,219000]:cases.append(simulate('song timer invalidation at '+str(at),reset_at=at))
report={'script_sha256':sha(data),'worker_stack':workerstack,'stop_stack':stopstack,'modeled_cases':cases,'native_game_executed':False,'limits':'Control-flow and deterministic syscall model only. The native engine, actual sprite opacity/priority, font appearance and song sync remain user verification.'};dump(C/'evidence/control-flow-review.json',report);print(json.dumps(report,ensure_ascii=False))