"""The new 연표's own look switch (10-27): runtime-test (its own progress, 모든 콘텐츠 개방 off), the story map's first chapter,
the text box's 연표 tab; in the new 연표 the switch's halves clicked as the mouse would (posted to the view): 원래 -> the look
flips and is remembered, 새 -> back, 새 again -> nothing. Each state as a picture of the view (qa/chron-switch-<label>/; the
frame's corner with the switch is cut out apart for looking at, the whole pictures are Claude's checking only).
python test_chronicle_switch.py [label]   -> qa/chron-switch-<label>.json
"""
import json, re, shutil, sys, time
from PIL import Image
import qa
from test_hitch import VK

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
WM_APP = 0x8000
OUT = qa.QA / f'chron-switch-{label}'
OUT.mkdir(parents=True, exist_ok=True)
INI = qa.RUN / 'chronicle-look.ini'
INI.unlink(missing_ok=True)
(qa.RUN / 'review-unlock.enabled').unlink(missing_ok=True)
res = {'label': label, 'steps': []}
g = qa.Game(extra_env={'RECON_PERF': '2', 'RECON_HD_START_FULLSCREEN': '1'})
shots = qa.RUN / 'qa'
for p in shots.glob('chron-view-*.png') if shots.exists() else []:
    p.unlink()


def lines(prefix):
    return [l for l in g.log().splitlines() if l.startswith(prefix)]


def step(name, **kw):
    res['steps'].append({'step': name, 't': round(time.time() - g.started, 1), **kw})
    print(name, json.dumps(kw, ensure_ascii=False)[:500], flush=True)


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
    g.until(lambda: lines('chron_proto show'), 15, 'view shows')
    time.sleep(1.5)


def at(view, x, y):
    r = qa.w.RECT()
    qa.u.GetClientRect(view, qa.c.byref(r))
    return ((round(y * r.bottom / 600) & 0xffff) << 16) | (round(x * r.right / 800) & 0xffff)


def shot(view, n, name):
    before = len(lines('chron_proto shot'))
    g.post(view, WM_APP + 3, n, 0)
    g.until(lambda: len(lines('chron_proto shot')) > before, 10, f'shot {n}')
    src = shots / f'chron-view-{n}.png'
    shutil.copy2(src, OUT / f'{n}-{name}.png')
    im = Image.open(src)
    s = im.width / 800
    im.crop((int(90 * s), int(14 * s), int(232 * s), int(66 * s))).save(OUT / f'{n}-{name}-switch.png')   # the frame's corner only
    return lines('chron_proto shot')[-1]


def click(view, x, y):
    lp = at(view, x, y)
    g.post(view, 0x200, 0, lp)
    time.sleep(.15)
    g.post(view, 0x201, 1, lp)
    time.sleep(.08)
    g.post(view, 0x202, 0, lp)
    time.sleep(.5)


def ini():
    return INI.read_text('utf-16', errors='replace').strip() if INI.exists() and INI.read_bytes()[:2] == b'\xff\xfe' else (INI.read_text('utf-8', errors='replace').strip() if INI.exists() else None)


try:
    open_chronicle()
    view = qa.u.FindWindowExW(g.hwnd, None, 'ReconChronicleProto', None)
    step('view', show=lines('chron_proto show')[-1:], table=lines('chron_proto table')[-1:])
    g.post(view, 0x200, 0, at(view, 400, 590))                       # the mouse away from the switch and the table
    time.sleep(.3)
    step('new', shot=shot(view, 1, 'new'))
    click(view, 180, 40)                                             # the switch's right half: 원래
    step('to original', look=lines('chron_proto look=')[-1:], ini=ini(), shot=shot(view, 2, 'original-hover'))
    g.post(view, 0x200, 0, at(view, 400, 590))
    time.sleep(.3)
    step('original', shot=shot(view, 3, 'original'))
    click(view, 135, 40)                                             # the left half: 새
    step('to new', look=lines('chron_proto look=')[-1:], ini=ini(), shot=shot(view, 4, 'new-hover'))
    n = len(lines('chron_proto look='))
    click(view, 135, 40)                                             # 새 again: nothing to change
    step('new again', changed=len(lines('chron_proto look=')) != n, ini=ini())
    g.post(view, 0x200, 0, at(view, 180, 40))                        # over the unlit half
    time.sleep(.3)
    step('hover original half', shot=shot(view, 5, 'new-hover-other'))
    res['looks'] = lines('chron_proto look=')
except Exception as e:
    res['error'] = repr(e)
    print('error', repr(e)[:500], flush=True)
finally:
    res['normal_exit'] = g.close_normally()
    INI.unlink(missing_ok=True)
    res['tail'] = [l for l in g.log().splitlines() if l.startswith('chron')][-8:]
qa.dump(f'chron-switch-{label}.json', res)
print(json.dumps({'normal_exit': res['normal_exit'], 'error': res.get('error', '')[:300], 'looks': res.get('looks'), 'tail': res['tail']}, ensure_ascii=False, indent=0)[:2500])
