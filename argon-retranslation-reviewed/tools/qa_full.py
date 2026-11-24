# 숨은 시험 5회차(11-22, 사용자 「좋아 체크해봐」): 지난 검수에서 확인 못 한 것을 아르곤 반입 빌드 시험 사본에서 돌린다.
#  save   : 지도 이동 없이(= 진짜 savedata\) 메뉴 저장·불러오기, 빠른 저장·빠른 불러오기
#  movie  : 게임 안 오프닝 영상(도입부 3 마지막 줄 뒤) — 소리는 그 프로세스 세션만 음소거, 영상 창·길이·뒤 이어짐
#  routes : 갈래 끝 102곳(work\route_targets.json)으로 지도 이동 → 도착 → 클릭으로 그 뒤를 넘김(엔딩 6곳은 타이틀까지)
# 숨은 데스크톱·사용자 입력 없음(PostMessage)·끝에 정상 종료. 같은 게임은 단일 실행이라 다른 세션 시험과는 HOLD 파일로 차례.
# python -I tools\qa_full.py save|movie|routes [first] [count]
import sys, time, json, os, re, subprocess, codecs, threading
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools'); sys.path.insert(0, str(HERE)); sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
RVD = HERE.parent; RUN = RVD / 'runtime-argon-qa-20261121'; OUT = RVD / 'qa-20261122'
# 배포판(10-28 최신판) 사본을 시험할 땐 QA_RUN·QA_OUT·QA_STORYMAP 으로 바꾼다(찾기 문구는 그 판 지도에서 뽑아야 맞음)
RUN = Path(os.environ['QA_RUN']) if os.environ.get('QA_RUN') else RUN; OUT = Path(os.environ['QA_OUT']) if os.environ.get('QA_OUT') else OUT; OUT.mkdir(exist_ok=True)
STORYMAP = Path(os.environ['QA_STORYMAP']) if os.environ.get('QA_STORYMAP') else RVD / 'build-20261121' / 'storymap.bin'
HOLD = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024\qa\release-audit-20261121\HOLD')
mode = sys.argv[1]; NUM = [int(a) for a in sys.argv[2:] if a.isdigit()]
FIRST = NUM[0] if NUM else 0; COUNT = NUM[1] if len(NUM) > 1 else 999
CWAIT = float(next((a[6:] for a in sys.argv if a.startswith('cwait=')), '1.4'))   # 도착 뒤 클릭 간격(초)
COVER_XY = tuple(int(v) for v in next((a[8:] for a in sys.argv if a.startswith('coverxy=')), '400,300').split(','))   # 가림막 시한 뒤 클릭할 자리(보기 하나 선택지는 위쪽 400,155)
PS = ['powershell', '-NoProfile', '-Command']


def ps(cmd):
    return subprocess.run(PS + [cmd], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()


def nv():
    v = ps("@(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='nvlddmkm'} -ErrorAction SilentlyContinue).Count")
    return int(v) if v.isdigit() else -1


def games():
    v = ps("@(Get-Process | Where-Object { $_.Path -like '*\\レコンキスタ.exe' }).Count")
    return int(v) if v.isdigit() else -1


if games():
    print('레콘키스타가 켜져 있어 시험하지 않음'); sys.exit(2)
import psutil
import qa
from test_hitch import WM_APP
from mute_audio import Muter
from PIL import Image

VK = dict(F11=0x7a, RET=0x0d, ESC=0x1b, DOWN=0x28, RIGHT=0x27, HOME=0x24)
res = {'mode': mode, 'started': time.strftime('%Y-%m-%d %H:%M:%S'), 'nv_before': nv(), 'runs': []}


class Tail:
    """hires-runtime.log 를 이어 읽는다(앞부분은 버림, 위치는 파일 기준 절대값)"""
    def __init__(s, p):
        s.p, s.pos, s.base, s.buf = p, 0, 0, ''; s.dec = codecs.getincrementaldecoder('utf-8')('replace')

    def pull(s):
        try:
            with open(s.p, 'rb') as f:
                f.seek(s.pos); d = f.read()
        except OSError:
            return
        s.pos += len(d); s.buf += s.dec.decode(d)
        if len(s.buf) > 8_000_000: cut = len(s.buf) - 4_000_000; s.base += cut; s.buf = s.buf[cut:]

    def mark(s):
        s.pull(); return s.base + len(s.buf)

    def find(s, needle, start):
        s.pull(); i = s.buf.find(needle, max(0, start - s.base)); return None if i < 0 else s.base + i

    def line_at(s, at):
        i = at - s.base; j = s.buf.find('\n', i); return s.buf[i:j if j >= 0 else None]

    def lines(s, start, prefix):
        s.pull(); return [l for l in s.buf[max(0, start - s.base):].splitlines() if l.startswith(prefix)]


class Run:
    def __init__(self, label, perf=True):
        log = RUN / 'hires-runtime.log'
        if log.exists(): log.unlink()                 # 앞 판 기록은 qa-20261121\game.log 등에 따로 있음
        for p in (RUN / 'qa').glob('*.bmp'): p.unlink()
        self.reviews0 = set(p.name for p in RUN.glob('savedata-review-*'))
        self.g = qa.Game(run=RUN, extra_env={'RECON_PERF': '2' if perf else None, 'RECON_FLOW_PROBE': None})
        self.t = Tail(log); self.m = Muter(self.g.pid); self.m.start(); self.n = 0
        self.r = {'label': label, 'pid': self.g.pid, 'steps': [], 'dialogs': []}; res['runs'].append(self.r)
        self.wait('asset ', 0, 90, 'start')
        self.until(lambda: any(self.t.find(f'asset {k} ', 0) is not None for k in ('1de0628c', 'ef1f6a40', 'c1e942c6')), 90, 'title')
        g = self.g; g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS'); time.sleep(2)
        if not qa.u.IsWindowVisible(g.hwnd): qa.u.ShowWindow(g.hwnd, 4)
        for m, a in [(0x1c, 1), (6, 1), (7, 0)]: qa.u.SendMessageW(g.hwnd, m, a, 0)
        time.sleep(1)

    def step(self, name, **k):
        self.r['steps'].append({'step': name, 't': round(time.time() - self.g.started, 1), **k}); print(name, json.dumps(k, ensure_ascii=False)[:300], flush=True)

    def alive(self):
        if self.g.poll() is not None: raise RuntimeError(f'process exited {self.g.poll():#x}')

    def until(self, pred, seconds, what):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if pred(): return
            self.alive(); self.dialogs(); time.sleep(.1)
        raise TimeoutError(what)

    def wait(self, needle, start, seconds, what):
        hit = [None]
        self.until(lambda: (hit.__setitem__(0, self.t.find(needle, start)) or hit[0] is not None), seconds, what)
        return hit[0]

    def dialogs(self):
        """오류 창 등 대화 상자: 글을 적고 닫는다"""
        out = []
        for x in self.g.windows():
            if x['class'] != '#32770': continue
            texts = []
            cb = qa.CB(lambda h, l: (texts.append(self.text(h)) or True))
            qa.u.EnumChildWindows(x['h'], cb, 0)
            d = {'title': x['title'], 'text': [s for s in texts if s][:6], 't': round(time.time() - self.g.started, 1)}
            out.append(d); self.r['dialogs'].append(d); print('DIALOG', json.dumps(d, ensure_ascii=False), flush=True)
            qa.u.PostMessageW(x['h'], 0x111, 6, 0); qa.u.PostMessageW(x['h'], 0x111, 1, 0)     # 예/아니요 창이면 「예」, 확인 창이면 「확인」
            time.sleep(.5)
        return out

    @staticmethod
    def text(h):
        b = qa.c.create_unicode_buffer(512); qa.u.GetWindowTextW(h, b, 512); return b.value

    def cap(self, name, hd=False):
        self.n += 1; n = self.n; shots = RUN / 'qa'
        for p in shots.glob(f'quality-{n:02d}-*.bmp'): p.unlink()
        self.g.post(self.g.hwnd, WM_APP + 80, 10 + n, 0)
        self.until(lambda: (shots / f'quality-{n:02d}-output.bmp').exists(), 30, 'capture ' + name); time.sleep(.4)
        out = OUT / f'{self.r["label"]}-{n:03d}-{name}.png'
        Image.open(shots / f'quality-{n:02d}-base.bmp').convert('RGB').save(out)
        if hd: Image.open(shots / f'quality-{n:02d}-hd.bmp').convert('RGB').save(out.with_name(out.stem + '-hd.png'))
        for p in shots.glob(f'quality-{n:02d}-*.bmp'): p.unlink()
        return out

    def click(self, x=400, y=300, wait=1.6):
        self.g.move(self.g.hwnd, x, y); time.sleep(.2); self.g.logical_click(self.g.hwnd, x, y); time.sleep(wait)

    def open_map(self):
        for attempt in range(5):
            k = self.t.mark(); self.g.key(self.g.hwnd, VK['F11'])
            try:
                self.wait('inflow opened', k, 20, 'map open'); time.sleep(1); return self.g.child()
            except TimeoutError:
                self.step('map not opened, click and retry', attempt=attempt); self.click(wait=3)
        raise TimeoutError('map open x5')

    def goto(self, order, phrase, arrive_s=900):
        """지도 찾기 → 순번이 맞는 항목 → 「여기서부터 본편으로」 → 도착"""
        g = self.g; child = self.open_map()
        k = self.t.mark(); g.logical_click(child, 576, 20); self.wait('search_all', k, 5, 'search all'); time.sleep(.5)
        ed = g.edit()
        for _ in range(60): g.post(ed, 0x102, 8)
        time.sleep(.6)
        k = self.t.mark(); g.chars(ed, phrase); at = self.wait(f'search len={len(phrase)} ', k, 10, 'search'); time.sleep(.6)
        line = self.t.line_at(at); items = int(re.search(r'items=(\d+)', line).group(1)); scenes = int(re.search(r'scenes=(\d+)', line).group(1))
        # 11-22 고침: 찾기 결과는 장면(왼쪽 목록)별로 나뉘고 처음엔 첫 장면의 첫 항목이 이미 골라져 있다 →
        # 장면마다 HOME(첫 항목, 기록이 남음)부터 보고 ↓, 없으면 → 로 다음 장면(첫 판은 ↓ 부터 눌러 첫 항목·둘째 장면을 놓쳤다)
        got = None; seen = []
        for sc in range(max(1, min(scenes, 8))):
            if sc:
                k = self.t.mark(); g.key(child, VK['RIGHT'], 1, 0); at = self.wait('inflow scene=', k, 5, 'scene')
                items = int(re.search(r'items=(\d+)', self.t.line_at(at)).group(1)); time.sleep(.3)
            k = self.t.mark(); g.key(child, VK['HOME'], 1, 0); at = self.wait('inflow item=', k, 5, 'item')
            got = int(re.search(r'order=(\d+)', self.t.line_at(at)).group(1)); seen.append(got)
            for _ in range(min(items, 12)):
                if got == order: break
                k = self.t.mark(); g.key(child, VK['DOWN'], 1, 0); at = self.wait('inflow item=', k, 5, 'item')
                got = int(re.search(r'order=(\d+)', self.t.line_at(at)).group(1)); seen.append(got); time.sleep(.3)
            if got == order: break
        if got != order:
            g.key(child, VK['ESC']); time.sleep(1); raise LookupError(f'search scenes={scenes} seen={seen[-8:]}')
        k = self.t.mark(); g.story_jump(child); at = self.wait('inflow jump order=', k, 10, 'jump')
        # 가림막 120초 시한(cover_timeout)이 지나면 화면을 찍고, 사용자가 하듯 15초마다 한 번씩(최대 10번) 클릭해 이어지는지 본다
        t0 = time.time(); self.cover = None; self.cover_clicks = 0; last = 0; end = time.monotonic() + arrive_s
        while self.t.find(f'inflow arrived order={order} ', k) is None:
            if self.cover is None and self.t.find('inflow cover_timeout', k) is not None:
                self.cover = round(time.time() - t0, 1); time.sleep(2); self.cap('cover-timeout', hd=True)
            if self.cover is not None and self.cover_clicks < 10 and time.time() - last > 15:
                self.click(*COVER_XY, wait=1); self.cover_clicks += 1; last = time.time()
                if self.cover_clicks == 1: time.sleep(3); self.cap('cover-click1', hd=True)
            if time.monotonic() > end: raise TimeoutError(f'arrive (cover_timeout@{self.cover} clicks={self.cover_clicks})')
            self.alive(); self.dialogs(); time.sleep(.2)
        return round(time.time() - t0, 1), items

    def mem(self):
        try: return round(psutil.Process(self.g.pid).memory_info().private / 2**20)
        except Exception: return None

    def close(self):
        rv = sorted(set(p.name for p in RUN.glob('savedata-review-*')) - self.reviews0)
        self.r['new_review_folders'] = rv; self.r['mem_mb_end'] = self.mem()
        self.r['normal_exit'] = self.g.close_normally(); self.m.stop(); self.r['audio'] = self.m.report()
        log = RUN / 'hires-runtime.log'
        if log.exists():
            d = log.read_bytes(); self.r['log_mb'] = round(len(d) / 2**20, 1)
            (OUT / f'{self.r["label"]}-game-tail.log').write_bytes(d[-400_000:])
            self.r['log_errors'] = [l for l in d.decode('utf-8', 'replace').splitlines() if re.search(r'error|fail|exception|crash', l, re.I)][:20]


def savehash():
    import hashlib
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in (RUN / 'savedata').iterdir() if p.is_file() and p.suffix == '.sav'}


def unique_phrase(order):
    from read_storymap import parse
    x = parse(STORYMAP); texts = [n['text'] for n in x['nodes']]
    t = next(n['text'] for n in x['nodes'] if n['order'] == order)
    for L in (10, 12, 14, 8, 16):
        for s in range(0, max(1, len(t) - L + 1)):
            p = t[s:s + L]
            if len(p) == L and p[0] != ' ' and p[-1] != ' ' and not any(q in '「」『』〔〕《》（）…―　' for q in p) and sum(1 for u in texts if p in u) == 1: return p


def printwindow(h, path, flags=2):
    """그 창을 PrintWindow 로(숨은 데스크톱이라 화면째 찍기는 못 씀). 2 = PW_RENDERFULLCONTENT"""
    import ctypes as C
    from ctypes import wintypes as W
    u, g = C.WinDLL('user32'), C.WinDLL('gdi32')
    for f, a, r in [(u.GetDC, [W.HWND], C.c_void_p), (g.CreateCompatibleDC, [C.c_void_p], C.c_void_p), (g.CreateCompatibleBitmap, [C.c_void_p, C.c_int, C.c_int], C.c_void_p),
                    (g.SelectObject, [C.c_void_p, C.c_void_p], C.c_void_p), (u.PrintWindow, [W.HWND, C.c_void_p, W.UINT], W.BOOL),
                    (g.GetDIBits, [C.c_void_p, C.c_void_p, W.UINT, W.UINT, C.c_void_p, C.c_void_p, W.UINT], C.c_int),
                    (g.DeleteObject, [C.c_void_p], W.BOOL), (g.DeleteDC, [C.c_void_p], W.BOOL), (u.ReleaseDC, [W.HWND, C.c_void_p], C.c_int)]:
        f.argtypes, f.restype = a, r
    rc = W.RECT(); u.GetWindowRect(h, C.byref(rc)); wd, ht = rc.right - rc.left, rc.bottom - rc.top
    sdc = u.GetDC(None); mdc = g.CreateCompatibleDC(sdc); bmp = g.CreateCompatibleBitmap(sdc, wd, ht); old = g.SelectObject(mdc, bmp)
    ok = u.PrintWindow(h, mdc, flags)
    bi = (C.c_uint32 * 10)(40, wd, (-ht) & 0xffffffff, 1 | (32 << 16), 0, 0, 0, 0, 0, 0); buf = C.create_string_buffer(wd * ht * 4)
    n = g.GetDIBits(mdc, bmp, 0, ht, buf, bi, 0)
    g.SelectObject(mdc, old); g.DeleteObject(bmp); g.DeleteDC(mdc); u.ReleaseDC(None, sdc)
    im = Image.frombuffer('RGBA', (wd, ht), buf, 'raw', 'BGRA', 0, 1).convert('RGB'); im.save(path)
    return {'ok': bool(ok), 'rows': n, 'size': [wd, ht], 'nonblack': round(sum(1 for p in im.resize((64, 36)).getdata() if max(p) > 16) / (64 * 36), 3)}


def box(a): return a[455:560, 20:600]


def diff(a, b):
    import numpy as np
    A = np.asarray(Image.open(a).convert('RGB')).astype(int); B = np.asarray(Image.open(b).convert('RGB')).astype(int)
    return int((np.abs(box(A) - box(B)).max(axis=2) > 24).sum())


HOLD.write_text(f'argon qa_full {mode} {time.strftime("%H:%M:%S")}', 'utf-8')
try:
    if mode == 'save':
        before = savehash(); R = Run('save')
        R.cap('title'); R.click(638, 388, 3); R.cap('loadscreen'); R.click(200, 150, 2); R.click(310, 300, 6); R.cap('loaded')
        R.click(wait=3.5); A = R.cap('A-before-save')                     # 글이 다 찍힌 뒤
        menu = lambda: (R.g.logical_click(R.g.hwnd, 400, 300, button='right'), time.sleep(1.5), R.g.logical_click(R.g.hwnd, 400, 300, button='right'), time.sleep(2))
        menu(); R.click(634, 56, 2.5); R.cap('save-screen'); R.click(440, 150, 2.5); R.cap('saved-slot2'); R.step('save slot2', dialogs=R.dialogs())
        mid = savehash()
        if mid == before:                                                   # 이미 있는 칸: 「덮어써서 저장할까요?」 → 예
            R.click(310, 300, 6); R.cap('overwrite-yes'); mid = savehash(); R.step('overwrite confirmed')
        R.step('main savedata after save', changed=sorted(k for k in set(before) | set(mid) if before.get(k) != mid.get(k)))
        for i in range(3):                                                  # 「저장했습니다」가 사라진 뒤 「이전 화면으로」
            R.click(670, 30, 4); back = R.cap(f'back-in-game{i + 1}')
            if diff(A, back) < 2000: break
        R.step('back after save', same_as_A=diff(A, back), tries=i + 1)
        for _ in range(3): R.click(wait=3)
        B = R.cap('B-read-on'); R.step('read on', diff_from_A=diff(A, B))
        menu(); R.click(634, 118, 2.5); R.cap('load-screen'); R.click(440, 150, 2.5); R.dialogs(); time.sleep(3); C = R.cap('C-after-load')
        if diff(A, C) > 2000: R.click(310, 300, 4); C = R.cap('C2-after-yes')
        R.step('after load slot2', diff_from_A=diff(A, C), diff_from_B=diff(B, C))
        # 글이 찍히는 동안의 클릭은 단추가 아니라 「글 다 보이기」로 먹힌다(엔진 본래 동작) → 다 찍힌 뒤 누른다
        R.click(wait=3.5); Q0 = R.cap('Q0'); h0 = savehash(); R.click(325, 574, 3); QS = R.cap('quicksave'); R.step('quick save', dialogs=R.dialogs())
        h1 = savehash(); R.step('quick save file', changed=sorted(k for k in set(h0) | set(h1) if h0.get(k) != h1.get(k)))
        for _ in range(3): R.click(wait=3)
        Q1 = R.cap('Q1-read-on'); R.click(375, 574, 2.5); R.dialogs(); time.sleep(2); Q2 = R.cap('Q2-after-quickload')
        if diff(Q0, Q2) > 2000: R.click(310, 300, 4); Q2 = R.cap('Q2b-after-yes')
        R.step('after quick load', diff_from_Q0=diff(Q0, Q2), diff_from_Q1=diff(Q1, Q2))
        R.r['redirected_writes'] = len(R.t.lines(0, 'inflow savedata_write'))
        R.close(); after = savehash(); R.r['main_savedata_changed'] = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))

    elif mode == 'endsave':
        # 지도 없이도 멈추나: 1판은 지도로 order(기본 37758)에 가서 빠른 저장 → 파일을 꺼낸다.
        # 2판은 새 프로세스에서 지도를 한 번도 안 열고 타이틀 → 1번 칸 불러오기 → 빠른 불러오기(꺼낸 파일) → 클릭으로 타이틀까지(30초 시간축·멈춤이면 hang_probe).
        # 시험 사본의 savedata\majiro_9999.sav 는 끝에 원래대로 돌린다.
        import shutil
        ES = RVD / 'work' / 'endsave'; ES.mkdir(parents=True, exist_ok=True)
        order = int(next((a[6:] for a in sys.argv if a.startswith('order=')), '37758'))
        LIMIT = int(next((a[6:] for a in sys.argv if a.startswith('limit=')), '600'))
        t0s = time.time(); R = Run('endsave-a')
        secs, _ = R.goto(order, unique_phrase(order)); R.step('arrived', order=order, arrive_s=secs)
        # 이 자리 글상자는 단추 줄이 없는 꼴이라(빠른 저장 단추 없음) 오른쪽 클릭 메뉴 → 저장 → 2번 칸(덮어쓰기면 「예」). 지도 이동 뒤라 검수용 폴더에 써진다.
        menu = lambda: (R.g.logical_click(R.g.hwnd, 400, 300, button='right'), time.sleep(1.5), R.g.logical_click(R.g.hwnd, 400, 300, button='right'), time.sleep(2))
        time.sleep(5); R.cap('a-before-save'); menu(); R.click(634, 56, 2.5); R.cap('a-save-screen'); R.click(440, 150, 2.5)
        fresh = lambda: [p for p in list(RUN.glob('savedata-review-*/majiro_0102.sav')) + [RUN / 'savedata' / 'majiro_0102.sav'] if p.exists() and p.stat().st_mtime > t0s]
        if not fresh(): R.click(310, 300, 6); R.cap('a-overwrite-yes')
        R.step('save slot2', dialogs=R.dialogs()); R.close()
        cands = fresh(); R.r['save_files'] = [str(p.relative_to(RUN)) for p in cands]
        if not cands: raise RuntimeError('slot2 save file not found')
        shutil.copy2(max(cands, key=lambda p: p.stat().st_mtime), ES / 'majiro_0102.sav')
        main = RUN / 'savedata' / 'majiro_0102.sav'; bak = ES / 'main_majiro_0102.sav.bak'; had = main.exists()
        if had and not bak.exists(): shutil.copy2(main, bak)
        shutil.copy2(ES / 'majiro_0102.sav', main)
        try:
            time.sleep(20); R = Run('endsave-b')
            R.cap('b-title'); R.click(638, 388, 3); R.cap('b-loadscreen'); kq = R.t.mark(); R.click(440, 150, 2.5)
            R.cap('b-load-confirm'); R.click(310, 300, 6)                       # 「데이터를 불러올까요?」 → 예 (확인 창이 뜰 때 검정 그림이 먼저 불려 그림 불림으로는 못 가름)
            time.sleep(3); R.cap('b-loaded-slot2')
            rec = {'loaded_images': [l.split()[2] for l in R.t.lines(kq, 'load call ')][:8]}
            k = R.t.mark(); clicks = 0; tl = []; t0 = time.time(); tnext = t0 + 30; kp = k
            while True:
                R.click(wait=CWAIT); clicks += 1
                if R.t.find('load call title1_', k) is not None: rec['title_after_clicks'] = clicks; break
                if time.time() - t0 > LIMIT: rec['title_timeout'] = True; break
                if time.time() > tnext:
                    tnext += 30; ls = R.t.lines(k, 'load call ')
                    tl.append([round(time.time() - t0), clicks, len(R.t.lines(kp, 'present attempt')), ls[-1].split()[2] if ls else None]); kp = R.t.mark(); rec['timeline'] = tl
                    if len(tl) >= 2 and tl[-1][2] == 0 and tl[-2][2] == 0:
                        from hang_probe import probe
                        R.cap('b-hang', hd=True); rec['hang'] = probe(R.g.pid, R.g.hwnd)
                        k2 = R.t.mark(); R.g.key(R.g.hwnd, VK['RET']); time.sleep(5); rec['hang']['enter_presents'] = len(R.t.lines(k2, 'present attempt'))
                        k2 = R.t.mark(); R.g.logical_click(R.g.hwnd, 400, 300, button='right'); time.sleep(5)
                        rec['hang']['rclick_presents'] = len(R.t.lines(k2, 'present attempt')); rec['hang']['at_s'] = round(time.time() - t0); break
            rec['clicks'] = clicks; rec['presents'] = len(R.t.lines(k, 'present attempt'))
            rec['map_used_in_session_b'] = len(R.t.lines(0, 'inflow opened')) + len(R.t.lines(0, 'inflow jump'))
            R.r['play'] = rec; R.step('b play', **{a_: b_ for a_, b_ in rec.items() if a_ != 'timeline'}); time.sleep(1.5); R.cap('b-after', hd=True)
            R.close()
        finally:
            if had: shutil.copy2(bak, main)
            else: main.unlink(missing_ok=True)
            res['main_slot2_restored'] = (not had and not main.exists()) or (had and main.read_bytes() == bak.read_bytes())

    elif mode == 'movie':
        R = Run('movie'); stop_gpu = threading.Event(); gpu = {'base': res['nv_before'], 'hits': []}

        def gpu_watch():
            while not stop_gpu.wait(4):
                v = nv()
                if v > gpu['base'] >= 0:
                    gpu['hits'].append(v); print('GPU EVENT', v, flush=True); qa.k.TerminateProcess(R.g.handle, 9); return
        threading.Thread(target=gpu_watch, daemon=True).start()
        phrase = unique_phrase(5414); secs, items = R.goto(5414, phrase); R.step('arrived 5414', secs=secs); time.sleep(2.5); R.cap('arrived')

        def children():
            out = []
            def cb(h, l):
                b = qa.c.create_unicode_buffer(128); qa.u.GetClassNameW(h, b, 128); out.append(b.value); return True
            qa.u.EnumChildWindows(R.g.hwnd, qa.CB(cb), 0)
            return sorted(set(out + [x['class'] for x in R.g.windows()]))
        base = set(children()); R.step('windows before', classes=sorted(base))

        def mci():
            """엔진이 MCIWndCreateA 로 만드는 영상 창(자식이든 위 창이든)"""
            found = []
            def cb(h, l):
                b = qa.c.create_unicode_buffer(128); qa.u.GetClassNameW(h, b, 128)
                if 'MCI' in b.value.upper(): found.append(h)
                return True
            qa.u.EnumChildWindows(R.g.hwnd, qa.CB(cb), 0)
            return found[0] if found else next((x['h'] for x in R.g.windows() if 'MCI' in x['class'].upper()), None)

        def rect(h, client=False):
            r = qa.w.RECT(); (qa.u.GetClientRect if client else qa.u.GetWindowRect)(h, qa.c.byref(r)); return [r.left, r.top, r.right, r.bottom]
        WM_USER = 0x400; GETMODE, GETPOS, GETLEN = WM_USER + 106, WM_USER + 102, WM_USER + 104      # MCIWNDM_GETMODEA·GETPOSITION·GETLENGTH
        started = None; h = None; user_save = 'usersave' in sys.argv
        for i in range(30):                         # 한 줄이 여러 번 클릭일 수 있어 5초 간격으로 클릭하며 영상 창을 기다린다(영상 중엔 클릭 안 함)
            h = mci()
            if h: break
            if user_save and i == 0:                # 영상 서너 클릭 앞(도착한 줄; 3클릭 뒤는 효과 화면이라 메뉴가 안 열림) — 사용자 눈 확인용 저장(지도 이동 뒤라 검수용 폴더로 감)
                P0 = R.cap('before-usersave')
                R.g.logical_click(R.g.hwnd, 400, 300, button='right'); time.sleep(1.5); R.g.logical_click(R.g.hwnd, 400, 300, button='right'); time.sleep(2)
                R.click(634, 56, 2.5); R.click(680, 150, 6); R.cap('usersave-slot3')
                for k_ in range(3):
                    R.click(670, 30, 4); P1 = R.cap(f'usersave-back{k_ + 1}')
                    if diff(P0, P1) < 2000: break
                R.step('user save made', back_same=diff(P0, P1))
            R.click(wait=0)
            for _ in range(20):
                time.sleep(.25); h = mci()
                if h: break
            if h: break
            if i % 4 == 3: R.cap(f'click{i + 1}')
        timeline = []
        if h:
            started = time.time(); R.step('movie window', after_clicks=i + 1, game_client=rect(R.g.hwnd, True), game_window=rect(R.g.hwnd), movie_window=rect(h),
                                          movie_client=rect(h, True), visible=bool(qa.u.IsWindowVisible(h)), length_ms=qa.u.SendMessageW(h, GETLEN, 0, 0))
            GWL_STYLE = -16; qa.u.GetWindowLongW.restype = qa.c.c_long
            R.r['styles'] = {'game': hex(qa.u.GetWindowLongW(R.g.hwnd, GWL_STYLE) & 0xffffffff), 'movie': hex(qa.u.GetWindowLongW(h, GWL_STYLE) & 0xffffffff)}
            caps = {8: 'movie-8s', 50: 'movie-50s', 95: 'movie-95s'}; pws = {10: 'pw-10s', 52: 'pw-52s'}; last = None
            k_present = R.t.mark()
            while time.time() - started < 300:
                el = time.time() - started; h2 = mci(); R.alive(); R.dialogs()
                if not h2: break
                pos = qa.u.SendMessageW(h2, GETPOS, 0, 0); mmode = qa.u.SendMessageW(h2, GETMODE, 0, 0)
                timeline.append((round(el, 1), pos, mmode, rect(h2)))
                for s_, nm in list(caps.items()):
                    if el >= s_: R.cap(nm, hd=True); caps.pop(s_)
                for s_, nm in list(pws.items()):
                    if el >= s_:
                        pws.pop(s_)
                        try:
                            R.r.setdefault('printwindow', {})[nm] = {'game': printwindow(R.g.hwnd, OUT / f'movie-{nm}-game.png'), 'movie': printwindow(h2, OUT / f'movie-{nm}-movie.png', 0)}
                        except Exception as e: R.r.setdefault('printwindow', {})[nm] = repr(e)[:200]
                time.sleep(.5)
            R.r['presents_during_movie'] = len(R.t.lines(k_present, 'present attempt'))
            R.r['movie_timeline'] = timeline
            R.step('movie window gone', seconds=round(time.time() - started, 1), last=timeline[-1] if timeline else None,
                   max_pos=max((p for _, p, _, _ in timeline), default=None), modes=sorted({m for _, _, m, _ in timeline}),
                   rects=sorted({tuple(r_) for *_, r_ in timeline}))
            time.sleep(3); R.cap('after-movie', hd=True); R.click(wait=3); R.cap('after-movie-click1'); R.click(wait=3); R.cap('after-movie-click2')
        else:
            R.step('no movie window after clicks', clicks=i + 1)
        R.r['gpu'] = gpu; stop_gpu.set(); R.close()

    elif mode == 'routes':
        ALL = json.loads((RVD / 'work' / 'route_targets.json').read_text('utf-8'))
        only = next((a[5:] for a in sys.argv if a.startswith('only=')), None)        # 다시 시험: only=6,7,41 → 그 번호만, 하나마다 새 게임
        T = [(i, ALL[i]) for i in map(int, only.split(','))] if only else list(enumerate(ALL))[FIRST:FIRST + COUNT]
        extra = next((a[6:] for a in sys.argv if a.startswith('extra=')), None)   # extra=37792:e → 갈래 끝 목록에 없는 줄(e = 엔딩처럼 타이틀까지)
        if extra: T = [(1000 + int(o), {'order': int(o), 'phrase': unique_phrase(int(o)), 'chapter': '?', 'ending': f == 'e', 'stepped_back': 0}) for o, f in (v.split(':') for v in extra.split(','))]
        R = None; done = 0; per_run = 1 if only or extra else 20
        for idx, t in T:
            if R is None: R = Run(f'routes-{idx:03d}' + ('-re' if only or extra else '')); R.r['mem_mb_start'] = R.mem()
            rec = {'i': idx, 'order': t['order'], 'chapter': t['chapter'], 'ending': t['ending']}
            try:
                secs, items = R.goto(t['order'], t['phrase']); rec.update(arrive_s=secs, items=items)
                if R.cover is not None: rec.update(cover_timeout_s=R.cover, cover_clicks=R.cover_clicks)
                time.sleep(2); R.cap(f'r{idx:03d}-arrived', hd=bool(only or extra))
                k = R.t.mark(); clicks = 0; limit = int(next((a_[6:] for a_ in sys.argv if a_.startswith('limit=')), 600)) if t['ending'] else 0
                t0 = time.time(); probed = False; tl = []; tnext = t0 + 30; kp = k
                capon = [n for n in next((a_[6:] for a_ in sys.argv if a_.startswith('capon=')), '').split(',') if n]   # capon=kr_ed_001,... → 그 그림이 처음 불리면 1초 뒤 화면 저장
                while True:
                    R.click(wait=CWAIT); clicks += 1
                    for n_ in list(capon):
                        nm_, _, dl_ = n_.partition('@')                     # kr_ed_024@6.8 → 그 그림이 불린 뒤 6.8초에 찍음
                        if R.t.find(f'load call {nm_}.', k) is not None:
                            capon.remove(n_); time.sleep(float(dl_ or 1)); R.cap(f'r{idx:03d}-on-{nm_}' + (f'-{dl_}s' if dl_ else ''), hd=True); rec.setdefault('capon_s', {})[n_] = round(time.time() - t0, 1)
                    # 다시 시험: 30초마다 [경과 초, 클릭 수, 그 30초의 그리기 수, 마지막으로 불린 그림, 글줄 누계] — 멈춤인지 느린 연출인지 시간축으로 가른다
                    if (only or extra) and time.time() > tnext:
                        tnext += 30; ls = R.t.lines(k, 'load call '); tx = R.t.lines(k, 'text4k lines=')
                        tl.append([round(time.time() - t0), clicks, len(R.t.lines(kp, 'present attempt')), ls[-1].split()[2] if ls else None,
                                   int(re.search(r'lines=(\d+)', tx[-1]).group(1)) if tx else None]); kp = R.t.mark(); rec['timeline'] = tl
                        # 그리기가 있다가 60초 동안 0번이면: 화면·CPU·스레드 위치(hang_probe)·Enter/오른쪽 클릭 반응을 한 번 잰다
                        if 'hang' not in rec and len(tl) >= 2 and tl[-1][2] == 0 and tl[-2][2] == 0:
                            from hang_probe import probe, deep
                            R.cap(f'r{idx:03d}-hang', hd=True); rec['hang'] = probe(R.g.pid, R.g.hwnd)
                            if any(a == 'deep' for a in sys.argv): rec['hang']['deep'] = deep(R.g.pid)
                            k2 = R.t.mark(); R.g.key(R.g.hwnd, VK['RET']); time.sleep(5); rec['hang']['enter_presents'] = len(R.t.lines(k2, 'present attempt'))
                            k2 = R.t.mark(); R.g.logical_click(R.g.hwnd, 400, 300, button='right'); time.sleep(5)
                            rec['hang']['rclick_presents'] = len(R.t.lines(k2, 'present attempt')); rec['hang']['at_s'] = round(time.time() - t0)
                            if any(a == 'hangquit' for a in sys.argv): rec['title_timeout'] = True; break
                    if R.t.find('load call title1_', k) is not None: rec['title_after_clicks'] = clicks; break
                    if not t['ending'] and clicks >= t['stepped_back'] + 8: break
                    if t['ending'] and time.time() - t0 > limit: rec['title_timeout'] = True; break
                    # 엔딩에서 2분 동안 그리기가 한 번도 없으면 멈춤으로 보고 화면을 찍고 다른 입력(Enter·오른쪽 클릭)이 먹는지 본다
                    if (only or extra) and t['ending'] and not probed and time.time() - t0 > 120 and not R.t.lines(k, 'present attempt'):
                        probed = True; R.cap(f'r{idx:03d}-stall', hd=True); k2 = R.t.mark()
                        R.g.key(R.g.hwnd, VK['RET']); time.sleep(5); rec['stall_enter_presents'] = len(R.t.lines(k2, 'present attempt'))
                        k2 = R.t.mark(); R.g.logical_click(R.g.hwnd, 400, 300, button='right'); time.sleep(5)
                        rec['stall_rclick_presents'] = len(R.t.lines(k2, 'present attempt')); R.cap(f'r{idx:03d}-stall-after-inputs', hd=True)
                rec['presents_after_arrival'] = len(R.t.lines(k, 'present attempt'))
                rec['clicks'] = clicks; time.sleep(1.5); R.cap(f'r{idx:03d}-after', hd=bool(only or extra))
                rec['ok'] = True; rec['mem_mb'] = R.mem()
            except Exception as e:
                rec['error'] = repr(e)[:300]; print('FAIL', idx, rec['error'], flush=True)
                try: R.alive()
                except Exception: rec['crash'] = True
            R.step(f'route {idx}', **{k_: v for k_, v in rec.items() if k_ not in ('i',)})
            R.r.setdefault('routes', []).append(rec); done += 1
            if 'error' in rec or done % per_run == 0:
                R.close(); R = None
        if R: R.close()
except Exception as e:
    res['error'] = repr(e)[:400]; print('ERROR', repr(e)[:300], flush=True)
    try: R.close()
    except Exception: pass
finally:
    HOLD.unlink(missing_ok=True)
    res['nv_after'] = nv(); res['ended'] = time.strftime('%Y-%m-%d %H:%M:%S')
    retry = any(a.startswith(('only=', 'extra=')) for a in sys.argv)            # 다시 시험 결과가 첫 판 routes-000.json 을 덮지 않게
    name = f'{mode}' + ('-retry-' + time.strftime('%H%M') if retry else (f'-{FIRST:03d}' if mode == 'routes' else '')) + '.json'
    (OUT / name).write_text(json.dumps(res, ensure_ascii=False, indent=1), 'utf-8')
    print(json.dumps({k: v for k, v in res.items() if k != 'runs'}, ensure_ascii=False))
