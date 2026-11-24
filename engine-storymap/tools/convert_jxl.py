"""JPEG XL copies of the 4x art for the HD layer. The PNGs in runtime-play/hires are only read (they are hard links shared
with Codex's folders). RGB art goes lossy at distance 0.5 (about 48 dB, the setting chosen 10-24 after the eye-check
sheets) with decoding speed tier 3: in the game's 32-bit libjxl (SSE2 only) that decodes 35-40% faster for about 3%
more bytes at the same score. The 154 gray UI masks (8-bit L, the uiGrayKeys list) stay PNG: lossless JXL decoded them
three times slower. Every output is decoded back and checked before it is kept; art must stay at 40 dB or better (else
it is redone at distance 0.3). tools/select_jxl.py later drops the copies that still decode slower than their PNG.
Resumable: a key whose source size and time and settings match the manifest and whose .jxl exists is skipped.
python convert_jxl.py [--workers 2] [--threads 6] [--limit N]   -> build/hires-jxl/<key>.jxl, build/hires-jxl/manifest.json
"""
import argparse
import ctypes
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'build' / 'pylib'))
SRC = HERE / 'runtime-play' / 'hires'
OUT = HERE / 'build' / 'hires-jxl'
SLOWER = HERE / 'build' / 'hires-jxl-slower'   # copies select_jxl.py set aside: done, not redone
MANIFEST = OUT / 'manifest.json'
DISTANCE, RETRY_DISTANCE, MIN_PSNR, SPEED = 0.5, 0.3, 40.0, 3


def psnr(a, b):
    import numpy as np
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return 99.0 if mse == 0 else 10 * math.log10(255 * 255 / mse)


def convert(src, threads):
    import imagecodecs
    import numpy as np
    from PIL import Image
    t0 = time.perf_counter()
    with Image.open(src) as im:
        arr = np.asarray(im.convert('RGB'))
    for d in (DISTANCE, RETRY_DISTANCE):
        data = imagecodecs.jpegxl_encode(arr, distance=d, effort=7, decodingspeed=SPEED, numthreads=threads)
        back = imagecodecs.jpegxl_decode(data, numthreads=threads)
        if back.shape != arr.shape:
            raise ValueError(f'{src.name}: decoded shape {back.shape} != {arr.shape}')
        p = psnr(back, arr)
        if p >= MIN_PSNR:
            break
    else:
        raise ValueError(f'{src.name}: only {p:.1f} dB at distance {d}')
    diff = np.abs(back.astype(np.int16) - arr.astype(np.int16))
    row = {'mode': 'RGB', 'w': int(arr.shape[1]), 'h': int(arr.shape[0]), 'speed': SPEED, 'distance': d, 'psnr': round(p, 2),
           'max_diff': int(diff.max())}
    tmp = OUT / f'{src.stem}.jxl.tmp'
    tmp.write_bytes(data)
    os.replace(tmp, OUT / f'{src.stem}.jxl')
    row.update(jxl_bytes=len(data), seconds=round(time.perf_counter() - t0, 2))
    return row


def save(manifest):
    tmp = MANIFEST.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=0, sort_keys=True), 'utf-8')
    os.replace(tmp, MANIFEST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--threads', type=int, default=6)
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # below normal; workers inherit it
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text('utf-8')) if MANIFEST.exists() else {}
    todo = []
    for src in sorted(SRC.glob('*.png')):
        with open(src, 'rb') as f:
            gray = f.read(26)[25] == 0   # IHDR colour type 0: the uiGrayKeys masks
        if gray:
            manifest.pop(src.stem, None)
            (OUT / f'{src.stem}.jxl').unlink(missing_ok=True)   # lossless copies from the first run
            continue
        st = src.stat()
        old = manifest.get(src.stem)
        if (old and old['src_bytes'] == st.st_size and old['src_mtime_ns'] == st.st_mtime_ns and old.get('speed') == SPEED
                and ((OUT / f'{src.stem}.jxl').exists() or (SLOWER / f'{src.stem}.jxl').exists())):
            continue
        todo.append((src, st))
    if args.limit:
        todo = todo[:args.limit]
    print(f'todo {len(todo)} of {len(list(SRC.glob("*.png")))}', flush=True)
    t0, done, failed = time.perf_counter(), 0, []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(convert, src, args.threads): (src, st) for src, st in todo}
        for job in as_completed(jobs):
            src, st = jobs[job]
            try:
                row = job.result()
            except Exception as ex:  # keep going; the PNG stays the fallback for this key
                failed.append(src.stem)
                print(f'FAIL {src.stem} {ex}', flush=True)
                continue
            row.update(src_bytes=st.st_size, src_mtime_ns=st.st_mtime_ns)
            manifest[src.stem] = row
            done += 1
            if done % 25 == 0 or done == len(todo):
                save(manifest)
                el = time.perf_counter() - t0
                print(f'{done}/{len(todo)} {el / 60:.1f} min, eta {el / done * (len(todo) - done) / 60:.1f} min', flush=True)
    save(manifest)
    png = sum(r['src_bytes'] for r in manifest.values())
    jxl = sum(r['jxl_bytes'] for r in manifest.values())
    art = [r for r in manifest.values() if r['mode'] == 'RGB']
    print(json.dumps({'converted': len(manifest), 'failed': failed, 'png_gb': round(png / 2**30, 2), 'jxl_gb': round(jxl / 2**30, 2),
                      'min_psnr': min((r['psnr'] for r in art), default=None),
                      'retried_at_0.3': sum(r['distance'] == RETRY_DISTANCE for r in art)}), flush=True)


if __name__ == '__main__':
    main()
