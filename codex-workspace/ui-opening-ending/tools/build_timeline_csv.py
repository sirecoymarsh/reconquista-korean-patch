"""Build isolated CSV payloads, preserve control cells and extend frozen UI font only."""
from pathlib import Path
import json,io,csv,sys,hashlib,unicodedata,datetime
from fontTools.ttLib import TTFont
U=Path(__file__).resolve().parents[1];B=U.parent;sys.path.insert(0,str(B/'tools'));from inspect_majiro import Arc,sha
D=json.loads((U/'translation/timeline-ko.json').read_text(encoding='utf-8'));assert all(r['status'].startswith('context_pass') for r in D['records'])
O=U/'candidates/timeline-csv-v1';assert not O.exists()
oldpath=U/'translation/hangul-cp932-ui-map.json';oldobj=json.loads(oldpath.read_bytes());mapping=oldobj['mapping'].copy();old=mapping.copy();centralbytes=(B/'translation/hangul-cp932-map.json').read_bytes();central=json.loads(centralbytes)['mapping']
used=set()
for line in (B/'localization/catalog/catalog.jsonl').open(encoding='utf-8'):used.update(json.loads(line)['source'])
for folder,pattern in [('fastdata','*.cfg'),('scenario','*.csv')]:
 for p in (B/'research/extracted'/folder).glob(pattern):used.update(p.read_bytes().decode('cp932'))
for line in (B/'research/extracted/fastdata/majiro.env').read_bytes().decode('cp932').splitlines():
 if not line.lstrip().startswith('//'):used.update(line.split('//',1)[0])
assert len(set(mapping.values()))==len(mapping) and not used&set(mapping.values())
occupied=set(mapping.values())|set(central.values());available=[]
for lead in list(range(0xe0,0xf0))+list(range(0x88,0xa0)):
 for trail in range(0x40,0xfd):
  if trail==0x7f:continue
  b=bytes([lead,trail])
  try:c=b.decode('cp932')
  except UnicodeError:continue
  if len(c)==1 and '\u3400'<=c<='\u9fff' and c.encode('cp932')==b and c not in used|occupied:available.append(c)
needed={c for r in D['records'] for c in r['target'] if '가'<=c<='힣'}
for c in sorted(needed-set(mapping)):mapping[c]=available.pop(0)
additions={k:v for k,v in mapping.items() if k not in old};inverse={v:k for k,v in mapping.items()};assert len(inverse)==len(mapping)
def enc(t):
 s=''.join(mapping.get(c,c) for c in t);b=s.encode('cp932');assert b.decode('cp932')==s and ''.join(inverse.get(c,c) for c in s)==t;return b
for d in ['payloads','font']:(O/d).mkdir(parents=True,exist_ok=True)
mapobj={'translator_model':'Codex internal','base_map':str(oldpath),'base_sha256':sha(oldpath.read_bytes()),'mapping':mapping,'additions':additions,'prior_slots_preserved':True,'central_snapshot_sha256':sha(centralbytes),'central_file_modified':False,'central_current_slots_avoided':True,'integration':'Reallocate from semantic Unicode records during final central integration. Never overwrite central mapping.'}
mp=U/'translation/hangul-cp932-ui-timeline-map.json';mp.write_text(json.dumps(mapobj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(U/'translation/hangul-cp932-timeline-additions.json').write_text(json.dumps({'mapping':additions},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Token spans preserve every unchanged cell and separator, including quoted actual-LF cells.
def tokens(text):
 result=[];start=0;i=0;quoted=False
 while i<len(text):
  ch=text[i]
  if ch=='"':
   if quoted and i+1<len(text) and text[i+1]=='"':i+=2;continue
   quoted=not quoted
  elif not quoted and ch in ',\r\n':
   result.append((start,i));i+=2 if ch=='\r' and i+1<len(text) and text[i+1]=='\n' else 1;start=i;continue
  i+=1
 assert not quoted
 if start<len(text):result.append((start,len(text)))
 return result
reports=[];out_hashes={};byfile={s['entry']:{} for s in D['source_files']}
for r in D['records']:byfile[r['entry']][(r['row'],r['column'])]=r
outrows={}
for src in D['source_files']:
 fn=src['entry'];data=(B/'research/extracted/scenario'/fn).read_bytes();assert sha(data)==src['sha256'];text=data.decode('cp932');rows=list(csv.reader(io.StringIO(text,newline='')));spans=tokens(text);assert len(spans)==1040
 chunks=[];last=0;changed=[];protected=0
 for idx,(a,b) in enumerate(spans):
  r,c=divmod(idx,13);token=text[a:b];value=next(csv.reader(io.StringIO(token,newline='')))[0] if token else '';assert value==rows[r][c]
  chunks.append(text[last:a].encode('cp932'));rec=byfile[fn].get((r,c))
  if rec:
   assert rec['source']==value;target=rec['target'];assert target.count('\n')==value.count('\n');raw=enc(target)
   if token.startswith('"'):raw=b'"'+raw+b'"'
   else:assert all(x not in raw for x in [b',',b'\n',b'\r',b'"'])
   changed.append(rec['id'])
  else:raw=token.encode('cp932');protected+=1
  chunks.append(raw);last=b
 chunks.append(text[last:].encode('cp932'));blob=b''.join(chunks);p=O/'payloads'/fn;p.write_bytes(blob);persisted=p.read_bytes();assert persisted==blob
 check=list(csv.reader(io.StringIO(blob.decode('cp932'),newline='')));assert len(check)==80 and all(len(r)==13 for r in check)
 decoded=[[''.join(inverse.get(c,c) for c in v) for v in row] for row in check];outrows[fn]=check
 for r in range(80):
  for c in range(13):assert decoded[r][c]==(byfile[fn][(r,c)]['target'] if (r,c) in byfile[fn] else rows[r][c])
 changedspans=tokens(blob.decode('cp932'));assert len(changedspans)==len(spans)
 for idx,((a,b),(na,nb)) in enumerate(zip(spans,changedspans)):
  if divmod(idx,13) not in byfile[fn]:assert text[a:b].encode('cp932')==blob.decode('cp932')[na:nb].encode('cp932')
 assert blob.count(b'\r\n')==data.count(b'\r\n') and blob.count(b'\n')==data.count(b'\n')
 # The custom reader strips leading ASCII; all meaningful target cells begin at >= U+3000 in the encoded CP932 view.
 for (r,c),rec in byfile[fn].items():
  if not fn.startswith('exec_'):assert ord(enc(rec['target']).decode('cp932')[0])>=0x3000,(fn,r,c)
 out_hashes[fn]=sha(blob);reports.append({'entry':fn,'source_sha256':sha(data),'output_sha256':sha(blob),'shape':[80,13],'changed_cells':len(changed),'protected_cells':protected,'protected_tokens_and_delimiters_preserved':True,'actual_newline_counts_preserved':True,'semantic_roundtrip_exact':True,'ids':changed})
# Base/alt formatting is 12 characters for dates; our date cells fit without padding. EXEC must compare equal after fullwidth normalization.
ns=list(outrows)
for r in range(80):
 dates=[outrows[n][r][0] for n in ns];assert dates[0]==dates[1]==dates[2];assert dates[0]=='[EOF]' or len(dates[0])<=12
# Font: preserve prior CFF glyph programs and all old slot mappings, append only new codepoint aliases.
fontbase=U/'candidates/ui-trial-v10/font/ReconquistaUIKR.otf';assert sha(fontbase.read_bytes())=='7703661cd363a137fc025db1d3454980e75021a053cf5693aa737a40ff0bd61f';font=TTFont(fontbase,recalcTimestamp=False);cm=font.getBestCmap();cff=font.getTableData('CFF ');prior=dict(cm);expected={ord(slot):cm[ord(ko)] for ko,slot in additions.items()}
for table in font['cmap'].tables:
 if table.isUnicode():table.cmap.update(expected)
fout=O/'font/ReconquistaUIKR.otf';font.save(fout);check=TTFont(fout);newcm=check.getBestCmap();assert check.getTableData('CFF ')==cff;assert all(newcm[k]==v for k,v in prior.items() if k not in expected);assert all(newcm[k]==v for k,v in expected.items());assert {k:v for k,v in newcm.items() if prior.get(k)!=v}==expected
(O/'font/LICENSE.txt').write_bytes((U/'candidates/ui-trial-v10/font/LICENSE.txt').read_bytes())
manifest={'translator_model':'Codex internal','task_id':D['task_id'],'source_translation_sha256':sha((U/'translation/timeline-ko.json').read_bytes()),'entries':reports,'output_hashes':out_hashes,'semantic_cells_authored':len(D['records']),'semantic_cells_context_approved':sum(not r['provisional_readings'] for r in D['records']),'name_reading_pending_ids':[r['id'] for r in D['records'] if r['provisional_readings']],'structural_pass':True,'runtime_pass':False,'display_layout_pass':False,'release_ready':False,'font':{'source_sha256':sha(fontbase.read_bytes()),'output_sha256':sha(fout.read_bytes()),'mapped_glyphs':len(mapping),'new_glyph_aliases':len(additions),'old_slots_and_all_CFF_programs_preserved':True,'mapping_path':str(mp),'mapping_sha256':sha(mp.read_bytes()),'old_gdi_proof_reused':'reports/font-gdi-ui.json','new_gdi_pass':False},'consumer_proof':'reports/timeline-csv-consumers.json'}
(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'entries':3,'semantic_cells':len(D['records']),'name_reading_pending':manifest['name_reading_pending_ids'],'new_glyphs':len(additions),'total_glyphs':len(mapping),'hashes':out_hashes},ensure_ascii=False))
