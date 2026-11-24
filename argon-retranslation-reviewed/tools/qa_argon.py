# 아르곤 반입 빌드 숨은 시험(숨은 데스크톱·음량 0·설정 키 따로, 사용자 입력 안 받음, 끝에 정상 종료)
# A 세이브 이어 하기: 타이틀 → 불러오기 → 1번 칸 → 예 → 세 쪽 읽기  (다른 세션 test_user_save.py 와 같은 조작)
# B 지도: F11 → 대사 찾기 → 문구 → 첫 줄 → 「여기서부터 본편으로」 → 도착 화면 찍기
import sys, time, json
from pathlib import Path
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools'); sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
import qa
from test_hitch import WM_APP
from PIL import Image
RVD = Path(__file__).resolve().parent.parent
run = RVD / 'runtime-argon-qa-20261121'; OUT = RVD / 'qa-20261121'; OUT.mkdir(exist_ok=True)
shots = run / 'qa'; shots.mkdir(exist_ok=True)
VK = dict(F11=0x7a, RET=0x0d, ESC=0x1b, DOWN=0x28)
n = 0; res = {'run': run.name, 'caps': [], 'jumps': []}
g = qa.Game(run=run, extra_env={'RECON_PERF': '2'})

def cap(name):
    global n; n += 1
    for p in shots.glob(f'quality-{n:02d}-*.bmp'): p.unlink()
    g.post(g.hwnd, WM_APP + 80, 10 + n, 0); g.until(lambda: (shots / f'quality-{n:02d}-base.bmp').exists(), 20, name); time.sleep(.4)
    out = OUT / f'{n:02d}-{name}.png'; Image.open(shots / f'quality-{n:02d}-base.bmp').convert('RGB').save(out); res['caps'].append(out.name)

def click(x, y, wait=2.0):
    g.move(g.hwnd, x, y); time.sleep(.3); g.logical_click(g.hwnd, x, y); time.sleep(wait)

def flow_snap(name):
    files = sorted((shots).glob('inflow-*.bmp'), key=lambda p: p.stat().st_mtime_ns)
    if files:
        out = OUT / f'{name}.png'; Image.open(files[-1]).convert('RGB').save(out); res['caps'].append(out.name)

def open_map():
    k = g.count('inflow opened'); g.key(g.hwnd, VK['F11']); g.until(lambda: g.count('inflow opened') > k, 20, 'map open'); time.sleep(1)
    return g.child()

def jump_to(tag, phrase, after_clicks=0):
    child = open_map()
    k = g.count('search_all'); g.logical_click(child, 576, 20); g.until(lambda: g.count('search_all') > k, 5, 'search all'); time.sleep(.5)
    ed = g.edit()
    for _ in range(40): g.post(ed, 0x102, 8)          # 앞 검색어 지우기
    time.sleep(.5)
    g.chars(ed, phrase); g.until(lambda: f'search len={len(phrase)} ' in g.log(), 8, 'search ' + tag); time.sleep(.5)
    hit = g.log().split(f'search len={len(phrase)} ')[-1].split('\n')[0]
    k = g.count('item='); g.key(child, VK['DOWN'], 1, 0); g.until(lambda: g.count('item=') > k, 5, 'item ' + tag)
    item = g.log().split('inflow item=')[-1].split('\n')[0][:80]
    k = g.count('inflow jump order='); g.story_jump(child); g.until(lambda: g.count('inflow jump order=') > k, 10, 'jump ' + tag)
    order = g.last('inflow jump order='); g.until(lambda: f'inflow arrived order={order} ' in g.log(), 180, 'arrive ' + tag)
    time.sleep(2.5); cap(tag)
    for i in range(after_clicks): g.logical_click(g.hwnd, 400, 300); time.sleep(2.2); cap(f'{tag}-next{i + 1}')
    res['jumps'].append({'tag': tag, 'phrase': phrase, 'search': hit[:120], 'item': item, 'order': order})

try:
    g.until(lambda: any(f'asset {k} ' in g.log() for k in ('1de0628c', 'ef1f6a40', 'c1e942c6')), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS'); time.sleep(2)
    if not qa.u.IsWindowVisible(g.hwnd): qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]: qa.u.SendMessageW(g.hwnd, m, a, 0)
    time.sleep(1); cap('title'); click(638, 388, 3); cap('loadscreen'); click(200, 150, 2); cap('slot'); click(310, 300, 6); cap('loaded')
    for i in range(3): g.logical_click(g.hwnd, 400, 300); time.sleep(2.2); cap(f'read{i + 1}')
    res['after_load_alive'] = g.poll() is None
    child = open_map(); flow_snap('map-open'); g.key(child, VK['ESC']); g.until(lambda: 'inflow closed' in g.log(), 10, 'map close'); time.sleep(1)
    PLAN = [('glyph-yun', '소설가로서의 재능 따윈', 0), ('glyph-saet', '샛길 쪽을 쓱', 0), ('glyph-mu', '커뮤니케이션을 할 생각은', 0),
            ('glyph-kick', '방금 그 킥은', 0), ('glyph-jamo', '낳긴 뭘 낳아', 0), ('choice-intro2', '그녀의 모습을 찾아볼까', 1),
            ('ruby-maho19', '달 없는 밤의', 0), ('ruby-maho16', '그 결과 마지막 고삐가', 0), ('ruby-kureha07', '그런데도 나는 고개를', 0),
            ('long-sina14', '유에와 나 나와 유에 유에와', 0),
            ('glyph-kwel', '이퀄 하교 시간이라는', 0), ('revert-group', '친한 무리가 확실히', 0)]   # 11-21 새 글자 퀄 / 일상어 되돌림 확인(그룹→무리)
    for tag, phrase, nxt in PLAN:
        try: jump_to(tag, phrase, nxt)
        except Exception as e: res['jumps'].append({'tag': tag, 'error': repr(e)[:300]}); print('JUMP FAIL', tag, repr(e)[:200])
    res['dialogs'] = [x['title'] for x in g.windows() if x['class'] == '#32770']; res['alive'] = g.poll() is None
    res['errors'] = [l for l in g.log().splitlines() if 'error' in l.lower() or 'fail' in l.lower()][:15]
except Exception as e:
    res['error'] = repr(e)[:400]; print('ERROR', repr(e)[:300])
finally:
    res['normal_exit'] = g.close_normally()
    (OUT / 'game.log').write_text(g.log(), 'utf-8')
(OUT / 'result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), 'utf-8'); print(json.dumps(res, ensure_ascii=False, indent=1))
