"""The new 연표's actions handed to the game's own (10-27): runtime-test, 모든 콘텐츠 개방 on (every cell open), the story map's
first chapter, the text box's 연표 tab; then in the new 연표: 새 항목 찾기, 추가 이야기 찾기 (twice), and one of:
  python test_chronicle_actions.py scene <label>   into the first sub-episode cell: the game's 연표 must go into that scene
  python test_chronicle_actions.py help <label>    도움말: the game's own help (c_setumei) must start
  python test_chronicle_actions.py close <label>   닫기 (the frame's button): back to the scene, the NEW table cleared as the game does
No pictures kept (opened-up 연표: spoilers). -> qa/chron-actions-<label>.json
"""
import json, re, sys, time
import qa
from test_hitch import VK

what = sys.argv[1] if len(sys.argv) > 1 else 'scene'
label = sys.argv[2] if len(sys.argv) > 2 else 'now'
WM_APP = 0x8000
res = {'what': what, 'label': label, 'steps': []}
(qa.RUN / 'review-unlock.enabled').write_text('1')
g = qa.Game(extra_env={'RECON_PERF': '2', 'RECON_HD_START_FULLSCREEN': '1', 'RECON_CHRON_PROTO': '1'})


def lines(prefix):
    return [l for l in g.log().splitlines() if l.startswith(prefix)]


def step(name, **kw):
    res['steps'].append({'step': name, 't': round(time.time() - g.started, 1), **kw})
    print(name, json.dumps(kw, ensure_ascii=False)[:500], flush=True)


def hover(x, y):
    r = qa.w.RECT()
    qa.u.GetClientRect(g.hwnd, qa.c.byref(r))
    vw = min(r.right, r.bottom * 4 // 3)
    vh = vw * 3 // 4
    g.post(g.hwnd, 0x200, 0, ((((r.bottom - vh) // 2 + round(y * vh / 600)) & 0xffff) << 16) | (((r.right - vw) // 2 + round(x * vw / 800)) & 0xffff))
    time.sleep(.4)


def open_chronicle():
    g.until(lambda: 'asset 1de0628c ' in g.log() or 'asset ef1f6a40 ' in g.log() or 'asset c1e942c6 ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(3)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
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
    t0 = time.time()
    while time.time() - t0 < 90 and 'chronicle_open=1' not in g.log():
        g.logical_click(g.hwnd, 400, 520)
        time.sleep(1.2)
        hover(770, 510)
        g.logical_click(g.hwnd, 770, 510)
        end = time.time() + 2.5
        while time.time() < end and 'chronicle_open=1' not in g.log():
            time.sleep(.1)
    g.until(lambda: 'chronicle_open=1' in g.log(), 5, 'the game 연표 opens')
    g.until(lambda: lines('chron_proto show'), 15, 'view shows')
    time.sleep(1.5)


try:
    open_chronicle()
    view = qa.u.FindWindowExW(g.hwnd, None, 'ReconChronicleProto', None)
    step('view', table=lines('chron_proto table')[-1:])
    for b in (1, 2, 2):                                  # 새 항목 찾기, 추가 이야기 찾기 twice (the cursor moves on)
        g.post(view, WM_APP + 7, b, 0)
        time.sleep(.8)
        step(f'press {b}', line=lines('chron_proto test_press')[-1:])
    loads = len(re.findall(r'^load call', g.log(), re.M))
    if what == 'scene':
        g.post(view, WM_APP + 6, 0, 0)
    elif what == 'help':
        g.post(view, WM_APP + 7, 3, 0)
    else:
        g.post(view, WM_APP + 7, 4, 0)
    g.until(lambda: lines('chron_proto act=') and re.search(r'chron_proto act=\d done=', g.log()), 15, 'act done')
    time.sleep(6)                                        # the scene / help / previous screen has started
    step('after', act=lines('chron_proto act')[-3:], test=lines('chron_proto test_')[-1:], opens=g.log().count('chronicle_open=1'),
         closes=g.log().count('chronicle_open=0'), loads_after=len(re.findall(r'^load call', g.log(), re.M)) - loads,
         view_visible=bool(qa.u.IsWindowVisible(view)), dialogs=[x['title'] for x in g.windows() if x['class'] == '#32770'],
         frames=g.log().count('present attempt'))
    res['loaded_after'] = [l[:60] for l in re.findall(r'^load call .*$', g.log(), re.M)[loads:loads + 6]]
except Exception as e:
    res['error'] = repr(e)
    print('error', repr(e)[:500], flush=True)
finally:
    res['normal_exit'] = g.close_normally()
    (qa.RUN / 'review-unlock.enabled').unlink(missing_ok=True)
    res['tail'] = [l for l in g.log().splitlines() if l.startswith('chron')][-8:]
qa.dump(f'chron-actions-{label}.json', res)
print(json.dumps({'normal_exit': res['normal_exit'], 'error': res.get('error', '')[:300], 'tail': res['tail']}, ensure_ascii=False, indent=0)[:2500])
