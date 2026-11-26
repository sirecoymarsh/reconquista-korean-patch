"""Korean versions of the game's floating lines and time cards (11-26, the user: 「이 장면에서 잠깐 일본어 연출이 지나가는데
그거 한국어화 안됐어 … 이런 플로팅 연출 찾아서 한국어화 안된거 있으면 폰트 디자인 맞춰서 한국어화하고 패치 다시 만들어」).

Each picture (spec.py) is the engine's composed picture with its Japanese line taken out and the Korean line laid in:
  - the clean picture: the original everywhere but the line's footprint, where it comes from the same picture without
    the line (a sibling the game has: 40 of them), the sibling scaled (netu110g1 = 0.71 x netu110f, ev5043cd = white
    half-way over ev5043c), plain white, or the picture's own pixels filled in (cv2 inpaint) where nothing else has it;
  - the Korean line: one text layer drawn at 4x (textlayer.py, the original's halo, blur and fade), laid over the clean
    4x art (the HD layer) and, made small, over the clean 1x picture;
  - stored as the original stored it: a TC00 picture whole; a TC01 delta over its (Korean) base, pure red where the
    two agree, so the engine composes it as before; the 4x art whole (the HD layer replaces the composed picture).
Then the things with Japanese written on them (objects.py, objects_spec.py).
python build.py <runtime> <out> [names or things...]   -> <out>/payloads/<arc>/<entry>, <out>/hires/<key>.png, <out>/hires-jxl/<key>.jxl,
                                               <out>/preview/<name>.png (original | Korean, 1x and a 4x crop), manifest.json, objects.json
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assets as A  # noqa: E402
import textlayer as T  # noqa: E402
import spec as SP  # noqa: E402

RED = A.RED


def dilate(m, r):
    if r <= 0:
        return m
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.dilate(m.astype(np.uint8), k).astype(bool)


def up(m, k=4):
    return np.repeat(np.repeat(m, k, 0), k, 1)


def feather(m, r):
    """a soft 0..1 weight from a mask (the inside 1, falling to 0 over r pixels outside)"""
    if r <= 0:
        return m.astype(np.float32)
    d = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    return np.clip(1 - d / r, 0, 1).astype(np.float32)


def large(rgb):
    return np.asarray(Image.fromarray(rgb).resize((rgb.shape[1] * 4, rgb.shape[0] * 4), Image.LANCZOS))


def fill4(orig4, clean1, m4, soft):
    """the 4x art with the 1x fill (made large) laid into m4, its colour matched to the art just outside (the
    upscaler's art sits a level or two off the 1x picture: a plain fill showed as a faint box on the flat cards)"""
    big = large(clean1).astype(np.float32)
    ring = dilate(m4, soft + 6) & ~dilate(m4, soft)
    off = np.median(orig4[ring].astype(np.float32) - big[ring], axis=0) if ring.any() else 0
    big = np.clip(big + off, 0, 255).round().astype(np.uint8)
    return blend(orig4, big, feather(m4, soft))


def blend(a, b, w):
    w = w[..., None]
    return np.clip(a.astype(np.float32) * (1 - w) + b.astype(np.float32) * w, 0, 255).round().astype(np.uint8)


def fit_width(text, style, width):
    """the tracking that gives the line the Japanese line's width (within the style's bounds)"""
    n = len(text)
    w0 = T.line_width(text, {**style, 'tracking': 0}, 1)
    if n < 2:
        return style
    t = (width - w0) / (n - 1) / style['size']
    return {**style, 'tracking': float(np.clip(t, style.get('min_tracking', 0.0), style.get('max_tracking', 1.0)))}


class Builder:
    def __init__(self, run, out):
        self.g = A.Game(run)
        self.out = Path(out)
        self.done = {}                       # name -> final 1x (Korean), for deltas over a Korean base
        self.done4 = {}                      # name -> final 4x (objects.py carries a thing onto a picture built before)
        self.cleans = {}                     # name -> (clean 1x, clean 4x): a later picture over this one takes its clean
        self.records = []

    # ------------------------------------------------------------------ the clean picture
    def estimate(self, name, how):
        """(1x, 4x) of the picture without its line, from what `how` names"""
        g = self.g
        kind = how['kind']
        if kind == 'sibling':
            return g.composed(how['from']), g.art(how['from'])
        if kind == 'scaled':
            k, b = how['k'], how.get('b', 0.0)
            s1, s4 = g.composed(how['from']).astype(np.float32), g.art(how['from']).astype(np.float32)
            return np.clip(s1 * k + b, 0, 255).round().astype(np.uint8), np.clip(s4 * k + b, 0, 255).round().astype(np.uint8)
        if kind == 'clean_of':              # the clean of a picture built before (ev501d over ev501c: both faint lines gone)
            return self.cleans[how['from']]
        if kind == 'flat':
            c = np.array(how['rgb'], np.uint8)
            return np.broadcast_to(c, (600, 800, 3)).copy(), np.broadcast_to(c, (2400, 3200, 3)).copy()
        if kind == 'inpaint':
            return None, None
        raise ValueError(kind)

    def footprint(self, name, how, est1):
        """the 1x pixels of the Japanese line (with its halo), from the difference to the estimate, or found in its box"""
        orig = self.g.composed(name).astype(np.int16)
        x0, y0, x1, y1 = how['box']
        m = np.zeros(orig.shape[:2], bool)
        if est1 is not None:
            d = np.abs(orig - est1.astype(np.int16)).max(2)
            m[y0:y1, x0:x1] = d[y0:y1, x0:x1] > how.get('threshold', 6)
        else:
            gray = cv2.cvtColor(orig.astype(np.uint8), cv2.COLOR_RGB2GRAY)
            bg = cv2.medianBlur(gray, 31)
            d = np.abs(gray.astype(np.int16) - bg.astype(np.int16))
            m[y0:y1, x0:x1] = d[y0:y1, x0:x1] > how.get('threshold', 10)
        return m, dilate(m, how.get('grow', 2))

    def clean(self, name, how):
        g = self.g
        orig1, orig4 = g.composed(name), g.art(name)
        est1, est4 = self.estimate(name, how)
        core, m1 = self.footprint(name, how, est1)
        if 'mask' in how:                  # explicit extra boxes to clear (x0, y0, x1, y1)
            for x0, y0, x1, y1 in how['mask']:
                m1[y0:y1, x0:x1] = True
        m4 = dilate(up(m1), how.get('grow4', 10))
        if est1 is None:                    # nothing else has these pixels: fill them from around, at 1x; the 4x takes that
            r = how.get('radius', 5)        # fill made large (an inpaint of the 4x art spread the upscaler's dark rims)
            clean1 = cv2.inpaint(orig1, m1.astype(np.uint8), r, cv2.INPAINT_TELEA)
            clean4 = fill4(orig4, clean1, m4, how.get('feather4', 8))
        else:
            clean1 = orig1.copy()
            clean1[m1] = est1[m1]
            w = feather(m4, how.get('feather4', 6))
            clean4 = blend(orig4, est4, w)
        ys, xs = np.where(core)
        return clean1, clean4, m1, (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)

    # ------------------------------------------------------------------ one picture
    def from4k(self, item):
        """a picture whose 4x art is Korean already (Codex's redraw: the title logos, the bus) but whose own 1x is not:
        the 1x takes the 4x art made small where the two differ in the given boxes (the logo, the signs), its colour
        matched to the 1x just around; the 4x art stays as it is"""
        g = self.g
        name = item['name']
        t0 = time.time()
        o1, a4 = g.composed(name), g.art(name)
        small = a4.reshape(600, 4, 800, 4, 3).mean(axis=(1, 3))
        diff = np.abs(small - o1.astype(np.float32)).max(2)
        m = np.zeros(diff.shape, bool)
        for x0, y0, x1, y1 in item['from4k']['boxes']:
            m[y0:y1, x0:x1] = diff[y0:y1, x0:x1] > item['from4k'].get('threshold', 40)
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
        if item['from4k'].get('hull'):     # the whole logo's hull: the old logo's dark tails differ from the redrawn sea by little
            n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
            big = np.isin(lab, [i for i in range(1, n) if st[i][4] >= 40])
            ys, xs = np.nonzero(big)
            hull = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))
            m = np.zeros(m.shape, np.uint8)
            cv2.fillPoly(m, [hull], 1)
            m = m.astype(bool)
        m = dilate(m, item['from4k'].get('grow', 2))
        ring = dilate(m, 6) & ~dilate(m, 2)
        off = np.median(o1[ring].astype(np.float32) - small[ring], axis=0) if ring.any() else 0
        w = feather(m, item['from4k'].get('soft', 2))
        final1 = blend(o1, np.clip(small + off, 0, 255), w)
        self.store(name, final1, a4, {'name': name, 'view': item['view'], 'source': item.get('source')}, t0,
                   lines=item.get('lines'), clean='from_4x', art4=False)

    def build(self, item):
        name = item['name']
        g = self.g
        t0 = time.time()
        if 'from4k' in item:
            return self.from4k(item)
        if 'card' in item:
            clean1, clean4, m1, layers = self.card(item)
        else:
            clean1, clean4, m1, (bx0, by0, bx1, by1) = self.clean(name, item['clean'])
            self.cleans[name] = (clean1, clean4)
            item['found_box'] = [bx0, by0, bx1, by1]
            layers = []
            for t in item['text']:               # placed where the Japanese line was (its centre), unless given
                x = t['x'] if 'x' in t else (bx0 + bx1) / 2 + t.get('dx', 0)
                y = t['y'] if 'y' in t else (by0 + by1) / 2 + t.get('dy', 0)
                style = {**SP.STYLES[t['style']], **t.get('style_over', {})}
                if 'x' not in t and style.get('fit', True) and len(t['lines']) == 1:
                    style = fit_width(t['lines'][0], style, (bx1 - bx0) - 2 * style.get('margin', 0))
                layers.append(T.layer(t['lines'], style, x, y))
        lay4 = layers[0]
        for extra in layers[1:]:
            lay4.alpha_composite(extra)
        lay1 = T.small(lay4)
        final1 = T.over(clean1, lay1)
        final4 = T.over(clean4, lay4)
        self.store(name, final1, final4, item, t0,
                   lines=[l for t in item.get('text', []) for l in t['lines']] or item.get('card', {}).get('lines'),
                   clean=(item.get('clean') or {}).get('kind', 'card'), japanese_box_1x=item.get('found_box'))

    def changed(self, name):
        """whether this picture or a base under it was rebuilt"""
        while name:
            if name in self.done:
                return True
            name = self.g.base_of(name)
        return False

    def current(self, name):
        """the picture as it stands now (1x, 4x): rebuilt, or its own delta over its rebuilt base (where the delta is pure
        red the engine shows the base: there the 4x art takes the base's new 4x too, as Codex's 4x was the composed
        picture made large), or the original"""
        g = self.g
        if name in self.done:
            return self.done[name], self.done4[name]
        base = g.base_of(name)
        if base and self.changed(base):
            b1, b4 = self.current(base)
            raw = g.raw(name)
            red = np.all(raw == RED, axis=2)
            c1 = raw.copy()
            c1[red] = b1[red]
            c4 = g.art(name).copy()
            red4 = up(red)
            c4[red4] = b4[red4]
            return c1, c4
        return g.composed(name), g.art(name)

    def dependents(self):
        """every TC01 picture over a rebuilt base that was not rebuilt itself (yana09 over yana08): its delta stays, its
        4x art takes the base's new 4x where the delta shows the base"""
        g = self.g
        for stem in sorted(g.entries):
            if stem in self.done or not g.base_of(stem) or not self.changed(g.base_of(stem)):
                continue
            c1, c4 = self.current(stem)
            self.store(stem, c1, c4, {'name': stem, 'view': [0, 0, 800, 600], 'source': 'over a rebuilt base'}, time.time(),
                       clean='dependent', base_rebuilt=g.base_of(stem))

    def store(self, name, final1, final4, item, t0, art4=True, **extra):
        """the picture's payload as the original stored it (TC00 whole; TC01 a delta over its Korean base, pure red where
        the two agree), its 4x art (PNG and the HD layer's JPEG XL), a preview, and its record"""
        g = self.g
        payload = g.payload(name)
        base = g.base_of(name)
        if base:
            base1 = self.done.get(base)
            if base1 is None:
                base1 = g.composed(base)
            diff = np.any(final1 != base1, axis=2)
            delta = np.empty_like(final1)
            delta[:] = RED
            px = final1.copy()
            pure = np.all(px == RED, axis=2)
            px[pure] = (254, 0, 0)          # a real pure red would read as 'take the base'
            delta[diff] = px[diff]
            new = A.encode_payload(payload, delta)
        else:
            new = A.encode_payload(payload, final1)
        self.done[name] = final1
        self.done4[name] = final4
        arc = g.arc_of(name)
        entry = g.name(name)
        (self.out / 'payloads' / arc).mkdir(parents=True, exist_ok=True)
        (self.out / 'payloads' / arc / entry).write_bytes(new)
        k = A.key(entry)
        (self.out / 'hires').mkdir(parents=True, exist_ok=True)
        (self.out / 'hires-jxl').mkdir(parents=True, exist_ok=True)
        dist = psnr = None
        if art4:                            # the 4x art when it changed (a 4x already Korean stays as it is)
            Image.fromarray(final4).save(self.out / 'hires' / f'{k}.png')
            data, dist, psnr = A.jxl(final4)
            (self.out / 'hires-jxl' / f'{k}.jxl').write_bytes(data)
        self.preview(name, final1, final4, item)
        rec = {'name': entry, 'archive': arc, 'key': k, 'base': base, 'source': item.get('source'), **extra,
               'payload_before_sha256': hashlib.sha256(payload).hexdigest(), 'payload_after_sha256': hashlib.sha256(new).hexdigest(),
               'changed_1x_pixels': int(np.any(final1 != g.composed(name), axis=2).sum()), 'jxl_distance': dist, 'jxl_psnr': round(float(psnr), 2) if psnr is not None else None,
               'seconds': round(time.time() - t0, 1)}
        self.records.append(rec)
        print(name, rec['changed_1x_pixels'], 'px', rec['seconds'], 's', flush=True)

    # ------------------------------------------------------------------ the time cards
    def card_clean(self, name):
        """the card without its line: its own line and 04yb2's (the base it is a delta over) filled in"""
        g = self.g
        mask = np.zeros((600, 800), bool)
        for n in {name, '04yb2'}:
            gray = cv2.cvtColor(g.composed(n), cv2.COLOR_RGB2GRAY)
            x0, y0, x1, y1 = SP.CARD_BOX
            mask[y0:y1, x0:x1] |= gray[y0:y1, x0:x1] > 60
        mask = dilate(mask, 4)
        clean1 = cv2.inpaint(g.composed(name), mask.astype(np.uint8), 6, cv2.INPAINT_TELEA)
        m4 = dilate(up(mask), 20)                             # the 4x art's soft rims round the old glyphs reach further
        clean4 = fill4(g.art(name), clean1, m4, 12)
        return clean1, clean4, mask

    def card(self, item):
        """a time card: the number stays the original's own art (1x and 4x); 약 takes 約's place and 년 전 / 주 전 start
        where 年前 / 週間前 started, on the same baseline. 「한 달 후」 / 「몇 시간 전」 are set whole where theirs was."""
        g = self.g
        name = item['name']
        c = item['card']
        orig1, orig4 = g.composed(name), g.art(name)
        gray = cv2.cvtColor(orig1, cv2.COLOR_RGB2GRAY)
        x0, y0, x1, y1 = c['box']
        bw = np.zeros(gray.shape, np.uint8)
        bw[y0:y1, x0:x1] = gray[y0:y1, x0:x1] > 90
        n, lab, st, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
        comps = [(i, *map(int, st[i][:4])) for i in range(1, n) if st[i][4] >= 6]
        if c.get('whole'):
            m = bw.astype(bool)
            ys, xs = np.where(m)
            left, right, top, bottom = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
            m1 = np.zeros_like(m)                             # a flat navy card: the line's whole box, filled
            X0, Y0, X1, Y1 = max(0, left - 6), max(0, top - 6), right + 6, bottom + 6
            m1[Y0:Y1, X0:X1] = True
            # with the card's own navy from beside the line (same rows), so its fine grain carries on (a smooth fill
            # showed as a box at 4x)
            shift = (X1 - X0) + 24
            if X1 + shift > 800:
                shift = -shift
            clean1 = orig1.copy()
            clean1[m1] = np.roll(orig1, -shift, axis=1)[m1]
            m4 = dilate(up(m1), 8)
            clean4 = blend(orig4, np.roll(orig4, -shift * 4, axis=1), feather(m4, 10))
            style = SP.STYLES[c['style']]
            lay = T.layer([c['lines'][0]], fit_width(c['lines'][0], style, right - left), (left + right) / 2, (top + bottom) / 2 + c.get('dy', 0))
            return clean1, clean4, m1, [lay]
        digits = [cc for cc in comps if cc[4] >= 60]
        dx0 = min(cc[1] for cc in digits)
        dx1 = max(cc[1] + cc[3] for cc in digits)
        base_y = max(cc[2] + cc[4] for cc in digits)            # the digits' bottom: the line's baseline
        pre = [cc for cc in comps if cc[1] + cc[3] <= dx0 + 1 and cc not in digits]
        post = [cc for cc in comps if cc[1] >= dx1 - 1 and cc not in digits]
        clean1, clean4, union = self.card_clean(name)
        dm = np.zeros(gray.shape, bool)
        for i, *_ in digits:
            dm |= lab == i
        dm1 = dilate(dm, 2)                                   # the number, with its soft edge, from the original
        clean1 = clean1.copy()
        clean1[dm1] = orig1[dm1]
        clean4 = blend(clean4, orig4, feather(dilate(up(dm1), 2), 6))
        st = SP.STYLES['card']
        f = T.font(st, 1)
        layers = []
        px0, px1 = min(cc[1] for cc in pre), max(cc[1] + cc[3] for cc in pre)
        w = T.line_width(c['lines'][0], st, 1)
        bottom = f.getbbox(c['lines'][0], anchor='ls')[3]         # the hangul's bottom below its baseline
        layers.append(T.layer_baseline(c['lines'][0], st, (px0 + px1) / 2 - w / 2, base_y - bottom))
        qx0 = min(cc[1] for cc in post)
        layers.append(T.layer_baseline(c['lines'][1], st, qx0 + c.get('post_dx', 0), base_y - f.getbbox(c['lines'][1], anchor='ls')[3]))
        return clean1, clean4, union | dm1, layers

    # ------------------------------------------------------------------ for the eye
    def preview(self, name, final1, final4, item):
        g = self.g
        orig1 = g.composed(name)
        (self.out / 'preview').mkdir(parents=True, exist_ok=True)
        top = np.concatenate([orig1, final1], axis=1)
        bx = item.get('view') or item.get('clean', {}).get('box') or item.get('card', {}).get('box')
        x0, y0, x1, y1 = bx
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        w, h = 400, 75
        X0, Y0 = max(0, min(800 - w, cx - w // 2)), max(0, min(600 - h, cy - h // 2))
        o4 = g.art(name)[Y0 * 4:(Y0 + h) * 4, X0 * 4:(X0 + w) * 4]
        k4 = final4[Y0 * 4:(Y0 + h) * 4, X0 * 4:(X0 + w) * 4]
        crop = np.concatenate([o4, k4], axis=1)          # 3200 x 300
        crop = np.asarray(Image.fromarray(crop).resize((1600, 150), Image.LANCZOS))
        z1 = np.concatenate([orig1[Y0:Y0 + h, X0:X0 + w], final1[Y0:Y0 + h, X0:X0 + w]], axis=1)
        z1 = np.repeat(np.repeat(z1, 2, 0), 2, 1)          # 1600 x 150
        Image.fromarray(np.concatenate([top, z1, crop], axis=0)).save(self.out / 'preview' / f'{name}.png')


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    only = set(n.lower() for n in sys.argv[3:])
    b = Builder(run, out)
    for item in SP.ITEMS:                   # bases come before their deltas in ITEMS
        if only and item['name'].lower() not in only and not any(o in item['name'].lower() for o in only):
            continue
        b.build(item)
    import objects as OB                    # the things with Japanese written on them, after the floating lines
    things = OB.run_things(b, [t for t in OB.OS.THINGS if not only or t in only])   # named: those only (none if none named)
    b.dependents()
    (out / 'objects.json').write_text(json.dumps(things, ensure_ascii=False, indent=1), 'utf-8')
    last = {}
    for r in b.records:                     # a picture stored twice (two things on it) keeps its last record
        last[r['name']] = r
    (out / 'manifest.json').write_text(json.dumps({'runtime': str(run), 'made': time.strftime('%Y-%m-%d %H:%M'), 'pictures': list(last.values())},
                                                  ensure_ascii=False, indent=1), 'utf-8')


if __name__ == '__main__':
    main()
