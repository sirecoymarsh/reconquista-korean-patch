"""Codex's checked redraws and cloud repairs (tools/check_redraw.py, check_cloud.py) as JPEG XL like the rest of the 4x art,
ready for make_runtime.py, which links them over the blend: cloud\<key>.png -> build/hires-jxl-cloud, <key>.png at the
delivery's top (the redrawn pictures, which win over cloud) -> build/hires-jxl-redraw. Distance 0.5, decoding speed 3,
decoded back and kept only at 40 dB or better (else 0.3), as tools/blend_art.py. A file whose PNG is unchanged since its
JXL was made is skipped. Idle priority: the user may be playing.
python pack_redraw.py   -> build/hires-jxl-redraw/<key>.jxl, build/hires-jxl-cloud/<key>.jxl, each with manifest.json
"""
import ctypes
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x40)
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'build' / 'pylib'))
import imagecodecs  # noqa: E402

DELIVERY = Path(r'P:\AI\Codex\projects\reconquista-ko\deliverables\redraw-4k-20261025')
JOBS = ((DELIVERY, HERE / 'build' / 'hires-jxl-redraw'), (DELIVERY / 'cloud', HERE / 'build' / 'hires-jxl-cloud'))


def encode(rgb):
    for d in (0.5, 0.3):
        data = imagecodecs.jpegxl_encode(rgb, distance=d, effort=7, decodingspeed=3, numthreads=4)
        back = imagecodecs.jpegxl_decode(data, numthreads=4)
        mse = float(np.mean((back.astype(np.float64) - rgb.astype(np.float64)) ** 2))
        p = 99.0 if mse == 0 else 10 * math.log10(255 * 255 / mse)
        if back.shape == rgb.shape and p >= 40.0:
            return data, d, p
    raise ValueError(f'only {p:.1f} dB at distance 0.3')


for src_dir, out_dir in JOBS:
    out_dir.mkdir(parents=True, exist_ok=True)
    man_path = out_dir / 'manifest.json'
    man = json.loads(man_path.read_text('utf-8')) if man_path.exists() else {}
    t0, done = time.perf_counter(), 0
    for p in sorted(src_dir.glob('*.png')):
        key, st = p.stem.lower(), p.stat()
        if len(key) != 8 or any(c not in '0123456789abcdef' for c in key):
            continue
        if man.get(key, {}).get('png_mtime_ns') == st.st_mtime_ns and (out_dir / f'{key}.jxl').exists():
            continue
        rgb = np.ascontiguousarray(np.asarray(Image.open(p).convert('RGB')))
        if rgb.shape != (2400, 3200, 3):
            print(f'{key}: skipped, {rgb.shape}', flush=True)
            continue
        data, d, ps = encode(rgb)
        tmp = out_dir / f'{key}.jxl.tmp'
        tmp.write_bytes(data)
        os.replace(tmp, out_dir / f'{key}.jxl')
        man[key] = {'png': str(p), 'png_mtime_ns': st.st_mtime_ns, 'png_bytes': st.st_size, 'distance': d, 'psnr': round(ps, 2), 'jxl_bytes': len(data)}
        man_path.write_text(json.dumps(man, ensure_ascii=False, indent=1), 'utf-8')
        done += 1
    print(json.dumps({'folder': out_dir.name, 'packed': done, 'total': len(man), 'min_psnr': min((v['psnr'] for v in man.values()), default=None),
                      'minutes': round((time.perf_counter() - t0) / 60, 1)}), flush=True)
