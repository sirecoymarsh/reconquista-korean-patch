"""python test_console_keys.py <runtime>: the text box keys on a private desktop (11-25).

Gets to a text wait (story map jump to 도입부 2, as test_text_speed), then: W (quick load of a copy of the oldest save,
made before the console changes: the save's resume point is inside console.mjo, so its old offsets must still hold), S twice (the next empty slots, as the save
menu numbers them: majiro_<p*100+1+i>.sav), Q (majiro_9999.sav), A (auto on, the game stays up), a click (auto off).
The runtime's savedata is put back as it was at the end. Result: qa/console-keys.json.
"""
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa  # noqa: E402

YES = tuple(int(v) for v in sys.argv[2].split(',')) if len(sys.argv) > 2 else (485, 302)   # message_box.mjo buttons 0 (400..569) and 1 (231..400), y 275..330
VK = dict(F11=0x7a, RET=0x0d, RIGHT=0x27, UP=0x26, END=0x23, S=0x53, Q=0x51, A=0x41, W=0x57)
run = Path(sys.argv[1])
saves = run / 'savedata'
keep = qa.QA / 'console-keys-savedata'
if keep.exists():
    shutil.rmtree(keep)
shutil.copytree(saves, keep)
(run / 'storymap-read.bin').unlink(missing_ok=True)
oldest = saves / sys.argv[3] if len(sys.argv) > 3 else min(saves.glob('majiro_0*.sav'), key=lambda p: p.stat().st_mtime)
shutil.copy2(oldest, saves / 'majiro_9999.sav')
result = {'steps': []}


def files():
    """the saves where the game writes them now: after a story map jump, its own copy (savedata-review-<pid>-<tick>)"""
    review = sorted(run.glob(f'savedata-review-{g.pid}-*'))
    return {p.name: p.stat().st_mtime_ns for p in (review[-1] if review else saves).glob('majiro_*.sav')}


def capture(name):
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
    Image.frombuffer('RGBA', (r.right, r.bottom), buf, 'raw', 'BGRA', 0, 1).convert('RGB').resize((r.right // 4, r.bottom // 4)).save(qa.QA / f'console-keys-{name}.png')
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


g = qa.Game(run=run)
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
    g.key(child, VK['RIGHT'])
    g.until(lambda: 'cursor=' in g.log(), 10, 'cursor move')
    g.key(child, VK['RET'])
    g.until(lambda: 'page=2 chapter=3' in g.log(), 10, 'chapter page')
    n = g.count('inflow snapshot')
    g.key(child, VK['RIGHT'], 34, .03)
    g.until(lambda: g.count('inflow snapshot') >= n + 34, 30, 'scene steps')
    time.sleep(.5)
    g.key(child, VK['END'])
    time.sleep(.5)
    g.key(child, VK['UP'])
    time.sleep(.4)
    g.story_jump(child)
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    order = int(g.log().split('inflow jump order=')[-1].split()[0])
    g.until(lambda: f'inflow arrived order={order} ' in g.log(), 120, 'arrival')
    time.sleep(3)
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
    time.sleep(6)
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
    qa.dump('console-keys', result)
    print(json.dumps(result, ensure_ascii=False, indent=1))
