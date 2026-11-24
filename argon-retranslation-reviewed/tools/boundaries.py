# 원본 스크립트 명령으로 한 행 안 칸 사이 경계(줄바꿈 NL / 줄 안 INLINE / 루비 RUBY) 구하기 → work/boundaries.json
# 그리고 줄 안 경계의 띄어쓰기 누락 후보 → work/inline_space.tsv
import json, sys, collections, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *
sys.dont_write_bytecode = True
C = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타')
sys.path.insert(0, str(C / 'tools'))
import build_trial as b
from inspect_majiro import Arc

T = json.load(open(RV / 'work' / 'table.json', encoding='utf-8'))
byid = {r['id']: r for r in T['rows']}
units = T['units']
p = C / 'research/disc/scenario.arc'
a = Arc(p); raw = p.read_bytes()
ent = {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}
cache = {}
def ins(script):
    if script not in cache:
        cache[script] = b.decode(ent[script])[0].instructions
    return cache[script]

bnd = {}
for key, u in units.items():
    fs = u['fields']
    if len(fs) < 2: continue
    I = ins(u['script'])
    out = []
    for x, y in zip(fs, fs[1:]):
        i = int(x.split('::')[1]); j = int(y.split('::')[1])
        mids = I[i + 1:j]
        kinds = [m.opcode.mnemonic + (':' + m.string if m.opcode.mnemonic == 'ctrl' and m.string else '') for m in mids]
        if 'ctrl:n' in kinds: t = 'NL'
        elif any(k.startswith('ctrl:p') or k.startswith('ctrl:w') for k in kinds): t = 'PAGE'
        else: t = 'INLINE'
        out.append(t)
    bnd[key] = out
json.dump(bnd, open(RV / 'work' / 'boundaries.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('units with boundaries', len(bnd), collections.Counter(t for v in bnd.values() for t in v))

# 줄 안 경계 띄어쓰기 점검
rows = []
H = lambda ch: bool(ch) and bool(HANGUL.match(ch))
for key, kinds in bnd.items():
    fs = units[key]['fields']
    for (x, y), t in zip(zip(fs, fs[1:]), kinds):
        if t != 'INLINE': continue
        rx, ry = byid.get(x), byid.get(y)
        if not rx or not ry: continue
        # 루비 읽기 칸(빈칸 허용)은 건너뜀: 다음 칸과 짝
        a_, b_ = rx['ko'], ry['ko']
        if rx['fixed'] or ry['fixed']: continue
        if not a_ or not b_: continue
        joined_gap = a_[-1:] + b_[:1]
        nospace = H(a_[-1:]) and H(b_[:1])
        v20gap = None
        if rx['v20'] is not None and ry['v20'] is not None and rx['v20'] and ry['v20']:
            v20gap = rx['v20'][-1:] in (' ', '　') or ry['v20'][:1] in (' ', '　')
        newgap = a_[-1:] in (' ', '　') or b_[:1] in (' ', '　')
        double = a_[-1:] in (' ', '　') and b_[:1] in (' ', '　')
        if nospace or double:
            rows.append((x, y, rx['model'], 'NOSPACE' if nospace else 'DOUBLE', str(v20gap), rx['ja'] + '|' + ry['ja'], a_ + '|' + b_, (rx['v20'] or '') + '|' + (ry['v20'] or '')))
with open(RV / 'work' / 'inline_space.tsv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['id_a', 'id_b', 'model', 'kind', 'v20_has_gap', 'ja', 'ko', 'v20']); w.writerows(rows)
print(collections.Counter((r[2], r[3], r[4]) for r in rows))
