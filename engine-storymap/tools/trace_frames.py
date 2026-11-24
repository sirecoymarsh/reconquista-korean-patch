"""What the heavy frames draw (hitch.inc trace_next + TraceBlit lines in a hitch log), grouped by blit kind, destination,
size and source picture. python trace_frames.py qa/hitch-read-trace2.log
"""
import re
import sys
from collections import Counter
from pathlib import Path

TRACE = re.compile(r'trace (\w) src=\S+ (\d+)x(\d+) box=(-?\d+),(-?\d+),(\d+),(\d+) dst=(SCREEN )?(\S+) (\d+)x(\d+) at=(-?\d+),(-?\d+) t=(-?\d+)'
                   r'(?: shadows=(\d)(\d) alt=(\d)(\d) mask=(\d))? name=(.*)$')
lines = Path(sys.argv[1]).read_text('utf-8').splitlines()
frames, cur = [], None
for line in lines:
    if line.startswith('trace_next'):
        cur = {'head': line, 'blits': [], 'after': []}
        frames.append(cur)
    elif cur is not None:
        m = TRACE.match(line)
        if m:
            cur['blits'].append(m.groups())
        elif line.startswith('hitch') and len(cur['after']) < 2 and cur['blits']:
            cur['after'].append(line)
for f in frames:
    print(f['head'], 'blits', len(f['blits']))
    for a in f['after']:
        print('  ', a[:230])
    c = Counter()
    px = Counter()
    for g in f['blits']:
        kind, sw, sh, bx, by, bw, bh, scr, dst, dw, dh, ax, ay, t, sha, shb, alta, altb, mask, name = g
        key = (kind, 'screen' if scr else f'page{dw}x{dh}', f'{bw}x{bh}', name or f'(unnamed {sw}x{sh})', f'sh={sha}{shb} alt={alta}{altb} mask={mask}')
        c[key] += 1
        px[key] += int(bw) * int(bh)
    for key, n in c.most_common(14):
        print(f'   {n:4d}x  {" ".join(key)}  px={px[key]}')
    print()
