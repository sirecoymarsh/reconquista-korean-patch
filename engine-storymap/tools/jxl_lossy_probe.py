"""Lossy JPEG XL for the 4x art: size, decode time and difference per distance, on the compress_probe sample, plus a
side-by-side crop of one 도입부 2 background (bg_260b = 181c0121) for judging by eye (no later-story art is shown).
python jxl_lossy_probe.py   -> qa/jxl_lossy_probe.json, qa/jxl_compare_bg260b.png
"""
import json
import math
import statistics as st
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'build' / 'pylib'))
import imagecodecs  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

HIRES = HERE / 'runtime-play' / 'hires'
DISTANCES = [0.5, 1.0, 1.5, 2.0]
files = sorted(HIRES.glob('*.png'), key=lambda p: p.stat().st_size)
big = [p for p in files if p.stat().st_size > 1 << 20]
sample = [big[int(i * (len(big) - 1) / 11)] for i in range(12)]
total_png = sum(p.stat().st_size for p in files)


def timed(fn, *a, **k):
    t = time.perf_counter()
    r = fn(*a, **k)
    return time.perf_counter() - t, r


def psnr(a, b):
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else 10 * math.log10(255 * 255 / mse)


rows = []
for p in sample:
    ref = np.asarray(Image.open(p).convert('RGB'))
    t_png, _ = timed(lambda: np.asarray(Image.open(p).convert('RGB')))
    row = {'file': p.name, 'png': p.stat().st_size, 'png_decode_s': round(t_png, 3)}
    for d in DISTANCES:
        t_enc, data = timed(imagecodecs.jpegxl_encode, ref, distance=d, effort=7, numthreads=12)
        t12, out = timed(imagecodecs.jpegxl_decode, data, numthreads=12)
        t1, _ = timed(imagecodecs.jpegxl_decode, data, numthreads=1)
        diff = np.abs(out.astype(np.int16) - ref.astype(np.int16))
        row[f'd{d}'] = {'bytes': len(data), 'ratio': round(len(data) / p.stat().st_size, 4), 'encode_s': round(t_enc, 2),
                        'decode_12t_s': round(t12, 3), 'decode_1t_s': round(t1, 3), 'psnr': round(psnr(out, ref), 2),
                        'max_diff': int(diff.max()), 'pixels_off_by_more_than_8': round(float(np.mean(diff.max(axis=2) > 8)), 5)}
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)

summary = {'png_total_gb': round(total_png / 2**30, 2), 'png_decode_s_median': round(st.median(r['png_decode_s'] for r in rows), 3)}
for d in DISTANCES:
    k = f'd{d}'
    ratio = st.median(r[k]['ratio'] for r in rows)
    summary[k] = {'size_ratio_median': round(ratio, 4), 'projected_total_gb': round(total_png * ratio / 2**30, 2),
                  'decode_12t_s_median': round(st.median(r[k]['decode_12t_s'] for r in rows), 3),
                  'decode_1t_s_median': round(st.median(r[k]['decode_1t_s'] for r in rows), 3),
                  'psnr_median': round(st.median(r[k]['psnr'] for r in rows), 2),
                  'encode_s_median': round(st.median(r[k]['encode_s'] for r in rows), 2)}

# eye check: a 도입부 2 background, a 520x390 crop at 1:1 4K pixels, original then each distance
bg = HIRES / '181c0121.png'
ref = np.asarray(Image.open(bg).convert('RGB'))
h, w = ref.shape[:2]
x0, y0, cw, ch = w // 2 - 260, h // 2 - 195, 520, 390
tiles = [('원본 PNG (%.1f MB)' % (bg.stat().st_size / 2**20), ref)]
for d in DISTANCES:
    data = imagecodecs.jpegxl_encode(ref, distance=d, effort=7, numthreads=12)
    tiles.append(('JPEG XL d=%.1f (%.1f MB)' % (d, len(data) / 2**20), imagecodecs.jpegxl_decode(data, numthreads=12)))
sheet = Image.new('RGB', (cw * len(tiles) + 10 * (len(tiles) - 1), ch + 28), (24, 24, 24))
draw = ImageDraw.Draw(sheet)
for i, (label, arr) in enumerate(tiles):
    sheet.paste(Image.fromarray(arr[y0:y0 + ch, x0:x0 + cw]), (i * (cw + 10), 28))
    draw.text((i * (cw + 10) + 6, 6), label, fill=(235, 235, 235))
out = HERE / 'qa' / 'jxl_compare_bg260b.png'
sheet.save(out)
summary['compare_sheet'] = str(out)
(HERE / 'qa' / 'jxl_lossy_probe.json').write_text(json.dumps({'rows': rows, 'summary': summary}, ensure_ascii=False, indent=1), 'utf-8')
print(json.dumps(summary, ensure_ascii=False), flush=True)
