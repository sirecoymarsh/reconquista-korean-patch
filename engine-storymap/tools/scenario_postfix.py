# 레콘키스타 대본(scenario.arc) 뒷손질 — 지도 빌드(build_storymap.py)·10-28 최신판·아르곤 반입 빌드가 같이 쓴다(11-22 아르곤 검수 세션).
# 다시 돌려도 결과가 같다(이미 고친 곳은 세고 건너뜀). 바꾸는 것:
#  ① staffroll.mjo ED 가사 자막 스레드(0xf7adcfda)·정리 함수(0x47611c0a)의 wait(-2) 65곳 → wait(16)
#     까닭: wait(-2) 는 엔진 시계 멈춤 깃발 [0x494674] 을 켠다(레콘키스타.exe 0x41045f). 프레임마다 시계 [0x494678] 는 깃발이 꺼졌을 때만
#     timeGetTime 으로 갱신되고(0x40b260) $timer 는 그 시계를 돌려준다(0x40a620). $timer 로 곡 시각을 기다리며 매 프레임 wait(-2) 하면
#     시계가 영영 서서 진엔딩 곡 장면(last_ep 2456 뒤)에서 게임 전체가 멈췄다. 양수 wait 는 깃발을 안 건드린다.
#  ② 같은 스레드의 가사 24·32번째 줄 끝 시각: 노래가 끝음을 끄는 동안 자막이 먼저 꺼졌다(원곡−반주로 보컬을 뽑아 0.5초 단위로 잼)
#     → 155200→157800, 220700→224000 ms. 다음 줄 시작(179100·없음)과 안 겹친다. 다른 줄은 시작·끝 모두 ±1.5초 안이라 그대로.
#  ③ 이야기 장의 callp 꼴 선택(보기 하나짜리, maho_13 두 곳)을 지도 빨리 감기 분기로 감싼다. 지도 빌드는 call 꼴만 감쌌다.
#     빨리 감기 중엔 인자만 버린다(callp 라 결과는 원래 버려짐). 보통 플레이는 그대로.
#     주의: ③은 maho_13.mjo 바이트 위치를 바꾼다 → 그 장 안에서 만든 옛 세이브는 어긋난다(배포 전·사용자 진도는 도입부).
# 사용: python -I scenario_postfix.py <입력 scenario.arc> <출력 scenario.arc>   (입력=출력 거부 — 하드 링크 사본 보호)
#       또는 import scenario_postfix; report = scenario_postfix.postfix_payload(payload)   # {이름: mjo 바이트} 를 그 자리에서 고침
import sys, struct, hashlib
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_model as CM
core = CM.core; b = core.b

WORKER, STOP, WAIT = 0xf7adcfda, 0x47611c0a, 0xcf35f0e3
WAIT_EXPECT = {WORKER: 64, STOP: 1}
LYRIC_END = {155200: 157800, 220700: 224000}          # 가사 24·32번째 줄 끝(ms)
STORY_CALLP_SELECT = 2                                # maho_13 1186·2098 (10-28 최신판 번호)


def _ranges(s, raw, hashes):
    fn = sorted((f.offset, f.name_hash) for f in s.functions)
    return {h: (o, next((o2 for o2, _ in fn if o2 > o), len(raw))) for o, h in fn if h in hashes}


def fix_staffroll(old):
    s, raw = b.decode(old); rng = _ranges(s, raw, WAIT_EXPECT)
    if set(rng) != set(WAIT_EXPECT): return old, {'staffroll': 'no ED lyric thread (original or other build) — unchanged'}
    new = bytearray(raw); waits = {h: 0 for h in WAIT_EXPECT}; ends = {k: 0 for k in LYRIC_END}; L = s.instructions
    wa, wz = rng[WORKER]
    for k, x in enumerate(L[:-1]):
        y = L[k + 1]
        if x.opcode.mnemonic == 'ldc.i' and y.opcode.mnemonic == 'syscallp' and (y.hash or 0) == WAIT:
            for h, (a, z) in rng.items():
                if a <= x.offset < z and x.int_value in (-2, 16):
                    struct.pack_into('<i', new, x.offset + x.size - 4, 16); waits[h] += 1
        if x.opcode.mnemonic == 'ldc.i' and wa <= x.offset < wz:
            for old_ms, new_ms in LYRIC_END.items():
                if x.int_value in (old_ms, new_ms):
                    struct.pack_into('<i', new, x.offset + x.size - 4, new_ms); ends[old_ms] += 1
    assert waits == WAIT_EXPECT, waits
    assert all(v == 2 for v in ends.values()), ends          # 줄마다 「지난 줄 건너뛰기」·「끝까지 기다리기」 두 곳
    out = old[:s.bytecode_offset] + (b.crypt32(bytes(new)) if s.signature == s.SIGNATURE_ENCRYPTED else bytes(new))
    s2, r2 = b.decode(out)
    assert r2 == bytes(new) and [(f.name_hash, f.offset) for f in s2.functions] == [(f.name_hash, f.offset) for f in s.functions]
    return out, {'staffroll_waits': waits, 'lyric_end_sites': ends}


def gate_callp_select(mjo):
    """callp 꼴 선택 함수를 core.gate 로 감싼다. 이미 감싼 곳(바로 앞이 그 명령만 건너뛰는 br)은 센다."""
    s, raw = b.decode(mjo); L = s.instructions; repl = {}; already = 0
    for i, x in enumerate(L):
        if x.opcode.mnemonic == 'callp' and (x.hash or 0) == core.SELECT:
            p = L[i - 1] if i else None
            if p is not None and p.opcode.mnemonic == 'br' and p.offset + p.size + p.jump_offset == x.offset + x.size: already += 1; continue
            repl[i] = core.gate(raw[x.offset:x.offset + x.size], b.op('pop') * x.argument_count)
    for x in L:
        if x.is_jump: assert x.opcode.encoding == 'j', x.opcode.mnemonic       # core.rewrite 가 옮길 수 있는 꼴만
    return (core.rewrite(mjo, repl, {}, {}) if repl else mjo), len(repl), already


def postfix_payload(payload, story=None):
    rep = {}
    if 'staffroll.mjo' in payload:
        payload['staffroll.mjo'], r = fix_staffroll(payload['staffroll.mjo']); rep.update(r)
    story = story if story is not None else set(CM.model().s)
    gated = {}; total = 0
    for n in sorted(story):
        key = n + '.mjo'
        if key not in payload: continue
        payload[key], g, a = gate_callp_select(payload[key])
        if g or a: gated[n] = {'gated_now': g, 'already': a}; total += g + a
    assert total == STORY_CALLP_SELECT, gated
    rep['story_callp_select'] = gated
    return rep


def main(src, dst):
    src, dst = Path(src), Path(dst)
    assert src.resolve() != dst.resolve(), '입력과 출력이 같은 파일'
    arc = core.Arc(src); raw = arc.path.read_bytes()
    before = {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in arc.entries}; payload = dict(before)
    rep = postfix_payload(payload)
    data = arc.rebuild(payload); dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(data)
    chk = core.Arc(dst); cr = chk.path.read_bytes(); back = {e['name']: cr[e['offset']:e['offset'] + e['size']] for e in chk.entries}
    assert back == payload and len(back) == len(before)
    sha = lambda d: hashlib.sha256(d).hexdigest()
    rep.update(input=sha(raw)[:8], output=sha(data)[:8], changed=sorted(k for k in before if before[k] != payload[k]), entries=len(back))
    print(rep)
    return rep


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(*sys.argv[1:3])
