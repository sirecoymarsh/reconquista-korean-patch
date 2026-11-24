"""Smoke test: open the map on the title screen, both pages, one chapter page, help; close; normal exit."""
import time

import qa

VK = dict(F11=0x7a, TAB=0x09, RET=0x0d, ESC=0x1b, LEFT=0x25, UP=0x26, RIGHT=0x27, DOWN=0x28, F1=0x70)
result = {'tests': []}
before = qa.savehash()
g = qa.Game()
try:
    g.until(lambda: 'asset 1de0628c ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    n = g.count('inflow snapshot')
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open')
    result['tests'].append('opened')
    child = g.child()
    assert child
    g.snapshot('01-map-main', n)
    n = g.count('inflow snapshot')
    g.key(child, VK['TAB'])
    g.snapshot('02-map-final', n)
    n = g.count('inflow snapshot')
    g.key(child, VK['TAB'])
    g.snapshot('03-map-main-again', n)
    n = g.count('inflow snapshot')
    g.key(child, VK['RIGHT'])                      # 도입부 1 -> 도입부 2
    g.snapshot('04-cursor-intro2', n)
    n = g.count('inflow snapshot')
    g.key(child, VK['RET'])
    g.until(lambda: 'page=2 chapter=' in g.log(), 10, 'chapter page')
    g.snapshot('05-chapter-intro2', n)
    n = g.count('inflow snapshot')
    g.key(child, VK['RIGHT'], 34, .02)             # scene 35 (the first choice)
    g.until(lambda: g.count('inflow snapshot') >= n + 34, 20, 'scene steps')
    n = g.count('inflow snapshot')
    g.key(child, VK['DOWN'], 9, .02)
    g.until(lambda: g.count('inflow snapshot') >= n + 9, 20, 'item steps')
    n2 = g.count('inflow snapshot')
    g.key(child, VK['F1'])
    g.snapshot('07-help', n2)
    g.key(child, VK['ESC'])                        # closes help
    time.sleep(.3)
    n = g.count('inflow snapshot')
    g.key(child, VK['ESC'])                        # back to map
    g.snapshot('08-back-to-map', n)
    g.key(child, VK['ESC'])                        # close chart
    g.until(lambda: 'inflow closed_resume' in g.log(), 10, 'close')
    result['tests'].append('closed_resume')
    result['pass'] = True
except Exception as e:
    result['error'] = repr(e)
    print('ERROR', repr(e))
finally:
    result['normal_exit'] = g.close_normally()
    result['savedata_unchanged'] = qa.savehash() == before
    (qa.QA / 'test_open.log').write_text(g.log(), 'utf-8')
    qa.dump('test_open.json', result)
    print(result)
