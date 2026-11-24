"""Where the 4x art invented things (read-only on Codex's art and decoder), after the user's play on 10-25: 「CG에 흐린
부분은 제멋대로 검은 외곽선을 그어놨다던가, 버스가 뭉개졌다던가」.
Each picture is compared with its source enlarged smoothly (Lanczos x4). What the upscaler invents (dark contours in
out-of-focus areas, brush and paper texture on smooth surfaces) appears where the source is flat: only pixels whose 3x3
neighbourhood in the source varies by less than FLAT are looked at, the difference is blurred (so sharpened edges do not
count), and differences over STRONG are counted; darker-than-source ones separately (the black outlines). The mean colour
of large areas is compared too (the model is known to fade saturated reds).
python audit_upscale.py [--names a.rct b.rct ...] [--top N]   -> qa/upscale-audit/scores.json, sheet_###.png (worst first)
"""
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / 'qa' / 'upscale-audit'
FLAT, STRONG = 24, 40
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista-ko\tools')
import hires_assets  # noqa: E402  (Codex's decoder over its v9 runtime archives, read-only)


def entries():
    m = json.loads((HERE / 'runtime-play' / 'hires-manifest.json').read_text('utf-8-sig'))
    return [(e['name'], e['file']) for e in m['entries'] if 'size' in e and e['name'].lower().endswith('.rct')]


def score(name, file):
    src = hires_assets.decode(name)[:, :, :3].astype(np.uint8)            # RGB, source size
    art = cv2.imread(str(HERE / 'runtime-play' / 'hires' / file), cv2.IMREAD_COLOR)[:, :, ::-1]
    h, w = src.shape[:2]
    if art.shape[:2] != (h * 4, w * 4):
        return None
    smooth = cv2.resize(src, (w * 4, h * 4), interpolation=cv2.INTER_LANCZOS4)
    lum = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY)
    span = cv2.dilate(lum, np.ones((3, 3), np.uint8)).astype(np.int16) - cv2.erode(lum, np.ones((3, 3), np.uint8))
    flat = cv2.resize((span < FLAT).astype(np.uint8), (w * 4, h * 4), interpolation=cv2.INTER_NEAREST).astype(bool)
    d = art.astype(np.int16) - smooth.astype(np.int16)
    big = cv2.GaussianBlur(np.abs(d).max(axis=2).astype(np.float32), (5, 5), 0) > STRONG
    dark = cv2.GaussianBlur((-d).min(axis=2).astype(np.float32), (5, 5), 0) > STRONG    # darker in every channel
    inv, invd = big & flat, dark & flat
    n = int(flat.sum()) or 1
    small_a = cv2.resize(art, (w // 8, h // 8), interpolation=cv2.INTER_AREA).astype(np.int16)
    small_s = cv2.resize(src, (w // 8, h // 8), interpolation=cv2.INTER_AREA).astype(np.int16)
    shift = float(np.abs(small_a - small_s).max(axis=2).mean())
    return {'name': name, 'file': file, 'invented_pct': round(100 * inv.sum() / n, 3), 'dark_pct': round(100 * invd.sum() / n, 3),
            'flat_pct': round(100 * flat.mean(), 1), 'colour_shift': round(shift, 2)}, (src, art, inv, invd)


def sheet(rows, k):
    tiles = []
    for r in rows:
        _, (src, art, inv, invd) = score(r['name'], r['file'])
        h, w = src.shape[:2]
        heat = np.zeros_like(art)
        heat[inv] = (255, 200, 0)
        heat[invd] = (255, 40, 40)
        cells = [cv2.resize(x, (w, h), interpolation=cv2.INTER_AREA) for x in (cv2.resize(src, (w * 4, h * 4), interpolation=cv2.INTER_LANCZOS4), art)]
        cells.append(cv2.resize(cv2.dilate(heat, np.ones((9, 9), np.uint8)), (w, h), interpolation=cv2.INTER_AREA))   # thin marks stay visible
        tile = np.concatenate([cv2.resize(c, (400, 300), interpolation=cv2.INTER_AREA) for c in cells], axis=1)
        cv2.putText(tile, f"{r['name']} invented {r['invented_pct']}% dark {r['dark_pct']}%", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 2)
        tiles.append(tile)
    Image.fromarray(np.concatenate(tiles, axis=0)).save(OUT / f'sheet_{k:03d}.png')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    args = sys.argv[1:]
    top = int(args[args.index('--top') + 1]) if '--top' in args else 24
    todo = entries()
    if '--names' in args:
        want = {a.lower() for a in args[args.index('--names') + 1:] if not a.startswith('--')}
        todo = [e for e in todo if e[0].lower() in want]
    rows = []
    for i, (name, file) in enumerate(todo):
        try:
            r = score(name, file)
        except Exception as e:  # noqa: BLE001
            r = ({'name': name, 'file': file, 'error': repr(e)}, None)
        if r:
            rows.append(r[0])
        if i % 100 == 0:
            print(i, len(todo), flush=True)
    rows.sort(key=lambda r: -r.get('invented_pct', 0))
    (OUT / 'scores.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), 'utf-8')
    good = [r for r in rows if 'invented_pct' in r]
    for k in range(0, min(top, len(good)), 6):
        sheet(good[k:k + 6], k // 6)
    print(json.dumps(good[:12], ensure_ascii=False))
