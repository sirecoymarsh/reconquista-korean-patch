"""Which pictures one 연표 frame draws onto the screen, from the DLL's blit trace (perf mode logs every blit of present 150,
with the source asset name when it has one). Prints the blits that cover a page rect and the overall counts.
python probe_chronicle_trace.py [x0 y0 x1 y1]   (default: the band 335,450 - 612,480)
"""
import re
import sys
from collections import Counter

import qa
import test_chronicle_perf as T

TRACE = re.compile(r'trace (\w) src=\w+ (\d+)x(\d+) box=(-?\d+),(-?\d+),(\d+),(\d+) dst=SCREEN \w+ \d+x\d+ at=(-?\d+),(-?\d+) t=(-?\d+) name=([^\n]*)')
x0, y0, x1, y1 = map(int, sys.argv[1:5]) if len(sys.argv) >= 5 else (335, 450, 612, 480)
g = qa.Game(run=T.RUN, extra_env={'RECON_PERF': '2'})
try:
    frame = T.keys('クロニクル枠')
    g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    g.until(lambda: 'perf_present seq=152 ' in g.log(), 120, 'present 152')
    rows = TRACE.findall(g.log())
    print('screen blits', len(rows))
    hits = [r for r in rows if int(r[8]) < y1 and int(r[8]) + int(r[6]) > y0 and int(r[7]) < x1 and int(r[7]) + int(r[5]) > x0]
    for (kind, size, name), n in Counter((r[0], r[1] + 'x' + r[2], r[10]) for r in hits).most_common(15):
        boxes = sorted({(r[7], r[8], r[5], r[6], r[9]) for r in hits if (r[0], r[1] + 'x' + r[2], r[10]) == (kind, size, name)})[:4]
        print('over rect:', kind, size, repr(name), n, 'e.g. at,size,t:', boxes)
    print('all:', Counter((r[0], r[1] + 'x' + r[2], r[10]) for r in rows).most_common(12))
finally:
    print('normal_exit', g.close_normally())
