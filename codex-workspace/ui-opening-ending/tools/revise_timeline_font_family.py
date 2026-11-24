"""Distinct family identity for the expanded font, preserving all glyphs and mapping."""
from pathlib import Path
import json,hashlib,shutil,sys
from fontTools.ttLib import TTFont
U=Path(__file__).resolve().parents[1];src=U/'candidates/timeline-csv-v2';out=U/'candidates/timeline-csv-v3';assert not out.exists();shutil.copytree(src,out)
sha=lambda b:hashlib.sha256(b).hexdigest()
p=out/'font/ReconquistaUIKR.otf';f=TTFont(p,recalcTimestamp=False);cff=f['CFF '].cff;top=cff.topDictIndex[0];prior_cmaps=[(t.platformID,t.platEncID,t.format,dict(t.cmap)) for t in f['cmap'].tables];prior_tables={tag:f.getTableData(tag) for tag in ['OS/2','hmtx','vmtx']}
family='Reconquista UI K2';ps='ReconquistaUIK2-Regular';full=family+' Regular';names={1:family,3:ps+'-20261023',4:full,6:ps,16:family}
for rec in f['name'].names:
 if rec.nameID in names:rec.string=names[rec.nameID].encode(rec.getEncoding())
for nid,val in names.items():f['name'].setName(val,nid,3,1,0x409)
cff.fontNames=[ps];top.FullName=full;top.FamilyName=family;top.FontName=ps;f.save(p);g=TTFont(p);assert [(t.platformID,t.platEncID,t.format,dict(t.cmap)) for t in g['cmap'].tables]==prior_cmaps;assert all(g.getTableData(k)==v for k,v in prior_tables.items())
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
m=json.loads((out/'manifest.json').read_text(encoding='utf-8'));assert program_hash(g)==m['font']['glyph_program_hash'];m['font'].update(output_sha256=sha(p.read_bytes()),font_identity_revision=ps,family=family,new_gdi_pass=False);m['font'].pop('family_unchanged',None);m['inherits_static_evidence']='../timeline-csv-v2/manifest.json';m['font_identity_reason']='New explicit family for reliable DEFAULT_CHARSET and SHIFTJIS_CHARSET selection. Consumer strings require same-length KR→K2 replacement. Existing 804 mappings, glyph programs, metrics and charset unchanged.';(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'new_font':sha(p.read_bytes()),'family':family}),flush=True)
sys.path.insert(0,str(U/'tools'));import check_gdi_ui
mapping=json.loads((U/'translation/hangul-cp932-ui-timeline-map.json').read_bytes())['mapping'];check_gdi_ui.run(p,family=family,reportname='font-gdi-timeline-v3-family.json',mapping_override=mapping)
m['font'].update(new_gdi_pass=True,new_gdi_report='reports/font-gdi-timeline-v3-family.json',gdi_scope_reason='Family selection changed for all mapped text; all804 directly affected glyphs checked once in both requested charset paths.');(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
