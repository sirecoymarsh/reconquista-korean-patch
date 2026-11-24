"""Side by side: the reading scene under each RECON_OFF setting (qa/hitch-read-m-<setting>-<n>.log, matrix runs).
For phases 2 (reading at 1.2 s a click) and 3 (300 clicks at 0.12 s): busy frames over 30 ms (the game thread awake more
than half the gap) by size, their summed length, and the frame-time spread of the whole phase.
python matrix_report.py [prefix=m] [settings ...]
"""
import re
import statistics as st
import sys
from pathlib import Path

QA = Path(__file__).resolve().parents[1] / 'qa'
prefix = sys.argv[1] if len(sys.argv) > 1 else 'm'
settings = sys.argv[2:] or ['on', 'async', 'par', 'load', 'defer', 'all']
NUM = re.compile(r'(\w+)=([\d.]+)')


def phase_rows(lines, phase):
    marks = {int(m.group(1)): int(m.group(2)) for l in lines if (m := re.match(r'hitch_mark (\d+) frame=(\d+)', l))}
    lo, hi = marks.get(phase, 0), marks.get(phase + 1, 10 ** 9)
    rows = []
    for l in lines:
        if l.startswith('hitch gap='):
            d = {k: float(v) for k, v in NUM.findall(l.replace('/', ' '))}
            if lo < d['frame'] <= hi and d['sleep'] < d['gap'] / 2:
                rows.append(d)
    return rows, hi - lo


def presents(lines, phase):
    """per-present total time of the layer (perf_present) inside the phase, by the hitch frame counter of nearby lines"""
    marks = {int(m.group(1)): int(m.group(2)) for l in lines if (m := re.match(r'hitch_mark (\d+) frame=(\d+)', l))}
    return marks


print(f'{"setting":8} {"run":3} | phase 2 busy>30 (30-50/50-100/100-200/200+) sum ms | phase 3 busy>30 (bins) sum ms worst | frames in phase 3')
agg = {}
for s in settings:
    for n in (1, 2, 3):
        f = QA / f'hitch-read-{prefix}-{s}-{n}.log'
        if not f.exists():
            continue
        lines = f.read_text('utf-8', 'replace').splitlines()
        out = []
        for ph in (2, 3):
            rows, frames = phase_rows(lines, ph)
            bins = [sum(a <= r['gap'] < b for r in rows) for a, b in ((30, 50), (50, 100), (100, 200), (200, 10 ** 6))]
            out.append((len(rows), bins, round(sum(r['gap'] for r in rows)), max((r['gap'] for r in rows), default=0), frames))
            agg.setdefault((s, ph), []).append((len(rows), sum(r['gap'] for r in rows)))
        (c2, b2, s2, w2, f2), (c3, b3, s3, w3, f3) = out
        print(f'{s:8} {n:3} | {c2:4} {b2} {s2:6} | {c3:4} {b3} {s3:6} {w3:6.0f} | {f3}')
print()
for s in settings:
    v2, v3 = agg.get((s, 2), []), agg.get((s, 3), [])
    if v3:
        print(f'{s:8} mean phase 2: {st.mean(c for c, _ in v2):6.1f} frames {st.mean(t for _, t in v2):7.0f} ms | phase 3: {st.mean(c for c, _ in v3):6.1f} frames {st.mean(t for _, t in v3):7.0f} ms')
