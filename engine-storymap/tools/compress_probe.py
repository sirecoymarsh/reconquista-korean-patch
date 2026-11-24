"""Lossless size options for the 4x art, on a sample (read-only on the art; temp files are deleted).
For each sample: PNG as shipped, PNG at the strongest zlib setting, WebP lossless (method 4 and 6). Sizes, Pillow decode
time, and whether every decoded pixel equals the shipped PNG's.
python compress_probe.py [count]   -> qa/compress_probe.json
"""
import json
import statistics as st
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parents[1]
HIRES = HERE / 'runtime-play' / 'hires'
TMP = HERE / 'build' / 'temp' / 'compress'
TMP.mkdir(parents=True, exist_ok=True)
count = int(sys.argv[1]) if len(sys.argv) > 1 else 16

files = sorted(HIRES.glob('*.png'), key=lambda p: p.stat().st_size)
big = [p for p in files if p.stat().st_size > 1 << 20]
sample = [big[int(i * (len(big) - 1) / (count - 1))] for i in range(count)]   # spread over the size range


def decode(path):
    t = time.perf_counter()
    with Image.open(path) as im:
        im.load()
        px = im.tobytes()
        mode = im.mode
    return time.perf_counter() - t, px, mode


rows = []
for p in sample:
    t_png, ref, mode = decode(p)
    with Image.open(p) as im:
        im.load()
        out = {}
        q = TMP / 'opt.png'
        im.save(q, optimize=True, compress_level=9)
        t, px, _ = decode(q)
        out['png_max'] = (q.stat().st_size, t, px == ref)
        for m in (4, 6):
            w = TMP / f'm{m}.webp'
            t0 = time.perf_counter()
            im.save(w, 'WEBP', lossless=True, quality=100, method=m, exact=True)
            enc = time.perf_counter() - t0
            t, px, m2 = decode(w)
            if m2 != mode:   # gray comes back as RGB from WebP; compare one channel
                with Image.open(w) as wi:
                    px = wi.convert(mode).tobytes()
            out[f'webp_m{m}'] = (w.stat().st_size, t, px == ref, enc)
    row = {'file': p.name, 'mode': mode, 'png': p.stat().st_size, 'png_decode_s': round(t_png, 3)}
    for k, v in out.items():
        row[k] = {'bytes': v[0], 'ratio': round(v[0] / p.stat().st_size, 3), 'decode_s': round(v[1], 3), 'identical': v[2], **({'encode_s': round(v[3], 1)} if len(v) > 3 else {})}
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)

for q in TMP.glob('*'):
    q.unlink()
summary = {}
for k in ('png_max', 'webp_m4', 'webp_m6'):
    summary[k] = {'size_ratio_median': round(st.median(r[k]['ratio'] for r in rows), 3),
                  'decode_vs_png_median': round(st.median(r[k]['decode_s'] / r['png_decode_s'] for r in rows), 2),
                  'all_identical': all(r[k]['identical'] for r in rows)}
summary['png_decode_s_median'] = round(st.median(r['png_decode_s'] for r in rows), 3)
(HERE / 'qa' / 'compress_probe.json').write_text(json.dumps({'rows': rows, 'summary': summary}, ensure_ascii=False, indent=1), 'utf-8')
print(json.dumps(summary, ensure_ascii=False))
