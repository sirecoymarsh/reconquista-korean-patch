"""Jump test on 도입부 2's first choice; read tracking after arrival; current position on reopen; normal exit.

Only 도입부 1·2 screens are captured for the user (spoiler rule): map, 도입부 2 scene 35, help, arrival, reopen.
"""
import time

import qa

VK = dict(F11=0x7a, TAB=0x09, RET=0x0d, ESC=0x1b, LEFT=0x25, UP=0x26, RIGHT=0x27, DOWN=0x28, F1=0x70)
result = {'tests': []}
run = qa.RUN
read_file = run / 'storymap-read.bin'
if read_file.exists():
    read_file.unlink()
before = qa.savehash()
g = qa.Game()


def snap(name):
    n = g.count('inflow snapshot')
    return lambda: g.snapshot(name, n)


try:
    g.until(lambda: 'asset 1de0628c ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    s = snap('j01-map-title')
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open')
    s()
    child = g.child()
    s = snap('j02-cursor')
    g.key(child, VK['RIGHT'])
    g.until(lambda: 'cursor=' in g.log(), 10, 'cursor move')
    s()
    cursor = int(g.log().split('cursor=')[-1].split()[0])
    result['cursor_after_right'] = cursor
    assert cursor == 3, cursor                     # catalogue order: 0 도입부1, 1 과거01, 2 현재01, 3 도입부2
    result['tests'].append('right_moves_to_intro2')
    s = snap('j03-chapter-intro2')
    g.key(child, VK['RET'])
    g.until(lambda: 'page=2 chapter=3' in g.log(), 10, 'chapter page')
    s()
    n = g.count('inflow snapshot')
    g.key(child, VK['RIGHT'], 34, .03)
    g.until(lambda: g.count('inflow snapshot') >= n + 34, 30, 'scene steps')
    time.sleep(.5)
    n = g.count('inflow snapshot')
    g.key(child, VK['END'] if 'END' in VK else 0x23)
    g.until(lambda: g.count('inflow snapshot') > n, 10, 'end')
    s = snap('j04-scene35-choice')
    g.key(child, VK['UP'])
    s()
    s = snap('j05-help')
    g.key(child, VK['F1'])
    s()
    g.key(child, VK['ESC'])
    time.sleep(.4)
    item = int(g.log().split('item=')[-1].split()[0])
    result['selected_item'] = item
    g.story_jump(child)
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    order = int(g.log().split('inflow jump order=')[-1].split()[0])
    result['jump_order'] = order
    g.until(lambda: f'inflow arrived order={order} ' in g.log(), 120, 'arrival')
    result['tests'].append('arrived')
    time.sleep(3)
    # read a few pages normally (left clicks on the game window)
    for _ in range(8):
        g.logical_click(g.hwnd, 400, 520)
        time.sleep(1.2)
    s = snap('j06-map-after-reading')
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: g.count('inflow opened') >= 2, 20, 'reopen')
    s()
    opened = g.log().split('inflow opened here=')[-1].split()[0]
    result['reopen_here_order'] = int(opened)
    assert int(opened) > order, (opened, order)
    result['tests'].append('current_position_tracked')
    child = g.child()
    s = snap('j07-chapter-current')
    g.key(child, VK['RET'])
    s()
    g.key(child, VK['ESC'])
    time.sleep(.3)
    g.key(child, VK['ESC'])
    g.until(lambda: g.count('inflow closed_resume') >= 1, 10, 'close')
    result['tests'].append('closed_resume')
    result['pass'] = True
except Exception as e:
    result['error'] = repr(e)
    print('ERROR', repr(e))
finally:
    result['normal_exit'] = g.close_normally()
    after = qa.savehash()
    result['savedata_changed_files'] = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    result['review_folders'] = sorted(p.name for p in run.glob('savedata-review-*'))
    result['read_file_bytes'] = read_file.stat().st_size if read_file.exists() else 0
    (qa.QA / 'test_jump.log').write_text(g.log(), 'utf-8')
    qa.dump('test_jump.json', result)
    print(result)
