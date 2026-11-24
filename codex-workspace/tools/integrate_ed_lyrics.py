"""Integrate reviewed ED overlay without changing original dialogue, audio, fonts or executable."""
from pathlib import Path
import sys,json,os,shutil,struct,zlib,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));from inspect_majiro import Arc,sha,dump
base='body-ui-20261023-v4';label='body-ui-20261023-v5';A=R/'builds'/base;O=R/'builds'/label;C=R/'builds/ed-lyrics-overlay-v3';T=R/('runtime-'+label);S=R/('runtime-'+base)
cm=json.loads((C/'manifest.json').read_text(encoding='utf-8'));assert cm['visual_review'] and cm['independent_technical_review'];assert not O.exists() and not T.exists();O.mkdir()
m=json.loads((A/'manifest.json').read_text(encoding='utf-8'))
changed={};proof=[]
for name in ['scenario.arc','fastdata.arc']:
 a=Arc(A/name);blob=a.path.read_bytes();assert sha(blob)==m['outputs'][name];data={e['name']:blob[e['offset']:e['offset']+e['size']] for e in a.entries};before={k:sha(v) for k,v in data.items()}
 if name=='scenario.arc':
  assert before['staffroll.mjo']==cm['script']['source_sha256'];replacement=(C/'payloads/staffroll.mjo').read_bytes();assert sha(replacement)==cm['script']['output_sha256'];data['staffroll.mjo']=replacement;out=a.rebuild(data);added=[];changes=['staffroll.mjo']
 else:
  assert [int(e['hash'],16) for e in a.entries]==sorted(int(e['hash'],16) for e in a.entries)
  added=[]
  for row in cm['assets']:
   n=row['entry'];assert n not in data and Path(n).suffix in ['.rct','.rc8'];v=(C/'payloads'/n).read_bytes();assert sha(v)==row['sha256'];data[n]=v;added.append(n)
  names=sorted(data,key=lambda n:zlib.crc32(n.encode('cp932')));hashes=[zlib.crc32(n.encode('cp932')) for n in names];assert len(set(hashes))==len(hashes)
  names_offset=28+len(names)*12;strings=b''.join(n.encode('cp932')+b'\0' for n in names);data_offset=names_offset+len(strings);pos=data_offset;table=[];parts=[]
  for n,h in zip(names,hashes):table.append(struct.pack('<III',h,pos,len(data[n])));parts.append(data[n]);pos+=len(data[n])
  out=blob[:16]+struct.pack('<III',len(names),names_offset,data_offset)+b''.join(table)+strings+b''.join(parts);changes=[]
 (O/name).write_bytes(out);pa=Arc(O/name);read={e['name']:out[e['offset']:e['offset']+e['size']] for e in pa.entries};assert set(read)==set(data)
 for n,v in read.items():assert v==data[n]
 actual=[n for n in before if before[n]!=sha(read[n])];assert actual==changes;assert set(read)-set(before)==set(added)
 changed[name]=sha(out);proof.append({'archive':name,'parent_sha256':sha(blob),'output_sha256':sha(out),'changed_existing':changes,'added':added,'all_other_payloads_byte_identical':True,'crc_table_order_and_readback_pass':True})
 for ar in m['archives']:
  if ar['archive']==name:
   ar['output_sha256']=sha(out);ar['entries']=len(pa.entries)
   for n in changes:assert n not in [x['entry'] for x in ar['changed']];ar['changed'].append({'entry':n,'source_sha256':before[n],'output_sha256':sha(read[n])})
   for n in added:ar['changed'].append({'entry':n,'source_sha256':None,'output_sha256':sha(read[n]),'new_localization_asset':True})
for p in A.iterdir():
 if p.name in changed or p.name in ['manifest.json','installation.json']:continue
 if p.is_dir():shutil.copytree(p,O/p.name,copy_function=os.link,dirs_exist_ok=True)
 else:os.link(p,O/p.name)
I=O/'delta-inputs/ed-lyrics-overlay-v3';shutil.copytree(C,I,copy_function=shutil.copy2)
m.update(label=label,parent_build=str(A),parent_manifest_sha256=sha((A/'manifest.json').read_bytes()),status='body_ui_ending_lyrics_static_review_pass_user_runtime_deferred');m['outputs'].update(changed)
m['op_ed_status'].update(ending_lyrics_localized=True,ending_lyric_lines=32,ending_lyrics_font='Eulyoo1945 SemiBold',ending_lyrics_source_uncertain_ids=['ed-lyrics::014'],actual_game_sync_verified=False)
m['ed_lyric_integration']={'candidate':str(C),'frozen_manifest':'delta-inputs/ed-lyrics-overlay-v3/manifest.json','candidate_manifest_sha256':sha((C/'manifest.json').read_bytes()),'validation':proof,'body_and_audio_unchanged':True,'new_game_scripts':0,'new_script_functions':2,'added_raster_assets':64,'static_flow_review':'delta-inputs/ed-lyrics-overlay-v3/evidence/control-flow-review.json','runtime_limits':['User verifies ED song sync and top-line visibility','User verifies menu, load and title transitions during ED','Old save already past music start requires ED replay to start overlay']}
m['source_unit_accounting']['op_ed_status']=m['op_ed_status'];T.mkdir()
for p in S.rglob('*'):
 rel=p.relative_to(S);q=T/rel
 if p.is_dir():q.mkdir(exist_ok=True)
 elif str(rel) not in changed and p.name not in ['BUILD-IDENTITY.json','한국어화-상태.md']:
  if rel.parts[0]=='savedata':shutil.copy2(p,q)
  else:os.link(p,q)
for name,expected in changed.items():shutil.copy2(O/name,T/name);assert sha((T/name).read_bytes())==expected
m.update(installed_runtime=str(T),savedata_copied_from=str(S/'savedata'));dump(O/'manifest.json',m);dump(T/'BUILD-IDENTITY.json',m)
l=R/'Start-Korean.ps1';txt=l.read_text(encoding='utf-8-sig');assert base in txt;l.write_text(txt.replace(base,label),encoding='utf-8-sig')
s=json.loads((R/'progress.json').read_text(encoding='utf-8'));s['updated_at']=datetime.datetime.now().astimezone().isoformat();s['runtime']=str(T);s['body_ui_integration'].update(label=label,build=str(O),runtime=str(T),op_ed_status=m['op_ed_status']);s['translation']['build']=str(O);s['next']='Integrate dedicated-session OP movie and title logo typography; continue remaining UI. Actual native screen/playback verification remains user-owned.';dump(R/'progress.json',s);dump(R/'reports/combined-source-coverage.json',m['source_unit_accounting']);dump(R/'reports/latest-combined-build.json',{'path':str(O),'runtime':str(T),'manifest_sha256':sha((O/'manifest.json').read_bytes()),'label':label})
doc=R/'한국어화-실행안내.md';txt=doc.read_text(encoding='utf-8').replace('UI의 나머지 이미지 문구, OP와 노래 자막은 별도 세션에서 계속 작업 중이며 아직 통합되지 않았습니다.','ED 가사32줄도 을유1945 글꼴로 화면 위쪽에 반영했습니다. OP·타이틀 로고와 나머지 UI 이미지는 계속 작업 중입니다.');txt+='\n\nED 가사는 음악 시작 시각에 맞춘 별도 표시 스크립트입니다. 실제 게임의 싱크·메뉴·로드·타이틀 전환 검증은 사용자가 나중에 진행합니다. ED가 이미 시작된 옛 저장 파일에서는 엔딩을 다시 시작해야 자막 표시가 시작됩니다. 가사14번의 원문 청취는 잠정 판독 상태입니다.\n';doc.write_text(txt,encoding='utf-8');(T/'한국어화-상태.md').write_text(txt,encoding='utf-8');print(json.dumps({'build':label,'runtime':str(T),'new_lyrics':32,'outputs':changed,'game_executed':False},ensure_ascii=False))