# 에이전트 지적(Pxx_fixes.tsv)을 칸 id 에 붙이고 대조표를 만든다 → work/agent_fixes_resolved.json, work/agent_verify.txt
import json, sys, csv, glob, collections, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from common import *
T = json.load(open(RV / 'work' / 'table.json', encoding='utf-8'))
byid = {r['id']: r for r in T['rows']}; units = T['units']
mech = {f['id']: f['new'] for f in json.load(open(RV / 'work' / 'fixes_mech.json', encoding='utf-8'))}
cur = lambda fid: mech.get(fid, byid[fid]['ko'])
out = []; bad = []; policy = []
for p in sorted(glob.glob(str(RV / 'work' / 'agent_review' / 'P*_fixes.tsv'))):
    pk = Path(p).stem.split('_')[0]
    rows = list(csv.reader(open(p, encoding='utf-8-sig'), delimiter='\t'))
    for row in rows[1:]:
        if not row or not any(row): continue
        row = row + [''] * (6 - len(row))
        script, uid, kind, old, new, why = row[:6]
        if kind == '정책보류':
            policy.append((pk, script, uid)); continue
        key = f'{script}::{uid}'
        if key not in units: bad.append((pk, row, 'no unit')); continue
        hits = [f for f in units[key]['fields'] if f in byid and old and cur(f).count(old) == 1]
        if len(hits) != 1:
            # 원래 KO 기준으로 다시
            hits = [f for f in units[key]['fields'] if f in byid and old and byid[f]['ko'].count(old) == 1]
        if len(hits) != 1: bad.append((pk, row, f'hits={len(hits)}')); continue
        fid = hits[0]
        out.append(dict(packet=pk, id=fid, unit=key, kind=kind, old=old, new=new, why=why, model=byid[fid]['model']))
json.dump(out, open(RV / 'work' / 'agent_fixes_resolved.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('resolved', len(out), 'bad', len(bad), 'policy ranges', len(policy))
print(collections.Counter(o['kind'] for o in out))
print(collections.Counter(o['packet'] for o in out))
for b_ in bad: print('BAD', b_)
with open(RV / 'work' / 'agent_verify.txt', 'w', encoding='utf-8') as f:
    for o in out:
        u = units[o['unit']]
        ja = ' ⏎ '.join(byid[x]['ja'] for x in u['fields'] if x in byid)
        ko = ' ⏎ '.join(cur(x) for x in u['fields'] if x in byid)
        v = ' ⏎ '.join(byid[x]['v20'] for x in u['fields'] if x in byid and byid[x]['v20'] is not None)
        f.write(f"#{out.index(o)} {o['packet']} {o['unit']} [{u['sp']}] {o['kind']} ({o['model'][:6]})\n  JA: {ja}\n  KO: {ko}\n  V20: {v}\n  고침: 「{o['old']}」→「{o['new']}」\n  근거: {o['why']}\n")
json.dump(policy, open(RV / 'work' / 'policy_ranges.json', 'w', encoding='utf-8'), ensure_ascii=False)
