"""Give an extended font a distinct face identity while preserving the family used by scripts."""
from pathlib import Path
import json,hashlib,shutil,sys
from fontTools.ttLib import TTFont
U=Path(__file__).resolve().parents[1];src=U/'candidates/timeline-csv-v1';out=U/'candidates/timeline-csv-v2';assert not out.exists();shutil.copytree(src,out)
sha=lambda b:hashlib.sha256(b).hexdigest()
p=out/'font/ReconquistaUIKR.otf';f=TTFont(p,recalcTimestamp=False);cff=f['CFF '].cff;top=cff.topDictIndex[0]
def program_hash(font):
 c=font['CFF '].cff;t=c.topDictIndex[0];h=hashlib.sha256()
 def add(label,cs):
  if cs.bytecode is None:cs.compile()
  b=cs.bytecode;h.update(label.encode()+b'\0'+len(b).to_bytes(4,'little')+b)
 for name in font.getGlyphOrder():add(name,t.CharStrings[name])
 for i,cs in enumerate(c.GlobalSubrs):add('global'+str(i),cs)
 for i,fd in enumerate(t.FDArray):
  for j,cs in enumerate(getattr(fd.Private,'Subrs',[])):add(f'local{i}:{j}',cs)
 return h.hexdigest()
prior_program=program_hash(f);prior_cmaps=[(t.platformID,t.platEncID,t.format,dict(t.cmap)) for t in f['cmap'].tables];prior_tables={tag:f.getTableData(tag) for tag in ['OS/2','hmtx','vmtx']}
ps='ReconquistaUIKR-Regular-TimelineV1';full='Reconquista UI KR Timeline V1';names={3:ps+'-20261023',4:full,6:ps}
for rec in f['name'].names:
 if rec.nameID in names:rec.string=names[rec.nameID].encode(rec.getEncoding())
for nid,val in names.items():f['name'].setName(val,nid,3,1,0x409)
cff.fontNames=[ps];top.FullName=full;top.FontName=ps
f.save(p);g=TTFont(p);assert program_hash(g)==prior_program;assert [(t.platformID,t.platEncID,t.format,dict(t.cmap)) for t in g['cmap'].tables]==prior_cmaps;assert all(g.getTableData(k)==v for k,v in prior_tables.items())
m=json.loads((out/'manifest.json').read_text(encoding='utf-8'));m['font'].update(output_sha256=sha(p.read_bytes()),font_identity_revision=ps,family_unchanged='Reconquista UI KR',glyph_program_hash=prior_program,new_gdi_pass=False);m['inherits_static_evidence']='../timeline-csv-v1/manifest.json';m['font_identity_reason']='Distinct PostScript/unique/full name for expanded cmap; keep requested family and every glyph program, metric, charset, and mapping unchanged.';(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'new_font':sha(p.read_bytes()),'glyph_program_hash':prior_program,'old_CSV_checks_reused':True}),flush=True)
sys.path.insert(0,str(U/'tools'));import check_gdi_ui
mapping=json.loads((U/'translation/hangul-cp932-timeline-additions.json').read_bytes())['mapping'];check_gdi_ui.run(p,family='Reconquista UI KR',reportname='font-gdi-timeline-v2-additions.json',mapping_override=mapping)
m['font'].update(new_gdi_pass=True,new_gdi_report='reports/font-gdi-timeline-v2-additions.json');(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
