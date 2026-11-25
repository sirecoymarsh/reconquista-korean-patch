"""python test_console_keys.py <runtime>: the text box keys on a private desktop (11-25).

Gets to a text wait (story map jump to 도입부 2, as test_text_speed), then: W (quick load of a copy of the oldest save,
made before the console changes: the save's resume point is inside console.mjo, so its old offsets must still hold), S twice (the next empty slots, as the save
menu numbers them: majiro_<p*100+1+i>.sav), Q (majiro_9999.sav), A (auto on, the game stays up), a click (auto off).
The runtime's savedata is put back as it was at the end. Result: qa/console-keys.json.
"""
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa  # noqa: E402

YES = tuple(int(v) for v in sys.argv[2].split(',')) if len(sys.argv) > 2 else (485, 302)   # message_box.mjo buttons 0 (400..569) and 1 (231..400), y 275..330
VK = dict(F11=0x7a, RET=0x0d, RIGHT=0x27, UP=0x26, DOWN=0x28, END=0x23, S=0x53, Q=0x51, A=0x41, W=0x57)
run = Path(sys.argv[1])
saves = run / 'savedata'
keep = qa.QA / 'console-keys-savedata'
if keep.exists():
    shutil.rmtree(keep)
shutil.copytree(saves, keep)
read = run / 'storymap-read.bin'                         # the copy's read marks: put back at the end (the map opens with them)
read_kept = read.read_bytes() if read.exists() else None
read.unlink(missing_ok=True)
review = run / 'review-unlock.enabled'                    # the jump below needs every chapter open (the map opens with the story)
review_was = review.exists()
review.write_text('1')
oldest = saves / sys.argv[3] if len(sys.argv) > 3 else min(saves.glob('majiro_0*.sav'), key=lambda p: p.stat().st_mtime)
shutil.copy2(oldest, saves / 'majiro_9999.sav')
result = {'steps': []}
MODE = sys.argv[4] if len(sys.argv) > 4 else ''


def files():
    """the saves where the game writes them now: after a story map jump, its own copy (savedata-review-<pid>-<tick>)"""
    review = sorted(run.glob(f'savedata-review-{g.pid}-*'))
    return {p.name: p.stat().st_mtime_ns for p in (review[-1] if review else saves).glob('majiro_*.sav')}


def capture_full(name, box):
    """like capture, a part of the window at full size: box = (x0, y0, x1, y1) in 800x600 units"""
    capture(name, full=box)


def capture(name, full=None):
    """the game window as it is (PrintWindow) -> qa/console-keys-<name>.png"""
    import ctypes as c
    from ctypes import wintypes as w
    from PIL import Image
    r = w.RECT()
    qa.u.GetClientRect(g.hwnd, c.byref(r))
    gdi = c.WinDLL('gdi32')
    gdi.CreateCompatibleDC.restype = w.HDC
    gdi.CreateCompatibleBitmap.restype = w.HBITMAP
    qa.u.GetDC.restype = w.HDC
    hdc = qa.u.GetDC(w.HWND(g.hwnd))
    mem = gdi.CreateCompatibleDC(w.HDC(hdc))
    bmp = gdi.CreateCompatibleBitmap(w.HDC(hdc), r.right, r.bottom)
    gdi.SelectObject(w.HDC(mem), w.HBITMAP(bmp))
    qa.u.PrintWindow(w.HWND(g.hwnd), w.HDC(mem), 3)
    buf = c.create_string_buffer(r.right * r.bottom * 4)
    gdi.GetBitmapBits(w.HBITMAP(bmp), len(buf), buf)
    im = Image.frombuffer('RGBA', (r.right, r.bottom), buf, 'raw', 'BGRA', 0, 1).convert('RGB')
    if full:
        vw = min(r.right, r.bottom * 4 // 3)
        vh = vw * 3 // 4
        ox, oy = (r.right - vw) // 2, (r.bottom - vh) // 2
        im.crop(tuple(int(v * vw / 800) + o for v, o in zip(full, (ox, oy, ox, oy)))).save(qa.QA / f'console-keys-{name}.png')
    else:
        im.resize((r.right // 4, r.bottom // 4)).save(qa.QA / f'console-keys-{name}.png')
    gdi.DeleteObject(w.HBITMAP(bmp))
    gdi.DeleteDC(w.HDC(mem))
    qa.u.ReleaseDC(w.HWND(g.hwnd), w.HDC(hdc))


def press(x, y):
    """a button the way a hand presses it: onto it, a moment for its hover, then the click"""
    g.move(g.hwnd, x, y)
    time.sleep(.4)
    g.logical_click(g.hwnd, x, y)


def changed(before):
    now = files()
    return sorted(k for k in now if before.get(k) != now[k])


g = qa.Game(run=run, extra_env={'RECON_PERF': '2'} if MODE in ('text', 'textreplay', 'text1') or os.environ.get('RECON_PERF') else None)
try:
    g.until(lambda: 'load call title' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open')
    child = g.child()
    if MODE != 'text1':                                   # text1: 도입부 1 (its large serif lines)
        g.key(child, VK['RIGHT'])
        g.until(lambda: 'cursor=' in g.log(), 10, 'cursor move')
    if MODE.startswith('deep'):                           # deep*: a late chapter, down the lane
        g.key(child, VK['DOWN'], int(os.environ.get('DEEP_DOWN', 16)), .08)   # DEEP_DOWN: how far down the lane
        time.sleep(.5)
    g.key(child, VK['RET'])
    g.until(lambda: re.search(r'page=2 chapter=\d+', g.log()) if MODE.startswith('deep') else f'page=2 chapter={0 if MODE == "text1" else 3}' in g.log(), 10, 'chapter page')
    n = g.count('inflow snapshot')
    g.key(child, VK['RIGHT'], 34, .03)
    g.until(lambda: g.count('inflow snapshot') >= n + 34, 30, 'scene steps')
    time.sleep(.5)
    g.key(child, VK['END'])
    time.sleep(.5)
    g.key(child, VK['UP'])
    time.sleep(.4)
    if MODE in ('textreplay', 'text1', 'deepreplay'):
        g.key(child, VK['RET'])                           # 「이 대사부터 다시보기」 (Enter on the line)
    else:
        g.story_jump(child)                               # 「여기서부터 본편으로」, then 예 to its question
        time.sleep(.6)
        g.key(child, VK['RET'])
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    order = int(g.log().split('inflow jump order=')[-1].split()[0])
    t_jump = time.time()
    g.until(lambda: f'inflow arrived order={order} ' in g.log(), 120, 'arrival')
    result['jump_seconds'] = round(time.time() - t_jump, 2)
    time.sleep(3)
    if os.environ.get('NOSAVE'):                          # a replay refuses saves and loads (11-25): Q, then L, with the message each
        time.sleep(2)
        for k, vk in (('l', 0x4c), ('q', VK['Q']), ('w', VK['W']), ('s', VK['S']), ('button', None)):
            if vk:
                g.key(g.hwnd, vk)
            else:
                press(325, 574)                           # the 퀵 저장 button
            time.sleep(1.2)
            capture_full(f'nosave-{k}', (0, 0, 800, 600))
            g.logical_click(g.hwnd, 400, 300)
            time.sleep(1.2)
        result['nosave'] = [l for l in g.log().splitlines() if 'console_replay_no_save' in l or 'console_key' in l][-4:]
        raise SystemExit
    if MODE in ('text', 'textreplay', 'text1', 'deepreplay', 'deepmain'):        # the text after a story map jump: 4x or not (11-25)
        for k in range(8):                                # the arrival line, once the screen shows it
            capture_full(f'text-arrived-{k}', (0, 0, 800, 600))
            time.sleep(.7)
        for k in range(3):
            g.logical_click(g.hwnd, 400, 300)
            time.sleep(1.5)
        capture_full('text-later', (0, 0, 800, 600))
        if os.environ.get('RECON_PERF'):                  # the engine's own 4x frame (perf capture WM_APP+80)
            g.post(g.hwnd, 0x8000 + 80, 11, 0)
            g.until(lambda: 'quality_capture id=1 ' in g.log(), 20, 'quality capture')
            time.sleep(.5)
            shutil.copy2(run / 'qa' / 'quality-01-hd.bmp', qa.QA / 'console-keys-text-later-hd.bmp')
        result['text'] = [l for l in g.log().splitlines() if l.startswith('text4k lines')][-2:]
        raise SystemExit
    if len(sys.argv) > 4 and sys.argv[4] == 'hist':        # 기록: the pages it shows (backlog.inc HistPos)
        capture('hist-before')
        for _ in range(4):
            g.logical_click(g.hwnd, 400, 300)
            time.sleep(1.5)
        capture('hist-read')
        g.key(g.hwnd, 0x21)                               # PgUp: 기록
        time.sleep(2)
        for _ in range(2):
            g.wheel(g.hwnd, 400, 300, 1)                  # a page back
            time.sleep(.8)
        capture('hist')
        g.key(g.hwnd, 0x0d)                               # Enter: back to this page's line (asked)
        time.sleep(1.5)
        capture('hist-ask')
        g.key(g.hwnd, 0x0d)                               # 예
        g.until(lambda: 'inflow backlog go' in g.log(), 10, 'backlog go')
        order = int(g.log().split('inflow backlog node=')[-1].split()[0])
        g.until(lambda: f'inflow arrived order={order} ' in g.log(), 120, 'backlog arrival')
        time.sleep(2)
        capture('hist-arrived')
        result['hist'] = [l for l in g.log().splitlines() if l.startswith('hist_pos') or 'backlog' in l or 'inflow arrived' in l][-8:]
        result['marks'] = [l for l in g.log().splitlines() if 'inflow here' in l or 'flow_arrived' in l][-3:]
        raise SystemExit
    if len(sys.argv) > 4 and sys.argv[4] == 'mkey':        # M in play, then the map's 「연표」: the 연표 opens
        maps = g.log().count('inflow opened')
        g.key(g.hwnd, 0x4d)
        g.until(lambda: g.log().count('inflow opened') > maps, 15, 'map by M')
        time.sleep(1)
        child = g.child()
        g.move(child, 143, 42)
        time.sleep(.3)
        g.logical_click(child, 143, 42)
        g.until(lambda: 'inflow chronicle_up' in g.log(), 10, 'chronicle from map')
        result['to_chronicle'] = [l for l in g.log().splitlines() if 'to_chronicle' in l or 'chronicle_up' in l or 'console_choice' in l][-3:]
        raise SystemExit
    if len(sys.argv) > 4 and sys.argv[4] == 'config':      # the config screen's buttons are gone while its story map is up
        def buttons():
            out = []
            def cb(h, l):
                if qa.u.IsWindowVisible(h):
                    t = qa.c.create_unicode_buffer(64)
                    qa.u.GetWindowTextW(h, t, 64)
                    k = qa.c.create_unicode_buffer(32)
                    qa.u.GetClassNameW(h, k, 32)
                    if k.value == 'Button':
                        out.append((h, t.value))
                return True
            qa.u.EnumChildWindows(g.hwnd, qa.CB(cb), 0)
            return out
        g.key(g.hwnd, 0x1b)
        g.until(lambda: len(buttons()) >= 3, 15, 'config buttons')
        result['config_buttons'] = [t for _, t in buttons()]
        ask = next(h for h, t in buttons() if '기록 점프' in t)  # 「기록 점프」: asked or not, both ways
        labels = []
        for _ in range(2):
            qa.u.PostMessageW(ask, 0xf5, 0, 0)
            time.sleep(.6)
            labels.append(next(t for h, t in buttons() if '기록 점프' in t))
        result['backlog_ask'] = labels + [l for l in g.log().splitlines() if l.startswith('backlog ask=')][-2:]
        h = next(h for h, t in buttons() if '흐름' in t)
        qa.u.PostMessageW(h, 0xf5, 0, 0)                  # BM_CLICK
        g.until(lambda: g.log().count('inflow opened') >= 2, 15, 'map from config')
        time.sleep(1)
        result['buttons_over_map'] = [t for _, t in buttons()]
        capture('config-map')
        child = g.child()
        press_child = lambda x, y: (g.move(child, x, y), time.sleep(.3), g.logical_click(child, x, y))
        press_child(143, 42)
        time.sleep(1)
        result['refused'] = 'to_chronicle refused' in g.log()
        g.key(child, 0x1b)
        time.sleep(1.5)
        result['buttons_after_map'] = [t for _, t in buttons()]
        raise SystemExit
    if len(sys.argv) > 4:
        n = g.count('console_key ')
        g.key(g.hwnd, 0x4c)
        g.until(lambda: g.count('console_key ') > n, 10, 'key L')
        time.sleep(3)
        capture('load-menu')
        if len(sys.argv) > 5:
            x, y = (int(v) for v in sys.argv[5].split(','))
            press(x, y)
            time.sleep(2)
            capture('load-asked')
            press(*YES)
            time.sleep(8)
            capture('load-after')
            result['menu_load_alive'] = g.poll() is None
        raise SystemExit
    n = g.count('console_key ')
    g.key(g.hwnd, VK['W'])
    g.until(lambda: g.count('console_key ') > n, 10, 'key W')
    time.sleep(1.5)
    capture('w-asked')
    loads = g.count('load call ')
    press(*YES)                   # 「불러올까요?」: 예
    time.sleep(8)
    capture('w-after')
    result['loads_after_yes'] = g.count('load call ') - loads
    result['steps'].append({'key': 'W', 'from': oldest.name, 'alive': g.poll() is None})
    assert g.poll() is None, 'game ended after loading ' + oldest.name
    g.logical_click(g.hwnd, 485, 302)
    time.sleep(2)
    result['before'] = sorted(files())
    for k in ('S', 'S', 'Q'):
        before = files()
        n = g.count('console_key ')
        g.key(g.hwnd, VK[k])
        g.until(lambda: g.count('console_key ') > n, 10, 'key ' + k)
        g.until(lambda: changed(before), 10, 'save ' + k)
        new = changed(before)
        result['steps'].append({'key': k, 'log': g.log().split('console_key ')[-1].split('\n')[0], 'new': new})
        time.sleep(1.5)
        capture(f'{k}-{len(result["steps"])}')
        g.logical_click(g.hwnd, 485, 302)                     # the message box
        time.sleep(1.5)
        assert g.poll() is None, 'game ended after ' + k
    n = g.count('console_key ')
    g.key(g.hwnd, VK['A'])
    g.until(lambda: g.count('console_key ') > n, 10, 'key A')
    result['steps'].append({'key': 'A', 'log': g.log().split('console_key ')[-1].split('\n')[0]})
    time.sleep(2)
    capture('auto')
    for _ in range(2):                                    # A while auto runs: the rate (auto_rate.inc)
        g.key(g.hwnd, VK['A'])
        time.sleep(.3)
    time.sleep(3)
    capture('auto-x3')
    result['auto'] = [l for l in g.log().splitlines() if l.startswith(('auto_rate', 'auto_wait'))][-8:]
    assert g.poll() is None, 'game ended in auto'
    g.logical_click(g.hwnd, 485, 302)
    time.sleep(2)
    assert g.poll() is None, 'game ended after auto off'
    result['ok'] = True
except Exception as e:  # noqa: BLE001
    result['error'] = repr(e)
finally:
    result['alive_at_end'] = g.poll() is None
    result['normal_exit'] = g.close_normally()
    result['after'] = sorted(files())
    shutil.rmtree(saves)
    shutil.copytree(keep, saves)
    if read_kept is None:
        read.unlink(missing_ok=True)
    else:
        read.write_bytes(read_kept)
    if not review_was:
        review.unlink(missing_ok=True)
    qa.dump('console-keys', result)
    print(json.dumps(result, ensure_ascii=False, indent=1))
