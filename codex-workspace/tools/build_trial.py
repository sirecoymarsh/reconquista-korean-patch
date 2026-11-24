"""Hash-bound Majiro text trial builder. No executable changes, no external MT."""
from pathlib import Path
import sys, io, json, struct, hashlib, re, shutil, math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research/vendor/majiro-py/src'))
from mjotool import MjoScript
from mjotool.crypt import crypt32
from mjotool.opcodes import Opcode
from fontTools.ttLib import TTFont
from inspect_majiro import Arc,sha,dump
from translation_context import context

FAMILY='Reconquista KR'
OPENING='00_レコンキスタ_start.mjo'
EXPECTED_SCENARIO='95b6592ce3d9f4f94a4051bbbc217e26fbb9c63586a4e0b5bcd9932f961aeb99'
SERIF_FAMILY='Reconquista KR Serif'
SECOND='00_レコンキスタ_start_2.mjo'
NAMES={'もみじ':'모미지','槙野':'마키노','暮葉':'쿠레하','麻咲':'마사키','義父':'장인','信哉':'신야','真帆子':'마호코','まほほ':'마호호','おばさん':'아주머니','まほママ':'마호 엄마','詩菜':'시이나'}

def remaining_deferred(chosen):
    result=[]
    for n in sorted((set(range(91,101))|set(range(210,270)))-set(chosen)):
        if result and result[-1][1]+1==n:result[-1][1]=n
        else:result.append([n,n])
    return result

def op(name):return struct.pack('<H',Opcode.fromname(name).value)
def string_ins(name,text):
    b=text.encode('cp932'); assert b'\0' not in b and len(b)<65534
    return op(name)+struct.pack('<H',len(b)+1)+b+b'\0'
def decode(b):
    s=MjoScript.disassemble_script(io.BytesIO(b))
    raw=b[s.bytecode_offset:]
    return s,crypt32(raw) if s.signature==s.SIGNATURE_ENCRYPTED else raw

def _rewrite(b,replacements=None,insertions=None):
    """Copy unmodified instructions verbatim, relocate only measured offsets."""
    replacements=replacements or {};insertions=insertions or {}
    s,raw=decode(b); old={x.offset for x in s.instructions}|{s.bytecode_size}
    assert set(replacements)<=set(range(len(s.instructions)))
    assert set(insertions)<=set(range(len(s.instructions)))
    chunks=[]; mapping={}; starts={}; pos=0
    for i,x in enumerate(s.instructions):
        mapping[x.offset]=pos
        prefix=insertions.get(i,b''); pos+=len(prefix); starts[x.offset]=pos
        chunk=replacements.get(i,raw[x.offset:x.offset+x.size])
        chunks.append([prefix,bytearray(chunk)]);pos+=len(chunk)
    mapping[s.bytecode_size]=pos
    jump_count=switch_count=0
    for i,x in enumerate(s.instructions):
        if x.opcode.encoding=='j':
            assert i not in replacements
            dest=x.offset+x.size+x.jump_offset;assert dest in old
            struct.pack_into('<i',chunks[i][1],2,mapping[dest]-(starts[x.offset]+x.size));jump_count+=1
        if x.switch_cases is not None:
            assert i not in replacements
            for j,off in enumerate(x.switch_cases):
                dest=x.offset+8+j*4+off; assert dest in old
                struct.pack_into('<i',chunks[i][1],4+j*4,mapping[dest]-(starts[x.offset]+8+j*4));switch_count+=1
    code=b''.join(p+bytes(c) for p,c in chunks)
    header=bytearray(b[:s.bytecode_offset]);struct.pack_into('<I',header,16,mapping[s.main_offset])
    for j,f in enumerate(s.functions):struct.pack_into('<I',header,28+j*8+4,mapping[f.offset])
    struct.pack_into('<I',header,len(header)-4,len(code))
    result=bytes(header)+(crypt32(code) if s.signature==s.SIGNATURE_ENCRYPTED else code)
    new,newraw=decode(result); lookup={x.offset:x for x in new.instructions}; boundaries=set(lookup)|{len(code)}
    assert new.main_offset==mapping[s.main_offset]
    assert [(x.name_hash,x.offset) for x in new.functions]==[(x.name_hash,mapping[x.offset]) for x in s.functions]
    for i,x in enumerate(s.instructions):
        y=lookup[starts[x.offset]]
        if i in replacements:
            assert newraw[y.offset:y.offset+len(replacements[i])]==replacements[i]
        elif x.opcode.encoding=='j':
            assert y.opcode==x.opcode
            assert y.offset+y.size+y.jump_offset==mapping[x.offset+x.size+x.jump_offset]
        elif x.switch_cases is not None:
            assert y.opcode==x.opcode
            assert [y.offset+8+j*4+d for j,d in enumerate(y.switch_cases)]==[mapping[x.offset+8+j*4+d] for j,d in enumerate(x.switch_cases)]
        else:assert newraw[y.offset:y.offset+y.size]==raw[x.offset:x.offset+x.size]
    for x in new.instructions:
        if x.opcode.encoding=='j':assert x.offset+x.size+x.jump_offset in boundaries
        if x.switch_cases is not None:assert all(x.offset+8+j*4+d in boundaries for j,d in enumerate(x.switch_cases))
    return result,{'source_sha256':sha(b),'output_sha256':sha(result),'original_instructions':len(s.instructions),'output_instructions':len(new.instructions),'replacement_indices':sorted(replacements),'insertion_indices':sorted(insertions),'relocated_jumps':jump_count,'relocated_switch_cases':switch_count,'validation':'unchanged raw instructions + original branch/function target equivalence + inserted branch boundaries'}

def rewrite(b,replacements=None,insertions=None):
    plan={'source':sha(b),'replacements':{str(k):v.hex() for k,v in (replacements or {}).items()},'insertions':{str(k):v.hex() for k,v in (insertions or {}).items()}}
    key=sha(json.dumps(plan,sort_keys=True,separators=(',',':')).encode())
    cache=ROOT/'build-cache/mjo';cache.mkdir(parents=True,exist_ok=True)
    meta=cache/(key+'.json');payload=cache/(key+'.mjo')
    if meta.exists() and payload.exists():
        saved=json.loads(meta.read_text(encoding='utf-8'));data=payload.read_bytes()
        assert sha(data)==saved['report']['output_sha256']
        return data,{**saved['report'],'verification_reused_from':saved['verified_artifact']}
    data,report=_rewrite(b,replacements,insertions)
    payload.write_bytes(data);dump(meta,{'report':report,'verified_artifact':str(payload)})
    return data,report

def read_translation(prefix='opening'):
    units=json.loads((ROOT/f'translation/{prefix}-source.json').read_text(encoding='utf-8'))['units']
    targets={}; records=[]; chosen=[]
    for path in sorted((ROOT/'translation').glob(f'{prefix}-ko-*.tsv')):
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            number,target=line.split('\t',1);number=int(number);assert number not in chosen
            unit=units[number-1];fields=[f for f in unit['fields'] if f['role']=='text'];parts=target.split(' || ')
            assert len(fields)==len(parts),(number,len(fields),len(parts))
            for f,t in zip(fields,parts):
                assert t.strip() and '\x00' not in t
                targets[f['index']]=t
                records.append({'id':f['id'],'unit':unit['unit'],'source':f['source'],'target':t,'speaker':unit['speaker'],'translator_model':'Codex internal','provenance':'primary task, 2026-10-22','status':'context_reviewed_static_checked_runtime_pending','context':context(prefix,number,unit)})
            chosen.append(number)
    assert chosen==sorted(set(chosen)),chosen
    if prefix=='opening':assert chosen==list(range(1,max(chosen)+1)),chosen
    return units,targets,records,chosen

def font_mapping(targets):
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
    registry=ROOT/'translation/hangul-cp932-map.json'
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

def build_font(out,mapping,serif=False):
    family=SERIF_FAMILY if serif else FAMILY
    ps=family.replace(' ','')+'-Regular'
    source=ROOT/'research/fonts'/('NotoSerifCJKkr-Regular.otf' if serif else 'NotoSansCJKkr-Regular.otf')
    assert sha(source.read_bytes())==('77b4b741f864d27f15e90f275b17106dde90b2ad28f82bab72dc95805db5fb42' if serif else '6bcb2a0703aa137e874fc2dffa85f6c21ba9a67fa329e81b8c801663af7e992a')
    font=TTFont(source,recalcTimestamp=False);cmap=font.getBestCmap(); expected={}
    for hangul,code in mapping.items():
        glyph=cmap.get(ord(hangul));assert glyph and glyph!='.notdef'
        assert glyph in font['CFF '].cff.topDictIndex[0].CharStrings
        expected[ord(code)]=glyph
    for table in font['cmap'].tables:
        if table.isUnicode():table.cmap.update(expected)
    names={1:family,2:'Regular',3:ps+'-20261022',4:family+' Regular',6:ps,16:family,17:'Regular'}
    for entry in font['name'].names:
        if entry.nameID in names:entry.string=names[entry.nameID].encode(entry.getEncoding(),errors='strict')
    for nid,value in names.items():font['name'].setName(value,nid,3,1,0x409)
    cff=font['CFF '].cff;cff.fontNames=[ps]
    top=cff.topDictIndex[0];top.FamilyName=family;top.FullName=family+' Regular';top.FontName=ps
    font['OS/2'].ulCodePageRange1=(font['OS/2'].ulCodePageRange1|(1<<17))&~((1<<18)|(1<<19)|(1<<20)|(1<<21))
    font['head'].modified=font['head'].created
    font.save(out); reopened=TTFont(out,recalcTimestamp=False)
    cm=reopened.getBestCmap();assert all(cm[k]==v for k,v in expected.items())
    return {'source_sha256':sha(source.read_bytes()),'output_sha256':sha(out.read_bytes()),'mapped_hangul':sum('\uac00'<=c<='\ud7a3' for c in mapping),'mapped_extra_characters':[c for c in mapping if not '\uac00'<=c<='\ud7a3'],'saved_cmap_verified':True,'family':family,'runtime_gdi_verified':False,'license':'SIL OFL 1.1; derived font renamed'}

def main():
    global FAMILY,SERIF_FAMILY
    units,targets,records,chosen=read_translation()
    units2,targets2,records2,chosen2=read_translation('chapter02')
    out=ROOT/'builds'/f'trial-body-through-ch02-{max(chosen2):04d}';out.mkdir(parents=True,exist_ok=True)
    inline=[r for r in json.loads((ROOT/'translation/opening-inline-ko.json').read_text(encoding='utf-8'))['records'] if r['unit'] in chosen]
    inline2=json.loads((ROOT/'translation/chapter02-inline-ko.json').read_text(encoding='utf-8'))['records']
    assert all(r['unit'] in chosen2 for r in inline2)
    mappings=font_mapping(list(targets.values())+list(targets2.values())+list(NAMES.values())+[r['target'] for r in inline+inline2])
    revision=sha(json.dumps(mappings,sort_keys=True,ensure_ascii=False).encode('utf-8'))[:8]
    FAMILY='Reconquista KR '+revision
    SERIF_FAMILY='Reconquista KR Serif '+revision
    assert len(SERIF_FAMILY)<32
    inverse={v:k for k,v in mappings.items()}
    def encode_text(text):
        encoded=''.join(mappings.get(c,c) for c in text);b=encoded.encode('cp932');assert b.decode('cp932')==encoded
        assert ''.join(inverse.get(c,c) for c in encoded)==text
        return encoded
    fontdir=out/'font';fontdir.mkdir(exist_ok=True)
    fontreport=build_font(fontdir/'ReconquistaKR.otf',mappings)
    serifreport=build_font(fontdir/'ReconquistaKRSerif.otf',mappings,serif=True)
    shutil.copyfile(ROOT/'research/fonts/LICENSE',fontdir/'LICENSE.txt')
    a=Arc(ROOT/'research/disc/scenario.arc');assert sha(a.path.read_bytes())==EXPECTED_SCENARIO
    originals={e['name']:(ROOT/'research/extracted/scenario'/e['name']).read_bytes() for e in a.entries}
    payloads=originals.copy();reports={}
    source,_=decode(originals[OPENING]);replacements={}
    for index,target in targets.items():
        assert source.instructions[index].opcode.mnemonic=='text'
        replacements[index]=string_ins('text',encode_text(target))
    for rec in inline:
        index=rec['index'];ins=source.instructions[index]
        assert ins.opcode.mnemonic=='ldstr' and ins.string==rec['source']
        assert index not in replacements
        replacements[index]=string_ins('ldstr',encode_text(rec['target']))
    serif_indices=[i for i,x in enumerate(source.instructions) if x.opcode.mnemonic=='ldstr' and x.string=='ＭＳ 明朝']
    assert serif_indices==[6318,6347,6364,6397,6414,6445,6467,6498]
    for i in serif_indices:
        assert source.instructions[i+1].is_syscall and source.instructions[i+1].hash==0x06b3c8ac
        replacements[i]=string_ins('ldstr',SERIF_FAMILY)
    payloads[OPENING],reports[OPENING]=rewrite(originals[OPENING],replacements)
    source2,_=decode(originals[SECOND]);replacements2={}
    for index,target in targets2.items():
        assert source2.instructions[index].opcode.mnemonic=='text'
        replacements2[index]=string_ins('text',encode_text(target))
    for rec in inline2:
        index=rec['index'];ins=source2.instructions[index]
        assert ins.opcode.mnemonic=='ldstr' and ins.string==rec['source']
        replacements2[index]=string_ins('ldstr',encode_text(rec['target']))
    payloads[SECOND],reports[SECOND]=rewrite(originals[SECOND],replacements2)
    loader,raw=decode(originals['load_sysdata.mjo'])
    store=next(x for x in loader.instructions if x.opcode.mnemonic=='st.s' and x.hash==0x391053c5)
    force=string_ins('ldstr',FAMILY)+raw[store.offset:store.offset+store.size]+op('pop')
    hook=string_ins('ldstr',r'font\ReconquistaKR.otf')+op('syscallp')+struct.pack('<IH',0x877445ce,1)+string_ins('ldstr',r'font\ReconquistaKRSerif.otf')+op('syscallp')+struct.pack('<IH',0x877445ce,1)+force
    index=next(i for i,x in enumerate(loader.instructions) if x.offset==0x0f)
    payloads['load_sysdata.mjo'],reports['load_sysdata.mjo']=rewrite(originals['load_sysdata.mjo'],insertions={index:hook})
    con,raw=decode(originals['console.mjo']);byoff={x.offset:x for x in con.instructions}
    load=raw[0x31d3:0x31d3+byoff[0x31d3].size];store=raw[0x31bf:0x31bf+byoff[0x31bf].size]
    namehook=b''
    for jp,ko in NAMES.items():
        for display in ([jp,jp[0]+'\u3000'+jp[1]] if len(jp)==2 else [jp]):
            body=string_ins('ldstr',encode_text(ko))+store+op('pop')
            namehook+=load+string_ins('ldstr',display)+op('ceq.s')+op('brfalse')+struct.pack('<i',len(body))+body
    at=next(i for i,x in enumerate(con.instructions) if x.offset==0x323e)
    payloads['console.mjo'],reports['console.mjo']=rewrite(originals['console.mjo'],insertions={at:namehook})
    cfg,_=decode(originals['config.mjo'])
    fixed={i:op('pop')+string_ins('ldstr',FAMILY) for i,x in enumerate(cfg.instructions) if x.opcode.mnemonic=='st.s' and x.hash==0x391053c5}
    assert len(fixed)==2
    payloads['config.mjo'],reports['config.mjo']=rewrite(originals['config.mjo'],insertions=fixed)
    scenario=out/'scenario.arc';scenario.write_bytes(a.rebuild(payloads))
    modified=sorted(name for name in payloads if payloads[name]!=originals[name]);assert modified==sorted(reports)
    ar=Arc(scenario)
    with scenario.open('rb') as f:
        for entry in ar.entries:
            f.seek(entry['offset']);assert f.read(entry['size'])==payloads[entry['name']]
    fast=Arc(ROOT/'research/disc/fastdata.arc');fp={e['name']:(ROOT/'research/extracted/fastdata'/e['name']).read_bytes() for e in fast.entries}
    original_cfg=fp['sysdata.cfg'];needle='ＭＳ ゴシック, 0'.encode('cp932');assert original_cfg.count(needle)==2
    fp['sysdata.cfg']=original_cfg.replace(needle,(FAMILY+', 0').encode('ascii'))
    (out/'fastdata.arc').write_bytes(fast.rebuild(fp))
    fastr=Arc(out/'fastdata.arc')
    with (out/'fastdata.arc').open('rb') as f:
        for entry in fastr.entries:
            f.seek(entry['offset']);assert f.read(entry['size'])==fp[entry['name']]
    warnings=[]
    for rec in records+records2:
        # Approximate engine grid width: ASCII half-cell, CJK and mapped Hangul full-cell.
        width=sum(.5 if ord(c)<128 else 1 for c in rec['target'])
        if width>31:warnings.append({'id':rec['id'],'estimated_cells':width,'target':rec['target']})
    dump(ROOT/'translation/opening-target.json',{'translator_model':'Codex internal','source_sha256':sha(originals[OPENING]),'completed_units':chosen,'records':records,'inline_records':inline})
    dump(ROOT/'translation/chapter02-target.json',{'translator_model':'Codex internal','source_sha256':sha(originals[SECOND]),'completed_units':chosen2,'records':records2,'inline_records':inline2})
    manifest={'status':'static_pass_runtime_pending','translator_model':'Codex internal','source_iso':r'P:\GAME\Reqonquist Novel H\Reconquista.iso','translated_units':len(chosen)+len(chosen2),'translated_text_fields':len(targets)+len(targets2),'translated_inline_fields':len(inline)+len(inline2),'coverage':{OPENING:chosen,SECOND:chosen2},'deferred_untranslated':{SECOND:remaining_deferred(chosen2)},'age_context_review':'translation/age-context-review.json','opening_total_units':len(units),'all_game_text_fields':96399,'font':fontreport,'serif_font':serifreport,'direct_serif_consumers_replaced':serif_indices,'modified_scenario_entries':modified,'modified_fastdata_entries':['sysdata.cfg'],'script_validation':reports,'line_width_review':warnings,'fixed_font_in_trial':True,'name_internal_tokens_preserved':True,'source_archive_sha256':EXPECTED_SCENARIO,'outputs':{p.name:sha(p.read_bytes()) for p in out.glob('*.arc')},'runtime':{'title':False,'korean_dialogue':False,'names':False,'save_load':False,'backlog':False},'known_limits':['Original Japanese menus and raster UI remain untranslated.','Only manifest coverage IDs have Korean text; remaining and deferred ranges keep original Japanese.','Runtime rendering, audio/page timing and save/load require verification.','Font setting is fixed to the derived Korean font in this trial.']}
    dump(out/'manifest.json',manifest);dump(ROOT/'reports/latest-build.json',{'path':str(out),**manifest})
    print(json.dumps({'path':str(out),'units':len(chosen)+len(chosen2),'text_fields':len(targets)+len(targets2),'glyphs':len(mappings),'line_width_warnings':warnings,'modified':modified},ensure_ascii=False,indent=2))
if __name__=='__main__':main()