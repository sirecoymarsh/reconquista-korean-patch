"""4x screen crops of text for checking text sharpness (perf capture WM_APP+80). Dialogue: runtime-test after the
test_text_speed route (도입부 2); chronicle: runtime-chron, the left date column only. Crops go to the scratchpad given.
python capture_text_crops.py <out_dir>
"""
import sys
import time
from pathlib import Path

from PIL import Image

import qa
import test_chronicle_perf as T

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
WM_PERF = 0x8000 + 80


def grab(g, run, cid, name, box):
    g.post(g.hwnd, WM_PERF, 10 + cid, 0)
    g.until(lambda: f'quality_capture id={cid} ' in g.log(), 20, 'capture')
    time.sleep(.5)
    hd = Image.open(run / 'qa' / f'quality-{cid:02d}-hd.bmp').convert('RGB')
    hd.crop(box).save(OUT / f'{name}.png')
    for p in (run / 'qa').glob('quality-*'):
        p.unlink()


# chronicle: date column (logical x 0..95, y 71..574) -> 4x
g = qa.Game(run=T.RUN, extra_env={'RECON_PERF': '1'})
try:
    frame = T.keys('クロニクル枠')
    g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    time.sleep(4)
    grab(g, T.RUN, 1, 'chronicle-dates-4x', (0, 71 * 4, 96 * 4, 300 * 4))
finally:
    print('chronicle normal_exit', g.close_normally())

# dialogue: same route as test_text_speed, then two clicks
import test_text_speed as S  # noqa: E402
(qa.RUN / 'storymap-read.bin').unlink(missing_ok=True)
g = qa.Game(extra_env={'RECON_PERF': '1'})
try:
    g.until(lambda: 'asset 1de0628c ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    VK = S.VK
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open')
    child = g.child()
    g.key(child, VK['RIGHT'])
    g.until(lambda: 'cursor=' in g.log(), 10, 'cursor move')
    g.key(child, VK['RET'])
    g.until(lambda: 'page=2 chapter=3' in g.log(), 10, 'chapter page')
    n = g.count('inflow snapshot')
    g.key(child, VK['RIGHT'], 34, .03)
    g.until(lambda: g.count('inflow snapshot') >= n + 34, 30, 'scene steps')
    time.sleep(.5)
    n = g.count('inflow snapshot')
    g.key(child, VK['END'])
    g.until(lambda: g.count('inflow snapshot') > n, 10, 'end')
    g.key(child, VK['UP'])
    time.sleep(.4)
    g.story_jump(child)
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    order = int(g.log().split('inflow jump order=')[-1].split()[0])
    g.until(lambda: f'inflow arrived order={order} ' in g.log(), 120, 'arrival')
    time.sleep(3)
    g.logical_click(g.hwnd, 400, 520)
    time.sleep(3)
    grab(g, qa.RUN, 2, 'dialogue-box-4x', (60 * 4, 440 * 4, 520 * 4, 580 * 4))
finally:
    print('dialogue normal_exit', g.close_normally())
print('saved to', OUT)
