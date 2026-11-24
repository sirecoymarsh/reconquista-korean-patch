"""연표 whole-table view (overview.inc, 10-25) on runtime-chron, timing-only perf mode. Numbers only: every capture and the
dumped table picture are deleted at the end (the table holds later chronicle entries; nothing is looked at).
- wheel down at 1x collects the table (how many positions, how long), then shows it;
- the collected picture against direct captures at tile and in-between positions (seams would show here);
- the shown table area against the picture scaled the same way, and against a shifted part (must be far worse);
- drag pans by the dragged distance / zoom; a click returns to 1x with the clicked point under the cursor;
- the button returns to 1x with the middle kept; all the way out shows the whole table.
python test_chronicle_overview.py   -> qa/test_chronicle_overview.json
"""
import math
import re
import time

import numpy as np
from PIL import Image

import qa
import test_chronicle_perf as T

WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_KEYDOWN, WM_KEYUP, WM_MOUSEWHEEL, WM_APP = 0x200, 0x201, 0x202, 0x100, 0x101, 0x20A, 0x8000
ZOOM = re.compile(r'chronicle_zoom level=([\d.]+) area=[\d.,]+ at=(-?\d+),(-?\d+) overview=(-?[\d.]+),(-?[\d.]+)')
MOVED = re.compile(r'chronicle_moved ok=(\d) at=(-?\d+),(-?\d+) max=(-?\d+),(-?\d+)')
SCROLL = re.compile(r'chronicle_scroll msg=\w+ at=(-?\d+),(-?\d+)')
TX0, TY0, TX1, TY1, BX, BY = 19, 73, 762, 566, 95, 114


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
        cr = qa.w.RECT()
        qa.u.GetClientRect(g.hwnd, qa.c.byref(cr))
        cw, ch = cr.right, cr.bottom
        vw, vh = (ch * 4 // 3, ch) if cw * 3 > ch * 4 else (cw, cw * 3 // 4)
        vx, vy = (cw - vw) // 2, (ch - vh) // 2
        to_client = lambda sx, sy: (vx + round(sx * vw / 800), vy + round(sy * vh / 600))   # noqa: E731

        def screen(x, y):
            p = qa.w.POINT(x, y)
            qa.u.ClientToScreen(g.hwnd, qa.c.byref(p))
            return p.x, p.y

        def wheel(notches, sx, sy):
            x, y = screen(*to_client(sx, sy))
            for _ in range(abs(notches)):
                g.post(g.hwnd, WM_MOUSEWHEEL, ((120 if notches > 0 else -120) & 0xffff) << 16, ((y & 0xffff) << 16) | (x & 0xffff))
                time.sleep(.25)

        def move_to(x, y):
            n = len(MOVED.findall(g.log()))
            g.post(g.hwnd, WM_APP + 83, x, y)
            g.until(lambda: len(MOVED.findall(g.log())) > n, 10, f'move {x},{y}')
            time.sleep(1.0)
            return MOVED.findall(g.log())[-1]

        def capture(n, kind):
            for p in shots.glob(f'quality-{n:02d}-*.bmp'):
                p.unlink()
            g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
            g.until(lambda: (shots / f'quality-{n:02d}-output.bmp').exists(), 20, f'capture {n}')
            time.sleep(.8)
            return np.asarray(Image.open(shots / f'quality-{n:02d}-{kind}.bmp').convert('RGB')).astype(np.int16)

        def position():
            g.post(g.hwnd, WM_KEYDOWN, 0x27, 1)
            g.post(g.hwnd, WM_KEYUP, 0x27, 0xc0000001)
            time.sleep(1.2)
            at = SCROLL.findall(g.log())[-1]
            g.post(g.hwnd, WM_KEYDOWN, 0x25, 1)
            g.post(g.hwnd, WM_KEYUP, 0x25, 0xc0000001)
            time.sleep(1.2)
            return int(at[0]), int(at[1])

        r['start'] = move_to(128, 88)
        # 1) collect
        t0 = time.time()
        wheel(-1, 400, 300)
        g.until(lambda: 'overview capture done' in g.log(), 60, 'capture done')
        r['capture'] = {'log': re.findall(r'overview capture (?:start|done)[^\n]*', g.log()), 'wall_s': round(time.time() - t0, 2)}
        time.sleep(1)
        r['after_capture_position'] = position.__name__ and None
        # 2) the picture against direct captures
        g.post(g.hwnd, WM_APP + 80, 9, 0)
        g.until(lambda: 'overview dumped' in g.log(), 30, 'dump')
        time.sleep(2)
        canvas = np.asarray(Image.open(shots / 'overview-canvas.bmp').convert('RGB')).astype(np.int16)
        r['canvas'] = canvas.shape
        g.post(g.hwnd, WM_APP + 80, 8, 0)                    # back to 1x
        time.sleep(1)
        checks = []
        off = to_client(799, 599)                              # the cursor over the frame corner, as during collecting
        g.post(g.hwnd, WM_MOUSEMOVE, 0, (off[1] << 16) | off[0])
        for x, y in [(0, 0), (643, 2140), (869, 5431), (400, 2000), (300, 3333)]:
            at = move_to(x, y)
            X, Y = int(at[1]), int(at[2])
            hd = capture(1, 'hd')
            body = hd[BY * 4:TY1 * 4, BX * 4:TX1 * 4]
            body2 = ((body[0::2, 0::2] + body[1::2, 0::2] + body[0::2, 1::2] + body[1::2, 1::2] + 2) // 4)
            cx, cy = (BX + X - TX0) * 2, (BY + Y - TY0) * 2
            part = canvas[cy:cy + body2.shape[0], cx:cx + body2.shape[1]]
            e = 24                                             # OV_EDGE at 2x: a live frame shades its window edge, the picture does not
            keep = np.ones(part.shape[:2], bool)
            keep[:e], keep[-e:], keep[:, :e], keep[:, -e:] = False, False, False, False
            keep[(450 - BY) * 2:(480 - BY) * 2] = False      # the live screen's half-clear mark (submenu_マーク), left out of the picture
            inner = psnr(part[keep], body2[keep])
            d = np.abs(part - body2).max(axis=2)
            runs = lambda m: [(int(a), int(b)) for a, b in zip(np.where(np.diff(np.r_[0, m.astype(int), 0]) == 1)[0], np.where(np.diff(np.r_[0, m.astype(int), 0]) == -1)[0])]   # noqa: E731
            checks.append({'at': (X, Y), 'psnr': psnr(part, body2), 'psnr_inside_edges': inner, 'max_diff': int(d.max()), 'pixels_over_24': round(float((d > 24).mean() * 100), 3),
                           'rows_2x': runs(d.mean(axis=1) > 2)[:12], 'cols_2x': runs(d.mean(axis=0) > 2)[:12], 'size_2x': d.shape})
        r['canvas_vs_direct'] = checks
        # 3) shown table area against the picture scaled the same way
        move_to(128, 88)
        wheel(-3, 400, 300)
        time.sleep(1.5)
        z, ax, ay, ox, oy = map(float, ZOOM.findall(g.log())[-1])
        out = capture(2, 'output')[vy:vy + vh, vx:vx + vw]          # the capture is the whole client; the frame is the viewport
        h, w = out.shape[:2]
        tx0, ty0, tx1, ty1 = TX0 * w // 800, TY0 * h // 600, TX1 * w // 800, TY1 * h // 600
        shown = out[ty0:ty1, tx0:tx1]
        def expect(dx=0.0, dy=0.0):
            vw_, vh_ = (TX1 - TX0) / z, (TY1 - TY0) / z
            box = ((ox + dx - TX0) * 2, (oy + dy - TY0) * 2, (ox + dx + vw_ - TX0) * 2, (oy + dy + vh_ - TY0) * 2)
            img = Image.fromarray(canvas.astype(np.uint8)).crop(tuple(round(v) for v in box)).resize((tx1 - tx0, ty1 - ty0), Image.BOX)
            return np.asarray(img).astype(np.int16)
        r['shown'] = {'zoom': z, 'overview': (ox, oy), 'size': shown.shape, 'psnr_vs_expected': psnr(shown, expect()), 'psnr_vs_shifted_40': psnr(shown, expect(40, 40))}
        best = max(((psnr(shown, expect(dx, dy)), dx, dy) for dx in range(-24, 25, 6) for dy in range(-24, 25, 6)))
        r['shown']['best_shift'] = best
        quarter = lambda a: a[:a.shape[0] // 4 * 4, :a.shape[1] // 4 * 4].reshape(a.shape[0] // 4, 4, a.shape[1] // 4, 4, 3).mean(axis=(1, 3))   # noqa: E731
        r['shown']['psnr_at_quarter_size'] = psnr(quarter(shown), quarter(expect()))   # filter differences on thin lines average out
        r['shown']['mean_shown_vs_expected'] = (round(float(shown.mean()), 1), round(float(expect().mean()), 1))
        # 4) drag pans by distance / zoom
        a, b = to_client(400, 300), to_client(300, 250)
        g.post(g.hwnd, WM_LBUTTONDOWN, 1, (a[1] << 16) | a[0])
        for i in range(1, 6):
            p = (a[0] + (b[0] - a[0]) * i // 5, a[1] + (b[1] - a[1]) * i // 5)
            g.post(g.hwnd, WM_MOUSEMOVE, 1, (p[1] << 16) | p[0])
            time.sleep(.1)
        g.post(g.hwnd, WM_LBUTTONUP, 0, (b[1] << 16) | b[0])
        time.sleep(1)
        drag = re.findall(r'chronicle_overview drag overview=(-?[\d.]+),(-?[\d.]+)', g.log())
        r['drag'] = {'before': (ox, oy), 'after': tuple(map(float, drag[-1])) if drag else None, 'expected_shift': (round(100 / z, 1), round(50 / z, 1))}
        # 5) click returns to 1x with the point under the cursor
        c = to_client(500, 400)
        g.post(g.hwnd, WM_LBUTTONDOWN, 1, (c[1] << 16) | c[0])
        g.post(g.hwnd, WM_LBUTTONUP, 0, (c[1] << 16) | c[0])
        time.sleep(1.5)
        click = re.findall(r'chronicle_zoom click level=1 table=(-?[\d.]+),(-?[\d.]+)', g.log())
        pos = position()
        if click:
            tvx, tvy = map(float, click[-1])
            sx, sy = (c[0] - vx) * 800 / vw, (c[1] - vy) * 600 / vh
            r['click'] = {'table_point': (tvx, tvy), 'position': pos, 'expected': (round(tvx - sx), round(tvy - sy))}
        # 6) the button keeps the middle; 7) all the way out
        wheel(-2, 400, 300)
        time.sleep(1)
        z2, _, _, ox2, oy2 = map(float, ZOOM.findall(g.log())[-1])
        g.post(g.hwnd, WM_APP + 80, 8, 0)
        time.sleep(1.5)
        mid = (ox2 + (TX1 - TX0) / z2 / 2 - (TX0 + TX1) / 2, oy2 + (TY1 - TY0) / z2 / 2 - (TY0 + TY1) / 2)
        r['button'] = {'zoom_before': z2, 'position': position(), 'expected': (round(mid[0]), round(mid[1]))}
        wheel(-15, 400, 300)
        time.sleep(1.5)
        r['all_out'] = ZOOM.findall(g.log())[-1]
        r['render_ms'] = [float(x) for x in re.findall(r'perf_overview_render ms=([\d.]+)', g.log())]
    except Exception as e:  # noqa: BLE001
        r['error'] = repr(e)
    finally:
        r['normal_exit'] = g.close_normally()
        for p in list(shots.glob('quality-*.bmp')) + list(shots.glob('overview-canvas.bmp')):
            p.unlink()
    return r


if __name__ == '__main__':
    res = run()
    qa.dump('test_chronicle_overview.json', res)
    for k, v in res.items():
        print(k, v)
