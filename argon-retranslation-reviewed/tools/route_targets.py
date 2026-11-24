# 「모든 갈래를 끝까지」 시험의 목적지: 이야기 지도 코드 나무(info 의 부모 고리)에서 다른 지도 줄의 조상이 아닌 줄(= 갈래 끝) 102개.
# 지도 이동은 뿌리에서 그 줄까지의 길을 엔진이 빨리 감기로 실제로 돈다 → 이 102곳에 모두 도착하면 지도 44,020줄이 모두 한 번은 실행된다.
# 줄마다 지도 찾기로 하나만 걸리는 문구를 고른다(문구는 파일에만; 채팅·보고서엔 번호만).
# 사용: python -I tools\route_targets.py   -> work\route_targets.json
import sys, json, collections
from pathlib import Path
sys.dont_write_bytecode = True; sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools')
from read_storymap import parse
RV = Path(__file__).resolve().parent.parent
x = parse(RV / 'build-20261121' / 'storymap.bin'); nodes, ch = x['nodes'], x['chapters']; par = [i[0] for i in x['info']]
anc = set()
for n in nodes:
    p = par[n['gid']]
    while p >= 0 and p not in anc: anc.add(p); p = par[p]
leaf = [i for i, n in enumerate(nodes) if n['gid'] not in anc]
by_gid = {n['gid']: i for i, n in enumerate(nodes)}
covered = set()
for i in leaf:
    g = nodes[i]['gid']
    while g >= 0:
        if g in by_gid: covered.add(by_gid[g])
        g = par[g]
assert len(covered) == len(nodes), (len(covered), len(nodes))
texts = [n['text'] for n in nodes]
BAD = set('「」『』〔〕《》（）()…―─　\n\t“”‘’"\'・')          # 보통 빈칸은 문구 안에 둬도 됨(끝만 안 됨)


def unique_phrase(i):
    t = texts[i]
    for L in (10, 12, 14, 16, 8, 18, 20):
        for s in range(0, max(1, len(t) - L + 1)):
            p = t[s:s + L]
            if len(p) < L or p[0] == ' ' or p[-1] == ' ' or any(ch_ in BAD for ch_ in p): continue
            if sum(1 for u in texts if p in u) == 1 and not any(p in n['speaker'] for n in nodes): return p
    return None


ENDS = {c['id'] for k, c in enumerate(ch) if k not in {a for a, b in x['edges']}}
out = []
for i in leaf:
    j = i
    # 글 없는 줄(선택지 표지 등)이면 같은 길의 앞 글줄을 목적지로(그 뒤는 도착 후 클릭으로 지나간다)
    g = nodes[j]['gid']
    while not texts[j].strip():
        g = par[g]
        while g >= 0 and g not in by_gid: g = par[g]
        j = by_gid[g]
    p = unique_phrase(j); back = 0
    while p is None and back < 5:          # 문구가 겹치면 같은 길의 한 줄 앞
        g = par[nodes[j]['gid']]
        while g >= 0 and g not in by_gid: g = par[g]
        j = by_gid[g]; p = unique_phrase(j); back += 1
    hits = 1
    if p is None:                         # 짧고 흔한 줄: 겹치는 문구로 찾고 시험에서 ↓ 를 눌러 순번(order)이 맞는 항목을 고른다
        t = texts[j]; cands = [t[a:b] for a in range(len(t)) for b in range(len(t), a, -1)
                               if t[a] != ' ' and t[b - 1] != ' ' and not any(q in BAD for q in t[a:b])]
        p = max(cands, key=len) if cands else t.strip(); hits = sum(1 for u in texts if p in u)
    c_ = ch[nodes[i]['chapter']]['id']
    out.append({'leaf': i, 'target': j, 'order': nodes[j]['order'], 'chapter': c_, 'ending': c_ in ENDS, 'kind': nodes[i]['kind'],
                'phrase': p, 'hits': hits, 'stepped_back': back + (j != i and back == 0)})
out.sort(key=lambda o: o['order'])
(RV / 'work' / 'route_targets.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), 'utf-8')
print('leaves', len(leaf), 'covered nodes', len(covered), 'no phrase', sum(1 for o in out if not o['phrase']),
      'endings', sum(o['ending'] for o in out), 'stepped back', sum(1 for o in out if o['stepped_back']), 'end chapters', sorted(ENDS))
