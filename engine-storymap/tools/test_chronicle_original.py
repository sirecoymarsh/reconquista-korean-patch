"""연표 원래 화면 (F8, chronicle-original.enabled) on runtime-chron: the 연표 in 4K, F8 to the original picture, F8 back.
Checks: the switch is logged and remembered; the original frames skip the 4x (drops counted, presents timed); its output is
the 1x screen enlarged (against a bilinear enlargement of the captured 1x); after F8 back the 4x and the output are as
before F8. The test copy's own 연표 (not opened up); numbers only for the user.
python test_chronicle_original.py [label]   -> qa/chron-original-<label>/ (captures), qa/chron-original-<label>.json
"""
import json, re, sys, time
import numpy as np
from PIL import Image
import qa
import test_chronicle_perf as T
from test_hitch import WM_APP

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
RUN = T.RUN
OUT = qa.QA / f'chron-original-{label}'
OUT.mkdir(parents=True, exist_ok=True)
flag = RUN / 'chronicle-original.enabled'
flag.unlink(missing_ok=True)
(RUN / 'review-unlock.enabled').unlink(missing_ok=True)
g = qa.Game(run=RUN, extra_env={'RECON_PERF': '2'})
res = {'label': label}
shots = RUN / 'qa'
n = 0


def capture(tag):
    global n
    n += 1
    for p in shots.glob(f'quality-{n:02d}-*.bmp'):
        p.unlink()
    g.post(g.hwnd, WM_APP + 80, 10 + n, 0)
    g.until(lambda: (shots / f'quality-{n:02d}-output.bmp').exists(), 20, f'capture {tag}')
    time.sleep(.3)
    out = {}
    for kind in ('hd', 'base', 'output'):
        im = Image.open(shots / f'quality-{n:02d}-{kind}.bmp').convert('RGB')
        im.save(OUT / f'{tag}-{kind}.png')
        out[kind] = np.asarray(im).astype(np.int16)
    m = re.findall(rf'quality_capture id={n} .*viewport=(\d+),(\d+),(\d+),(\d+)', g.log())
    out['viewport'] = tuple(int(v) for v in m[-1]) if m else None
    return out


def f8():
    g.post(g.hwnd, 0x100, 0x77, 1)
    g.post(g.hwnd, 0x101, 0x77, 0xc0000001)


def diff(a, b):
    if a.shape != b.shape:
        return {'shape': [list(a.shape), list(b.shape)]}
    d = np.abs(a - b)
    return {'mean': round(float(d.mean()), 3), 'over8_pct': round(100 * float((d.max(axis=2) > 8).mean()), 3), 'max': int(d.max())}


try:
    frame = T.keys('クロニクル枠')
    g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    g.until(lambda: 'chronicle_open=1' in g.log(), 30, 'chronicle open')
    time.sleep(4)
    res['k4_idle'] = T.window(g, 4)['per_second']
    a = capture('a-4k')
    f8()
    g.until(lambda: 'chronicle_original=1' in g.log(), 10, 'F8 on')
    res['remembered'] = flag.exists()
    time.sleep(1.5)
    res['original_idle'] = T.window(g, 4)['per_second']
    b = capture('b-original')
    f8()
    g.until(lambda: 'chronicle_original=0' in g.log(), 10, 'F8 off')
    res['forgotten'] = not flag.exists()
    time.sleep(1.5)
    c = capture('c-4k-again')
    res['k4_idle_again'] = T.window(g, 4)['per_second']
    res['same_1x_a_b'] = diff(a['base'], b['base'])
    res['hd_a_c'] = diff(a['hd'], c['hd'])
    res['output_a_c'] = diff(a['output'], c['output'])
    if b['viewport']:
        x, y, w, h = b['viewport']
        want = np.asarray(Image.fromarray(b['base'].astype(np.uint8)).resize((w, h), Image.BILINEAR)).astype(np.int16)
        res['original_output_vs_1x_enlarged'] = diff(b['output'][y:y + h, x:x + w], want)
        res['original_output_vs_4k_output'] = diff(b['output'], a['output'])
    log = g.log()
    res['original_lines'] = [l for l in log.splitlines() if l.startswith('original ')][-2:]
    res['problems'] = [l for l in log.splitlines() if 'original_present_failed' in l or 'defer_mismatch' in l][:5]
except Exception as e:
    res['error'] = repr(e)
finally:
    res['normal_exit'] = g.close_normally()
    flag.unlink(missing_ok=True)
    qa.dump(f'chron-original-{label}.json', res)
    print(json.dumps(res, ensure_ascii=False))
