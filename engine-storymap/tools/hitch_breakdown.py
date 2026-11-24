"""Busy frame gaps of a test_hitch.py log, grouped by what happened in them (pictures loaded, transition-like, other),
with every timer averaged per gap. Gaps where the game thread slept more than half are idle waits, not stutter.
python hitch_breakdown.py qa/hitch-read-<label>.log [phases...]
"""
import re
import sys
from collections import defaultdict

H = re.compile(r'hitch gap=([\d.]+) cpu=([\d.]+) sleep=([\d.]+) read=([\d.]+)/(\d+)KB/(\d+) decode=(-?[\d.]+) nearest=(-?[\d.]+) compose=(-?[\d.]+) gdi=([\d.]+) loads=(\d+) shadows=(\d+) alphas=(\d+) texts=(\d+)')
M = re.compile(r'hitch_more load=([\d.]+) engine_load=([\d.]+) hooks=([\d.]+) engine_blit=([\d.]+) pair=([\d.]+) snapshot=([\d.]+) alternates=([\d.]+)/(\d+)\+/(\d+)- free=([\d.]+)')
phases = set(map(int, sys.argv[2:])) or {2, 3}
phase, rows, last = 0, [], None
for line in open(sys.argv[1], encoding='utf-8', errors='replace'):
    m = re.search(r'hitch_mark (\d+)', line)
    if m:
        phase = int(m.group(1))
        continue
    m = H.search(line)
    if m:
        last = (phase, list(map(float, m.groups())))
        continue
    m = M.search(line)
    if m and last and last[0] in phases:
        v = last[1]
        if v[2] <= 0.5 * v[0]:
            rows.append((last[0], v, list(map(float, m.groups()))))
        last = None
kind = lambda v: 'pictures' if v[10] > 0 or v[11] > 0 else 'transition' if v[12] >= 40 else 'other'   # noqa: E731
for p in sorted(phases):
    groups = defaultdict(list)
    for ph, v, x in rows:
        if ph == p:
            groups[kind(v)].append((v, x))
    print(f'== phase {p}: busy gaps {sum(len(g) for g in groups.values())}, total {sum(v[0] for g in groups.values() for v, _ in g):.0f} ms')
    for k, items in groups.items():
        n = len(items)
        a = lambda f: sum(f(v, x) for v, x in items) / n   # noqa: E731
        compose_in_hooks = a(lambda v, x: x[2] - x[3] - x[4] - x[5])
        print(f'  {k:10} n={n:3} gap {a(lambda v, x: v[0]):6.1f} max {max(v[0] for v, _ in items):6.1f} | cpu {a(lambda v, x: v[1]):5.1f} | load {a(lambda v, x: x[0]):5.1f} '
              f'(engine {a(lambda v, x: x[1]):4.1f}, decode {a(lambda v, x: v[6]):5.1f}) | hooks {a(lambda v, x: x[2]):5.1f} = engine {a(lambda v, x: x[3]):4.1f} + pair {a(lambda v, x: x[4]):5.1f} '
              f'+ snapshot {a(lambda v, x: x[5]):4.1f} + 4x blits {compose_in_hooks:5.1f} | compose timer {a(lambda v, x: v[8]):5.1f} | screen sync {a(lambda v, x: v[7]):5.1f} '
              f'| alt {a(lambda v, x: x[6]):4.1f} (+{a(lambda v, x: x[7]):.1f}) free {a(lambda v, x: x[9]):4.1f} | present {a(lambda v, x: v[9]):4.1f}')
