"""Chronicle drag on the QA runtime: the engine's ClipCursor box must cover the whole 4:3 viewport, not 800x600 pixels.

Title 「추가 메뉴」 then its first button (start.mjo: buttonmenu id 1 -> EXTRA_CHRONICLE) opens the chronicle. A posted drag (down, two moves, up) makes the chronicle clip the cursor;
ClipToGame logs the box it maps (probe runs never clip the real cursor). Frame stats show the chronicle's cost.
"""
import json
import re
import time

import qa
from test_more import boot

CLIP = re.compile(r'clip_cursor logical=(-?\d+),(-?\d+),(-?\d+),(-?\d+) screen=(-?\d+),(-?\d+),(-?\d+),(-?\d+)')
FRAME = re.compile(r'frame=(\d+) .*present_ms=([\d.]+)')


def chronicle_keys():
    m = json.loads((qa.RUN / 'hires-manifest.json').read_text('utf-8'))
    return {e.get('key') or e['file'].split('.')[0] for e in m['entries'] if e.get('name', '').startswith('クロニクル枠')}   # v19 menu-4x entries carry no 'key'


def lparam(g, x, y):
    px, py = g.client_point(g.hwnd, x, y)
    return ((py & 0xffff) << 16) | (px & 0xffff)


def run():
    result = {}
    g = qa.Game()
    try:
        boot(g)
        keys = chronicle_keys()
        for x, y, wait in ((640, 471, 'load call title3_off'), (640, 348, None)):   # 추가 메뉴 (title3_* art), then its first button
            g.move(g.hwnd, x, y)
            time.sleep(.4)
            n = g.count('load call title3_off')
            g.logical_click(g.hwnd, x, y)
            if wait:
                g.until(lambda: g.count(wait) > n, 20, 'extra menu')
                time.sleep(1.5)
        g.until(lambda: any(f'asset {k} ' in g.log() for k in keys), 30, 'chronicle frame')
        time.sleep(3)
        n = len(CLIP.findall(g.log()))
        g.post(g.hwnd, 0x201, 1, lparam(g, 400, 300))
        for x in (350, 300, 250):
            time.sleep(.15)
            g.post(g.hwnd, 0x200, 1, lparam(g, x, 300))
        time.sleep(.15)
        g.post(g.hwnd, 0x202, 0, lparam(g, 250, 300))
        g.until(lambda: len(CLIP.findall(g.log())) > n, 10, 'clip_cursor')
        clip = [tuple(map(int, c)) for c in CLIP.findall(g.log())][n]
        r = qa.w.RECT()
        qa.u.GetClientRect(g.hwnd, qa.c.byref(r))
        vw = min(r.right, r.bottom * 4 // 3)
        vh = vw * 3 // 4
        pt = qa.w.POINT((r.right - vw) // 2, (r.bottom - vh) // 2)
        qa.u.ClientToScreen(g.hwnd, qa.c.byref(pt))
        result['clip'] = clip
        result['viewport_screen'] = (pt.x, pt.y, pt.x + vw, pt.y + vh)
        result['clip_covers_viewport'] = clip[:4] == (0, 0, 800, 600) and abs(clip[4] - pt.x) <= 1 and abs(clip[5] - pt.y) <= 1 \
            and abs(clip[6] - (pt.x + vw)) <= 1 and abs(clip[7] - (pt.y + vh)) <= 1
        time.sleep(12)                                         # let the frame counter report inside the chronicle
        frames = [(int(f), float(ms)) for f, ms in FRAME.findall(g.log())]
        result['frames'] = frames[-4:]
        result['pass'] = result['clip_covers_viewport']
    except Exception as e:
        result['error'] = repr(e)
    finally:
        result['normal_exit'] = g.close_normally()
        (qa.QA / 'test_chronicle.log').write_text(g.log(), 'utf-8')
    return result


if __name__ == '__main__':
    r = run()
    qa.dump('test_chronicle.json', r)
    print(r)
