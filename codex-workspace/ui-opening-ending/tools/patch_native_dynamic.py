from pathlib import Path
import json,hashlib,shutil,sys,ctypes as C,re,pefile
u=Path('P:/AI/Codex/projects/reconquista-ko/ui-opening-ending').resolve();b=u.parent;sys.path.insert(0,str(b/'tools'));from inspect_majiro import Arc
sha=lambda b:hashlib.sha256(b).hexdigest();assert C.windll.kernel32.GetACP()==949,'Native ANSI candidate is bound to Korean Windows ACP 949'
v2=u/'candidates/native-ui-v2';v3=u/'candidates/native-ui-v3';v3.mkdir(exist_ok=True);src=(v2/'レコンキスタ.exe').read_bytes();assert sha(src)=='dbf8f588a4be752ce47b2a54d806970f21bf36b0fc29ffd351a6d025ff0cfc2c';p=pefile.PE(data=src);off=p.get_offset_from_rva(0x7cf94);old='標準'.encode('cp932');new='기본'.encode('cp949');assert src[off:off+6]==old+b'\0\0' and len(old)==len(new)==4;out=src[:off]+new+src[off+4:];assert [i for i,(a,z) in enumerate(zip(src,out)) if a!=z]==list(range(off,off+4));(v3/'レコンキスタ.exe').write_bytes(out)
m=json.loads((v2/'manifest.json').read_text(encoding='utf-8'));m['inherits_resource_verification']='../native-ui-v2/manifest.json';m['candidate_sha256']=sha(out);m['native_dynamic_patch']={'id':'native::0x47cf94::screen_default','source':'標準','target':'기본','display_encoding':'cp949','required_windows_acp':949,'source_bytes':old.hex(),'target_bytes':new.hex(),'file_offset':off,'source_va':'0x47cf94','consumer':'0x42689b push string; 0x4268a2 CB_INSERTSTRING; 0x4268ad call SendMessageA','exact_change_allowlist':[off,off+4],'code_changed':False};m['runtime_pass']=False;m['defender_scan_pending']=True
for s in m['sections']:
 sec=next(s2 for s2 in pefile.PE(data=out).sections if s2.Name.rstrip(b'\0').decode()==s['name']);s['candidate_sha256']=sha(sec.get_data());s['bytes_identical']=s['original_sha256']==s['candidate_sha256']
(v3/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
base=u/'candidates/ui-trial-v2';trial=u/'candidates/ui-trial-v3';trial.mkdir(exist_ok=True);shutil.copy2(base/'scenario.arc',trial/'scenario.arc');shutil.copytree(base/'font',trial/'font',dirs_exist_ok=True);shutil.copytree(base/'payloads',trial/'payloads',dirs_exist_ok=True)
a=Arc(base/'fastdata.arc');raw=(base/'fastdata.arc').read_bytes();payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries};env=payload['majiro.env'];records=[]
for key,target in [('APPNAME','레콘퀴스타'),('VERSION','버전|1.00'),('COPYRIGHT','(C)COTTON|SOFTWARE|2007')]:
 pat=rb'(?m)^'+key.encode()+rb'[\t ]+([^\r\n]+)';match=re.search(pat,env);assert match;source=match.group(1).decode('cp932');replacement=key.encode()+b'\t\t'+target.encode('cp949');env,n=re.subn(pat,lambda x:replacement,env);assert n==1;records.append({'id':'majiro.env::'+key,'source':source.replace('|',' '),'target':target.replace('|',' '),'consumer':'native About dialog SetWindowTextA','encoding':'cp949','translator_model':'Codex internal'})
payload['majiro.env']=env;(trial/'payloads/fastdata.arc/majiro.env').write_bytes(env);(trial/'fastdata.arc').write_bytes(a.rebuild(payload));parsed=Arc(trial/'fastdata.arc');newraw=(trial/'fastdata.arc').read_bytes()
for e in parsed.entries:assert newraw[e['offset']:e['offset']+e['size']]==payload[e['name']]
man=json.loads((base/'manifest.json').read_text(encoding='utf-8'));man['inherits_static_evidence']='../ui-trial-v2/manifest.json';man['required_windows_acp']=949;man['native_display_fields']=records
for x in man['archives']:
 x['output_sha256']=sha((trial/x['archive']).read_bytes())
 for e in x['changed']:e['output_sha256']=sha((trial/'payloads'/x['archive']/e['entry']).read_bytes())
(trial/'manifest.json').write_text(json.dumps(man,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(u/'translation/native-dynamic-display-map.json').write_text(json.dumps({'translator_model':'Codex internal','native_display_encoding':'cp949','required_windows_acp':949,'records':records+[m['native_dynamic_patch']],'engine_text_stays_cp932_mapped':True,'cross_locale_runtime_unverified':True},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'native_exe_sha256':sha(out),'changed_native_bytes':4,'native_env_fields':3,'requires_windows_acp':949},ensure_ascii=False))
