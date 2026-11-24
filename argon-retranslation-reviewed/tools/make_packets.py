# 사람 눈 검수 묶음 만들기: AG 행 + 코덱스 미검수 아르곤 행을 장면 순서대로 묶음 파일로
# 출력: work/packets/P01.txt ... + work/packets/index.json
import json, sys, collections, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

T = json.load(open(RV / 'work' / 'table.json', encoding='utf-8'))
units = T['units']; order = T['order']; byid = {r['id']: r for r in T['rows']}
B = json.load(open(RV / 'work' / 'boundaries.json', encoding='utf-8'))
man = json.load(open(BASE / 'manifest.json', encoding='utf-8'))
chapter = {v['script']: v['chapter'] for v in man['scenes'].values()}

# 기계 점검 표시
hint = collections.defaultdict(set)
for r in csv.reader(open(RV / 'work' / 'machine_findings.tsv', encoding='utf-8-sig'), delimiter='\t'):
    if r[3] in ('POLITENESS_VS_V20',): hint[r[1]].add('말투가 v20과 다름(존댓말/반말)')
    if r[3] in ('PRONOUN_DIALOG',): hint[r[1]].add('대사에 그/그녀')
    if r[3] in ('LEN_RATIO_V20', 'SHIFT_SUSPECT'): hint[r[1]].add('길이·내용이 v20과 크게 다름')

SKIP_SCRIPTS = {'maho_18_2ero.mjo', 'sina_18_2ero.mjo'}   # 성인 장면 전용 파일: 정책상 사람 눈 검수 제외

def target(k):
    fs = [byid[f] for f in units[k]['fields'] if f in byid]
    if not fs: return False
    if any(f['model'] == 'antigravity-hybrid' for f in fs): return True
    if any(f['model'] == 'gemini-4-argon' and f['codex'] is None for f in fs): return True
    return False

def render(k):
    u = units[k]; bk = B.get(k, [])
    ja, ko, v = [], [], []
    fs = u['fields']
    for j, f in enumerate(fs):
        r = byid.get(f)
        if r is None: continue
        sep = '' if j == 0 else {'NL': ' ⏎ ', 'INLINE': '', 'PAGE': ' ⏎ '}.get(bk[j - 1] if j - 1 < len(bk) else 'NL', ' ⏎ ')
        role = u['roles'][f]
        if role == 'r':
            ja.append(f'{{읽기:{r["ja"]}}}'); ko.append(f'{{루비:{r["ko"]}}}')
            continue
        if r['fixed']:
            ja.append(f'{{읽기:{r["ja"]}}}'); ko.append(f'{{루비칸:{r["ko"]}}}')
            continue
        ja.append(sep + r['ja']); ko.append(sep + r['ko'])
        if r['v20'] is not None: v.append(sep + r['v20'])
    return ''.join(ja), ''.join(ko), ''.join(v)

# 대상 유닛 + 문맥(앞뒤 3행)
by_script = collections.OrderedDict()
for k in order:
    by_script.setdefault(units[k]['script'], []).append(k)
blocks = []   # (script, [(k, is_target)])
for s, ks in by_script.items():
    if s in SKIP_SCRIPTS: continue
    flags = [target(k) for k in ks]
    if not any(flags): continue
    keep = set()
    for i, f in enumerate(flags):
        if f:
            for j in range(max(0, i - 3), min(len(ks), i + 4)): keep.add(j)
    seq = [(ks[i], flags[i]) for i in sorted(keep)]
    blocks.append((s, seq))

# 글자 수로 묶음 나누기
def size(seq): return sum(sum(len(x) for x in render(k)) for k, t in seq)
N = 10
total = sum(size(seq) for s, seq in blocks)
per = total / N
packets = [[]]; acc = 0
for s, seq in blocks:
    sz = size(seq)
    if acc > 0 and acc + sz / 2 > per * len(packets) and len(packets) < N:
        packets.append([])
    packets[-1].append((s, seq)); acc += sz
out = RV / 'work' / 'packets'; out.mkdir(exist_ok=True)
index = {}
for pi, pk in enumerate(packets, 1):
    name = f'P{pi:02d}'
    lines = []
    ntarget = 0
    for s, seq in pk:
        lines.append(f'\n### {s} ({chapter.get(s, "")})')
        prev = None
        for k, t in seq:
            ja, ko, v = render(k)
            uid = k.split('::')[1]
            sp = units[k]['sp']
            if not t:
                lines.append(f'({uid} 문맥·검수 대상 아님) [{sp}] JA: {ja} / KO: {ko}')
                continue
            ntarget += 1
            model = '/'.join(sorted({byid[f]["model"][:2] for f in units[k]["fields"] if f in byid}))
            h = ' ⚑' + '·'.join(sorted(hint[k])) if k in hint else ''
            lines.append(f'{uid} [{sp}]{h}\n  JA: {ja}\n  KO: {ko}' + (f'\n  V20: {v}' if v else ''))
    (out / f'{name}.txt').write_text('\n'.join(lines), encoding='utf-8')
    index[name] = dict(scripts=[s for s, _ in pk], targets=ntarget, chars=sum(size(seq) for _, seq in pk))
json.dump(index, open(out / 'index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, v in index.items(): print(k, v['targets'], v['chars'], v['scripts'][0], '...', v['scripts'][-1])
print('total targets', sum(v['targets'] for v in index.values()))
