"""Visible run on the real desktop: open the 연표, then framemeter measures what reaches the screen while real input scrolls."""
import sys, time, re, json, subprocess, os
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from pathlib import Path
import ctypes as c
import qa
from test_hitch import VK
RUN = Path(sys.argv[1]); label = sys.argv[2]; proto = sys.argv[3]
FM = Path(__file__).resolve().parent / 'framemeter'   # framemeter.exe: cl /O2 /EHsc framemeter.cpp user32.lib winmm.lib (x64)
qa.desktop = None
class VGame(qa.Game):
    def __init__(self, run, env_extra):
        self.run = run
        env = os.environ.copy()
        env.update(RECON_FLOW_PROBE='1', TEMP=str(qa.HERE / 'build' / 'temp'), TMP=str(qa.HERE / 'build' / 'temp'))
        for n in ['RECON_HD_PROBE', 'RECON_REVIEW_PROBE', 'RECON_INPUT_PROBE', 'RECON_CONFIG_PROBE', 'RECON_PERF', 'RECON_CHRON_PROTO', 'RECON_HITCH']: env.pop(n, None)
        env.update({k: v for k, v in env_extra.items() if v is not None})
        log = run / 'hires-runtime.log'
        if log.exists(): os.replace(log, qa.QA / f'before-{time.time_ns()}.log')
        self.p = subprocess.Popen([str(run / 'レコンキスタ.exe')], cwd=str(run), env=env)
        self.pid = self.p.pid; self.handle = int(c.windll.kernel32.OpenProcess(0x1F0FFF, False, self.pid)); self.hwnd = None; self.started = time.time()
    def windows(self):
        out = []
        def cb(h, l):
            pid = qa.w.DWORD(); qa.u.GetWindowThreadProcessId(h, c.byref(pid))
            if pid.value == self.pid:
                cl = c.create_unicode_buffer(128); qa.u.GetClassNameW(h, cl, 128); out.append({'h': int(h), 'class': cl.value, 'title': ''})
            return True
        qa.u.EnumWindows(qa.CB(cb), 0); return out
qa.u.EnumWindows.argtypes = [qa.CB, c.c_ssize_t]
if len(sys.argv) < 5: (RUN / 'review-unlock.enabled').unlink(missing_ok=True)
(RUN / 'storymap-read.bin').unlink(missing_ok=True)
env = {'RECON_HD_START_FULLSCREEN': '1', 'RECON_CHRON_PROTO': None if proto == '0' else '1', 'RECON_HITCH': '1'}
g = VGame(RUN, env); res = {'label': label, 'proto': proto, 'runs': {}}
def fg():
    qa.u.keybd_event(0x12, 0, 0, 0); qa.u.keybd_event(0x12, 0, 2, 0)   # an Alt tap lets this process hand the foreground over
    qa.u.ShowWindow(g.hwnd, 5); qa.u.SetForegroundWindow(g.hwnd); qa.u.BringWindowToTop(g.hwnd)
try:
    g.until(lambda: 'mode full=1' in g.log(), 120, 'fullscreen'); time.sleep(6)
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(4); fg()
    g.key(g.hwnd, VK['F11']); g.until(lambda: 'inflow opened' in g.log(), 20, 'open map')
    child = g.child(); time.sleep(.5)
    g.key(child, VK['RET']); g.until(lambda: re.search(r'page=2 chapter=\d+', g.log()), 10, 'chapter'); time.sleep(.5)
    g.story_jump(child); g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump')
    o = int(g.log().split('inflow jump order=')[-1].split()[0]); g.until(lambda: f'inflow arrived order={o} ' in g.log(), 120, 'arrival')
    time.sleep(4)
    end = time.time() + 60
    while time.time() < end and 'chronicle_open=1' not in g.log():
        g.logical_click(g.hwnd, 400, 520); time.sleep(1.2); g.move(g.hwnd, 770, 510); time.sleep(.4); g.logical_click(g.hwnd, 770, 510); time.sleep(2)
    assert 'chronicle_open=1' in g.log(), 'chronicle did not open'
    time.sleep(3); fg(); time.sleep(.5)
    r = qa.w.RECT(); qa.u.GetClientRect(g.hwnd, c.byref(r)); vw = min(r.right, r.bottom * 4 // 3); vh = vw * 3 // 4; vx = (r.right - vw) // 2; vy = (r.bottom - vh) // 2
    pt = qa.w.POINT(vx, vy); qa.u.ClientToScreen.argtypes = [qa.w.HWND, c.POINTER(qa.w.POINT)]; qa.u.ClientToScreen(g.hwnd, c.byref(pt))
    # the table body (800x600 units: x 95..770, y 114..574) in screen pixels
    bx, by = pt.x + round(110 * vw / 800), pt.y + round(120 * vh / 600); bw, bh = round(650 * vw / 800), round(440 * vh / 600)
    cx, cy = bx + bw // 2, by + bh // 2
    for mode, secs in [('idle', 3), ('wheel', 8), ('keys', 6), ('drag', 6)]:
        fg(); time.sleep(.3)
        out = subprocess.run([str(FM / 'framemeter.exe'), str(secs), str(bx), str(by), str(bw), str(bh), mode, str(cx), str(cy - 250)], cwd=str(FM), capture_output=True, text=True, timeout=60).stdout
        fgw = qa.u.GetForegroundWindow(); top = qa.u.GetAncestor(fgw, 2) if fgw else 0
        res['runs'][mode] = out.strip() + f' foreground_game={int(top) == g.hwnd}'; print(mode, res['runs'][mode], flush=True)
        os.replace(FM / 'frames.csv', FM / f'frames-{label}-{mode}.csv'); time.sleep(1)
    pv = qa.u.FindWindowExW(g.hwnd, None, 'ReconChronicleProto', None)
    if pv: g.post(pv, 0x204, 2, (500 << 16) | 500); g.post(pv, 0x205, 0, (500 << 16) | 500); time.sleep(2)
except Exception as e:
    res['error'] = repr(e)[:1500]; print(res['error'])
finally:
    res['normal_exit'] = g.close_normally()
    (qa.QA / f'visible-fps-{label}.log').write_text(g.log(), 'utf-8'); qa.dump(f'visible-fps-{label}.json', res)
