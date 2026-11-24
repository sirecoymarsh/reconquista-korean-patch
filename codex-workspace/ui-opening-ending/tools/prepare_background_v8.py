from pathlib import Path
import json,sys,re,os,datetime
U=Path(__file__).resolve().parents[1];sys.path.insert(0,str(U.parent/'tools'))
from inspect_majiro import Arc,sha
C=U/'candidates/ui-trial-v8';R=U/'runtime-ui-bg'
assert U.drive.upper()=='P:' and R.resolve().is_relative_to(U.resolve())
source_expected='816891d3c237f6f4165849e216eacf81a5deac60e4dcfa8da3fc78ca2bfb3426'
prior_expected='bcadb79e854a3bbe00af83e515b4bafd516e2b860a7e5286cacd65627a2041bf'
exe_expected='f67195682944663b9546665eb3b63a639ace3f910e2ebf6ffaccda001d625b50'
scenario_expected='db150e681b1096eec109b0b94ee304573ff44d320de4628fd973bbe32392cc5c'
assert sha((C/'fastdata.arc').read_bytes())==source_expected
assert sha((R/'fastdata.arc').read_bytes())==prior_expected
assert sha((R/'レコンキスタ.exe').read_bytes())==exe_expected
assert sha((R/'scenario.arc').read_bytes())==scenario_expected
assert sha((C/'scenario.arc').read_bytes())==scenario_expected
assert (R/'fastdata.arc').stat().st_nlink==1
arc=Arc(C/'fastdata.arc');raw=arc.path.read_bytes();payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in arc.entries};before=dict(payload)
env=payload['majiro.env'];changes={'TITLEBAR':'Reconquista-UI-BG-v8','REG_LOCAL':'Reconquista-UI-BG-v8-20261023','MUSICVOL':'0','SOUNDVOL':'0','VOICEVOL':'0','ISPLAYMUSIC':'0'}
records=[]
for key,val in changes.items():
 pat=rb'(?m)^('+re.escape(key.encode())+rb'[ \t]+)[^ \t\r\n]+'
 m=re.search(pat,env);assert m,key
 env,n=re.subn(pat,lambda m:m[1]+val.encode('ascii'),env);assert n==1
 records.append({'field':key,'value':val})
payload['majiro.env']=env
blob=arc.rebuild(payload);stage=R/'fastdata.v8-staging.arc';assert not stage.exists();stage.write_bytes(blob)
check=Arc(stage);data=stage.read_bytes();assert [(e['name'],e['hash']) for e in check.entries]==[(e['name'],e['hash']) for e in arc.entries]
assert all(data[e['offset']:e['offset']+e['size']]==payload[e['name']] for e in check.entries)
assert [n for n in payload if before[n]!=payload[n]]==['majiro.env']
os.replace(stage,R/'fastdata.arc')
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'candidates/ui-trial-v8','runtime':str(R.resolve()),'exe_sha256':exe_expected,'scenario_sha256':scenario_expected,'fastdata_sha256':sha(blob),'source_fastdata_sha256':source_expected,'prior_runtime_fastdata_sha256':prior_expected,'only_runtime_adjustments':changes,'purpose':'Silent private-desktop validation of changed v6-v8 UI only; no physical input, foreground activation or desktop switch','payload_identity_except_majiro_env':True,'unchanged_input_links':'Reused reports/background-runtime-prepared.json; no linked input was written','reuse':['Native EXE v5 Defender scan','773-glyph font GDI proof','v5 modal runtime proof','scenario v4 unchanged']}
(U/'reports/background-runtime-v8-prepared.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
