"""Screens for the user, 도입부 1·2 only (spoiler rule): full-screen map, final page, 도입부 2 choice, help, chapter search."""
import time

import qa
from test_more import VK, boot, open_chart, step_to_kind

g = qa.Game()
shots = {}
try:
    boot(g)
    s = g.count('inflow snapshot')
    child = open_chart(g)
    shots['map'] = str(g.snapshot('u01-map', s))
    s = g.count('inflow snapshot')
    g.key(child, VK['TAB'])
    shots['final'] = str(g.snapshot('u02-final', s))
    g.key(child, VK['TAB'])
    time.sleep(.3)
    x, y = 316 + 111, 127                                  # 도입부 2 cell centre
    n = g.count('page=2 chapter=')
    g.logical_click(child, x, y)
    g.until(lambda: g.count('page=2 chapter=') > n, 10, 'open 도입부 2')
    n = g.count('scene=')
    g.key(child, VK['LEFT'], 70, .01)                      # first scene
    g.until(lambda: g.count('scene=') >= n + 70, 20, 'to first scene')
    n = g.count('scene=')
    g.key(child, VK['RIGHT'], 34, .02)                     # 장면 35: the game's first choice
    g.until(lambda: g.count('scene=') >= n + 34, 20, 'to scene 35')
    order = step_to_kind(g, child, 2, scenes=1, limit=150)
    s = g.count('inflow snapshot')
    g.key(child, VK['UP'], 2, .05)
    g.until(lambda: g.count('inflow snapshot') >= s + 2, 10, 'up')
    shots['choice'] = str(g.snapshot('u03-intro2-choice', s + 1))
    s = g.count('inflow snapshot')
    g.key(child, VK['F1'])
    shots['help'] = str(g.snapshot('u04-help', s))
    g.key(child, VK['ESC'])
    time.sleep(.3)
    g.logical_click(child, 400, 101)
    time.sleep(.3)
    s = g.count('inflow snapshot')
    g.chars(g.edit(), '마호')
    g.until(lambda: 'search len=2 ' in g.log(), 5, 'search maho')
    shots['search'] = str(g.snapshot('u05-search-in-chapter', s + 1))
    g.key(child, VK['ESC'])
    time.sleep(.3)
    g.key(child, VK['ESC'])
    g.until(lambda: 'inflow closed_resume' in g.log(), 10, 'close')
except Exception as e:
    print('ERROR', repr(e))
finally:
    print({'normal_exit': g.close_normally(), 'shots': shots})
