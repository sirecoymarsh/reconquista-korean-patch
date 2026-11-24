"""Dedicated UI candidate builder. Never writes the parent workspace or progress records."""
from pathlib import Path
import json,sys,struct,collections,re,shutil
from fontTools.ttLib import TTFont
U=Path(r'P:\AI\Codex\projects\reconquista-ko\ui-opening-ending').resolve()
B=Path(r'P:\AI\Codex\projects\reconquista-ko').resolve()
assert U.name=='ui-opening-ending' and U.parent==B
sys.path.insert(0,str(B/'tools'))
import build_trial as bt
from inspect_majiro import Arc,sha
FAMILY='Reconquista UI KR'
def safe(p):
 p=p.resolve();assert p!=U and U in p.parents,('outside dedicated UI root',p);return p
def put(p,b):
 p=safe(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def dump(p,x):put(p,(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
source=json.loads((U/'source/ui-string-candidates.json').read_text(encoding='utf-8'));byid={r['id']:r for r in source['records']};targets={}
for l in (U/'translation/ui-text-ko.tsv').read_text(encoding='utf-8-sig').splitlines():
 k,v=l.split('\t',1);assert k not in targets;targets[k]=v
assert sha((U/'translation/ui-text-ko.tsv').read_bytes())=='be3776a8fc9c6f2a179ae5409a74146205eb698997dbbeac761dbde111423d44'
review={'reviewer':'/root/ui_text_review','mode':'read-only independent QA','translation_sha256':sha((U/'translation/ui-text-ko.tsv').read_bytes()),'source_sha256':sha((U/'source/ui-string-candidates.json').read_bytes()),'records':143,'tutorial_fields':89,'verdict':'context_pass','findings':[],'notes':['Keep load substring test before save test: Korean quick-load prompt contains both 저장 and 불러.','OS diagnostic font and surname reading remain pending.'],'runtime_pass':False}
dump(U/'reports/ui-text-independent-review.json',review)
deferred={k for k,v in byid.items() if k in targets and ('パラメータ' in v['source'] or '[EOF]の存在' in v['source'])}|{'config.mjo::008005','config.mjo::008011'}
rows=[{**byid[k],'target':t,'translator_model':'Codex internal','provenance':'Codex task 01a162df-720c-77d2-96ed-6429e90b3333, 2026-10-22','lane':'effect_sound_substring_key' if k.startswith('message_box.mjo::') else 'native_diagnostic' if k in deferred else 'display','status':'context_reviewed','build_included':k not in deferred} for k,t in targets.items()]
# The central map is read-only. Local additions must be re-allocated at final integration.
centralbytes=(B/'translation/hangul-cp932-map.json').read_bytes();mapping=json.loads(centralbytes)['mapping'].copy();base_mapping=mapping.copy();used=set()
for l in (B/'localization/catalog/catalog.jsonl').open(encoding='utf-8'):used.update(json.loads(l)['source'])
for folder,pattern in [('fastdata','*.cfg'),('scenario','*.csv')]:
 for p in (B/'research/extracted'/folder).glob(pattern):used.update(p.read_bytes().decode('cp932'))
for envline in (B/'research/extracted/fastdata/majiro.env').read_bytes().decode('cp932').splitlines():
 if not envline.lstrip().startswith('//'):used.update(envline.split('//',1)[0])
occupied=set(mapping.values());assert len(occupied)==len(mapping) and not occupied&used
needed={c for t in targets.values() for c in t if '\uac00'<=c<='\ud7a3'};slots=[]
for lead in list(range(0xe0,0xf0))+list(range(0x88,0xa0)):
 for trail in range(0x40,0xfd):
  if trail==0x7f:continue
  b=bytes([lead,trail])
  try:c=b.decode('cp932')
  except UnicodeError:continue
  if len(c)==1 and '\u3400'<=c<='\u9fff' and c.encode('cp932')==b and c not in used|occupied:slots.append(c)
for c in sorted(needed-set(mapping)):mapping[c]=slots.pop(0)
inverse={v:k for k,v in mapping.items()}
def enc(t):
 s=''.join(mapping.get(c,c) for c in t);assert s.encode('cp932').decode('cp932')==s;assert ''.join(inverse.get(c,c) for c in s)==t;return s
mapobj={'translator_model':'Codex internal','central_base_sha256':sha(centralbytes),'base_entry_count':len(base_mapping),'mapping':mapping,'additions':{k:v for k,v in mapping.items() if k not in base_mapping},'central_file_modified':False,'integration':'Merge Unicode target text and allocate central slots before re-encoding. Do not overwrite central mapping.'}
dump(U/'translation/hangul-cp932-ui-map.json',mapobj)
O=safe(U/'candidates/ui-trial-v1');O.mkdir(exist_ok=True);safe(O/'font').mkdir(exist_ok=True)
fpath=B/'research/fonts/NotoSansCJKkr-Regular.otf';font=TTFont(fpath,recalcTimestamp=False);cmap=font.getBestCmap();expected={}
for ko,slot in mapping.items():
 glyph=cmap.get(ord(ko));assert glyph and glyph!='.notdef';assert glyph in font['CFF '].cff.topDictIndex[0].CharStrings;expected[ord(slot)]=glyph
for table in font['cmap'].tables:
 if table.isUnicode():table.cmap.update(expected)
names={1:FAMILY,2:'Regular',3:'ReconquistaUIKR-Regular-20261022',4:FAMILY+' Regular',6:'ReconquistaUIKR-Regular',16:FAMILY,17:'Regular'}
for n in font['name'].names:
 if n.nameID in names:n.string=names[n.nameID].encode(n.getEncoding())
for nid,value in names.items():font['name'].setName(value,nid,3,1,0x409)
cff=font['CFF '].cff;cff.fontNames=['ReconquistaUIKR-Regular'];top=cff.topDictIndex[0];top.FamilyName=FAMILY;top.FullName=FAMILY+' Regular';top.FontName='ReconquistaUIKR-Regular'
font['OS/2'].ulCodePageRange1=(font['OS/2'].ulCodePageRange1|(1<<17))&~((1<<18)|(1<<19)|(1<<20)|(1<<21));font['head'].modified=font['head'].created
fontout=safe(O/'font/ReconquistaUIKR.otf');font.save(fontout);cm=TTFont(fontout).getBestCmap();assert all(cm[k]==v for k,v in expected.items());put(O/'font/LICENSE.txt',(B/'research/fonts/LICENSE').read_bytes())
a=Arc(B/'research/disc/scenario.arc');originals={e['name']:(B/'research/extracted/scenario'/e['name']).read_bytes() for e in a.entries};payloads=originals.copy();reps=collections.defaultdict(dict);insers=collections.defaultdict(dict);support=[]
for rec in rows:
 if rec['id'] in deferred:continue
 f=rec['entry'];idx=rec['instruction_index'];s,_=bt.decode(originals[f]);assert s.instructions[idx].string==rec['source'];reps[f][idx]=bt.string_ins(rec['opcode'],enc(rec['target']))
loader,raw=bt.decode(originals['load_sysdata.mjo']);store=next(x for x in loader.instructions if x.opcode.mnemonic=='st.s' and x.hash==0x391053c5)
force=bt.string_ins('ldstr',FAMILY)+raw[store.offset:store.offset+store.size]+bt.op('pop');hook=bt.string_ins('ldstr',r'font\ReconquistaUIKR.otf')+bt.op('syscallp')+struct.pack('<IH',0x877445ce,1)+force
idx=next(i for i,x in enumerate(loader.instructions) if x.offset==0x0f);insers['load_sysdata.mjo'][idx]=hook;support.append({'file':'load_sysdata.mjo','index':idx,'change':'register dedicated UI font/select family','integration_overlap':'main loader hook; merge once'})
cfg,_=bt.decode(originals['config.mjo'])
for i,x in enumerate(cfg.instructions):
 if x.opcode.mnemonic=='st.s' and x.hash==0x391053c5:insers['config.mjo'][i]=bt.op('pop')+bt.string_ins('ldstr',FAMILY);support.append({'file':'config.mjo','index':i,'change':'trial font fixed to compatible mapped family'})
for rec in source['records']:
 if rec['entry']=='chronicle.mjo' and rec['source']=='ＭＳ ゴシック':reps[rec['entry']][rec['instruction_index']]=bt.string_ins(rec['opcode'],FAMILY);support.append({'file':rec['entry'],'index':rec['instruction_index'],'change':'direct UI font consumer'})
script_reports={}
for f in sorted(set(reps)|set(insers)):
 # _rewrite is the already-reviewed pure byte rewrite; do not call the parent's cached rewrite/main.
 payloads[f],script_reports[f]=bt._rewrite(originals[f],reps[f],insers[f]);put(O/'payloads/scenario.arc'/f,payloads[f])
scenario=O/'scenario.arc';put(scenario,a.rebuild(payloads))
fast=Arc(B/'research/disc/fastdata.arc');fp0={e['name']:(B/'research/extracted/fastdata'/e['name']).read_bytes() for e in fast.entries};fp=fp0.copy()
for n,b in fp0.items():
 if n.endswith('.cfg') and 'ＭＳ ゴシック'.encode('cp932') in b:fp[n]=b.replace('ＭＳ ゴシック'.encode('cp932'),FAMILY.encode('ascii'));support.append({'file':n,'change':'UI font consumer','occurrences':b.count('ＭＳ ゴシック'.encode('cp932'))})
env=fp0['majiro.env'].decode('cp932')
for key,value in [('REG_LOCAL','Reconquista-UI-Isolated-20261022'),('TITLEBAR','Reconquista UI Test'),('CAPTURE_NAME','Reconquista-UI'),('FC_NAME','Reconquista|UI|KR')]:
 env,n=re.subn(r'(?m)^'+key+r'[\t ]+[^\r\n]*',key+'\t\t'+value,env);assert n==1
fp['majiro.env']=env.encode('cp932');support.append({'file':'majiro.env','change':'runtime-only registry/title/capture isolation and font default','exclude_from_final_integration':['REG_LOCAL','TITLEBAR','CAPTURE_NAME']})
title=json.loads((U/'candidates/title-menu-v1/manifest.json').read_text(encoding='utf-8'))
for e in title['entries']:
 b=(U/'candidates/title-menu-v1/payloads'/e['entry']).read_bytes();assert sha(b)==e['output_sha256'];fp[e['entry']]=b
for n,b in fp.items():
 if b!=fp0[n]:put(O/'payloads/fastdata.arc'/n,b)
fastout=O/'fastdata.arc';put(fastout,fast.rebuild(fp));archive_reports=[]
for path,src,desired,original in [(scenario,a,payloads,originals),(fastout,fast,fp,fp0)]:
 parsed=Arc(path);assert [e['name'] for e in parsed.entries]==[e['name'] for e in src.entries];changed=[]
 with path.open('rb') as stream:
  for e in parsed.entries:
   stream.seek(e['offset']);v=stream.read(e['size']);assert v==desired[e['name']]
   if v!=original[e['name']]:changed.append({'entry':e['name'],'source_sha256':sha(original[e['name']]),'output_sha256':sha(v)})
 assert {e['entry'] for e in changed}=={n for n in desired if desired[n]!=original[n]}
 archive_reports.append({'archive':path.name,'source_sha256':sha(src.path.read_bytes()),'output_sha256':sha(path.read_bytes()),'entries':len(parsed.entries),'changed':changed,'unchanged_payloads_identical':True,'entry_order_names_hashes_preserved':True})
for rec in rows:
 if rec['id'] not in deferred:rec['status']='static_pass_runtime_pending'
dump(U/'translation/ui-semantic-map.json',{'translator_model':'Codex internal','records':rows,'untranslated_nonsemantic':[{k:r[k] for k in ['id','source','context']} for r in source['records'] if r['id'] not in targets]})
manifest={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','status':'partial_ui_static_pass_runtime_pending','semantic_authored':len(rows),'semantic_included':len(rows)-len(deferred),'deferred_native_diagnostic_ids':sorted(deferred),'archives':archive_reports,'scripts':script_reports,'support_changes':support,'font':{'family':FAMILY,'source_sha256':sha(fpath.read_bytes()),'output_sha256':sha(fontout.read_bytes()),'mapping_base_sha256':sha(centralbytes),'map_sha256':sha((U/'translation/hangul-cp932-ui-map.json').read_bytes()),'mapped_glyphs':len(mapping),'additions':len(mapping)-len(base_mapping),'persisted_cmap_pass':True,'runtime_pass':False},'raster_manifest':'../title-menu-v1/manifest.json','raster_entries':9,'runtime_pass':False,'remaining':['Most raster UI other than titles','Native PE menus/dialogs/diagnostics','Timeline CSV and dynamic-name audit','UI runtime state matrix','OP/ED after UI gate']}
dump(O/'manifest.json',manifest)
print(json.dumps({'semantic_included':len(rows)-len(deferred),'deferred_diagnostics':len(deferred),'changed_entries':{x['archive']:len(x['changed']) for x in archive_reports},'font_additions':len(mapping)-len(base_mapping),'out':str(O)},ensure_ascii=False))
