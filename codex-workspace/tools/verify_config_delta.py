"""Bind the config delta to source scripts and existing diagnostic byte payloads."""
from pathlib import Path
import sys,json,struct,hashlib,inspect,textwrap
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));import build_trial as b
from inspect_majiro import Arc
import mjotool.script as ms
ns=dict(vars(ms));exec(textwrap.dedent(inspect.getsource(ms.Instruction.read_instruction)).replace(".decode('cp932')", ".decode('cp932',errors='replace')"),ns);ms.Instruction.read_instruction=ns['read_instruction']
C=R/'candidates/config-completion-v1';B=R/'builds/body-ui-20261023-v12-input-logo';h=0xfe9ea26b
arc=Arc(B/'scenario.arc');blob=arc.path.read_bytes();scanned=0;collisions=[]
for e in arc.entries:
 if not e['name'].lower().endswith('.mjo'):continue
 raw=blob[e['offset']:e['offset']+e['size']];count=struct.unpack_from('<I',raw,24)[0];start=32+8*count
 code=b.crypt32(raw[start:]) if raw[:16]==b.MjoScript.SIGNATURE_ENCRYPTED else raw[start:]
 if struct.pack('<I',h) in code:collisions.append(e['name'])
 scanned+=1
assert not collisions
s,code=b.decode((C/'payloads/config.mjo').read_bytes());base=json.loads((B/'manifest.json').read_text('utf-8-sig'));diag=base['native_diagnostic_validation']['config.mjo'];updated=[]
for row in diag['records']:
 raw=bytes.fromhex(row['payload_hex']);hits=[(i,x) for i,x in enumerate(s.instructions) if x.opcode.encoding=='s' and code[x.offset+4:x.offset+x.size-1]==raw]
 assert len(hits)==1,(row['id'],len(hits));i,x=hits[0];updated.append({**row,'instruction_index_current':i,'bytecode_range':[x.offset+4,x.offset+x.size-1]})
result={'private_hash':f'{h:08x}','source_archive_sha256':hashlib.sha256(blob).hexdigest(),'source_scripts_scanned':scanned,'collisions':collisions,'native_diagnostic_records':updated,'native_cp949_payload_bytes_unchanged':True,'config_output_sha256':hashlib.sha256((C/'payloads/config.mjo').read_bytes()).hexdigest(),'pass':True}
(C/'source-binding.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8');print('source binding PASS',scanned,'scripts,',len(updated),'diagnostics')
