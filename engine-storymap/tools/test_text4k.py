"""4K dialogue text, before and after a fix (the user, 10-25: 「글자를 4K로 만들려 했는데 흐리게 나오네」): runtime-test,
도입부 2's last scene (the reading route of test_hitch, spoiler-safe), three text pages, 12 clicks apart, captured as the player sees them
(quality-NN-output.bmp, the scaled screen) and at 4x (quality-NN-hd.bmp), with the text4k counters from the log.
python test_text4k.py <label>   -> qa/text4k-<label>/page<N>-output.png, page<N>-hd.png; qa/text4k-<label>.json
"""
import json
import re
import shutil
import sys
import time

from PIL import Image

import qa
from test_hitch import WM_APP, mark, to_intro2

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
out = qa.QA / f'text4k-{label}'
out.mkdir(parents=True, exist_ok=True)
g = qa.Game(extra_env={'RECON_PERF': '2'})
result = {'label': label}
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
    shots = qa.RUN / 'qa'
    for n in (1, 2, 3):
        time.sleep(4)                                          # the page fully shown
        for p in shots.glob(f'quality-{n:02d}-*.bmp'):
            p.unlink()
        g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
        g.until(lambda: (shots / f'quality-{n:02d}-output.bmp').exists(), 20, f'capture {n}')
        time.sleep(1)
        for kind in ('output', 'hd'):
            Image.open(shots / f'quality-{n:02d}-{kind}.bmp').convert('RGB').save(out / f'page{n}-{kind}.png')
        for _ in range(12):                                  # on to a later page: speech with 「」 and …
            g.logical_click(g.hwnd, 400, 520)
            time.sleep(1.0)
    stats = re.findall(r'^text4k (lines=.*)$', g.log(), re.M)
    if stats:
        result['text4k'] = dict(kv.split('=') for kv in stats[-1].split())
except Exception as e:  # noqa: BLE001
    result['error'] = repr(e)
finally:
    result['normal_exit'] = g.close_normally()
qa.dump(f'text4k-{label}.json', result)
print(json.dumps(result, ensure_ascii=False))
