"""Inputs for Codex's AI upscale of standing pictures (the user, 10-25: 「인물 그림은 기존과 같이 high-fidelity-4x + 섞기로
하자. 코덱스는 AI 확대만, 나머지는 네가 해.」): each base and each expression of a sample, as the engine shows it at 1x
(an expression's 255,0,0 pixels take its base), with the colour under its mask's clear pixels (255) replaced by the colour
of the nearest pixel the mask shows. Under the clear part the originals are mostly white with some black, and an upscaler
smears that into the outline as a light or dark rim.

python sprite_prep.py <sample.json or job.json> <out dir> [--workers N]
  -> <out>\<key>.png (RGB, 1x size; an expression with crop_1x (sprite_job.py) only that crop), <out>\inputs.json
"""
import functools, json, sys
from multiprocessing import Pool
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista-ko\tools')
from inspect_majiro import Arc
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista-ko\ui-opening-ending\tools')
from raster_codec import raw_image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_runtime as M

arc = Arc(M.GAME / 'slowdata.arc')
ent = {e['name'].lower(): e for e in arc.entries}
f = arc.path.open('rb')


def blob(n):
    e = ent[n.lower()]
    f.seek(e['offset'])
    return f.read(e['size'])


@functools.lru_cache(maxsize=4)
def _base(n):
    """a base as decoded, kept for its next expressions (a job runs a family's pictures one after another)"""
    a = composed(n)
    a.setflags(write=False)
    return a


def composed(n):
    """the picture as the engine shows it: an expression (TC01) takes its base where it is marked 255,0,0"""
    b = blob(n)
    img, head, _ = raw_image(b)
    if b[4:8] == b'TC01':
        base = head[22:].rstrip(b'\0').decode('cp932')
        base_img = _base(base if base.lower().endswith('.rct') else base + '.rct')
        skip = np.all(img == [255, 0, 0], axis=2)
        img = img.copy()
        img[skip] = base_img[skip]
    return np.ascontiguousarray(img)


def filled(n):
    """what the AI is given: the picture with the colour under its clear pixels filled from its edge (whole)"""
    return edge_fill(composed(n), mask_of(n))


def mask_of(n):
    a, _, _ = raw_image(blob(n[:-4] + '_.rc8'))
    return np.ascontiguousarray(a[..., 0] if a.ndim == 3 else a)


def edge_fill(rgb, mask):
    """clear pixels (255) take the colour of the nearest shown pixel, then a little blur there so the fill has no seams"""
    clear = mask == 255
    if not clear.any() or clear.all():
        return rgb
    _, labels = cv2.distanceTransformWithLabels(clear.astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(~clear)
    lab2i = np.zeros(labels.max() + 1, np.int64)
    lab2i[labels[ys, xs]] = np.arange(len(ys))
    out = rgb.copy()
    i = lab2i[labels[clear]]
    out[clear] = rgb[ys[i], xs[i]]
    soft = cv2.GaussianBlur(out, (0, 0), 1.5)
    out[clear] = soft[clear]
    return out


def one(item, out):
    n = item['name']
    m = mask_of(n)
    a = edge_fill(composed(n), m)
    c = item.get('crop_1x')
    if c:
        x, y, w, h = c
        a, m = a[y:y + h, x:x + w], m[y:y + h, x:x + w]
    Image.fromarray(np.ascontiguousarray(a)).save(out / f"{item['key']}.png")
    row = {'name': n, 'key': item['key'], 'size_1x': [a.shape[1], a.shape[0]], 'size_4k': [a.shape[1] * 4, a.shape[0] * 4],
           'kind': 'base' if 'base' not in item else 'expression', 'clear_pct': round(100 * float((m == 255).mean()), 1)}
    if c:
        row['kind'], row['crop_1x'] = 'expression face crop', c
    return row


def main():
    sample = json.loads(Path(sys.argv[1]).read_text('utf-8'))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 1
    items = sample['bases'] + sorted(sample['patches'], key=lambda p: p['base'])   # a family together: its base decodes once
    if workers > 1:
        with Pool(workers) as pool:
            rows = list(pool.imap(functools.partial(one, out=out), items, chunksize=32))
    else:
        rows = [one(item, out) for item in items]
    (out / 'inputs.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    print(len(rows), 'inputs ->', out)


if __name__ == '__main__':
    main()
