"""Is something at a fixed place on the 연표 screen changing by itself? Three 1x captures of one position, 1.5 s apart, with
the cursor parked over the frame corner: per 4-row band of the page, how much changed between captures. Numbers only;
captures deleted. python probe_chronicle_band.py -> printed
"""
import time

import numpy as np
from PIL import Image

import qa
import test_chronicle_perf as T

WM_MOUSEMOVE, WM_APP = 0x200, 0x8000


def run():
    g = qa.Game(run=T.RUN, extra_env={'RECON_PERF': '2'})
    shots = T.RUN / 'qa'
    out = {}
    try:
        frame = T.keys('クロニクル枠')
        g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
        g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
        if not qa.u.IsWindowVisible(g.hwnd):
            qa.u.ShowWindow(g.hwnd, 4)
        time.sleep(4)
        cr = qa.w.RECT()
        qa.u.GetClientRect(g.hwnd, qa.c.byref(cr))
        cw, ch = cr.right, cr.bottom
        vw, vh = (ch * 4 // 3, ch) if cw * 3 > ch * 4 else (cw, cw * 3 // 4)
        vx, vy = (cw - vw) // 2, (ch - vh) // 2
        g.post(g.hwnd, WM_MOUSEMOVE, 0, ((vy + vh * 599 // 600) << 16) | (vx + vw * 799 // 800))
        g.post(g.hwnd, WM_APP + 83, 400, 2000)
        time.sleep(1.5)
        pages = []
        for n in range(1, 4):
            for p in shots.glob(f'quality-{n:02d}-*.bmp'):
                p.unlink()
            g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
            g.until(lambda: (shots / f'quality-{n:02d}-base.bmp').exists(), 20, f'capture {n}')
            time.sleep(.8)
            pages.append(np.asarray(Image.open(shots / f'quality-{n:02d}-base.bmp').convert('RGB')).astype(np.int16))
            time.sleep(1.5)
        for i in (0, 1):
            d = np.abs(pages[i] - pages[i + 1]).max(axis=2)
            bands = [(y, round(float(d[y:y + 4].mean()), 2), int(d[y:y + 4].max())) for y in range(0, 600, 4) if d[y:y + 4].max() > 8]
            ys, xs = np.where(d > 8)
            out[f'change_{i + 1}_{i + 2}'] = {'bands': bands[:30], 'box': (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if len(xs) else None}
    except Exception as e:  # noqa: BLE001
        out['error'] = repr(e)
    finally:
        out['normal_exit'] = g.close_normally()
        for p in shots.glob('quality-*.bmp'):
            p.unlink()
    return out


if __name__ == '__main__':
    for k, v in run().items():
        print(k, v)
