"""Build frozen recovery snapshot with isolated font registry; no mutation of worker snapshots."""
from pathlib import Path
import json,sys,struct,shutil,collections
import build_trial as b
from inspect_majiro import Arc,sha,dump
ROOT=b.ROOT
NAMES=json.loads((ROOT/'translation/integration/recovery-full-20261023-v1/names.json').read_text(encoding='utf-8'))['mapping']

def isolated_font_mapping(targets,registry):
    catalog=ROOT/'localization/catalog/catalog.jsonl'
    used=set()
    with catalog.open(encoding='utf-8') as f:
        for line in f:used.update(json.loads(line)['source'])
    for p in (ROOT/'research/extracted/fastdata').glob('*.cfg'):
        used.update(p.read_bytes().decode('cp932'))
    for p in (ROOT/'research/extracted/scenario').glob('*.csv'):
        used.update(p.read_bytes().decode('cp932'))
    needed={c for text in targets for c in text if '\uac00'<=c<='\ud7a3'}
    # Preserve unsupported display punctuation exactly, using the same proven glyph path.
    for c in {c for text in targets for c in text}:
        try: roundtrips=c.encode('cp932').decode('cp932')==c
        except UnicodeError: roundtrips=False
        if not roundtrips: needed.add(c)
    registry=Path(registry)
    mappings=json.loads(registry.read_text(encoding='utf-8'))['mapping'] if registry.exists() else {}
    occupied=set(mappings.values()); assert len(occupied)==len(mappings)
    candidates=[]
    for lead in list(range(0xe0,0xf0))+list(range(0x88,0xa0)):
        for trail in range(0x40,0xfd):
            if trail==0x7f:continue
            b=bytes([lead,trail])
            try:c=b.decode('cp932')
            except UnicodeError:continue
            if len(c)==1 and '\u3400'<=c<='\u9fff' and c.encode('cp932')==b and c not in used and c not in occupied:candidates.append(c)
    for c in sorted(needed-set(mappings)):
        assert candidates,'No safe unused CP932 CJK slots'
        mappings[c]=candidates.pop(0)
    assert not (set(mappings.values())&used),'Font mapping collides with original text'
    dump(registry,{'translator_model':'Codex internal','algorithm':'stable Korean syllables and non-CP932 display characters to globally unused round-trip CP932 CJK; lead 88-9F/E0-EF; no PUA','mapping':mappings,'remaining_safe_slots':len(candidates)})
    return mappings

def main():
    label=sys.argv[1];folder=ROOT/'translation/integration'/label;d=json.loads((folder/'integrated-targets.json').read_text(encoding='utf-8'));assert label=='recovery-full-20261023-v1';assert sha((folder/'integrated-targets.json').read_bytes())==json.loads((folder/'integration-report.json').read_text(encoding='utf-8'))['snapshot_sha256']
    out=ROOT/'builds'/('integrated-'+label);assert not (out/'manifest.json').exists(),'Do not replace an existing build'
    out.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(folder/'fontmap-seed.json',out/'font-map.json')
    mapping=isolated_font_mapping([r['target'] for r in d['records']+d['inline_records']]+list(NAMES.values()),out/'font-map.json')
    revision=sha(json.dumps(mapping,sort_keys=True,ensure_ascii=False).encode())[:8]
    b.FAMILY='Reconquista KR '+revision;b.SERIF_FAMILY='Reconquista KR Serif '+revision
    assert len(b.SERIF_FAMILY)<32
    inverse={v:k for k,v in mapping.items()}
    def encode(t):
        s=''.join(mapping.get(c,c) for c in t);assert s.encode('cp932').decode('cp932')==s
        assert ''.join(inverse.get(c,c) for c in s)==t
        return s
    fd=out/'font';fd.mkdir(exist_ok=True)
    fonts=[b.build_font(fd/'ReconquistaKR.otf',mapping),b.build_font(fd/'ReconquistaKRSerif.otf',mapping,True)]
    shutil.copyfile(ROOT/'research/fonts/LICENSE',fd/'LICENSE.txt')
    a=Arc(ROOT/'research/disc/scenario.arc');assert sha(a.path.read_bytes())==b.EXPECTED_SCENARIO
    originals={e['name']:(ROOT/'research/extracted/scenario'/e['name']).read_bytes() for e in a.entries}
    payloads=originals.copy();reports={};groups=collections.defaultdict(list)
    for r in d['records']:groups[r['id'].split('::')[0]].append((r,'text'))
    for r in d['inline_records']:groups[r['id'].split('::')[0]].append((r,'ldstr'))
    for name,records in groups.items():
        assert sha(originals[name])==d['source_files'][name]
        source,_=b.decode(originals[name]);replacements={}
        for r,opcode in records:
            index=int(r['id'].split('::')[1]);ins=source.instructions[index]
            assert ins.opcode.mnemonic==opcode and ins.string==r['source'],r['id']
            assert index not in replacements
            replacements[index]=b.string_ins(opcode,encode(r['target']))
        for i,x in enumerate(source.instructions):
            if x.opcode.mnemonic=='ldstr' and x.string=='ＭＳ 明朝':
                serif_consumers={b.OPENING:{6318,6347,6364,6397,6414,6445,6467,6498}, '00_レコンキスタ_start_3.mjo':{16776,16801,16898,16926,16973,17403,17415,17427}, 'テスト用.mjo':{1033,1045,1057}}
                assert i in serif_consumers.get(name,set()),(name,i)
                assert source.instructions[i+1].is_syscall and source.instructions[i+1].hash==0x06b3c8ac
                replacements[i]=b.string_ins('ldstr',b.SERIF_FAMILY)
        payloads[name],reports[name]=b.rewrite(originals[name],replacements)
    loader,raw=b.decode(originals['load_sysdata.mjo'])
    store=next(x for x in loader.instructions if x.opcode.mnemonic=='st.s' and x.hash==0x391053c5)
    force=b.string_ins('ldstr',b.FAMILY)+raw[store.offset:store.offset+store.size]+b.op('pop')
    hook=b.string_ins('ldstr',r'font\ReconquistaKR.otf')+b.op('syscallp')+struct.pack('<IH',0x877445ce,1)+b.string_ins('ldstr',r'font\ReconquistaKRSerif.otf')+b.op('syscallp')+struct.pack('<IH',0x877445ce,1)+force
    index=next(i for i,x in enumerate(loader.instructions) if x.offset==0x0f)
    payloads['load_sysdata.mjo'],reports['load_sysdata.mjo']=b.rewrite(originals['load_sysdata.mjo'],insertions={index:hook})
    con,raw=b.decode(originals['console.mjo']);byoff={x.offset:x for x in con.instructions}
    load=raw[0x31d3:0x31d3+byoff[0x31d3].size];store=raw[0x31bf:0x31bf+byoff[0x31bf].size]
    namehook=b''
    for jp,ko in NAMES.items():
        for display in ([jp,jp[0]+'\u3000'+jp[1]] if len(jp)==2 else [jp]):
            body=b.string_ins('ldstr',encode(ko))+store+b.op('pop')
            namehook+=load+b.string_ins('ldstr',display)+b.op('ceq.s')+b.op('brfalse')+struct.pack('<i',len(body))+body
    at=next(i for i,x in enumerate(con.instructions) if x.offset==0x323e)
    payloads['console.mjo'],reports['console.mjo']=b.rewrite(originals['console.mjo'],insertions={at:namehook})
    cfg,_=b.decode(originals['config.mjo']);fixed={i:b.op('pop')+b.string_ins('ldstr',b.FAMILY) for i,x in enumerate(cfg.instructions) if x.opcode.mnemonic=='st.s' and x.hash==0x391053c5};assert len(fixed)==2
    payloads['config.mjo'],reports['config.mjo']=b.rewrite(originals['config.mjo'],insertions=fixed)
    (out/'scenario.arc').write_bytes(a.rebuild(payloads))
    modified=sorted(n for n in payloads if payloads[n]!=originals[n]);assert modified==sorted(reports)
    ar=Arc(out/'scenario.arc')
    with ar.path.open('rb') as f:
        for e in ar.entries:f.seek(e['offset']);assert f.read(e['size'])==payloads[e['name']]
    fast=Arc(ROOT/'research/disc/fastdata.arc');fp={e['name']:(ROOT/'research/extracted/fastdata'/e['name']).read_bytes() for e in fast.entries}
    cfg=fp['sysdata.cfg'];needle='ＭＳ ゴシック, 0'.encode('cp932');assert cfg.count(needle)==2
    fp['sysdata.cfg']=cfg.replace(needle,(b.FAMILY+', 0').encode('ascii'));(out/'fastdata.arc').write_bytes(fast.rebuild(fp))
    fr=Arc(out/'fastdata.arc')
    with fr.path.open('rb') as f:
        for e in fr.entries:f.seek(e['offset']);assert f.read(e['size'])==fp[e['name']]
    manifest={'status':'static_pass_runtime_pending','translator_model':'Codex internal','snapshot':label,'snapshot_sha256':sha((ROOT/'translation/integration'/label/'integrated-targets.json').read_bytes()),'translated_units':d['units'],'translated_text_fields':d['text_fields'],'translated_inline_fields':d['inline_fields'],'coverage':d['coverage'],'all_game_units':47021,'font':fonts[0],'serif_font':fonts[1],'modified_scenario_entries':modified,'modified_fastdata_entries':['sysdata.cfg'],'script_validation':reports,'root_review':d['root_review'],'source_archive_sha256':b.EXPECTED_SCENARIO,'original_exe_sha256':'cd1c38ac20d9e502fbc58b7392ca77ec32e3d56f90d988580a3cf58cb6f95146','outputs':{p.name:sha(p.read_bytes()) for p in out.glob('*.arc')},'runtime':{'normal_start':False,'korean_dialogue':False,'names':False,'long_lines':False,'full_screen':False,'ruby':False},'limits':['Only the listed IDs are translated.','Original Japanese UI remains; UI project is separate.','Runtime and complete route playthrough pending.','Original Japanese executable basename required; executable unmodified.']}
    manifest.update(font_map='font-map.json',font_map_sha256=sha((out/'font-map.json').read_bytes()),body_pending=d['pending_at_snapshot'],read_history_compatibility='Translated choice strings change their CRC read-history keys; old read/skip state may not transfer for choices. Saves and story branching untouched.');dump(out/'manifest.json',manifest);dump(ROOT/'reports/latest-recovery-build.json',{'path':str(out),**manifest})
    print(json.dumps({'path':str(out),'units':d['units'],'fields':d['text_fields'],'inline':d['inline_fields'],'glyphs':len(mapping),'root_edits':len(d['root_review']['changes']),'modified_scripts':len(modified)},ensure_ascii=False))
if __name__=='__main__':main()
