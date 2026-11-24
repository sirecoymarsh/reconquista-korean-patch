"""연표 with the wheel left to the engine (10-25): what the wheel does there, and the arrow keys still moving it. runtime-chron,
timing-only perf mode. In-engine captures of the 1x page (WM_APP+80) before and after wheel up/down are compared as numbers
only and deleted at the end (the chronicle can show later events; nothing is looked at or kept).
python test_chronicle_wheel.py   -> qa/test_chronicle_wheel.json
"""
import re
import time

import numpy as np
from PIL import Image

import qa
import test_chronicle_perf as T

WM_KEYDOWN, WM_KEYUP, WM_MOUSEWHEEL, WM_APP = 0x100, 0x101, 0x20A, 0x8000
VK = dict(LEFT=0x25, UP=0x26, RIGHT=0x27, DOWN=0x28)
LINE = re.compile(r'chronicle_scroll msg=(\w+) at=(-?\d+),(-?\d+) target=(-?\d+),(-?\d+)')


def run():
    g = qa.Game(run=T.RUN, extra_env={'RECON_PERF': '2'})
    shots = T.RUN / 'qa'
    result = {}
    try:
        frame = T.keys('クロニクル枠')
        g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
        g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
        if not qa.u.IsWindowVisible(g.hwnd):
            qa.u.ShowWindow(g.hwnd, 4)
        time.sleep(4)
        rect = qa.w.RECT()
        qa.u.GetWindowRect(g.hwnd, qa.c.byref(rect))
        cx, cy = (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2   # wheel LPARAM is in screen coordinates

        def capture(n):
            for p in shots.glob(f'quality-{n:02d}-*.bmp'):
                p.unlink()
            g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
            g.until(lambda: (shots / f'quality-{n:02d}-base.bmp').exists(), 15, f'capture {n}')
            time.sleep(.5)
            return np.asarray(Image.open(shots / f'quality-{n:02d}-base.bmp').convert('RGB')).astype(np.int16)

        def wheel(notches):
            for _ in range(abs(notches)):
                g.post(g.hwnd, WM_MOUSEWHEEL, (((120 if notches > 0 else -120) & 0xffff) << 16), ((cy & 0xffff) << 16) | (cx & 0xffff))
                time.sleep(.15)

        a = capture(1)
        time.sleep(1.5)
        b = capture(2)                       # nothing sent: the chronicle's own animation
        wheel(3)
        time.sleep(1.5)
        c = capture(3)                       # after wheel up 3
        wheel(-3)
        time.sleep(1.5)
        d = capture(4)                       # after wheel down 3

        def diff(x, y):
            return {'mean_abs': round(float(np.abs(x - y).mean()), 2), 'pixels_changed_pct': round(float((np.abs(x - y).max(axis=2) > 24).mean() * 100), 2)}
        result['idle'] = diff(a, b)
        result['wheel_up_3'] = diff(b, c)
        result['wheel_down_3'] = diff(c, d)
        result['back_to_start'] = diff(b, d)
        result['scroll_lines_after_wheel'] = len(LINE.findall(g.log()))   # must stay 0: the DLL no longer moves it on the wheel
        n = len(LINE.findall(g.log()))
        for vk in (VK['RIGHT'], VK['DOWN'], VK['LEFT'], VK['UP']):
            g.post(g.hwnd, WM_KEYDOWN, vk, 1)
            g.post(g.hwnd, WM_KEYUP, vk, 0xc0000001)
            time.sleep(1.2)
        result['arrow_moves'] = [dict(zip(('msg', 'x', 'y', 'tx', 'ty'), r)) for r in LINE.findall(g.log())[n:]]
    except Exception as e:  # noqa: BLE001
        result['error'] = repr(e)
    finally:
        result['normal_exit'] = g.close_normally()
        for p in shots.glob('quality-*.bmp'):
            p.unlink()
    return result


if __name__ == '__main__':
    r = run()
    qa.dump('test_chronicle_wheel.json', r)
    print(r)
