"""First-time 4x art loads in two perf logs side by side: per key, the file stage (open) plus the decode stage (wic) in ms.
python compare_loads.py qa/text_speed-text4k.log qa/text_speed-jxl.log   -> printed table and totals
"""
import re
import sys
from pathlib import Path

LOAD = re.compile(r'perf_load key=(\w+) size=(\d+x\d+) cg=\d cached=0(?: src=(\w+))? open=([\d.]+) get=[\d.]+ alt=[\d.]+ wic=([\d.]+)')


def loads(path):
    out = {}
    for key, size, src, op, dec in LOAD.findall(Path(path).read_text('utf-8', 'replace')):
        out.setdefault(key, (size, src or 'png', float(op) + float(dec)))   # the first load of each key
    return out


a, b = loads(sys.argv[1]), loads(sys.argv[2])
both = [k for k in a if k in b]
print(f'{"key":10} {"size":9} {"A ms":>7} {"B ms":>7}  B source')
for k in sorted(both, key=lambda k: -a[k][2]):
    print(f'{k:10} {a[k][0]:9} {a[k][2]:7.1f} {b[k][2]:7.1f}  {b[k][1]}')
for name, rows in (('A', a), ('B', b)):
    ms = [rows[k][2] for k in both]
    print(f'{name}: {len(ms)} shared first loads, total {sum(ms):.0f} ms, worst {max(ms, default=0):.1f} ms')
print('B sources:', {s: sum(1 for k in both if b[k][1] == s) for s in {b[k][1] for k in both}})
