"""Build the 이야기 지도 runtime data: scenario.arc (position tracking ungated) and storymap.bin (RKSM0002).

python build_storymap.py [--gated]   ->  build/scenario.arc, build/storymap.bin, build/build-proof.json

--gated reproduces Codex's ingame-flowchart-v1 scenario exactly (byte check against v18) before the real build.
The real build differs in two rules: the virtual 'here' write at every catalogue node / visual point runs
in normal play too (Codex gated it to fast review replay; the DLL uses it for 지금 자리 and 읽음), and the
chronicle reads its cells as open while 모든 콘텐츠 개방 is on (review_chronicle).
"""
import collections
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

import codex_model as CM

core = CM.core
CODEX = CM.CODEX
sys.path.insert(0, str(CODEX / 'candidates' / 'ingame-flowchart-v1'))
import build_data as BD  # noqa: E402  (Codex builder: functions + virtual hashes only; main() not called)

b = core.b
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / 'build'
OUT.mkdir(exist_ok=True)
REF = HERE / 'ref'
V18 = CODEX / 'runtime-body-ui-20261024-v18-cg-switch'
NORMAL = CODEX / 'runtime-body-ui-20261023-v16-ui-rest'
BASE = CODEX / 'builds' / 'body-ui-20261023-v13-config'
DISP_BACK = 0xa4eb1e4c
CHRONICLE_TABLE = 0xaa2e632d                  # chronicle.mjo's cell table: bit 0 hidden, bit 1 link locked (3 at first open)
CHRONICLE_REVEAL = {0x15636109, 0xb2ae7021}   # the chronicle functions the story calls to open cells (&= 6 / &= 4)
REVIEW_CHRONICLE = zlib.crc32(b'#kr_review_chronicle@CHRONICLE')   # virtual in the DLL: ~3 while 모든 콘텐츠 개방 is on, else -1


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ----------------------------------------------------------------------------- scenario (Codex rules)

def build_scenario(m, cat, gated):
    arc = core.Arc(NORMAL / 'scenario.arc')
    araw = arc.path.read_bytes()
    payload = {e['name']: araw[e['offset']:e['offset'] + e['size']] for e in arc.entries}
    for n in m.s:
        assert payload[n + '.mjo'] == m.payload[n + '.mjo'], n
    positions = list(m.parent)
    gid = {p: i for i, p in enumerate(positions)}
    nodes = {gid[(x['chapter'], x['index'])] for x in cat['nodes']}
    V = BD.V
    for n, s in m.s.items():
        repl, insert, branches, raw = {}, {}, {}, m.raw[n]
        for i, x in enumerate(s.instructions):
            typ = x.opcode.mnemonic
            orig = raw[x.offset:x.offset + x.size]
            g = gid.get((n, i))
            if typ in ['text', 'proc', 'ctrl']:
                repl[i] = core.gate(orig, b'')
            elif typ in ['callp', 'syscallp'] and x.hash in core.SKIP:
                repl[i] = core.gate(orig, b.op('pop') * x.argument_count)
            elif typ == 'call' and x.hash == core.SELECT:
                repl[i] = core.gate(orig, b.op('pop') * x.argument_count + BD.query('selection', g))
            elif typ == 'call' and x.hash == 0xeed07382:
                mconsole = b.string_ins('ldstr', 'console_on_m') + b.string_ins('ldstr', 'console_off_m') + core.call(0x1558c5f5, 2)
                sconsole = b.string_ins('ldstr', 'console_on_s') + b.string_ins('ldstr', 'console_off_s') + core.call(0x1558c5f5, 2)
                alt = (b.op('pop') * x.argument_count + BD.query('selection', g) + b.op('brfalse') + struct.pack('<i', len(sconsole) + 6)
                       + sconsole + b.op('br') + struct.pack('<i', len(mconsole)) + mconsole + core.var(V['selection']))
                repl[i] = core.gate(orig, alt)
            if g is not None:
                if g in nodes or x.hash == DISP_BACK:
                    here = core.put(V['here'], g)
                    insert[i] = core.gate(b'', here) if gated else here
                if typ in ['brfalse', 'brtrue', 'bne.case']:
                    branches[i] = g
        payload[n + '.mjo'] = BD.dynamic_rewrite(payload[n + '.mjo'], repl, insert, branches)
    for n in ['pic', 'transit', 'transit_top', 'yazlib']:
        s, raw = b.decode(payload[n + '.mjo'])
        repl = {}
        for i, x in enumerate(s.instructions):
            orig = raw[x.offset:x.offset + x.size]
            if x.opcode.mnemonic == 'syscall' and x.hash == 0xa62aa5eb:
                repl[i] = core.gate(orig, core.const(1))
            elif x.opcode.mnemonic == 'syscallp' and x.hash == 0xcf35f0e3:
                repl[i] = core.gate(orig, b.op('pop') * x.argument_count)
        if repl:
            payload[n + '.mjo'] = core.rewrite(payload[n + '.mjo'], repl, {}, {})
    s, _ = b.decode(payload['start.mjo'])
    anchor = next(i for i, x in enumerate(s.instructions) if x.offset >= s.main_offset and x.opcode.mnemonic == 'alloca') + 1
    boot = core.put(core.FAST, 2) + core.put(core.MARK, 0) + core.syscall(0x4d849aa6) + core.syscall(0x1bb47604) + b.string_ins('ldstr', 'FLOW_REVIEW') + core.syscall(0xf8004993, 1)
    for j, root in enumerate(core.ROOTS):
        con = 'h' if j == 1 else 'm'
        code = b.string_ins('ldstr', 'console_on_' + con) + b.string_ins('ldstr', 'console_off_' + con) + core.call(0x1558c5f5, 2) + b.string_ins('ldstr', root) + core.syscall(core.EXEC, 1)
        boot += core.var(V['root' + str(j)]) + b.op('brfalse') + struct.pack('<i', len(code)) + code
    ins = core.var(V['active']) + b.op('brfalse') + struct.pack('<i', len(boot)) + boot
    payload['start.mjo'] = core.rewrite(payload['start.mjo'], {}, {anchor: ins}, {})
    if not gated:
        payload['chronicle.mjo'] = review_chronicle(payload['chronicle.mjo'])
    # 11-22: ED 가사 자막 스레드 멈춤(wait(-2)→wait(16))·가사 24·32줄 끝 시각·maho_13 callp 선택 빨리 감기 — 다시 빌드해도 되돌아가지 않게
    import scenario_postfix
    print('scenario_postfix', scenario_postfix.postfix_payload(payload, set(m.s)))
    return arc.rebuild(payload)


def review_chronicle(data):
    """With 모든 콘텐츠 개방 on, the chronicle draws and clicks every cell as open: each of its 8 display reads of the cell
    table is ANDed with the DLL's mask. The saved table is never written, and the reveal functions keep their raw reads,
    so the story still opens cells and shows its 'new event' notice as before."""
    s, raw = b.decode(data)
    starts = sorted((f.offset, f.name_hash) for f in s.functions)
    owner = lambda off: max((p for p in starts if p[0] <= off), default=(0, 0))[1]  # noqa: E731
    repl = {i: raw[x.offset:x.offset + x.size] + core.var(REVIEW_CHRONICLE) + b.op('and') for i, x in enumerate(s.instructions)
            if x.opcode.mnemonic == 'ldelem' and x.hash == CHRONICLE_TABLE and owner(x.offset) not in CHRONICLE_REVEAL}
    assert len(repl) == 8, len(repl)
    return core.rewrite(data, repl, {}, {})


# ----------------------------------------------------------------------------- v1 catalogue blob (same bytes as Codex)

def v1_blob(m, cat):
    positions = list(m.parent)
    gid = {p: i for i, p in enumerate(positions)}
    chap = {x['id']: i for i, x in enumerate(cat['chapters'])}
    info, select = [], []
    for p in positions:
        n, i = p
        x = m.s[n].instructions[i]
        kind = x.opcode.mnemonic
        par = m.parent[p]
        branch = kind in ['brfalse', 'brtrue', 'bne.case']
        taken = gid.get((n, m.offsets[n].get(x.offset + x.size + x.jump_offset, -1)), -1) if branch else -1
        info.append((gid[par] if par else -1, gid.get((n, i + 1), -1), taken, 1 if x.hash == DISP_BACK else 0))
        if kind == 'call' and x.hash in [core.SELECT, 0xeed07382]:
            pairs, began = [], False
            for j in range(i + 1, len(m.s[n].instructions)):
                y = m.s[n].instructions[j]
                if y.opcode.mnemonic == 'br.case':
                    if began:
                        break
                    began = True
                if began and y.opcode.mnemonic == 'bne.case' and (n, j) in gid:
                    pairs.append((gid[n, j], m.s[n].instructions[j - 1].int_value))
            select.append((gid[p], 1 if x.hash == core.SELECT else 0, pairs))
    roots = [gid[n, m.offsets[n][m.s[n].main_offset]] for n in core.ROOTS]
    out = bytearray()

    def ints(*v):
        out.extend(struct.pack('<' + 'i' * len(v), *v))

    def txt(v):
        data = v.encode('utf8')
        ints(len(data))
        out.extend(data)
    ints(len(info), len(cat['chapters']), len(cat['nodes']), len(cat['edges']), len(select), *roots)
    for row in info:
        ints(*row)
    for row in cat['chapters']:
        txt(row['id']); txt(row['group']); txt(row['label'])
    types = {'page': 0, 'choice': 1, 'branch': 2, 'view': 3}
    for row in cat['nodes']:
        ints(chap[row['chapter']], gid[row['chapter'], row['index']], types[row['kind']], row['order'])
        txt(row['id']); txt(row['label']); txt(row['preview'])
    for e in cat['edges']:
        ints(chap[e['from']], chap[e['to']])
    for g, default, pairs in select:
        ints(g, default, len(pairs))
        for pair in pairs:
            ints(*pair)
    return bytes(out), gid


# ----------------------------------------------------------------------------- text, speakers, scenes

def load_json(p):
    return json.loads(Path(p).read_text('utf-8-sig'))


INVERSE = {v: k for k, v in load_json(BASE / 'font-map.json')['mapping'].items()}
NAMES = load_json(CODEX / 'translation' / 'integration' / 'recovery-full-20261023-v1' / 'names.json')['mapping']


def ko(s):
    return ''.join(INVERSE.get(c, c) for c in s)


def fixname(t):
    """console.mjo _fixname: what the name plate actually shows."""
    for mark in ('＠', '（', '／'):
        if mark in t:
            t = t[:t.index(mark)]
    for left, right in (('[', ']'), ('［', '］')):
        if left in t:
            t = t[t.index(left) + 1:][:99]
        if right in t:
            t = t[:t.index(right)]
    return t


def speaker_display(token):
    t = fixname(token)
    return ko(NAMES.get(t, t))


def page_text(ins, i):
    """Speaker and body of the message that starts at instruction i (until ctrl w)."""
    texts = []
    j = i
    while j < len(ins):
        x = ins[j]
        mn = x.opcode.mnemonic
        if mn == 'text':
            texts.append(x.string or '')
        elif mn == 'ctrl' and x.string == 'w':
            break
        elif mn == 'ctrl' and x.string == 'n':
            texts.append('\n')
        elif mn in ('ret', 'br', 'brfalse', 'brtrue', 'br.case', 'bne.case') or (mn == 'syscallp' and x.hash == core.EXEC):
            break
        j += 1
    speaker = ''
    body = [t for t in texts]
    real = [t for t in body if t != '\n']
    if len(real) >= 2 and real[1].startswith('「') and not real[0].startswith('「'):
        speaker = speaker_display(real[0])
        k = body.index(real[0])
        body = body[k + 1:]
    s = ''
    for t in body:
        if t == '\n':
            s += ' '
        else:
            s += ko(t)
    s = re.sub(r'\s+', ' ', s.replace('　', ' ')).strip()
    return speaker, s


def scenes_for(ins, nodes):
    """Fade-through-black scene split; returns per-node scene number (0-based) and scene rows."""
    bg_at = {}
    for i, x in enumerate(ins):
        if x.opcode.mnemonic == 'callp' and x.hash == DISP_BACK:
            for j in range(i - 1, max(-1, i - 4), -1):
                if ins[j].opcode.mnemonic == 'ldstr':
                    bg_at[i] = re.sub(r'\.(png|rct|bmp)$', '', ko(ins[j].string or ''), flags=re.I)
                    break
    points = sorted(bg_at)
    scenes, assign = [], {}
    faded, last_bg, last_plain, k = True, None, None, 0
    for n in nodes:
        new_after_fade = None
        while k < len(points) and points[k] <= n['index']:
            name = bg_at[points[k]]
            if name in ('black', 'white', 'red'):
                faded = True
            else:
                if faded:
                    new_after_fade = name
                faded = False
                last_bg = name
                if name.startswith('bg_'):
                    last_plain = name
            k += 1
        if not scenes or new_after_fade is not None:
            # thumbnail = latest plain background (event CGs never become thumbnails)
            scenes.append({'first': n['order'] - 1, 'bg': last_plain, 'pages': 0, 'choices': 0, 'views': 0, 'snippet': '', 'count': 0})
        sc = scenes[-1]
        if not sc['bg'] and last_plain:
            sc['bg'] = last_plain
        sc['count'] += 1
        assign[n['order'] - 1] = len(scenes) - 1
        if n['kind'] == 'page':
            sc['pages'] += 1
        elif n['kind'] == 'choice':
            sc['choices'] += 1
        elif n['kind'] == 'view':
            sc['views'] += 1
    return scenes, assign


# ----------------------------------------------------------------------------- map layout (same rules as mock_map.py)

GRID_X = [94, 260, 427, 594, 760]
BODY_TOP = 114
LV = 21
INTRO_TOP, INTRO_BOT = 114, 140
WEEK = ['수', '목', '금', '토', '일', '월', '화']
SAT, SUN, PLAIN = 0x58_8C_FF, 0xEE_34_3C, 0xD6_D4_DC
THREAD_CRIMSON, THREAD_NAVY = 0x8A_2C_3A, 0x44_52_9A


def weekday(d):
    return WEEK[(d - 1) % 7]


def wcolor(d):
    return SUN if weekday(d) == '일' else SAT if weekday(d) == '토' else PLAIN


def day_rows():
    y = {4: INTRO_BOT}
    y[5] = y[4] + 2 * LV
    y[6] = y[5] + 2 * LV
    for d in range(7, 21):
        y[d] = y[d - 1] + LV
    return y, y[20] + LV


def short_label(cid):
    tail = cid.split('_', 1)[1]
    if tail in ('ep', 'epi'):
        return '후일담'
    return tail.replace('_2ero', '-2').replace('_3', '-3').replace('_2', '-2')


ROUTE = {'kureha': ('쿠레하', 0), 'masa': ('마사키', 1), 'maho': ('마호코', 2), 'sina': ('시이나', 3)}


def layout(cat, days):
    """Cells (chapter rects per page) and decorations, in 1/10 game pixels."""
    cells, deco = {}, []
    y, body_bot = day_rows()

    def R(x0, y0, x1, y1):
        return [round(x0 * 10), round(y0 * 10), round(x1 * 10), round(y1 * 10)]

    def add_deco(page, kind, rect, main='', sub='', color=0):
        deco.append({'page': page, 'kind': kind, 'rect': R(*rect), 'main': main, 'sub': sub, 'color': color})
    # page 0 headers: crimson (Makino side) / navy (Shinya side)
    for k, name in enumerate(['쿠레하', '마사키', '마호코', '시이나']):
        x0, x1 = GRID_X[k], GRID_X[k + 1]
        w = min(150, x1 - x0 - 12)
        add_deco(0, 3 if k < 2 else 4, ((x0 + x1) / 2 - w / 2, 74.5, (x0 + x1) / 2 + w / 2, 110.5), name)
    # page 0 sheet rules
    for d in range(4, 21):
        add_deco(0, 0, (GRID_X[0], y[d], GRID_X[-1], y[d] + 0.5))
    add_deco(0, 0, (GRID_X[0], body_bot - 0.5, GRID_X[-1], body_bot))
    for x in GRID_X:
        add_deco(0, 0, (x, y[4], x + 0.5, body_bot))
    for k in range(4):
        cx = (GRID_X[k] + GRID_X[k + 1]) / 2
        add_deco(0, 6, (cx - 0.25, y[4], cx + 0.25, y[20]), color=THREAD_CRIMSON if k < 2 else THREAD_NAVY)   # dotted thread through days without a chapter
    # axis (both pages share the day rows)
    for page in (0, 1):
        for d in range(4, 20):
            h = 2 * LV if d in (4, 5) else LV
            add_deco(page, 1, (20, y[d], 92, y[d] + h), f'{d}일째', weekday(d), wcolor(d))
        add_deco(page, 2, (20, y[20], 92, y[20] + LV), '그 뒤')
    # page 0 cells
    third = (GRID_X[-1] - GRID_X[0]) / 3
    for k, cid in enumerate(['00_レコンキスタ_start', '00_レコンキスタ_start_2', '00_レコンキスタ_start_3']):
        d = k + 1
        cells[cid] = {'page': 0, 'rect': R(GRID_X[0] + k * third, INTRO_TOP, GRID_X[0] + (k + 1) * third, INTRO_BOT),
                      'label': f'도입부 {d}', 'extra': f'{d}일째 {weekday(d)}', 'title': f'도입부 {d}', 'day': d}
    cells['makino_kyoutu'] = {'page': 0, 'rect': R(GRID_X[0], y[4], GRID_X[2], y[5] + LV), 'label': '마키노 공통', 'extra': '4~5일째', 'title': '마키노 공통', 'day': 4}
    cells['shinya_kyoutu'] = {'page': 0, 'rect': R(GRID_X[2], y[4], GRID_X[4], y[4] + LV), 'label': '신야 공통', 'extra': '4일째', 'title': '신야 공통', 'day': 4}
    placed = collections.defaultdict(list)
    for ch in cat['chapters']:
        cid = ch['id']
        pre = cid.split('_', 1)[0]
        if pre not in ROUTE:
            continue
        day = 20 if cid.endswith(('_ep', '_epi')) else days[cid]['end']
        placed[(ROUTE[pre][1], day)].append(cid)
    for (ci, day), ids in placed.items():
        x0, x1 = GRID_X[ci], GRID_X[ci + 1]
        if day == 4:
            r = (x0, y[4] + LV, x1, y[5])
        elif day == 5 and ci in (0, 1):
            r = (x0, y[5] + LV, x1, y[6])
        else:
            r = (x0, y[day], x1, y[day] + (2 * LV if day == 5 else LV))
        ids.sort(key=lambda i: [int(p) if p.isdigit() else 0 for p in short_label(i).split('-')])
        seg = (r[2] - r[0]) / len(ids)
        for k, cid in enumerate(ids):
            name = ROUTE[cid.split('_', 1)[0]][0]
            lab = short_label(cid)
            cells[cid] = {'page': 0, 'rect': R(r[0] + k * seg, r[1], r[0] + (k + 1) * seg, r[3]), 'label': lab, 'extra': '',
                          'title': f'{name} {lab}', 'day': day if day <= 19 else 0}
    # page 1: 현재 on the day rows, 과거 evenly divided
    split = 470
    cols = [(GRID_X[0], split), (split + 16, GRID_X[-1])]
    for k, name in enumerate(['현재', '과거']):
        x0, x1 = cols[k]
        add_deco(1, 3, ((x0 + x1) / 2 - 75, 74.5, (x0 + x1) / 2 + 75, 110.5), name)
    x0, x1 = cols[0]
    for d in range(4, 21):
        add_deco(1, 0, (x0, y[d], x1, y[d] + 0.5))
    add_deco(1, 0, (x0, body_bot - 0.5, x1, body_bot))
    add_deco(1, 0, (x0, y[4], x0 + 0.5, body_bot))
    add_deco(1, 0, (x1, y[4], x1 + 0.5, body_bot))
    add_deco(1, 6, ((x0 + x1) / 2 - 0.25, INTRO_TOP, (x0 + x1) / 2 + 0.25, y[20]), color=THREAD_CRIMSON)
    for i in range(1, 17):
        cid = f'last_gendai{i:02d}'
        d = days[cid]['end']
        if d <= 3:
            r = (x0, INTRO_TOP, x1, INTRO_BOT)
        else:
            r = (x0, y[d], x1, y[d] + (2 * LV if d in (4, 5) else LV))
        cells[cid] = {'page': 1, 'rect': R(*r), 'label': f'현재 {i:02d}', 'extra': f'{d}일째 {weekday(d)}' if d <= 3 else '', 'title': f'최종편 현재 {i:02d}', 'day': d}
    cells['last_ep'] = {'page': 1, 'rect': R(x0, y[20], x1, y[20] + LV), 'label': '결말 후일담', 'extra': '', 'title': '최종편 결말 후일담', 'day': 0}
    px0, px1 = cols[1]
    add_deco(1, 5, (px0, INTRO_TOP, px1, INTRO_TOP + 18), '날짜 없이 이어지는 이야기')
    top = INTRO_TOP + 20
    hgt = (body_bot - top) / 12
    for i in range(1, 13):
        cells[f'last_kako{i:02d}'] = {'page': 1, 'rect': R(px0, top + (i - 1) * hgt, px1, top + i * hgt), 'label': f'과거 {i:02d}', 'extra': '', 'title': f'최종편 과거 {i:02d}', 'day': 0}
    assert len(cells) == len(cat['chapters']), (len(cells), len(cat['chapters']))
    return cells, deco


# ----------------------------------------------------------------------------- main

def main():
    gated = '--gated' in sys.argv
    m = CM.model()
    cat = core.load(CODEX / 'candidates' / 'flowchart-v1' / 'catalogue.json')
    assert m.catalogue() == cat
    arc = build_scenario(m, cat, gated)
    if gated:
        ok = arc == (V18 / 'scenario.arc').read_bytes()
        print(json.dumps({'gated_matches_v18_scenario': ok, 'bytes': len(arc)}))
        if not ok:
            raise SystemExit(1)
        return
    (OUT / 'scenario.arc').write_bytes(arc)
    blob, gid = v1_blob(m, cat)
    days = json.loads((REF / 'chapter_days.json').read_text('utf-8'))
    cells, deco = layout(cat, days)
    nodes_by_ch = collections.defaultdict(list)
    for n in cat['nodes']:
        nodes_by_ch[n['chapter']].append(n)
    node_extra = [None] * len(cat['nodes'])
    scene_rows = []
    chapter_scene_range = {}
    for ch in cat['chapters']:
        cid = ch['id']
        ins = m.s[cid].instructions
        ns = nodes_by_ch[cid]
        scenes, assign = scenes_for(ins, ns)
        base = len(scene_rows)
        for sc in scenes:
            first = cat['nodes'][sc['first']]
            spk, body = page_text(ins, first['index']) if first['kind'] == 'page' else ('', '')
            if not body:
                nxt = next((n for n in ns if n['order'] - 1 >= sc['first'] and n['kind'] == 'page'), None)
                if nxt:
                    spk, body = page_text(ins, nxt['index'])
            sc['snippet'] = (spk + ' ' + body).strip() if spk else body
            scene_rows.append({'chapter': cid, **sc})
        chapter_scene_range[cid] = (base, len(scene_rows))
        for n in ns:
            idx = n['order'] - 1
            value = -1
            if n['kind'] == 'page':
                spk, body = page_text(ins, n['index'])
            elif n['kind'] == 'choice':
                spk, body = '', n['label']
            elif n['kind'] == 'view':
                spk, body = '', '시점 전환'
            else:
                spk = ''
                mm = re.search(r'선택 (\d+)$', n['label'])
                if n['label'].startswith('시점 전환'):
                    body = '마키노 게이고' if n['label'].endswith('마키노') else '미사와 신야'
                    value = 0 if n['label'].endswith('마키노') else 1
                elif mm:
                    value = int(mm.group(1))
                    body = n['preview'] or f'선택 {value}'
                else:
                    cm = re.search(r'조건 (\d+) · 결과 (-?\d+)', n['label'])
                    value = int(cm.group(2)) if cm else -1
                    body = f'조건 갈림 {cm.group(1)} · {cm.group(2)}' if cm else n['label']
            node_extra[idx] = {'scene': base + assign[idx], 'value': value, 'speaker': spk, 'text': body,
                               'switch': n['switch'] or ''}
    # choice -> owning choice node index for branch rows
    by_id = {n['id']: n['order'] - 1 for n in cat['nodes']}
    out = bytearray(b'RKSM0002')
    out += blob

    def ints(*v):
        out.extend(struct.pack('<' + 'i' * len(v), *v))

    def txt(v):
        data = (v or '').encode('utf8')
        ints(len(data))
        out.extend(data)
    ints(len(scene_rows))
    for sc in scene_rows:
        ints([c['id'] for c in cat['chapters']].index(sc['chapter']), sc['first'], sc['count'], sc['pages'], sc['choices'], sc['views'])
        txt(sc['bg'] or ''); txt(sc['snippet'][:120])
    for idx, ex in enumerate(node_extra):
        owner = by_id.get(ex['switch'], -1) if ex['switch'] and ':condition:' not in ex['switch'] else -1
        ints(ex['scene'], ex['value'], owner)
        txt(ex['speaker']); txt(ex['text'])
    for ch in cat['chapters']:
        c = cells[ch['id']]
        a, z = chapter_scene_range[ch['id']]
        ints(c['page'], *c['rect'], c['day'], a, z - a)
        txt(c['label']); txt(c['extra']); txt(c['title'])
    ints(len(deco))
    for d in deco:
        ints(d['page'], d['kind'], *d['rect'], d['color'])
        txt(d['main']); txt(d['sub'])
    out += b'RKSMEND!'
    (OUT / 'storymap.bin').write_bytes(bytes(out))
    thumbs = sorted({sc['bg'] for sc in scene_rows if sc['bg']})
    proof = {'scenario_sha256': sha(OUT / 'scenario.arc'), 'v18_scenario_sha256': sha(V18 / 'scenario.arc'),
             'storymap_sha256': sha(OUT / 'storymap.bin'), 'bytes': len(out), 'scenes': len(scene_rows),
             'thumbnail_backgrounds': thumbs, 'rule_change': 'virtual here write ungated (normal play records position)',
             'catalogue_sha256': sha(CODEX / 'candidates' / 'flowchart-v1' / 'catalogue.json')}
    (OUT / 'build-proof.json').write_text(json.dumps(proof, ensure_ascii=False, indent=1), 'utf-8')
    # human check sample
    sample = [dict(order=n['order'], kind=n['kind'], **{k: node_extra[n['order'] - 1][k] for k in ('speaker', 'text', 'scene', 'value')})
              for n in cat['nodes'] if n['chapter'] == '00_レコンキスタ_start_2'][1280:1300]
    (OUT / 'sample-start2.json').write_text(json.dumps(sample, ensure_ascii=False, indent=1), 'utf-8')
    print(json.dumps({k: proof[k] for k in ('bytes', 'scenes', 'scenario_sha256')} | {'thumbs': len(thumbs)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
