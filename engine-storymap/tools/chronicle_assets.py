"""Pictures for the new 연표 (native/chronicle_proto.inc, 10-27): the original 연표's own art from Codex's 4K (menu-4x) as
straight-alpha PNGs (colour picture + its `_.rc8` mask, where 255 is clear), and the Korean patch's letter table (the CP932
kanji it stands Korean syllables in, hangul-cp932-map.json) for the DLL to turn the 연표 script's text back into Korean.
python chronicle_assets.py   -> build/chronicle-new/ (the runtime copies link it as chronicle-new\)
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_runtime as M

OUT = M.BUILD / 'chronicle-new'
MAP = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\translation\hangul-cp932-map.json')
# the name plates in the 연표 script's own column order (267e7e45's switch), then the unknown one
PEOPLE = ['暮葉', '上条', '紅葉', '槙野', 'もみじ', 'まほこ', 'まほこ母', '詞菜', '麻咲', '信哉', '汐見', 'ゆえ']
PICS = {'frame_off': 'クロニクル枠_off', 'frame_on': 'クロニクル枠_on', 'hidden': '情報隠蔽', 'graybar': 'クロニクル灰バー',
        'bluebar': 'クロニクル青バー', 'subframe': 'サブエピソード用の枠', 'tri_dark': '右上▲_ダーク', 'tri_light': '右上▲_ライト',
        'hand_open': 'カーソル、パー', 'hand_grab': 'カーソル、グー', 'mark': 'submenu_マーク', 'thumb_h': 'コンフィグボタン',
        'thumb_v': 'ヒストリボタン', 'plate_q': '名前プレート_？？？'}
PICS.update({f'plate_{i:02d}': '名前プレート_' + n for i, n in enumerate(PEOPLE)})
CROP = {'mark': (0, 453, 492, 147)}   # the script shows only this part of submenu_マーク (800x600 units)


def picture(name, files):
    """colour (.rct, else .rc8) with the mask of <name>_.rc8 when there is one; a TC01 picture fixed by fix_tc01_art.py (two
    name plates whose 4K art kept the red) from build/hires-tc01"""
    color = files.get(name + '.rct') or files.get(name + '.rc8')
    if not color:
        raise SystemExit(f'no 4K picture for {name}')
    fixed = M.BUILD / 'hires-tc01' / color
    im = Image.open(fixed if fixed.exists() else M.GAME / 'hires' / color).convert('RGB')
    mask = files.get(name + '_.rc8')
    alpha = Image.fromarray(255 - np.asarray(Image.open(M.GAME / 'hires' / mask).convert('L'))) if mask else Image.new('L', im.size, 255)
    if alpha.size != im.size:
        alpha = alpha.resize(im.size, Image.LANCZOS)
    im.putalpha(alpha)
    return im


# 새 모양's panel: each column's person as a bust, from their first standing picture (expression 01) in the 4K sprites; both
# 「모미지」 plates (紅葉, もみじ) take momi. Shown only for a person the 연표 shows (not ???).
BUST = ['kure', 'kami', 'momi', 'maki', 'momi', 'maho', 'mohh', 'sina', 'masa', 'shin', 'sio', 'yue']


def key(name):
    import re, zlib
    n = re.split(r'[\\/]', name)[-1].lower()
    return zlib.crc32((n if '.' in n else n + '.rct').encode('cp932')) & 0xffffffff


def busts():
    import re
    sys.path.insert(0, str(M.BUILD / 'pylib'))   # imagecodecs (JPEG XL), as blend_art.py
    import imagecodecs
    names = [e['name'] for a in ('data.arc', 'data1.arc', 'data2.arc', 'slowdata.arc') for e in M.core.Arc(M.GAME / a).entries]
    folders = [M.BUILD / 'hires-jxl-sprites', M.GAME / 'hires-jxl']
    def art(k):
        for f in folders:
            p = f / f'{k:08x}.jxl'
            if p.exists():
                return imagecodecs.jpegxl_decode(p.read_bytes())
        return None
    made = {}
    for i, prefix in enumerate(BUST):
        if prefix in made:
            made[prefix].save(OUT / f'bust_{i:02d}.png')
            continue
        cands = sorted(n for n in names if re.fullmatch(prefix + r'_[0-9a-z]+_\d+_01\.rct', n.lower()))
        for n in cands:
            c, m = art(key(n)), art(key(n[:-4] + '_.rc8'))
            if c is None or m is None:
                continue
            im = Image.fromarray(c[..., :3] if c.ndim == 3 else c).convert('RGB')
            mm = m[..., 0] if m.ndim == 3 else m
            a = 255 - mm
            ys, xs = np.nonzero(a > 40)
            if not len(xs):
                continue
            top, cx = ys.min(), int(np.median(xs[ys < ys.min() + 600]))   # the head: the opaque part's top
            w = 900
            box = (max(0, cx - w // 2), max(0, top - 60), min(im.width, cx + w // 2), min(im.height, top - 60 + 1150))
            im.putalpha(Image.fromarray(a))
            bust = im.crop(box)
            bust = bust.resize((bust.width // 2, bust.height // 2), Image.LANCZOS)
            made[prefix] = bust
            bust.save(OUT / f'bust_{i:02d}.png')
            print(f'  bust {i:02d} {prefix} from {n} {bust.size}')
            break
        else:
            print(f'  bust {i:02d} {prefix}: no 4K standing picture')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    busts()
    m = json.loads((M.GAME / 'hires-manifest.json').read_text('utf-8'))
    files = {e['name']: e['file'] for e in m['entries']}
    sizes = {}
    for key, name in PICS.items():
        im = picture(name, files)
        if key in CROP:
            x, y, w, h = (v * 4 for v in CROP[key])
            im = im.crop((x, y, x + w, y + h))
        im.save(OUT / f'{key}.png', optimize=False, compress_level=1)
        sizes[key] = im.size
    pairs = json.loads(MAP.read_text('utf-8'))['mapping']
    (OUT / 'hangul.txt').write_text(''.join(f'{ord(v):04x} {ord(k):04x}\n' for k, v in pairs.items()), 'ascii')
    print(len(sizes), 'pictures', len(pairs), 'letters ->', OUT)
    for k, v in sizes.items():
        print(f'  {k} {v[0]}x{v[1]}')


if __name__ == '__main__':
    main()
