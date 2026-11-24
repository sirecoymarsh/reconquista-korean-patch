"""「지도」 button on the text box's button row (11-25, the user: 「연표 옆에 이야기 지도 버튼을 추가하는게 좋겠네」).

Over the 연표 tab there is no room the game draws: it copies the text box art from y 454 down (sysdata.cfg CONALL) and
the button art from x 286, y 450 (BUTALL). So the button goes at the row's left end, right before 「퀵 저장」, the same
plate as the row's buttons:
- art: console_{off,on,push}_{m,h,k,e,s,t}.rct and their _.rc8 masks (fastdata.arc) and their 4x (hires): the 퀵 저장
  plate from Codex's clean (letter-free) frames (candidates/ui-completion-v1/clean) copied 50 px left, 「지도」 set as Codex
  set the row (ui-completion-v1/build.py: NotoSansCJKkr 9 px x4 in [x+3,568,45,12], stroke 2 (20,12,19,235), colour
  by state);
- sysdata.cfg BUTALL 286,450,514,150 -> 236,450,564,150, so the hover and press art (cut from there) holds it;
- console.mjo: an areaevent_set for button 11 at 250,563,51,39 after the 연표's (the same handlers);
- the DLL opens the story map when $click@CONSOLE writes @ret 11 (ReconquistaHD.cpp MapTabPressed).

python build_map_tab.py <source runtime> <out>                build from a runtime (its fastdata, scenario, hires)
python build_map_tab.py <source runtime> <out> <target>       and put it into <target> (its own fastdata keeps its env)
"""
import json
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
BUTALL = (b'286, 450, 514, 150', b'236, 450, 564, 150')
AREA_10 = 0x09ba9                # console.mjo: the 연표's areaevent_set, the new one goes after it
COLOR = {'off': (255, 244, 232, 255), 'on': (255, 255, 230, 255), 'push': (255, 209, 151, 255)}
STATES, CODES = ('off', 'on', 'push'), ('m', 'h', 'k', 'e', 's', 't')


def key(name):
    return f'{zlib.crc32(name.lower().encode("cp932")):08x}'


def arc_payload(path):
    a = core.Arc(path)
    raw = a.path.read_bytes()
    return a, {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}


def ink(state):
    """「지도」 at 4x on a transparent 3200x2400 layer, as Codex set the row's labels."""
    layer = Image.new('RGBA', (3200, 2400))
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(str(FONT), round(9 * 4))
    x, y, w, h = BUTTON[0] + 3, 568, 45, 12
    d.text(((x + w / 2) * 4, (y + h / 2) * 4), '지도', font=f, anchor='mm', fill=COLOR[state], stroke_width=2, stroke_fill=(20, 12, 19, 235))
    return layer


def build(src, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'payloads').mkdir(exist_ok=True)
    (out / 'hd').mkdir(exist_ok=True)
    _, P = arc_payload(src / 'fastdata.arc')
    x, y, w, h = SRC
    nx = x + DX
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
            clean = np.asarray(Image.open(CLEAN / (n + '.png')).convert('RGB'))
            cmatte = np.asarray(Image.open(CLEAN / (n + '.matte.png')))
            region = (slice(y - m, y + h + m), slice(x - m, x + w + m))
            plate = Image.fromarray(clean[region]).convert('RGBA')
            plate.putalpha(Image.fromarray(255 - cmatte[region]))
            plate4 = plate.resize((plate.width * 4, plate.height * 4), Image.Resampling.LANCZOS).crop((m * 4, m * 4, (m + w) * 4, (m + h) * 4))
            box4 = (nx * 4, y * 4, (nx + w) * 4, (y + h) * 4)
            ink4 = layer.crop(box4)
            colour4 = Image.alpha_composite(plate4.convert('RGB').convert('RGBA'), ink4).convert('RGB')
            a4 = np.asarray(ink4.getchannel('A')).astype(float)
            matte4 = np.rint((255 - np.asarray(plate4.getchannel('A')).astype(float)) * (255 - a4) / 255).clip(0, 255).astype(np.uint8)
            low = np.asarray(colour4.resize((w, h), Image.Resampling.LANCZOS))
            a1 = np.asarray(ink4.getchannel('A').resize((w, h), Image.Resampling.LANCZOS)).astype(float)
            m1 = np.rint(cmatte[y:y + h, x:x + w].astype(float) * (255 - a1) / 255).clip(0, 255).astype(np.uint8)
            rgb2 = rgb.copy()
            rgb2[y:y + h, nx:nx + w] = low
            matte2 = matte.copy()
            matte2[y:y + h, nx:nx + w] = m1
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
    s, raw = core.b.decode(S['console.mjo'])
    at = next(i for i, x in enumerate(s.instructions) if x.offset == AREA_10)
    assert s.instructions[at].opcode.mnemonic == 'syscallp'
    bx, by, bw, bh = BUTTON
    extra = b''.join(core.const(v) for v in (0xe9da3d95 - (1 << 32), 0xedf9e430 - (1 << 32), 0x5438644d, bh, bw, by, bx, 11)) + core.syscall(0xf8d18340, 8)
    ins = s.instructions[at]
    (out / 'console.mjo').write_bytes(core.rewrite(S['console.mjo'], {at: raw[ins.offset:ins.offset + ins.size] + extra}, {}, {}))
    (out / 'scenario.arc.source').write_text(str(src / 'scenario.arc'), 'utf-8')
    (out / 'manifest.json').write_text(json.dumps({'entries': record, 'button': BUTTON, 'butall': BUTALL[1].decode(), 'area_id': 11}, ensure_ascii=False, indent=1), 'utf-8')
    print('built', len(record), 'frames ->', out)


def apply(dst, out):
    """Into <dst>: its own fastdata.arc with the payloads, scenario.arc rebuilt from the build's source with the new
    console.mjo (both written as new files, never through a hard link), and the 4x pngs (their jxl copies removed)."""
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
    for p in (out / 'hd').iterdir():
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
