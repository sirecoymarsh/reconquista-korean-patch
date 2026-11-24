# 세이브 오프셋 옮겨 적기: Majiro 세이브(majiro_*.sav)는 호출 단계마다 「스크립트 이름 128바이트 + 바이트 오프셋 + … + 줄 번호」를 저장한다.
# 새 번역으로 문자열 길이가 바뀌면 오프셋이 어긋나므로, 같은 번호의 명령 위치로 옮겨 적는다(명령 수·순서는 그대로라 1:1).
# 사용: python convert_saves.py <원래 savedata 폴더> <새 savedata 폴더>   (원래 폴더는 읽기만)
import sys, struct, json, shutil, re
from pathlib import Path
sys.dont_write_bytecode = True; sys.stdout.reconfigure(encoding='utf-8')
C = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타'); R = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024')
sys.path.insert(0, str(C / 'tools'))
import build_trial as b
from inspect_majiro import Arc
HERE = Path(__file__).resolve().parent
NEW = HERE.parent / 'build-20261121' / 'scenario.arc'
OLDS = [R / 'runtime-final-20261028' / 'scenario.arc', R / 'runtime-play' / 'scenario.arc']   # 옛 판 후보(명령 구조가 새 판과 같은 것)
def payload(p):
    a = Arc(p); raw = Path(p).read_bytes(); return {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}
new = payload(NEW); olds = [payload(p) for p in OLDS if p.exists()]
lower = {k.lower(): k for k in new}
cache = {}
def ins(arcdict, name, tag):
    key = (tag, name)
    if key not in cache: cache[key] = b.decode(arcdict[name])[0].instructions
    return cache[key]

changed = {k for k in new if any(k in od and od[k] != new[k] for od in olds)}
NAMEPATS = []
for k in new:
    if not k.lower().endswith('.mjo'): continue
    try: nb = k.encode('cp932')
    except UnicodeEncodeError: continue
    NAMEPATS.append((k, nb)); NAMEPATS.append((k, nb.upper())) if nb.upper() != nb else None

def convert(path, out):
    d = bytearray(path.read_bytes()); log = []
    assert d[:15] == b'MajiroSavV1.103', path
    seen = set()
    for ent, nb in NAMEPATS:
        for m in re.finditer(re.escape(nb) + rb'\x00', bytes(d)):
            st = m.start()
            if st in seen or st + 128 + 20 > len(d) or any(d[m.end():st + 128]): continue
            seen.add(st)
            off, a1, a2, a3, line = struct.unpack_from('<5I', d, st + 128)
            if ent not in changed:
                log.append({'frame_at': st, 'script': ent, 'offset': off, 'line': line, 'result': 'script unchanged in new build'}); continue
            nins = ins(new, ent, 'new'); hit = None
            for k, od in enumerate(olds):
                if ent not in od: continue
                oi = ins(od, ent, k)
                if len(oi) != len(nins) or any(x.opcode.mnemonic != y.opcode.mnemonic for x, y in zip(oi, nins)): continue
                j = next((j for j, x in enumerate(oi) if x.offset <= off < x.offset + x.size), None)
                if j is None and off == (oi[-1].offset + oi[-1].size): j = len(oi)
                if j is None: continue
                pl = next((x.line_number for x in reversed(oi[:j + 1]) if x.opcode.mnemonic == 'line'), None)
                if pl == line: hit = (k, j, off - (oi[j].offset if j < len(oi) else off)); break
            if hit is None:
                log.append({'frame_at': st, 'script': ent, 'offset': off, 'line': line, 'result': 'NOT MATCHED (left unchanged) - check by hand'}); continue
            k, j, delta = hit
            noff = (nins[j].offset if j < len(nins) else nins[-1].offset + nins[-1].size) + delta
            struct.pack_into('<I', d, st + 128, noff)
            log.append({'frame_at': st, 'script': ent, 'offset': off, 'new_offset': noff, 'instruction_index': j, 'inside_delta': delta, 'line': line, 'old_version': str(OLDS[k])})
    out.write_bytes(bytes(d)); return log

def main(src, dst):
    src, dst = Path(src), Path(dst); dst.mkdir(parents=True, exist_ok=True)
    report = {}
    for p in sorted(src.iterdir()):
        if p.is_dir(): continue
        if p.name.lower().startswith('fc_') and p.suffix.lower() == '.fcd':
            report[p.name] = 'glyph cache dropped (font map changed; engine rebuilds it)'; continue
        if p.suffix.lower() == '.sav':
            report[p.name] = convert(p, dst / p.name)
        else:
            shutil.copy2(p, dst / p.name); report[p.name] = 'copied unchanged'
    (dst / 'save-conversion.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), 'utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=1)[:3000])

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
