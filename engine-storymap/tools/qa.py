"""Private-desktop QA helpers for the 이야기 지도 build (no audio, no user input, normal exit at the end)."""
import ctypes as c
import hashlib
import json
import os
import time
from ctypes import wintypes as w
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parents[1]
RUN = HERE / 'runtime-test'
QA = HERE / 'qa'
QA.mkdir(exist_ok=True)
u = c.WinDLL('user32', use_last_error=True)
k = c.WinDLL('kernel32', use_last_error=True)
u.CreateDesktopW.argtypes = [w.LPCWSTR, c.c_void_p, c.c_void_p, w.DWORD, w.DWORD, c.c_void_p]
u.CreateDesktopW.restype = w.HANDLE
DESK = 'ReconquistaStoryMapTest'
desktop = u.CreateDesktopW(DESK, None, None, 0, 0x1ff, None)
assert desktop
CB = c.WINFUNCTYPE(w.BOOL, w.HWND, c.c_ssize_t)
u.EnumDesktopWindows.argtypes = [w.HANDLE, CB, c.c_ssize_t]
u.EnumChildWindows.argtypes = [w.HWND, CB, c.c_ssize_t]
u.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u.SendMessageW.restype = c.c_ssize_t
u.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, c.c_int]
u.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, c.c_int]
u.GetClientRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
u.FindWindowExW.argtypes = [w.HWND, w.HWND, w.LPCWSTR, w.LPCWSTR]
u.FindWindowExW.restype = w.HWND
u.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]


class SI(c.Structure):
    _fields_ = [('cb', w.DWORD), ('lpReserved', w.LPWSTR), ('lpDesktop', w.LPWSTR), ('lpTitle', w.LPWSTR), ('dwX', w.DWORD), ('dwY', w.DWORD),
                ('dwXSize', w.DWORD), ('dwYSize', w.DWORD), ('dwXCountChars', w.DWORD), ('dwYCountChars', w.DWORD), ('dwFillAttribute', w.DWORD),
                ('dwFlags', w.DWORD), ('wShowWindow', w.WORD), ('cbReserved2', w.WORD), ('lpReserved2', c.c_void_p), ('hStdInput', w.HANDLE),
                ('hStdOutput', w.HANDLE), ('hStdError', w.HANDLE)]


class PI(c.Structure):
    _fields_ = [('hProcess', w.HANDLE), ('hThread', w.HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]


k.CreateProcessW.argtypes = [w.LPCWSTR, w.LPWSTR, c.c_void_p, c.c_void_p, w.BOOL, w.DWORD, c.c_void_p, w.LPCWSTR, c.POINTER(SI), c.POINTER(PI)]
k.GetExitCodeProcess.argtypes = [w.HANDLE, c.POINTER(w.DWORD)]
k.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
k.TerminateProcess.argtypes = [w.HANDLE, w.UINT]


class Game:
    def __init__(self, run=RUN, extra_env=None):
        self.run = run
        env = os.environ.copy()
        env.update(RECON_HD_PROBE='2', RECON_FLOW_PROBE='1', TEMP=str(HERE / 'build' / 'temp'), TMP=str(HERE / 'build' / 'temp'))
        for name in ['RECON_HD_START_FULLSCREEN', 'RECON_REVIEW_PROBE', 'RECON_INPUT_PROBE', 'RECON_CONFIG_PROBE', 'RECON_PERF']:
            env.pop(name, None)
        env.update(extra_env or {})
        env = {a: b for a, b in env.items() if b is not None}          # extra_env value None drops a variable
        log = run / 'hires-runtime.log'
        if log.exists():
            os.replace(log, QA / f'before-{time.time_ns()}.log')
        for p in (run / 'qa').glob('*.bmp') if (run / 'qa').exists() else []:
            p.unlink()
        si = SI()
        si.cb = c.sizeof(si)
        si.lpDesktop = 'winsta0\\' + DESK
        si.dwFlags = 1
        si.wShowWindow = 0
        pi = PI()
        eb = c.create_unicode_buffer('\0'.join(f'{a}={b}' for a, b in sorted(env.items())) + '\0\0')
        exe = run / 'レコンキスタ.exe'
        assert k.CreateProcessW(str(exe), None, None, None, False, 0x400, eb, str(run), c.byref(si), c.byref(pi)), c.get_last_error()
        self.pid, self.handle = pi.pid, pi.hProcess
        k.CloseHandle(pi.hThread)
        self.hwnd = None
        self.started = time.time()

    def poll(self):
        v = w.DWORD()
        k.GetExitCodeProcess(self.handle, c.byref(v))
        return None if v.value == 259 else v.value

    def log(self):
        p = self.run / 'hires-runtime.log'
        return p.read_text('utf8', errors='replace') if p.exists() else ''

    def windows(self):
        out = []

        def cb(h, l):
            pid = w.DWORD()
            u.GetWindowThreadProcessId(h, c.byref(pid))
            if pid.value == self.pid:
                t = c.create_unicode_buffer(512)
                cl = c.create_unicode_buffer(128)
                u.GetWindowTextW(h, t, 512)
                u.GetClassNameW(h, cl, 128)
                out.append({'h': int(h), 'title': t.value, 'class': cl.value})
            return True
        u.EnumDesktopWindows(desktop, CB(cb), 0)
        return out

    def until(self, pred, seconds=30, what=''):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if pred():
                return
            if self.poll() is not None:
                raise RuntimeError(f'process exited {self.poll()} while waiting {what}: ' + self.log()[-1500:])
            time.sleep(.1)
        raise RuntimeError(f'timeout {what}: ' + self.log()[-1500:])

    def count(self, s):
        return self.log().count(s)

    def post(self, h, m, a=0, b=0):
        assert u.PostMessageW(h, m, a, b), c.get_last_error()

    def key(self, h, vk, times=1, gap=0.05):
        for _ in range(times):
            self.post(h, 0x100, vk)
            self.post(h, 0x101, vk, 0xC0000001)
            time.sleep(gap)

    def chars(self, h, text):
        for ch in text:
            self.post(h, 0x102, ord(ch))
            time.sleep(.03)

    def child(self):
        return u.FindWindowExW(self.hwnd, None, 'ReconquistaInGameFlow', None)

    def edit(self):
        ch = self.child()
        return u.FindWindowExW(ch, None, 'EDIT', None) if ch else None

    def logical_click(self, h, x, y, double=False, button='left'):
        r = w.RECT()
        u.GetClientRect(h, c.byref(r))
        vw = min(r.right, r.bottom * 4 // 3)
        vh = vw * 3 // 4
        px = (r.right - vw) // 2 + round(x * vw / 800)
        py = (r.bottom - vh) // 2 + round(y * vh / 600)
        lp = ((py & 0xffff) << 16) | (px & 0xffff)
        down, up = (0x201, 0x202) if button == 'left' else (0x204, 0x205)
        self.post(h, 0x200, 0, lp)
        self.post(h, down, 1, lp)
        self.post(h, up, 0, lp)
        if double:
            self.post(h, 0x203, 1, lp)
            self.post(h, up, 0, lp)

    def story_jump(self, child):
        """the chapter page's 「여기서부터 본편으로」 plate (10-27: Enter there is 다시보기 now, which ends at the chapter's end)"""
        r = w.RECT()
        u.GetClientRect(child, c.byref(r))
        vw = min(r.right, r.bottom * 4 // 3)
        vh = vw * 3 // 4
        lp = ((((r.bottom - vh) // 2 + round(538 * vh / 600)) & 0xffff) << 16) | (((r.right - vw) // 2 + round(685 * vw / 800)) & 0xffff)
        self.post(child, 0x200, 0, lp)
        time.sleep(.1)
        self.post(child, 0x201, 1, lp)
        self.post(child, 0x202, 0, lp)

    def client_point(self, h, x, y):
        r = w.RECT()
        u.GetClientRect(h, c.byref(r))
        vw = min(r.right, r.bottom * 4 // 3)
        vh = vw * 3 // 4
        return (r.right - vw) // 2 + round(x * vw / 800), (r.bottom - vh) // 2 + round(y * vh / 600)

    def move(self, h, x, y):
        px, py = self.client_point(h, x, y)
        self.post(h, 0x200, 0, ((py & 0xffff) << 16) | (px & 0xffff))

    def wheel(self, h, x, y, notches):
        px, py = self.client_point(h, x, y)
        pt = w.POINT(px, py)
        u.ClientToScreen.argtypes = [w.HWND, c.POINTER(w.POINT)]
        u.ClientToScreen(h, c.byref(pt))
        self.post(h, 0x20a, ((notches * 120) & 0xffff) << 16, ((pt.y & 0xffff) << 16) | (pt.x & 0xffff))

    def last(self, prefix):
        part = self.log().split(prefix)[-1].split()[0]
        return int(part)

    def snapshot(self, name, after_count):
        """Newest inflow BMP written after the given snapshot count -> qa/<name>.png."""
        self.until(lambda: self.count('inflow snapshot') > after_count, 15, 'snapshot ' + name)
        time.sleep(.3)
        files = sorted((self.run / 'qa').glob('inflow-*.bmp'), key=lambda p: p.stat().st_mtime_ns)
        Image.open(files[-1]).save(QA / f'{name}.png')
        return QA / f'{name}.png'

    def close_normally(self):
        if self.poll() is not None:
            return True
        for x in self.windows():
            if x['class'] == 'MAJIRO_EXEC_CLASS':
                self.post(x['h'], 0x10)
        deadline = time.time() + 15
        while self.poll() is None and time.time() < deadline:
            for x in self.windows():
                if x['class'] == '#32770':
                    self.post(x['h'], 0x111, 6, 0)
            time.sleep(.25)
        ok = self.poll() is not None
        if not ok:
            k.TerminateProcess(self.handle, 1)
        return ok


def savehash(run=RUN):
    return {str(p.relative_to(run / 'savedata')): hashlib.sha256(p.read_bytes()).hexdigest() for p in (run / 'savedata').rglob('*') if p.is_file()}


def dump(name, obj):
    (QA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), 'utf-8')
