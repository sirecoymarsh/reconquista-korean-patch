"""Pictures and layout for the new 연표 prototype (native/chronicle_proto.inc), from the mock-up (chronicle_mockup.py):
the background, the people's strips and the open panel, the date plates, a hidden-event plate, and one small picture per
event cell at its final size (143 of them, as when everything is opened: the worst case for opening and scrolling).
The event cells sit where the 연표's own table has them; their pictures are the 도입부 1 scenes the user has seen, in turn;
the date labels and the panel text are stand-ins (the prototype measures drawing, it shows no story).
python chronicle_proto_assets.py   -> build/chronicle-proto/ (PNG/JPEG + layout.txt)
"""
import csv, io, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chronicle_mockup as K
import make_runtime as M

OUT = M.BUILD / 'chronicle-proto'
OUT.mkdir(parents=True, exist_ok=True)
COLW, ROWH, HEAD = 226, 182, 380
CW, CH = COLW - 12, ROWH - 12
TW, TH = CW - 8, CH - 8          # an event picture inside its cell


def save(im, name, q=None):
    p = OUT / name
    if q:
        im.convert('RGB').save(p, quality=q, subsampling=0)
    else:
        im.save(p)
    return p


def main():
    # the table's shape: CSV row 0 people, column 0 dates, row 1 the date column's caption; events where a cell has text
    core = M.core
    arc = core.Arc(M.BUILD / 'scenario.arc')
    raw = arc.path.read_bytes()
    def rows_of(name):
        e = next(e for e in arc.entries if e['name'] == name)
        return list(csv.reader(io.StringIO(raw[e['offset']:e['offset'] + e['size']].decode('cp932'))))
    table, links = rows_of('ホラー年表改.csv'), rows_of('exec_ホラー年表改.csv')
    data = table[2:]
    events = [(r, c) for r, row in enumerate(data) for c in range(12) if c + 1 < len(row) and row[c + 1].strip()]
    linked = {(r, c) for r, row in enumerate(links[2:]) for c in range(12) if c + 1 < len(row) and row[c + 1].strip()}
    blocks, start = [], 0
    for r, row in enumerate(data):
        if r and row[0].strip():
            blocks.append((start, r - start))
            start = r
    blocks.append((start, len(data) - start))
    # stand-in labels: N일 전 counting down, with weekdays (the real ones say how far back each block is)
    days = '월화수목금토일'
    lines = [f'G {len(data)} 12']
    for i, (r0, n) in enumerate(blocks):
        lines.append(f'D {r0} {n} {len(blocks) - i}일 전|{days[(i * 3) % 7]}')
    # pictures: the opening scenes, cut to the cell's shape (4:3 trimmed at the sides)
    scenes = ['383d51d4', 'c12e54c8', 'ae35ac32', 'e9d6589f', '9bc77d33', '13fbdc59', 'f0dddea4', 'b77da474', '8a1d8dc4', '1d530f9d', 'dc6707e3', '2a76e09c', 'bce46b87']
    small = []
    for k in scenes:
        im = K.picture(k)
        w = int(im.height * TW / TH)
        x0 = (im.width - w) // 2
        small.append(im.crop((x0, 0, x0 + w, im.height)).resize((TW, TH), Image.LANCZOS))
    for i, (r, c) in enumerate(events):
        save(small[i % len(small)], f't{i:03d}.jpg', q=92)
        lines.append(f'E {r} {c} {i} {int((r, c) in linked)} {int(i % 23 == 0)}')
    # people: two met (모미지 open in the mock-up, 마사키), the rest hidden
    momi = K.sprite('df814e2c', '95098e0a')
    masa = K.sprite('ef61881b', '2d84cbc3')
    lines += ['P 2 모미지 momi', 'P 8 마사키 masa']
    for key, sp, (fx, fy) in (('momi', momi, (980, 300)), ('masa', masa, (1000, 330))):
        crop = sp.crop((fx - 300, fy - 260, fx + 300, fy + 900)).resize((int((COLW - 6) * 1.9), int(HEAD * 2.0)), Image.LANCZOS)
        layer = Image.new('RGBA', (COLW - 6, HEAD), (0, 0, 0, 0))
        layer.paste(crop, ((COLW - 6 - crop.width) // 2, -40), crop)
        a = np.asarray(layer).astype(np.float32)
        a[..., :3] *= .55
        a[..., 3] *= .9
        save(Image.fromarray(a.astype(np.uint8)), f'strip_face_{key}.png')
        bust = sp.crop((fx - 380, fy - 330, fx + 380, fy + 980)).resize((int(760 * .43), int(1310 * .43)), Image.LANCZOS)
        a = np.asarray(bust).astype(np.float32)
        a[..., 3] *= np.clip(np.arange(bust.width) / 120.0, 0, 1)[None, :]
        save(Image.fromarray(a.astype(np.uint8)), f'bust_{key}.png')
    # plates and the background, as the mock-up draws them
    save(K.background(), 'bg.jpg', q=90)
    save(K.plate((COLW - 6, HEAD), fill=(30, 11, 16), border=(120, 96, 96), border_w=2, seed=10), 'strip.png')
    save(K.plate((5 * COLW - 6, HEAD), fill=(46, 13, 22), glow=True, seed=99), 'panel.png')
    save(K.plate((CW - 10, CH - 10), fill=(58, 24, 30), border=(96, 62, 66), border_w=2, seed=5), 'hidden.png')
    for n in range(1, 9):
        save(K.plate((380, n * ROWH - 8), fill=(24, 8, 12), border=(176, 150, 120), border_w=3, seed=n), f'date{n}.png')
    em = K.plate((380, 380), fill=(40, 12, 18), glow=True, seed=1)
    ed = ImageDraw.Draw(em)
    ed.line((14, 14, 366, 366), fill=K.SILVER, width=4)
    for r, col in ((48, (60, 10, 20)), (40, (150, 24, 44)), (26, (210, 60, 80)), (12, (255, 170, 180))):
        ed.ellipse((190 - r, 190 - r, 190 + r, 190 + r), fill=col)
    ed.ellipse((142, 142, 238, 238), outline=K.SILVER, width=4)
    f = K.font(K.SERIF_L, 92)
    ed.text((346, 40), '인물', font=f, fill=K.INK, anchor='ra')
    ed.text((34, 340), '날짜', font=f, fill=K.INK, anchor='ld')
    save(em, 'corner.png')
    for label in ('새 항목 찾기', '추가 이야기 찾기', '도움말', '닫기'):
        pass   # buttons: plates drawn with their label at run time (button.png stretched)
    save(K.plate((300, 96), fill=(92, 22, 36), border=(214, 186, 176), border_w=3, seed=4), 'button.png')
    (OUT / 'layout.txt').write_text('\n'.join(lines) + '\n', 'utf-8')
    total = sum(p.stat().st_size for p in OUT.iterdir())
    print(f'events {len(events)} linked {len(linked & set(events))} rows {len(data)} blocks {len(blocks)} files {len(list(OUT.iterdir()))} bytes {total}')


if __name__ == '__main__':
    main()
