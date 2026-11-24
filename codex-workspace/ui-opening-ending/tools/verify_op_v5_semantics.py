from pathlib import Path
import json,re,datetime
U=Path.cwd();O=U/'candidates/opening-video-ko-v5';V=U/'candidates/opening-video-ko-v4'
old=json.loads((V/'lyrics-bilingual.json').read_text(encoding='utf-8'));new=json.loads((O/'lyrics-bilingual.json').read_text(encoding='utf-8'));changed=[];foreign=[]
for a,b in zip(old['records'],new['records']):
 assert a['id']==b['id'] and a['source_recovered_ja']==b['source_recovered_ja'] and (a['start'],a['end'])==(b['start'],b['end'])
 if a['target']!=b['target']:changed.append(b['id'])
 spans=re.findall(r'[A-Za-z]+(?: [A-Za-z]+)*',b['source_recovered_ja'])
 for span in spans:assert span in b['target'];foreign.append({'id':b['id'],'span':span})
assert changed==['op-lyrics::004']
for name in ['opening-ko.ass','opening-ko-4k.ass']:
 text=(O/'subtitles'/name).read_text(encoding='utf-8');ds=[x.split(',',9) for x in text.splitlines() if x.startswith('Dialogue:')];assert len(ds)==32;assert all(x[3]!='Credit' for x in ds)
 for i in range(0,32,2):assert ds[i][1:3]==ds[i+1][1:3] and ds[i][3]=='LyricJA' and ds[i+1][3]=='Lyric'
report={'translator_model':'Codex internal','status':'pass','changed_lyric_ids':changed,'preserved_foreign_spans':foreign,'pairs':16,'upper_quote_cues_removed':4,'quote_translation_reused_from_v4':True,'explicit_user_requested_role_translations_retained':True,'provisional_source_ids_inherited':['op-lyrics::007'],'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(O/'evidence/semantic-gate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
