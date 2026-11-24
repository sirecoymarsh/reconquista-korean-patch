"""Chronicle speed with the screen batch on, then off (storymap-defer.off), back to back so both see the same PC load.
python tune_defer.py [rounds]   -> qa/tune_defer.json   (runtime-chron, perf mode, verify off)
The worker and band counts were tuned with temporary knobs on 10-24 (7/14, 11/24, 11/48, 15/48, 22/64, 11/96); the DLL now
fixes them (up to one worker per physical core, ~4 bands a thread, at most 48).
"""
import json
import sys

import qa
import test_chronicle_perf as T

OFF = T.RUN / 'storymap-defer.off'


def row(label, r):
    out = {'label': label, 'normal_exit': r.get('normal_exit'), 'error': r.get('error')}
    for k in ('idle', 'drag', 'after'):
        v = r.get(k) or {}
        out[k] = (v.get('per_second'), (v.get('compose') or {}).get('median'))
    return out


rows = []
for n in range(int(sys.argv[1]) if len(sys.argv) > 1 else 1):
    OFF.unlink(missing_ok=True)
    rows.append(row(f'on-{n}', T.run(f'on-{n}')))
    print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    OFF.write_text('', 'utf-8')
    try:
        rows.append(row(f'off-{n}', T.run(f'off-{n}')))
    finally:
        OFF.unlink(missing_ok=True)
    print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
qa.dump('tune_defer.json', rows)
