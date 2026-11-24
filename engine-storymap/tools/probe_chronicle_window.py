"""Where the 연표's moving content is visible: 1x page captures at five scroll positions (set at once with WM_APP+83),
compared pixel by pixel; what changes between positions is content, what never changes is frame and UI. Numbers only,
captures deleted. Also writes qa/chronicle_chrome.png: the page at (0,0) with the content area (19..770, 71..574) blacked
out, so the frame and its buttons can be looked at without any chronicle entry (for placing the zoom button).
python probe_chronicle_window.py   -> qa/chronicle_window.json, qa/chronicle_chrome.png
"""
import json
import re
import time

import numpy as np
from PIL import Image

import qa
import test_chronicle_perf as T

WM_APP = 0x8000
MOVED = re.compile(r'chronicle_moved ok=(\d) at=(-?\d+),(-?\d+) max=(-?\d+),(-?\d+)')


def runs(mask):
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

        def capture(n):
            for p in shots.glob(f'quality-{n:02d}-*.bmp'):
                p.unlink()
            g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
            g.until(lambda: (shots / f'quality-{n:02d}-base.bmp').exists(), 20, f'capture {n}')
            time.sleep(.8)
            return np.asarray(Image.open(shots / f'quality-{n:02d}-base.bmp').convert('RGB')).astype(np.int16)

        pages, moved = [], []
        for i, (x, y) in enumerate([(0, 0), (300, 1000), (869, 5431), (500, 3000), (128, 88)]):
            n = len(MOVED.findall(g.log()))
            g.post(g.hwnd, WM_APP + 83, x, y)
            g.until(lambda: len(MOVED.findall(g.log())) > n, 10, f'move {x},{y}')
            moved.append(MOVED.findall(g.log())[-1])
            time.sleep(1.0)
            pages.append(capture(i + 1))
        r['moved'] = moved
        stack = np.stack(pages)
        changes = (stack.max(axis=0) - stack.min(axis=0)).max(axis=2) > 8          # 600 x 800
        r['changing_pixels'] = int(changes.sum())
        ys, xs = np.where(changes)
        r['changing_box'] = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if len(xs) else None
        body = changes[114:574, :]
        r['cols_changing_in_body_rows'] = runs(body.mean(axis=0) > 0.02)
        r['rows_changing_in_body_cols'] = [(a + 0, b) for a, b in runs(changes[:, 95:770].mean(axis=1) > 0.02)]
        r['header_row_cols'] = runs(changes[71:114, :].mean(axis=0) > 0.02)
        r['left_col_rows'] = runs(changes[:, 19:95].mean(axis=1) > 0.02)
        chrome = pages[0].copy()
        chrome[71:574, 19:770] = 0
        Image.fromarray(chrome.astype(np.uint8)).save(qa.QA / 'chronicle_chrome.png')
    except Exception as e:  # noqa: BLE001
        r['error'] = repr(e)
    finally:
        r['normal_exit'] = g.close_normally()
        for p in shots.glob('quality-*.bmp'):
            p.unlink()
    return r


if __name__ == '__main__':
    res = run()
    (qa.QA / 'chronicle_window.json').write_text(json.dumps(res, indent=1), 'utf-8')
    for k, v in res.items():
        print(k, v)
