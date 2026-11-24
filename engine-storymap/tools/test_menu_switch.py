"""Menu screens switching (the user, 10-25: 「메뉴가 아주 천천히 바뀌어 잔상이 남는 식인건 여전하네」), after test_menu.py
showed the right-click menu itself opening in 0.4 s: runtime-test, 도입부 2's last scene; the menu is opened, an item is
clicked (저장하기, then 설정), and each switch and each way back (right click) is captured at fixed times, base and hd.
python test_menu_switch.py <label>   -> qa/menuswitch-<label>/<step>-base.png, -hd.png (hd at 1/2), qa/menuswitch-<label>.json
"""
import json
import sys
import time

import numpy as np
from PIL import Image

import qa
from test_hitch import WM_APP, to_intro2

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
out = qa.QA / f'menuswitch-{label}'
out.mkdir(parents=True, exist_ok=True)
g = qa.Game(extra_env={'RECON_PERF': '2'})
result = {'label': label, 'steps': []}
shots = qa.RUN / 'qa'
n = 0
TIMES = (0.2, 0.6, 1.2, 2.5)
ITEMS = {'save': (634, 56), 'config': (634, 304)}


def capture(step):
    global n
    n += 1
    for p in shots.glob(f'quality-{n:02d}-*.bmp'):
        p.unlink()
    g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
    g.until(lambda: (shots / f'quality-{n:02d}-output.bmp').exists(), 20, f'capture {step}')
    time.sleep(.3)
    base = Image.open(shots / f'quality-{n:02d}-base.bmp').convert('RGB')
    hd = Image.open(shots / f'quality-{n:02d}-hd.bmp').convert('RGB')
    base.save(out / f'{step}-base.png')
    hd.resize((hd.width // 2, hd.height // 2), Image.LANCZOS).save(out / f'{step}-hd.png')
    small = np.asarray(hd.resize(base.size, Image.BOX)).astype(np.int16)
    d = np.abs(small - np.asarray(base).astype(np.int16)).max(axis=2)
    row = {'step': step, 'hd_vs_base_over48': int((d > 48).sum()), 'mean_luma': round(float(np.asarray(base.convert('L')).mean()), 1)}
    result['steps'].append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)


def act(name, do):
    do()
    t = time.perf_counter()
    for at in TIMES:
        time.sleep(max(0, at - (time.perf_counter() - t)))
        capture(f'{name}-{at:.1f}s')


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
    g.logical_click(g.hwnd, 400, 300, button='right')     # hides the message window
    time.sleep(1.5)
    act('1-menu', lambda: g.logical_click(g.hwnd, 400, 300, button='right'))
    for i, key in enumerate(ITEMS, start=2):
        x, y = ITEMS[key]
        g.move(g.hwnd, x, y)
        time.sleep(.8)
        act(f'{i}-{key}', lambda: g.logical_click(g.hwnd, x, y))
        act(f'{i}-{key}-back', lambda: g.logical_click(g.hwnd, 400, 300, button='right'))
except Exception as e:  # noqa: BLE001
    result['error'] = repr(e)
finally:
    result['normal_exit'] = g.close_normally()
qa.dump(f'menuswitch-{label}.json', result)
print(json.dumps({k: v for k, v in result.items() if k != 'steps'}, ensure_ascii=False))
