"""Stand-in 4K for a sprite sample (plain Lanczos x4), to try the DLL's base + face patch loading before Codex's art arrives.
Not for play: the test copy's hires\ is relinked (and so cleared of these) by make_runtime.py.

python sprite_standin.py <sample.json> <sprite-index.txt> [runtime]   (runtime: runtime-test)
-> <runtime>\hires\<base key>.png and <mask file key>.png, <runtime>\hires-patch\<variant key>.png, <runtime>\hires-sprites.txt
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista-ko\tools')
from inspect_majiro import Arc
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista-ko\ui-opening-ending\tools')
from raster_codec import raw_image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_runtime as M

sample = json.loads(Path(sys.argv[1]).read_text('utf-8'))
index = Path(sys.argv[2])
run = M.HERE / (sys.argv[3] if len(sys.argv) > 3 else 'runtime-test')
arc = Arc(M.GAME / 'slowdata.arc')
ent = {e['name'].lower(): e for e in arc.entries}
f = arc.path.open('rb')


def blob(n):
    e = ent[n.lower()]
    f.seek(e['offset'])
    return f.read(e['size'])


def raw(n):
    return raw_image(blob(n))


def composed(n):
    """the picture as the engine shows it: an expression (TC01) takes its base where it is marked 255,0,0"""
    b = blob(n)
    img, head, _ = raw_image(b)
    if b[4:8] == b'TC01':
        base = head[22:].rstrip(b'\0').decode('cp932')
        base_img = composed(base if base.lower().endswith('.rct') else base + '.rct')
        skip = np.all(img == [255, 0, 0], axis=2)
        img = img.copy()
        img[skip] = base_img[skip]
    return img


def x4(a, mode):
    im = Image.fromarray(a, mode)
    return im.resize((im.width * 4, im.height * 4), Image.LANCZOS)


(run / 'hires').mkdir(exist_ok=True)
(run / 'hires-patch').mkdir(exist_ok=True)
for b in sample['bases']:
    x4(composed(b['name']), 'RGB').save(run / 'hires' / b['file'])
for m in sample['masks']:
    a, _, _ = raw(m['name'])
    a = a[..., 0] if a.ndim == 3 else a
    x4(np.ascontiguousarray(a), 'L').save(run / 'hires' / m['file'])
for p in sample['patches']:
    big = x4(composed(p['name']), 'RGB')
    x, y, w, h = p['box_4k']
    big.crop((x, y, x + w, y + h)).save(run / 'hires-patch' / p['file'])
(run / 'hires-sprites.txt').write_text(index.read_text('ascii'), 'ascii')
print('bases', len(sample['bases']), 'masks', len(sample['masks']), 'patches', len(sample['patches']), '->', run)
