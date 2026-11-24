"""Resolve reviewed ED worker stop/restart race; copy verified raster artifacts unchanged."""
from pathlib import Path
import sys,struct,json,zlib,os
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));import build_trial as b
from inspect_majiro import dump,sha
A=R/'builds/ed-lyrics-overlay-v1';C=R/'builds/ed-lyrics-overlay-v2';assert not C.exists();C.mkdir()
for p in A.rglob('*'):
 rel=p.relative_to(A);q=C/rel
 if p.is_dir():q.mkdir(exist_ok=True)
 elif str(rel).replace('\\','/') not in ['manifest.json','payloads/staffroll.mjo','evidence/staffroll-patched.mjil','evidence/control-flow-review.json']:os.link(p,q)
m=json.loads((A/'manifest.json').read_text(encoding='utf-8'));old=(A/'payloads/staffroll.mjo').read_bytes();s,raw=b.decode(old);STOP=int(m['script']['new_functions']['stop'],16);TID=int(m['script']['thread_global'],16);off=next(f.offset for f in s.functions if f.name_hash==STOP);OLD=zlib.crc32(b'_kr_ed_stop_old_thread@')
code=bytearray();labels={};fix=[]
def add(v):code.extend(v)
def op(n):add(b.op(n))
def i(v):op('ldc.i');add(struct.pack('<I',v&0xffffffff))
def v(n,h,index=-1,flags=0x20):op(n);add(struct.pack('<HIh',flags,h,index))
def syscall(h,n,ret=False):op('syscall' if ret else 'syscallp');add(struct.pack('<IH',h,n))
def j(n,label):op(n);fix.append((len(code),label));add(bytes(4))
def lab(n):labels[n]=len(code)
op('argcheck');add(struct.pack('<H',0));op('alloca');add(struct.pack('<HB',1,0))
v('ld',TID);v('st.i',OLD,0,0x60);op('pop');v('ld',OLD,0,0x60);j('brfalse','done')
v('ld',OLD,0,0x60);syscall(0x9fb53fbe,1,True);j('brfalse','clear')
v('ld',OLD,0,0x60);syscall(0x4ef903f3,1)
lab('wait');v('ld',OLD,0,0x60);syscall(0x9fb53fbe,1,True);j('brfalse','clear');i(-2);syscall(0xcf35f0e3,1);j('br','wait')
lab('clear');i(0);v('st.i',TID);op('pop');lab('done');i(0);op('ret')
for at,label in fix:struct.pack_into('<i',code,at,labels[label]-(at+4))
newraw=raw[:off]+code;head=bytearray(old[:s.bytecode_offset]);struct.pack_into('<I',head,len(head)-4,len(newraw));new=bytes(head)+(b.crypt32(newraw) if s.signature==s.SIGNATURE_ENCRYPTED else newraw)
ss,rr=b.decode(new);assert rr==newraw and rr[:off]==raw[:off];assert [(f.name_hash,f.offset) for f in ss.functions]==[(f.name_hash,f.offset) for f in s.functions]
bounds={x.offset for x in ss.instructions}|{len(rr)}
for x in ss.instructions:
 if x.opcode.encoding=='j':assert x.offset+x.size+x.jump_offset in bounds
(C/'payloads/staffroll.mjo').write_bytes(new);(C/'evidence/staffroll-patched.mjil').write_text('\n'.join(x.format_instruction() for x in ss.instructions)+'\n',encoding='utf-8')
m['script']['output_sha256']=sha(new);m['script']['lifecycle_revision']={'parent_script_sha256':sha(old),'change':'Stop helper snapshots old thread ID into local; checks existence; requests thread_end; yields until exact old ID no longer exists. Caller cannot start replacement until confirmed. No fixed frame-count assumption.','only_stop_helper_changed':True,'other_code_bytes_identical':True};m['engine_evidence']=[x for x in m['engine_evidence'] if not x.startswith('yazlib.mjo 0x641c')]+['menu.mjo 0x1320 uses thread_is_exist on thread handle before thread_end','yazlib.mjo 0x641c yields twelve frames after thread_end; fixed two-frame assumption rejected']
m['raster_verification_reused_from']=str(A);m['independent_technical_review']=False;dump(C/'manifest.json',m);print(json.dumps({'candidate':str(C),'script_sha256':sha(new),'raster_assets_unchanged':64},ensure_ascii=False))