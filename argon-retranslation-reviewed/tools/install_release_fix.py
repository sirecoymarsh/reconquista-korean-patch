# 10-28 최신판(runtime-final-20261028)에 11-22 고침 넣기 — 대본 d5f17003(scenario_postfix)·DLL 86b18144(movie.inc).
# 옛 판은 build\backups 로 옮겨 두고, BUILD-IDENTITY.json 에 새 해시·바꾼 까닭·되돌리는 법을 적는다(11-21 배포 세션의 DLL 넣기와 같은 꼴).
# auto mode 가 Claude 의 최신판 쓰기를 막아(처음 조건 「runtime-final 은 덮어쓰지 않는다」) 사용자가 직접 돌린다:
#   python -I tools\install_release_fix.py        (results_reviewed_20261121 폴더에서)
# 같은 대본·DLL 로 숨은 시험 사본 runtime-release-qa-20261122 에서 시험을 마쳤다(qa-20261122\release\).
import sys, json, hashlib, shutil
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
R = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024'); S = R / 'runtime-final-20261028'; BK = R / 'build' / 'backups'
RV = Path(__file__).resolve().parent.parent; sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
new_arc = RV / 'work' / 'postfix-final1028' / 'scenario.arc'; new_dll = BK / 'ReconquistaHD-movie-86b18144.dll'
assert sha(new_arc).startswith('d5f17003') and sha(new_dll).startswith('86b18144'), '넣을 파일 해시가 다름'
if sha(S / 'scenario.arc').startswith('d5f17003') and sha(S / 'ReconquistaHD.dll').startswith('86b18144'):
    print('이미 들어가 있음'); sys.exit(0)
assert sha(S / 'scenario.arc').startswith('072aa90c') and sha(S / 'ReconquistaHD.dll').startswith('f11d9dca'), '최신판이 예상한 판(072aa90c·f11d9dca)이 아님'
for src, dst in ((S / 'scenario.arc', BK / 'scenario-final-072aa90c.arc'), (S / 'ReconquistaHD.dll', BK / 'ReconquistaHD-final-f11d9dca.dll'),
                 (S / 'BUILD-IDENTITY.json', BK / 'BUILD-IDENTITY-final-before-postfix-20261122.json')):
    if not dst.exists(): shutil.copyfile(src, dst)
    assert sha(dst) == sha(src)
idt = json.loads((S / 'BUILD-IDENTITY.json').read_text('utf-8'))
old_s, old_d = idt['scenario_sha256'], idt['dll_sha256']
shutil.copyfile(new_arc, S / 'scenario.arc'); shutil.copyfile(new_dll, S / 'ReconquistaHD.dll')
idt['scenario_sha256'] = sha(S / 'scenario.arc'); idt['dll_sha256'] = sha(S / 'ReconquistaHD.dll')
idt['scenario_sha256_before_20261122'] = old_s; idt['dll_sha256_before_20261122'] = old_d
idt['change_20261122'] = {
    'by': 'Claude (아르곤 검수 세션, 사용자 「전부 해결해」) — 사용자가 이 스크립트로 넣음',
    'scenario': 'tools/scenario_postfix.py — staffroll.mjo ED 가사 자막 스레드 wait(-2)→wait(16)(진엔딩 곡 장면 멈춤), 가사 24·32줄 끝 157.8·224.0초, maho_13 callp 선택 2곳 지도 빨리 감기 분기',
    'dll': 'native/movie.inc — 게임 안 영상 창을 4:3 화면 칸에 맞춤(MoveWindow), 지도 이동 중엔 영상 창을 안 만듦(MCIWndCreateA __cdecl)',
    'tests': '숨은 시험 runtime-release-qa-20261122(같은 대본·DLL): 영상 4:3 칸 끝까지 재생, 진엔딩 타이틀 287클릭·가사 24·32줄 늘린 끝 확인, maho_13 도착 13.2·8.9초, 영상 뒤 이동 5.2초',
    'revert': 'build/backups/scenario-final-072aa90c.arc · ReconquistaHD-final-f11d9dca.dll · BUILD-IDENTITY-final-before-postfix-20261122.json 을 되돌려 넣는다'}
(S / 'BUILD-IDENTITY.json').write_text(json.dumps(idt, ensure_ascii=False, indent=2), 'utf-8')
print('넣음: scenario', idt['scenario_sha256'][:8], 'dll', idt['dll_sha256'][:8])
