# 시험 게임 한 프로세스의 소리 세션만 끈다(윈도 볼륨 믹서의 그 앱 음소거와 같음; 다른 앱·시스템 음량은 안 건드림).
# 영상(DirectShow) 소리는 엔진 음량 0 을 안 따를 수 있어서, 숨은 시험 동안 15ms 마다 그 PID 의 세션을 찾아 음소거·음량 0 으로 둔다.
# 세션별 최고 음량(음소거 전 신호)도 기록해 영상 소리가 실제로 나왔는지 본다.
# 사용: m = Muter(pid); m.start(); ... m.stop(); m.report()   /   python -I mute_audio.py --list  (지금 세션 목록만 읽음)
import ctypes as c, threading, time, uuid, sys
from ctypes import wintypes as w

ole = c.OleDLL('ole32')


class GUID(c.Structure):
    _fields_ = [('a', c.c_uint32), ('b', c.c_uint16), ('c', c.c_uint16), ('d', c.c_ubyte * 8)]


def guid(s):
    u = uuid.UUID(s); g = GUID(); g.a, g.b, g.c = u.fields[0], u.fields[1], u.fields[2]
    for i, v in enumerate(u.bytes[8:]): g.d[i] = v
    return g


CLSID_Enum = guid('BCDE0395-E52F-467C-8E3D-C4579291692E'); IID_Enum = guid('A95664D2-9614-4F35-A746-DE8DB63617E6')
IID_Mgr2 = guid('77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F'); IID_Ctl2 = guid('bfb7ff88-7239-4fc9-8fa2-07c950be9c6d')
IID_Vol = guid('87CE5498-68D6-44E5-9215-6DA47EF883D8'); IID_Meter = guid('C02216F6-8C67-4B5B-9D00-D008E73E0064')


def call(obj, idx, types, *args):
    vt = c.cast(obj, c.POINTER(c.POINTER(c.c_void_p)))[0]
    return c.WINFUNCTYPE(c.HRESULT, c.c_void_p, *types)(vt[idx])(obj, *args)


def release(obj):
    if obj:
        vt = c.cast(obj, c.POINTER(c.POINTER(c.c_void_p)))[0]
        c.WINFUNCTYPE(c.c_ulong, c.c_void_p)(vt[2])(obj)


def qi(obj, iid):
    p = c.c_void_p(); call(obj, 0, [c.POINTER(GUID), c.POINTER(c.c_void_p)], c.byref(iid), c.byref(p)); return p


def sessions():
    """(pid, ISimpleAudioVolume, IAudioMeterInformation) for every session on every active render endpoint; caller releases"""
    out = []; en = c.c_void_p(); coll = c.c_void_p()
    ole.CoCreateInstance(c.byref(CLSID_Enum), None, 0x17, c.byref(IID_Enum), c.byref(en))
    try:
        call(en, 3, [c.c_int, w.DWORD, c.POINTER(c.c_void_p)], 0, 1, c.byref(coll))
        n = c.c_uint(); call(coll, 3, [c.POINTER(c.c_uint)], c.byref(n))
        for i in range(n.value):
            dev = c.c_void_p(); mgr = c.c_void_p(); se = c.c_void_p()
            try:
                call(coll, 4, [c.c_uint, c.POINTER(c.c_void_p)], i, c.byref(dev))
                call(dev, 3, [c.POINTER(GUID), w.DWORD, c.c_void_p, c.POINTER(c.c_void_p)], c.byref(IID_Mgr2), 0x17, None, c.byref(mgr))
                call(mgr, 5, [c.POINTER(c.c_void_p)], c.byref(se))
                k = c.c_int(); call(se, 3, [c.POINTER(c.c_int)], c.byref(k))
                for j in range(k.value):
                    ctl = c.c_void_p(); call(se, 4, [c.c_int, c.POINTER(c.c_void_p)], j, c.byref(ctl))
                    try:
                        c2 = qi(ctl, IID_Ctl2); pid = w.DWORD()
                        try: call(c2, 14, [c.POINTER(w.DWORD)], c.byref(pid))
                        except OSError: pid.value = 0
                        release(c2)
                        out.append((pid.value, qi(ctl, IID_Vol), qi(ctl, IID_Meter)))
                    finally: release(ctl)
            finally:
                for o in (se, mgr, dev): release(o)
    finally:
        release(coll); release(en)
    return out


class Muter(threading.Thread):
    def __init__(self, pid, period=.015):
        super().__init__(daemon=True); self.pid, self.period = pid, period
        self.alive = True; self.muted = 0; self.first = None; self.peak = 0.0; self.loud = []; self.errors = []
        self.t0 = time.time()

    def run(self):
        ole.CoInitializeEx(None, 0)
        while self.alive:
            try:
                for pid, vol, met in sessions():
                    try:
                        if pid == self.pid:
                            m = w.BOOL(); call(vol, 6, [c.POINTER(w.BOOL)], c.byref(m))
                            if not m.value:
                                call(vol, 5, [w.BOOL, c.c_void_p], 1, None); call(vol, 3, [c.c_float, c.c_void_p], 0.0, None)
                                self.muted += 1; self.first = self.first or round(time.time() - self.t0, 3)
                            pk = c.c_float(); call(met, 3, [c.POINTER(c.c_float)], c.byref(pk))
                            if pk.value > 0.001: self.loud.append(round(time.time() - self.t0, 2))
                            self.peak = max(self.peak, pk.value)
                    finally:
                        release(vol); release(met)
            except OSError as e:
                if len(self.errors) < 5: self.errors.append(repr(e)[:120])
            time.sleep(self.period)

    def stop(self):
        self.alive = False; self.join(2)

    def loud_spans(self, gap=1.0):
        """[(start, end)] of seconds where the session meter showed signal (before the mute)"""
        spans = []
        for t in self.loud:
            if spans and t - spans[-1][1] <= gap: spans[-1][1] = t
            else: spans.append([t, t])
        return [(a, b) for a, b in spans]

    def report(self):
        return {'mute_actions': self.muted, 'first_mute_s': self.first, 'peak': round(self.peak, 4), 'loud_spans': self.loud_spans()[:20], 'errors': self.errors}


if __name__ == '__main__' and '--list' in sys.argv:
    ole.CoInitializeEx(None, 0)
    for pid, vol, met in sessions():
        m = w.BOOL(); call(vol, 6, [c.POINTER(w.BOOL)], c.byref(m)); pk = c.c_float(); call(met, 3, [c.POINTER(c.c_float)], c.byref(pk))
        print(pid, 'muted' if m.value else '-', round(pk.value, 4)); release(vol); release(met)
