"""Read only: Codex's 4K UI pictures (the manifest entries without a size: UI plates and masks) against the original 1x they
stand for. Each 4K picture is averaged down to 1x and laid over grey with its own mask, the original likewise; big
differences (or a mask that covers much less) mean the 4K is not the original redrawn. Output F:/AI/reconquista-qa/art-audit"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools')
import make_runtime as M
sys.path.insert(0, r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\ui-opening-ending\tools')
import decode_ui

OUT = Path(r'F:\AI\reconquista-qa\art-audit')
ORIG = OUT / 'orig'
ORIG.mkdir(parents=True, exist_ok=True)
man = json.loads((M.GAME / 'hires-manifest.json').read_text('utf-8'))
entries = [e for e in man['entries'] if 'file' in e]
file_of = {e['name']: e['file'] for e in entries}
targets = [e['name'] for e in entries if not e.get('size') or tuple(e['size']) in ((131, 43), (215, 82))]
want = set(targets) | {n[:-4] + '_.rc8' for n in targets if n.endswith('.rct')}
found = {}
for a in ('data.arc', 'data1.arc', 'data2.arc', 'fastdata.arc', 'slowdata.arc'):
    try:
        arc = M.core.Arc(M.GAME / a)
    except Exception:
        continue
    raw = arc.path.read_bytes()
    for e in arc.entries:
        if e['name'] in want and e['name'] not in found:
            found[e['name']] = raw[e['offset']:e['offset'] + e['size']]
for n, b in found.items():
    p = ORIG / n
    if not p.exists():
        p.write_bytes(b)
decode_ui.SRC = ORIG
grey = np.array([90, 90, 96], np.float32)


def down(im):
    return np.asarray(im.resize((im.width // 4, im.height // 4), Image.BOX), np.float32)


rows = []
for n in targets:
    if n not in found or not n.endswith('.rct'):
        continue
    try:
        c1 = np.asarray(decode_ui.decode(n)[0].convert('RGB'), np.float32)
        c4 = down(Image.open(M.GAME / 'hires' / file_of[n]).convert('RGB'))
    except Exception as ex:
        rows.append((n, None, None, repr(ex)[:60]))
        continue
    mk = n[:-4] + '_.rc8'
    a1 = a4 = None
    if mk in found and mk in file_of:
        a1 = (255 - np.asarray(decode_ui.decode(mk)[0].convert('L'), np.float32)) / 255
        a4 = (255 - down(Image.open(M.GAME / 'hires' / file_of[mk]).convert('L'))) / 255
    if c4.shape != c1.shape or (a1 is not None and a4.shape != a1.shape):
        rows.append((n, None, None, f'size {c1.shape} vs {c4.shape}'))
        continue
    if a1 is None:
        a1 = a4 = np.ones(c1.shape[:2], np.float32)
    o1 = c1 * a1[..., None] + grey * (1 - a1[..., None])
    o4 = c4 * a4[..., None] + grey * (1 - a4[..., None])
    seen = (a1 > .1) | (a4 > .1)
    mad = float(np.abs(o1 - o4)[seen].mean()) if seen.any() else 0.0
    cover = float(a4.sum() / max(a1.sum(), 1e-6))
    rows.append((n, mad, cover, ''))
rows.sort(key=lambda r: -(r[1] or 0))
lines = [f'{r[1] if r[1] is None else round(r[1], 1)!s:>6}  cover {r[2] if r[2] is None else round(r[2], 2)!s:>5}  {r[0]}  {r[3]}' for r in rows]
(OUT / 'audit.txt').write_text('\n'.join(lines), 'utf-8')
print(len(rows), 'colour pictures compared;', sum(1 for r in rows if r[1] is None), 'not comparable')
print('\n'.join(lines[:40]))
