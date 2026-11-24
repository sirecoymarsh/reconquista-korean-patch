# 게임이 그리기를 멈췄을 때 「바쁘게 도는지(CPU) / 무언가를 기다리며 서 있는지」와 각 스레드가 어느 모듈 어디에 있는지 읽는다(읽기만).
# 32비트 게임을 64비트 파이썬에서 본다: Wow64GetThreadContext 로 Eip, EnumProcessModulesEx(32비트 목록)로 모듈 기준 주소.
# 사용: from hang_probe import probe; probe(pid, hwnd)  ->  dict
import ctypes as c, time
from ctypes import wintypes as w
import psutil

k32 = c.WinDLL('kernel32', use_last_error=True); psapi = c.WinDLL('psapi', use_last_error=True); u32 = c.WinDLL('user32')


class WOW64_CONTEXT(c.Structure):
    _fields_ = [('ContextFlags', w.DWORD), ('Dr', w.DWORD * 6), ('FloatSave', c.c_byte * 112),
                ('SegGs', w.DWORD), ('SegFs', w.DWORD), ('SegEs', w.DWORD), ('SegDs', w.DWORD),
                ('Edi', w.DWORD), ('Esi', w.DWORD), ('Ebx', w.DWORD), ('Edx', w.DWORD), ('Ecx', w.DWORD), ('Eax', w.DWORD),
                ('Ebp', w.DWORD), ('Eip', w.DWORD), ('SegCs', w.DWORD), ('EFlags', w.DWORD), ('Esp', w.DWORD), ('SegSs', w.DWORD),
                ('ExtendedRegisters', c.c_byte * 512)]


class MODINFO(c.Structure):
    _fields_ = [('base', c.c_void_p), ('size', w.DWORD), ('entry', c.c_void_p)]


k32.OpenProcess.restype = w.HANDLE; k32.OpenThread.restype = w.HANDLE


def modules(pid):
    h = k32.OpenProcess(0x0410, False, pid); out = []
    try:
        arr = (c.c_void_p * 1024)(); need = w.DWORD()
        if not psapi.EnumProcessModulesEx(h, arr, c.sizeof(arr), c.byref(need), 0x01): return out
        for i in range(need.value // c.sizeof(c.c_void_p)):
            mi = MODINFO(); name = c.create_unicode_buffer(260)
            psapi.GetModuleInformation(h, c.c_void_p(arr[i]), c.byref(mi), c.sizeof(mi))
            psapi.GetModuleBaseNameW(h, c.c_void_p(arr[i]), name, 260)
            out.append((mi.base or 0, mi.size, name.value))
    finally:
        k32.CloseHandle(h)
    return out


def where(mods, eip):
    for b, s, n in mods:
        if b <= eip < b + s: return f'{n}+0x{eip - b:x}'
    return f'0x{eip:08x}'


def eip_of(tid):
    h = k32.OpenThread(0x0002 | 0x0008 | 0x0040, False, tid)  # SUSPEND_RESUME | GET_CONTEXT | QUERY_INFORMATION
    if not h: return None
    try:
        if k32.Wow64SuspendThread(h) == 0xFFFFFFFF: return None
        try:
            ctx = WOW64_CONTEXT(); ctx.ContextFlags = 0x10001  # WOW64_CONTEXT_CONTROL
            return ctx.Eip if k32.Wow64GetThreadContext(h, c.byref(ctx)) else None
        finally:
            k32.ResumeThread(h)
    finally:
        k32.CloseHandle(h)


class WOW64_CONTEXT_FULL(WOW64_CONTEXT):
    pass


def read(pid, addr, n):
    h = k32.OpenProcess(0x0010, False, pid); buf = c.create_string_buffer(n); got = c.c_size_t()
    try:
        ok = k32.ReadProcessMemory(h, c.c_void_p(addr), buf, n, c.byref(got))
        return buf.raw[:got.value] if ok else b''
    finally:
        k32.CloseHandle(h)


def rd32(pid, addr):
    d = read(pid, addr, 4); return int.from_bytes(d, 'little') if len(d) == 4 else None


# 엔진 전역(레콘키스타.exe 0x400000 기준, 11-22 정적 분석): 시각·대기 깃발·양보 깃발·빨리 감기 깃발·현재 VM 스레드·VM 문맥
GLOBALS = {'now_494678': 0x494678, 'waitflag_494674': 0x494674, 'yield_494888': 0x494888, 'fast_494894': 0x494894,
           'f_494898': 0x494898, 'f_4948a0': 0x4948a0, 'f_4948ac': 0x4948ac}


def deep(pid, samples=20, gap=.1):
    """가장 바쁜 스레드의 스택에서 exe·DLL 안 반환 주소 후보를 모으고, 엔진 전역·VM 스레드 상태를 표본마다 읽는다"""
    p = psutil.Process(pid); mods = modules(pid)
    rng = [(b, b + s, n) for b, s, n in mods if n.lower().endswith(('.exe', 'reconquistahd.dll'))]
    t0 = {t.id: t.user_time + t.system_time for t in p.threads()}; time.sleep(1)
    t1 = {t.id: t.user_time + t.system_time for t in p.threads()}; tid = max(t1, key=lambda x: t1[x] - t0.get(x, 0))
    hist = {}; rows = []
    for _ in range(samples):
        h = k32.OpenThread(0x0002 | 0x0008 | 0x0040, False, tid); esp = eip = None
        if h:
            try:
                if k32.Wow64SuspendThread(h) != 0xFFFFFFFF:
                    try:
                        ctx = WOW64_CONTEXT(); ctx.ContextFlags = 0x10007
                        if k32.Wow64GetThreadContext(h, c.byref(ctx)): esp, eip = ctx.Esp, ctx.Eip
                        stack = read(pid, esp, 0x2000) if esp else b''
                        g = {k: rd32(pid, a) for k, a in GLOBALS.items()}
                        th = rd32(pid, 0x56e1a4); cx = rd32(pid, 0x56e1a8)
                        if th: g.update(th_ip=rd32(pid, th), th_8=rd32(pid, th + 8), th_44=rd32(pid, th + 0x44))
                        if cx: g.update(cx_4=rd32(pid, cx + 4), cx_4c34=rd32(pid, cx + 0x4c34))
                    finally:
                        k32.ResumeThread(h)
            finally:
                k32.CloseHandle(h)
        seen = []
        for k in range(0, len(stack) - 3, 4):
            v = int.from_bytes(stack[k:k + 4], 'little')
            for a, z, n in rng:
                if a + 0x1000 <= v < z: seen.append(f'{n}+0x{v - a:x}')
        for s_ in dict.fromkeys(seen[:40]): hist[s_] = hist.get(s_, 0) + 1
        rows.append({'eip': where(mods, eip) if eip else None, **g})
        time.sleep(gap)
    return {'tid': tid, 'samples': rows, 'stack_ret_candidates': sorted(hist.items(), key=lambda kv: -kv[1])[:40]}


def probe(pid, hwnd=None, secs=5.0, samples=6):
    p = psutil.Process(pid); mods = modules(pid)
    t0 = {t.id: t.user_time + t.system_time for t in p.threads()}; time.sleep(secs)
    t1 = {t.id: t.user_time + t.system_time for t in p.threads()}
    busy = {tid: round((t1[tid] - t0.get(tid, 0)) / secs, 3) for tid in t1}
    eips = {tid: [] for tid in t1}
    for _ in range(samples):
        for tid in t1:
            e = eip_of(tid)
            if e is not None: eips[tid].append(where(mods, e))
        time.sleep(.15)
    th = sorted(t1, key=lambda x: -busy[x])
    return {'cpu_total': round(sum(busy.values()), 3), 'hung_window': bool(u32.IsHungAppWindow(w.HWND(hwnd))) if hwnd else None,
            'threads': [{'tid': tid, 'cpu': busy[tid], 'eip': sorted(set(eips[tid]))[:4]} for tid in th[:8]]}
