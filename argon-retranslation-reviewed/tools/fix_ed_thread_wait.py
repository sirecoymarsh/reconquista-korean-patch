# 진엔딩 곡 장면 멈춤 고침 — 11-22 부터 지도 프로젝트 공용 도구 scenario_postfix.py 를 부르는 껍데기.
# 까닭(엔진 분석): wait(-2) 는 「시계 멈춤 깃발」[0x494674] 을 켜고 한 프레임 쉰다. 깃발이 켜진 프레임엔 엔진 시계 [0x494678](=$timer)가 안 바뀐다.
#   $timer 로 곡 시각을 기다리며 매 프레임 wait(-2) 하면 시계가 영영 서서 고리도 본문도 멈춘다. 양수 wait 는 깃발을 안 건드린다.
# 근거(11-22 숨은 시험, qa-20261122\variant-*·endsave-fixed.json): wait(-2) 판은 곡 시작 뒤 첫 가사(16.2초) 전에 멈추고,
#   wait(16) 판은 보통 진행·지도 이동·지도 없이 세이브로 이어 하기 모두 타이틀까지 가며 가사 32줄이 뜬다.
# 공용 도구가 함께 고치는 것: 가사 24·32번째 줄 끝 시각(노래보다 먼저 꺼짐), maho_13 의 callp 꼴 선택 빨리 감기.
# 사용: python -I tools\fix_ed_thread_wait.py <입력 scenario.arc> <출력 scenario.arc>   (입력과 출력이 같으면 거부 — 하드 링크 사본 보호)
import sys
sys.dont_write_bytecode = True; sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools')
import scenario_postfix

if __name__ == '__main__':
    scenario_postfix.main(*sys.argv[1:3])
