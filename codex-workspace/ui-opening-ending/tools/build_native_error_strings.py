"""Hash-bound native display-only error strings; no code/resource/behavior edits."""
from pathlib import Path
import json,hashlib,re,datetime,pefile
U=Path(__file__).resolve().parents[1];base=U/'candidates/native-ui-v5';outdir=U/'candidates/native-ui-v6';assert not outdir.exists();sha=lambda b:hashlib.sha256(b).hexdigest()
raw=(base/'レコンキスタ.exe').read_bytes();assert sha(raw)=='f67195682944663b9546665eb3b63a639ace3f910e2ebf6ffaccda001d625b50';pe=pefile.PE(data=raw);out=bytearray(raw)
f=U/'translation/native-errors-ko.json';tr=json.loads(f.read_text(encoding='utf-8'));excluded=next(r for r in tr['records'] if r['va']==0x47cb44);excluded={k:v for k,v in excluded.items() if k not in ['target','target_byte_length','encoding','required_windows_acp','protected_printf_tokens']};excluded.update(status='protected_control',consumer_status='sprintf to buffer 0x512fb0; EnumWindows callback reads window captions via GetWindowTextA and compares against this buffer before SendMessageA(0x9005). Preserve exact source bytes.');tr['protected_records']=[excluded];tr['records']=[r for r in tr['records'] if r['va']!=0x47cb44];assert len(tr['records'])==11
for r in tr['records']:
 src=r['source'].encode('cp932');tgt=r['target'].encode('cp949');off=pe.get_offset_from_rva(r['va']-pe.OPTIONAL_HEADER.ImageBase);assert off==r['file_offset'];assert raw[off:off+len(src)+1]==src+b'\0';assert len(tgt)<=len(src)
 tokens=lambda s:re.findall(r'%(?:\d+\$)?[-+#0 ]*\d*(?:\.\d+)?[a-zA-Z%]',s)
 assert tokens(r['source'])==tokens(r['target']);assert r['source'].count('\n')==r['target'].count('\n');out[off:off+len(src)]=tgt+b'\0'*(len(src)-len(tgt));assert bytes(out[off:off+len(src)]).split(b'\0')[0].decode('cp949')==r['target']
 r.update(status='included_static_pass',consumer_status='Verified native MessageBoxA or printf-to-MessageBoxA; CP949 on ACP949 host',source_bytes=src.hex(),target_bytes=tgt.hex(),source_null_preserved=True,format_tokens_preserved=True,line_breaks_preserved=True,rva=r['va']-pe.OPTIONAL_HEADER.ImageBase)
changed=[i for i,(a,b) in enumerate(zip(raw,out)) if a!=b];allowed={i for r in tr['records'] for i in range(r['file_offset'],r['file_offset']+r['byte_length'])};assert set(changed)<=allowed and len(raw)==len(out);po=pefile.PE(data=out)
def imports(p):return [(d.dll.decode(),[(i.name.decode() if i.name else None,i.ordinal,i.address) for i in d.imports]) for d in p.DIRECTORY_ENTRY_IMPORT]
assert imports(pe)==imports(po)
for s,t in zip(pe.sections,po.sections):
 assert s.Name==t.Name and s.VirtualAddress==t.VirtualAddress and s.PointerToRawData==t.PointerToRawData and s.SizeOfRawData==t.SizeOfRawData
 if s.Name.rstrip(b'\0')!=b'.data':assert s.get_data()==t.get_data(),s.Name
assert bytes(out[excluded['file_offset']:excluded['file_offset']+excluded['byte_length']+1])==excluded['source'].encode('cp932')+b'\0'
outdir.mkdir();(outdir/'レコンキスタ.exe').write_bytes(out);assert sha((outdir/'レコンキスタ.exe').read_bytes())==sha(out)
m=json.loads((base/'manifest.json').read_text(encoding='utf-8'));m.update(candidate_sha256=sha(out),inherits='native-ui-v5',native_error_display_patches=tr['records'],native_error_display_count=11,protected_native_control_ids=[excluded['id']],new_changed_bytes=len(changed),new_changes_only_display_string_slots=True,new_code_and_resources_unchanged=True,new_imports_unchanged=True,consumer_evidence='../../evidence/native-error-consumers-rea.json',runtime_error_paths='Not triggered: general error wrapper also overwrites the clipboard; no runtime pass claimed',release_scan='pending');m['data_change_allowlist'] += [[r['rva'],r['byte_length']] for r in tr['records']]
for sec in m['sections']:
 data=next(s.get_data() for s in po.sections if s.Name.rstrip(b'\0').decode()==sec['name']);sec['candidate_sha256']=sha(data);sec['bytes_identical']=sec['original_sha256']==sec['candidate_sha256']
assert all(s['bytes_identical'] for s in m['sections'] if s['name'] not in ['.data','.rsrc'])
tr.update(semantic_authored_and_included=11,protected_control_records=1,candidate_sha256=sha(out),review={'method':'Primary Codex context/consumer review; source meaning, line breaks, placeholders, byte capacity and native encoding checked','source_typo':'0x47ca7c repeated 以上終了 interpreted as abnormal termination from its preceding sentence and cache-recovery branch','caption_register':'0x47cb24 이상 종료 감지 is the compact native diagnostic heading'},updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());f.write_text(json.dumps(tr,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(outdir/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'candidate':str(outdir),'sha256':sha(out),'new_fields':11,'changed_bytes':len(changed),'code_resources_imports_unchanged_from_v5':True,'protected_control_unchanged':excluded['id']},ensure_ascii=False))
