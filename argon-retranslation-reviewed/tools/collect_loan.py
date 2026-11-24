# 외래어 되살리기 에이전트 결과(work/loan_review/Lxx_fixes.tsv)를 칸 id 에 붙인다 → work/fixes_loan.json, work/loan_verify.txt
import json, sys, csv, glob, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from common import *
T = json.load(open(RV / 'work' / 'table.json', encoding='utf-8')); units = T['units']
F = {json.loads(l)['id']: json.loads(l) for l in open(RV / 'work' / 'confirmed_before_loan.jsonl', encoding='utf-8')}  # 외래어 고침 전 확정본(바꿀부분 기준)
out = []; bad = []; policy = []; native = []
for p in sorted(glob.glob(str(RV / 'work' / 'loan_review' / 'L*_fixes.tsv'))):
    pk = Path(p).stem.split('_')[0]
    for row in list(csv.reader(open(p, encoding='utf-8-sig'), delimiter='\t'))[1:]:
        if not row or not any(row): continue
        row = row + [''] * (7 - len(row))
        script, uid, word, old, new, form, why = row[:7]
        if word == '정책보류': policy.append((pk, script, uid)); continue
        key = f'{script}::{uid}'
        if key not in units: bad.append((pk, key, 'no unit')); continue
        hits = [f for f in units[key]['fields'] if f in F and old and F[f]['ko'].count(old) == 1]
        if len(hits) != 1: bad.append((pk, key, f'hits={len(hits)}', old)); continue
        if old == new: bad.append((pk, key, 'same')); continue
        out.append(dict(packet=pk, id=hits[0], unit=key, word=word, old=old, new=new, form=form, why=why))
for p in sorted(glob.glob(str(RV / 'work' / 'loan_review' / 'L*_native.tsv'))):
    pk = Path(p).stem.split('_')[0]
    for row in list(csv.reader(open(p, encoding='utf-8-sig'), delimiter='\t'))[1:]:
        if row and any(row): native.append([pk] + row)
# 같은 칸 여러 고침이 겹치는지
byf = collections.defaultdict(list)
for o in out: byf[o['id']].append(o)
over = [k for k, v in byf.items() if len(v) > 1]
json.dump(out, open(RV / 'work' / 'fixes_loan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(dict(policy=policy, native=native, bad=bad), open(RV / 'work' / 'loan_other.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('resolved', len(out), 'fields', len(byf), 'multi-fix fields', len(over), 'bad', len(bad), 'policy', len(policy), 'native', len(native))
print(collections.Counter(o['packet'] for o in out))
forms = collections.defaultdict(collections.Counter)
for o in out: forms[o['word']][o['form']] += 1
print('낱말별 꼴:', ' '.join(f'{w}=' + '/'.join(f'{f}:{n}' for f, n in c.most_common()) for w, c in sorted(forms.items(), key=lambda x: -sum(x[1].values()))))
for b_ in bad: print('BAD', b_)
with open(RV / 'work' / 'loan_verify.txt', 'w', encoding='utf-8') as f:
    for i, o in enumerate(out):
        u = units[o['unit']]
        ja = ' ⏎ '.join(F[x]['ja'] for x in u['fields'] if x in F)
        f.write(f"#{i} {o['packet']} {o['unit']} [{u['sp']}] {o['word']}→{o['form']}\n  JA: {ja}\n  KO: {F[o['id']]['ko']}\n  고침: 「{o['old']}」→「{o['new']}」  ({o['why']})\n")
