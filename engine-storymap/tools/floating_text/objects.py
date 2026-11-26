"""Japanese written ON things in the pictures (11-27, after the floating lines; the user: 「간단히 일본어인데 그림 애셋이고
한국어화 안된 것들 찾아보자」, and the list sent back: Momiji's card, the 故障中 paper, the まほこ name tag, the bridge sign).

One master picture per thing, where it is clearest and largest:
  - its Japanese strokes: what is darker than the paper around it inside each Japanese line's box (set by hand along
    the line), less the boxes of the drawings kept (the card's hearts beside the words); filled in from the paper;
  - the Korean, line by line where the Japanese lines were (each line's slant, start and letter height from its own
    strokes), in a handwriting face with a little wobble per letter, the strokes' colour and softness, drawn at 4x
    (laid on the 4x art) and made small for the 1x picture.
Every other picture of the same thing gets the master's change carried over:
  - the homography from the master to the copy (SIFT on the thing, or ECC where the copy is too blurred for keypoints);
  - the copy's own blur and colour, fitted on the thing (copy = a * blur(master, s) + b per channel, twice, the worst
    tenth of the pixels dropped the second time: what covers the thing, the phone over the card, does not fit);
  - the Japanese strokes moved there (grown by the blur) filled in from the copy's own paper, and the Korean letters'
    own change (the master's ink over its clean paper) moved, blurred and scaled the same way; laid on the whole thing,
    or where the copy fits for a thing partly covered (11-27: carrying the bare difference left the faded frames'
    Japanese half there: their strokes did not fit the linear model);
at 1x, and at 4x on the 4x art (the homography conjugated by the 4x scale, the blur 4x wider).
The pictures are stored as build.py stores them (TC01 deltas over their Korean base).
Run from build.py (after the floating lines, so a copy that has one keeps it).
"""
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assets as A  # noqa: E402
import build as Bd  # noqa: E402
import textlayer as T  # noqa: E402
import objects_spec as OS  # noqa: E402

S = 4


def poly_mask(poly, shape=(600, 800)):
    m = np.zeros(shape, np.uint8)
    k = shape[0] / 600
    cv2.fillPoly(m, [np.round(np.array(poly, np.float64) * k).astype(np.int32)], 1)
    return m.astype(bool)


def luma(rgb):
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)


def blur(img, s):
    return img if s <= 0 else cv2.GaussianBlur(img, (0, 0), s)


def paper_fill(rgb, fill, paper, sigma):
    """fill's pixels from the paper alone: a normalized convolution (blur(paper * colour) / blur(paper)), so nothing
    beside the paper (a swimsuit, a frame) bleeds in as an inpaint from all sides did. Where the paper is too far for
    sigma (the middle of a dense knot of strokes), twice and four times wider."""
    w = paper.astype(np.float32)
    out = rgb.copy()
    todo = fill.copy()
    for k in (1, 2, 4, 8, 16):
        den = cv2.GaussianBlur(w, (0, 0), sigma * k)
        ok = todo & (den > 0.08)
        if k == 16:
            ok = todo
        for c in range(3):
            num = cv2.GaussianBlur(rgb[..., c].astype(np.float32) * w, (0, 0), sigma * k)
            est = num / np.maximum(den, 1e-4)
            out[..., c][ok] = np.clip(est[ok], 0, 255).round().astype(np.uint8)
        todo &= ~ok
        if not todo.any():
            break
    return out


def region_fill(rgb, fill, strokes_grown, selects, sigma):
    """fill's pixels from the region each lies in: for every region (a selector of its own pixels, the strokes left
    out) its own paper fill, and each pixel takes the region of the nearest pixel outside the strokes (the speech cloud
    and the face beside it, the purple page and the hair over it, the white tag and the swimsuit: neither bleeds into
    the other, their border running on straight through the stroke)"""
    f = rgb.astype(np.float32)
    region = np.full(rgb.shape[:2], -1, np.int32)
    fills = []
    for i, sel in enumerate(selects):
        r = sel(f) & ~strokes_grown
        region[(region < 0) & r] = i
        fills.append(paper_fill(rgb, fill, r, sigma))
    known = region >= 0
    _, labels = cv2.distanceTransformWithLabels((~known).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    of_label = np.concatenate([[0], region[known].ravel()])   # labels count the zero (known) pixels in scan order from 1
    pick = of_label[labels]
    out = rgb.copy()
    for i, fl in enumerate(fills):
        m = fill & (pick == i)
        out[m] = fl[m]
    return out


def hull_fill(rgb, fill, strokes_grown, spec, sigma):
    """a light tag on dark cloth (the name tags): the tag is the convex hull of its light pixels and the strokes on it
    (inside 'inside'); a pixel to fill inside the hull takes the tag's own light pixels, outside it the cloth's. The
    hull keeps the tag's edge straight where the strokes covered it (a nearest-region split cut dark notches into it)"""
    g = luma(rgb)
    inside = poly_mask(spec['inside'], rgb.shape[:2])
    light = g > spec['hull_light']
    pts = np.argwhere((light | strokes_grown) & inside)[:, ::-1].astype(np.int32)
    hull = np.zeros(g.shape, np.uint8)
    cv2.fillPoly(hull, [cv2.convexHull(pts)], 1)
    hull = hull.astype(bool)
    tag = paper_fill(rgb, fill & hull, hull & light & ~strokes_grown, sigma)
    cloth = paper_fill(rgb, fill & ~hull, ~hull & ~strokes_grown, sigma)
    out = rgb.copy()
    out[fill & hull] = tag[fill & hull]
    out[fill & ~hull] = cloth[fill & ~hull]
    return out


def paper_of(rgb, spec, strokes_grown):
    """the paper: inside the thing, not a stroke, light enough and (where given) not blue"""
    g = luma(rgb)
    paper = poly_mask(spec['inside'], rgb.shape[:2]) & ~strokes_grown & (g > spec.get('paper_light', 0))
    if 'paper_select' in spec:
        paper &= spec['paper_select'](rgb.astype(np.float32))
    if 'max_blue' in spec:
        f = rgb.astype(np.float32)
        paper &= (f[..., 2] - (f[..., 0] + f[..., 1]) / 2) < spec['max_blue']
    return paper


# ---------------------------------------------------------------------------------------------- the master
def line_box(ls):
    """a Japanese line's box: from 'from' to 'to' (its middle line), 'half' each side across, 'pad' past both ends"""
    p0, p1 = np.array(ls['from'], np.float64), np.array(ls['to'], np.float64)
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    n = np.array([-d[1], d[0]])
    e = ls.get('pad', 8) * d
    h = ls['half'] * n
    return [tuple(p0 - e - h), tuple(p1 + e - h), tuple(p1 + e + h), tuple(p0 - e + h)]


def strokes(rgb, spec):
    """the Japanese strokes: darker than the paper (its median around) by spec['dark'], inside the lines' boxes and not
    in a kept box (the drawings beside them)"""
    g = luma(rgb)
    if 'select' in spec:                    # the letters by their own colour (a function of the float RGB picture)
        dark = spec['select'](rgb.astype(np.float32))
    elif 'abs_dark' in spec:                # thick marker letters on a light tag: a plain threshold (the local median of
        dark = g < spec['abs_dark']         # dense strokes is a stroke itself)
    elif 'tophat' in spec:                  # thin light letters on a dark textured sign: a white top-hat
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (spec.get('tophat_k', 7),) * 2)
        dark = cv2.morphologyEx(g.astype(np.uint8), cv2.MORPH_TOPHAT, k).astype(np.float32) > spec['tophat']
    elif 'light' in spec:                   # light letters on a dark sign: brighter than the sign around them
        paper = cv2.medianBlur(g.astype(np.uint8), 31).astype(np.float32)
        dark = (g - paper) > spec['light']
    else:
        paper = cv2.medianBlur(g.astype(np.uint8), 31).astype(np.float32)
        dark = (paper - g) > spec.get('dark', 22)
    boxes = np.zeros(g.shape, bool)
    for ls in spec['lines']:
        boxes |= poly_mask(line_box(ls))
    if spec.get('erase_all_inside'):         # a plain page with only the note on it: every stroke inside goes
        boxes[:] = True
    m = dark & boxes & poly_mask(spec['inside'])
    if 'max_blue' in spec:                  # neutral strokes only (a grey marker on a tag on a navy swimsuit)
        f = rgb.astype(np.float32)
        m &= (f[..., 2] - (f[..., 0] + f[..., 1]) / 2) < spec['max_blue']
    for x0, y0, x1, y1 in spec.get('keep', []):
        m[y0:y1, x0:x1] = False
    if 'keep_small' in spec:                # tiny marks inside a polygon stay (small print beside the letters)
        most, poly = spec['keep_small']
        n, lab, st, cen = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
        inside = poly_mask(poly, m.shape)
        tiny = [i for i in range(1, n) if st[i][4] <= most and inside[int(cen[i][1]), int(cen[i][0])]]
        m &= ~np.isin(lab, tiny)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    small = np.isin(lab, [i for i in range(1, n) if st[i][4] < spec.get('min_area', 3)])
    return m & ~small


def lines_of(mask, spec):
    """each Japanese line from its own strokes (those in its box): slant, start, end, middle and letter height"""
    out = []
    for ls in spec['lines']:
        own = mask & poly_mask(line_box(ls))
        for j in ls.get('exclude_lines', ()):
            own &= ~poly_mask(line_box(spec['lines'][j]))
        ys, xs = np.nonzero(own)
        pts = np.stack([xs, ys], 1).astype(np.float64)
        c = pts.mean(0)
        p0, p1 = np.array(ls['from'], np.float64), np.array(ls['to'], np.float64)
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        if len(pts) > 50:                                    # the strokes' own slant where there are enough of them
            vt = np.linalg.svd(pts - c, full_matrices=False)[2]
            pd = vt[0] if vt[0] @ d > 0 else -vt[0]
            if abs(np.rad2deg(np.arctan2(pd[1], pd[0]) - np.arctan2(d[1], d[0]))) < 8:
                d = pd
        nrm = np.array([-d[1], d[0]])
        along = (pts - c) @ d
        acr = (pts - c) @ nrm
        lo, hi = np.percentile(acr, [3, 97])
        out.append({'center': c, 'angle': float(np.rad2deg(np.arctan2(d[1], d[0]))), 'dir': d, 'normal': nrm,
                    'start': float(along.min()), 'end': float(along.max()), 'height': float(hi - lo), 'mid': float((lo + hi) / 2)})
    return out


def text_line(text, line, spec, line_no, scale=S, size=(800, 600)):
    """one Korean line as an alpha layer at scale: placed along the Japanese line (start, middle or end as spec says),
    the letters as tall as the Japanese ones, each with a little turn, lift and size of its own (fixed per line)"""
    rng = np.random.default_rng(1000 + line_no)
    face = spec['font']
    target = spec['lines'][line_no].get('size', line['target'])
    # the size whose hangul ink is as tall as the Japanese letters
    from PIL import ImageFont
    probe = ImageFont.truetype(str(face), 100, index=spec.get('index', 0))
    if 'weight' in spec:
        probe.set_variation_by_axes([spec['weight']])
    bb = probe.getbbox(spec.get('probe', '한글'), anchor='ls')     # the letters whose ink is to be that tall
    px = 100 * target / (bb[3] - bb[1])
    if 'centers' in spec['lines'][line_no]:   # each letter where a Japanese letter was (a short name: its own spacing)
        return letters_at(text, spec['lines'][line_no]['centers'], line['angle'] + spec['lines'][line_no].get('turn', 0)
                          - (90 if spec['lines'][line_no].get('vertical') else 0), px, spec, rng, scale, size)
    f = ImageFont.truetype(str(face), max(4, round(px * scale)), index=spec.get('index', 0))
    if 'weight' in spec:
        f.set_variation_by_axes([spec['weight']])
    vertical = spec['lines'][line_no].get('vertical', False)
    track = spec.get('tracking', 0.0) * px * scale
    # a vertical line steps one em (plus tracking) down per letter; a horizontal one by each letter's advance
    widths = [(px * scale if vertical else f.getlength(ch)) + track for ch in text]
    total = sum(widths) - track
    room = (line['end'] - line['start']) * scale * spec['lines'][line_no].get('room', 1.04)
    if spec['lines'][line_no].get('fit', True) and total > room > 0:   # no wider than the Japanese line: tracking, then size
        while track > 0 and total > room:
            track = max(0.0, track - 0.01 * px * scale)
            widths = [(px * scale if vertical else f.getlength(ch)) + track for ch in text]
            total = sum(widths) - track
        if total > room:
            k = room / total
            px *= k
            track *= k
            f = ImageFont.truetype(str(face), max(4, round(px * scale)), index=spec.get('index', 0))
            if 'weight' in spec:
                f.set_variation_by_axes([spec['weight']])
            widths = [(px * scale if vertical else f.getlength(ch)) + track for ch in text]
            total = sum(widths) - track
    if vertical:
        W, Hh = int(px * scale * 3), int(total + px * scale * 2)
    else:
        W, Hh = int(total + px * scale * 2), int(px * scale * 3)
    canvas = Image.new('L', (W, Hh), 0)
    pen = px * scale
    base = Hh / 2 + (bb[3] - bb[1]) / 100 * px * scale / 2       # the ink's middle on the canvas middle
    wob = spec.get('wobble', (3.0, 0.05, 0.05))                  # degrees, lift (em), size (fraction)
    for ch, w in zip(text, widths):
        if ch.strip():
            sz = 1 + rng.uniform(-wob[2], wob[2])
            fc = ImageFont.truetype(str(face), max(4, round(px * scale * sz)), index=spec.get('index', 0))
            if 'weight' in spec:
                fc.set_variation_by_axes([spec['weight']])
            if ch in spec.get('alt_chars', ''):  # a letter the face lacks, from a fallback face
                fc = ImageFont.truetype(str(spec['alt_font']), max(4, round(px * scale * sz * spec.get('alt_scale', 1.0))))
            cell = Image.new('L', (int(px * scale * 2.4), int(px * scale * 2.4)), 0)
            cd = ImageDraw.Draw(cell)
            if spec.get('ink_center'):           # the probe letters' ink on the cell's middle, on one baseline
                kk = px * scale * sz / 100
                cd.text((cell.width / 2 - fc.getlength(ch) / 2, cell.height / 2 - (bb[1] + bb[3]) / 2 * kk), ch, font=fc, fill=255, anchor='ls')
            else:
                cd.text((cell.width / 2, cell.height / 2), ch, font=fc, fill=255, anchor='mm')
            cell = cell.rotate(rng.uniform(-wob[0], wob[0]), resample=Image.BICUBIC, center=(cell.width / 2, cell.height / 2))
            lift = rng.uniform(-wob[1], wob[1]) * px * scale
            if vertical:
                cx, cy = W / 2 + lift, pen + px * scale / 2
            else:
                cx, cy = pen + fc.getlength(ch) / 2, base - (bb[3] - bb[1]) / 100 * px * scale / 2 + lift
            canvas.paste(Image.new('L', cell.size, 255), (int(cx - cell.width / 2), int(cy - cell.height / 2)), cell)
        pen += w
    # where the line goes: its start along the Japanese line, its middle across it
    align = spec['lines'][line_no].get('align', 'start')
    d, nrm, c = line['dir'], line['normal'], line['center']
    if align == 'start':
        along0 = line['start'] + spec['lines'][line_no].get('shift', 0)
    elif align == 'end':
        along0 = line['end'] - total / scale + spec['lines'][line_no].get('shift', 0)
    else:
        along0 = (line['start'] + line['end']) / 2 - total / scale / 2 + spec['lines'][line_no].get('shift', 0)
    # the canvas' line start (px*scale along it, its middle across) -> picture point c + along0*d + mid*nrm (at scale);
    # a vertical canvas runs down its y, so it turns a quarter less
    origin = (c + along0 * d + (np.clip(line['mid'], -4, 4) + spec['lines'][line_no].get('lift', 0)) * nrm) * scale
    a = np.deg2rad(line['angle'] + spec['lines'][line_no].get('turn', 0) - (90 if vertical else 0))
    ca, sa = np.cos(a), np.sin(a)
    M = np.array([[ca, -sa, 0], [sa, ca, 0]], np.float64)
    M[:, 2] = origin - M[:, :2] @ (np.array([W / 2, px * scale]) if vertical else np.array([px * scale, Hh / 2]))
    out = cv2.warpAffine(np.asarray(canvas), M, (size[0] * scale, size[1] * scale), flags=cv2.INTER_LINEAR)
    return out


def stamp_line(ls, line, spec, scale=S, size=(800, 600)):
    """a picture (its alpha) laid along the line in place of the Japanese one: as long as it, centred on it, turned with
    it (the poster's logo: the Korean brand logo where the Japanese one was, upright to the poster as that was)"""
    im = Image.open(ls['stamp']).convert('RGBA')
    a = np.asarray(im)[..., 3]
    ys, xs = np.nonzero(a > 10)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    length = (line['end'] - line['start']) * ls.get('room', 1.0) * scale
    k = length / a.shape[1]
    a = cv2.resize(a, (max(1, int(round(a.shape[1] * k))), max(1, int(round(a.shape[0] * k)))), interpolation=cv2.INTER_AREA)
    h, w = a.shape
    d, nrm, c = line['dir'], line['normal'], line['center']
    centre = (c + (line['start'] + line['end']) / 2 * d + (line['mid'] + ls.get('lift', 0)) * nrm) * scale
    t = np.deg2rad(line['angle'] + ls.get('turn', 0))
    ca, sa = np.cos(t), np.sin(t)
    M = np.array([[ca, -sa, 0], [sa, ca, 0]], np.float64)
    M[:, 2] = centre - M[:, :2] @ np.array([w / 2, h / 2])
    return cv2.warpAffine(a, M, (size[0] * scale, size[1] * scale), flags=cv2.INTER_LINEAR)


def letters_at(text, centers, angle, px, spec, rng, scale=S, size=(800, 600)):
    """the letters each centred on its own point (1x), turned with the line and a little wobble"""
    from PIL import ImageFont
    out = Image.new('L', (size[0] * scale, size[1] * scale), 0)
    wob = spec.get('wobble', (3.0, 0.05, 0.05))
    for ch, (x, y) in zip([c for c in text if c.strip()], centers):
        sz = 1 + rng.uniform(-wob[2], wob[2])
        fc = ImageFont.truetype(str(spec['font']), max(4, round(px * scale * sz)), index=spec.get('index', 0))
        if 'weight' in spec:
            fc.set_variation_by_axes([spec['weight']])
        cell = Image.new('L', (int(px * scale * 2.4), int(px * scale * 2.4)), 0)
        ImageDraw.Draw(cell).text((cell.width / 2, cell.height / 2), ch, font=fc, fill=255, anchor='mm')
        cell = cell.rotate(-angle + rng.uniform(-wob[0], wob[0]), resample=Image.BICUBIC, center=(cell.width / 2, cell.height / 2))
        out.paste(Image.new('L', cell.size, 255), (int(x * scale - cell.width / 2), int(y * scale - cell.height / 2)), cell)
    return np.asarray(out)


def ink_layer(alpha4, spec):
    """the letters as an RGBA layer: the Japanese strokes' colour and opacity, softened like them"""
    if spec.get('bold', 0):                                  # a pencil line a little wider than the face's own
        alpha4 = cv2.dilate(alpha4, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (spec['bold'], spec['bold'])))
    a = alpha4.astype(np.float32) / 255
    if spec.get('soft', 0):
        a = cv2.GaussianBlur(a, (0, 0), spec['soft'] * S)
    a *= spec.get('opacity', 0.92)
    rgba = np.zeros(a.shape + (4,), np.uint8)
    rgba[..., :3] = spec['ink']
    rgba[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
    lay = Image.fromarray(rgba, 'RGBA')
    outlines = spec.get('outlines') or ([spec['outline']] if spec.get('outline') else [])
    for r, gg, b, wd in sorted(outlines, key=lambda o: o[3]):   # (r, g, b, width in 1x px) under the letters, the widest lowest
        k = max(3, int(round(wd * S)) * 2 + 1)
        o = cv2.dilate(alpha4, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))).astype(np.float32) / 255
        o = cv2.GaussianBlur(o, (0, 0), max(0.5, spec.get('soft', 0.3)) * S)
        under = np.zeros(o.shape + (4,), np.uint8)
        under[..., :3] = (r, gg, b)
        under[..., 3] = np.clip(o * 255, 0, 255).astype(np.uint8)
        base = Image.fromarray(under, 'RGBA')
        base.alpha_composite(lay)
        lay = base
    return lay


def master(g, spec, name, debug=None, orig1=None, orig4=None):
    """one picture redrawn: its Japanese strokes filled in, the Korean set along their lines"""
    if orig1 is None:
        orig1, orig4 = g.composed(name), g.art(name)
    m = strokes(orig1, spec)
    lines = lines_of(m, spec)
    common = float(np.median([l['height'] for l in lines])) * spec.get('height_ratio', 0.85)   # one letter size for the thing
    for l in lines:
        l['target'] = common
    if 'ink' not in spec:
        spec['ink'] = tuple(int(v) for v in np.median(orig1[m], axis=0) * spec.get('ink_scale', 0.85))
    grow = Bd.dilate(m, spec.get('grow', 1))
    m4 = Bd.dilate(Bd.up(grow), spec.get('grow4', 5))
    if spec.get('fill') == 'paper':          # from the paper alone, at each scale from its own pixels
        sg = spec.get('fill_sigma', 4)
        clean1 = paper_fill(orig1, grow, paper_of(orig1, spec, Bd.dilate(grow, 1)), sg)
        clean4 = paper_fill(orig4, m4, paper_of(orig4, spec, Bd.dilate(m4, 4)), sg * S)
    elif spec.get('fill') == 'hull':         # a light tag on dark cloth
        sg = spec.get('fill_sigma', 4)
        clean1 = hull_fill(orig1, grow, Bd.dilate(grow, 1), spec, sg)
        clean4 = hull_fill(orig4, m4, Bd.dilate(m4, 4), spec, sg * S)
    elif spec.get('fill') == 'regions':      # from the region each pixel lies in
        sg = spec.get('fill_sigma', 4)
        clean1 = region_fill(orig1, grow, Bd.dilate(grow, 1), spec['regions'], sg)
        clean4 = region_fill(orig4, m4, Bd.dilate(m4, 4), spec['regions'], sg * S)
    else:
        clean1 = cv2.inpaint(orig1, grow.astype(np.uint8), 4, cv2.INPAINT_TELEA)
        clean4 = Bd.fill4(orig4, clean1, m4, 6)
    alpha = np.zeros((600 * S, 800 * S), np.uint8)
    for i, (line, ls) in enumerate(zip(lines, spec['lines'])):
        alpha = np.maximum(alpha, stamp_line(ls, line, spec) if 'stamp' in ls else text_line(ls['text'], line, spec, i))
    lay4 = ink_layer(alpha, spec)
    final1 = T.over(clean1, T.small(lay4))
    final4 = T.over(clean4, lay4)
    if debug is not None:
        dbg = Image.fromarray(orig1).copy()
        dd = ImageDraw.Draw(dbg)
        ov = np.asarray(dbg).copy()
        ov[m] = (255, 0, 0)
        dbg = Image.fromarray(ov)
        dd = ImageDraw.Draw(dbg)
        for line in lines:
            c, d = line['center'], line['dir']
            p0, p1 = c + line['start'] * d, c + line['end'] * d
            dd.line([tuple(p0), tuple(p1)], fill=(0, 255, 255), width=1)
        dd.polygon([tuple(p) for p in spec['inside']], outline=(255, 255, 0))
        for ls in spec['lines']:
            dd.polygon([tuple(p) for p in line_box(ls)], outline=(255, 128, 0))
        for x0, y0, x1, y1 in spec.get('keep', []):
            dd.rectangle([x0, y0, x1, y1], outline=(0, 255, 0))
        dbg.save(debug)
    return final1, final4, grow, clean1, clean4, {'lines': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in l.items()} for l in lines],
                            'strokes_1x': int(m.sum()), 'ink': list(spec['ink'])}


# ---------------------------------------------------------------------------------------------- the copies
def homography(m1, c1, roi):
    """the master->copy homography: SIFT on the thing (ratio 0.75, RANSAC 3 px), else ECC (homography) on both blurred"""
    sift = cv2.SIFT_create(6000)
    k1, d1 = sift.detectAndCompute(m1.astype(np.uint8), roi.astype(np.uint8) * 255)
    k2, d2 = sift.detectAndCompute(c1.astype(np.uint8), None)
    H, how, inl = None, 'none', 0
    if d1 is not None and d2 is not None and len(k1) > 8 and len(k2) > 8:
        pairs = cv2.BFMatcher().knnMatch(d1, d2, k=2)
        good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
        if len(good) >= 12:
            src = np.float32([k1[x.queryIdx].pt for x in good])
            dst = np.float32([k2[x.trainIdx].pt for x in good])
            H, mk = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
            inl = int(mk.sum()) if mk is not None else 0
            how = 'sift'
            if inl < 12:
                H = None
    if H is None:
        warp = np.eye(3, dtype=np.float32)
        how = 'ecc'
        for s in (8, 4, 2):
            a = cv2.GaussianBlur(c1, (0, 0), s)
            b = cv2.GaussianBlur(m1, (0, 0), s)
            try:
                _, warp = cv2.findTransformECC(a, b, warp, cv2.MOTION_HOMOGRAPHY,
                                               (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), roi.astype(np.uint8) * 0 + 1, 5)
            except cv2.error:
                pass
        H = np.linalg.inv(warp.astype(np.float64))   # ECC's warp takes copy points to master points
    return H, how, inl


def photometric(warped, copy, mask):
    """copy = a * blur(warped, s) + b per channel on mask: the s that fits best, a, b, the fit's error and its own mask"""
    best = None
    for s in (0, 0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20):
        bw = blur(warped, s)
        X, Y = bw[mask], copy[mask].astype(np.float32)
        ok = np.ones(len(X), bool)
        for _ in range(2):
            ab = []
            res = np.zeros(len(X), np.float32)
            for ch in range(3):
                Am = np.stack([X[ok, ch], np.ones(ok.sum(), np.float32)], 1)
                coef = np.linalg.lstsq(Am, Y[ok, ch], rcond=None)[0]
                ab.append(coef)
                res += np.abs(X[:, ch] * coef[0] + coef[1] - Y[:, ch])
            res /= 3
            ok = res <= np.percentile(res, 90)
        err = float(res[ok].mean())
        if best is None or err < best[0]:
            best = (err, s, np.array([c[0] for c in ab], np.float32), np.array([c[1] for c in ab], np.float32))
    return best


def carry(c1, c4, H, s, a, b, strokes1, add1, add4, m_orig1, roi, occluded=False):
    """the copy (c1, c4) with the master's change carried over: the Japanese strokes, moved by H and grown by the copy's
    blur (and a little for the fit), filled in from the copy's own paper around them; then the Korean letters' own
    change (the master's ink over its clean paper, add1 / add4) moved by H, blurred by s and scaled by the gains a. On the
    whole thing, or (occluded) only where the copy fits the master, the strokes' own small misfits closed."""
    Wm = cv2.warpPerspective(m_orig1.astype(np.float32), H, (800, 600), flags=cv2.INTER_LINEAR)
    fit = blur(Wm, s) * a + b
    wroi = cv2.warpPerspective(roi.astype(np.uint8), H, (800, 600), flags=cv2.INTER_NEAREST).astype(bool)
    if occluded:
        res = np.abs(blur(fit, 3) - blur(c1.astype(np.float32), 3)).mean(2)
        fits = wroi & (res < max(12.0, np.percentile(res[wroi], 60) * 2.0))
        fits = cv2.morphologyEx(fits.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)).astype(bool) & wroi
    else:
        fits = wroi
    ms = cv2.warpPerspective(strokes1.astype(np.uint8), H, (800, 600), flags=cv2.INTER_NEAREST).astype(bool)
    ms = Bd.dilate(ms, int(np.ceil(2 * s)) + 2) & fits
    e1 = cv2.inpaint(c1, ms.astype(np.uint8), 4 + int(2 * s), cv2.INPAINT_TELEA)
    e4 = Bd.fill4(c4, e1, Bd.dilate(Bd.up(ms), 4), 6)
    w1 = Bd.feather(fits, 2) * wroi
    A1 = blur(cv2.warpPerspective(add1, H, (800, 600), flags=cv2.INTER_LINEAR), s) * a
    out1 = np.clip(e1.astype(np.float32) + A1 * w1[..., None], 0, 255).round().astype(np.uint8)
    Sm = np.diag([S, S, 1.0])
    H4 = Sm @ H @ np.linalg.inv(Sm)
    A4 = blur(cv2.warpPerspective(add4, H4, (800 * S, 600 * S), flags=cv2.INTER_LINEAR), s * S) * a
    w4 = cv2.resize(w1, (800 * S, 600 * S), interpolation=cv2.INTER_LINEAR)
    out4 = np.clip(e4.astype(np.float32) + A4 * w4[..., None], 0, 255).round().astype(np.uint8)
    return out1, out4, float(fits.mean())


def run_things(b, things):
    """every thing of objects_spec (or those named): each master redrawn, then the copies carrying a master's change;
    stored by the Builder b. A thing drawn the same in several pictures at nearly one place (the 故障中 paper in the hall
    backgrounds) lists them all as masters: each is redrawn from its own strokes."""
    g = b.g
    (b.out / 'debug').mkdir(parents=True, exist_ok=True)
    report = {}
    for thing, spec in OS.THINGS.items():
        if thing not in things:
            continue
        masters = spec.get('masters') or [spec['master']]
        for name in masters:
            t0 = time.time()
            o1, o4 = b.current(name)              # a picture rebuilt before (a floating line, another thing) or over a rebuilt base
            k1, k4, grown, clean1, clean4, info = master(g, spec, name, b.out / 'debug' / f'{thing}-{name}.png', o1, o4)
            b.store(name, k1, k4, {'name': name, 'view': spec['view'], 'source': spec['source']}, t0,
                    lines=[''.join(l['text']) if 'text' in l else '(logo)' for l in spec['lines']], clean='master', thing=thing)
            report[f'{name}/{thing}'] = {'thing': thing, 'master': True, **info}   # a picture may carry several things
        if not spec.get('copies'):
            continue
        name = masters[0]
        o1 = g.composed(name)
        add1 = k1.astype(np.float32) - clean1.astype(np.float32)   # the Korean letters' own change, over the clean paper
        add4 = k4.astype(np.float32) - clean4.astype(np.float32)
        roi = poly_mask(spec['inside'])
        for cname in spec['copies']:
            t1 = time.time()
            base1, base4 = b.current(cname)       # a copy built before (a floating line) keeps that
            H, how, inl = homography(luma(o1), luma(base1), roi)
            Wm = cv2.warpPerspective(o1.astype(np.float32), H, (800, 600), flags=cv2.INTER_LINEAR)
            wroi = cv2.warpPerspective(roi.astype(np.uint8), H, (800, 600), flags=cv2.INTER_NEAREST).astype(bool)
            wroi &= ~Bd.dilate(~wroi, 4)
            err, s, a, bb = photometric(Wm, base1, wroi)
            c1, c4, share = carry(base1, base4, H, s, a, bb, grown, add1, add4, o1, roi, cname in spec.get('occluded', ()))
            b.store(cname, c1, c4, {'name': cname, 'view': spec['view'], 'source': spec['source']}, t1,
                    lines=[''.join(l['text']) if 'text' in l else '(logo)' for l in spec['lines']], clean='carried', thing=thing)
            report[f'{cname}/{thing}'] = {'thing': thing, 'from': name, 'homography': how, 'inliers': inl, 'blur': s, 'gain': a.round(3).tolist(),
                             'offset': bb.round(1).tolist(), 'fit_error': round(err, 2), 'fits_share': round(share, 3), 'H': np.round(H, 5).tolist()}
            print(cname, how, 'inl', inl, 'blur', s, 'err', round(err, 2), 'fits', round(share, 3), flush=True)
    return report
