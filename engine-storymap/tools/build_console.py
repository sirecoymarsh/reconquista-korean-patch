"""The text box (console): its 「지도」 button and its 「빈 칸 저장」 case.

「빈 칸 저장」 (11-25, the user's standard: S saves at once to the next empty slot): console.mjo's pause loop gets a case 12
before the 퀵 저장's case 8, written as that case is (the save info, the 저장할 수 없습니다 check), with the save menu's own
numbering (loadsave.mjo: page p from 1 to $f68bcd63, slot i under $b51b948b, the save number p*100+1+i, the last slot of
a page the auto save's while $30b6a7d9) and its sound and voice; the first number whose $get_save_info$ is empty is
saved, then 「p쪽 i번째 칸에 저장했습니다」 (or 「빈 칸이 없습니다」). The DLL's S key chooses case 12 (ReconquistaHD.cpp
ConsoleKey).

console.mjo's code keeps every offset it had: two 6-byte ldc.i are each replaced by a br of the same size into code
appended after the file's last instruction, which does what they did and jumps back; patch_console checks every other
byte. (11-25: a save made before the change, loaded on a build that had inserted code, loaded fine, so this is not what
an old save needs; it keeps the original script as it was, which is the simpler thing to reason about.)

「지도」 button on the text box's button row (11-25, the user: 「연표 옆에 이야기 지도 버튼을 추가하는게 좋겠네」).

Over the 연표 tab there is no room the game draws: it copies the text box art from y 454 down (sysdata.cfg CONALL) and
the button art from x 286, y 450 (BUTALL). So the button goes at the row's left end, right before 「퀵 저장」, the same
plate as the row's buttons:
- art: console_{off,on,push}_{m,h,k,e,s,t}.rct and their _.rc8 masks (fastdata.arc) and their 4x (hires): the 퀵 저장
  plate from Codex's clean (letter-free) frames (candidates/ui-completion-v1/clean) copied 50 px left;
- every label of the row set again with its key (11-25, the user: 「하단 메뉴 바 아이콘들에 괄호치고 영어 단축키도 넣어줘.
  지금은 단축키가 존재한다는 사실을 알 수가 없어」), as Codex set the row (ui-completion-v1/build.py: the clean frame
  made 4x, NotoSansCJKkr 9 px x4 in [x+3,568,45,12], smaller by 0.25 px until it fits, stroke 2 (20,12,19,235), colour
  by state); 1x is the 4x made small, as Codex's;
- sysdata.cfg BUTALL 286,450,514,150 -> 236,450,564,150, so the hover and press art (cut from there) holds it;
- console.mjo: an areaevent_set for button 11 at 250,563,51,39 after the 연표's (the same handlers), in appended code;
- the DLL opens the story map when $click@CONSOLE writes @ret 11 (ReconquistaHD.cpp MapTabPressed).

python build_console.py <source runtime> <out>                build from a runtime (its fastdata, scenario, hires)
python build_console.py <source runtime> <out> <target>       and put it into <target> (its own fastdata keeps its env)
"""
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_runtime as M  # noqa: E402

core = M.core
CODEX = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타')
sys.path.insert(0, str(CODEX / 'ui-opening-ending' / 'tools'))
from raster_codec import raw_image, encode_array  # noqa: E402

CLEAN = CODEX / 'candidates' / 'ui-completion-v1' / 'clean'
FONT = CODEX / 'research' / 'fonts' / 'NotoSansCJKkr-Regular.otf'
SRC = (296, 558, 55, 32)         # the 퀵 저장 plate with its pointed left end (x, y, w, h)
DX = -50                         # the 지도 plate one button to the left
BUTTON = (250, 563, 51, 39)      # its area, as sysdata.cfg's BUT* rows
ROW = (246, 558, 460, 32)        # the row's plates, 지도's to 설정's (x, y, w, h)
LABELS = [(250, '지도(M)'), (300, '퀵 저장(Q)'), (350, '퀵 로드(W)'), (400, '저장(S)'), (450, '불러오기(L)'),
          (501, '건너뛰기(Ctrl)'), (551, '자동(A)'), (601, '기록(PgUp)'), (651, '설정(Esc)')]   # the buttons' x (sysdata.cfg BUT*)
BUTALL = (b'286, 450, 514, 150', b'236, 450, 564, 150')
AREA_10 = 0x09ba3                # console.mjo: the 연표's areaevent_set's last argument (ldc.i 10), then the call (8 bytes)
COLOR = {'off': (255, 244, 232, 255), 'on': (255, 255, 230, 255), 'push': (255, 209, 151, 255)}
STATES, CODES = ('off', 'on', 'push'), ('m', 'h', 'k', 'e', 's', 't')


HANGUL = json.loads((CODEX / 'translation' / 'hangul-cp932-map.json').read_text('utf-8'))['mapping']
CASE_8 = 0x0cea3                 # console.mjo: the 퀵 저장 case's ldc.i 8 (its bne.case follows); case 12 is tried first
CASES_END = 0x0d0d2              # where every case of that loop ends (its line before the loop's back jump)
PAUSE_LOOP = 0xbd66              # that function; its locals 1, 2, 3 (ints) are unused, case 12 takes them
P, I, N = 1, 2, 3


def text(s):
    b = ''.join(HANGUL.get(c, c) for c in s).encode('cp932') + b'\0'
    return core.b.op('ldstr') + struct.pack('<H', len(b)) + b


def var(op, scope, h, index=-1):
    """ld / st.i of an int: savefile 0x20, persistent 0x00, local 0x60 (its index)."""
    return core.b.op(op) + struct.pack('<HIh', scope, h, index)


def local(op, index):
    return var(op, 0x60, zlib.crc32({P: '_p@', I: '_i@', N: '_n@'}[index].encode()), index)


def call(h, n):
    return core.b.op('callp') + struct.pack('<IIH', h, 0, n)


def op(*names):
    return b''.join(core.b.op(n) for n in names)


class Code:
    """Instructions with labels; jumps are 6 bytes (opcode, int32 from the jump's end)."""
    def __init__(self):
        self.parts = []

    def __call__(self, *chunks):
        self.parts.extend(chunks)
        return self

    def label(self, name):
        self.parts.append(('label', name))
        return self

    def jump(self, mnemonic, target):
        self.parts.append(('jump', mnemonic, target))
        return self

    def labels(self, origin):
        pos, at = origin, {}
        for p in self.parts:
            if isinstance(p, tuple) and p[0] == 'label':
                at[p[1]] = pos
            else:
                pos += 6 if isinstance(p, tuple) else len(p)
        return at, pos

    def build(self, origin, outside):
        """The code placed at offset origin; outside: label -> offset elsewhere in the file."""
        at, end = self.labels(origin)
        at.update(outside)
        out = b''
        for p in self.parts:
            if isinstance(p, tuple) and p[0] == 'jump':
                out += core.b.op(p[1]) + struct.pack('<i', at[p[2]] - (origin + len(out) + 6))
            elif not isinstance(p, tuple):
                out += p
        assert origin + len(out) == end
        return out


def save_case(c):
    """case 12, entered from CASE_8's place; 'next' does that ldc.i 8 and goes on to case 8's bne.case."""
    pages, slots, auto = (var('ld', 0x00, h) for h in (0xf68bcd63, 0xb51b948b, 0x30b6a7d9))
    c(core.const(12)).jump('bne.case', 'next')
    c(call(0x73099731, 0))                                                  # the save info, as case 8
    c(core.syscall(0x4ffab7c4, 0, True)).jump('brfalse', 'free')            # $is_save_menu_disable
    c(text('저장할 수 없습니다'), call(0xe72d9f52, 1)).jump('br', 'end')     # $message@MSG_BOX
    c.label('free')(core.const(1), local('st.i', P), op('pop'))
    c.label('page')(local('ld', P), pages, op('cle.i')).jump('brfalse', 'full')
    c(core.const(0), local('st.i', I), op('pop'))
    c.label('slot')(local('ld', I), slots, op('clt.i')).jump('brfalse', 'next_page')
    c(auto, local('ld', I), slots, core.const(1), op('sub.i', 'ceq.i', 'andl')).jump('brtrue', 'next_slot')
    c(local('ld', P), core.const(100), op('mul.i'), core.const(1), op('add.i'), local('ld', I), op('add.i'), local('st.i', N), op('pop'))
    c(local('ld', N), core.syscall(0x65075141, 1, True), text(''), op('ceq.s')).jump('brfalse', 'next_slot')   # $get_save_info$
    c(text('save'), core.syscall(0xed84e320, 1))                            # $sound3, as the save menu
    c(local('ld', N), core.syscall(0x89018dd1, 1))                          # $do_save
    c(text('save'), call(0x0bcee4d0, 1))                                    # $guide_voice@KOEKOE
    c(local('ld', P), core.syscall(0x6f769889, 1, True), text('쪽 '), op('add.s'),
      local('ld', I), core.const(1), op('add.i'), core.syscall(0x6f769889, 1, True), op('add.s'),
      text('번째 칸에 저장했습니다'), op('add.s'), call(0xe72d9f52, 1)).jump('br', 'end')
    c.label('next_slot')(local('ld', I), core.const(1), op('add.i'), local('st.i', I), op('pop')).jump('br', 'slot')
    c.label('next_page')(local('ld', P), core.const(1), op('add.i'), local('st.i', P), op('pop')).jump('br', 'page')
    c.label('full')(text('빈 칸이 없습니다'), call(0xe72d9f52, 1)).jump('br', 'end')
    c.label('next')(core.const(8)).jump('br', 'case_8')


def map_area(c):
    """the 연표's areaevent_set as it was, then button 11's; back to after the old call."""
    bx, by, bw, bh = BUTTON
    c(core.const(10), core.syscall(0xf8d18340, 8))
    c(*(core.const(v) for v in (0xe9da3d95 - (1 << 32), 0xedf9e430 - (1 << 32), 0x5438644d, bh, bw, by, bx, 11)), core.syscall(0xf8d18340, 8))
    c.jump('br', 'after_area')


def patch_console(source):
    """console.mjo with the two entries (a br over a 6-byte ldc.i) and the appended code; every other byte as it was."""
    s, raw = core.b.decode(source)
    at = {x.offset: x for x in s.instructions}
    assert raw[AREA_10:AREA_10 + 6] == core.const(10) and raw[AREA_10 + 6:AREA_10 + 14] == core.syscall(0xf8d18340, 8)
    assert raw[CASE_8:CASE_8 + 6] == core.const(8) and at[CASE_8 + 6].opcode.mnemonic == 'bne.case'
    assert CASES_END in at
    free_locals(s, raw)
    end = s.bytecode_size
    c = Code().label('area')
    map_area(c)
    c.label('save')
    save_case(c)
    tail = c.build(end, {'after_area': AREA_10 + 14, 'case_8': CASE_8 + 6, 'end': CASES_END})
    where, _ = c.labels(end)
    code = bytearray(raw)
    for place, label in ((AREA_10, 'area'), (CASE_8, 'save')):
        code[place:place + 6] = Code().jump('br', label).build(place, {label: where[label]})
    code += tail
    head = bytearray(source[:s.bytecode_offset])
    struct.pack_into('<I', head, len(head) - 4, len(code))
    out = bytes(head) + (core.b.crypt32(bytes(code)) if s.signature == s.SIGNATURE_ENCRYPTED else bytes(code))
    s2, raw2 = core.b.decode(out)
    assert bytes(raw2) == bytes(code)
    changed = [i for i in range(end) if raw2[i] != raw[i]]
    assert all(AREA_10 <= i < AREA_10 + 6 or CASE_8 <= i < CASE_8 + 6 for i in changed), changed[:8]
    bounds = {x.offset for x in s2.instructions} | {len(raw2)}
    assert {x.offset for x in s.instructions} <= bounds
    for x in s2.instructions:
        if x.opcode.encoding == 'j':
            assert x.offset + x.size + x.jump_offset in bounds, hex(x.offset)
    return out


def free_locals(s, raw):
    """The pause loop's locals P, I, N are used nowhere in it (its instructions up to the next function)."""
    end = min((f.offset for f in s.functions if f.offset > PAUSE_LOOP), default=s.bytecode_size)
    for x in s.instructions:
        if PAUSE_LOOP <= x.offset < end and x.opcode.mnemonic in ('ld', 'st.i', 'st.s', 'ldelem') and x.size >= 10:
            scope, _, index = struct.unpack_from('<HIh', raw, x.offset + 2)
            assert not (scope & 0x60 == 0x60 and index in (P, I, N)), hex(x.offset)


def key(name):
    return f'{zlib.crc32(name.lower().encode("cp932")):08x}'


def arc_payload(path):
    a = core.Arc(path)
    raw = a.path.read_bytes()
    return a, {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}


def ink(state):
    """the row's labels at 4x on a transparent 3200x2400 layer, as Codex set them"""
    layer = Image.new('RGBA', (3200, 2400))
    d = ImageDraw.Draw(layer)
    for bx, label in LABELS:
        x, y, w, h = bx + 3, 568, 45, 12
        size = 9.0
        while True:
            f = ImageFont.truetype(str(FONT), round(size * 4))
            if d.textbbox((0, 0), label, font=f)[2] <= w * 4 - 8 or size <= 7:
                break
            size -= .25
        d.text(((x + w / 2) * 4, (y + h / 2) * 4), label, font=f, anchor='mm', fill=COLOR[state], stroke_width=2, stroke_fill=(20, 12, 19, 235))
        box = d.textbbox(((x + w / 2) * 4, (y + h / 2) * 4), label, font=f, anchor='mm', stroke_width=2)
        assert x * 4 <= box[0] and box[2] <= (x + w) * 4, (label, size, box)
    return layer


def build(src, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'payloads').mkdir(exist_ok=True)
    (out / 'hd').mkdir(exist_ok=True)
    _, P = arc_payload(src / 'fastdata.arc')
    x, y, w, h = SRC
    rx, ry, rw, rh = ROW
    m = 2                                                   # a margin for the 4x resample, cropped off again
    record = []
    for st in STATES:
        layer = ink(st)
        for code in CODES:
            n = f'console_{st}_{code}.rct'
            mn = n[:-4] + '_.rc8'
            rgb, pre, ch = raw_image(P[n])
            mi, mp, mc = raw_image(P[mn])
            pal = np.frombuffer(mp[20:788], np.uint8).reshape(256, 3)
            inv = np.empty(256, np.uint8)
            inv[pal[:, 0]] = np.arange(256, dtype=np.uint8)
            matte = pal[mi, 0].copy()                       # 0 opaque .. 255 clear
            clean = np.asarray(Image.open(CLEAN / (n + '.png')).convert('RGB')).copy()
            cmatte = np.asarray(Image.open(CLEAN / (n + '.matte.png'))).copy()
            clean[y:y + h, x + DX:x + DX + w] = clean[y:y + h, x:x + w].copy()     # the 지도 plate
            cmatte[y:y + h, x + DX:x + DX + w] = cmatte[y:y + h, x:x + w].copy()
            region = (slice(ry - m, ry + rh + m), slice(rx - m, rx + rw + m))
            plate = Image.fromarray(clean[region]).convert('RGBA')
            plate.putalpha(Image.fromarray(255 - cmatte[region]))
            plate4 = plate.resize((plate.width * 4, plate.height * 4), Image.Resampling.LANCZOS).crop((m * 4, m * 4, (m + rw) * 4, (m + rh) * 4))
            box4 = (rx * 4, ry * 4, (rx + rw) * 4, (ry + rh) * 4)
            ink4 = layer.crop(box4)
            colour4 = Image.alpha_composite(plate4.convert('RGB').convert('RGBA'), ink4).convert('RGB')
            a4 = np.asarray(ink4.getchannel('A')).astype(float)
            matte4 = np.rint((255 - np.asarray(plate4.getchannel('A')).astype(float)) * (255 - a4) / 255).clip(0, 255).astype(np.uint8)
            low = np.asarray(colour4.resize((rw, rh), Image.Resampling.LANCZOS))
            a1 = np.asarray(ink4.getchannel('A').resize((rw, rh), Image.Resampling.LANCZOS)).astype(float)
            m1 = np.rint(cmatte[ry:ry + rh, rx:rx + rw].astype(float) * (255 - a1) / 255).clip(0, 255).astype(np.uint8)
            rgb2 = rgb.copy()
            rgb2[ry:ry + rh, rx:rx + rw] = low
            matte2 = matte.copy()
            matte2[ry:ry + rh, rx:rx + rw] = m1
            ob = encode_array(rgb2, pre, ch)
            back, _, _ = raw_image(ob)
            assert np.array_equal(back, rgb2)
            (out / 'payloads' / n).write_bytes(ob)
            (out / 'payloads' / mn).write_bytes(encode_array(inv[matte2], mp, mc))
            for name, part, mode in ((n, np.asarray(colour4), 'RGB'), (mn, matte4, 'L')):
                k = key(name)
                arr = np.asarray(Image.open(src / 'hires' / f'{k}.png').convert(mode)).copy()
                arr[box4[1]:box4[3], box4[0]:box4[2]] = part
                Image.fromarray(arr).save(out / 'hd' / f'{k}.png')
            record.append({'entry': n, 'mask': mn, 'colour_key': key(n), 'mask_key': key(mn)})
    cfg = P['sysdata.cfg']
    assert cfg.count(BUTALL[0]) == 1
    (out / 'payloads' / 'sysdata.cfg').write_bytes(cfg.replace(BUTALL[0], BUTALL[1]))
    _, S = arc_payload(src / 'scenario.arc')
    (out / 'console.mjo').write_bytes(patch_console(S['console.mjo']))
    (out / 'scenario.arc.source').write_text(str(src / 'scenario.arc'), 'utf-8')
    (out / 'manifest.json').write_text(json.dumps({'entries': record, 'button': BUTTON, 'butall': BUTALL[1].decode(), 'area_id': 11, 'save_case': 12, 'labels': LABELS}, ensure_ascii=False, indent=1), 'utf-8')
    print('built', len(record), 'frames ->', out)


def apply(dst, out):
    """Into <dst>: its own fastdata.arc with the payloads, scenario.arc rebuilt from the build's source with the new
    console.mjo (both written as new files, never through a hard link), and, where it has 4K art (a hires folder), the 4x
    pngs (their jxl copies removed)."""
    a, P = arc_payload(dst / 'fastdata.arc')
    for p in (out / 'payloads').iterdir():
        P[p.name] = p.read_bytes()
    data = a.rebuild(P)
    (dst / 'fastdata.arc').unlink()
    (dst / 'fastdata.arc').write_bytes(data)
    a, S = arc_payload(Path((out / 'scenario.arc.source').read_text('utf-8')))
    S['console.mjo'] = (out / 'console.mjo').read_bytes()
    data = a.rebuild(S)
    (dst / 'scenario.arc').unlink()
    (dst / 'scenario.arc').write_bytes(data)
    for p in (out / 'hd').iterdir() if (dst / 'hires').is_dir() else ():
        for q in (dst / 'hires-jxl' / f'{p.stem}.jxl', dst / 'hires' / p.name):
            if q.exists():
                q.unlink()
        (dst / 'hires' / p.name).write_bytes(p.read_bytes())
    print('applied to', dst)


if __name__ == '__main__':
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    build(src, out)
    if len(sys.argv) > 3:
        apply(Path(sys.argv[3]), out)
