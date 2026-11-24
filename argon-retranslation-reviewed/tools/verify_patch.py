# 반입 빌드 독립 검증: 빌드 결과를 처음부터 다시 읽어 확정본과 칸마다 맞는지, 그 밖은 최신판과 같은지
import sys, json, collections, difflib, re, hashlib
from pathlib import Path
sys.dont_write_bytecode = True; sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); from common import *
C = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타'); R = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024')
sys.path.insert(0, str(C / 'tools')); sys.path.insert(0, str(R / 'tools'))
import build_trial as b
from inspect_majiro import Arc
from read_storymap import parse
OUT = RV / 'build-20261121'; FINAL = R / 'runtime-final-20261028'
def payload(p):
    a = Arc(p); raw = Path(p).read_bytes(); return {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}
newmap = json.loads((OUT / 'font-map.json').read_text('utf-8'))['mapping']; newinv = {v: k for k, v in newmap.items()}
oldmap = json.loads((C / 'builds/body-ui-20261025-v20-nuance/font-map.json').read_text('utf-8-sig'))['mapping']; oldinv = {v: k for k, v in oldmap.items()}
assert all(newmap[k] == v for k, v in oldmap.items())
kn = lambda s: ''.join(newinv.get(c, c) for c in (s or '')); ko = lambda s: ''.join(oldinv.get(c, c) for c in (s or ''))
F = [json.loads(l) for l in open(RV / '검수확정_번역필드.jsonl', encoding='utf-8') if l.strip()]
want = {o['id']: o['ko'] for o in F if o['translator_model'] != 'source retained'}
orig = payload(C / 'research/disc/scenario.arc'); fin = payload(FINAL / 'scenario.arc'); new = payload(OUT / 'scenario.arc')
assert set(fin) == set(new)
st = collections.Counter(); bad = []
for s in sorted(new):
    if fin[s] == new[s]: st['entries_identical'] += 1; continue
    try:
        oi = b.decode(orig[s])[0].instructions; fi = b.decode(fin[s])[0].instructions; ni = b.decode(new[s])[0].instructions
    except UnicodeDecodeError:
        # cp949 문자열이 든 설정 스크립트: 글꼴 이름(같은 길이)만 바뀌었는지 바이트로 본다
        import struct as _st
        from mjotool.crypt import crypt32
        d0, d1 = fin[s], new[s]; cnt = _st.unpack_from('<I', d0, 24)[0]; off = 32 + cnt * 8
        c0, c1 = crypt32(d0[off:]), crypt32(d1[off:])
        assert len(c0) == len(c1) and d0[:off] == d1[:off]
        REN = json.loads((OUT / 'build-proof.json').read_text('utf-8'))['font_rename']['renames']
        for x, y in REN.items():
            c0 = c0.replace(x.encode('cp932'), y.encode('cp932'))
        assert c0 == c1, s
        st['cp949_rename_only'] += 1; continue
    assert [x.opcode.mnemonic for x in fi] == [x.opcode.mnemonic for x in ni], s
    ot = [i for i, x in enumerate(oi) if x.opcode.mnemonic == 'text']; nt = [i for i, x in enumerate(ni) if x.opcode.mnemonic == 'text']
    tmap = dict(zip(ot, nt))
    targets = {}
    for i, j in tmap.items():
        fid = f'{s}::{i:06d}'
        if fid in want: targets[j] = want[fid]
    # 최신판 대비 바뀐 명령이 모두 확정본 칸인지
    for j, (x, y) in enumerate(zip(fi, ni)):
        if x.string != y.string:
            if y.opcode.mnemonic == 'text':
                if j not in targets: bad.append((s, j, 'unexpected text change')); continue
            elif y.opcode.mnemonic == 'ldstr': st['ldstr_changed'] += 1; continue
            else: bad.append((s, j, 'non-string change'))
        if x.offset != y.offset: st['offset_moved'] += 1
    for j, t in targets.items():
        if kn(ni[j].string) != t: bad.append((s, j, 'text mismatch'))
        else: st['text_ok'] += 1
    # 분기 대상이 같은 명령을 가리키는지(번호 기준)
    fo = {x.offset: k for k, x in enumerate(fi)}; no = {x.offset: k for k, x in enumerate(ni)}
    for x, y in zip(fi, ni):
        if x.opcode.encoding == 'j':
            if fo[x.offset + x.size + x.jump_offset] != no[y.offset + y.size + y.jump_offset]: bad.append((s, 'jump'))
            else: st['jumps_ok'] += 1
print(dict(st), 'bad', len(bad), bad[:5])
# 확정본 칸 중 빌드에 반영 안 된 text 칸
miss = 0
for s in {k.split('::')[0] for k in want}:
    oi = b.decode(orig[s])[0].instructions; ni = b.decode(new[s])[0].instructions
    ot = [i for i, x in enumerate(oi) if x.opcode.mnemonic == 'text']; nt = [i for i, x in enumerate(ni) if x.opcode.mnemonic == 'text']
    tm = dict(zip(ot, nt))
    for i in ot:
        fid = f'{s}::{i:06d}'
        if fid in want and kn(ni[tm[i]].string) != want[fid]: miss += 1
print('text fields not matching', miss)
# 지도
m = parse(OUT / 'storymap.bin'); m0 = parse(FINAL / 'storymap.bin')
print('map nodes', len(m['nodes']), 'text changed', sum(1 for x, y in zip(m['nodes'], m0['nodes']) if x['text'] != y['text']))
kana = [n['id'] for n in m['nodes'] if re.search('[\u3041-\u3096\u30a1-\u30fa]', n['text'])]
print('map nodes with kana', len(kana), kana[:3])
# 지도 문장 표본이 대본과 맞는지: 한 줄짜리 대사 노드 200개
import random
random.seed(1); ok = tot = 0
idx = {f"{o['id'].split('::')[0][:-4]}:{int(o['id'].split('::')[1])}": o['ko'] for o in F}
for n in random.sample([n for n in m['nodes'] if n['kind'] == 0], 3000):
    if n['id'] in idx and len(idx[n['id']]) > 6:
        tot += 1; ok += idx[n['id']].replace('　', ' ').strip()[:10] in (n['speaker'] + ' ' + n['text'])
    if tot >= 200: break
print('map sample nodes containing their field text', ok, '/', tot)
