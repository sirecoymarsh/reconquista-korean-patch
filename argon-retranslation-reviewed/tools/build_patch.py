# 반입 빌드: 확정본(검수확정_번역필드.jsonl)을 최신판(runtime-final-20261028) 위에 얹는다.
#  1) 글꼴 대응표 확장(v20 font-map 1,400칸 그대로 + 새 글자)  2) 글꼴 4벌에 새 칸만 덧붙임
#  3) scenario.arc 의 해당 text/ldstr 명령 문자열만 교체(분기 재배치는 build_trial._rewrite 검증)
#  4) storymap.bin 의 표시 문장만 재생성(구조·좌표 그대로, repair_text.py 의 page/preview 규칙)
# 출력: results_reviewed_20261121/build-20261121/  (원본·게임 폴더는 읽기만)
import sys, json, copy, re, struct, hashlib, collections, difflib, io
from pathlib import Path
sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); from common import *
C = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타'); R = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024')
sys.path.insert(0, str(C / 'tools')); sys.path.insert(0, str(R / 'tools'))
import build_trial as b
from inspect_majiro import Arc
from read_storymap import parse
from fontTools.ttLib import TTFont

FINAL = R / 'runtime-final-20261028'
OUT = RV / 'build-20261121'; (OUT / 'font').mkdir(parents=True, exist_ok=True)
FIELDS = RV / '검수확정_번역필드.jsonl'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
shab = lambda d: hashlib.sha256(d).hexdigest()
load = lambda p: json.loads(Path(p).read_text('utf-8-sig'))
def payload(p):
    a = Arc(p); raw = Path(p).read_bytes(); return a, {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}
proof = {'translator_model': 'gemini-4-argon + antigravity-hybrid, reviewed by Claude (Opus 5.5)', 'fields_file': str(FIELDS), 'fields_sha256': sha(FIELDS),
         'base_runtime': str(FINAL), 'base_scenario_sha256': sha(FINAL / 'scenario.arc'), 'base_storymap_sha256': sha(FINAL / 'storymap.bin')}
assert proof['base_scenario_sha256'] == '072aa90cf29801d3d4a53cc67f37eafbcbc8699298518b2dba3c62a15bacaf8c'

F = [json.loads(l) for l in open(FIELDS, encoding='utf-8') if l.strip()]
F = [o for o in F if o['translator_model'] != 'source retained']   # 기호뿐인 칸은 최신판 글 그대로

# ---------------------------------------------------------------- 1) 대응표
oldmap = load(C / 'builds/body-ui-20261025-v20-nuance/font-map.json')['mapping']
oldinv = {v: k for k, v in oldmap.items()}
def cp932_ok(ch):
    try: return ch.encode('cp932').decode('cp932') == ch
    except UnicodeError: return False
needed = set()
for o in F:
    for ch in o['ko']:
        if ch in oldmap: continue
        if '\uac00' <= ch <= '\ud7a3' or not cp932_ok(ch): needed.add(ch)
# 11-21 고정: 숨은 시험 3회차를 통과한 판(466b5524)의 덧붙인 95자를 늘 넣는다 — 일상어 되돌림으로 안 쓰게 된 글자가 생겨도
#        대응표·글꼴·글꼴 이름이 그 판과 같게 유지된다(안 쓰는 칸은 해가 없다)
PIN = RV / 'build-20261121' / 'prev-95' / 'font-map.json'
if PIN.exists(): needed |= set(load(PIN)['added'])
_, fin = payload(FINAL / 'scenario.arc')
used = set()
with open(C / 'localization/catalog/catalog.jsonl', encoding='utf-8') as f:
    for line in f: used.update(json.loads(line)['source'])
for p in (C / 'research/extracted/fastdata').glob('*.cfg'): used.update(p.read_bytes().decode('cp932'))
for p in (C / 'research/extracted/scenario').glob('*.csv'): used.update(p.read_bytes().decode('cp932'))
for name, data in fin.items():                      # 최신판 대본에 문자 그대로 들어 있는 글자
    if not name.endswith('.mjo'): continue
    try: ins_ = b.decode(data)[0].instructions
    except UnicodeDecodeError: continue       # cp949 진단 문자열이 든 UI 스크립트(본문 아님)
    for x in ins_:
        if x.string: used.update(x.string)
for o in F: used.update(o['ko'])                      # 새 번역에 한자로 쓰인 글자(紅葉 등)
occupied = set(oldmap.values())
cands = []
for lead in list(range(0xe0, 0xf0)) + list(range(0x88, 0xa0)):
    for trail in range(0x40, 0xfd):
        if trail == 0x7f: continue
        bb = bytes([lead, trail])
        try: ch = bb.decode('cp932')
        except UnicodeError: continue
        if len(ch) == 1 and '\u3400' <= ch <= '\u9fff' and ch.encode('cp932') == bb and ch not in used and ch not in occupied: cands.append(ch)
newmap = dict(oldmap)
for ch in sorted(needed): newmap[ch] = cands.pop(0)
assert len(set(newmap.values())) == len(newmap) and not (set(newmap.values()) - occupied) & used
newinv = {v: k for k, v in newmap.items()}
(OUT / 'font-map.json').write_text(json.dumps({'translator_model': 'Codex internal (v20 map) + Claude extension 2026-11-21', 'algorithm': 'v20 font-map 1,400 slots unchanged; new Korean syllables and non-CP932 characters appended to unused round-trip CP932 CJK (lead E0-EF, 88-9F), excluding every literal character of the catalogue, cfg/csv, final scenario strings and new Korean text', 'mapping': newmap, 'remaining_safe_slots': len(cands), 'added': {c: newmap[c] for c in sorted(needed)}}, ensure_ascii=False, indent=1), 'utf-8')
proof['font_map'] = {'prior_slots_preserved': len(oldmap), 'added': len(needed), 'total': len(newmap), 'remaining_safe_slots': len(cands), 'sha256': sha(OUT / 'font-map.json')}
def enc(s):
    t = ''.join(newmap.get(c, c) for c in s); assert ''.join(newinv.get(c, c) for c in t) == s, s; t.encode('cp932'); return t
ko_old = lambda s: ''.join(oldinv.get(c, c) for c in (s or ''))
ko_new = lambda s: ''.join(newinv.get(c, c) for c in (s or ''))

# ---------------------------------------------------------------- 2) 글꼴 4벌
fontproof = []
add = {ord(newmap[c]): c for c in needed}
for fn in ['ReconquistaKR.otf', 'ReconquistaKRSerif.otf', 'ReconquistaKRLarge.otf', 'ReconquistaKRSerifLarge.otf']:
    src = FINAL / 'font' / fn
    font = TTFont(src, recalcTimestamp=False)
    cm = font.getBestCmap(); expected = {}
    for code, hangul in add.items():
        g = cm.get(ord(hangul)); assert g and g != '.notdef', (fn, hangul)
        expected[code] = g
    for t in font['cmap'].tables:
        if t.isUnicode(): t.cmap.update(expected)
    font.save(OUT / 'font' / fn)
    a0 = TTFont(src, recalcTimestamp=False); a1 = TTFont(OUT / 'font' / fn, recalcTimestamp=False)
    c0, c1 = a0.getBestCmap(), a1.getBestCmap()
    assert all(c1[k] == v for k, v in expected.items())
    assert all(c1.get(k) == v for k, v in c0.items() if k not in expected)          # 기존 칸 그대로
    assert all(c0.get(ord(h)) == c1.get(ord(newmap[h])) for h in oldmap)                # 기존 한글 칸 그대로
    other = sorted(set(a0.reader.keys()) - {'cmap', 'head'})
    same = [t for t in other if a0.reader[t] == a1.reader[t]]
    hd0, hd1 = bytearray(a0.reader['head']), bytearray(a1.reader['head']); hd0[8:12] = hd1[8:12] = b'\0\0\0\0'
    assert same == other and hd0 == hd1, (fn, set(other) - set(same))
    fontproof.append({'font': fn, 'source_sha256': sha(src), 'output_sha256': sha(OUT / 'font' / fn), 'added_cmap_entries': len(expected),
                      'other_tables_byte_identical': len(other), 'head_identical_except_checksum': True})
proof['fonts'] = fontproof

# ---------------------------------------------------------------- 3) 대본
_, orig = payload(C / 'research/disc/scenario.arc')
snap = load(C / 'translation/integration/nuance-20261025-v1/integrated-targets.json')
v20inline = {r['id']: r['target'] for r in snap['inline_records']}
by_script = collections.defaultdict(list)
for o in F: by_script[o['id'].split('::')[0]].append(o)
MANUAL = {}   # 정렬로 못 찾은 ldstr: 아래에서 문맥으로 찾는다
arc_a, finp = payload(FINAL / 'scenario.arc')
newp = dict(finp); sproof = []; stat = collections.Counter(); mism = []
for s, rows in sorted(by_script.items()):
    oi = b.decode(orig[s])[0].instructions; fi = b.decode(finp[s])[0].instructions
    ot = [i for i, x in enumerate(oi) if x.opcode.mnemonic == 'text']; ft = [i for i, x in enumerate(fi) if x.opcode.mnemonic == 'text']
    assert len(ot) == len(ft), s
    tmap = dict(zip(ot, ft))
    oseq = [(i, x.string) for i, x in enumerate(oi) if x.opcode.mnemonic == 'ldstr']
    fseq = [(i, ko_old(x.string)) for i, x in enumerate(fi) if x.opcode.mnemonic == 'ldstr']
    exp = [v20inline.get(f'{s}::{i:06d}', st) for i, st in oseq]
    sm = difflib.SequenceMatcher(None, exp, [t for _, t in fseq], autojunk=False)
    lmap = {}
    for a, bb, n in sm.get_matching_blocks():
        for k in range(n): lmap[oseq[a + k][0]] = fseq[bb + k][0]
    repl = {}
    for o in rows:
        i = int(o['id'].split('::')[1]); kind = oi[i].opcode.mnemonic
        if kind == 'text': j = tmap[i]
        elif kind == 'ldstr':
            j = lmap.get(i)
            if j is None:
                # 앞뒤 text 명령(최신판 위치가 정해진 닻) 사이의 ldstr 개수가 같으면 자리 순서로 맞춘다
                pt = max(k for k in range(0, i) if oi[k].opcode.mnemonic == 'text')
                nt = next(k for k in range(i + 1, len(oi)) if oi[k].opcode.mnemonic == 'text')
                lo = [k for k in range(pt + 1, nt) if oi[k].opcode.mnemonic == 'ldstr']
                lf = [k for k in range(tmap[pt] + 1, tmap[nt]) if fi[k].opcode.mnemonic == 'ldstr']
                assert len(lo) == len(lf), (o['id'], len(lo), len(lf))
                j = lf[lo.index(i)]
                MANUAL[o['id']] = {'final_index': j, 'final_string': ko_old(fi[j].string), 'source': oi[i].string, 'method': 'same ldstr count between the neighbouring mapped text opcodes; matched by position'}
            stat['ldstr'] += 1
        else: raise SystemExit((o['id'], kind))
        assert fi[j].opcode.mnemonic == kind
        new = enc(o['ko'])
        if fi[j].string == new: stat['same'] += 1; continue
        repl[j] = b.string_ins(kind, new); stat['replaced_' + kind] += 1
    if not repl: continue
    data, p = b._rewrite(finp[s], repl)
    ns = b.decode(data)[0].instructions
    assert len(ns) == len(fi) and all(x.opcode.mnemonic == y.opcode.mnemonic for x, y in zip(ns, fi))
    for j, rb in repl.items(): assert b.string_ins(ns[j].opcode.mnemonic, ns[j].string) == rb
    for j, (x, y) in enumerate(zip(fi, ns)):
        if j not in repl and x.opcode.mnemonic in ('text', 'ldstr', 'ctrl'): assert x.string == y.string, (s, j)
    newp[s] = data; sproof.append({'entry': s, 'replaced': len(repl), 'relocated_jumps': p['relocated_jumps'], 'relocated_switch_cases': p['relocated_switch_cases'], 'output_sha256': p['output_sha256']})
# 11-22: 진엔딩 곡 장면 멈춤(ED 자막 스레드 wait(-2))·가사 24·32줄 끝·maho_13 callp 선택 빨리 감기 — 지도 프로젝트 공용 뒷손질(다시 돌려도 같음)
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools'); import scenario_postfix
proof['scenario_postfix'] = scenario_postfix.postfix_payload(newp)
blob = arc_a.rebuild(newp); (OUT / 'scenario.arc').write_bytes(blob)
_, back = payload(OUT / 'scenario.arc'); assert back == newp
assert arc_a.rebuild(finp) == (FINAL / 'scenario.arc').read_bytes()
proof['scenario'] = {'sha256': sha(OUT / 'scenario.arc'), 'changed_entries': len(sproof), 'unchanged_entries_byte_identical': len(finp) - len(sproof), 'counts': dict(stat), 'manual_ldstr': MANUAL, 'entries': sproof}

# ---------------------------------------------------------------- 4) 이야기 지도
_, v13 = payload(C / 'builds/body-ui-20261023-v13-config/scenario.arc')
names = load(C / 'translation/integration/recovery-full-20261023-v1/names.json')['mapping']
audit = load(R / 'qa/final-audit-20261028/text-audit.json')
heldnodes = {x['id'] for x in audit['storymap_kana_nodes'] if x['id'].startswith(('masa_15:', 'masa_16:'))}
newko = {o['id']: o['ko'] for o in F}

def mk_name(ko):
    def name(t):
        for mark in ['＠', '（', '／']:
            if mark in t: t = t[:t.index(mark)]
        for a, z in [('[', ']'), ('［', '］')]:
            if a in t: t = t[t.index(a) + 1:][:99]
            if z in t: t = t[:t.index(z)]
        return ko(names.get(t, t))
    return name

def page(ins, start, ko, fix=True):
    name = mk_name(ko)
    if fix:
        while start > 0:
            j = start - 1
            while j >= 0 and ins[j].opcode.mnemonic == 'line': j -= 1
            if j < 0 or ins[j].opcode.mnemonic not in ('call', 'callp') or ins[j].hash not in (0x3198fd01, 0x2f93f26a): break
            need = 2 if ins[j].hash == 0x3198fd01 else 1; k = j - 1
            for _ in range(need):
                while k >= 0 and ins[k].opcode.mnemonic == 'line': k -= 1
                assert k >= 0 and ins[k].opcode.mnemonic == 'ldstr'; k -= 1
            before = k
            while before >= 0 and ins[before].opcode.mnemonic == 'line': before -= 1
            assert before >= 0 and ins[before].opcode.mnemonic == 'ctrl' and ins[before].string == 'w'
            start = k + 1
    fields = []
    for j in range(start, len(ins)):
        x = ins[j]; mn = x.opcode.mnemonic
        if mn == 'text': fields.append((j, x.string or ''))
        elif fix and mn in ('call', 'callp') and x.hash in (0x3198fd01, 0x2f93f26a):
            argc = 2 if x.hash == 0x3198fd01 else 1; args = []; k = j - 1
            while k >= 0 and len(args) < argc:
                q = ins[k]
                if q.opcode.mnemonic == 'line': k -= 1; continue
                assert q.opcode.mnemonic == 'ldstr'; args.insert(0, q.string or ''); k -= 1
            if argc == 1: value = args[0]
            else:
                reading, base = args; value = base
                if ko(reading).strip() and ko(reading).strip() != ko(base).strip() and not re.fullmatch(r'[・·.．…、 ]+', ko(reading)): value = base + '〔' + reading + '〕'
            fields.append((j, value))
        elif mn == 'ctrl' and x.string == 'w': break
        elif mn == 'ctrl' and x.string == 'n': fields.append((-1, '\n'))
        elif mn in ('ret', 'br', 'brfalse', 'brtrue', 'br.case', 'bne.case') or (mn == 'syscallp' and x.hash == 0x718ef651): break
    real = [t for i, t in fields if t != '\n']; sp = ''; body = list(fields)
    if len(real) >= 2 and real[1].startswith('「') and not real[0].startswith('「') and (not fix or ins[next(i for i, t in fields if t != '\n')].opcode.mnemonic == 'text'):
        sp = name(real[0]); k = next(k for k, (i, t) in enumerate(body) if t == real[0]); body = body[k + 1:]
    chunks = []
    for k, (i, t) in enumerate(body):
        nxt = next((v for _, v in body[k + 1:] if v != '\n'), '')
        if t == '\n': chunks.append(' ')
        elif fix and not t.startswith('「') and nxt.startswith('「') and (t in names or any(x in t for x in ['＠', '（', '／'])): chunks.append((name(t).strip() + ' ') if name(t).strip() else '')
        else: chunks.append(ko(t))
    return sp, re.sub(r'\s+', ' ', ''.join(chunks).replace('　', ' ')).strip()

def preview(ins, i, ko, fix=True):
    name = mk_name(ko); parts = []
    for j in range(i, min(i + 12, len(ins))):
        x = ins[j]
        if x.opcode.mnemonic != 'text': continue
        t = x.string or ''; k = j + 1
        while k < len(ins) and ins[k].opcode.mnemonic == 'line': k += 1
        if fix and k < len(ins) and ins[k].opcode.mnemonic == 'text' and (ins[k].string or '').startswith('「'): t = name(t)
        parts.append(ko(t))
    return ' '.join(parts).replace('＠', ' · ')[:85]

map0 = parse(FINAL / 'storymap.bin'); m = copy.deepcopy(map0); mapchanges = collections.Counter(); oldins = {}; newins = {}
for ch in m['chapters']:
    n = ch['id'] + '.mjo'
    s0 = b.decode(v13[n])[0].instructions; oldins[n] = s0
    s1 = []
    for j, x in enumerate(s0):
        fid = f'{n}::{j:06d}'
        if fid in newko and x.opcode.mnemonic in ('text', 'ldstr'):
            y = copy.copy(x); y.string = enc(newko[fid]); s1.append(y)
        else:
            s1.append(x)   # 옛 대응표 칸은 새 대응표에서도 같은 칸이므로 ko_new 로 그대로 읽힌다
    newins[n] = s1
for n, n0 in zip(m['nodes'], map0['nodes']):
    if n['kind'] != 0 or n['id'] in heldnodes: continue
    cn = m['chapters'][n['chapter']]['id'] + '.mjo'; start = int(n['id'].split(':')[1])
    o_sp, o_t = page(oldins[cn], start, ko_old); n_sp, n_t = page(newins[cn], start, ko_new)
    if (n_sp, n_t) != (o_sp, o_t):
        n['speaker'] = n_sp; n['text'] = n_t; mapchanges['body'] += 1
    po = preview(oldins[cn], start, ko_old); pn = preview(newins[cn], start, ko_new)
    if pn != po:
        if n_t != o_t and any(x.opcode.mnemonic in ('call', 'callp') and x.hash in (0x3198fd01, 0x2f93f26a) for x in newins[cn][max(0, start - 4):min(start + 12, len(newins[cn]))]):
            pn = ((n_sp + ' ' + n_t).strip() if n_sp else n_t)[:85]
        if n['preview'] != pn: n['preview'] = pn; mapchanges['preview'] += 1
for sc, oldsc in zip(m['scenes'], map0['scenes']):
    n0 = map0['nodes'][sc['first']]; n = m['nodes'][sc['first']]
    if n0['kind'] != 0 or not n0['text']:
        ix = next((i for i, z in enumerate(map0['nodes']) if z['chapter'] == sc['chapter'] and z['order'] - 1 >= sc['first'] and z['kind'] == 0), None)
        if ix is None: continue
        n0 = map0['nodes'][ix]; n = m['nodes'][ix]
    oldsn = ((n0['speaker'] + ' ' + n0['text']).strip() if n0['speaker'] else n0['text'])[:120]
    newsn = ((n['speaker'] + ' ' + n['text']).strip() if n['speaker'] else n['text'])[:120]
    if oldsc['snippet'] == oldsn and oldsn != newsn: sc['snippet'] = newsn; mapchanges['scene_snippet'] += 1

def pack(d):
    out = bytearray(b'RKSM0002')
    def ints(*v): out.extend(struct.pack('<' + 'i' * len(v), *v))
    def txt(t): v = t.encode('utf-8'); ints(len(v)); out.extend(v)
    ints(len(d['info']), len(d['chapters']), len(d['nodes']), len(d['edges']), len(d['sels']), *d['roots'])
    for x in d['info']: ints(*x)
    for x in d['chapters']: txt(x['id']); txt(x['group']); txt(x['label'])
    for x in d['nodes']: ints(x['chapter'], x['gid'], x['kind'], x['order']); txt(x['id']); txt(x['label']); txt(x['preview'])
    for x in d['edges']: ints(*x)
    for g, default, pairs in d['sels']:
        ints(g, default, len(pairs))
        for p in pairs: ints(*p)
    ints(len(d['scenes']))
    for s in d['scenes']: ints(s['chapter'], s['first'], s['count'], s['pages'], s['choices'], s['views']); txt(s['bg']); txt(s['snippet'])
    for n in d['nodes']: ints(n['scene'], n['value'], n['owner']); txt(n['speaker']); txt(n['text'])
    for x in d['chapters']: ints(x['page'], *x['rect'], x['day'], x['scene0'], x['scenes']); txt(x['cell']); txt(x['extra']); txt(x['title'])
    ints(len(d['deco']))
    for x in d['deco']: ints(x['page'], x['kind'], *x['rect'], x['color']); txt(x['main']); txt(x['sub'])
    return bytes(out) + b'RKSMEND!'
assert pack(map0) == (FINAL / 'storymap.bin').read_bytes()
(OUT / 'storymap.bin').write_bytes(pack(m)); assert parse(OUT / 'storymap.bin') == m
for k in ['roots', 'info', 'chapters', 'edges', 'sels', 'deco']: assert m[k] == map0[k]
for x, y in zip(m['nodes'], map0['nodes']): assert {k: v for k, v in x.items() if k not in ['text', 'speaker', 'preview']} == {k: v for k, v in y.items() if k not in ['text', 'speaker', 'preview']}
residual = [n['id'] for n in m['nodes'] if n['id'] not in heldnodes and re.search('[\u3041-\u3096\u30a1-\u30fa]', n['text'])]
residual0 = [n['id'] for n in map0['nodes'] if n['id'] not in heldnodes and re.search('[\u3041-\u3096\u30a1-\u30fa]', n['text'])]
proof['storymap'] = {'sha256': sha(OUT / 'storymap.bin'), 'changes': dict(mapchanges), 'graph_ids_and_geometry_unchanged': True, 'roundtrip_exact': True,
                     'held_nodes_unchanged': len(heldnodes), 'residual_kana_nodes_outside_held': len(residual), 'residual_kana_nodes_before': len(residual0)}
(OUT / 'build-proof.json').write_text(json.dumps(proof, ensure_ascii=False, indent=1), 'utf-8')
print(json.dumps({k: (v if k not in ('scenario',) else {kk: vv for kk, vv in v.items() if kk != 'entries'}) for k, v in proof.items()}, ensure_ascii=False, indent=1)[:4000])
