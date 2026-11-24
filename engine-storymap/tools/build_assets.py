"""이야기 지도 UI art at 4x (3200x2400 basis) from label-free 1x game sources.

python build_assets.py  ->  build/storymap/*.png, build/storymap/thumb/*.jpg, build/assets-proof.json
RGB is upscaled with the same local model Codex used for the game's HD UI (Upscayl high-fidelity-4x);
alpha is resized with LANCZOS (no invented edges). Every model output is checked against its source.
"""
import json
import shutil
import subprocess
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

import mock_lib as L

HERE = L.HERE
WORK = HERE / 'build' / 'asset-work'
OUT = HERE / 'build' / 'storymap'
UPSCAYL = Path(r'P:\AI\Codex\projects\image-upscaling-tools\apps\Upscayl-2.15.0\resources')
HIRES = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\runtime-body-ui-20261024-v18-cg-switch\hires')
MANIFEST = HIRES.parent / 'hires-manifest.json'


def flood_alpha(rgb, thresh=14):
    """Transparent where near-black background connects to the image border; plate interiors stay opaque."""
    a = np.asarray(rgb.convert('RGB')).astype(int)
    h, w = a.shape[:2]
    dark = a.max(axis=2) <= thresh
    seen = np.zeros((h, w), bool)
    q = deque([(y, x) for y in range(h) for x in (0, w - 1) if dark[y, x]] + [(y, x) for x in range(w) for y in (0, h - 1) if dark[y, x]])
    for y, x in q:
        seen[y, x] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and dark[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    alpha = np.where(seen, 0, 255).astype('uint8')
    im = rgb.convert('RGBA')
    im.putalpha(Image.fromarray(alpha))
    return im


def outline_like(seg):
    mx, mn = seg.max(-1), seg.min(-1)
    return (mx >= 100) & (mx - mn <= 70)


def plate_interior(a, box, inset=1):
    """Pixels strictly inside a plate's light outline, row by row (outline pixels themselves excluded)."""
    x0, y0, x1, y1 = box
    mask = np.zeros(a.shape[:2], bool)
    line = outline_like(a.astype(int))
    edge = np.zeros_like(mask)
    for y in range(y0, y1):
        xs = np.nonzero(line[y, x0:x1])[0]
        if len(xs) >= 2 and xs.max() - xs.min() > 8:
            mask[y, x0 + xs.min() + inset:x0 + xs.max() - inset + 1] = True
            if line[y, x0 + xs.min():x0 + xs.max() + 1].mean() > 0.5:   # the top / bottom rule
                edge[y, x0 + xs.min():x0 + xs.max() + 1] = True
            else:                                                       # the slanted ends
                edge[y, x0 + xs.min():x0 + xs.min() + 4] = True
                edge[y, x0 + xs.max() - 3:x0 + xs.max() + 1] = True
    # only the real outline stays: light specks mid-row are old caption strokes and get refilled too
    mask &= ~(line & edge)
    # drop the outline's anti-aliased rim
    rim = mask.copy()
    rim[1:, :] &= mask[:-1, :]
    rim[:-1, :] &= mask[1:, :]
    return rim


def refill_plates(a):
    """Old Japanese button captions left smudges in the clean crimson-top and gold bars: refill their interiors.
    Crimson: tiles of the clean small crimson plate's granite (mirrored). Gold: the bar's own clean-end colour
    statistics carried by the game's grey noise texture. Outlines and pointed ends stay original."""
    a = a.copy()
    close = plate_interior(a, (658, 23, 728, 47))
    ys, xs = np.nonzero(close)
    patch = a[ys.min() + 2:ys.max() - 1, xs.min() + 4:xs.max() - 3].copy()
    ph, pw = patch.shape[:2]
    red = plate_interior(a, (496, 10, 658, 31))
    for y, x in zip(*np.nonzero(red)):
        tx = (x - 496) % (2 * pw)
        tx = tx if tx < pw else 2 * pw - 1 - tx
        a[y, x] = patch[(y - 10) % ph, tx]
    gold = plate_interior(a, (496, 38, 658, 59))
    ends = gold.copy()
    ends[:, 519:637] = False
    sample = a[ends].astype('float32')
    mean, std = sample.mean(0), sample.std(0)
    noise = np.asarray(L.decode('情報隠蔽.rc8')[0].convert('L')).astype('float32')
    noise = (noise - noise.mean()) / max(1.0, noise.std())
    for y, x in zip(*np.nonzero(gold)):
        n = noise[(y * 7) % noise.shape[0], (x * 3) % noise.shape[1]]
        a[y, x] = np.clip(mean + n * std * 0.85, 0, 255)
    return a


def shape_alpha(rgb, open_left=False):
    """Alpha from the plate's own light outline: inside = between the outermost outline pixels of each row."""
    a = np.asarray(rgb.convert('RGB')).astype(int)
    h, w = a.shape[:2]
    alpha = np.zeros((h, w), 'uint8')
    light = outline_like(a)
    # only the outer rim counts: ignore light pixels in the middle (the ⚜ glyph, granite highlights)
    edge = np.zeros_like(light)
    edge[:, :w // 5] = light[:, :w // 5]
    edge[:, -w // 5:] = light[:, -w // 5:]
    rows = [y for y in range(h) if edge[y].any()]
    if rows:
        top, bot = rows[0], rows[-1]
        for y in range(top, bot + 1):
            win = edge[max(top, y - 6):min(bot, y + 6) + 1]
            cols = np.nonzero(win.any(0))[0]
            right = cols.max()
            left = 0 if open_left else cols.min()
            own = np.nonzero(edge[y])[0]
            if len(own):
                right = max(right if open_left else own.max(), own.max())
                if not open_left:
                    left = own.min()
            alpha[y, left:right + 1] = 255
    im = rgb.convert('RGBA')
    im.putalpha(Image.fromarray(alpha))
    return im


def sources():
    s = {}
    frame = Image.open(L.CAND / 'ui-rest-v1' / 'clean' / 'クロニクル枠_off.rct.png').convert('RGB')
    a = refill_plates(np.asarray(frame))
    a[31:58, 148:301] = 0                                         # old title; uniform black beneath (Codex proof)
    alpha = 255 - np.asarray(L.decode('クロニクル枠_off_.rc8')[0].convert('L'))
    a[alpha < 128] = 0                                            # content window -> black sheet
    s['frame'] = Image.fromarray(a, 'RGB').convert('RGBA')
    plate = Image.open(L.CAND / 'name-display-v1' / 'clean' / '名前プレート_信哉.rct.png').convert('RGB')
    pa = 255 - np.asarray(L.decode('名前プレート_信哉_.rc8')[0].convert('L'))
    plate = plate.convert('RGBA')
    plate.putalpha(Image.fromarray(pa.astype('uint8')))
    s['plate_crimson'] = plate
    for k, bar in enumerate(L.choice_bars()):
        s[f'bar{k}'] = bar
    s['banner'] = shape_alpha(L.banner_blank().convert('RGB'), open_left=True)
    red, navy = L.chevron_plates()
    s['chev_red'] = shape_alpha(red.convert('RGB'))
    s['chev_navy'] = shape_alpha(navy.convert('RGB'))
    leaf = L.decoded('momiba5')
    s['leaf'] = leaf.crop(leaf.getbbox())
    s['stone_navy'] = L.decoded('クロニクル青バー').crop((22, 120, 96, 560))
    s['stone_gray'] = L.decode('クロニクル灰バー.rc8')[0].convert('RGBA').crop((22, 120, 96, 560))
    panel = L.decoded('バックログ画面')
    pa = np.asarray(panel).copy()
    pa[455:571, 16:770] = pa[290:406, 16:770]                    # drop the [RECONQUISTA] watermark under the list
    s['panel'] = Image.fromarray(pa, 'RGBA')
    return s


NOISE_ONLY = {'noise'}


def upscale_all(src):
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / 'in').mkdir(parents=True)
    (WORK / 'out').mkdir()
    for name, im in src.items():
        rgb = Image.new('RGB', im.size, (0, 0, 0))
        rgb.paste(im.convert('RGB'), mask=None)
        # premultiply-like matte: transparent pixels carry black so edges do not glow
        a = np.asarray(im)[..., 3:4].astype('float32') / 255
        rgbm = (np.asarray(im)[..., :3].astype('float32') * a).astype('uint8')
        Image.fromarray(rgbm, 'RGB').save(WORK / 'in' / f'{name}.png')
    log = (WORK / 'upscale.log').open('w')
    subprocess.run([str(UPSCAYL / 'bin' / 'upscayl-bin.exe'), '-i', str(WORK / 'in'), '-o', str(WORK / 'out'), '-n', 'high-fidelity-4x',
                    '-m', str(UPSCAYL / 'models'), '-s', '4', '-t', '256', '-j', '1:1:1', '-f', 'png'],
                   stdout=log, stderr=log, check=True, creationflags=0x08000000, cwd=WORK)
    log.close()
    proof = {}
    OUT.mkdir(parents=True, exist_ok=True)
    for name, im in src.items():
        out = Image.open(WORK / 'out' / f'{name}.png').convert('RGB')
        assert out.size == (im.width * 4, im.height * 4), (name, out.size)
        back = np.asarray(out.resize(im.size, Image.BOX)).astype(int)
        a = np.asarray(im)[..., 3:4].astype('float32') / 255
        ref = (np.asarray(im)[..., :3].astype('float32') * a).astype(int)
        diff = float(np.abs(back - ref).mean())
        dark = float(back.mean()) < 0.25 * max(1.0, float(ref.mean())) and float(ref.mean()) > 8
        proof[name] = {'mean_abs_diff_at_1x': round(diff, 2), 'source_mean': round(float(ref.mean()), 1), 'output_mean': round(float(back.mean()), 1)}
        if diff > 18 or dark:
            raise SystemExit(f'upscale check failed for {name}: {proof[name]}')
        alpha = Image.fromarray(np.asarray(im)[..., 3]).resize(out.size, Image.LANCZOS)
        rgba = out.convert('RGBA')
        # un-premultiply against the LANCZOS alpha so plate edges keep their colour
        o = np.asarray(rgba).astype('float32')
        al = np.asarray(alpha).astype('float32')[..., None] / 255
        rgb = np.where(al > 0.02, np.clip(o[..., :3] / np.maximum(al, 0.02), 0, 255), 0)
        final = np.concatenate([rgb, al * 255], axis=2).astype('uint8')
        Image.fromarray(final, 'RGBA').save(OUT / f'{name}.png', optimize=True)
    return proof


def navy_plate():
    crimson = Image.open(OUT / 'plate_crimson.png')
    L.hue_shift(crimson, 232, sat_mul=0.95, val_mul=1.05).save(OUT / 'plate_navy.png', optimize=True)


def noise_and_thumbs():
    noise = L.decode('情報隠蔽.rc8')[0].convert('RGB')
    noise.resize((noise.width * 4, noise.height * 4), Image.NEAREST).save(OUT / 'noise.png', optimize=True)
    proof = json.loads((HERE / 'build' / 'build-proof.json').read_text('utf-8'))
    m = json.loads(MANIFEST.read_text('utf-8'))
    by = {e['name'].lower(): e['file'] for e in m['entries']}
    (OUT / 'thumb').mkdir(exist_ok=True)
    missing = []
    for bg in proof['thumbnail_backgrounds']:
        f = by.get(bg.lower() + '.rct')
        if not f:
            missing.append(bg)
            continue
        im = Image.open(HIRES / f).convert('RGB').resize((256, 192), Image.LANCZOS)
        im.save(OUT / 'thumb' / f'{bg}.jpg', quality=90)
    return missing


if __name__ == '__main__':
    src = sources()
    proof = upscale_all(src)
    navy_plate()
    missing = noise_and_thumbs()
    (HERE / 'build' / 'assets-proof.json').write_text(json.dumps({'model': 'high-fidelity-4x', 'checks': proof, 'thumbs_missing': missing,
                                                              'alpha': 'LANCZOS from 1x source alpha'}, ensure_ascii=False, indent=1), 'utf-8')
    print(json.dumps({'ok': True, 'checks': proof, 'thumbs_missing': missing}, ensure_ascii=False))
