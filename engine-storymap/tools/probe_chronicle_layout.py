"""Which part of the 연표 screen scrolls, measured as numbers only (captures are deleted; nothing is looked at): 1x page
captures before and after ↓ (y+88) and → (x+128). For every row and column, whether it matches the other capture moved
by the scroll step (scrolling content) or unmoved (fixed frame and headers). runtime-chron, timing-only perf mode.
python probe_chronicle_layout.py   -> qa/chronicle_layout.json
"""
import json
import re
import time

import numpy as np
from PIL import Image

import qa
import test_chronicle_perf as T

WM_KEYDOWN, WM_KEYUP, WM_APP = 0x100, 0x101, 0x8000
SCROLL = re.compile(r'chronicle_scroll msg=\w+ at=(-?\d+),(-?\d+) target=(-?\d+),(-?\d+) max=(-?\d+),(-?\d+)')


def runs(mask):
    """[start, end) runs of True in a 1-D bool array."""
    out, start = [], None
    for i, v in enumerate(list(mask) + [False]):
        if v and start is None:
            start = i
        if not v and start is not None:
            out.append((start, i))
            start = None
    return out


def run():
    g = qa.Game(run=T.RUN, extra_env={'RECON_PERF': '2'})
    shots = T.RUN / 'qa'
    r = {}
    try:
        frame = T.keys('クロニクル枠')
        g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
        g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
        if not qa.u.IsWindowVisible(g.hwnd):
            qa.u.ShowWindow(g.hwnd, 4)
        time.sleep(4)

        def key(vk, n=1):
            for _ in range(n):
                g.post(g.hwnd, WM_KEYDOWN, vk, 1)
                g.post(g.hwnd, WM_KEYUP, vk, 0xc0000001)
                time.sleep(1.4)

        def capture(n):
            for p in shots.glob(f'quality-{n:02d}-*.bmp'):
                p.unlink()
            g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
            g.until(lambda: (shots / f'quality-{n:02d}-base.bmp').exists(), 20, f'capture {n}')
            time.sleep(.8)
            return np.asarray(Image.open(shots / f'quality-{n:02d}-base.bmp').convert('RGB')).astype(np.int16)

        key(0x25, 9)                      # ← and ↑ to the top-left corner first, then one step in from it
        key(0x26, 70)
        key(0x27)
        key(0x28)
        pos0 = SCROLL.findall(g.log())[-1]
        a = capture(1)
        key(0x28)                         # ↓: content moves up by 88
        b = capture(2)
        key(0x26)
        key(0x27)                         # →: content moves left by 128
        c = capture(3)
        r['positions'] = [SCROLL.findall(g.log())[i] for i in (-4, -3, -2, -1)] + [pos0]
        h, w = a.shape[:2]
        same_y = np.array([np.abs(a[y] - b[y]).max() <= 8 for y in range(h)])
        moved_y = np.array([y + 88 < h and np.abs(a[y + 88] - b[y]).max() <= 8 for y in range(h)])
        same_x = np.array([np.abs(a[:, x] - c[:, x]).max() <= 8 for x in range(w)])
        moved_x = np.array([x + 128 < w and np.abs(a[:, x + 128] - c[:, x]).max() <= 8 for x in range(w)])
        # per region: rows that slide with ↓ (in the body columns), columns that slide with →
        r['rows_moving_with_down'] = runs(moved_y & ~same_y)
        r['rows_fixed_on_down'] = runs(same_y)
        r['cols_moving_with_right'] = runs(moved_x & ~same_x)
        r['cols_fixed_on_right'] = runs(same_x)
        # finer: inside each row band, which columns slide (a header column stays put while rows move, and so on)
        band = [y for y in range(h - 88) if moved_y[y] or not same_y[y]]
        if band:
            cols_moving_in_body = [x for x in range(w) if np.abs(a[band[0] + 88:band[-1] + 1, x] - b[band[0]:band[-1] + 1 - 88, x]).max() <= 8]
            r['cols_sliding_vertically'] = runs(np.isin(np.arange(w), cols_moving_in_body))
        colband = [x for x in range(w - 128) if moved_x[x] or not same_x[x]]
        if colband:
            rows_moving_in_body = [y for y in range(h) if np.abs(a[y, colband[0] + 128:colband[-1] + 1] - c[y, colband[0]:colband[-1] + 1 - 128]).max() <= 8]
            r['rows_sliding_horizontally'] = runs(np.isin(np.arange(h), rows_moving_in_body))
        r['diff_down_rows'] = runs(~same_y)
        r['diff_right_cols'] = runs(~same_x)
    except Exception as e:  # noqa: BLE001
        r['error'] = repr(e)
    finally:
        r['normal_exit'] = g.close_normally()
        for p in shots.glob('quality-*.bmp'):
            p.unlink()
    return r


if __name__ == '__main__':
    res = run()
    (qa.QA / 'chronicle_layout.json').write_text(json.dumps(res, indent=1, default=str), 'utf-8')
    for k, v in res.items():
        print(k, v)
