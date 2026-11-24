"""The 연표 view by hand on the private desktop, as the user's try uses it: made ready hidden
at the title; F7 to the game window shows it; wheel and arrows to it; F7, Esc, a right click, or F7 to the game window hides
it; shown again at once each time; then the game closes normally with it shown.
python test_chronicle_proto_hand.py [label]   -> qa/chron-proto-hand-<label>.json
"""
import json, sys, time
from ctypes import wintypes as w
import qa

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
VK_F7, VK_ESC, VK_DOWN, VK_RIGHT = 0x76, 0x1b, 0x28, 0x27
qa.u.GetWindowLongW.argtypes = [w.HWND, w.INT]
res = {'label': label, 'steps': []}


def visible(h):   # its own WS_VISIBLE: the game window itself is hidden off screen in these tests (RECON_HD_PROBE)
    return bool(h and qa.u.GetWindowLongW(h, -16) & 0x10000000)
g = qa.Game(extra_env={'RECON_HD_START_FULLSCREEN': '1'})


def lines(prefix):
    return [l for l in g.log().splitlines() if l.startswith(prefix)]


def step(name, **kw):
    res['steps'].append({'step': name, **kw})
    print(name, json.dumps(kw, ensure_ascii=False), flush=True)


try:
    g.until(lambda: lines('chron_proto open'), 120, 'ready')
    game = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    child = qa.u.FindWindowExW(game, None, 'ReconChronicleProto', None)
    step('ready', line=lines('chron_proto open')[-1], child=bool(child), visible=visible(child))
    for n, how in enumerate(['f7', 'esc', 'right-click', 'f7-to-game'], 1):
        g.key(game, VK_F7)                                   # shown from the game window
        g.until(lambda: len(lines('chron_proto show')) >= n, 10, f'show {n}')
        time.sleep(.3)
        shown = visible(child)
        for _ in range(3):
            g.post(child, 0x20a, ((-120) & 0xffff) << 16, 0)   # wheel down
            time.sleep(.15)
        g.key(child, VK_DOWN, 6)
        g.key(child, VK_RIGHT, 3)
        time.sleep(1.5)
        if how == 'f7':
            g.key(child, VK_F7)
        elif how == 'esc':
            g.key(child, VK_ESC)
        elif how == 'right-click':
            g.post(child, 0x204, 2, 0)
            g.post(child, 0x205, 0, 0)
        else:
            g.key(game, VK_F7)
        g.until(lambda: len(lines('chron_proto session')) >= n, 10, f'hide {n}')
        time.sleep(.2)
        step('show-hide ' + how, show=lines('chron_proto show')[-1], visible_when_shown=shown, hidden_after=not visible(child),
             session=lines('chron_proto session')[-1], dialogs=[x for x in g.windows() if x['class'] == '#32770'])
    g.key(game, VK_F7)                                       # left shown while the game closes
    g.until(lambda: len(lines('chron_proto show')) >= 5, 10, 'show 5')
    time.sleep(1)
    step('shown for closing', show=lines('chron_proto show')[-1])
except Exception as e:
    res['error'] = repr(e)
    print('error', repr(e), flush=True)
finally:
    res['normal_exit'] = g.close_normally()
    res['tail'] = lines('chron_proto')[-3:]
    res['problems'] = [l for l in g.log().splitlines() if 'recreate_target' in l or 'register_class' in l]
qa.dump(f'chron-proto-hand-{label}.json', res)
print(json.dumps({'normal_exit': res['normal_exit'], 'tail': res['tail'], 'problems': res['problems']}, ensure_ascii=False))
