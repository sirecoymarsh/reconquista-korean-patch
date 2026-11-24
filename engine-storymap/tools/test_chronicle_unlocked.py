"""The opened-up 연표 (review-unlock.enabled) on runtime-chron: idle, arrow-key glides (a drag would click an open cell and
jump to its scene; the wheel zooms), then zoomed in, idle and glides; presents per second per phase, the hitch_avg lines
(with RECON_HITCH=1) and the low-res lines. Numbers only: the opened-up 연표 is past the user's progress, no pictures.
python test_chronicle_unlocked.py <label> [K=V ...]   e.g. RECON_OFF=lowres, RECON_DEFER_VERIFY=1
"""
import json, re, sys, time
from pathlib import Path
TOOLS = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools')
sys.path.insert(0, str(TOOLS))
import qa
import test_chronicle_perf as T

label = sys.argv[1]
env = {'RECON_PERF': '2'}
for kv in sys.argv[2:]:
    k, v = kv.split('=', 1)
    env[k] = v
RUN = T.RUN
(RUN / 'review-unlock.enabled').write_text('1\n')
g = qa.Game(run=RUN, extra_env=env)
res = {'label': label, 'env': env}
try:
    frame = T.keys('クロニクル枠')
    g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    time.sleep(4)
    marks = {'idle': len(g.log())}
    res['idle'] = T.window(g, 6)
    marks['arrows'] = len(g.log())
    cr = qa.w.RECT()
    qa.u.GetClientRect(g.hwnd, qa.c.byref(cr))
    pt = qa.w.POINT(cr.right // 2, cr.bottom // 2)
    qa.u.ClientToScreen(g.hwnd, qa.c.byref(pt))

    def keys(vk, n):
        for k in range(n):
            g.post(g.hwnd, 0x100, vk, 1)
            g.post(g.hwnd, 0x101, vk, 0xc0000001)
            time.sleep(.45)
    res['arrows'] = T.window(g, 6, lambda: (keys(0x27, 6), keys(0x25, 6)))   # right x6, then left x6: column glides
    def zoom_in():
        for k in range(2):
            g.post(g.hwnd, 0x20A, (120 & 0xffff) << 16, ((pt.y & 0xffff) << 16) | (pt.x & 0xffff))
            time.sleep(.5)
    marks['zoom'] = len(g.log())
    zoom_in()
    time.sleep(2)
    res['zoomed_idle'] = T.window(g, 5)
    res['zoomed_arrows'] = T.window(g, 6, lambda: keys(0x27, 6))
    marks['end'] = len(g.log())
    names = list(marks)
    for a, b in zip(names, names[1:]):
        res['avg_' + a] = [l[:200] for l in g.log()[marks[a]:marks[b]].splitlines() if l.startswith('hitch_avg')]
    res['hi_built_by'] = [l[:400] for l in g.log().splitlines() if l.startswith('hi_built_by')][-1:]
    log = g.log()
    res['lowres'] = [l for l in log.splitlines() if l.startswith('lowres ')][-1:]
    res['defer'] = [l for l in log.splitlines() if l.startswith('defer frames')][-1:]
    res['mismatch_lines'] = log.count('defer_mismatch')
    res['scene_jump'] = 'chronicle_open=0' in log
except Exception as e:
    res['error'] = repr(e)
finally:
    res['normal_exit'] = g.close_normally()
    (RUN / 'review-unlock.enabled').unlink(missing_ok=True)
print(json.dumps({k: (v.get('per_second') if isinstance(v, dict) else v) for k, v in res.items()}, ensure_ascii=False, indent=1))
