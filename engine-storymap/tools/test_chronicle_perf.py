"""Where the chronicle's frame time goes, on runtime-chron (start.mjo opens the chronicle) with RECON_PERF=1.

Idle for a while, then a slow posted drag; every present logs total / sync / gdi and the sync breakdown.
python test_chronicle_perf.py [label]   -> qa/chronicle_perf[-label].json
"""
import json
import re
import statistics as st
import sys
import time

import qa

RUN = qa.HERE / 'runtime-chron'
PERF = re.compile(r'perf_present seq=(\d+) total_ms=([\d.]+) sync_ms=([\d.]+) gdi_ms=([\d.]+) nearest_ms=([\d.]+) decode_ms=([\d.]+) compose_ms=([\d.]+)')


def keys(prefix):
    m = json.loads((RUN / 'hires-manifest.json').read_text('utf-8'))
    # v19 menu entries (group menu-4x) carry no 'key': their png name is the key
    return {e.get('key') or e['file'].split('.')[0] for e in m['entries'] if e.get('name', '').startswith(prefix)}


def summary(rows, seconds):
    out = {'presents': len(rows), 'per_second': round(len(rows) / seconds, 1)}
    for k, i in (('total', 1), ('sync', 2), ('gdi', 3), ('nearest', 4), ('decode', 5), ('compose', 6)):
        v = [float(r[i]) for r in rows]
        if v:
            out[k] = {'mean': round(st.mean(v), 2), 'median': round(st.median(v), 2), 'p95': round(sorted(v)[int(len(v) * .95) - 1], 2)}
    return out


def window(g, seconds, action=None):
    n = len(PERF.findall(g.log()))
    t = time.time()
    if action:
        action()
    while time.time() - t < seconds:
        time.sleep(.1)
    return summary(PERF.findall(g.log())[n:], time.time() - t)


def run(label, env=None):
    result = {'label': label}
    g = qa.Game(run=RUN, extra_env={'RECON_PERF': '1', **(env or {})})
    try:
        frame = keys('クロニクル枠')
        g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
        g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
        if not qa.u.IsWindowVisible(g.hwnd):                       # the chronicle opens before the title shows the window
            qa.u.ShowWindow(g.hwnd, 4)                             # SW_SHOWNOACTIVATE on the private desktop (Codex runtime_qa does the same)
        for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
            qa.u.SendMessageW(g.hwnd, m, a, 0)
        time.sleep(4)
        result['idle'] = window(g, 6)

        def drag():
            def lp(x, y):
                px, py = g.client_point(g.hwnd, x, y)
                return ((py & 0xffff) << 16) | (px & 0xffff)
            g.post(g.hwnd, 0x201, 1, lp(600, 300))
            for k in range(60):
                time.sleep(.05)
                g.post(g.hwnd, 0x200, 1, lp(600 - k * 6, 300))
            g.post(g.hwnd, 0x202, 0, lp(240, 300))
        result['drag'] = window(g, 5, drag)
        result['after'] = window(g, 4)
        result['fallback'] = [l for l in g.log().splitlines() if l.startswith('frame=')][-1:]
    except Exception as e:
        result['error'] = repr(e)
    finally:
        result['normal_exit'] = g.close_normally()
        (qa.QA / f'chronicle_perf{"-" + label if label else ""}.log').write_text(g.log(), 'utf-8')
    return result


if __name__ == '__main__':
    label = sys.argv[1] if len(sys.argv) > 1 else ''
    r = run(label)
    qa.dump(f'chronicle_perf{"-" + label if label else ""}.json', r)
    print(json.dumps(r, ensure_ascii=False, indent=1))
