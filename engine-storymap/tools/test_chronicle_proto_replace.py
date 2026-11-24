"""The 연표 view taking the game's own 연표 over (cproto::Replace in native/chronicle_proto.inc):
runtime-test, the story map's first chapter (도입부 1), then the text box's 연표 tab, as test_chronicle_close.py opens it. The
prototype must show over the game's 연표, the 연표 under it close by itself (a right click), and hiding the prototype leave the
scene as it was, with no click reaching it afterwards.
python test_chronicle_proto_replace.py [label]   -> qa/chron-proto-replace-<label>.json
"""
import json, re, sys, time
from ctypes import wintypes as w
import qa
from test_hitch import VK

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
VK_F7 = 0x76
qa.u.GetWindowLongW.argtypes = [w.HWND, w.INT]
res = {'label': label, 'steps': []}
(qa.RUN / 'review-unlock.enabled').unlink(missing_ok=True)
g = qa.Game(extra_env={'RECON_HD_START_FULLSCREEN': '1', 'RECON_PERF': '2'})


def lines(prefix):
    return [l for l in g.log().splitlines() if l.startswith(prefix)]


def visible(h):
    return bool(h and qa.u.GetWindowLongW(h, -16) & 0x10000000)


def step(name, **kw):
    res['steps'].append({'step': name, 't': round(time.time() - g.started, 1), **kw})
    print(name, json.dumps(kw, ensure_ascii=False), flush=True)


def hover(x, y):
    r = qa.w.RECT()
    qa.u.GetClientRect(g.hwnd, qa.c.byref(r))
    vw = min(r.right, r.bottom * 4 // 3)
    vh = vw * 3 // 4
    px, py = (r.right - vw) // 2 + round(x * vw / 800), (r.bottom - vh) // 2 + round(y * vh / 600)
    g.post(g.hwnd, 0x200, 0, ((py & 0xffff) << 16) | (px & 0xffff))
    time.sleep(.4)


try:
    (qa.RUN / 'storymap-read.bin').unlink(missing_ok=True)
    g.until(lambda: 'asset 1de0628c ' in g.log() or 'asset ef1f6a40 ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(3)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    step('title', ready=(lines('chron_proto open') or ['-'])[-1][:110])
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open map')
    child = g.child()
    time.sleep(.5)
    g.key(child, VK['RET'])
    g.until(lambda: re.search(r'page=2 chapter=\d+', g.log()), 10, 'chapter page')
    time.sleep(.5)
    g.story_jump(child)
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    got = int(g.log().split('inflow jump order=')[-1].split()[0])
    g.until(lambda: f'inflow arrived order={got} ' in g.log(), 120, 'arrival')
    time.sleep(4)
    step('in the scene')
    proto = qa.u.FindWindowExW(g.hwnd, None, 'ReconChronicleProto', None)
    t0 = time.time()                                         # the text box (and its 연표 tab) comes with the first lines
    while time.time() - t0 < 90 and not lines('chron_proto replace opened'):
        g.logical_click(g.hwnd, 400, 520)
        time.sleep(1.2)
        hover(770, 510)                                      # the 연표 tab right of the text box
        g.logical_click(g.hwnd, 770, 510)
        end = time.time() + 2.5
        while time.time() < end and not lines('chron_proto replace opened'):
            time.sleep(.1)
    g.until(lambda: lines('chron_proto replace opened'), 5, 'the game 연표 opens')
    step('game 연표 opened', after_s=round(time.time() - t0, 1))
    g.until(lambda: len(lines('chron_proto show')) >= 1, 10, 'prototype shows')
    step('prototype shown', show=lines('chron_proto show')[-1], visible=visible(proto))
    g.until(lambda: lines('chron_proto replace closed_under') or lines('chron_proto replace gave_up'), 15, 'game 연표 under it')
    step('game 연표 under it', result=(lines('chron_proto replace closed_under') or lines('chron_proto replace gave_up'))[-1],
         clicks=len(lines('chron_proto replace right_click')), opens=g.log().count('chronicle_open=1'), closes=g.log().count('chronicle_open=0'))
    time.sleep(3)
    clicks = len(lines('chron_proto replace right_click'))
    step('settled', clicks=clicks, prototype_visible=visible(proto))
    g.key(proto, VK_F7)                                      # the user closes the prototype
    g.until(lambda: lines('chron_proto session'), 10, 'prototype hides')
    time.sleep(2)
    step('prototype hidden', session=lines('chron_proto session')[-1][:200], visible=visible(proto),
         clicks_after=len(lines('chron_proto replace right_click')), opens=g.log().count('chronicle_open=1'),
         closes=g.log().count('chronicle_open=0'), dialogs=[x['title'] for x in g.windows() if x['class'] == '#32770'])
    hover(770, 510)                                          # and once more: the game's 연표 again goes to the prototype
    g.logical_click(g.hwnd, 770, 510)
    g.until(lambda: len(lines('chron_proto replace opened')) >= 2, 20, 'second open')
    g.until(lambda: len(lines('chron_proto replace closed_under')) + len(lines('chron_proto replace gave_up')) >= 2, 15, 'second close under')
    step('second time', show=len(lines('chron_proto show')), result=(lines('chron_proto replace closed_under') or ['-'])[-1])
    g.key(proto, VK_F7)
    g.until(lambda: len(lines('chron_proto session')) >= 2, 10, 'second hide')
except Exception as e:
    res['error'] = repr(e)
    print('error', repr(e)[:600], flush=True)
finally:
    res['normal_exit'] = g.close_normally()
    res['tail'] = [l for l in g.log().splitlines() if l.startswith('chron') or 'chronicle_open' in l][-14:]
qa.dump(f'chron-proto-replace-{label}.json', res)
print(json.dumps({'normal_exit': res['normal_exit'], 'error': res.get('error', '')[:300], 'tail': res['tail']}, ensure_ascii=False, indent=0))
