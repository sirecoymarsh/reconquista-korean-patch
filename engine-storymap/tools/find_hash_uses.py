"""Which scripts of a scenario.arc mention a variable/function hash (read-only), and how many times.
python find_hash_uses.py aa2e632d [scenario.arc]
"""
import struct
import sys
from pathlib import Path

import codex_model as CM

sys.path.insert(0, str(CM.CODEX / 'tools'))
import build_trial as b  # noqa: E402
from inspect_majiro import Arc  # noqa: E402

h = int(sys.argv[1], 16)
arc_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / 'runtime-play' / 'scenario.arc'
arc = Arc(arc_path)
raw = arc.path.read_bytes()
needle = struct.pack('<I', h)
hits = []
for e in arc.entries:
    if not e['name'].endswith('.mjo'):
        continue
    try:
        s, code = b.decode(raw[e['offset']:e['offset'] + e['size']])
    except Exception as ex:  # noqa: BLE001
        print('skip', e['name'], ex)
        continue
    n = sum(1 for x in s.instructions if getattr(x, 'hash', None) == h)
    if n:
        ops = {}
        for x in s.instructions:
            if getattr(x, 'hash', None) == h:
                ops[x.opcode.mnemonic] = ops.get(x.opcode.mnemonic, 0) + 1
        hits.append((e['name'], n, ops))
for name, n, ops in sorted(hits, key=lambda t: -t[1]):
    print(f'{n:5d} {name} {ops}')
print('scripts', len(hits))
