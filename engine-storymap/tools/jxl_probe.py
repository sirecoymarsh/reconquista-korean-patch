"""JPEG XL lossless for the 4x art, on the same sample as compress_probe.py (read-only on the art; nothing is written but
the result). imagecodecs lives in build\pylib. For each sample and setting: size vs the shipped PNG, decode time on one
thread and on twelve, encode time, and whether every decoded pixel equals the PNG's.
python jxl_probe.py [count]   -> qa/jxl_probe.json
"""
import json
import statistics as st
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'build' / 'pylib'))
import imagecodecs  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

HIRES = HERE / 'runtime-play' / 'hires'
count = int(sys.argv[1]) if len(sys.argv) > 1 else 12
files = sorted(HIRES.glob('*.png'), key=lambda p: p.stat().st_size)
big = [p for p in files if p.stat().st_size > 1 << 20]
sample = [big[int(i * (len(big) - 1) / (count - 1))] for i in range(count)]
gray = [p for p in files if p.stat().st_size > 1 << 20 and Image.open(p).mode == 'L'][:2]
SETTINGS = {'e5': dict(effort=5), 'e7': dict(effort=7), 'e7_fastdec': dict(effort=7, decodingspeed=2)}


def timed(fn, *a, **k):
    t = time.perf_counter()
    r = fn(*a, **k)
    return time.perf_counter() - t, r


rows = []
for p in sample + gray:
    t_png, im = timed(lambda: Image.open(p).convert(Image.open(p).mode))
    ref = np.asarray(im)
    row = {'file': p.name, 'mode': im.mode, 'png': p.stat().st_size, 'png_decode_s': round(t_png, 3)}
    for name, opt in SETTINGS.items():
        t_enc, data = timed(imagecodecs.jpegxl_encode, ref, lossless=True, numthreads=12, **opt)
        t1, a1 = timed(imagecodecs.jpegxl_decode, data, numthreads=1)
        t12, a12 = timed(imagecodecs.jpegxl_decode, data, numthreads=12)
        row[name] = {'bytes': len(data), 'ratio': round(len(data) / p.stat().st_size, 3), 'encode_s': round(t_enc, 2),
                     'decode_1t_s': round(t1, 3), 'decode_12t_s': round(t12, 3),
                     'identical': bool(np.array_equal(a1, ref) and np.array_equal(a12, ref))}
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)

summary = {'imagecodecs': imagecodecs.__version__, 'jpegxl': getattr(imagecodecs, 'jpegxl_version', lambda: '?')()}
rgb = [r for r in rows if r['mode'] == 'RGB']
for name in SETTINGS:
    summary[name] = {'size_ratio_median': round(st.median(r[name]['ratio'] for r in rgb), 3),
                     'decode_1t_vs_png': round(st.median(r[name]['decode_1t_s'] / r['png_decode_s'] for r in rgb), 2),
                     'decode_12t_vs_png': round(st.median(r[name]['decode_12t_s'] / r['png_decode_s'] for r in rgb), 2),
                     'decode_12t_s_median': round(st.median(r[name]['decode_12t_s'] for r in rgb), 3),
                     'encode_s_median': round(st.median(r[name]['encode_s'] for r in rgb), 2),
                     'all_identical': all(r[name]['identical'] for r in rows)}
summary['png_decode_s_median'] = round(st.median(r['png_decode_s'] for r in rgb), 3)
(HERE / 'qa' / 'jxl_probe.json').write_text(json.dumps({'rows': rows, 'summary': summary}, ensure_ascii=False, indent=1), 'utf-8')
print(json.dumps(summary, ensure_ascii=False), flush=True)
