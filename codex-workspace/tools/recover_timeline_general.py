"""Translate general timeline text while retaining only unconfirmed proper-name spans."""
from pathlib import Path
import sys,json,csv,io,shutil,os,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));from inspect_majiro import Arc,sha,dump
from integrate_body_ui import tokens
OLD='body-ui-20261023-v1';NEW='body-ui-20261023-v2';A=R/'builds'/OLD;O=R/'builds'/NEW;assert not O.exists();O.mkdir()
manifest=json.loads((A/'manifest.json').read_text(encoding='utf-8'));mapping=json.loads((A/'font-map.json').read_text(encoding='utf-8'))['mapping'];inverse={v:k for k,v in mapping.items()}
def enc(t):
 s=''.join(mapping.get(c,c) for c in t);s.encode('cp932');assert ''.join(inverse.get(c,c) for c in s)==t;return s
records=[
 {'id':'alt_ホラー年表改.csv::r017c07','entry':'alt_ホラー年表改.csv','row':17,'column':7,'target':'마을 밖 출신인\n하토리 高文과 결혼.\n성은 一ノ瀬에서 하토리로 바꿈.','retained_source_name_spans':['高文','一ノ瀬']},
 {'id':'alt_ホラー年表改.csv::r028c07','entry':'alt_ホラー年表改.csv','row':28,'column':7,'target':'朋子는 마을에\n별다른 애착이 없어\n처음에는 전혀 다른 곳으로 이주할 생각도 했음.\n그러나 섬의 병원과 시설이\n마호코의 백혈병 치료에 적합하여\n결국 뉴타운으로 이주하기로 함.','retained_source_name_spans':['朋子']},
 {'id':'exec_ホラー年表改.csv::r000c07','entry':'exec_ホラー年表改.csv','row':0,'column':7,'target':'하토리 朋子','retained_source_name_spans':['朋子']}]
sources={r['id']:r for r in json.loads((A/'inputs/timeline-ko.json').read_text(encoding='utf-8'))['records']}
for r in records:
 r.update(source=sources[r['id']]['source'],translator_model='Codex internal',status='general_text_translated_unconfirmed_name_readings_retained_in_kanji',rationale='Translate ordinary surrounding content without accepting a guessed name pronunciation. 思い入れ is emotional attachment, not an asserted factual memory.')
 assert r['source'].count('\n')==r['target'].count('\n');enc(r['target'])
arc=Arc(A/'scenario.arc');raw=arc.path.read_bytes();payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in arc.entries};reports=[]
for name in sorted({r['entry'] for r in records}):
 before=payload[name];text=before.decode('cp932');spans=tokens(text);assert len(spans)==1040;rows=list(csv.reader(io.StringIO(text,newline='')));by={(r['row'],r['column']):r for r in records if r['entry']==name};chunks=[];last=0
 for i,(start,end) in enumerate(spans):
  key=divmod(i,13);token=text[start:end];chunks.append(text[last:start]);r=by.get(key)
  if r:
   assert rows[key[0]][key[1]]==r['source'];value=enc(r['target']);new='"'+value+'"' if token.startswith('"') else value
   if not token.startswith('"'):assert not any(c in value for c in ',\n\r"')
   if not name.startswith('exec_'):assert ord(value[0])>=0x3000
  else:new=token
  chunks.append(new);last=end
 chunks.append(text[last:]);changed=''.join(chunks);new=changed.encode('cp932');newrows=list(csv.reader(io.StringIO(changed,newline='')));assert len(newrows)==80 and all(len(r)==13 for r in newrows)
 for i,((start,end),(ns,ne)) in enumerate(zip(spans,tokens(changed))):
  key=divmod(i,13)
  if key in by:assert ''.join(inverse.get(c,c) for c in newrows[key[0]][key[1]])==by[key]['target']
  else:assert changed[ns:ne]==text[start:end]
 assert new.count(b'\r\n')==before.count(b'\r\n') and new.count(b'\n')==before.count(b'\n');payload[name]=new;reports.append({'entry':name,'source_sha256':sha(before),'output_sha256':sha(new),'changed_cells':len(by),'other_tokens_and_all_delimiters_identical':True,'semantic_roundtrip_pass':True,'shape':[80,13]})
blob=arc.rebuild(payload);(O/'scenario.arc').write_bytes(blob);re=Arc(O/'scenario.arc');assert [e['name'] for e in re.entries]==[e['name'] for e in arc.entries]
for e in re.entries:assert blob[e['offset']:e['offset']+e['size']]==payload[e['name']]
for name in ['fastdata.arc','レコンキスタ.exe','font-map.json','gdi-subset-map.json']:os.link(A/name,O/name)
shutil.copytree(A/'font',O/'font',copy_function=os.link);shutil.copytree(A/'inputs',O/'inputs',copy_function=os.link)
dump(O/'timeline-general-text-recovery.json',{'translator_model':'Codex internal','records':records,'validation':reports,'name_readings_confirmed':False,'font_map_and_font_files_unchanged':True,'prior_static_gdi_and_exe_security_proofs_reused':True})
manifest.update(label=NEW,parent_build=str(A),parent_manifest_sha256=sha((A/'manifest.json').read_bytes()),timeline_cells=355,timeline_fully_korean_cells=352,timeline_cells_with_source_names=3,timeline_original_retained_ids=[],timeline_source_name_spans=[{'id':r['id'],'source_names':r['retained_source_name_spans']} for r in records],timeline_recovery=str(O/'timeline-general-text-recovery.json'),delta_validation=reports)
manifest['outputs']['scenario.arc']=sha(blob)
for row in manifest['archives']:
 if row['archive']=='scenario.arc':
  row['output_sha256']=sha(blob)
  for changed in row['changed']:
   if changed['entry'] in {r['entry'] for r in records}:changed['output_sha256']=sha(payload[changed['entry']])
for row in manifest['csv_validation']:
 if row['entry'] in {r['entry'] for r in records}:
  row['output_sha256']=sha(payload[row['entry']]);row['changed_cells']+=sum(r['entry']==row['entry'] for r in records)
T=R/('runtime-'+NEW);S=R/('runtime-'+OLD);assert not T.exists();T.mkdir()
for p in S.rglob('*'):
 relative=p.relative_to(S);q=T/relative
 if p.is_dir():q.mkdir(exist_ok=True)
 elif p.name not in ['BUILD-IDENTITY.json','한국어화-상태.md'] and relative!=Path('scenario.arc'):
  if relative.parts[0]=='savedata':shutil.copy2(p,q)
  else:os.link(p,q)
shutil.copy2(O/'scenario.arc',T/'scenario.arc');assert sha((T/'scenario.arc').read_bytes())==sha(blob)
manifest.update(installed_runtime=str(T),savedata_copied_from=str(S/'savedata'))
dump(O/'manifest.json',manifest);dump(T/'BUILD-IDENTITY.json',manifest)
launch=R/'Start-Korean.ps1';txt=launch.read_text(encoding='utf-8-sig');assert OLD in txt;launch.write_text(txt.replace(OLD,NEW),encoding='utf-8-sig')
state=json.loads((R/'progress.json').read_text(encoding='utf-8'));state['runtime']=str(T);state['updated_at']=datetime.datetime.now().astimezone().isoformat();state['body_ui_integration'].update(label=NEW,runtime=str(T),build=str(O),timeline_cells=355,timeline_source_retained_ids=[],timeline_cells_with_source_names=3,timeline_name_spans=manifest['timeline_source_name_spans']);dump(R/'progress.json',state)
dump(R/'reports/latest-combined-build.json',{'path':str(O),'runtime':str(T),'manifest_sha256':sha((O/'manifest.json').read_bytes()),'label':NEW})
doc=R/'한국어화-실행안내.md';text=doc.read_text(encoding='utf-8').replace('연표352셀','연표355셀').replace('연표의 잠정 인명3셀과 본문16구간은 원문입니다.','연표3셀은 일반 설명을 한국어로 번역하고 독음 미확정 이름 高文·一ノ瀬·朋子만 한자 표기로 보존했습니다. 본문16구간은 원문입니다.');doc.write_text(text,encoding='utf-8');(T/'한국어화-상태.md').write_text(text,encoding='utf-8')
print(json.dumps({'build':str(O),'runtime':str(T),'timeline_cells':355,'name_readings_still_unconfirmed':['高文','一ノ瀬','朋子'],'scenario_sha256':sha(blob),'no_font_or_exe_change':True},ensure_ascii=False))
