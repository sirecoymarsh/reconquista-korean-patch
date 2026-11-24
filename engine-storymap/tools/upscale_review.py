"""Look at the 4x art against its source (read-only on Codex's data and decoder).
python upscale_review.py sheet <out.png> <name> ...          thumbnails of the 4x art, a grid with the names
python upscale_review.py crop <out.png> <name> x y w h [s]   one region (source pixels): source x4 (Lanczos) | 4x art, at s
The source is decoded from the game archives with Codex's hires_assets.decode (no .pyc is written into Codex's folder).
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
CODEX_TOOLS = Path(r'P:\AI\Codex\projects\reconquista-ko\tools')
MANIFEST = json.loads((HERE / 'runtime-play' / 'hires-manifest.json').read_text('utf-8-sig'))
KEY = {e['name'].lower(): e['file'][:8] for e in MANIFEST['entries']}


def art(name):
    return Image.open(HERE / 'runtime-play' / 'hires' / f'{KEY[name.lower()]}.png').convert('RGB')


def source(name):
    sys.path.insert(0, str(CODEX_TOOLS))
    import hires_assets  # noqa: E402  (reads the archives of Codex's v9 runtime, read-only)
    return Image.fromarray(hires_assets.decode(name)).convert('RGB')


def font(px):
    try:
        return ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', px)
    except OSError:
        return ImageFont.load_default()


def sheet(out, names, tw=320, th=240, cols=6):
    rows = (len(names) + cols - 1) // cols
    img = Image.new('RGB', (cols * tw, rows * (th + 22)), (30, 30, 30))
    d = ImageDraw.Draw(img)
    for i, n in enumerate(names):
        x, y = (i % cols) * tw, (i // cols) * (th + 22)
        img.paste(art(n).resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 4, y + th + 2), n, fill=(230, 230, 230), font=font(16))
    img.save(out)


def crop(out, name, x, y, w, h, s=1.0):
    a, b = source(name), art(name)
    left = a.crop((x, y, x + w, y + h)).resize((w * 4, h * 4), Image.LANCZOS)
    right = b.crop((x * 4, y * 4, (x + w) * 4, (y + h) * 4))
    img = Image.new('RGB', (w * 8 + 8, h * 4 + 26), (30, 30, 30))
    img.paste(left, (0, 26))
    img.paste(right, (w * 4 + 8, 26))
    d = ImageDraw.Draw(img)
    d.text((4, 4), f'{name} source x4 (Lanczos)', fill=(230, 230, 230), font=font(18))
    d.text((w * 4 + 12, 4), 'current 4x art', fill=(230, 230, 230), font=font(18))
    if s != 1.0:
        img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
    img.save(out)


if __name__ == '__main__':
    if sys.argv[1] == 'sheet':
        sheet(sys.argv[2], sys.argv[3:])
    else:
        a = sys.argv[3:]
        crop(sys.argv[2], a[0], *map(int, a[1:5]), *(map(float, a[5:6])))
