"""Shared assets and drawing helpers for the Reconquista story-map mockups (2x of the 800x600 game screen).

All source art is read from the Codex project (read-only). Coordinates passed to helpers are 1x game
pixels; S converts to the 2x mock canvas.
"""
import colorsys
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 2
W, H = 800 * S, 600 * S
HERE = Path(__file__).resolve().parents[1]
REF = HERE / 'ref'
CODEX = Path(r'P:\AI\Codex\projects\reconquista-ko')
CAND = CODEX / 'candidates'
FONTS = CODEX / 'research' / 'fonts'
SERIF = str(FONTS / 'NotoSerifCJKkr-Regular.otf')
SANS = str(FONTS / 'NotoSansCJKkr-Regular.otf')
TOOLS = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\ui-opening-ending\tools')
sys.path.insert(0, str(TOOLS))
from decode_ui import decode  # noqa: E402

WHITE = (238, 234, 228)
DIM = (156, 156, 164)
PROMPT = (236, 202, 176)      # config/save prompt line
NAME = (226, 192, 142)        # speaker name in lists
LINE = (118, 116, 124)        # chronicle grid line
SAT = (88, 140, 255)
SUN = (238, 52, 60)
LEAF = (244, 150, 52)         # current position only

_fonts = {}


def font(kind, px):
    key = (kind, px)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(SERIF if kind == 'serif' else SANS, int(px * S))
    return _fonts[key]


def s(v):
    return int(round(v * S))


def box(x0, y0, x1, y1):
    return (s(x0), s(y0), s(x1), s(y1))


def text(img, xy, t, kind='serif', px=12, fill=WHITE, anchor='la', shadow=True, bold=False):
    d = ImageDraw.Draw(img)
    f = font(kind, px)
    x, y = s(xy[0]), s(xy[1])
    if shadow:
        d.text((x + S, y + S), t, font=f, fill=(0, 0, 0, 200), anchor=anchor)
    d.text((x, y), t, font=f, fill=fill, anchor=anchor)
    if bold:
        d.text((x + 1, y), t, font=f, fill=fill, anchor=anchor)
    return d.textlength(t, font=f) / S


def text_width(t, kind='serif', px=12):
    return ImageDraw.Draw(Image.new('L', (1, 1))).textlength(t, font=font(kind, px)) / S


def up(im):
    """1x RGBA art -> 2x canvas pixels."""
    return im.resize((im.width * S, im.height * S), Image.LANCZOS)


def rgba(path):
    return Image.open(path).convert('RGBA')


def decoded(stem):
    """Original raster with its _.rc8 alpha, as RGBA (1x)."""
    im = decode(stem + '.rct')[0].convert('RGBA')
    try:
        a = 255 - np.asarray(decode(stem + '_.rc8')[0].convert('L'))
        im.putalpha(Image.fromarray(a.astype('uint8')))
    except FileNotFoundError:
        pass
    return im


def hue_shift(im, target_hue_deg, sat_mul=1.0, val_mul=1.0):
    a = np.asarray(im.convert('RGBA')).astype('float32') / 255
    rgb, al = a[..., :3], a[..., 3:]
    flat = rgb.reshape(-1, 3)
    out = np.empty_like(flat)
    for i, (r, g, b) in enumerate(flat):
        h_, s_, v_ = colorsys.rgb_to_hsv(r, g, b)
        out[i] = colorsys.hsv_to_rgb(target_hue_deg / 360, min(1, s_ * sat_mul), min(1, v_ * val_mul))
    res = np.concatenate([out.reshape(rgb.shape), al], axis=2)
    return Image.fromarray((res * 255).astype('uint8'), 'RGBA')


def three_slice(im, width, cap):
    """Stretch a plate horizontally keeping both pointed ends (cap px each, in the image's own pixels)."""
    w, h = im.size
    if width <= 2 * cap:
        return im.resize((width, h), Image.LANCZOS)
    left = im.crop((0, 0, cap, h))
    right = im.crop((w - cap, 0, w, h))
    mid = im.crop((cap, 0, w - cap, h)).resize((width - 2 * cap, h), Image.LANCZOS)
    out = Image.new('RGBA', (width, h))
    out.paste(left, (0, 0))
    out.paste(mid, (cap, 0))
    out.paste(right, (width - cap, 0))
    return out


def plate(im, w1x, h1x, cap1x):
    """Plate art resized to w1x x h1x game pixels (2x canvas), ends preserved."""
    src = im.resize((im.width, int(round(im.height * (h1x / im.height)))), Image.LANCZOS) if im.height != h1x else im
    sliced = three_slice(src, int(round(w1x)), int(round(cap1x * (h1x / im.height))))
    return up(sliced)


def paste(canvas, im, x1x, y1x):
    canvas.alpha_composite(im, (s(x1x), s(y1x)))


def fill(canvas, rect1x, color):
    d = ImageDraw.Draw(canvas)
    d.rectangle(box(*rect1x), fill=color)


def rect(canvas, rect1x, color, width=1):
    d = ImageDraw.Draw(canvas)
    x0, y0, x1, y1 = box(*rect1x)
    d.rectangle((x0, y0, x1 - 1, y1 - 1), outline=color, width=width)


def tile_texture(tex, w, h):
    """Tile a texture (canvas px) to w x h."""
    out = Image.new('RGBA', (w, h))
    for yy in range(0, h, tex.height):
        for xx in range(0, w, tex.width):
            out.paste(tex, (xx, yy))
    return out


def textured(canvas, rect1x, tex, alpha=255):
    x0, y0, x1, y1 = box(*rect1x)
    t = tile_texture(tex, x1 - x0, y1 - y0)
    if alpha < 255:
        t.putalpha(Image.fromarray((np.asarray(t)[..., 3].astype('uint16') * alpha // 255).astype('uint8')))
    canvas.alpha_composite(t, (x0, y0))


# ---------------------------------------------------------------- assets

def chronicle_frame():
    """Clean chronicle frame at 2x: HD art, Korean label pixels replaced from the clean plate, title cleared,
    transparent content area filled black."""
    hd = Image.open(CAND / 'ui-rest-v1' / 'hd' / 'クロニクル枠_off.rct.png').convert('RGB').resize((W, H), Image.LANCZOS)
    clean = Image.open(CAND / 'ui-rest-v1' / 'clean' / 'クロニクル枠_off.rct.png').convert('RGB').resize((W, H), Image.LANCZOS)
    layer = Image.open(CAND / 'ui-rest-v1' / 'layers' / 'クロニクル枠_off.rct.png').split()[3].resize((W, H), Image.BILINEAR)
    mask = layer.point(lambda v: 255 if v > 8 else 0).filter(ImageFilter.MaxFilter(7))
    frame = Image.composite(clean, hd, mask)
    d = ImageDraw.Draw(frame)
    d.rectangle(box(148, 31, 301, 58), fill=(0, 0, 0))          # old screen title (uniform black under it)
    alpha = 255 - np.asarray(decode('クロニクル枠_off_.rc8')[0].convert('L'))
    hole = Image.fromarray(((alpha < 128) * 255).astype('uint8')).resize((W, H), Image.NEAREST)
    frame.paste((0, 0, 0), mask=hole)
    return frame.convert('RGBA')


def backlog_frame(clear_watermark=True):
    """The backlog panel keeps its own translucency (alpha 165): the paused scene shows through, dimmed.
    The bottom-left [RECONQUISTA] + Revelation watermark is replaced by plain panel rows for the list page."""
    im = decoded('バックログ画面')
    if clear_watermark:
        a = np.asarray(im).copy()
        a[455:571, 16:770] = a[290:406, 16:770]
        im = Image.fromarray(a, 'RGBA')
    return up(im)


def name_plate_crimson():
    return rgba(CAND / 'name-display-v1' / 'clean' / '名前プレート_信哉.rct.png')


def name_plate_navy():
    return hue_shift(name_plate_crimson(), 232, sat_mul=0.95, val_mul=1.05)


def name_plate_gray():
    return decoded('名前プレート_？？？')


def choice_bars():
    """(normal, hover, chosen-before) 560x56 bars from 選択肢台."""
    im = decoded('選択肢台')
    return [im.crop((122, y0, 683, y1 + 1)) for y0, y1 in ((74, 129), (173, 228), (272, 327))]


def navy_stone():
    bar = decoded('クロニクル青バー')
    return up(bar.crop((22, 120, 96, 560)))


def gray_stone():
    im = decode('クロニクル灰バー.rc8')[0].convert('RGBA')
    return up(im.crop((22, 120, 96, 560)))


def hidden_noise():
    return up(decode('情報隠蔽.rc8')[0].convert('RGBA'))


def leaf(size1x=16):
    im = decoded('momiba5')
    bb = im.getbbox()
    im = im.crop(bb)
    return im.resize((s(size1x), s(size1x * im.height / im.width)), Image.LANCZOS)


def config_top():
    """Clean config screen (Korean title baked) for banner + top-right chevron plates."""
    return rgba(CAND / 'config-completion-v1' / 'clean' / 'off.png')


def banner_blank():
    """Crimson ⚜ banner with the old title painted over by its own granite."""
    c = config_top()
    b = c.crop((0, 22, 202, 78)).copy()
    src = b.crop((132, 6, 168, 52))                   # clean granite right of the old title
    b.paste(src, (78, 6))
    b.paste(src.transpose(Image.FLIP_LEFT_RIGHT), (100, 6))
    return b


def chevron_plates():
    c = config_top()
    return c.crop((586, 13, 762, 45)), c.crop((586, 45, 762, 77))


def check_icon(img, x1x, y1x, px=11, fill=WHITE):
    text(img, (x1x, y1x), '✓', 'sans', px, fill, anchor='lm', shadow=False, bold=True)


def choice_icon(img, x1x, y1x, count=1, w=12, h=5):
    """Tiny 選択肢台 glyph (elongated hexagon, crimson granite) + count."""
    d = ImageDraw.Draw(img)
    x, y = s(x1x), s(y1x)
    ww, hh = s(w), s(h)
    pts = [(x, y + hh // 2), (x + s(2.5), y), (x + ww - s(2.5), y), (x + ww, y + hh // 2), (x + ww - s(2.5), y + hh), (x + s(2.5), y + hh)]
    d.polygon(pts, fill=(150, 22, 44), outline=(214, 206, 206))
    if count > 1:
        text(img, (x1x + w + 2.5, y1x + h / 2), str(count), 'sans', 9, (226, 200, 200), anchor='lm', shadow=False)
        return w + 2.5 + text_width(str(count), 'sans', 9)
    return w


def view_icon(img, x1x, y1x, r=5.0):
    """Tiny two-colour loop arrow (視点変更 motif): crimson upper arc, navy-violet lower arc."""
    d = ImageDraw.Draw(img)
    cx, cy = s(x1x + r), s(y1x + r * 0.6)
    rx, ry = s(r), s(r * 0.6)
    bb = (cx - rx, cy - ry, cx + rx, cy + ry)
    d.arc(bb, 190, 350, fill=(222, 40, 70), width=max(2, s(1.4)))
    d.arc(bb, 10, 170, fill=(110, 60, 230), width=max(2, s(1.4)))
    d.polygon([(cx + rx, cy - s(1.6)), (cx + rx + s(1.8), cy - s(0.2)), (cx + rx - s(1.4), cy + s(0.6))], fill=(222, 40, 70))
    d.polygon([(cx - rx, cy + s(1.6)), (cx - rx - s(1.8), cy + s(0.2)), (cx - rx + s(1.4), cy - s(0.6))], fill=(110, 60, 230))
    return r * 2 + 2
