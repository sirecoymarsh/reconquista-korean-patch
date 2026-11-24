"""Map sounds through the game's $sound3 channel, on the muted QA runtime (volume multiplier 0 = -100 dB).

Checks every action's sound reaches the engine, that the engine's sound thread finished the opening on2 (its handle
leaves the engine's list), the hover rule (on only on an idle channel), and a normal exit afterwards.
"""
import re
import time

import qa
from test_more import VK, boot, center, open_chart

SE = re.compile(r'inflow se (\w+) setting=(-?\d+) muted=(\d) prev=(-?\d+) prev_state=(-?\d+) handle=(-?\d+) state=(-?\d+)')


def sounds(g):
    return [m.groups() for m in SE.finditer(g.log())]


def step(g, child, vk, name, wait=1.2):
    n = len(sounds(g))
    g.key(child, VK[vk])
    g.until(lambda: any(s[0] == name for s in sounds(g)[n:]), 8, f'{vk} -> {name}')
    time.sleep(wait)


def run():
    result = {'tests': []}
    g = qa.Game()
    try:
        boot(g)
        child = open_chart(g)
        g.until(lambda: any(s[0] == 'on2' for s in sounds(g)), 5, 'on2 at open')
        result['tests'].append('open_on2')
        time.sleep(2.5)                                        # on2 is ~0.3 s: the engine must have played and dropped it
        step(g, child, 'RIGHT', 'on')
        last = sounds(g)[-1]
        result['on2_finished_before_next'] = last[4] == '0' and last[3] != '0'
        step(g, child, 'RET', 'push')                          # open the chapter
        step(g, child, 'RIGHT', 'on')                          # next scene
        step(g, child, 'ESC', 'cancel')                        # back to the map
        step(g, child, 'F1', 'push')                           # help
        step(g, child, 'ESC', 'cancel')                        # help closed
        step(g, child, 'TAB', 'push')                          # final page
        step(g, child, 'TAB', 'push')                          # back
        n = len(sounds(g))
        x, y = center('kureha_10')
        g.move(child, x, y)                                    # hover a cell on an idle channel
        g.until(lambda: any(s[0] == 'on' for s in sounds(g)[n:]), 5, 'hover on')
        result['tests'].append('hover_on')
        n = len(sounds(g))
        g.key(child, VK['ESC'])                                # close the map
        g.until(lambda: 'inflow closed_resume' in g.log(), 10, 'close')
        result['close_cancel'] = any(s[0] == 'cancel' for s in sounds(g)[n:])
        time.sleep(1)
        all_se = sounds(g)
        result['count'] = len(all_se)
        result['names'] = [s[0] for s in all_se]
        result['all_muted'] = all(s[2] == '1' for s in all_se)
        result['settings'] = sorted({s[1] for s in all_se})
        result['queued'] = sum(1 for s in all_se if s[5] != '0')
        result['pass'] = result['all_muted'] and result['close_cancel'] and result['on2_finished_before_next']
    except Exception as e:
        result['error'] = repr(e)
    finally:
        result['normal_exit'] = g.close_normally()
        (qa.QA / 'test_sound.log').write_text(g.log(), 'utf-8')
    return result


if __name__ == '__main__':
    r = run()
    qa.dump('test_sound.json', r)
    print(r)
