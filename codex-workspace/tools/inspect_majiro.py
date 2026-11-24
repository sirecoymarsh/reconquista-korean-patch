from pathlib import Path
import sys, io, json, struct, hashlib, collections, re, zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research/vendor/majiro-py/src'))
from mjotool import MjoScript
from mjotool import known_hashes

def sha(b): return hashlib.sha256(b).hexdigest()
def dump(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
class Arc:
    def __init__(self,path):
        self.path=Path(path)
        with self.path.open('rb') as f:
            h=f.read(28)
            assert h[:16]==b'MajiroArcV2.000\0'
            n,self.names_offset,self.data_offset=struct.unpack_from('<III',h,16)
            table=f.read(n*12)
            f.seek(self.names_offset)
            raw_names=f.read(self.data_offset-self.names_offset).split(b'\0')
        assert raw_names[-1]==b'' and len(raw_names)==n+1
        self.entries=[]
        for i,raw in enumerate(raw_names[:-1]):
            hsh,off,size=struct.unpack_from('<III',table,i*12)
            name=raw.decode('cp932')
            assert zlib.crc32(raw)==hsh,(name,hex(hsh))
            assert not any(c in name for c in ['/', '\\', ':']) and name not in ['.','..']
            assert off>=self.data_offset and off+size<=self.path.stat().st_size
            self.entries.append(dict(index=i,name=name,hash=f'{hsh:08x}',offset=off,size=size))
        ordered=sorted(self.entries,key=lambda x:x['offset'])
        assert len({e['name'] for e in ordered})==n
        assert all(a['offset']+a['size']<=b['offset'] for a,b in zip(ordered,ordered[1:]))
    def extract(self,out):
        out.mkdir(parents=True,exist_ok=True)
        with self.path.open('rb') as f:
            for e in self.entries:
                f.seek(e['offset']); b=f.read(e['size'])
                (out/e['name']).write_bytes(b); e['sha256']=sha(b)
    def rebuild(self,payloads):
        b=self.path.read_bytes(); out=bytearray(b[:self.data_offset]); cursor=self.data_offset
        for e in sorted(self.entries,key=lambda x:x['offset']):
            out.extend(b[cursor:e['offset']]); data=payloads[e['name']]
            struct.pack_into('<II',out,28+e['index']*12+4,len(out),len(data))
            out.extend(data); cursor=e['offset']+e['size']
        out.extend(b[cursor:]); return bytes(out)

def main():
    inventories=[]
    for p in sorted((ROOT/'research/disc').glob('*.arc')):
        a=Arc(p)
        if p.stem in ['scenario','fastdata']:
            a.extract(ROOT/'research/extracted'/p.stem)
        row={'archive':p.name,'bytes':p.stat().st_size,'entries':a.entries,'extensions':dict(collections.Counter(Path(e['name']).suffix for e in a.entries))}
        dump(ROOT/'reports/archive_inventory'/f'{p.stem}.json',row)
        inventories.append({k:v for k,v in row.items() if k!='entries'}|{'count':len(a.entries)})
    a=Arc(ROOT/'research/disc/scenario.arc')
    payloads={e['name']:(ROOT/'research/extracted/scenario'/e['name']).read_bytes() for e in a.entries}
    rebuilt=a.rebuild(payloads)
    assert rebuilt==a.path.read_bytes()
    roundtrip=ROOT/'research/roundtrip'/('scenario-'+sha(rebuilt)[:12]+'.arc')
    roundtrip.parent.mkdir(parents=True,exist_ok=True); roundtrip.write_bytes(rebuilt)
    Arc(roundtrip)
    scripts=[]; catalog=[]; errors=[]
    disasm=ROOT/'research/disassembly'; disasm.mkdir(exist_ok=True)
    for name,b in payloads.items():
        if not name.endswith('.mjo'): continue
        try:
            script=MjoScript.disassemble_script(io.BytesIO(b))
            stream=io.BytesIO(); script.assemble_script(stream)
            rebuilt_mjo=stream.getvalue()
            assert rebuilt_mjo==b,'MJO assemble byte mismatch'
            lines=[]; strings=[]
            for index,ins in enumerate(script.instructions):
                lines.append(ins.format_instruction())
                if ins.string is not None:
                    is_jp=bool(re.search('[\u3040-\u30ff\u3400-\u9fff\uff01-\uffef]',ins.string))
                    lane='dialogue_or_narration' if ins.opcode.mnemonic=='text' else 'protected_control' if ins.opcode.mnemonic=='ctrl' else 'string_literal_needs_consumer_audit'
                    row={'id':f'{name}::{index:06d}','file':name,'instruction_index':index,'offset':ins.offset,'opcode':ins.opcode.mnemonic,'source':ins.string,'lane':lane,'has_japanese':is_jp,'source_byte_sha256':sha(b),'status':'untranslated' if lane=='dialogue_or_narration' else 'audit_pending'}
                    catalog.append(row); strings.append(row)
            (disasm/(name+'.mjil')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
            scripts.append({'file':name,'instructions':len(script.instructions),'text_fields':sum(x['opcode']=='text' for x in strings),'text_chars':sum(len(x['source']) for x in strings if x['opcode']=='text'),'string_fields':len(strings),'sha256':sha(b),'byte_identical_roundtrip':True})
        except Exception as exc:
            errors.append({'file':name,'error':repr(exc)})
    cpath=ROOT/'localization/catalog/catalog.jsonl'
    cpath.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in catalog),encoding='utf-8')
    report={'archives':inventories,'scenario_archive_roundtrip':{'byte_identical':True,'sha256':sha(rebuilt),'path':str(roundtrip)},'scripts':scripts,'parse_errors':errors,'total_scripts':len(scripts),'text_fields':sum(s['text_fields'] for s in scripts),'text_chars':sum(s['text_chars'] for s in scripts),'catalog_entries':len(catalog),'translator_model':'Codex internal','source_tool_commit':'f7ec450d5b78f0ed6df603b8c0b0ed79748d9cee'}
    dump(ROOT/'reports/extraction.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['scripts','archives']},ensure_ascii=False,indent=2))
    print('START TEXT:',json.dumps([r for r in catalog if r['file']=='start.mjo'],ensure_ascii=False)[:6500])
    print('TOP SCRIPTS:',json.dumps(sorted(scripts,key=lambda x:x['text_fields'],reverse=True)[:8],ensure_ascii=False))
if __name__=='__main__': main()
