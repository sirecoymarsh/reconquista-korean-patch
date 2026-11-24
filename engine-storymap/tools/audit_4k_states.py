"""Read only: button pictures in states (<x>_off / _on / _push): where the original's states differ but the 4K art the play
copy uses is the same picture for them (hovering or pressing then shows nothing at 4K)."""
import json, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools')
import make_runtime as M
sys.path.insert(0, str(M.BUILD / 'pylib'))
import imagecodecs
sys.path.insert(0, r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\ui-opening-ending\tools')
import decode_ui

ORIG = Path(r'F:\AI\reconquista-qa\art-audit\orig')
RUN = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024\runtime-play')
man = json.loads((M.GAME / 'hires-manifest.json').read_text('utf-8'))
file_of = {e['name']: e['file'] for e in man['entries'] if 'file' in e}
stems = sorted({n[:-len('_off.rct')] for n in file_of if n.endswith('_off.rct')})
where = {}
for a in ('data.arc', 'data1.arc', 'data2.arc', 'fastdata.arc', 'slowdata.arc'):
    try:
        arc = M.core.Arc(M.GAME / a)
    except Exception:
        continue
    for e in arc.entries:
        where.setdefault(e['name'], (arc.path, e['offset'], e['size']))
decode_ui.SRC = ORIG
_decode = decode_ui.decode


def fetch(name):
    if not (ORIG / name).exists() and name in where:
        path, off, size = where[name]
        with open(path, 'rb') as f:
            f.seek(off)
            (ORIG / name).write_bytes(f.read(size))
    return (ORIG / name).exists()


def decode(name, stack=()):
    fetch(name)
    b = (ORIG / name).read_bytes()
    if b[4:8] == b'TC01':
        n = struct.unpack_from('<H', b, 20)[0]
        base = b[22:22 + n].split(bytes(1))[0].decode('cp932')
        fetch(base if base.endswith('.rct') else base + '.rct')
    return _decode(name, stack)


decode_ui.decode = decode


def art(name):
    k = file_of[name].split('.')[0]
    j = RUN / 'hires-jxl' / f'{k}.jxl'
    if j.exists():
        return imagecodecs.jpegxl_decode(j.read_bytes())[..., :3].astype(np.int16)
    return np.asarray(Image.open(RUN / 'hires' / f'{k}.png').convert('RGB'), np.int16)


for s in stems:
    states = [t for t in ('off', 'on', 'push') if f'{s}_{t}.rct' in file_of and fetch(f'{s}_{t}.rct')]
    if len(states) < 2:
        continue
    one = {t: np.asarray(decode(f'{s}_{t}.rct')[0].convert('RGB'), np.int16) for t in states}
    four = {t: art(f'{s}_{t}.rct') for t in states}
    out = []
    for a, b in (('off', 'on'), ('on', 'push'), ('off', 'push')):
        if a in one and b in one:
            d1 = float((np.abs(one[a] - one[b]).max(axis=2) > 24).mean())
            d4 = float((np.abs(four[a] - four[b]).max(axis=2) > 24).mean())
            out.append(f'{a}-{b} 1x {d1:.4f} 4k {d4:.4f}' + ('  <- same at 4K' if d1 > 0.001 and d4 < d1 * 0.1 else ''))
    print(s, ' | '.join(out), flush=True)
