"""연표 open / close / scene latency on a hardlinked copy of runtime-final-20261028 (private desktop). Measurement only."""
import sys, time, re, json, threading
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from pathlib import Path
import qa
from test_hitch import VK
RUN = Path(sys.argv[1]); label = sys.argv[2]; proto = sys.argv[3] if len(sys.argv) > 3 else '1'
env = {'RECON_HD_START_FULLSCREEN': '1', 'RECON_PERF': '2', 'RECON_HITCH': '1', 'RECON_CHRON_PROTO': None if proto == '0' else proto}
(RUN / 'review-unlock.enabled').unlink(missing_ok=True)
(RUN / 'storymap-read.bin').unlink(missing_ok=True)
g = qa.Game(run=RUN, extra_env=env)
lines = []  # (t, line)
stop = False
def tail():
    p = RUN / 'hires-runtime.log'; f = None; buf = b''
    while not stop:
        if f is None:
            if p.exists(): f = open(p, 'rb')
            else: time.sleep(.01); continue
        ch = f.read()
        if ch:
            t = time.perf_counter(); buf += ch
            *done, buf = buf.split(b'\n')
            for l in done: lines.append((t, l.decode('utf8', 'replace')))
        else: time.sleep(.0005)
th = threading.Thread(target=tail, daemon=True); th.start()
def first(pred, after, timeout):
    end = time.perf_counter() + timeout; i = 0
    while time.perf_counter() < end:
        for t, l in lines[i:]:
            if t >= after and pred(l): return t
        i = max(0, len(lines) - 1) if False else 0
        time.sleep(.005)
    return None
res = {'label': label, 'proto': proto, 'opens': [], 'closes': [], 'scene': None}
def ms(a, b): return None if (a is None or b is None) else round((a - b) * 1000)
try:
    g.until(lambda: 'asset 1de0628c ' in g.log() or 'asset ef1f6a40 ' in g.log(), 120, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(4)
    if not qa.u.IsWindowVisible(g.hwnd): qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]: qa.u.SendMessageW(g.hwnd, m, a, 0)
    g.key(g.hwnd, VK['F11']); g.until(lambda: 'inflow opened' in g.log(), 20, 'open map')
    child = g.child(); time.sleep(.5)
    g.key(child, VK['RET']); g.until(lambda: re.search(r'page=2 chapter=\d+', g.log()), 10, 'chapter page'); time.sleep(.5)
    g.story_jump(child); g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump')
    o = int(g.log().split('inflow jump order=')[-1].split()[0]); g.until(lambda: f'inflow arrived order={o} ' in g.log(), 120, 'arrival')
    time.sleep(4)
    def open_once():
        t0 = None; deadline = time.time() + 60
        while time.time() < deadline:
            g.logical_click(g.hwnd, 400, 520); time.sleep(1.2)
            g.move(g.hwnd, 770, 510); time.sleep(.4)
            t0 = time.perf_counter(); g.logical_click(g.hwnd, 770, 510)
            got = first(lambda l: l.startswith('chronicle_open=1'), t0, 3)
            if got: break
        r = {'chronicle_open_ms': ms(got, t0),
             'replace_ms': ms(first(lambda l: 'chron_proto replace opened' in l, t0, 10), t0),
             'shown_ms': ms(first(lambda l: 'chron_proto show ' in l, t0, 15), t0)}
        time.sleep(8)
        r['loads_during_open'] = sum(1 for t, l in lines if t >= t0 and l.startswith('perf_load'))
        r['decode_ms_during_open'] = round(sum(float(m.group(1)) for t, l in lines if t >= t0 for m in [re.search(r'decode=([\d.]+)', l)] if m and l.startswith('perf_load')))
        r['presents_while_open'] = sum(1 for t, l in lines if t >= t0 and l.startswith('perf_present'))
        return r
    def close_once():
        pv = qa.u.FindWindowExW(g.hwnd, None, 'ReconChronicleProto', None)
        t0 = time.perf_counter()
        if pv:
            g.post(pv, 0x200, 0, (500 << 16) | 500); g.post(pv, 0x204, 2, (500 << 16) | 500); g.post(pv, 0x205, 0, (500 << 16) | 500)
        else:
            g.move(g.hwnd, 400, 330); g.post(g.hwnd, 0x204, 2, 0); g.logical_click(g.hwnd, 400, 330, button='right')
        r = {'game_closed_ms': ms(first(lambda l: l.startswith('chronicle_open=0'), t0, 10), t0),
             'act_done_ms': ms(first(lambda l: 'chron_proto act=3 done=1' in l or 'closed_by_game' in l, t0, 10), t0)}
        time.sleep(.3)
        r['first_game_present_after_ms'] = ms(first(lambda l: l.startswith('perf_scale'), t0 + (r['game_closed_ms'] or 0) / 1000, 5), t0)
        time.sleep(2)
        return r
    for i in range(3):
        res['opens'].append(open_once()); print('open', res['opens'][-1], flush=True)
        res['closes'].append(close_once()); print('close', res['closes'][-1], flush=True)
    if True:
        res['opens'].append(open_once()); print('open', res['opens'][-1], flush=True)
        pv = qa.u.FindWindowExW(g.hwnd, None, 'ReconChronicleProto', None)
        t0 = time.perf_counter(); g.post(pv, 0x8000 + 6, 0, 0)
        res['scene'] = {'act_done_ms': ms(first(lambda l: 'act=1 done=1' in l, t0, 15), t0),
                        'game_closed_ms': ms(first(lambda l: l.startswith('chronicle_open=0'), t0, 15), t0)}
        time.sleep(1)
        gc = res['scene']['game_closed_ms']
        res['scene']['first_present_after_close_ms'] = ms(first(lambda l: l.startswith('perf_scale'), t0 + (gc or 0) / 1000, 10), t0)
        print('scene', res['scene'], flush=True)
        time.sleep(5)
except Exception as e:
    res['error'] = repr(e)[:1500]; print(res['error'])
finally:
    res['normal_exit'] = g.close_normally(); stop = True
    (qa.QA / f'chron-latency-{label}.log').write_text('\n'.join(f'{t:.4f} {l}' for t, l in lines), 'utf-8')
    qa.dump(f'chron-latency-{label}.json', res)
print(json.dumps(res, ensure_ascii=False))
