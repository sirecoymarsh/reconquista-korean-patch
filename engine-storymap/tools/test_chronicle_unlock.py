"""모든 콘텐츠 개방 → 연표 cells: capture the chronicle screen (engine's own 800x600 page) with the unlock off and on, then
count differing pixels. Spoiler rule: the captures are never shown or kept; only the numbers are written.
python test_chronicle_unlock.py   -> qa/test_chronicle_unlock.json
"""
import json
import shutil
import time

from PIL import Image, ImageChops

import qa
import test_chronicle_perf as T

RUN = T.RUN
FLAG = RUN / 'review-unlock.enabled'
WM_PERF = 0x8000 + 80


def capture(state, cid):
    FLAG.unlink(missing_ok=True)
    if state == 'on':
        FLAG.write_text('', 'utf-8')
    g = qa.Game(run=RUN, extra_env={'RECON_PERF': '1'})
    out = {}
    try:
        frame = T.keys('クロニクル枠')
        g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
        g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
        if not qa.u.IsWindowVisible(g.hwnd):
            qa.u.ShowWindow(g.hwnd, 4)
        time.sleep(5)
        g.post(g.hwnd, WM_PERF, 10 + cid, 0)
        g.until(lambda: f'quality_capture id={cid} ' in g.log(), 20, 'capture')
        time.sleep(.5)
        keep = qa.HERE / 'build' / 'temp' / f'unlock-{state}-{cid}-base.bmp'   # the next game start clears runtime\qa
        shutil.copy2(RUN / 'qa' / f'quality-{cid:02d}-base.bmp', keep)
        out['base'] = str(keep)
    except Exception as e:  # noqa: BLE001
        out['error'] = repr(e)
    finally:
        out['normal_exit'] = g.close_normally()
        FLAG.unlink(missing_ok=True)
    return out


runs = {'off1': capture('off', 1), 'off2': capture('off', 2), 'on': capture('on', 3)}
result = {k: {a: v for a, v in r.items() if a != 'base'} for k, r in runs.items()}


def compare(x, y):
    a, b = Image.open(runs[x]['base']).convert('RGB'), Image.open(runs[y]['base']).convert('RGB')
    diff = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v else 0)
    cells = diff.crop((95, 71, 760, 574))                 # the chronicle's cell area (logical px)
    return {'pixels': sum(1 for v in diff.getdata() if v), 'in_cell_area': sum(1 for v in cells.getdata() if v), 'box': diff.getbbox()}


if all('base' in r for r in runs.values()):
    result['noise_off_vs_off'] = compare('off1', 'off2')   # the pulsing overlay alone
    result['off_vs_on'] = compare('off1', 'on')
for p in [*(RUN / 'qa').glob('quality-*'), *(qa.HERE / 'build' / 'temp').glob('unlock-*-base.bmp')]:   # spoiler rule
    p.unlink()
result['captures_deleted'] = not any((RUN / 'qa').glob('quality-*')) and not any((qa.HERE / 'build' / 'temp').glob('unlock-*'))
qa.dump('test_chronicle_unlock.json', result)
print(json.dumps(result, ensure_ascii=False))
