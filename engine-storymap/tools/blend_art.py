"""4x art rebuilt by blending (the user, 10-25: 「섞기 방식으로 4K 그림을 전부 여기서 다시 만들어 줘」).
Codex's 4x art (Upscayl high-fidelity-4x, candidates/hires-v1) invents what its source does not have where the source is
soft: dark contours in out-of-focus areas, cracked lines in fine grain, sand on painted ground, brush and paper texture on
smooth surfaces (qa/upscale-compare/choice-sheet.png). On the source's drawn lines it is clean and sharp, so it is kept
there; everywhere else the source is enlarged with Lanczos. The weight is the source's edge strength (Sobel magnitude of
the luminance, 3x3 blurred): 0 below 40, 1 above 120, enlarged and feathered (9x9 at 4x).
Only the 1,758 AI pictures (all still Codex's upscale output byte for byte; not the menus, whose lettering was drawn at
4x). Codex's PNGs are only read (hard links shared with its folders). The result is JPEG XL like the rest of the art
(distance 0.5, decoding speed 3, decoded back and kept only at 40 dB or better, else distance 0.3) in build/hires-jxl-blend,
which make_runtime.py links over build/hires-jxl. Resumable; stops when P: has less than 4 GB free.
python blend_art.py [--workers 4] [--threads 3] [--limit N] [--names a.rct ...]   -> build/hires-jxl-blend/<key>.jxl, manifest.json
"""
import argparse
import ctypes
import json
import math
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'build' / 'pylib'))
ART = HERE / 'runtime-play' / 'hires'
OUT = HERE / 'build' / 'hires-jxl-blend'
MANIFEST = OUT / 'manifest.json'
EDGE_LO, EDGE_HI, FEATHER, VERSION = 40, 120, 9, 1
DISTANCE, RETRY_DISTANCE, MIN_PSNR, SPEED = 0.5, 0.3, 40.0, 3
MIN_FREE = 4 << 30


def pictures():
    m = json.loads((HERE / 'runtime-play' / 'hires-manifest.json').read_text('utf-8-sig'))
    return [e for e in m['entries'] if 'archive' in e and 'size' in e and e['name'].lower().endswith('.rct') and 'group' not in e]


def blend(src, ai):
    """src: source RGB (h, w, 3) uint8; ai: the 4x art RGB. -> blended 4x RGB uint8, share of the art kept"""
    import cv2
    import numpy as np
    h, w = src.shape[:2]
    g = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY).astype(np.float32)
    edge = cv2.GaussianBlur(cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)), (3, 3), 0)
    m = np.clip((edge - EDGE_LO) / (EDGE_HI - EDGE_LO), 0, 1)
    m = cv2.GaussianBlur(cv2.resize(m, (w * 4, h * 4), interpolation=cv2.INTER_LINEAR), (FEATHER, FEATHER), 0)
    soft = cv2.resize(src, (w * 4, h * 4), interpolation=cv2.INTER_LANCZOS4)
    return cv2.blendLinear(np.ascontiguousarray(ai), soft, m, 1 - m), float(m.mean())


def work(entry, threads):
    import cv2
    import imagecodecs
    import numpy as np
    sys.path.insert(0, r'P:\AI\Codex\projects\reconquista-ko\tools')
    import hires_assets  # noqa: E402  (Codex's decoder over its v9 runtime archives, read-only)
    t0 = time.perf_counter()
    key, name = entry['file'][:8], entry['name']
    src = np.ascontiguousarray(hires_assets.decode(name)[:, :, :3]).astype(np.uint8)
    ai = cv2.imread(str(ART / entry['file']), cv2.IMREAD_COLOR)
    if ai is None or ai.shape[:2] != (src.shape[0] * 4, src.shape[1] * 4):
        raise ValueError(f'{name}: art {None if ai is None else ai.shape} for source {src.shape}')
    out, kept = blend(src, ai[:, :, ::-1])
    for d in (DISTANCE, RETRY_DISTANCE):
        data = imagecodecs.jpegxl_encode(out, distance=d, effort=7, decodingspeed=SPEED, numthreads=threads)
        back = imagecodecs.jpegxl_decode(data, numthreads=threads)
        mse = float(np.mean((back.astype(np.float64) - out.astype(np.float64)) ** 2))
        p = 99.0 if mse == 0 else 10 * math.log10(255 * 255 / mse)
        if back.shape == out.shape and p >= MIN_PSNR:
            break
    else:
        raise ValueError(f'{name}: only {p:.1f} dB at distance {d}')
    small = cv2.resize(out, (src.shape[1], src.shape[0]), interpolation=cv2.INTER_AREA).astype(np.int16)
    tmp = OUT / f'{key}.jxl.tmp'
    tmp.write_bytes(data)
    os.replace(tmp, OUT / f'{key}.jxl')
    st = (ART / entry['file']).stat()
    return key, {'name': name, 'version': VERSION, 'kept_pct': round(100 * kept, 1), 'distance': d, 'psnr': round(p, 2),
                 'source_mad': round(float(np.abs(small - src.astype(np.int16)).mean()), 2), 'jxl_bytes': len(data),
                 'art_bytes': st.st_size, 'art_mtime_ns': st.st_mtime_ns, 'seconds': round(time.perf_counter() - t0, 2)}


def save(manifest):
    tmp = MANIFEST.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=0, sort_keys=True), 'utf-8')
    os.replace(tmp, MANIFEST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--names', nargs='*')
    args = ap.parse_args()
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)   # below normal; workers inherit it
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text('utf-8')) if MANIFEST.exists() else {}
    todo = []
    for e in pictures():
        key = e['file'][:8]
        if args.names and e['name'].lower() not in {n.lower() for n in args.names}:
            continue
        st = (ART / e['file']).stat()
        old = manifest.get(key)
        if old and old.get('version') == VERSION and old['art_bytes'] == st.st_size and old['art_mtime_ns'] == st.st_mtime_ns and (OUT / f'{key}.jxl').exists():
            continue
        todo.append(e)
    if args.limit:
        todo = todo[:args.limit]
    print(f'todo {len(todo)} of {len(pictures())}', flush=True)
    t0, done, failed = time.perf_counter(), 0, []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = {}
        pending = list(todo)
        while pending or jobs:
            while pending and len(jobs) < args.workers * 2:
                if shutil.disk_usage('P:\\').free < MIN_FREE:
                    print('STOP: less than 4 GB free on P:', flush=True)
                    pending = []
                    break
                e = pending.pop(0)
                jobs[pool.submit(work, e, args.threads)] = e
            if not jobs:
                break
            job = next(as_completed(jobs))
            e = jobs.pop(job)
            try:
                key, row = job.result()
            except Exception as ex:  # the key keeps its current art
                failed.append(e['name'])
                print(f'FAIL {e["name"]} {ex}', flush=True)
                continue
            manifest[key] = row
            done += 1
            if done % 25 == 0 or not (pending or jobs):
                save(manifest)
                el, free = time.perf_counter() - t0, shutil.disk_usage('P:\\').free / 2**30
                print(f'{done}/{len(todo)} {el / 60:.1f} min, eta {el / done * (len(todo) - done) / 60:.1f} min, free {free:.1f} GB', flush=True)
    save(manifest)
    rows = list(manifest.values())
    print(json.dumps({'blended': len(rows), 'failed': failed, 'jxl_gb': round(sum(r['jxl_bytes'] for r in rows) / 2**30, 2),
                      'min_psnr': min((r['psnr'] for r in rows), default=None), 'retried_at_0.3': sum(r['distance'] == RETRY_DISTANCE for r in rows),
                      'max_source_mad': max((r['source_mad'] for r in rows), default=None)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
