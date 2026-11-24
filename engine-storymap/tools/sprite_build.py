"""Standing pictures' 4K from Codex's AI upscale (the user, 10-25: 「인물 그림은 기존과 같이 high-fidelity-4x + 섞기로 하자.
코덱스는 AI 확대만, 나머지는 네가 해.」). Inputs: what sprite_prep.py gave Codex (rebuilt here from the archive) and Codex's
4x of each.
- a base: blended like the rest of the game's 4K art (blend_art.blend: the AI art on drawn lines, Lanczos elsewhere)
- an expression: its blended 4K (of the whole picture, or of its face crop when the job has crop_1x: sprite_job.py) cut
  to its box (sprite_index.py), the outer 32 pixels (the 1x margin of 8) faded into the base's blended 4K so the patch's
  edge is the base itself
- a mask: no AI; Lanczos x4 with its edge tightened (twice as steep about the middle), and every 4x4 block of a 1x clear
  pixel clear (the DLL's ClipMaskToBase), lossless
-> build/hires-jxl-sprites/<key>.jxl (bases, masks), build/hires-patch-sprites/<key>.jxl (expressions),
   build/sprites/hires-sprites.txt (the DLL's index for what was built), build/sprites/built.json
python sprite_build.py <sample.json or job.json> <ai dir> [--index <sprite-index.txt>] [--out <dry-run dir>] [--workers N]
A family (a base and its expressions) that fails a check is left out of the index (the game keeps its 1x) and listed.
"""
import argparse, functools, json, math, sys
from multiprocessing import Pool
from pathlib import Path
import cv2
import numpy as np
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'build' / 'pylib'))
import imagecodecs
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blend_art import blend, DISTANCE, RETRY_DISTANCE, MIN_PSNR, SPEED
from sprite_prep import filled, mask_of

OUT_ART = HERE / 'build' / 'hires-jxl-sprites'
OUT_PATCH = HERE / 'build' / 'hires-patch-sprites'
OUT_INDEX = HERE / 'build' / 'sprites'
MARGIN4 = 32    # the patch's fade into its base (sprite_index.MARGIN 8 at 1x)
THREADS = 4     # JPEG XL threads a picture (1 in a pool of workers)


def jxl(a, lossless=False):
    if lossless:
        return imagecodecs.jpegxl_encode(a, distance=0, effort=7, numthreads=THREADS), 99.0
    for d in (DISTANCE, RETRY_DISTANCE):
        data = imagecodecs.jpegxl_encode(a, distance=d, effort=7, decodingspeed=SPEED, numthreads=THREADS)
        back = imagecodecs.jpegxl_decode(data, numthreads=THREADS)
        mse = float(np.mean((back.astype(np.float64) - a.astype(np.float64)) ** 2))
        p = 99.0 if mse == 0 else 10 * math.log10(255 * 255 / mse)
        if back.shape == a.shape and p >= MIN_PSNR:
            return data, p
    raise ValueError(f'only {p:.1f} dB')


def nearer_own(small, own, other):
    """on the pixels where two 1x pictures differ, is the shrunk AI picture nearer the first? (a few changed pixels
    cannot tell, and a swap there would hardly show)"""
    m = np.abs(own - other).max(axis=2) > 8
    if m.sum() < 16:
        return True
    return np.abs(small - own)[m].mean() < np.abs(small - other)[m].mean()


def ai_of(ai_dir, key, own, others):
    """Codex's 4x of the 1x input <key> (own: that input, RGB); others: the same region of the other pictures of its
    family. Expressions differ only in the face, so a picture saved under a wrong name of its own family passes every
    whole-picture test (10-25: Codex's ai folder held all 12 under one another's names): shrunk back to 1x it must be
    near its own input, and nearer it than each other picture of the family where the two differ."""
    h, w = own.shape[:2]
    a = cv2.imread(str(Path(ai_dir) / f'{key}.png'), cv2.IMREAD_COLOR)
    if a is None or a.shape[:2] != (h * 4, w * 4):
        raise ValueError(f'{key}: AI art {None if a is None else a.shape[:2]} for 1x {h}x{w}')
    if a.mean() < 2:
        raise ValueError(f'{key}: AI art is black (a lost GPU writes black with exit code 0)')
    a = np.ascontiguousarray(a[:, :, ::-1])
    small = cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
    own = own.astype(np.float32)
    off = float(np.abs(small - own).mean())
    if off > 12:
        raise ValueError(f'{key}: the AI picture is not of its input (mean difference {off:.1f})')
    wrong = [k for k, o in others.items() if not nearer_own(small, own, o.astype(np.float32))]
    if wrong:
        m = np.zeros(own.shape[:2], bool)
        for o in others.values():
            m |= np.abs(o.astype(np.float32) - own).max(axis=2) > 8
        near = {k: float(np.abs(small - o.astype(np.float32))[m].mean()) for k, o in others.items()}
        near[key] = float(np.abs(small - own)[m].mean())
        raise ValueError(f'{key}: the AI picture under this name is nearer {", ".join(wrong)}, most like {min(near, key=near.get)} (saved under a wrong name?)')
    return a


def mask4(m1):
    h, w = m1.shape
    v = cv2.resize(m1.astype(np.float32), (w * 4, h * 4), interpolation=cv2.INTER_LANCZOS4)
    v = np.clip((v - 127.5) * 2 + 127.5, 0, 255)
    v[np.repeat(np.repeat(m1 == 255, 4, 0), 4, 1)] = 255
    v[np.repeat(np.repeat(m1 == 0, 4, 0), 4, 1)] = 0     # a fully shown 1x pixel stays fully shown
    return v.astype(np.uint8)


def fade(x, y, w4, h4, W4, H4):
    """1 inside, falling to 0 at the patch edge over MARGIN4 (smoothstep); a side on the picture's own edge does not fade
    (the box was cut short there, so its margin may hold changed pixels, and there is no base beyond it to meet)"""
    big = 1 << 20
    left = np.arange(w4) if x > 0 else np.full(w4, big)
    right = np.arange(w4)[::-1] if x + w4 < W4 else np.full(w4, big)
    top = np.arange(h4) if y > 0 else np.full(h4, big)
    bottom = np.arange(h4)[::-1] if y + h4 < H4 else np.full(h4, big)
    d = np.minimum(np.minimum(left, right)[None, :], np.minimum(top, bottom)[:, None]).astype(np.float32)
    t = np.clip(d / MARGIN4, 0, 1)
    return t * t * (3 - 2 * t)


def family(task, ai_dir, out_art, out_patch):
    """one base and its expressions -> (records, index lines) or {'error'}"""
    b, patches = task
    try:
        full = {b['key']: filled(b['name'])}
        for v in patches:
            full[v['key']] = filled(v['name'])
        W, H = b['size_1x']
        src = full[b['key']]
        others = {k: a for k, a in full.items() if k != b['key'] and a.shape == src.shape}
        out, kept = blend(src, ai_of(ai_dir, b['key'], src, others))
        data, p = jxl(out)
        (out_art / f"{b['key']}.jxl").write_bytes(data)
        recs = {'bases': [{'name': b['name'], 'key': b['key'], 'ai_kept_pct': round(100 * kept, 1), 'psnr': round(p, 1), 'bytes': len(data)}], 'patches': []}
        lines = []
        for v in patches:
            x, y, w, h = v.get('crop_1x') or [0, 0, W, H]
            own = np.ascontiguousarray(full[v['key']][y:y + h, x:x + w])
            others = {k: a[y:y + h, x:x + w] for k, a in full.items() if k != v['key'] and a.shape == src.shape}
            o, kept = blend(own, ai_of(ai_dir, v['key'], own, others))
            bx, by, bw, bh = v['box_4k']
            px, py = bx - x * 4, by - y * 4                     # the box inside the crop
            base4 = out[by:by + bh, bx:bx + bw].astype(np.float32)
            t = fade(bx, by, bw, bh, W * 4, H * 4)[..., None]
            patch = np.clip(o[py:py + bh, px:px + bw].astype(np.float32) * t + base4 * (1 - t) + 0.5, 0, 255).astype(np.uint8)
            data, p = jxl(patch)
            (out_patch / f"{v['key']}.jxl").write_bytes(data)
            x1, y1, w1, h1 = v['box_1x']
            lines.append(f"P {v['key']} {v['base_key']} {x1} {y1} {w1} {h1}")
            recs['patches'].append({'name': v['name'], 'key': v['key'], 'base_key': v['base_key'], 'ai_kept_pct': round(100 * kept, 1),
                                    'psnr': round(p, 1), 'bytes': len(data)})
        return recs, lines
    except Exception as e:
        return {'error': f"{b['name']}: {e!r}"}, []


def one_mask(m, out_art):
    m4 = mask4(mask_of(m['name'][:-5] + '.rct'))
    data, _ = jxl(m4, lossless=True)
    (out_art / f"{m['key']}.jxl").write_bytes(data)
    return {'name': m['name'], 'key': m['key'], 'bytes': len(data), 'used_by': len(m['used_by'])}


def pool_init():
    global THREADS
    THREADS = 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sample')
    ap.add_argument('ai')
    ap.add_argument('--index', default=None)
    ap.add_argument('--out', default=None, help='a dry run: the three outputs under this folder instead of build/')
    ap.add_argument('--workers', type=int, default=1)
    args = ap.parse_args()
    sample = json.loads(Path(args.sample).read_text('utf-8'))
    out_art, out_patch, out_index = OUT_ART, OUT_PATCH, OUT_INDEX
    if args.out:
        out_art, out_patch, out_index = Path(args.out) / 'hires-jxl-sprites', Path(args.out) / 'hires-patch-sprites', Path(args.out) / 'sprites'
    for d in (out_art, out_patch, out_index):
        d.mkdir(parents=True, exist_ok=True)
    tasks = [(b, [v for v in sample['patches'] if v['base_key'] == b['key']]) for b in sample['bases']]
    built, lines, errors = {'bases': [], 'patches': [], 'masks': []}, [], []
    run = functools.partial(family, ai_dir=args.ai, out_art=out_art, out_patch=out_patch)
    mrun = functools.partial(one_mask, out_art=out_art)
    if args.workers > 1:
        with Pool(args.workers, initializer=pool_init) as pool:
            fams = list(pool.imap_unordered(run, tasks))
            built['masks'] = list(pool.imap_unordered(mrun, sample['masks'], chunksize=8))
    else:
        fams = [run(t) for t in tasks]
        built['masks'] = [mrun(m) for m in sample['masks']]
    for recs, ls in fams:
        if 'error' in recs:
            errors.append(recs['error'])
            continue
        built['bases'] += recs['bases']
        built['patches'] += recs['patches']
        lines += ls
    # masks: every mask in the index whose file was built (expressions share their base's)
    have = {m['key'] for m in sample['masks']}
    if args.index:
        for l in Path(args.index).read_text('ascii').splitlines():
            if l.startswith('M ') and l.split()[2] in have:
                lines.append(l)
    built['errors'] = errors
    (out_index / 'hires-sprites.txt').write_text('\n'.join(sorted(lines)) + '\n', 'ascii')
    (out_index / 'built.json').write_text(json.dumps(built, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    print(json.dumps({k: len(v) for k, v in built.items()}), 'index lines', len(lines))
    for e in errors[:20]:
        print('error', e)


if __name__ == '__main__':
    main()
