# 외래어 방침 검수 묶음: loan_scan.json 의 후보 칸을 유닛째(현재 확정본 KO) 보여 준다 → work/loan_packets/L01.txt ...
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from common import *

T = json.load(open(RV / 'work' / 'table.json', encoding='utf-8'))
units = T['units']; order = T['order']
B = json.load(open(RV / 'work' / 'boundaries.json', encoding='utf-8'))
F = {json.loads(l)['id']: json.loads(l) for l in open(RV / 'work' / 'confirmed_before_loan.jsonl', encoding='utf-8')}  # 외래어 고침 전 확정본(바꿀부분 기준)
S = json.load(open(RV / 'work' / 'loan_scan.json', encoding='utf-8'))
words = collections.defaultdict(set)
for w, ids in S['miss'].items():
    for i in ids: words[F[i]['unit']].add(w)

def render(k):
    u = units[k]; bk = B.get(k, []); ja, ko = [], []
    for j, f in enumerate(u['fields']):
        r = F.get(f)
        if r is None: continue
        sep = '' if j == 0 else {'NL': ' ⏎ ', 'INLINE': '', 'PAGE': ' ⏎ '}.get(bk[j - 1] if j - 1 < len(bk) else 'NL', ' ⏎ ')
        role = u['roles'][f]
        if role == 'r' or u['fixed'].get(f):
            ja.append(f'{{읽기:{r["ja"]}}}'); ko.append(f'{{루비:{r["ko"]}}}'); continue
        ja.append(sep + r['ja']); ko.append(sep + r['ko'])
    return ''.join(ja), ''.join(ko)

pos = {k: i for i, k in enumerate(order)}
targets = sorted(words, key=lambda k: pos[k])
N = 4
per = len(targets) / N
out = RV / 'work' / 'loan_packets'; out.mkdir(exist_ok=True)
index = {}
for pi in range(N):
    part = targets[round(pi * per):round((pi + 1) * per)]
    lines = []; cur_s = None
    for k in part:
        s = units[k]['script']
        if s != cur_s: lines.append(f'\n### {s}'); cur_s = s
        i = pos[k]; prev = order[i - 1] if i > 0 and units[order[i - 1]]['script'] == s else None
        ja, ko = render(k)
        if prev:
            pj, pk_ = render(prev); lines.append(f'  (앞 줄) JA: {pj} / KO: {pk_}')
        lines.append(f'{k.split("::")[1]} [{units[k]["sp"]}] 낱말: {", ".join(sorted(words[k]))}\n  JA: {ja}\n  KO: {ko}')
    name = f'L{pi + 1:02d}'
    (out / f'{name}.txt').write_text('\n'.join(lines), encoding='utf-8')
    index[name] = dict(units=len(part), chars=sum(len(x) for x in lines), first=part[0], last=part[-1])
json.dump(index, open(out / 'index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, v in index.items(): print(k, v)
