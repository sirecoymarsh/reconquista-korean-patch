"""4K readability delta: body fonts and overflow-only page wait; no prose changes."""
from pathlib import Path
import sys,json,struct,zlib,re,collections
import build_trial as b
from inspect_majiro import Arc,sha,dump
import pefile
R=b.ROOT; B=R/'builds/body-ui-20261023-v8'; O=R/'candidates/large-text-v1'
OLD='Reconquista KR d00b8d76'; NEWS='Reconquista KR Large1'
OLDS='Reconquista KR Serif d00b8d76'; NEWSS='Reconquista KR Large Serif1'
EVENT='KR_LARGE_PAGE'; EH=zlib.crc32(EVENT.encode()); FH=zlib.crc32(b'$kr_large_page@CONSOLE')
i=lambda v:b.op('ldc.i')+struct.pack('<I',v&0xffffffff)
sy=lambda h,n:b.op('syscallp')+struct.pack('<IH',h,n)
call=lambda h:b.op('callp')+struct.pack('<IIH',h,0,0)
empty=lambda n:b.op(n)+struct.pack('<H',0)
def arc(p):
 a=Arc(p);d=p.read_bytes();return a,{e['name']:d[e['offset']:e['offset']+e['size']] for e in a.entries}
def packcode(blob,code):
 count=struct.unpack_from('<I',blob,24)[0];off=32+count*8
 return blob[:off]+b.crypt32(code) if blob[:16]==b'MajiroObjX1.000\0\0' else blob[:off]+code
m=json.loads((B/'manifest.json').read_text('utf-8'));assert sha((B/'manifest.json').read_bytes())=='b33a3bfe42bdffce79f0b23c09677f6e0770b8ab6f7dac16099b0cabddc392bd'
sa,src=arc(B/'scenario.arc');fa,fsrc=arc(B/'fastdata.arc');payload=src.copy();fp=fsrc.copy();reports={}
# Temporarily ASCII-mask only already-approved native ACP949 diagnostics for the CP932 decoder.
def mask_native(blob,name):
 rows=m.get('native_diagnostic_validation',{}).get(name,{}).get('records',[])
 count=struct.unpack_from('<I',blob,24)[0];off=32+count*8;code=b.crypt32(blob[off:]) if blob[:10]==b'MajiroObjX' else blob[off:]
 pairs=[]
 for no,hexstr in enumerate(dict.fromkeys(r['payload_hex'] for r in rows)):
  value=bytes.fromhex(hexstr);marker=(f'KR{no:02d}_'.encode()+b'Z'*len(value))[:len(value)]
  assert len(marker)==len(value) and marker not in code and code.count(value)>=1
  code=code.replace(value,marker);pairs.append((marker,value))
 return blob[:off]+(b.crypt32(code) if blob[:10]==b'MajiroObjX' else code),pairs
def restore_native(blob,pairs):
 s,code=b.decode(blob)
 for marker,value in pairs:
  assert code.count(marker)>=1;code=code.replace(marker,value)
 return blob[:s.bytecode_offset]+(b.crypt32(code) if s.signature==s.SIGNATURE_ENCRYPTED else code)
# Body consumers only. UI title/history/config label drawing keeps the v8 font.
for name in ['load_sysdata.mjo','config.mjo','00_レコンキスタ_start.mjo','00_レコンキスタ_start_3.mjo','テスト用.mjo']:
 safe,pairs=mask_native(src[name],name);s,raw=b.decode(safe);repl={};insert={}
 for idx,x in enumerate(s.instructions):
  if x.opcode.mnemonic=='ldstr' and x.string in [OLD,OLDS]:
   assert (name in ['load_sysdata.mjo','config.mjo'] and x.string==OLD) or (name not in ['load_sysdata.mjo','config.mjo'] and x.string==OLDS)
   repl[idx]=b.string_ins('ldstr',NEWS if x.string==OLD else NEWSS)
 assert len(repl)=={'load_sysdata.mjo':1,'config.mjo':2,'00_レコンキスタ_start.mjo':8,'00_レコンキスタ_start_3.mjo':8,'テスト用.mjo':3}[name]
 if name=='load_sysdata.mjo':
  idx=next(j for j,x in enumerate(s.instructions) if x.opcode.mnemonic=='ldstr' and x.string=='font\\ReconquistaKR.otf')
  insert[idx]=b''.join(b.string_ins('ldstr','font\\'+n)+sy(0x877445ce,1) for n in ['ReconquistaKRLarge.otf','ReconquistaKRSerifLarge.otf'])
 new,proof=b.rewrite(safe,repl,insert);payload[name]=restore_native(new,pairs);reports[name]=proof|{'native_diagnostic_byte_strings_preserved':len(pairs)}
# Append a private callback; only native vertical-overflow dispatch points to it.
name='console.mjo';s,raw=b.decode(src[name]);assert FH not in [f.name_hash for f in s.functions]
idx=next(j for j,x in enumerate(s.instructions) if x.offset==s.main_offset)+3
hook=i(FH)+b.string_ins('ldstr',EVENT)+sy(0x078a756e,2)
base,proof=b.rewrite(src[name],insertions={idx:hook});ss,code=b.decode(base)
forcewait=call(0x1fd318c6); normalwait=call(0x0a4e49ab)
waitcode=b.op('ld')+struct.pack('<HIh',0x20,0x47c73c5d,-1)+b.op('brfalse')+struct.pack('<i',len(forcewait)+6)+forcewait+b.op('br')+struct.pack('<i',len(normalwait))+normalwait
history_return=b.string_ins('ldstr','CONSOLE_CLS')+sy(0x76ee6c90,1)+i(0)+b.op('ret')
history_guard=b.op('call')+struct.pack('<IIH',0x3561da56,0,0)+b.op('brfalse')+struct.pack('<i',len(history_return))+history_return
wrapper=empty('argcheck')+empty('alloca')+history_guard+waitcode+i(0)+b.op('st.i')+struct.pack('<HIh',0x20,0x5e297ec7,-1)+b.op('pop')+call(0xa324ac31)+call(181607865)+i(0)+b.op('ret')
funcs=[(f.name_hash,f.offset) for f in ss.functions]+[(FH,len(code))];newcode=code+wrapper
header=base[:24]+struct.pack('<I',len(funcs))+b''.join(struct.pack('<II',h,o) for h,o in funcs)+struct.pack('<I',len(newcode))
payload[name]=header+(b.crypt32(newcode) if ss.signature==ss.SIGNATURE_ENCRYPTED else newcode)
ns,nr=b.decode(payload[name]);assert nr[:len(code)]==code and nr[len(code):]==wrapper
assert [(f.name_hash,f.offset) for f in ns.functions]==funcs
reports[name]=proof|{'appended_function_hash':hex(FH),'event':EVENT,'event_hash':hex(EH),'order':['force_play ? pause_inter force-only early-return : pause_nodisp','reset_fullpage_restore_flag','cb_console_cls'],'force_play_guard':True,'history_bypasses_new_wait':True,'gaizi_clear_preserved':True,'no_new_save_point_or_autosave':True,'name_hide_callback_omitted_for_continuation':True,'existing_function_bytecode_preserved_after_relocation':True}
# Fullscreen at startup. Built-in F4/Alt+Enter controls remain available in the game.
name='start.mjo';s,raw=b.decode(src[name]);idx=next(j for j,x in enumerate(s.instructions) if x.offset==s.main_offset)+3
assert idx==1522
payload[name],reports[name]=b.rewrite(src[name],insertions={idx:i(1)+sy(0x62374297,1)})
# Texts and original control-code sequences must be identical, including already-retained units.
for name in reports:
 old,p0=mask_native(src[name],name);new,p1=mask_native(payload[name],name)
 a,_=b.decode(old);c,_=b.decode(new)
 for op in ['text','ctrl']:
  assert [x.string for x in a.instructions if x.opcode.mnemonic==op]==[x.string for x in c.instructions if x.opcode.mnemonic==op],(name,op)
# The two sysdata font slots are body and speaker name; all numeric geometry is preserved.
assert fp['sysdata.cfg'].count(OLD.encode())==2
fp['sysdata.cfg']=fp['sysdata.cfg'].replace(OLD.encode(),NEWS.encode())
pat=rb'(?m)^(FC_NAME[ \t]+)([^\r\n]*)';mt=re.search(pat,fp['majiro.env']);assert mt[2].decode().replace('|',' ')==OLD
fp['majiro.env']=fp['majiro.env'][:mt.start(2)]+NEWS.replace(' ','|').encode()+fp['majiro.env'][mt.end(2):]
# Precisely one native immediate changes; no control-flow, imports, entrypoint, or resources move.
exe=bytearray((B/'レコンキスタ.exe').read_bytes());assert sha(exe)==m['exe_sha256'];pe=pefile.PE(data=exe);at=pe.get_offset_from_rva(0x4165d3-pe.OPTIONAL_HEADER.ImageBase)
assert exe[at:at+5]==b'\x68'+struct.pack('<I',0x93b38a0b)
assert exe[at+5:at+10]==b'\xe8'+struct.pack('<i',0x409460-(0x4165d8+5))
exe[at+1:at+5]=struct.pack('<I',EH)
(O/'payloads').mkdir(exist_ok=True);(O/'payloads/レコンキスタ.exe').write_bytes(exe)
areports=[]
for n,a,data,original in [('scenario.arc',sa,payload,src),('fastdata.arc',fa,fp,fsrc)]:
 result=a.rebuild(data);(O/'payloads'/n).write_bytes(result);aa,back=arc(O/'payloads'/n)
 assert back==data and [x['name'] for x in aa.entries]==[x['name'] for x in a.entries]
 changed=[k for k in data if data[k]!=original[k]]
 assert set(changed)==(set(reports) if n=='scenario.arc' else {'sysdata.cfg','majiro.env'})
 areports.append({'name':n,'sha256':sha(result),'changed':changed,'unchanged_entries_byte_identical':True,'reparse_exact':True})
for name,proof in reports.items():
 proof['relocation_stage_source_sha256']=proof['source_sha256'];proof['relocation_stage_output_sha256']=proof['output_sha256']
 proof['source_sha256']=sha(src[name]);proof['output_sha256']=sha(payload[name])
fonts=json.loads((O/'font-candidate.json').read_text('utf-8'))
for r in fonts['fonts']:assert sha((O/'font'/r['font']).read_bytes())==r['output_sha256']
report={'parent_build':B.name,'parent_manifest_sha256':sha((B/'manifest.json').read_bytes()),'translator_model':'Codex internal','semantic_text_unchanged':True,'original_control_codes_unchanged':True,'font_map_unchanged':True,'fonts':fonts['fonts'],'archives':areports,'script_changes':reports,'native_patch':{'file_offset':at+1,'length':4,'old':struct.pack('<I',0x93b38a0b).hex(),'new':struct.pack('<I',EH).hex(),'source_sha256':m['exe_sha256'],'output_sha256':sha(exe),'scope':'Only native vertical-overflow event immediate, 0x4165d4','code_and_resources_otherwise_identical':True},'fullscreen_startup':True,'logical_canvas':[800,600],'runtime_verified':False,'runtime_verification_owner':'user','performance_fix_claimed':False,'remaining_checks':['GDI all-glyph map equality and cell containment','independent callback review','launcher prepare-only']}
dump(O/'manifest.json',report)
print(json.dumps({'candidate':str(O),'changed_scripts':list(reports),'exe_sha256':sha(exe),'event':hex(EH),'function':hex(FH)},ensure_ascii=False))




