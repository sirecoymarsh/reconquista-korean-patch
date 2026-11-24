"""How long the game takes to show each line of text after a click, with whatever DLL runtime-test holds (perf mode).

Same route as test_jump (map at the title → 도입부 2 → its last scene → jump), then 10 clicks on the game window. Per
click: time from the click until presents stop for 0.8 s, and how many presents that took. Nothing is captured.
python test_text_speed.py label   -> qa/text_speed-<label>.json
"""
import json
import re
import sys
import time

import qa

VK = dict(F11=0x7a, RET=0x0d, ESC=0x1b, RIGHT=0x27, UP=0x26, END=0x23)
PERF = re.compile(r'perf_present seq=(\d+) total_ms=([\d.]+)')


def run(label, perf='1'):
    (qa.RUN / 'storymap-read.bin').unlink(missing_ok=True)   # start the map at 도입부 1, as test_jump does
    g = qa.Game(extra_env={'RECON_PERF': perf})   # '2': times only, without the DLL's byte checks (they slow the first loads)
    result = {'label': label, 'lines': []}
    try:
        g.until(lambda: 'asset 1de0628c ' in g.log(), 90, 'title')
        g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
        time.sleep(1)
        if not qa.u.IsWindowVisible(g.hwnd):                       # probe runs keep it hidden; hidden windows never present
            qa.u.ShowWindow(g.hwnd, 4)                             # SW_SHOWNOACTIVATE, on the private desktop
        for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
            qa.u.SendMessageW(g.hwnd, m, a, 0)
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
        for _ in range(10):
            start = seen = len(PERF.findall(g.log()))
            t0 = time.perf_counter()
            g.logical_click(g.hwnd, 400, 520)
            last = t0
            while time.perf_counter() - last < .8 and time.perf_counter() - t0 < 8:
                time.sleep(.02)
                now = len(PERF.findall(g.log()))
                if now > seen:
                    seen, last = now, time.perf_counter()
            result['lines'].append({'seconds': round(last - t0, 3), 'presents': seen - start})
        durations = sorted(x['seconds'] for x in result['lines'])
        result['median_seconds'] = durations[len(durations) // 2]
        blits = re.findall(r'perf_blits C=(\d+)/([\d.]+) S=\d+/[\d.]+ A=(\d+)/([\d.]+) M=(\d+)/([\d.]+)', g.log())
        present = [float(t) for _, t in PERF.findall(g.log())][-300:]
        result['present_ms_median'] = sorted(present)[len(present) // 2] if present else None
        if blits:
            tail = blits[-300:]
            result['alpha_ms_per_present_median'] = sorted(float(b[3]) for b in tail)[len(tail) // 2]
            result['copy_ms_per_present_median'] = sorted(float(b[1]) for b in tail)[len(tail) // 2]
            result['mask_ms_per_present_median'] = sorted(float(b[5]) for b in tail)[len(tail) // 2]
    except Exception as e:  # noqa: BLE001
        result['error'] = repr(e)
    finally:
        result['normal_exit'] = g.close_normally()
        (qa.QA / f'text_speed-{label}.log').write_text(g.log(), 'utf-8')
    return result


if __name__ == '__main__':
    label = sys.argv[1] if len(sys.argv) > 1 else 'now'
    r = run(label, sys.argv[2] if len(sys.argv) > 2 else '1')
    qa.dump(f'text_speed-{label}.json', r)
    print(json.dumps({k: v for k, v in r.items() if k != 'lines'}, ensure_ascii=False))
    print([x['seconds'] for x in r['lines']])
