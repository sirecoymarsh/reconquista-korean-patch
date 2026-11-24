"""Where the game still stutters (hitch.inc, RECON_HITCH=1 with RECON_PERF=2): play scenes on the private desktop and put
every frame gap over 30 ms down to the engine, the 4K layer, file reads or waiting. Numbers only, nothing captured.
python test_hitch.py read [label]    runtime-test: map -> 도입부 2, 40 clicks at 1.2 s, then 300 at 0.12 s
python test_hitch.py story [label]   runtime-test: map -> 도입부 2 from its first scene, 500 clicks at 0.2 s
-> qa/hitch-<scenario>-<label>.json and .log
"""
import json
import os
import re
import statistics as st
import sys
import time

import qa

WM_KEYDOWN, WM_KEYUP, WM_MOUSEWHEEL, WM_APP = 0x100, 0x101, 0x20A, 0x8000
VK = dict(F11=0x7a, RET=0x0d, RIGHT=0x27, LEFT=0x25, UP=0x26, DOWN=0x28, END=0x23)
HITCH = re.compile(r'hitch gap=([\d.]+) cpu=([\d.]+) sleep=([\d.]+) read=([\d.]+)/(\d+)KB/(\d+) decode=([\d.]+) nearest=([\d.]+) compose=([\d.]+) gdi=([\d.]+) loads=(\d+) shadows=(\d+) alphas=(\d+) texts=(\d+) frame=(\d+)')
MARK = re.compile(r'hitch_mark (\d+) frame=(\d+)')
FIELDS = ('gap', 'cpu', 'sleep', 'read', 'kb', 'reads', 'decode', 'nearest', 'compose', 'gdi', 'loads', 'shadows', 'alphas', 'texts', 'frame')


def mark(g, n):
    g.post(g.hwnd, WM_APP + 80, 100 + n, 0)
    time.sleep(.3)


def to_intro2(g):
    """test_text_speed's route: the story map at the title, 도입부 2, its last scene, jump."""
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open')
    child = g.child()
    g.key(child, VK['RIGHT'])
    g.until(lambda: 'cursor=' in g.log(), 10, 'cursor move')
    g.key(child, VK['RET'])
    g.until(lambda: 'page=2 chapter=3' in g.log(), 10, 'chapter page')
    n = g.count('inflow snapshot')
    g.key(child, VK['RIGHT'], 34, .03)
    g.until(lambda: g.count('inflow snapshot') >= n + 34, 30, 'scene steps')
    time.sleep(.5)
    n = g.count('inflow snapshot')
    g.key(child, VK['END'])
    g.until(lambda: g.count('inflow snapshot') > n, 10, 'end')
    g.key(child, VK['UP'])
    time.sleep(.4)
    g.story_jump(child)
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    order = int(g.log().split('inflow jump order=')[-1].split()[0])
    g.until(lambda: f'inflow arrived order={order} ' in g.log(), 120, 'arrival')
    time.sleep(3)


def read(g):
    (qa.RUN / 'storymap-read.bin').unlink(missing_ok=True)
    g.until(lambda: 'asset 1de0628c ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    mark(g, 1)                                   # phase 1: title and the map route
    to_intro2(g)
    mark(g, 2)                                   # phase 2: reading at a normal pace
    for _ in range(40):
        g.logical_click(g.hwnd, 400, 520)
        time.sleep(1.2)
    mark(g, 3)                                   # phase 3: clicking through fast
    for _ in range(300):
        g.logical_click(g.hwnd, 400, 520)
        time.sleep(.12)
    mark(g, 4)
    time.sleep(2)


def story(g):
    """도입부 2 from its first scene, 500 clicks at 0.2 s: one scene change after another (backgrounds, CGs read ahead)."""
    (qa.RUN / 'storymap-read.bin').unlink(missing_ok=True)
    g.until(lambda: 'asset 1de0628c ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    mark(g, 1)
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open')
    child = g.child()
    g.key(child, VK['RIGHT'])
    g.until(lambda: 'cursor=' in g.log(), 10, 'cursor move')
    g.key(child, VK['RET'])
    g.until(lambda: 'page=2 chapter=3' in g.log(), 10, 'chapter page')
    time.sleep(.5)
    g.story_jump(child)                      # the first scene card
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    order = int(g.log().split('inflow jump order=')[-1].split()[0])
    g.until(lambda: f'inflow arrived order={order} ' in g.log(), 120, 'arrival')
    time.sleep(3)
    mark(g, 2)
    for _ in range(500):
        g.logical_click(g.hwnd, 400, 520)
        time.sleep(.2)
    mark(g, 3)
    time.sleep(2)


def summary(log):
    marks = [(int(n), int(f)) for n, f in MARK.findall(log)]
    rows = [dict(zip(FIELDS, map(float, m))) for m in HITCH.findall(log)]
    hist = re.findall(r'hitch_histogram ([^\n]*)', log)
    phases = {}
    for i, (n, f0) in enumerate(marks):
        f1 = marks[i + 1][1] if i + 1 < len(marks) else 10 ** 9
        hs = [r for r in rows if f0 < r['frame'] <= f1]
        if i + 1 < len(marks) or hs:
            frames = (f1 - f0) if f1 < 10 ** 9 else None
            entry = {'frames': frames, 'gaps_over_30': len(hs), 'over_50': sum(r['gap'] > 50 for r in hs), 'over_100': sum(r['gap'] > 100 for r in hs),
                     'worst': max((r['gap'] for r in hs), default=0)}
            if hs:
                tot = {k: round(sum(r[k] for r in hs)) for k in ('gap', 'cpu', 'sleep', 'read', 'decode', 'nearest', 'compose', 'gdi')}
                tot['rest'] = round(tot['gap'] - tot['sleep'] - tot['read'] - tot['decode'] - tot['nearest'] - tot['compose'] - tot['gdi'])
                entry['time_in_long_gaps_ms'] = tot
                entry['median_gap'] = round(st.median(r['gap'] for r in hs), 1)
                entry['top'] = sorted(hs, key=lambda r: -r['gap'])[:6]
            phases[n] = entry
    return {'phases': phases, 'histograms': hist[-2:]}


if __name__ == '__main__':
    scenario = sys.argv[1] if len(sys.argv) > 1 else 'read'
    label = sys.argv[2] if len(sys.argv) > 2 else 'now'
    run = qa.RUN
    env = {'RECON_PERF': '2', 'RECON_HITCH': '1'}
    env.update({k: os.environ[k] for k in ('RECON_DEFER_VERIFY', 'RECON_HITCH_TRACE') if k in os.environ})   # also check every screen queue
    g = qa.Game(run=run, extra_env=env)
    result = {'scenario': scenario}
    try:
        {'story': story}.get(scenario, read)(g)
    except Exception as e:  # noqa: BLE001
        result['error'] = repr(e)
    finally:
        result['normal_exit'] = g.close_normally()
        log = g.log()
        (qa.QA / f'hitch-{scenario}-{label}.log').write_text(log, 'utf-8')
    result.update(summary(log))
    qa.dump(f'hitch-{scenario}-{label}.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'phases'}, ensure_ascii=False))
    for n, p in result.get('phases', {}).items():
        print('phase', n, {k: v for k, v in p.items() if k != 'top'})
        for r in p.get('top', [])[:4]:
            print('   ', {k: r[k] for k in ('gap', 'cpu', 'sleep', 'read', 'decode', 'nearest', 'compose', 'gdi', 'loads', 'shadows', 'alphas', 'texts')})
