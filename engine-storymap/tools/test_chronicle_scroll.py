"""연표 arrow keys (ChronicleScroll) on runtime-chron, perf mode. Each event logs the chronicle's position and the glide
target it set; the next event's position shows whether the chronicle got there. Nothing is captured. Since 10-25 the wheel
goes to the engine untouched (tools/test_chronicle_wheel.py checks that), so the wheel steps are gone.
python test_chronicle_scroll.py   -> qa/test_chronicle_scroll.json
"""
import json
import re
import time

import qa
import test_chronicle_perf as T

WM_KEYDOWN, WM_KEYUP = 0x100, 0x101
VK = dict(LEFT=0x25, UP=0x26, RIGHT=0x27, DOWN=0x28)
LINE = re.compile(r'chronicle_scroll msg=(\w+) at=(-?\d+),(-?\d+) target=(-?\d+),(-?\d+) max=(-?\d+),(-?\d+)')


def run():
    g = qa.Game(run=T.RUN, extra_env={'RECON_PERF': '1'})
    result = {'events': []}
    try:
        frame = T.keys('クロニクル枠')
        g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
        g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
        if not qa.u.IsWindowVisible(g.hwnd):
            qa.u.ShowWindow(g.hwnd, 4)
        time.sleep(4)

        def key(vk):
            g.post(g.hwnd, WM_KEYDOWN, vk, 1)
            g.post(g.hwnd, WM_KEYUP, vk, 0xc0000001)

        steps = [('down 3', lambda: [key(VK['DOWN']) for _ in range(3)]), ('up', lambda: key(VK['UP'])), ('right', lambda: key(VK['RIGHT'])),
                 ('right', lambda: key(VK['RIGHT'])), ('left', lambda: key(VK['LEFT'])), ('down', lambda: key(VK['DOWN'])),
                 ('up', lambda: key(VK['UP'])), ('up 9 (clamp)', lambda: [key(VK['UP']) for _ in range(9)]), ('left 9 (clamp)', lambda: [key(VK['LEFT']) for _ in range(9)])]
        for name, act in steps:
            n = len(LINE.findall(g.log()))
            act()
            g.until(lambda: len(LINE.findall(g.log())) > n, 10, name)
            time.sleep(1.2)                                           # let the 30-a-loop glide finish
            rows = LINE.findall(g.log())[n:]
            result['events'].append({'step': name, 'logged': [dict(zip(('msg', 'x', 'y', 'tx', 'ty', 'xmax', 'ymax'), r)) for r in rows]})
        n = len(LINE.findall(g.log()))
        key(VK['RIGHT'])                                              # last one only reports where the clamped glide ended
        g.until(lambda: len(LINE.findall(g.log())) > n, 10, 'final')
        last = LINE.findall(g.log())[-1]
        result['final_position'] = (int(last[1]), int(last[2]))
    except Exception as e:  # noqa: BLE001
        result['error'] = repr(e)
    finally:
        result['normal_exit'] = g.close_normally()
    return result


if __name__ == '__main__':
    r = run()
    qa.dump('test_chronicle_scroll.json', r)
    for e in r['events']:
        print(e['step'], [(x['msg'], (x['x'], x['y']), '->', (x['tx'], x['ty'])) for x in e['logged']])
    print({k: v for k, v in r.items() if k != 'events'})
