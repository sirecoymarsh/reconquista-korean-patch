"""Build only a frozen, coordinator-reviewed + root-integrated snapshot."""
from pathlib import Path
import json,sys,struct,shutil,collections
import build_trial as b
from inspect_majiro import Arc,sha,dump
ROOT=b.ROOT
NAMES={**b.NAMES,'男１':'남자 1','男２':'남자 2','男３':'남자 3','男達':'남자들','汐見':'시오미','紅葉':'모미지','村人':'마을 사람','上条':'카미조','教師':'교사'}

def canonical_character_names(text):
    for old, new in {'가미조': '카미조', '다무라': '타무라', '가스가이': '카스가이', '게이고': '케이고', '도오루': '토오루', '도모코': '토모코', '가나야마': '카나야마'}.items():
        text=text.replace(old,new)
    return text

def integrate(label):
    folder=ROOT/'translation/integration'/label
    original=folder/'targets.json';d=json.loads(original.read_text(encoding='utf-8'))
    changes=[]
    allrecords=d['records']+d['inline_records'];byid={r['id']:r for r in allrecords}
    def fix(r,t,reason):
        if r['target']==t:return
        changes.append({'id':r['id'],'before':r['target'],'after':t,'reason':reason})
        r['target']=t;r['integration_editor']='Codex internal / root';r['integration_review']=reason
    for r in allrecords:
        t=canonical_character_names(r['target']).replace('미션 스쿨','미션스쿨')
        fix(r,t,'Cross-batch canonical surname 카미조; existing school term 미션스쿨')
    edits={
        'maho_14.mjo::000259':('똑똑.','Match same protagonist/source knocking SFX'),
        'kureha_05.mjo::000435':('그','Emphasis helper marks spaces; move separator to adjacent ordinary text'),
        'kureha_05.mjo::000437':(' 쿠레하가 아무 저항도 하지 않고,','Separator moved from emphasized body; concatenated text unchanged'),
        'kureha_05.mjo::001666':('흔적','Emphasis helper marks spaces; move separator to preceding ordinary text'),
        'kureha_05.mjo::001664':('그래, 그곳에는 쿠레하의 ','Separator moved from emphasized body; concatenated text unchanged'),
        '00_レコンキスタ_start_2.mjo::004595':('ＰＨＯＮＥ','Preserve full-width source body for ruby width calculation'),
        '00_レコンキスタ_start_2.mjo::004600':('ＨＯＭＥ','Preserve full-width source body for ruby width calculation'),
    }
    for k,(v,reason) in edits.items():
        if k in byid:fix(byid[k],v,reason)
    d['root_review']={'translator_model':'Codex internal','source_snapshot_sha256':sha(original.read_bytes()),'review_agents':['review_opening_early','review_opening_late'],'new_inline_consumer_verified':12,'new_direct_font_consumers':0,'canonical_terms':{'上条':'카미조','ミッションスクール':'미션스쿨'},'changes':changes,'name_map':NAMES,'runtime_pending':True}
    d['stage']='root consistency reviewed; build and runtime pending'
    dump(folder/'integrated-targets.json',d)
    return d

def main():
    label=sys.argv[1];d=integrate(label)
    out=ROOT/'builds'/('integrated-'+label);assert not (out/'manifest.json').exists(),'Do not replace an existing build'
    out.mkdir(parents=True,exist_ok=True)
    mapping=b.font_mapping([r['target'] for r in d['records']+d['inline_records']]+list(NAMES.values()))
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
                serif_consumers={b.OPENING:{6318,6347,6364,6397,6414,6445,6467,6498}, '00_レコンキスタ_start_3.mjo':{16776,16801,16898,16926,16973,17403,17415,17427}}
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
    dump(out/'manifest.json',manifest);dump(ROOT/'reports/latest-build.json',{'path':str(out),**manifest})
    print(json.dumps({'path':str(out),'units':d['units'],'fields':d['text_fields'],'inline':d['inline_fields'],'glyphs':len(mapping),'root_edits':len(d['root_review']['changes']),'modified_scripts':len(modified)},ensure_ascii=False))
if __name__=='__main__':main()
