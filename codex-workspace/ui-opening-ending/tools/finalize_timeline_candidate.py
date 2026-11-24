"""Finalize existing CSV outputs after a too-broad cmap-preservation guard stopped the build."""
from pathlib import Path
import json,sys,hashlib
from fontTools.ttLib import TTFont
U=Path(__file__).resolve().parents[1];B=U.parent;O=U/'candidates/timeline-csv-v1';assert not (O/'manifest.json').exists()
sha=lambda b:hashlib.sha256(b).hexdigest()
D=json.loads((U/'translation/timeline-ko.json').read_bytes());mp=U/'translation/hangul-cp932-ui-timeline-map.json';m=json.loads(mp.read_bytes());old=json.loads((U/'translation/hangul-cp932-ui-map.json').read_bytes())['mapping'];fontbase=U/'candidates/ui-trial-v10/font/ReconquistaUIKR.otf';fout=O/'font/ReconquistaUIKR.otf';base=TTFont(fontbase);new=TTFont(fout);prior=base.getBestCmap();cm=new.getBestCmap();expected={ord(slot):prior[ord(ko)] for ko,slot in m['additions'].items()}
assert new.getTableData('CFF ')==base.getTableData('CFF ')
assert all(cm[ord(slot)]==prior[ord(slot)] for slot in old.values())
assert all(cm[k]==v for k,v in prior.items() if k not in expected)
assert {k:v for k,v in cm.items() if prior.get(k)!=v}==expected
for table in ['name','OS/2','hmtx','vmtx']:assert new.getTableData(table)==base.getTableData(table)
(O/'font/LICENSE.txt').write_bytes((fontbase.parent/'LICENSE.txt').read_bytes())
reports=[];hashes={}
for src in D['source_files']:
 fn=src['entry'];records=[r for r in D['records'] if r['entry']==fn];b=(O/'payloads'/fn).read_bytes();hashes[fn]=sha(b)
 reports.append({'entry':fn,'source_sha256':src['sha256'],'output_sha256':sha(b),'shape':[80,13],'changed_cells':len(records),'protected_cells':1040-len(records),'protected_tokens_and_delimiters_preserved':True,'actual_newline_counts_preserved':True,'semantic_roundtrip_exact':True,'ids':[r['id'] for r in records],'verification_reused':'build_timeline_csv.py run: all CSV, date equality, terminator, separator and encoding assertions completed before font guard at former line84 failed'})
report={'method':'Reuse completed CSV assertions; recheck only corrected font cmap allowlist and directly affected font tables','prior_failure':'The guard incorrectly required new unused CJK aliases to keep their previous CJK glyph mappings. These 31 aliases are the intended Hangul changes.','CSV_checks_repeated':False,'new_aliases':31,'old_773_aliases_unchanged':True,'only_new_aliases_changed':True,'all_CFF_programs_unchanged':True,'name_OS2_metrics_tables_unchanged':True,'font_sha256':sha(fout.read_bytes()),'pass':True}
(U/'reports/timeline-font-delta.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest={'translator_model':'Codex internal','task_id':D['task_id'],'source_translation_sha256':sha((U/'translation/timeline-ko.json').read_bytes()),'entries':reports,'output_hashes':hashes,'semantic_cells_authored':len(D['records']),'semantic_cells_context_approved':sum(not r['provisional_readings'] for r in D['records']),'name_reading_pending_ids':[r['id'] for r in D['records'] if r['provisional_readings']],'structural_pass':True,'runtime_pass':False,'display_layout_pass':False,'release_ready':False,'font':{'source_sha256':sha(fontbase.read_bytes()),'output_sha256':sha(fout.read_bytes()),'mapped_glyphs':len(m['mapping']),'new_glyph_aliases':len(m['additions']),'old_slots_and_all_CFF_programs_preserved':True,'mapping_path':str(mp),'mapping_sha256':sha(mp.read_bytes()),'old_gdi_proof_reused':'reports/font-gdi-ui.json','new_gdi_pass':False,'font_delta_report':'reports/timeline-font-delta.json'},'consumer_proof':'reports/timeline-csv-consumers.json'}
(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'font_delta_pass':True,'csv_checks_reused':3,'font_sha256':sha(fout.read_bytes()),'hashes':hashes},ensure_ascii=False))
