"""Busy long frames of two or more hitch runs side by side (frames over 30 ms where the game thread slept less than half).
python hitch_compare.py <log> [<log> ...] [--phase 3]   -> per run: count by size, and the summed parts of those frames
"""
import re
import statistics as st
import sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith('--')]
phase = int(sys.argv[sys.argv.index('--phase') + 1]) if '--phase' in sys.argv else 3
args = [a for a in args if a != str(phase)]
NUM = re.compile(r'(\w+)=([\d.]+)')
for path in args:
    lines = Path(path).read_text('utf-8', 'replace').splitlines()
    marks = {int(m.group(1)): int(m.group(2)) for l in lines if (m := re.match(r'hitch_mark (\d+) frame=(\d+)', l))}
    lo, hi = marks.get(phase, 0), marks.get(phase + 1, 10 ** 9)
    rows = []
    for i, l in enumerate(lines):
        if not l.startswith('hitch gap='):
            continue
        d = {k: float(v) for k, v in NUM.findall(l.replace('/', ' '))}
        if not lo < d['frame'] <= hi or d['sleep'] >= d['gap'] / 2:
            continue
        if i + 1 < len(lines) and lines[i + 1].startswith('hitch_more'):
            d.update({'more_' + k: float(v) for k, v in NUM.findall(lines[i + 1].replace('/', ' '))})
        rows.append(d)
    frames = hi - lo if hi < 10 ** 9 else None
    bins = [sum(a <= r['gap'] < b for r in rows) for a, b in ((30, 50), (50, 100), (100, 200), (200, 10 ** 6))]
    parts = {k: round(sum(r.get(k, 0) for r in rows)) for k in ('gap', 'cpu', 'decode', 'nearest', 'compose', 'gdi', 'more_load', 'more_pair', 'more_alternates', 'more_free', 'more_snapshot')}
    med = {k: round(st.median(r.get(k, 0) for r in rows), 1) for k in ('gap', 'compose', 'nearest', 'gdi')} if rows else {}
    print(f'{Path(path).name}: frames={frames} busy>30ms={len(rows)} by size 30-50/50-100/100-200/200+={bins}')
    print('   summed ms', parts)
    print('   medians', med, ' alphas median', st.median(r['alphas'] for r in rows) if rows else '-')
