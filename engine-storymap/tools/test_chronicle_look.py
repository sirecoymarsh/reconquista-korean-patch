"""The config screen's 「연표: 새 모양 / 원래 모양」 (10-27): runtime-test, the title's 설정, the button shown next to 「CG·메뉴」,
clicked twice: the look flips and is remembered in chronicle-look.ini each time.
python test_chronicle_look.py [label]   -> qa/chron-look-<label>.json
"""
import json, sys, time
from ctypes import wintypes as w
import qa

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
INI = qa.RUN / 'chronicle-look.ini'
INI.unlink(missing_ok=True)
res = {'label': label, 'steps': []}
g = qa.Game(extra_env={'RECON_CHRON_PROTO': '1', 'RECON_HD_START_FULLSCREEN': '1', 'RECON_PERF': '2'})
qa.u.GetDlgItem.argtypes = [w.HWND, w.INT]
qa.u.GetDlgItem.restype = w.HWND
qa.u.IsWindowVisible.argtypes = [w.HWND]


def lines(prefix):
    return [l for l in g.log().splitlines() if l.startswith(prefix)]


def step(name, **kw):
    res['steps'].append({'step': name, **kw})
    print(name, json.dumps(kw, ensure_ascii=False)[:400], flush=True)


def hover(x, y):
    r = qa.w.RECT()
    qa.u.GetClientRect(g.hwnd, qa.c.byref(r))
    vw = min(r.right, r.bottom * 4 // 3)
    vh = vw * 3 // 4
    g.post(g.hwnd, 0x200, 0, ((((r.bottom - vh) // 2 + round(y * vh / 600)) & 0xffff) << 16) | (((r.right - vw) // 2 + round(x * vw / 800)) & 0xffff))
    time.sleep(.4)


try:
    g.until(lambda: 'asset 1de0628c ' in g.log() or 'asset ef1f6a40 ' in g.log() or 'asset c1e942c6 ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(3)
    t0 = time.time()
    while time.time() - t0 < 30 and not lines('chron_proto look_button shown'):
        hover(620, 430)                                  # the title's 설정
        g.logical_click(g.hwnd, 620, 430)
        end = time.time() + 3
        while time.time() < end and not lines('chron_proto look_button shown'):
            time.sleep(.1)
    g.until(lambda: lines('chron_proto look_button shown'), 3, 'look button')
    time.sleep(.5)
    b = qa.u.GetDlgItem(g.hwnd, 0x7e47)
    step('shown', line=lines('chron_proto look_button')[-1], visible=bool(b and qa.u.IsWindowVisible(b)))
    shots = qa.RUN / 'qa'
    for p in shots.glob('quality-07-*.bmp') if shots.exists() else []:
        p.unlink()
    g.post(g.hwnd, 0x8000 + 80, 17, 0)
    g.until(lambda: (shots / 'quality-07-output.bmp').exists(), 20, 'capture config')
    time.sleep(.5)
    from PIL import Image
    Image.open(shots / 'quality-07-output.bmp').convert('RGB').save(qa.QA / f'chron-look-{label}-config.png')
    for k in range(2):
        g.post(b, 0x201, 1, (5 << 16) | 20)
        time.sleep(.1)
        g.post(b, 0x202, 0, (5 << 16) | 20)
        g.until(lambda: len(lines('chron_proto look=')) > k, 5, f'click {k}')
        time.sleep(.3)
        step(f'click {k}', line=lines('chron_proto look=')[-1], ini=INI.read_text('utf-16', errors='replace').strip() if INI.exists() and INI.read_bytes()[:2] == b'\xff\xfe' else (INI.read_text('utf-8', errors='replace').strip() if INI.exists() else None))
except Exception as e:
    res['error'] = repr(e)
    print('error', repr(e)[:400], flush=True)
finally:
    res['normal_exit'] = g.close_normally()
    INI.unlink(missing_ok=True)
qa.dump(f'chron-look-{label}.json', res)
print(json.dumps({'normal_exit': res['normal_exit'], 'error': res.get('error', '')[:300]}, ensure_ascii=False))
