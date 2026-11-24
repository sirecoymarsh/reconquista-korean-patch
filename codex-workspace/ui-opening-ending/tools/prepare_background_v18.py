from pathlib import Path
assert not Path("C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json").exists()
import sys,json,struct,re,os,datetime,psutil
U=Path.cwd().resolve();R=U/'runtime-ui-bg';C=U/'candidates/ui-trial-v18';sys.path.insert(0,str(U.parent/'tools'));from inspect_majiro import Arc,sha,MjoScript
from mjotool.crypt import crypt32
from mjotool.opcodes import Opcode
assert U.drive.upper()=='P:' and R.resolve().is_relative_to(U)
for p in psutil.process_iter(['pid','name','exe']):
 if p.info.get('exe') and Path(p.info['exe']).resolve()==(R/'レコンキスタ.exe').resolve():raise AssertionError(('Owned game already running',p.pid))
assert sha((R/'レコンキスタ.exe').read_bytes())=='f67195682944663b9546665eb3b63a639ace3f910e2ebf6ffaccda001d625b50'
assert sha((R/'fastdata.arc').read_bytes())=='3ce78e1289542b59333f915a275cfe8d42d450c46294010ce44a94d5b870ad5b'
assert sha((C/'fastdata.arc').read_bytes())=='26d9b28fa3b03a02f5960f87a6c94af267b0225145441387ad663025fa909e70'
scenariohash='040db0bf4ab872d47d3a6c06057a0c94f2056e8e8855fd9ae6e9d5a522913625';assert sha((R/'scenario.arc').read_bytes())==sha((C/'scenario.arc').read_bytes())==scenariohash
assert sha((R/'font/ReconquistaUIK2.otf').read_bytes())==sha((C/'font/ReconquistaUIK2.otf').read_bytes())=='746664ec37a73b7b4da5a14e274c1f3cf91e92e5aa9e08c6a0cd1fb2faf3292e'
def readarc(p):
 a=Arc(p);r=p.read_bytes();return a,{e['name']:r[e['offset']:e['offset']+e['size']] for e in a.entries}
def writearc(a,payload,path):
 assert path.stat().st_nlink==1;data=a.rebuild(payload);tmp=path.with_name(path.name+'.v18-staging');assert not tmp.exists();tmp.write_bytes(data);test=Arc(tmp);raw=tmp.read_bytes();assert all(raw[e['offset']:e['offset']+e['size']]==payload[e['name']] for e in test.entries);os.replace(tmp,path);return sha(data)
a,p=readarc(C/'fastdata.arc');_,old=readarc(R/'fastdata.arc');env=p['majiro.env'];changes={}
for key in ['TITLEBAR','REG_LOCAL','MUSICVOL','SOUNDVOL','VOICEVOL','ISPLAYMUSIC']:
 pattern=rb'(?m)^('+key.encode()+rb'[ \t]+)([^ \t\r\n]+)';v=b'Reconquista-UI-BG-v18' if key=='TITLEBAR' else re.search(pattern,old['majiro.env'])[2];assert key not in ['MUSICVOL','SOUNDVOL','VOICEVOL','ISPLAYMUSIC'] or v==b'0';env,n=re.subn(pattern,lambda m:m[1]+v,env);assert n==1;changes[key]=v.decode('ascii')
p['majiro.env']=env;fastsha=writearc(a,p,R/'fastdata.arc')
a,p=readarc(C/'scenario.arc');b=p['start.mjo'];n=struct.unpack_from('<I',b,24)[0];off=32+n*8;enc=b[:16]==MjoScript.SIGNATURE_ENCRYPTED;code=bytearray(crypt32(b[off:]) if enc else b[off:]);absolute=11068;pos=absolute-off;assert code[pos:pos+4]==struct.pack('<I',0xf698f3c0);assert code[pos-2:pos]==struct.pack('<H',Opcode.fromname('call').value);code[pos:pos+4]=struct.pack('<I',0xf932f5fc);changed=b[:off]+(crypt32(bytes(code)) if enc else bytes(code));assert [i for i,(x,y) in enumerate(zip(b,changed)) if x!=y]==list(range(absolute,absolute+4));p['start.mjo']=changed;testsha=writearc(a,p,R/'scenario.arc')
j={'candidate':'ui-trial-v18','native_candidate':'native-ui-v5','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_fastdata_sha256':sha((C/'fastdata.arc').read_bytes()),'runtime_fastdata_sha256':fastsha,'source_scenario_sha256':scenariohash,'test_scenario_sha256':testsha,'runtime_env_changes':changes,'test_entry':{'entry':'start.mjo','instruction_index':1601,'old_callee':'0xf698f3c0 initial title dispatcher','new_callee':'0xf932f5fc full extra menu','allowed_byte_region':[11068,4],'caller_argument_count':1,'callee_fixed_argcheck_parameters':0,'note':'Test-only entry bypasses title unlock gate without editing persistent progress flags. Existing caller operand/argument frame retained; verify actual execution.'},'candidate_untouched':True,'restore_scenario_after_test':True,'reused_font_804_and_archives':True}
(U/'reports/background-runtime-v18-prepared.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(j,ensure_ascii=False))
