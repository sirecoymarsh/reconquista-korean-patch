# 다른 세션의 연표 시험(test_chronicle_actions.py scene|help)을 아르곤 숨은 시험 사본에 돌린다
# (그쪽 안내: qa.Game.__init__·qa.savehash 기본값이 정의 때 묶이므로 바꿔 준 뒤 runpy 로 돌린다)
# 사용: python -I tools\chron_run.py scene|help <label>
import sys, runpy
from pathlib import Path
T = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools')
sys.path.insert(0, str(T)); sys.dont_write_bytecode = True
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
import qa
RUN = Path(__file__).resolve().parent.parent / 'runtime-argon-qa-20261121'
assert RUN.exists()
qa.RUN = RUN
qa.Game.__init__.__defaults__ = (qa.RUN, None)
qa.savehash.__defaults__ = (qa.RUN,)
sys.argv = ['test_chronicle_actions.py'] + sys.argv[1:]
try:
    runpy.run_path(str(T / 'test_chronicle_actions.py'), run_name='__main__')
except SystemExit:
    pass
