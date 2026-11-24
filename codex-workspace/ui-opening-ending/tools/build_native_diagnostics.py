"""Encode reviewed native-only MJO diagnostics; preserve engine CP932 text."""
from pathlib import Path
import json,sys,struct,collections,shutil,hashlib
U=Path('P:/AI/Codex/projects/reconquista-ko/ui-opening-ending').resolve();B=U.parent
sys.path.insert(0,str(B/'tools'));import build_trial as bt
from inspect_majiro import Arc,sha
from mjotool.crypt import crypt32
def apply_native(data,entry,rows):
    current,raw=bt.decode(data);original,_=bt.decode((B/'research/extracted/scenario'/entry).read_bytes())
    replacements={};records=[]
    for serial,r in enumerate(rows):
        index=r['instruction_index'];src=r['source'];assert original.instructions[index].string==src
        old_matches=[i for i,x in enumerate(original.instructions) if x.opcode.mnemonic==r['opcode'] and x.string==src]
        new_matches=[i for i,x in enumerate(current.instructions) if x.opcode.mnemonic==r['opcode'] and x.string==src]
        assert len(old_matches)==len(new_matches),(entry,r['id'])
        idx=new_matches[old_matches.index(index)]
        # Only already-audited native dialog consumers may use native ACP bytes.
        expected=0x4d2d4277 if r['id'] in ['config.mjo::008005','config.mjo::008011'] else 0xdf644f85
        tail=current.instructions[idx+1:idx+13]
        consumer=next((x for x in tail if x.is_syscall),None)
        assert consumer and consumer.hash==expected,(entry,r['id'],consumer)
        payload=r['target'].encode('cp949');assert b'\0' not in payload
        marker=('Q'+str(serial).zfill(7)).ljust(len(payload),'Z')
        assert len(marker)==len(payload) and marker.encode() not in raw
        replacements[idx]=bt.string_ins(r['opcode'],marker)
        records.append({'id':r['id'],'source':src,'target':r['target'],'instruction_index_current':idx,'marker':marker,'payload_hex':payload.hex(),'native_consumer_hash':f'{expected:08x}','encoding':'cp949'})
    staged,structural=bt._rewrite(data,replacements)
    parsed,code=bt.decode(staged);out=bytearray(code);allow=set()
    for r in records:
        x=parsed.instructions[r['instruction_index_current']];assert x.string==r['marker']
        target=bytes.fromhex(r['payload_hex']);start=x.offset+4;end=start+len(target)
        assert code[start:end]==r['marker'].encode() and code[end]==0
        out[start:end]=target;allow.update(range(start,end));r['bytecode_range']=[start,end];r.pop('marker')
    assert len(out)==len(code)
    assert all(i in allow for i,(a,b) in enumerate(zip(code,out)) if a!=b)
    # Restoring placeholders yields the exact structurally verified bytecode.
    recovered=bytearray(out)
    for r in records:
        start,end=r['bytecode_range'];recovered[start:end]=code[start:end]
        assert bytes(out[start:end]).decode('cp949')==r['target'] and out[end]==0
    assert recovered==code
    result=staged[:parsed.bytecode_offset]+(crypt32(bytes(out)) if parsed.signature==parsed.SIGNATURE_ENCRYPTED else bytes(out))
    return result,{'structural_rewrite':structural,'output_sha256':sha(result),'native_bytes_preserve_length':True,'outside_string_ranges_unchanged':True,'roundtrip_target_text_verified':True,'records':records}
def main():
    base=U/'candidates/ui-trial-v3';out=U/'candidates/ui-trial-v4';out.mkdir(exist_ok=True)
    rows=[r for r in json.loads((U/'translation/ui-semantic-map.json').read_text(encoding='utf-8'))['records'] if r['lane']=='native_diagnostic'];assert len(rows)==18
    groups=collections.defaultdict(list)
    for r in rows:groups[r['entry']].append(r)
    arc=Arc(base/'scenario.arc');raw=(base/'scenario.arc').read_bytes();payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in arc.entries};reports={}
    shutil.copytree(base/'payloads',out/'payloads',dirs_exist_ok=True);shutil.copytree(base/'font',out/'font',dirs_exist_ok=True);shutil.copy2(base/'fastdata.arc',out/'fastdata.arc')
    for entry,group in groups.items():
        payload[entry],reports[entry]=apply_native(payload[entry],entry,group)
        (out/'payloads/scenario.arc'/entry).write_bytes(payload[entry])
    result=arc.rebuild(payload);(out/'scenario.arc').write_bytes(result);parsed=Arc(out/'scenario.arc')
    assert [e['name'] for e in parsed.entries]==[e['name'] for e in arc.entries]
    changed=[]
    for before,after in zip(arc.entries,parsed.entries):
        b=result[after['offset']:after['offset']+after['size']];assert b==payload[after['name']]
        old=raw[before['offset']:before['offset']+before['size']]
        if old!=b:changed.append(after['name'])
    assert sorted(changed)==sorted(groups)
    manifest=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    manifest.update(inherits_static_evidence='../ui-trial-v3/manifest.json',semantic_included=143,deferred_native_diagnostic_ids=[],native_diagnostic_encoding='cp949',required_windows_acp=949,native_diagnostic_reports=reports,runtime_pass=False,validation_owner='User final combined runtime review')
    # Reports are indexed against original archive, not against the previous trial.
    original=Arc(B/'research/disc/scenario.arc');originalraw=original.path.read_bytes();originals={e['name']:originalraw[e['offset']:e['offset']+e['size']] for e in original.entries}
    for a in manifest['archives']:
        if a['archive']=='scenario.arc':
            a['output_sha256']=sha(result);a['changed']=[{'entry':n,'source_sha256':sha(originals[n]),'output_sha256':sha(b)} for n,b in payload.items() if originals[n]!=b]
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'translator_model':'Codex internal','source_translation':'translation/ui-text-ko.tsv','fields':18,'entries':len(groups),'required_windows_acp':949,'status':'static_pass_user_runtime_review_pending','outputs':reports}
    (U/'reports/native-diagnostics-static.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'out':str(out),'new_native_diagnostics':18,'script_entries':len(groups),'scenario_sha256':sha(result),'all_authored_script_fields_built':143},ensure_ascii=False))
if __name__=='__main__':main()
