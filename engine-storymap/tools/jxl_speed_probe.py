"""Encoder settings that make the 32-bit decode faster: the same art at distance 0.5 with decodingspeed 0-4 (libjxl's
faster_decoding tier), written to build/jxl-speedtest/<key>-s<tier>.jxl for jxlbench, with size and PSNR printed.
python jxl_speed_probe.py key...
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'build' / 'pylib'))
import imagecodecs  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

OUT = HERE / 'build' / 'jxl-speedtest'
for key in sys.argv[1:]:
    ref = np.asarray(Image.open(HERE / 'runtime-play' / 'hires' / f'{key}.png').convert('RGB'))
    for tier in range(5):
        data = imagecodecs.jpegxl_encode(ref, distance=0.5, effort=7, decodingspeed=tier, numthreads=12)
        back = imagecodecs.jpegxl_decode(data, numthreads=12)
        mse = float(np.mean((back.astype(np.float64) - ref) ** 2))
        (OUT / f'{key}-s{tier}.jxl').write_bytes(data)
        print(f'{key} s{tier} {len(data) / 2**20:6.2f} MB  psnr {10 * math.log10(65025 / mse):.2f}', flush=True)
