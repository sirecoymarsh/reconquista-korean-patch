"""The 연표 view (10-27; one look since 11-25): runtime-test, the story map's first chapter (도입부 1), the text box's 연표 tab.
  python test_chronicle_view.py view <label>   its frame at fixed positions, then the panel under a hovered cell
  ... [review]   with 모든 콘텐츠 개방 on (every cell open; spoilers, never shown to the user)
-> qa/chron-view-<label>/ (pictures: the test copy's own progress, review unlock off; Claude's checking only) and a .json
"""
import json, re, shutil, sys, time
from ctypes import wintypes as w
from PIL import Image
import qa
from test_hitch import VK, WM_APP

mode = sys.argv[1] if len(sys.argv) > 1 else 'view'
label = sys.argv[2] if len(sys.argv) > 2 else 'now'
OUT = qa.QA / f'chron-view-{label}'
OUT.mkdir(parents=True, exist_ok=True)
POS = [(0, 0), (384, 900), (869, 2600)]
HOVER = (415, 304)   # 800x600: at POS[1] (opened up), a cell with a description and no link
res = {'mode': mode, 'label': label, 'steps': []}
review = len(sys.argv) > 3 and sys.argv[3] == 'review'   # 모든 콘텐츠 개방 on: every cell open (spoilers: Claude's checking only)
(qa.RUN / 'review-unlock.enabled').unlink(missing_ok=True)
if review:
    (qa.RUN / 'review-unlock.enabled').write_text('1')
env = {'RECON_PERF': '2', 'RECON_HD_START_FULLSCREEN': '1'}
g = qa.Game(extra_env=env)
shots = qa.RUN / 'qa'
for p in shots.glob('chron-view-*.png') if shots.exists() else []:
    p.unlink()


def lines(prefix):
    return [l for l in g.log().splitlines() if l.startswith(prefix)]


def step(name, **kw):
    res['steps'].append({'step': name, **kw})
    print(name, json.dumps(kw, ensure_ascii=False)[:400], flush=True)


def hover(x, y):
    r = qa.w.RECT()
    qa.u.GetClientRect(g.hwnd, qa.c.byref(r))
    vw = min(r.right, r.bottom * 4 // 3)
    vh = vw * 3 // 4
    g.post(g.hwnd, 0x200, 0, ((((r.bottom - vh) // 2 + round(y * vh / 600)) & 0xffff) << 16) | (((r.right - vw) // 2 + round(x * vw / 800)) & 0xffff))
    time.sleep(.4)


def open_chronicle():
    g.until(lambda: 'asset 1de0628c ' in g.log() or 'asset ef1f6a40 ' in g.log() or 'asset c1e942c6 ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(3)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open map')
    child = g.child()
    time.sleep(.5)
    g.key(child, VK['RET'])
    g.until(lambda: re.search(r'page=2 chapter=\d+', g.log()), 10, 'chapter page')
    time.sleep(.5)
    g.story_jump(child)
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    got = int(g.log().split('inflow jump order=')[-1].split()[0])
    g.until(lambda: f'inflow arrived order={got} ' in g.log(), 120, 'arrival')
    time.sleep(4)
    t0 = time.time()
    while time.time() - t0 < 90 and 'chronicle_open=1' not in g.log():
        g.logical_click(g.hwnd, 400, 520)
        time.sleep(1.2)
        hover(770, 510)
        g.logical_click(g.hwnd, 770, 510)
        end = time.time() + 2.5
        while time.time() < end and 'chronicle_open=1' not in g.log():
            time.sleep(.1)
    g.until(lambda: 'chronicle_open=1' in g.log(), 5, 'the game 연표 opens')
    time.sleep(3)


try:
    open_chronicle()
    g.until(lambda: lines('chron_proto show'), 15, 'view shows')
    view = qa.u.FindWindowExW(g.hwnd, None, 'ReconChronicleProto', None)
    step('view', table=lines('chron_proto table')[-1:], show=lines('chron_proto show')[-1:])
    k = 0
    for i, (x, y) in enumerate(POS):
        g.post(view, WM_APP + 4, x, y)
        time.sleep(.6)
        g.post(view, WM_APP + 3, k, 0)
        g.until(lambda: (shots / f'chron-view-{k}.png').exists(), 10, f'shot {k}')
        time.sleep(.3)
        shutil.copy2(shots / f'chron-view-{k}.png', OUT / f'view-{i}.png')
        k += 1
    g.post(view, WM_APP + 4, *POS[1])                   # the panel, as under the user's cursor
    time.sleep(.4)
    g.post(view, 0x200, 0, ((round(HOVER[1] * 3.6) & 0xffff) << 16) | (round(HOVER[0] * 3.6) & 0xffff))
    time.sleep(.8)
    g.post(view, WM_APP + 3, k, 0)
    g.until(lambda: (shots / f'chron-view-{k}.png').exists(), 10, f'shot {k}')
    time.sleep(.3)
    shutil.copy2(shots / f'chron-view-{k}.png', OUT / 'view-hover.png')
    k += 1
    step('shots', n=k, lines=lines('chron_proto shot')[-2:])
    if mode == 'map':                                   # the 「이야기 지도」 button (120,28 82x24): the 연표 closes, the map opens
        r = qa.w.RECT()
        qa.u.GetClientRect(view, qa.c.byref(r))
        s = r.right / 800
        lp = ((round(40 * s) & 0xffff) << 16) | (round(161 * s) & 0xffff)
        maps = g.log().count('inflow opened')
        g.post(view, 0x200, 0, lp)
        time.sleep(.3)
        g.post(view, 0x201, 1, lp)
        g.post(view, 0x202, 0, lp)
        g.until(lambda: g.log().count('inflow opened') > maps, 15, 'map opens')
        time.sleep(1)
        step('map', act=lines('chron_proto act')[-2:], chronicle_closed='chronicle_open=0' in g.log(), maps=g.log().count('inflow opened'))
        raise SystemExit
    g.post(view, 0x205, 0, 0)                            # a right click closes, as the user would
    g.until(lambda: 'chronicle_open=0' in g.log() or lines('chron_proto act'), 10, 'close')
    time.sleep(1.5)
    step('closed', act=lines('chron_proto act')[-2:], opens=g.log().count('chronicle_open=1'), closes=g.log().count('chronicle_open=0'))
except Exception as e:
    res['error'] = repr(e)
    print('error', repr(e)[:500], flush=True)
finally:
    res['normal_exit'] = g.close_normally()
    (qa.RUN / 'review-unlock.enabled').unlink(missing_ok=True)
    res['tail'] = [l for l in g.log().splitlines() if l.startswith('chron')][-10:]
qa.dump(f'chron-view-{label}.json', res)
print(json.dumps({'normal_exit': res['normal_exit'], 'error': res.get('error', '')[:300], 'tail': res['tail']}, ensure_ascii=False, indent=0)[:2500])
