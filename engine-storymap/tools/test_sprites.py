"""Standing pictures in 4K (base + face patch): runtime-test, the story map's 도입부 1 card <order> (default 80, just
before the first standing picture), then clicks, capturing the 4x screen after each; the log's asset lines show which
pictures came as a patch on a base (patch_on=) or as a shared mask (file=).
python test_sprites.py <label> [order] [clicks]   -> qa/sprites-<label>/<n>-hd.png, <n>-base.png; qa/sprites-<label>.json
Only 도입부 1 is shown (the user's progress).
"""
import json
import re
import sys
import time

from PIL import Image

import qa
from test_hitch import VK, WM_APP

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
order = int(sys.argv[2]) if len(sys.argv) > 2 else 80
clicks = int(sys.argv[3]) if len(sys.argv) > 3 else 4
out = qa.QA / f'sprites-{label}'
out.mkdir(parents=True, exist_ok=True)
g = qa.Game(extra_env={'RECON_PERF': '2', 'RECON_HD_START_FULLSCREEN': '1'})   # the test copy's own setting went windowed (10-25 night)
result = {'label': label, 'order': order, 'steps': []}
shots = qa.RUN / 'qa'
n = 0


def capture(step):
    global n
    n += 1
    for p in shots.glob(f'quality-{n:02d}-*.bmp'):
        p.unlink()
    g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
    g.until(lambda: (shots / f'quality-{n:02d}-output.bmp').exists(), 20, f'capture {step}')
    time.sleep(.3)
    Image.open(shots / f'quality-{n:02d}-base.bmp').convert('RGB').save(out / f'{step}-base.png')
    Image.open(shots / f'quality-{n:02d}-hd.bmp').convert('RGB').save(out / f'{step}-hd.png')
    for p in shots.glob(f'quality-{n:02d}-*.bmp'):
        p.unlink()


try:
    (qa.RUN / 'storymap-read.bin').unlink(missing_ok=True)
    # title1_push (1de0628c) loads only under the cursor; a windowed start (10-25 night) never hovers it: title1_off too
    g.until(lambda: 'asset 1de0628c ' in g.log() or 'asset ef1f6a40 ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(3)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open')
    child = g.child()
    time.sleep(.5)
    g.key(child, VK['RET'])                      # the chapter the cursor starts on: 도입부 1
    g.until(lambda: re.search(r'page=2 chapter=\d+', g.log()), 10, 'chapter page')
    result['chapter'] = re.findall(r'page=2 chapter=(\d+)', g.log())[-1]
    # RIGHT moves a scene (a run of cards), DOWN a card inside it and logs its order: walk down to the card
    def items():
        return re.findall(r'item=\d+ kind=\d+ order=(\d+)', g.log())
    at, seen = 1, len(items())                       # entering the chapter selects its first card (order 1)
    for _ in range(600):
        if at >= order:
            break
        g.key(child, VK['DOWN'])
        time.sleep(.12)
        got = items()
        if len(got) > seen and int(got[-1]) != at:   # (DOWN on a scene's last card logs that card again)
            at, seen = int(got[-1]), len(got)
            continue
        seen = len(got)
        g.key(child, VK['RIGHT'])                    # no next card here: the next scene starts on the next order
        time.sleep(.3)
        at += 1
    result['card_order'] = at
    assert at == order, (at, order)
    time.sleep(.5)
    g.story_jump(child)
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    got = int(g.log().split('inflow jump order=')[-1].split()[0])
    result['jump_order'] = got
    g.until(lambda: f'inflow arrived order={got} ' in g.log(), 120, 'arrival')
    last = len(g.log())
    time.sleep(2.5)
    # the test copy has not read these pages, so a jump stops at the first unread one: page on until a standing picture
    # loads (the first comes after 도입부 1 card 80), then capture
    if '--until-sprite' in sys.argv:                 # no click budget (a click may only finish a line): a time limit
        t0, k = time.time(), 0
        while time.time() - t0 < 420 and not re.search(r'load call (?:b_)?(?:momi|masa|kami|sio|maho|sina)_\w+\.rct', g.log()[last:]):
            g.logical_click(g.hwnd, 400, 520)
            k += 1
            time.sleep(.3)
        result['pages_clicked'] = k
        result['sprite_seen'] = bool(re.search(r'load call (?:b_)?(?:momi|masa|kami|sio|maho|sina)_\w+\.rct', g.log()[last:]))
        time.sleep(1.5)
    for i in range(clicks + 1):
        if i:
            g.logical_click(g.hwnd, 400, 520)
            time.sleep(2.0)
        log = g.log()
        assets = re.findall(r'asset ([0-9a-f]{8}) (\d+x\d+) -> (\d+x\d+)(.*)', log[last:])
        loads = sorted(set(re.findall(r'load call (\S+)', log[last:])))
        last = len(log)
        capture(i)
        step = {'step': i, 'loaded': loads, 'assets': [' '.join(a).strip() for a in assets]}
        result['steps'].append(step)
        print(json.dumps(step, ensure_ascii=False), flush=True)
    result['sprites_line'] = [l for l in g.log().splitlines() if l.startswith('sprites ')][:1]
    result['errors'] = [l for l in g.log().splitlines() if l.startswith(('asset error', 'jxl_error'))][:10]
except Exception as e:
    result['error'] = repr(e)
finally:
    result['normal_exit'] = g.close_normally()
    qa.dump(f'sprites-{label}.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'steps'}, ensure_ascii=False))
