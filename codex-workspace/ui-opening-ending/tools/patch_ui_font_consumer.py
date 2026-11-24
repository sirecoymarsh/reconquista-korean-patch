from pathlib import Path
import sys,json,shutil,hashlib
u=Path('P:/AI/Codex/projects/reconquista-ko/ui-opening-ending').resolve();b=u.parent;sys.path.insert(0,str(b/'tools'))
import build_trial as bt
from inspect_majiro import Arc,sha
v1=u/'candidates/ui-trial-v1';v2=u/'candidates/ui-trial-v2';assert not v2.exists();v2.mkdir()
m=json.loads((v1/'manifest.json').read_text(encoding='utf-8'));m['inherits_static_evidence']='../ui-trial-v1/manifest.json'
a=Arc(v1/'scenario.arc');raw=(v1/'scenario.arc').read_bytes();payloads={e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries}
s,_=bt.decode(payloads['message_box.mjo']);ix=[i for i,x in enumerate(s.instructions) if x.string=='MS UI Gothic'];assert ix==[126]
payloads['message_box.mjo'],rep=bt._rewrite(payloads['message_box.mjo'],{126:bt.string_ins('ldstr','Reconquista UI KR')},{})
(v2/'scenario.arc').write_bytes(a.rebuild(payloads));(v2/'payloads/scenario.arc').mkdir(parents=True)
for p in (v1/'payloads/scenario.arc').iterdir():shutil.copy2(p,v2/'payloads/scenario.arc'/p.name)
(v2/'payloads/scenario.arc/message_box.mjo').write_bytes(payloads['message_box.mjo'])
a2=Arc(v2/'scenario.arc');r2=(v2/'scenario.arc').read_bytes();assert [(e['name'],e['hash']) for e in a.entries]==[(e['name'],e['hash']) for e in a2.entries]
assert [e['name'] for e in a2.entries if r2[e['offset']:e['offset']+e['size']] != raw[next(x['offset'] for x in a.entries if x['name']==e['name']):next(x['offset']+x['size'] for x in a.entries if x['name']==e['name'])]]==['message_box.mjo']
f=Arc(v1/'fastdata.arc');r=(v1/'fastdata.arc').read_bytes();fp={e['name']:r[e['offset']:e['offset']+e['size']] for e in f.entries}
needle=b'TITLEBAR\t\tReconquista UI Test';assert fp['majiro.env'].count(needle)==1
fp['majiro.env']=fp['majiro.env'].replace(needle,b'TITLEBAR\t\tReconquista-UI-Test');(v2/'fastdata.arc').write_bytes(f.rebuild(fp));shutil.copytree(v1/'payloads/fastdata.arc',v2/'payloads/fastdata.arc');(v2/'payloads/fastdata.arc/majiro.env').write_bytes(fp['majiro.env']);shutil.copytree(v1/'font',v2/'font')
for arc in m['archives']:
 arc['output_sha256']=sha((v2/arc['archive']).read_bytes())
 for e in arc['changed']:
  e['output_sha256']=sha((v2/'payloads'/arc['archive']/e['entry']).read_bytes())
m['support_changes'].append({'file':'message_box.mjo','index':126,'change':'direct MS UI Gothic fontout consumer replaced','reason':'runtime v1 showed question marks'})
m['targeted_change_report']={'message_box_font':rep,'title':'Reconquista-UI-Test','unchanged_scenario_entries_identical_to_v1':True,'semantic_text_unchanged':True,'font_payload_unchanged':True}
(v2/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for p in Path('P:/AI/Codex/visualizations/2026/10/22/01a162df-720c-77d2-96ed-6429e90b3333/runtime-evidence').glob('*.png'):shutil.copy2(p,u/'evidence/runtime-v1'/p.name)
print('V2 targeted patch built',v2)
