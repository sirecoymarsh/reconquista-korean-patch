"""4K art of a TC01 picture that still holds its pure red (10-27). A TC01 original is a delta over a base picture: where it is
pure red (255,0,0) the engine takes the base's pixel. Codex's 4K art did that for 1,112 of the 1,114 such pictures; the two
name plates 名前プレート_上条 and _詞菜 (over _ゆえ and _紅葉) kept the red, so the 연표's header showed them as bright red
plates. This lays each such 4K picture over its base's 4K art as the engine does (red -> base; the soft red edge of the red
part blended by how red it is) into build/hires-tc01/<key>.png, which make_runtime.py links over the copies' 4K art and
chronicle_assets.py prefers.
python fix_tc01_art.py   -> build/hires-tc01/ and a side-by-side sheet in F:/AI/reconquista-qa/tc01-fix/
"""
import json, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_runtime as M
sys.path.insert(0, str(M.BUILD / 'pylib'))   # imagecodecs (JPEG XL)
import imagecodecs

OUT = M.BUILD / 'hires-tc01'
SHEET = Path(r'F:\AI\reconquista-qa\tc01-fix')


def art(key):
    """the 4K art the copies use for a key: the blended/repaired JPEG XL over Codex's, else Codex's PNG"""
    for d in (M.BUILD / 'hires-jxl-redraw', M.BUILD / 'hires-jxl-cloud', M.BUILD / 'hires-jxl-blend', M.BUILD / 'hires-jxl'):
        p = d / f'{key}.jxl'
        if p.exists():
            return imagecodecs.jpegxl_decode(p.read_bytes())[..., :3].astype(np.float32)
    return np.asarray(Image.open(M.GAME / 'hires' / f'{key}.png').convert('RGB'), np.float32)


def redness(px):
    """1 where a pixel is the TC01 red, 0 where it is clearly not, between on the soft edge"""
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    return np.clip(((r - np.maximum(g, b)) - 120) / 100, 0, 1) * (r > 150)


def red_with_edge(px, reach=10):
    """redness, and within reach pixels of the red the red faded into black (no green or blue in it at all; the stone's dark
    reds have some) counted as red too"""
    red = redness(px)
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    faded = (g < 16) & (b < 16) & (r > 40)
    near = Image.fromarray(((red > .5) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * reach + 1))
    return np.maximum(red, (faded & (np.asarray(near) > 0)).astype(np.float32))


def main():
    man = json.loads((M.GAME / 'hires-manifest.json').read_text('utf-8'))
    key_of = {e['name']: e['file'].split('.')[0] for e in man['entries'] if 'file' in e}
    bases = {}
    for a in ('data.arc', 'data1.arc', 'data2.arc', 'fastdata.arc', 'slowdata.arc'):
        try:
            arc = M.core.Arc(M.GAME / a)
        except Exception:
            continue
        raw = arc.path.read_bytes()
        for e in arc.entries:
            if e['name'] in key_of and e['name'].endswith('.rct') and e['name'] not in bases:
                head = raw[e['offset']:e['offset'] + min(e['size'], 300)]
                if head[4:8] == b'TC01':
                    n = struct.unpack_from('<H', head, 20)[0]
                    base = head[22:22 + n].split(bytes(1))[0].decode('cp932')
                    bases[e['name']] = base if base.endswith('.rct') else base + '.rct'
    OUT.mkdir(parents=True, exist_ok=True)
    SHEET.mkdir(parents=True, exist_ok=True)
    made, rows = [], []
    for name, base in sorted(bases.items()):
        px = art(key_of[name])
        if (redness(px) > .99).mean() < .01 or base not in key_of:
            continue
        red = red_with_edge(px)
        under = art(key_of[base])
        if under.shape != px.shape:
            print('  size differs, left as it is:', name, px.shape, base, under.shape)
            continue
        out = px * (1 - red[..., None]) + under * red[..., None]
        im = Image.fromarray(out.round().clip(0, 255).astype(np.uint8))
        im.save(OUT / f'{key_of[name]}.png', compress_level=6)
        left = float((redness(out) > .99).mean())
        made.append(name)
        rows.append(np.concatenate([px, out], axis=1))
        print(f'  {name} over {base}: red {float((red > .99).mean()):.3f} -> {left:.4f}  -> {OUT / (key_of[name] + ".png")}')
    for p in OUT.glob('*.png'):   # a picture fixed since (Codex's new art) is not kept over it
        if p.stem not in {key_of[n] for n in made}:
            p.unlink()
    if rows:
        Image.fromarray(np.concatenate(rows, axis=0).round().clip(0, 255).astype(np.uint8)).save(SHEET / 'sheet.png')
    print(len(made), 'fixed of', len(bases), 'TC01 pictures with 4K art')


if __name__ == '__main__':
    main()
