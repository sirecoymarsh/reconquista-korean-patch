"""연표 wheel zoom (ChronicleZoom, 10-25) on runtime-chron, timing-only perf mode. In-engine captures (WM_APP+80: the 4x page
and the presented frame) are compared as numbers only and deleted at the end; nothing is looked at or kept.
- zoom in 3 notches at a point: the presented frame must match the 4x page's zoom area scaled to the window, and the point
  under the cursor must stay put; - arrows and a drag while zoomed: positions from the chronicle_scroll log;
- zoom out 3 notches: back to the whole page.
python test_chronicle_zoom.py   -> qa/test_chronicle_zoom.json
"""
import math
import re
import time

import numpy as np
from PIL import Image

import qa
import test_chronicle_perf as T

WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_KEYDOWN, WM_KEYUP, WM_MOUSEWHEEL, WM_APP = 0x200, 0x201, 0x202, 0x100, 0x101, 0x20A, 0x8000
ZOOM = re.compile(r'chronicle_zoom level=([\d.]+) area=([\d.]+),([\d.]+),([\d.]+),([\d.]+) at=(-?\d+),(-?\d+)')   # the overview= part after it is ignored
SCROLL = re.compile(r'chronicle_scroll msg=\w+ at=(-?\d+),(-?\d+) target=(-?\d+),(-?\d+)')


def psnr(a, b):
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return 99.0 if mse == 0 else round(10 * math.log10(65025 / mse), 2)


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
        client = qa.w.RECT()
        qa.u.GetClientRect(g.hwnd, qa.c.byref(client))
        cw, ch = client.right, client.bottom
        vw, vh = (ch * 4 // 3, ch) if cw * 3 > ch * 4 else (cw, cw * 3 // 4)
        vx, vy = (cw - vw) // 2, (ch - vh) // 2
        r['viewport'] = (vx, vy, vw, vh)

        def screen(x, y):
            p = qa.w.POINT(x, y)
            qa.u.ClientToScreen(g.hwnd, qa.c.byref(p))
            return p.x, p.y

        def wheel(notches, x, y):
            sx, sy = screen(x, y)
            for _ in range(abs(notches)):
                g.post(g.hwnd, WM_MOUSEWHEEL, ((120 if notches > 0 else -120) & 0xffff) << 16, ((sy & 0xffff) << 16) | (sx & 0xffff))
                time.sleep(.2)

        def capture(n):
            for p in shots.glob(f'quality-{n:02d}-*.bmp'):
                p.unlink()
            g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
            g.until(lambda: (shots / f'quality-{n:02d}-output.bmp').exists(), 20, f'capture {n}')
            time.sleep(.8)
            out = np.asarray(Image.open(shots / f'quality-{n:02d}-output.bmp').convert('RGB'))
            hd = Image.open(shots / f'quality-{n:02d}-hd.bmp').convert('RGB')
            return out, hd

        def key(vk):
            g.post(g.hwnd, WM_KEYDOWN, vk, 1)
            g.post(g.hwnd, WM_KEYUP, vk, 0xc0000001)
            time.sleep(1.2)

        def position():
            key(0x27)                                    # → logs where it was; ← puts it back
            at = SCROLL.findall(g.log())[-1]
            key(0x25)
            return int(at[0]), int(at[1])

        out1, hd1 = capture(1)
        frame_of = lambda out: out[vy:vy + vh, vx:vx + vw]   # noqa: E731
        whole = np.asarray(hd1.resize((vw, vh), Image.BICUBIC))
        r['unzoomed_vs_whole_page_psnr'] = psnr(frame_of(out1), whole)

        px, py = vx + int(vw * .7), vy + int(vh * .4)       # zoom at 70% across, 40% down
        n = len(ZOOM.findall(g.log()))
        wheel(3, px, py)
        g.until(lambda: len(ZOOM.findall(g.log())) >= n + 3, 10, 'zoom lines')
        level, zx, zy, zw, zh, ax, ay = map(float, ZOOM.findall(g.log())[-1])
        r['zoom_in'] = {'level': level, 'area': (zx, zy, zw, zh), 'cursor_client': (ax, ay)}
        time.sleep(1.5)
        out2, hd2 = capture(2)
        crop = hd2.crop((round(zx * 4), round(zy * 4), round((zx + zw) * 4), round((zy + zh) * 4))).resize((vw, vh), Image.BICUBIC)
        r['zoomed_vs_zoom_area_psnr'] = psnr(frame_of(out2), np.asarray(crop))
        r['zoomed_vs_whole_page_psnr'] = psnr(frame_of(out2), np.asarray(hd2.resize((vw, vh), Image.BICUBIC)))   # must be far lower
        # the logical point under the cursor before and after
        before = ((px - vx) / vw * 800, (py - vy) / vh * 600)
        after = (zx + (px - vx) / vw * zw, zy + (py - vy) / vh * zh)
        r['point_under_cursor'] = {'before': before, 'after': after}

        p0 = position()
        g.post(g.hwnd, WM_MOUSEMOVE, 0, ((vy + vh // 2) << 16) | (vx + vw // 2))
        time.sleep(.3)
        g.post(g.hwnd, WM_LBUTTONDOWN, 1, ((vy + vh // 2) << 16) | (vx + vw // 2))
        for i in range(1, 11):
            x = vx + vw // 2 - i * vw // 40               # 1/4 of the window to the left, in 10 steps
            g.post(g.hwnd, WM_MOUSEMOVE, 1, ((vy + vh // 2) << 16) | x)
            time.sleep(.08)
        g.post(g.hwnd, WM_LBUTTONUP, 0, ((vy + vh // 2) << 16) | (vx + vw // 2 - vw // 4))
        time.sleep(1.5)
        p1 = position()
        r['drag_zoomed'] = {'before': p0, 'after': p1, 'window_px': vw // 4, 'expected_logical_if_followed': round(vw / 4 * zw / vw, 1)}

        wheel(-3, px, py)
        time.sleep(1.5)
        level_out = float(ZOOM.findall(g.log())[-1][0])
        out3, hd3 = capture(3)
        r['zoom_out'] = {'level': level_out, 'vs_whole_page_psnr': psnr(frame_of(out3), np.asarray(hd3.resize((vw, vh), Image.BICUBIC)))}
        wheel(5, vx + 2, vy + 2)                            # corner: the area must stay inside the page
        r['corner_zoom'] = ZOOM.findall(g.log())[-1]
        wheel(-9, vx + 2, vy + 2)
        r['after_all_out'] = ZOOM.findall(g.log())[-1]
    except Exception as e:  # noqa: BLE001
        r['error'] = repr(e)
    finally:
        r['normal_exit'] = g.close_normally()
        for p in shots.glob('quality-*.bmp'):
            p.unlink()
    return r


if __name__ == '__main__':
    res = run()
    qa.dump('test_chronicle_zoom.json', res)
    for k, v in res.items():
        print(k, v)
