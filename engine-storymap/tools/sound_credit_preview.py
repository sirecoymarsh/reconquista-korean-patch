"""The sound mode's top strip as the engine composes it (music.mjo: background, button layer, then the credit plate at 37,116):
from the original 1x pictures (shown at 4x) and from the 4K pictures, one above the other. Output F:/AI/reconquista-qa/sound-credits"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools')
import make_runtime as M
sys.path.insert(0, r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\ui-opening-ending\tools')
import decode_ui

OUT = Path(r'F:\AI\reconquista-qa\sound-credits')
decode_ui.SRC = OUT / 'orig'
man = json.loads((M.GAME / 'hires-manifest.json').read_text('utf-8'))
file_of = {e['name']: e['file'] for e in man['entries'] if 'file' in e}


def one(name):
    return np.asarray(decode_ui.decode(name)[0].convert('RGB')).astype(np.float32)


def four(name):
    return np.asarray(Image.open(M.GAME / 'hires' / file_of[name]).convert('RGB')).astype(np.float32)


def mask1(name):
    return (255 - np.asarray(decode_ui.decode(name)[0].convert('L')).astype(np.float32)) / 255


def mask4(name):
    return (255 - np.asarray(Image.open(M.GAME / 'hires' / file_of[name]).convert('L')).astype(np.float32)) / 255


def blend(page, pic, a, x, y):
    h, w = pic.shape[:2]
    region = page[y:y + h, x:x + w]
    region[...] = pic * a[..., None] + region * (1 - a[..., None])


n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
rows = []
for scale, get, gm in ((1, one, mask1), (4, four, mask4)):
    page = get('サウンドモード_背景_off.rct').copy()
    btn = get('サウンドモード_off.rct')
    blend(page, btn, gm('サウンドモード_off_.rc8'), 0, 0)
    c = f'作曲_クレジット_{n}'
    blend(page, get(c + '.rct'), gm(c + '_.rc8'), 37 * scale, 116 * scale)
    im = Image.fromarray(page.clip(0, 255).round().astype(np.uint8))
    if scale == 1:
        im = im.resize((3200, 2400), Image.LANCZOS)
    rows.append(im.crop((30 * 4, 100 * 4, 690 * 4, 165 * 4)))
sheet = Image.new('RGB', (rows[0].width, rows[0].height * 2 + 8))
sheet.paste(rows[0], (0, 0))
sheet.paste(rows[1], (0, rows[0].height + 8))
sheet.save(OUT / f'onscreen-{n}.png')
sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS).save(OUT / f'onscreen-{n}-half.png')
print('->', OUT / f'onscreen-{n}.png', sheet.size)
