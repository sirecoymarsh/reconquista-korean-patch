"""A still mock-up of the new 연표 (the user's model case, 10-26: people across, days down, a scene picture in each event
cell, the cursor column's person spread open, Reconquista colours, the wheel scrolls). 3200x2400 (4x the game's 800x600).
Only what the user has seen goes in (도입부 1: 모미지, 마키노, 마사키 and its opening scenes); the other people are hidden
as in the 연표 itself, and the event title and text in the open panel are marked as examples.
python chronicle_mockup.py [out.png]   -> qa/chronicle-mockup-v1.png
"""
import math, random, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'build' / 'pylib'))
import imagecodecs

RUN = HERE / 'runtime-play'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'qa' / 'chronicle-mockup-v1.png'
FONT = RUN / 'font'
SERIF, SERIF_L, SANS = FONT / 'ReconquistaKRSerif.otf', FONT / 'ReconquistaKRSerifLarge.otf', FONT / 'ReconquistaKR.otf'
W, H = 3200, 2400
INK = (236, 226, 214)          # warm white
DIM = (150, 128, 122)
SILVER = (196, 184, 178)
RED = (122, 22, 38)
DEEP = (40, 10, 16)


def font(path, px):
    return ImageFont.truetype(str(path), px)


def art(key):
    a = imagecodecs.jpegxl_decode((RUN / 'hires-jxl' / f'{key}.jxl').read_bytes())
    return a


def picture(key):
    a = art(key)
    return Image.fromarray(a[..., :3] if a.ndim == 3 else a).convert('RGB')


def sprite(key, mask_key):
    """a standing picture with its 4K mask as alpha (the engine's mask: 255 clear, 0 shown)"""
    rgb = picture(key)
    m = art(mask_key)
    m = m[..., 0] if m.ndim == 3 else m
    im = rgb.convert('RGBA')
    im.putalpha(Image.fromarray(255 - m))
    return im


def background():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    base = np.zeros((H, W, 3), np.float32)
    top, bottom = np.array([30, 9, 14], np.float32), np.array([12, 5, 8], np.float32)
    base += (top * (1 - y) + bottom * y)[..., None].squeeze(-1)[..., None] if False else 0
    for c in range(3):
        base[..., c] = top[c] * (1 - y[:, 0])[:, None] + bottom[c] * y[:, 0][:, None]
    v = ((x - .5) ** 2 + (y - .45) ** 2)
    base *= (1.15 - 0.9 * v)[..., None]
    rng = np.random.default_rng(7)
    base += rng.normal(0, 3.0, (H, W, 1)).astype(np.float32)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    # faint thorn branches behind the table, as the 연표 frame has
    d = ImageDraw.Draw(im, 'RGBA')
    rnd = random.Random(3)
    for k in range(7):
        x0, y0 = rnd.randint(0, W), rnd.randint(0, H)
        ang = rnd.uniform(0, math.tau)
        for s in range(60):
            x1, y1 = x0 + math.cos(ang) * 38, y0 + math.sin(ang) * 38
            d.line((x0, y0, x1, y1), fill=(120, 70, 80, 26), width=5)
            if rnd.random() < .18:
                a2 = ang + rnd.choice((-1, 1)) * rnd.uniform(.6, 1.1)
                d.line((x1, y1, x1 + math.cos(a2) * 70, y1 + math.sin(a2) * 70), fill=(120, 70, 80, 20), width=3)
            ang += rnd.uniform(-.25, .25)
            x0, y0 = x1, y1
    return im


def plate(size, fill=(34, 12, 18), border=SILVER, border_w=3, glow=False, texture=True, seed=0):
    w, h = size
    im = Image.new('RGBA', size, fill + (255,))
    if texture:
        rng = np.random.default_rng(seed)
        n = rng.normal(0, 1, (h // 6 + 1, w // 6 + 1)).astype(np.float32)
        n = np.asarray(Image.fromarray(((n + 3) * 40).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32)
        a = np.asarray(im).astype(np.float32)
        a[..., :3] *= (0.85 + 0.3 * n[..., None] / 255.0)
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    if glow:
        for i in range(10, 0, -1):
            d.rectangle((i, i, w - 1 - i, h - 1 - i), outline=(170, 40, 60, int(10 + 9 * (10 - i))))
    d.rectangle((0, 0, w - 1, h - 1), outline=border, width=border_w)
    d.rectangle((border_w + 3, border_w + 3, w - border_w - 4, h - border_w - 4), outline=(90, 60, 64), width=1)
    return im


def vertical(d, text, x, y, f, fill, gap=6):
    for ch in text:
        bb = d.textbbox((0, 0), ch, font=f)
        d.text((x - (bb[2] - bb[0]) / 2 - bb[0], y), ch, font=f, fill=fill)
        y += (bb[3] - bb[1]) + gap + (f.size * .1)


def main():
    im = background()
    d = ImageDraw.Draw(im, 'RGBA')
    M = 36
    corner = 380
    gx0, gy0 = M + corner + 36, M + corner + 36            # the table's top left
    cols, colw = 12, (W - M - (M + corner + 36)) // 12       # 226
    rowh = 182
    head_h = corner
    # ── corner emblem: 인물 / 날짜 across a diagonal, a red jewel in the middle
    em = plate((corner, corner), fill=(40, 12, 18), glow=True, seed=1)
    ed = ImageDraw.Draw(em)
    ed.line((14, 14, corner - 14, corner - 14), fill=SILVER, width=4)
    cx = cy = corner // 2
    for r, col in ((48, (60, 10, 20)), (40, (150, 24, 44)), (26, (210, 60, 80)), (12, (255, 170, 180))):
        ed.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    ed.ellipse((cx - 48, cy - 48, cx + 48, cy + 48), outline=SILVER, width=4)
    f = font(SERIF_L, 92)
    ed.text((corner - 34, 40), '인물', font=f, fill=INK, anchor='ra')
    ed.text((34, corner - 40), '날짜', font=f, fill=INK, anchor='ld')
    im.paste(em, (M, M), em)
    # ── people across (12 columns, as the 연표's top row); only those met so far are named
    people = [None, None, ('모미지', 'momi'), ('마키노', None), None, None, None, None, ('마사키', 'masa'), None, None, None]
    cursor_col, cursor_row = 2, 3
    momi = sprite('df814e2c', '95098e0a')       # momi_2a_1_01 4K and its mask
    masa = sprite('ef61881b', '2d84cbc3')       # masa_3b_1_01
    faces = {'momi': (momi, (980, 300)), 'masa': (masa, (1000, 330))}   # face centres in the 4K picture
    fname = font(SERIF, 62)
    for c in range(cols):
        x = gx0 + c * colw
        p = people[c]
        st = plate((colw - 6, head_h), fill=(30, 11, 16), border=(120, 96, 96), border_w=2, seed=10 + c)
        if p and p[1]:
            sp, (fx, fy) = faces[p[1]]
            crop = sp.crop((fx - 300, fy - 260, fx + 300, fy + 900)).resize((int((colw - 6) * 1.9), int(head_h * 2.0)), Image.LANCZOS)
            dark = Image.new('RGBA', crop.size, (20, 6, 10, 150))
            crop = Image.alpha_composite(crop, Image.new('RGBA', crop.size, (0, 0, 0, 0)))
            ox = (st.width - crop.width) // 2
            layer = Image.new('RGBA', st.size, (0, 0, 0, 0))
            layer.paste(crop, (ox, -40), crop)
            arr = np.asarray(layer).astype(np.float32)
            arr[..., :3] *= .55
            arr[..., 3] *= .9
            st = Image.alpha_composite(st, Image.fromarray(arr.astype(np.uint8)))
        sd = ImageDraw.Draw(st)
        name = p[0] if p else '？？？'
        vertical(sd, name, st.width / 2, 34, fname, INK if p else (110, 86, 86))
        sd.rectangle((0, 0, st.width - 1, st.height - 1), outline=(120, 96, 96), width=2)
        im.paste(st, (x + 3, M), st)
    # the cursor column's person spread open over the next columns (here 모미지)
    span = 5
    px0 = gx0 + cursor_col * colw
    pw = span * colw - 6
    if cursor_col + span > cols:
        px0 = gx0 + (cols - span) * colw
    panel = plate((pw, head_h), fill=(46, 13, 22), glow=True, seed=99)
    sp, (fx, fy) = faces['momi']
    bust = sp.crop((fx - 380, fy - 330, fx + 380, fy + 980)).resize((int(760 * .43), int(1310 * .43)), Image.LANCZOS)   # the face only: room for the text
    bx = pw - bust.width - 16
    layer = Image.new('RGBA', panel.size, (0, 0, 0, 0))
    layer.paste(bust, (bx, -24), bust)
    # fade the bust into the panel on its left
    arr = np.asarray(layer).astype(np.float32)
    ramp = np.clip((np.arange(pw) - bx) / 120.0, 0, 1)[None, :]
    arr[..., 3] *= ramp
    panel = Image.alpha_composite(panel, Image.fromarray(arr.astype(np.uint8)))
    pd = ImageDraw.Draw(panel)
    tx, tw = 52, bx - 52 - 24
    pd.text((tx, 26), '모미지', font=font(SERIF_L, 84), fill=INK)
    pd.line((tx, 122, tx + tw, 122), fill=(170, 70, 84), width=3)
    pd.text((tx, 136), '사건 제목 (예시)', font=font(SERIF, 52), fill=(255, 214, 200))

    def wrap(text, f, width):
        lines, cur = [], ''
        for word in text.split(' '):
            trial = (cur + ' ' + word).strip()
            if pd.textlength(trial, font=f) <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        return lines + ([cur] if cur else [])
    fdesc = font(SANS, 34)
    for i, line in enumerate(wrap('고른 칸의 설명이 이 자리에 나옵니다. 길면 네 줄까지 줄을 바꿔 보여 주고, 아직 안 연 사건은 설명도 가립니다.', fdesc, tw)[:4]):
        pd.text((tx + 2, 206 + i * 42), line, font=fdesc, fill=(214, 196, 188))
    pd.rectangle((0, 0, pw - 1, head_h - 1), outline=(226, 206, 196), width=4)
    im.paste(panel, (px0 + 3, M), panel)
    # a notch under the panel over the cursor column: whose panel it is
    nx = gx0 + cursor_col * colw + colw // 2
    d.polygon([(nx - 34, M + head_h - 2), (nx + 34, M + head_h - 2), (nx, M + head_h + 30)], fill=(226, 206, 196))
    d.polygon([(nx - 26, M + head_h - 4), (nx + 26, M + head_h - 4), (nx, M + head_h + 20)], fill=(46, 13, 22))
    # ── days down: blocks of rows under one date, as the 연표's left column
    days = [('18일 전', '수', 2), ('17일 전', '목', 3), ('16일 전', '금', 1), ('15일 전', '토', 2), ('14일 전', '일', 2)]
    y = gy0
    fdate, fday = font(SERIF_L, 76), font(SERIF, 46)
    for label, wd, n in days:
        hgt = n * rowh - 8
        if y + hgt > H - 150:
            hgt = H - 150 - y
        bl = plate((corner, hgt), fill=(24, 8, 12), border=(176, 150, 120), border_w=3, seed=hash(label) & 0xffff)
        bd = ImageDraw.Draw(bl)
        lw = bd.textlength(label, font=fdate)
        ww = bd.textlength(f' ({wd})', font=fday)
        x0 = (corner - lw - ww) / 2
        bd.text((x0, 30), label, font=fdate, fill=INK)
        bd.text((x0 + lw, 58), f' ({wd})', font=fday, fill=DIM)
        im.paste(bl, (M, y), bl)
        y += n * rowh
    rows = (H - 150 - gy0) // rowh + 1
    # ── cells: a scene picture where an event is known, a dark plate where one is hidden, empty otherwise
    pics = {'ev102_04': 'f0dddea4'.replace('f0dddea4', '383d51d4'), 'bg_330a': 'c12e54c8', 'img107': 'ae35ac32', 'bg_020a': 'e9d6589f',
            'netu102b': '9bc77d33', 'netu101c_01': '13fbdc59'}
    known = {(2, 2): 'bg_330a', (2, 3): 'ev102_04', (3, 0): 'bg_020a', (3, 1): 'img107', (3, 4): 'netu102b', (3, 6): 'netu101c_01', (8, 3): 'bg_330a'}
    hidden = {(0, 1), (1, 5), (5, 6), (6, 2), (9, 7), (10, 4), (11, 8), (7, 0), (4, 7)}
    linked, new = {(2, 3), (3, 4)}, {(2, 3)}
    thumbs = {}
    cw, ch = colw - 12, rowh - 12
    clip_bottom = H - 150
    tableau = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(tableau)
    for r in range(rows):
        for c in range(cols):
            x, yy = gx0 + c * colw + 6, gy0 + r * rowh + 6
            if yy >= clip_bottom:
                continue
            hh = min(ch, clip_bottom - yy)
            col_on = c == cursor_col
            base_fill = (52, 34, 40, 255) if col_on else (22, 10, 14, 235)
            td.rectangle((x, yy, x + cw - 1, yy + hh - 1), fill=base_fill, outline=(70, 36, 44, 255), width=2)
            if (c, r) in known:
                n = known[(c, r)]
                if n not in thumbs:
                    thumbs[n] = picture(pics[n]).resize((cw - 8, int((cw - 8) * .75)), Image.LANCZOS)
                t = thumbs[n].crop((0, (thumbs[n].height - (ch - 8)) // 2, cw - 8, (thumbs[n].height - (ch - 8)) // 2 + ch - 8))
                tableau.paste(t.crop((0, 0, t.width, min(t.height, hh - 8))), (x + 4, yy + 4))
                td.rectangle((x + 2, yy + 2, x + cw - 3, yy + hh - 3), outline=(206, 190, 180, 255), width=2)
                if (c, r) in linked:
                    td.polygon([(x + cw - 46, yy + ch - 44), (x + cw - 46, yy + ch - 14), (x + cw - 18, yy + ch - 29)], fill=(255, 236, 226, 235))
                if (c, r) in new:
                    td.rectangle((x + 4, yy + 4, x + 98, yy + 44), fill=(170, 22, 44, 245))
                    td.text((x + 51, yy + 24), 'NEW', font=font(SANS, 30), fill=(255, 240, 236), anchor='mm')
            elif (c, r) in hidden:
                hp = plate((cw - 10, hh - 10), fill=(58, 24, 30), border=(96, 62, 66), border_w=2, seed=c * 31 + r)
                tableau.paste(hp, (x + 5, yy + 5), hp)
    im = Image.alpha_composite(im.convert('RGBA'), tableau)
    d = ImageDraw.Draw(im, 'RGBA')
    # the cursor: corner brackets a little outside the cell
    x, yy = gx0 + cursor_col * colw + 6, gy0 + cursor_row * rowh + 6
    L, T = 46, 9
    for (ax, ay, sx, sy) in ((x - 14, yy - 14, 1, 1), (x + cw + 13, yy - 14, -1, 1), (x - 14, yy + ch + 13, 1, -1), (x + cw + 13, yy + ch + 13, -1, -1)):
        d.line((ax, ay, ax + sx * L, ay), fill=(250, 244, 240), width=T)
        d.line((ax, ay, ax, ay + sy * L), fill=(250, 244, 240), width=T)
    # a thin scroll bar at the right of the table
    d.rectangle((W - M + 8, gy0, W - M + 18, clip_bottom - 6), fill=(60, 30, 36))
    d.rectangle((W - M + 8, gy0 + 200, W - M + 18, gy0 + 520), fill=(196, 168, 160))
    # ── bottom bar: hints and the 연표's buttons
    by = H - 128
    d.text((M + 8, by + 34), '휠 · ↑↓  굴리기      ←→  인물      Enter · 클릭  이 장면으로      Esc  닫기', font=font(SANS, 40), fill=(186, 168, 160))
    bx = W - M
    for label in ('닫기', '도움말', '추가 이야기 찾기', '새 항목 찾기'):
        f = font(SERIF, 46)
        tw = d.textlength(label, font=f)
        bw = int(tw + 96)
        bx -= bw
        btn = plate((bw, 96), fill=(92, 22, 36), border=(214, 186, 176), border_w=3, seed=len(label))
        bd = ImageDraw.Draw(btn)
        bd.text((bw / 2, 48), label, font=f, fill=INK, anchor='mm')
        im.paste(btn, (bx, by), btn)
        bx -= 24
    im = im.convert('RGB')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(OUT, im.size)


if __name__ == '__main__':
    main()
