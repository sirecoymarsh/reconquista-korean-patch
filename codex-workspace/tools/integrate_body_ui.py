"""Merge frozen body/UI Unicode records without reusing incompatible UI font slots."""
from pathlib import Path
import sys,json,struct,collections,shutil,csv,io,re
import build_trial as b
from inspect_majiro import Arc,sha,dump
from build_recovery_full import isolated_font_mapping
from fontTools.ttLib import TTFont
R=b.ROOT;U=R/'ui-opening-ending';sys.path.insert(0,str(U/'tools'))
from build_native_diagnostics import apply_native
LABEL='body-ui-20261023-v1';O=R/'builds'/LABEL
BODY=R/'builds/integrated-recovery-full-20261023-v2';UI=U/'candidates/ui-trial-v22'
EXPECTED_BODY='65d940600bc88e65583953c5cb672b10502500041fff38d8df121883d5fd3b30'
EXPECTED_UI_FAST='3ac688758ff60af61a7dbc21910d30c11d977bd959c0cddc3638dd2563fcfbc2'
EXPECTED_NATIVE='96d91f59d792c24160e0cc4be6d695fce06df2296344f7655b82e9d5b66ac31d'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def archive(p):
 a=Arc(p);raw=p.read_bytes();return a,{e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries}
def tokens(text):
 result=[];start=0;i=0;quoted=False
 while i<len(text):
  c=text[i]
  if c=='"':
   if quoted and i+1<len(text) and text[i+1]=='"':i+=2;continue
   quoted=not quoted
  elif not quoted and c in ',\r\n':
   result.append((start,i));i+=2 if c=='\r' and i+1<len(text) and text[i+1]=='\n' else 1;start=i;continue
  i+=1
 assert not quoted
 if start<len(text):result.append((start,len(text)))
 return result

def main():
 assert not (O/'manifest.json').exists(),'Frozen build already exists'
 O.mkdir(exist_ok=True);F=O/'inputs';F.mkdir(exist_ok=True)
 inputs={'ui-semantic-map.json':U/'translation/ui-semantic-map.json','timeline-ko.json':U/'translation/timeline-ko.json','native-dynamic-display-map.json':U/'translation/native-dynamic-display-map.json','ui-manifest.json':UI/'manifest.json','native-manifest.json':U/'candidates/native-ui-v6/manifest.json','body-manifest.json':BODY/'manifest.json'}
 for name,p in inputs.items():
  if not (F/name).exists():shutil.copy2(p,F/name)
 ui=load(F/'ui-manifest.json');body=load(F/'body-manifest.json');rows=load(F/'ui-semantic-map.json')['records'];timeline=load(F/'timeline-ko.json');native=load(F/'native-dynamic-display-map.json')['records']
 assert len(rows)==143
 held=[r for r in timeline['records'] if r['provisional_readings']];accepted=[r for r in timeline['records'] if not r['provisional_readings']]
 assert len(held)==3 and len(accepted)==352
 assert sha((BODY/'scenario.arc').read_bytes())==EXPECTED_BODY
 assert sha((UI/'fastdata.arc').read_bytes())==EXPECTED_UI_FAST
 names=load(R/'translation/integration/recovery-full-20261023-v1/names.json')['mapping']
 oldmap=load(BODY/'font-map.json')['mapping'];shutil.copy2(BODY/'font-map.json',O/'font-map.json')
 mapping=isolated_font_mapping([r['target'] for r in rows if r['lane']!='native_diagnostic']+[r['target'] for r in accepted]+[r['target'] for r in native if r['id'].endswith('::font_sample')],O/'font-map.json')
 assert all(mapping[k]==v for k,v in oldmap.items())
 envsource=(R/'research/extracted/fastdata/majiro.env').read_bytes()
 envused=set(''.join(x.split('//',1)[0] for x in envsource.decode('cp932').splitlines() if not x.lstrip().startswith('//')))
 assert not envused&set(mapping.values())
 revision=sha(json.dumps(mapping,sort_keys=True,ensure_ascii=False).encode())[:8]
 b.FAMILY='Reconquista KR '+revision;b.SERIF_FAMILY='Reconquista KR Serif '+revision
 assert len(b.SERIF_FAMILY)<32
 inv={v:k for k,v in mapping.items()}
 def enc(t):
  s=''.join(mapping.get(c,c) for c in t);assert s.encode('cp932').decode('cp932')==s;assert ''.join(inv.get(c,c) for c in s)==t;return s
 fd=O/'font';fd.mkdir(exist_ok=True)
 fonts=[];font_reuse=[]
 for filename,serif,key in [('ReconquistaKR.otf',False,'font'),('ReconquistaKRSerif.otf',True,'serif_font')]:
  metadata=b.build_font(fd/filename,mapping,serif);fonts.append(metadata)
  old=TTFont(BODY/'font'/filename);new=TTFont(fd/filename);oc=old.getBestCmap();nc=new.getBestCmap()
  assert old.getTableData('hmtx')==new.getTableData('hmtx')
  oldcs=old['CFF '].cff.topDictIndex[0].CharStrings;newcs=new['CFF '].cff.topDictIndex[0].CharStrings
  for ko,slot in oldmap.items():
   glyph=oc[ord(slot)];assert nc[ord(slot)]==glyph==nc[ord(ko)];assert oldcs[glyph].bytecode==newcs[glyph].bytecode
  font_reuse.append({'font':filename,'prior_sha256':body[key]['output_sha256'],'new_sha256':metadata['output_sha256'],'prior_mapping_and_glyph_programs_preserved':len(oldmap),'all_horizontal_metrics_identical':True,'prior_gdi_evidence_reused':str(R/'reports'/('recovery-full-gdi-serif.json' if serif else 'recovery-full-gdi-sans.json'))})
  old.close();new.close()
 shutil.copy2(BODY/'font/LICENSE.txt',fd/'LICENSE.txt')
 a,originals=archive(R/'research/disc/scenario.arc');_,bodypayload=archive(BODY/'scenario.arc');payload=bodypayload.copy();reports={};native_reports={}
 group=collections.defaultdict(list)
 for r in rows:group[r['entry']].append(r)
 core={'config.mjo','console.mjo','load_sysdata.mjo'}
 bodyrecords=load(R/'translation/integration/recovery-full-20261023-v2/integrated-targets.json')
 bodyids={r['id'] for r in bodyrecords['records']+bodyrecords['inline_records']};assert not bodyids&{r['id'] for r in rows}
 assert not any(r.split('::')[0] in core for r in bodyids)
 for entry in sorted(set(group)|core|{'chronicle.mjo','message_box.mjo'}):
  # UI candidates do not carry any translated body text in these source entries.
  assert entry in core or bodypayload[entry]==originals[entry],entry
  source,raw=b.decode(originals[entry]);repl={};insert={};native_rows=[]
  for r in group[entry]:
   idx=r['instruction_index'];x=source.instructions[idx];assert x.opcode.mnemonic==r['opcode'] and x.string==r['source'],r['id']
   if r['lane']=='native_diagnostic':native_rows.append(r)
   else:repl[idx]=b.string_ins(r['opcode'],enc(r['target']))
  font_indices={'chronicle.mjo':[250,847,2274],'message_box.mjo':[126]}.get(entry,[])
  for idx in font_indices:
   x=source.instructions[idx];assert x.opcode.mnemonic=='ldstr' and x.string in ['ＭＳ ゴシック','MS UI Gothic'];assert idx not in repl
   repl[idx]=b.string_ins('ldstr',b.FAMILY)
  if entry=='load_sysdata.mjo':
   store=next(x for x in source.instructions if x.opcode.mnemonic=='st.s' and x.hash==0x391053c5)
   force=b.string_ins('ldstr',b.FAMILY)+raw[store.offset:store.offset+store.size]+b.op('pop')
   hook=b''.join(b.string_ins('ldstr','font\\'+name)+b.op('syscallp')+struct.pack('<IH',0x877445ce,1) for name in ['ReconquistaKR.otf','ReconquistaKRSerif.otf'])+force
   idx=next(i for i,x in enumerate(source.instructions) if x.offset==0x0f);assert idx==3;insert[idx]=hook
  if entry=='config.mjo':
   insert={i:b.op('pop')+b.string_ins('ldstr',b.FAMILY) for i,x in enumerate(source.instructions) if x.opcode.mnemonic=='st.s' and x.hash==0x391053c5};assert sorted(insert)==[3546,8695]
  if entry=='console.mjo':
   byoff={x.offset:x for x in source.instructions};ld=raw[0x31d3:0x31d3+byoff[0x31d3].size];st=raw[0x31bf:0x31bf+byoff[0x31bf].size];hook=b''
   for jp,ko in names.items():
    for display in ([jp,jp[0]+'\u3000'+jp[1]] if len(jp)==2 else [jp]):
     block=b.string_ins('ldstr',enc(ko))+st+b.op('pop');hook+=ld+b.string_ins('ldstr',display)+b.op('ceq.s')+b.op('brfalse')+struct.pack('<i',len(block))+block
   idx=next(i for i,x in enumerate(source.instructions) if x.offset==0x323e);assert idx==2059;insert[idx]=hook
  data,report=b.rewrite(originals[entry],repl,insert)
  # Prove the same ordered source instructions and replacements via relocation report before native-byte injection.
  report.update(semantic_ids=[r['id'] for r in group[entry]],font_consumer_indices=font_indices)
  if native_rows:
   data,native_reports[entry]=apply_native(data,entry,native_rows)
   report['pre_native_output_sha256']=report['output_sha256'];report['output_sha256']=sha(data)
  payload[entry]=data;reports[entry]=report
 old_serif=body['serif_font']['family'];retargeted=0
 for entry in ['00_レコンキスタ_start.mjo','00_レコンキスタ_start_3.mjo','テスト用.mjo']:
  src,_=b.decode(bodypayload[entry]);repl={i:b.string_ins('ldstr',b.SERIF_FAMILY) for i,x in enumerate(src.instructions) if x.opcode.mnemonic=='ldstr' and x.string==old_serif}
  assert len(repl)==({'00_レコンキスタ_start.mjo':8,'00_レコンキスタ_start_3.mjo':8,'テスト用.mjo':3}[entry])
  for i in repl:assert src.instructions[i+1].is_syscall and src.instructions[i+1].hash==0x06b3c8ac
  payload[entry],reports[entry]=b.rewrite(bodypayload[entry],repl);retargeted+=len(repl)
 # Apply approved CSV cells only; preserve unresolved reading cells byte-for-byte.
 csvreports=[];outrows={}
 for item in timeline['source_files']:
  entry=item['entry'];data=originals[entry];assert sha(data)==item['sha256'];text=data.decode('cp932');rs=list(csv.reader(io.StringIO(text,newline='')));spans=tokens(text);assert len(spans)==1040
  bycell={(r['row'],r['column']):r for r in accepted if r['entry']==entry};chunks=[];last=0
  for index,(start,end) in enumerate(spans):
   rc=divmod(index,13);token=text[start:end];chunks.append(text[last:start].encode('cp932'));rec=bycell.get(rc)
   if rec:
    assert rs[rc[0]][rc[1]]==rec['source'];assert rec['source'].count('\n')==rec['target'].count('\n')
    new=enc(rec['target']).encode('cp932')
    if token.startswith('"'):new=b'"'+new+b'"'
    else:assert not any(x in new for x in [b'"',b'\n',b'\r',b','])
    if not entry.startswith('exec_'):assert ord(enc(rec['target'])[0])>=0x3000
   else:new=token.encode('cp932')
   chunks.append(new);last=end
  chunks.append(text[last:].encode('cp932'));result=b''.join(chunks);check=list(csv.reader(io.StringIO(result.decode('cp932'),newline='')))
  assert len(check)==80 and all(len(row)==13 for row in check)
  for r in range(80):
   for c in range(13):assert ''.join(inv.get(ch,ch) for ch in check[r][c])==(bycell[r,c]['target'] if (r,c) in bycell else rs[r][c])
  newtext=result.decode('cp932');newspans=tokens(newtext)
  for index,((s,e),(ns,ne)) in enumerate(zip(spans,newspans)):
   if divmod(index,13) not in bycell:assert text[s:e]==newtext[ns:ne]
  assert result.count(b'\r\n')==data.count(b'\r\n') and result.count(b'\n')==data.count(b'\n')
  payload[entry]=result;outrows[entry]=check;csvreports.append({'entry':entry,'changed_cells':len(bycell),'source_sha256':sha(data),'output_sha256':sha(result),'shape':[80,13],'unchanged_tokens_and_delimiters_preserved':True,'semantic_roundtrip':True})
 for r in range(80):
  dates=[v[r][0] for v in outrows.values()];assert len(set(dates))==1 and (dates[0]=='[EOF]' or len(dates[0])<=12)
 # Validated raster/mask payloads are byte-identical to v22; text supports are rebuilt from original.
 fa,foriginal=archive(R/'research/disc/fastdata.arc');_,uipayload=archive(UI/'fastdata.arc');fp=foriginal.copy();raster=[]
 fm=next(x for x in ui['archives'] if x['archive']=='fastdata.arc')
 for r in fm['changed']:
  entry=r['entry'];assert sha(foriginal[entry])==r['source_sha256'] and sha(uipayload[entry])==r['output_sha256']
  if Path(entry).suffix.lower() in ['.rct','.rc8']:fp[entry]=uipayload[entry];raster.append(r)
 assert len(raster)==111
 for entry,count in [('menudata.cfg',1),('sysdata.cfg',2),('messagebox.cfg',1),('loadsave.cfg',1)]:
  assert foriginal[entry].count('ＭＳ ゴシック'.encode('cp932'))==count
  fp[entry]=foriginal[entry].replace('ＭＳ ゴシック'.encode('cp932'),b.FAMILY.encode('ascii'))
 env=envsource;envchanges=[]
 for r in [x for x in native if x['id'].startswith('majiro.env::')]+[{'id':'majiro.env::FC_NAME','source':'ＭＳ ゴシック','target':b.FAMILY}]:
  key=r['id'].split('::')[1];pattern=rb'(?m)^('+key.encode()+rb'[ \t]+)([^\r\n]*)';matches=list(re.finditer(pattern,env));assert len(matches)==1
  match=matches[0];assert match[2].decode('cp932').replace('|',' ')==r['source']
  value=r['target'].replace(' ','|').encode('ascii' if key=='FC_NAME' else 'cp949')
  env=env[:match.start(2)]+value+env[match.end(2):];envchanges.append({'id':r['id'],'source':r['source'],'target':r['target'],'encoding':'ascii' if key=='FC_NAME' else 'cp949'})
 for key in ['REG_LOCAL','TITLEBAR','CAPTURE_NAME','INSTREADME']:
  patt=rb'(?m)^'+key.encode()+rb'[ \t]+[^\r\n]*';assert re.search(patt,env).group()==re.search(patt,envsource).group()
 fp['majiro.env']=env
 arcreports=[]
 for name,arc,orig,data in [('scenario.arc',a,originals,payload),('fastdata.arc',fa,foriginal,fp)]:
  blob=arc.rebuild(data);(O/name).write_bytes(blob);parsed,readback=archive(O/name)
  assert [e['name'] for e in parsed.entries]==[e['name'] for e in arc.entries] and readback==data
  arcreports.append({'archive':name,'source_sha256':sha(arc.path.read_bytes()),'output_sha256':sha(blob),'entries':len(parsed.entries),'changed':[{'entry':n,'source_sha256':sha(orig[n]),'output_sha256':sha(v)} for n,v in data.items() if v!=orig[n]],'order_names_hashes_preserved':True,'reparse_payload_exact':True})
 nd=bytearray((U/'candidates/native-ui-v6/レコンキスタ.exe').read_bytes());assert sha(nd)==EXPECTED_NATIVE
 sample=next(x for x in native if x['id'].endswith('::font_sample'));offset=sample['file_offset'];oldbytes=bytes.fromhex(sample['output_bytes']);assert nd[offset:offset+len(oldbytes)]==oldbytes
 newbytes=enc(sample['target']).encode('cp932');assert len(newbytes)<=26;newbytes=newbytes.ljust(26,b' ');assert len(oldbytes)==26
 nd[offset:offset+26]=newbytes;(O/'レコンキスタ.exe').write_bytes(nd)
 before=(U/'candidates/native-ui-v6/レコンキスタ.exe').read_bytes();assert len(nd)==len(before) and all(offset<=i<offset+26 for i,(x,y) in enumerate(zip(before,nd)) if x!=y)
 nativepatch={'source_ui_sha256':EXPECTED_NATIVE,'output_sha256':sha(nd),'file_offset':offset,'length':26,'unicode_target':sample['target'],'mapped_hex':newbytes.hex(),'only_existing_display_bytes_changed':True,'source_resource_and_code_proofs_reused':str(U/'candidates/native-ui-v6/manifest.json'),'new_defender_scan_pending':True}
 manifest={'translator_model':'Codex internal','label':LABEL,'status':'combined_static_pass_gdi_and_security_pending_user_runtime_deferred','body_source':str(BODY),'body_snapshot_sha256':'f10a5560655270b8cc8fc75666bcdc4d9540e03e27f51cff71b35ed885dec24c','ui_source':str(UI),'inputs':{name:sha((F/name).read_bytes()) for name in inputs},'body_units':46935,'body_text_fields':73350,'body_inline_fields':625,'body_original_retained_units':16,'names':len(names),'ui_script_fields':len(rows),'ui_native_diagnostics_cp949':18,'ui_raster_label_instances':419,'ui_raster_payloads':len(raster),'timeline_cells':len(accepted),'timeline_original_retained_ids':[r['id'] for r in held],'font':fonts[0],'serif_font':fonts[1],'font_map_sha256':sha((O/'font-map.json').read_bytes()),'map_prior_slots_preserved':len(oldmap),'map_additions':{k:v for k,v in mapping.items() if k not in oldmap},'font_proof_reuse':font_reuse,'body_entries_identical_to_v2':[n for n in payload if payload[n]==bodypayload[n]],'body_entries_changed_from_v2':[n for n in payload if payload[n]!=bodypayload[n]],'body_ui_semantic_id_overlap':0,'script_validation':reports,'native_diagnostic_validation':native_reports,'serif_consumers_retargeted':retargeted,'csv_validation':csvreports,'environment_display_changes':envchanges,'environment_functional_keys_preserved':True,'raster_proof_reuse':raster,'archives':arcreports,'native_font_sample':nativepatch,'original_exe_sha256':body['original_exe_sha256'],'exe_sha256':sha(nd),'outputs':{name:sha((O/name).read_bytes()) for name in ['scenario.arc','fastdata.arc','レコンキスタ.exe']},'required_windows_acp':949,'runtime_verified':False,'visual_verification_owner':'user','ui_remaining_owned_by_thread':'01a162df-720c-77d2-96ed-6429e90b3333','op_ed_integrated':False}
 dump(O/'manifest.json',manifest)
 chars=set(manifest['map_additions'])|set('가나다라마바사아자차카타파하글자예시입니다');dump(O/'gdi-subset-map.json',{'mapping':{k:v for k,v in mapping.items() if k in chars}})
 print(json.dumps({'build':str(O),'body_units':46935,'ui_script_fields':len(rows),'timeline_cells':len(accepted),'map_additions':manifest['map_additions'],'glyphs':len(mapping),'outputs':manifest['outputs']},ensure_ascii=False))
if __name__=='__main__':main()
