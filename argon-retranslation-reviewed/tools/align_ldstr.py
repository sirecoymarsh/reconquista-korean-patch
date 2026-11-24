# 최신판(runtime-final-20261028) 대본에서 원본 ldstr(루비·강조·선택지) 칸의 위치를 찾는 시험
# 방법: 원본 스크립트의 ldstr 문자열 열(v20 이 바꾼 칸은 v20 한국어로 치환)과 최신판 ldstr 문자열 열을 차례 맞춤
import sys, json, difflib, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from common import *
sys.dont_write_bytecode = True
C = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타'); R = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024')
sys.path.insert(0, str(C / 'tools'))
import build_trial as b
from inspect_majiro import Arc
def payload(p):
    a = Arc(p); raw = p.read_bytes(); return {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}
orig = payload(C / 'research/disc/scenario.arc'); fin = payload(R / 'runtime-final-20261028/scenario.arc')
mp = json.load(open(C / 'builds/body-ui-20261025-v20-nuance/font-map.json', encoding='utf-8-sig'))['mapping']; inv = {v: k for k, v in mp.items()}
dec = lambda s: ''.join(inv.get(x, x) for x in (s or ''))
snap = json.load(open(C / 'translation/integration/nuance-20261025-v1/integrated-targets.json', encoding='utf-8-sig'))
v20inline = {r['id']: r['target'] for r in snap['inline_records']}
T = json.load(open(RV / 'work' / 'table.json', encoding='utf-8'))
need = [r for r in T['rows'] if r['v20'] is None]
by_script = collections.defaultdict(list)
for r in need: by_script[r['id'].split('::')[0]].append(r)
found = {}; stat = collections.Counter()
for s, rs in by_script.items():
    oi = b.decode(orig[s])[0].instructions; fi = b.decode(fin[s])[0].instructions
    oseq = [(i, x.string) for i, x in enumerate(oi) if x.opcode.mnemonic == 'ldstr']
    fseq = [(i, dec(x.string)) for i, x in enumerate(fi) if x.opcode.mnemonic == 'ldstr']
    exp = [v20inline.get(f'{s}::{i:06d}', st) for i, st in oseq]
    sm = difflib.SequenceMatcher(None, exp, [t for _, t in fseq], autojunk=False)
    m = {}
    for a, bb, n in sm.get_matching_blocks():
        for k in range(n): m[oseq[a + k][0]] = fseq[bb + k][0]
    for r in rs:
        i = int(r['id'].split('::')[1])
        if i in m:
            found[r['id']] = f'{s}::{m[i]:06d}'; stat['mapped'] += 1
        else: stat['unmapped'] += 1
json.dump(found, open(RV / 'work' / 'ldstr_map_final.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(dict(stat), 'v20 inline records', len(v20inline), 'needed with v20 inline', sum(1 for r in need if r['id'] in v20inline))
