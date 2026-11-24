# 검수용 통합표 만들기: 번역필드 + 입력(화자·행 순서) + v20 + 코덱스 검수 판정 + AG 원파일
# 출력: work/table.json (id 순서대로 필드 목록), work/units.json
import json, csv, glob, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

import os
F = load_fields(os.environ.get('RV_FIELDS') or None)
V = load_v20()
v20 = V['v20']; ops = V['ops']

# 입력 행(화자·순서)
units = {}      # unit_key -> dict(script, uid, index, sp, fields=[ids])
order = []
scene_of_script = {}
for p in sorted(glob.glob(str(BASE / 'inputs' / 'S*.json'))):
    d = json.load(open(p, encoding='utf-8'))
    sc = Path(p).stem
    script = d['script']
    scene_of_script[script] = sc
    for r in d['rows']:
        if 'fields' not in r: continue
        key = f"{script}::{r['id']}"
        units[key] = dict(script=script, scene=sc, uid=r['id'], index=r['index'], sp=r.get('sp', ''),
                          voice=r.get('voice', ''), fields=[f"{script}::{x[0]:06d}" for x in r['fields']],
                          fixed={f"{script}::{x[0]:06d}": bool(x[3]) for x in r['fields']},
                          roles={f"{script}::{x[0]:06d}": x[1] for x in r['fields']})
        order.append(key)

# 코덱스 검수 판정 (아르곤 행)
codex = {}
with open(BASE / 'quality_review' / '검수_판정.tsv', encoding='utf-8-sig') as f:
    rd = csv.reader(f, delimiter='\t')
    hdr = next(rd)
    for row in rd:
        if len(row) < 6: continue
        job, scene, uid, chap, sp, verdict = row[:6]
        codex.setdefault(uid + '@' + job, verdict)
# 검수판정 키는 job+uid → 스크립트 대응은 job 으로
fixed_fields = {}
for l in open(BASE / 'quality_review' / '확정_교정필드.jsonl', encoding='utf-8'):
    if l.strip():
        o = json.loads(l); fixed_fields[o['id']] = o

# AG 원파일
ag = {}
for p in glob.glob(str(BASE / 'antigravity_translations' / 'T*.json')):
    d = json.load(open(p, encoding='utf-8'))
    ag[d['id']] = d

rows = []
for o in F:
    u = units.get(o['unit'])
    rec = dict(id=o['id'], unit=o['unit'], role=o['role'], ja=o['ja'], ko=o['ko'], model=o['translator_model'],
               job=o.get('job'), flags=o.get('review_flags') or [], v20=v20.get(o['id']),
               sp=(u['sp'] if u else None), scene=(u['scene'] if u else None),
               fixed=(u['fixed'].get(o['id']) if u else None),
               codex=None, codex_fixed=o['id'] in fixed_fields)
    if u and o.get('job'):
        rec['codex'] = codex.get(u['uid'] + '@' + o['job'])
    rows.append(rec)

json.dump(dict(rows=rows, order=order, units=units), open(os.environ.get('RV_TABLE') or (RV / 'work' / 'table.json'), 'w', encoding='utf-8'), ensure_ascii=False)
c = collections.Counter((r['model'], r['codex']) for r in rows)
for k, n in sorted(c.items(), key=lambda x: str(x)): print(k, n)
print('rows', len(rows), 'units', len(units), 'no-unit', sum(1 for r in rows if r['sp'] is None))
# codex 교정 반영 확인
mis = [i for i, o in fixed_fields.items() if i in {r['id'] for r in rows} and next(r for r in rows if r['id'] == i)['ko'] != o['ko']] if False else None
byid = {r['id']: r for r in rows}
applied = sum(1 for i, o in fixed_fields.items() if i in byid and byid[i]['ko'] == o['ko'])
notin = sum(1 for i in fixed_fields if i not in byid)
print('codex fixes', len(fixed_fields), 'applied', applied, 'not-in-fields', notin,
      'differs', len(fixed_fields) - applied - notin)
