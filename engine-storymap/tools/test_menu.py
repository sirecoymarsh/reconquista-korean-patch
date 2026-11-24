"""Menus changing slowly with an afterimage (the user, 10-25: 「메뉴가 아주 천천히 바뀌어 잔상이 남는 식인건 여전하네」).
runtime-test, 도입부 2's last scene (the reading route of test_hitch, spoiler-safe): the right-click menu is opened and
closed, and the screen is captured at fixed times after each click, as the engine has it (base, 800x600) and as the 4K
layer has it (hd, 3200x2400). Each pair is compared: hd scaled to 800x600 against base, so a 4K picture left behind (an
afterimage of the layer, not of the game) shows as a region where they differ.
python test_menu.py <label> [hover x,y x,y ...]   -> qa/menu-<label>/<step>-base.png, -hd.png (hd at 1/2), qa/menu-<label>.json
"""
import json
import sys
import time

import numpy as np
from PIL import Image

import qa
from test_hitch import WM_APP, to_intro2

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
hover = [tuple(int(v) for v in a.split(',')) for a in sys.argv[2:]]
out = qa.QA / f'menu-{label}'
out.mkdir(parents=True, exist_ok=True)
g = qa.Game(extra_env={'RECON_PERF': '2'})
result = {'label': label, 'steps': []}
shots = qa.RUN / 'qa'
n = 0


def capture(step):
    """the screen now, base and hd, and how far hd (scaled down) is from base"""
    global n
    n += 1
    for p in shots.glob(f'quality-{n:02d}-*.bmp'):
        p.unlink()
    t0 = time.perf_counter()
    g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
    g.until(lambda: (shots / f'quality-{n:02d}-output.bmp').exists(), 20, f'capture {step}')
    time.sleep(.3)
    base = Image.open(shots / f'quality-{n:02d}-base.bmp').convert('RGB')
    hd = Image.open(shots / f'quality-{n:02d}-hd.bmp').convert('RGB')
    small = np.asarray(hd.resize(base.size, Image.BOX)).astype(np.int16)
    d = np.abs(small - np.asarray(base).astype(np.int16)).max(axis=2)
    ys, xs = np.nonzero(d > 48)
    box = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None
    base.save(out / f'{step}-base.png')
    hd.resize((hd.width // 2, hd.height // 2), Image.LANCZOS).save(out / f'{step}-hd.png')
    row = {'step': step, 'capture_s': round(time.perf_counter() - t0, 2), 'hd_vs_base_over48': int((d > 48).sum()), 'box': box,
           'mean_diff': round(float(d.mean()), 2)}
    result['steps'].append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)


try:
    (qa.RUN / 'storymap-read.bin').unlink(missing_ok=True)
    g.until(lambda: 'asset 1de0628c ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    to_intro2(g)
    time.sleep(4)
    capture('0-reading')
    g.logical_click(g.hwnd, 400, 300, button='right')     # the first right click hides the message window
    time.sleep(1.5)
    g.logical_click(g.hwnd, 400, 300, button='right')     # the second opens the menu (buttons at x 634, y 56 + 62*i)
    t = time.perf_counter()
    for at in (0.15, 0.4, 0.8, 1.5):
        time.sleep(max(0, at - (time.perf_counter() - t)))
        capture(f'1-open-{at:.2f}s')
    for i, (x, y) in enumerate(hover):
        g.move(g.hwnd, x, y)
        t = time.perf_counter()
        for at in (0.1, 0.5):
            time.sleep(max(0, at - (time.perf_counter() - t)))
            capture(f'2-hover{i}-{at:.1f}s')
    g.logical_click(g.hwnd, 400, 300, button='right')     # close it
    t = time.perf_counter()
    for at in (0.15, 0.4, 0.8, 1.5, 3.0):
        time.sleep(max(0, at - (time.perf_counter() - t)))
        capture(f'3-close-{at:.2f}s')
except Exception as e:  # noqa: BLE001
    result['error'] = repr(e)
finally:
    result['normal_exit'] = g.close_normally()
qa.dump(f'menu-{label}.json', result)
print(json.dumps({k: v for k, v in result.items() if k != 'steps'}, ensure_ascii=False))
