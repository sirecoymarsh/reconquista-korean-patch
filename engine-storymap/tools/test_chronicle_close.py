"""연표 원래 화면 and going back to the story: runtime-test, a 도입부 1 scene with a standing picture (as test_sprites.py),
then three times: open the 연표 with its button, (F8 or not), close it with a right click, and capture the scene again.
  round 1: 4K -> F8 (original) -> close        round 2: opens original -> F8 (4K) -> close        round 3: 4K -> close
Each scene after closing must equal the scene before opening (4x and presented output): the original frames must leave
nothing stale behind. Only 도입부 1 is shown (the user's progress); the 연표 here is the test copy's own (not opened up).
python test_chronicle_close.py [label]   -> qa/chron-close-<label>/, qa/chron-close-<label>.json
"""
import ctypes, json, re, sys, time
import numpy as np
from PIL import Image
import qa
from test_hitch import VK, WM_APP

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
OUT = qa.QA / f'chron-close-{label}'
OUT.mkdir(parents=True, exist_ok=True)
flag = qa.RUN / 'chronicle-original.enabled'
flag.unlink(missing_ok=True)
(qa.RUN / 'review-unlock.enabled').unlink(missing_ok=True)
g = qa.Game(extra_env={'RECON_PERF': '2', 'RECON_HD_START_FULLSCREEN': '1'})
res = {'label': label, 'rounds': []}
shots = qa.RUN / 'qa'
n = 0


def capture(tag):
    global n
    n += 1
    for p in shots.glob(f'quality-{n:02d}-*.bmp'):
        p.unlink()
    g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
    g.until(lambda: (shots / f'quality-{n:02d}-output.bmp').exists(), 20, f'capture {tag}')
    time.sleep(.3)
    out = {}
    for kind in ('hd', 'base', 'output'):
        im = Image.open(shots / f'quality-{n:02d}-{kind}.bmp').convert('RGB')
        if kind != 'hd':
            im.save(OUT / f'{tag}-{kind}.png')
        out[kind] = np.asarray(im).astype(np.int16)
    return out


def diff(a, b):
    if a.shape != b.shape:
        return {'shape': [list(a.shape), list(b.shape)]}
    d = np.abs(a - b)
    return {'mean': round(float(d.mean()), 4), 'over8_pct': round(100 * float((d.max(axis=2) > 8).mean()), 4), 'max': int(d.max())}


def opens():
    return g.log().count('chronicle_open=1')


def closes():
    return g.log().count('chronicle_open=0')


def hover(x, y):
    r = qa.w.RECT()
    qa.u.GetClientRect(g.hwnd, qa.c.byref(r))
    vw = min(r.right, r.bottom * 4 // 3)
    vh = vw * 3 // 4
    px, py = (r.right - vw) // 2 + round(x * vw / 800), (r.bottom - vh) // 2 + round(y * vh / 600)
    g.post(g.hwnd, 0x200, 0, ((py & 0xffff) << 16) | (px & 0xffff))
    time.sleep(.4)                                   # a button lights under the cursor before it takes a click


def open_chronicle():
    k = opens()
    hover(770, 510)                                  # the 연표 tab right of the text box
    g.logical_click(g.hwnd, 770, 510)
    g.until(lambda: opens() > k, 20, 'chronicle opens')
    time.sleep(2.5)


def close_chronicle():
    k = closes()
    hover(400, 300)
    g.logical_click(g.hwnd, 400, 300, button='right')
    try:
        g.until(lambda: closes() > k, 10, 'chronicle closes')
    except Exception:
        g.key(g.hwnd, 0x1b)
        g.until(lambda: closes() > k, 10, 'chronicle closes (Esc)')
    time.sleep(3)


def switch_visible():
    h = ctypes.windll.user32.GetDlgItem(g.hwnd, 0x7e46)
    return bool(h and ctypes.windll.user32.IsWindowVisible(h))


def switch_click(right):
    h = ctypes.windll.user32.GetDlgItem(g.hwnd, 0x7e46)
    r = qa.w.RECT()
    ctypes.windll.user32.GetClientRect(h, ctypes.byref(r))
    lp = ((r.bottom // 2) << 16) | int(r.right * (.8 if right else .2))
    k = g.log().count('by=switch')
    g.post(h, 0x200, 0, lp)
    time.sleep(.2)
    g.post(h, 0x201, 1, lp)
    time.sleep(.1)
    g.post(h, 0x202, 0, lp)
    g.until(lambda: g.log().count('by=switch') > k, 10, 'switch click')
    time.sleep(2)


def f8(on):
    k = g.log().count(f'chronicle_original={int(on)}')
    g.post(g.hwnd, 0x100, 0x77, 1)
    g.post(g.hwnd, 0x101, 0x77, 0xc0000001)
    g.until(lambda: g.log().count(f'chronicle_original={int(on)}') > k, 10, f'F8 {"on" if on else "off"}')
    time.sleep(2)


try:
    (qa.RUN / 'storymap-read.bin').unlink(missing_ok=True)
    g.until(lambda: 'asset 1de0628c ' in g.log() or 'asset ef1f6a40 ' in g.log(), 90, 'title')
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
    last = len(g.log())
    time.sleep(2.5)
    t0 = time.time()
    while time.time() - t0 < 420 and not re.search(r'load call (?:b_)?(?:momi|masa)_\w+\.rct', g.log()[last:]):
        g.logical_click(g.hwnd, 400, 520)
        time.sleep(.3)
    time.sleep(3)
    before = capture('0-scene')
    for i, (start_on, toggle) in enumerate([(False, True), (True, True), (False, False)], 1):
        if start_on != flag.exists():
            raise RuntimeError(f'round {i}: setting is {flag.exists()}, wanted {start_on}')
        shown_before = switch_visible()
        open_chronicle()
        shown_open = switch_visible()
        mid = capture(f'{i}-chronicle')
        if toggle and i == 1:
            switch_click(True)                       # round 1 by the on-screen switch, round 2 by F8
            capture(f'{i}-chronicle-after-switch')
        elif toggle:
            f8(not start_on)
            capture(f'{i}-chronicle-after-f8')
        close_chronicle()
        shown_after = switch_visible()
        after = capture(f'{i}-scene-after')
        res['rounds'].append({'round': i, 'opened_original': start_on, 'toggle': ('switch' if i == 1 else 'F8') if toggle else None,
                              'switch_shown': [shown_before, shown_open, shown_after], 'setting_after': flag.exists(),
                              'scene_1x': diff(before['base'], after['base']), 'scene_4x': diff(before['hd'], after['hd']),
                              'scene_output': diff(before['output'], after['output'])})
        print(json.dumps(res['rounds'][-1]), flush=True)
    log = g.log()
    res['original_lines'] = [l for l in log.splitlines() if l.startswith('original ')][-1:]
    res['problems'] = [l for l in log.splitlines() if 'original_present_failed' in l or 'defer_mismatch' in l or 'asset error' in l][:5]
except Exception as e:
    res['error'] = repr(e)
finally:
    res['normal_exit'] = g.close_normally()
    flag.unlink(missing_ok=True)
    qa.dump(f'chron-close-{label}.json', res)
    print(json.dumps({k: v for k, v in res.items() if k != 'rounds'}, ensure_ascii=False))
