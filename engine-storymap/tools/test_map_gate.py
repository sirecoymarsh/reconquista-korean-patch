"""python test_map_gate.py <runtime> <label>: the story map at the title without the review unlock (11-25: it opens with the
story): its first page as drawn, then a press on 최종편 and Enter on the cursor; -> qa/gate-<label>.png and the log lines."""
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa  # noqa: E402

run, label = Path(sys.argv[1]), sys.argv[2]
review = run / 'review-unlock.enabled'
assert not review.exists(), 'the review unlock is on in this copy'
g = qa.Game(run=run)
res = {}
try:
    g.until(lambda: 'load call title' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(2)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    n = g.count('inflow snapshot')
    g.key(g.hwnd, 0x7a)
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open')
    g.snapshot(f'gate-{label}', n)
    child = g.child()
    g.key(child, 0x09)                                   # Tab: 최종편
    time.sleep(.6)
    g.key(child, 0x0d)                                   # Enter on the cursor
    time.sleep(.6)
    res['log'] = [l for l in g.log().splitlines() if l.startswith('inflow ') and ('not_yet' in l or 'page=' in l or 'cursor' in l)][-6:]
except Exception as e:  # noqa: BLE001
    res['error'] = repr(e)
finally:
    res['normal_exit'] = g.close_normally()
    qa.dump(f'gate-{label}.json', res)
    print(json.dumps(res, ensure_ascii=False, indent=1))
