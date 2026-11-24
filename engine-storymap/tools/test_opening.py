"""The opening's sky (the user, 10-25: 「실제 오프닝 부분 하늘 보면 검은색 사각형 무늬가 있어」): runtime-test, the story map's
first chapter from its first scene card, the screen captured as the engine has it (base, 800x600) and as the 4K layer
has it (hd, 3200x2400) after each of the first clicks, with the 4K picture names the engine loaded just before.
python test_opening.py <label> [clicks]   -> qa/opening-<label>/<n>-base.png, <n>-hd.png (full size), qa/opening-<label>.json
"""
import json
import re
import sys
import time

from PIL import Image

import qa
from test_hitch import VK, WM_APP

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
clicks = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 10
out = qa.QA / f'opening-{label}'
out.mkdir(parents=True, exist_ok=True)
g = qa.Game(extra_env={'RECON_PERF': '2'})
result = {'label': label, 'steps': []}
shots = qa.RUN / 'qa'
n = 0


def capture(step):
    global n
    n += 1
    for p in shots.glob(f'quality-{n:02d}-*.bmp'):
        p.unlink()
    mark = len(g.log())
    g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
    g.until(lambda: (shots / f'quality-{n:02d}-output.bmp').exists(), 20, f'capture {step}')
    time.sleep(.3)
    Image.open(shots / f'quality-{n:02d}-base.bmp').convert('RGB').save(out / f'{step}-base.png')
    Image.open(shots / f'quality-{n:02d}-hd.bmp').convert('RGB').save(out / f'{step}-hd.png')
    return mark


try:
    (qa.RUN / 'storymap-read.bin').unlink(missing_ok=True)
    g.until(lambda: 'asset 1de0628c ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open')
    child = g.child()
    time.sleep(.5)
    g.key(child, VK['RET'])                      # the chapter the cursor starts on
    g.until(lambda: re.search(r'page=2 chapter=\d+', g.log()), 10, 'chapter page')
    result['chapter'] = re.findall(r'page=2 chapter=(\d+)', g.log())[-1]
    time.sleep(.5)
    g.story_jump(child)                      # its first scene card
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    order = int(g.log().split('inflow jump order=')[-1].split()[0])
    g.until(lambda: f'inflow arrived order={order} ' in g.log(), 120, 'arrival')
    last = len(g.log())
    time.sleep(2.5)
    if '--audit' in sys.argv:                    # which shadow holds thin dark lines its 1x bitmap lacks (perf op 7)
        g.post(g.hwnd, WM_APP + 80, 7, 0)
        g.until(lambda: 'lines_audit done' in g.log(), 120, 'line audit')
        result['audit'] = re.findall(r'lines_audit rank=\d+ .*', g.log())[:12]
        for a in result['audit']:
            print(a, flush=True)
    for i in range(clicks + 1):
        if i:
            g.logical_click(g.hwnd, 400, 520)
            time.sleep(1.8)
        log = g.log()
        loads = sorted(set(re.findall(r'load call (\S+)', log[last:])))
        last = len(log)
        capture(f'{i:02d}')
        result['steps'].append({'step': i, 'loaded': loads})
        print(json.dumps(result['steps'][-1], ensure_ascii=False), flush=True)
except Exception as e:  # noqa: BLE001
    result['error'] = repr(e)
finally:
    result['normal_exit'] = g.close_normally()
qa.dump(f'opening-{label}.json', result)
print(json.dumps({k: v for k, v in result.items() if k != 'steps'}, ensure_ascii=False))
