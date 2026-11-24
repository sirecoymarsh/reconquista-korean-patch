"""PNG against JPEG XL on the test_text_speed route, back to back and timing only (RECON_PERF=2, no byte checks):
A hides runtime-test/hires-jxl so every picture comes from its PNG, B uses it. Order A, B, A, B, so the second pair runs
with the files already read once. Per run: first-time loads (open+decode), the slowest present and how many presents
took over 50 and 100 ms.
python ab_jxl.py   -> qa/text_speed-ab-{png,jxl}{1,2}.json/.log, qa/ab_jxl.json
"""
import json
import re
from pathlib import Path

import qa
import test_text_speed as tts

JXL = qa.RUN / 'hires-jxl'
OFF = qa.RUN / 'hires-jxl.off'
PRESENT = re.compile(r'perf_present seq=\d+ total_ms=([\d.]+)')
LOAD = re.compile(r'perf_load key=\w+ size=\d+x\d+ cg=\d cached=0 src=(\w+) open=([\d.]+) get=([\d.]+) alt=[\d.]+ wic=([\d.]+)')


def stats(label):
    log = (qa.QA / f'text_speed-{label}.log').read_text('utf-8', 'replace')
    present = [float(t) for t in PRESENT.findall(log)]
    loads = [(s, float(o) + float(d), float(g)) for s, o, g, d in LOAD.findall(log)]
    return {'presents': len(present), 'slowest_present_ms': max(present, default=0),
            'presents_over_50ms': sum(t > 50 for t in present), 'presents_over_100ms': sum(t > 100 for t in present),
            'first_loads': len(loads), 'load_ms_total': round(sum(t for _, t, _ in loads)), 'load_ms_worst': max((t for _, t, _ in loads), default=0),
            'get_ms_total': round(sum(g for _, _, g in loads)), 'sources': {s: sum(1 for x, _, _ in loads if x == s) for s in {x for x, _, _ in loads}}}


out = {}
try:
    for label, hide in (('ab-png1', True), ('ab-jxl1', False), ('ab-png2', True), ('ab-jxl2', False)):
        if hide and JXL.exists():
            JXL.rename(OFF)
        if not hide and OFF.exists():
            OFF.rename(JXL)
        r = tts.run(label, '2')
        qa.dump(f'text_speed-{label}.json', r)
        out[label] = {'median_line_s': r.get('median_seconds'), 'error': r.get('error'), 'normal_exit': r.get('normal_exit'), **stats(label)}
        print(label, json.dumps(out[label]), flush=True)
finally:
    if OFF.exists() and not JXL.exists():
        OFF.rename(JXL)
(qa.QA / 'ab_jxl.json').write_text(json.dumps(out, indent=1), 'utf-8')
