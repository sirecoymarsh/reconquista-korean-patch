"""python test_map_hover.py <label> [seconds before opening]: story map hover sweep (perf mode): every partial paint is checked against a full render (inflow partial_check)."""
import sys, time, re, json
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools')
import qa
from test_more import VK, boot, open_chart
label = sys.argv[1]
g = qa.Game(extra_env={'RECON_PERF': '2'})
res = {}
try:
    boot(g)
    if not qa.u.IsWindowVisible(g.hwnd): qa.u.ShowWindow(g.hwnd, 4)
    time.sleep(float(sys.argv[2]) if len(sys.argv) > 2 else 6); child = open_chart(g); time.sleep(1.5)
    for y in range(120, 540, 24):
        for x in range(100, 760, 36):
            g.move(child, x, y); time.sleep(.025)
    for x, y in [(445, 35), (576, 20), (576, 48), (693, 35), (300, 300), (445, 35)]:
        g.move(child, x, y); time.sleep(.2)
    time.sleep(1)
    g.key(child, VK['RET']); time.sleep(2)              # a chapter page: its plates
    for x, y in [(684, 34), (684, 66), (472, 538), (685, 538), (300, 300), (684, 34), (400, 400)]:
        g.move(child, x, y); time.sleep(.2)
    time.sleep(1)
finally:
    res['normal_exit'] = g.close_normally()
log = g.log()
chk = re.findall(r'inflow partial_check equal=(\d)', log)
ren = [(int(p), float(ms), int(parts)) for p, ms, parts in re.findall(r'inflow render page=(\d) ms=([\d.]+) size=\S+ parts=(\d+)', log)]
part = sorted(ms for p, ms, n in ren if n > 0); full = [ms for p, ms, n in ren if n == 0]
res.update(checks=len(chk), unequal=chk.count('0'), partial_n=len(part), partial_median=part[len(part)//2] if part else None, partial_max=part[-1] if part else None, full=full[:6])
(qa.QA / f'map-hover-{label}.log').write_text(log, 'utf-8'); print(json.dumps(res))
