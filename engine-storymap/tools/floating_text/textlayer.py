"""Text drawn the way the game's floating lines are: at 4x (3200x2400 for an 800x600 picture), letter-spaced, with the
originals' soft halo / blur / fade, as an RGBA layer that is laid over the clean picture at 4x and, made small, at 1x.

A style (dict):
  font        path, and 'index' for a .ttc face, 'weight' for a variable font
  size        em size in 1x pixels
  tracking    extra space after each character, in em
  leading     line advance in em (several lines)
  fill        RGBA of the letters
  halo        [r, g, b, a, radius_1x, spread_1x]: a blurred copy of the letters behind them (glow or soft shadow)
  shadow      [r, g, b, a, dx_1x, dy_1x, radius_1x]: an offset blurred copy
  blur        radius_1x of a blur over the whole finished layer (the originals' out-of-focus lines)
  opacity     0..1 over the whole layer
  align       'center' (each line centred on x) or 'left' (lines start at x)
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 4                                    # the 4x layer


def font(style, scale=S):
    f = ImageFont.truetype(str(style['font']), round(style['size'] * scale), index=style.get('index', 0))
    if 'weight' in style:
        f.set_variation_by_axes([style['weight']])
    return f


def fonts(style, scale=S):
    """the style's font, and the one for its alt_chars (a brush face's own 「」 are small: Gungsuh's take Noto Serif's)"""
    f = font(style, scale)
    alt = font({**style, 'font': style['alt_font'], 'index': 0}, scale) if style.get('alt_font') else None
    return lambda ch: alt if alt is not None and ch in style.get('alt_chars', '') else f


def line_width(text, style, scale=S):
    """the line's advance in pixels at this scale (tracking after every character but the last)"""
    pick = fonts(style, scale)
    tracking = style.get('tracking', 0) * style['size'] * scale
    return sum(pick(ch).getlength(ch) for ch in text) + tracking * max(0, len(text) - 1)


def draw_lines(lines, style, x, y, canvas_size, scale=S):
    """the letters alone (alpha), lines centred on (x, y) of the 1x picture, or starting at x for align left"""
    pick = fonts(style, scale)
    em = style['size'] * scale
    tracking = style.get('tracking', 0) * em
    leading = style.get('leading', 1.6) * em
    a = Image.new('L', canvas_size, 0)
    d = ImageDraw.Draw(a)
    n = len(lines)
    top = y * scale - (n - 1) * leading / 2
    for k, text in enumerate(lines):
        w = line_width(text, style, scale)
        cx = x * scale - w / 2 if style.get('align', 'center') == 'center' else x * scale
        base = top + k * leading
        pen = cx
        for ch in text:
            f = pick(ch)
            # each glyph placed by advance, centred vertically on the line's middle (em box)
            d.text((pen, base), ch, font=f, fill=255, anchor='lm')
            pen += f.getlength(ch) + tracking
    return a


def layer(lines, style, x, y, size=(800, 600), scale=S):
    """RGBA layer at scale (4 by default) of the picture size: lines centred on (x, y), or starting at x (align left)"""
    W, H = size[0] * scale, size[1] * scale
    return effects(draw_lines(lines, style, x, y, (W, H), scale), style, scale)


def layer_baseline(text, style, x, baseline, size=(800, 600), scale=S):
    """one run starting at x with its baseline at `baseline` (1x): the time cards' 약 / number / 년 전 on one line"""
    W, H = size[0] * scale, size[1] * scale
    pick = fonts(style, scale)
    tracking = style.get('tracking', 0) * style['size'] * scale
    a = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(a)
    pen = x * scale
    for ch in text:
        f = pick(ch)
        d.text((pen, baseline * scale), ch, font=f, fill=255, anchor='ls')
        pen += f.getlength(ch) + tracking
    return effects(a, style, scale)


def effects(letters, style, scale=S):
    """the letters (alpha) made a layer: shadow, halo, fill, then blur and fade over all"""
    W, H = letters.size
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if style.get('shadow'):
        r, g, b, alpha, dx, dy, rad = style['shadow']
        m = letters.filter(ImageFilter.GaussianBlur(rad * scale)) if rad else letters
        sh = Image.new('RGBA', (W, H), (r, g, b, 0))
        sh.putalpha(m.point(lambda v: int(v * alpha / 255)))
        out.alpha_composite(sh, (int(dx * scale), int(dy * scale)))
    if style.get('halo'):
        r, g, b, alpha, rad, spread = style['halo']
        m = letters
        if spread:
            m = m.filter(ImageFilter.MaxFilter(int(spread * scale) * 2 + 1))
        m = m.filter(ImageFilter.GaussianBlur(rad * scale))
        arr = np.asarray(m, np.float32) * (alpha / 255) * style.get('halo_gain', 1.0)
        h = Image.new('RGBA', (W, H), (r, g, b, 0))
        h.putalpha(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)))
        out.alpha_composite(h)
    fill = Image.new('RGBA', (W, H), tuple(style['fill'][:3]) + (0,))
    fa = np.asarray(letters, np.float32) * (style['fill'][3] / 255)
    fill.putalpha(Image.fromarray(fa.astype(np.uint8)))
    out.alpha_composite(fill)
    if style.get('blur'):
        out = premul_blur(out, style['blur'] * scale)
    if style.get('opacity', 1) < 1:
        arr = np.asarray(out).copy()
        arr[..., 3] = (arr[..., 3].astype(np.float32) * style['opacity']).astype(np.uint8)
        out = Image.fromarray(arr, 'RGBA')
    return out


def premul_blur(im, radius):
    """blur an RGBA layer without dark fringes (premultiplied)"""
    a = np.asarray(im, np.float32) / 255
    pm = np.dstack([a[..., :3] * a[..., 3:4], a[..., 3:4]])
    out = []
    for c in range(4):
        out.append(np.asarray(Image.fromarray((pm[..., c] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255)
    pm = np.dstack(out)
    alpha = pm[..., 3:4]
    rgb = np.where(alpha > 1e-4, pm[..., :3] / np.maximum(alpha, 1e-4), 0)
    return Image.fromarray(np.dstack([rgb, alpha]).clip(0, 1).__mul__(255).astype(np.uint8), 'RGBA')


def over(base_rgb, lay):
    """lay an RGBA layer over an RGB array of the same size"""
    b = Image.fromarray(base_rgb).convert('RGBA')
    b.alpha_composite(lay)
    return np.asarray(b.convert('RGB'))


def small(lay, size=(800, 600)):
    """the 4x layer made 1x (premultiplied box average, as the engine's own 4x->1x)"""
    a = np.asarray(lay, np.float32) / 255
    pm = np.dstack([a[..., :3] * a[..., 3:4], a[..., 3:4]])
    H, W = size[1], size[0]
    k = pm.shape[0] // H
    pm = pm.reshape(H, k, W, k, 4).mean(axis=(1, 3))
    alpha = pm[..., 3:4]
    rgb = np.where(alpha > 1e-4, pm[..., :3] / np.maximum(alpha, 1e-4), 0)
    return Image.fromarray((np.dstack([rgb, alpha]).clip(0, 1) * 255).round().astype(np.uint8), 'RGBA')
