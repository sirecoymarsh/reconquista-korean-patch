"""The order in which the scripts show pictures, for reading 4x art ahead (read-only on Codex's disassembly).
Every call of a picture function ($disp_back@PIC, $disp_char@PIC, ...) whose arguments include a string literal is one
step; only names with 4x art (hires-manifest.json) are kept, as their asset keys, script after script, a 0 between scripts.
python build_prefetch.py            -> build/prefetch.bin ("RPF1", uint32 count, then per step uint32 key, uint16 width,
                                       uint16 height at low res; key 0 between scripts), prints coverage
python build_prefetch.py simulate <hitch log>   also replays the log's load order through the look-ahead rule
"""
import json
import re
import struct
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
DIS = Path(r'P:\AI\Codex\projects\reconquista-ko\research\disassembly')
INS = re.compile(r'^([0-9a-f]{5}):\s+(\S+)\s*(.*)$')
CALL = re.compile(r'; \$(\w+)@PIC')


def key(name):
    """The DLL's Key(): base name, lower case, .rct when there is no extension, CRC-32 of the CP932 bytes."""
    n = name.replace('/', '\\').split('\\')[-1].lower()
    if '.' not in n:
        n += '.rct'
    try:
        return zlib.crc32(n.encode('cp932')) & 0xffffffff
    except UnicodeEncodeError:
        return None


def script_steps(path):
    ins = [m for line in path.read_text('utf-8').splitlines() if (m := INS.match(line))]
    steps = []
    for i, m in enumerate(ins):
        if m.group(2) != 'callp':
            continue
        c = CALL.search(m.group(3))
        if not c:
            continue
        for j in range(i - 1, max(-1, i - 5), -1):
            if ins[j].group(2) == 'callp':
                break
            if ins[j].group(2) == 'ldstr':
                s = ins[j].group(3).strip().strip('"')
                if s:
                    steps.append((c.group(1), s))
    return steps


def build():
    manifest = json.loads((HERE / 'runtime-test' / 'hires-manifest.json').read_text('utf-8-sig'))
    # colour pictures with a low-res size (the story's backgrounds and CGs); menus and mattes are not read ahead
    hd = {int(e['file'][:8], 16): e['size'] for e in manifest['entries'] if 'size' in e and e['name'].lower().endswith('.rct')}
    seq, funcs, seen, total = [], Counter(), set(), 0
    for path in sorted(DIS.glob('*.mjil')):
        steps = script_steps(path)
        keys = []
        for func, name in steps:
            total += 1
            k = key(name)
            if k in hd:
                funcs[func] += 1
                keys.append(k)
                seen.add(k)
        if keys:
            seq.extend(keys)
            seq.append(0)
    out = HERE / 'build' / 'prefetch.bin'
    out.write_bytes(b'RPF1' + struct.pack('<I', len(seq)) + b''.join(struct.pack('<IHH', k, *(hd[k] if k else (0, 0))) for k in seq))
    print(f'steps with a name {total}, with 4x art {sum(funcs.values())} ({len(seen)} distinct of {len(hd)} 4x keys), by function {dict(funcs)}')
    print(out, out.stat().st_size, 'bytes')
    return seq


def simulate(seq, log_path, ahead=4):
    """Replay the loads of a run: after each load of a key in the table, which keys would be read ahead, and how many of
    the later first-time loads had been read ahead."""
    pos = defaultdict(list)
    for i, k in enumerate(seq):
        if k:
            pos[k].append(i)
    loads = [int(m.group(1), 16) for m in re.finditer(r'^asset ([0-9a-f]{8}) ', Path(log_path).read_text('utf-8', 'replace'), re.M)]
    cursor, fetched, decoded = None, set(), set()
    hits = misses = 0
    for k in loads:
        if k not in decoded:
            if k in fetched:
                hits += 1
            elif k in pos:
                misses += 1
            decoded.add(k)
        if k not in pos:
            continue
        cands = pos[k]
        p = None
        if cursor is not None:
            p = next((q for q in cands if cursor < q <= cursor + 64), None)
        if p is None:
            p = cands[0] if len(cands) == 1 or cursor is None else min(cands, key=lambda q: (q < cursor, abs(q - cursor)))
        cursor = p
        n, q = 0, p + 1
        while n < ahead and q < len(seq) and seq[q]:
            if seq[q] not in decoded and seq[q] not in fetched:
                fetched.add(seq[q])
                n += 1
            q += 1
    print(f'first-time loads of keys in the table: {hits + misses}, read ahead in time: {hits} ({100 * hits / max(1, hits + misses):.0f}%)')


if __name__ == '__main__':
    s = build()
    if len(sys.argv) > 2 and sys.argv[1] == 'simulate':
        simulate(s, sys.argv[2])
