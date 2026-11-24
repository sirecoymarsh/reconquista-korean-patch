"""The story map's 다시보기 (10-27): runtime-test, hidden desktop, silenced.
  title  : at the title, F11, the cursor's chapter, its last scene's last lines -> 다시보기; reading on to the chapter's end
           must put the game back at the title and open the map again on that chapter
  ingame : 「여기서부터 본편으로」 into the story first, a line read on; then 다시보기 of another chapter's last lines; at its end
           the game must be loaded back where it was (the map opens again on the replayed chapter, 지금 자리 the old line), and
           one line read after closing the map must be the line after the old one
python test_replay.py title|ingame [label]   -> qa/replay-<mode>-<label>.json (no pictures)
"""
import json, re, sys, time
import qa
from test_hitch import VK

mode = sys.argv[1] if len(sys.argv) > 1 else 'title'
label = sys.argv[2] if len(sys.argv) > 2 else 'now'
VK.update(dict(END=0x23, HOME=0x24, ESC=0x1b))
res = {'mode': mode, 'label': label, 'steps': []}
before = qa.savehash()
g = qa.Game(extra_env={'RECON_PERF': '2', 'RECON_HD_START_FULLSCREEN': '1', 'RECON_FLOW_PROBE': None})   # no map snapshot per redraw (26 MB each)


def lines(prefix):
    return [l for l in g.log().splitlines() if l.startswith(prefix)]


def step(name, **kw):
    res['steps'].append({'step': name, 't': round(time.time() - g.started, 1), **kw})
    print(name, json.dumps(kw, ensure_ascii=False)[:400], flush=True)


def opened_here():
    return int(lines('inflow opened here=')[-1].split('here=')[1].split()[0])


def open_map():
    n = g.count('inflow opened here=')
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: g.count('inflow opened here=') > n, 20, 'map opens')
    time.sleep(.5)
    return g.child()


def replay_last_lines(child, back=2):
    """the cursor's chapter, its last scene, `back` lines before its last line: 다시보기 (Enter)"""
    n = g.count('page=2 chapter=')
    g.key(child, VK['RET'])
    g.until(lambda: g.count('page=2 chapter=') > n, 10, 'chapter page')
    chapter = int(re.findall(r'page=2 chapter=(\d+)', g.log())[-1])
    g.key(child, VK['RIGHT'], times=80, gap=.01)
    time.sleep(4)                       # each step redraws the page
    g.key(child, VK['END'])
    g.key(child, VK['UP'], times=back)
    time.sleep(.3)
    j = g.count('inflow jump order=')
    g.key(child, VK['RET'])
    g.until(lambda: g.count('inflow jump order=') > j, 10, 'replay request')
    return chapter


def read_until(what, limit=90):
    t0 = time.time()
    while time.time() - t0 < limit and what not in g.log():
        g.logical_click(g.hwnd, 400, 520)
        time.sleep(1.0)
    g.until(lambda: what in g.log(), 3, what)


try:
    g.until(lambda: 'asset 1de0628c ' in g.log() or 'asset ef1f6a40 ' in g.log() or 'asset c1e942c6 ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(3)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    if mode in ('ingame', 'esc', 'mapend'):
        child = open_map()
        n = g.count('page=2 chapter=')
        g.key(child, VK['RET'])
        g.until(lambda: g.count('page=2 chapter=') > n, 10, 'chapter page')
        time.sleep(.5)
        g.story_jump(child)
        g.until(lambda: 'inflow jump order=' in g.log(), 10, 'story jump')
        got = int(g.log().split('inflow jump order=')[-1].split()[0])
        g.until(lambda: f'inflow arrived order={got} ' in g.log(), 120, 'story arrival')
        time.sleep(3)
        g.logical_click(g.hwnd, 400, 520)   # a line on, so the old place is not the jump's own line
        time.sleep(2)
        child = open_map()
        res['before_here'] = opened_here()
        step('in story', arrived=lines('inflow arrived')[-1:], here=res['before_here'])
        g.key(child, VK['UP'])              # an earlier day's chapter to replay: reading on from the old place can never land in it
        time.sleep(.3)
    else:
        child = open_map()
        step('map at title', opened=lines('inflow opened')[-1:])
    if mode == 'storyjump':                  # the old jump to the same place (chapter 9's last lines): does it get there at all?
        g.key(child, VK['DOWN'])
        time.sleep(.3)
        n = g.count('page=2 chapter=')
        g.key(child, VK['RET'])
        g.until(lambda: g.count('page=2 chapter=') > n, 10, 'chapter page')
        g.key(child, VK['RIGHT'], times=80, gap=.01)
        time.sleep(4)
        g.key(child, VK['END'])
        g.key(child, VK['UP'], times=2)
        time.sleep(.3)
        g.story_jump(child)
        g.until(lambda: 'inflow jump order=' in g.log(), 10, 'story jump')
        got = int(g.log().split('inflow jump order=')[-1].split()[0])
        t0 = time.time()
        try:
            g.until(lambda: f'inflow arrived order={got} ' in g.log(), 150, 'story arrival')
            res['pass'] = True
        except Exception as e:
            res['pass'] = False
            res['stall'] = [l[:120] for l in g.log().splitlines() if l.startswith('load call')][-6:]
        step('story jump', order=got, seconds=round(time.time() - t0, 1), arrived=lines('inflow arrived')[-1:], cover=lines('inflow cover')[-1:])
        raise SystemExit
    chapter = replay_last_lines(child)
    step('replay asked', chapter=chapter, start=lines('inflow replay_start')[-1:], jump=lines('inflow jump order=')[-1:])
    got = int(g.log().split('inflow jump order=')[-1].split()[0])
    g.until(lambda: re.search(rf'inflow arrived order={got} .*replay=1', g.log()), 120, 'replay arrival')
    step('replay playing', arrived=lines('inflow arrived')[-1:], cover=g.count('inflow closed_cover'))
    if mode == 'esc':                       # Esc in the game ends it at once
        time.sleep(2)
        g.key(g.hwnd, VK['ESC'])
        g.until(lambda: 'inflow replay_return why=' in g.log(), 15, 'esc return')
    elif mode == 'mapend':                  # F11, then the map's 「다시보기 끝내기」 (its third plate)
        time.sleep(2)
        child = open_map()
        r = qa.w.RECT()
        qa.u.GetClientRect(child, qa.c.byref(r))
        vw = min(r.right, r.bottom * 4 // 3)
        vh = vw * 3 // 4
        lp = ((((r.bottom - vh) // 2 + round(48 * vh / 600)) & 0xffff) << 16) | (((r.right - vw) // 2 + round(577 * vw / 800)) & 0xffff)
        g.post(child, 0x200, 0, lp)
        time.sleep(.2)
        g.post(child, 0x201, 1, lp)
        g.post(child, 0x202, 0, lp)
        g.until(lambda: 'inflow replay_return why=' in g.log(), 15, 'map end return')
    else:
        read_until('inflow replay_return why=')
    step('return', why=lines('inflow replay_return why=')[-1:])
    g.until(lambda: 'inflow replay_reopen' in g.log(), 60, 'map again')
    g.until(lambda: g.count('inflow opened here=') >= {'ingame': 3, 'esc': 3, 'mapend': 4}.get(mode, 2), 20, 'map opened')
    res['after_here'] = opened_here()
    step('map again', opened=lines('inflow opened')[-1:], to_title=g.count('inflow replay_to_title'))
    child = g.child()
    g.key(child, VK['ESC'])
    g.until(lambda: 'inflow closed_resume' in g.log(), 10, 'map closed')
    time.sleep(1.5)
    if mode in ('ingame', 'esc', 'mapend'):
        for _ in range(4):                   # read on from the old place (a day card or a scene change can come first)
            g.logical_click(g.hwnd, 400, 520)
            time.sleep(2)
        open_map()
        res['next_here'] = opened_here()
        g.key(g.child(), VK['ESC'])
        time.sleep(1)
        # read on from where it was: forward of the old line (left in the replayed, earlier chapter it would be behind it)
        res['pass'] = res['after_here'] == res['before_here'] and res['next_here'] > res['before_here'] and 'load=1' in lines('inflow replay_return why=')[-1]
    else:
        res['pass'] = 'load=0' in lines('inflow replay_return why=')[-1] and g.count('inflow replay_to_title') == 1
    step('result', before=res.get('before_here'), after=res['after_here'], next=res.get('next_here'), passed=res['pass'])
except SystemExit:
    pass
except Exception as e:
    res['error'] = repr(e)
    print('error', repr(e)[:600], flush=True)
finally:
    res['normal_exit'] = g.close_normally()
    after = qa.savehash()
    res['savedata_changed'] = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    res['tail'] = [l for l in g.log().splitlines() if l.startswith('inflow') and 'render' not in l][-25:]
qa.dump(f'replay-{mode}-{label}.json', res)
print(json.dumps({k: res.get(k) for k in ('pass', 'error', 'normal_exit', 'savedata_changed', 'before_here', 'after_here', 'next_here')}, ensure_ascii=False))
