"""The sound mode's credit lines (作曲_クレジット_1..14) at 4K as the original draws them (10-27). Codex's 4K art set them again
in Noto Sans in the outline colour alone, so they sank into the dark wood (사용자 「사운드 모드에서 위에 글자가 깨져보여」,
then 「4K 였던거 어디갔냐?」). The original 1x lines are Codex's own Korean raster (ui-opening-ending/tools/
build_text_rasters.py): Noto Serif CJK KR, cream (222,202,179) letters with a 2 px outline (49,32,21), centred on the 636x38
plate, the size the largest from 17 down that fits the slot. Here the same at 4x: the same size x4, an 8 px outline, the
same centring, so it reduces to the original. Colour RGB (white where clear, as the original) and mask L (255 = clear), as
Codex's 4K art. -> build/hires-text/<key>.png (make_runtime.py links it over the copies' 4K art); a check against the 1x
original and a sheet in F:/AI/reconquista-qa/sound-credits.
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_runtime as M
sys.path.insert(0, r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\ui-opening-ending\tools')
import decode_ui

FONT = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\research\fonts\NotoSerifCJKkr-Regular.otf')
OUT = M.BUILD / 'hires-text'
QA = Path(r'F:\AI\reconquista-qa\sound-credits')
FILL, EDGE = (222, 202, 179), (49, 32, 21)
# the targets of build_text_rasters.py's credits, in its order (作曲_クレジット_1..14)
CREDITS = ['작곡: 上松範康 (Elements Garden)  편곡: 菊田大介 (Elements Garden)  노래: 飛蘭',
           '작곡: 上松範康 (Elements Garden)  편곡: 菊田大介 (Elements Garden)',
           '작곡: 上松範康 (Elements Garden)', '작곡: ANZE HIJIRI', '작곡: ANZE HIJIRI  노래: YURIA',
           '작곡: Barbarian on the groove  편곡: 館内', '작곡: Barbarian on the groove', '작곡: 館内', '작곡: 井出 今日子',
           '작곡: Sentive', '작곡: 443', '작곡: 児島 空', '작곡: Elements Garden  편곡: 館内', '작곡: Elements Garden']


def size_1x(text):
    """build_text_rasters.py's choice: from 17 down, the first size whose ink fits the slot 620x32 with 8 to spare"""
    size = 17
    while True:
        bb = ImageFont.truetype(str(FONT), size).getbbox(text, stroke_width=0)
        if bb[2] - bb[0] + 8 <= 620 and bb[3] - bb[1] + 8 <= 32:
            return size
        size -= 1
        assert size >= 14


def render(text, scale):
    w, h = 636 * scale, 38 * scale
    font = ImageFont.truetype(str(FONT), size_1x(text) * scale)
    bb = font.getbbox(text, stroke_width=0)
    px, py = round(w / 2 - (bb[0] + bb[2]) / 2), round(18 * scale - (bb[1] + bb[3]) / 2)
    layer = Image.new('RGBA', (w, h))
    ImageDraw.Draw(layer).text((px, py), text, font=font, fill=(*FILL, 255), stroke_width=2 * scale, stroke_fill=(*EDGE, 255))
    la = np.asarray(layer)
    rgb = np.full((h, w, 3), 255, np.uint8)
    on = la[..., 3] > 0
    rgb[on] = la[on, :3]
    return rgb, la[..., 3].copy()


def over_grey(rgb, alpha):
    a = alpha.astype(np.float32)[..., None] / 255
    return rgb.astype(np.float32) * a + np.array([90, 90, 96], np.float32) * (1 - a)


def main():
    man = json.loads((M.GAME / 'hires-manifest.json').read_text('utf-8'))
    key_of = {e['name']: e['file'].split('.')[0] for e in man['entries'] if 'file' in e}
    # the originals as the game has them (fastdata.arc): to check the 4x against
    orig = QA / 'orig'
    orig.mkdir(parents=True, exist_ok=True)
    arc = M.core.Arc(M.GAME / 'fastdata.arc')
    raw = arc.path.read_bytes()
    for e in arc.entries:
        if e['name'].startswith('作曲_クレジット_'):
            (orig / e['name']).write_bytes(raw[e['offset']:e['offset'] + e['size']])
    decode_ui.SRC = orig
    OUT.mkdir(parents=True, exist_ok=True)
    rows, worst = [], 0.0
    for i, text in enumerate(CREDITS, 1):
        stem = f'作曲_クレジット_{i}'
        rgb4, a4 = render(text, 4)
        rgb1, a1 = render(text, 1)
        g1 = np.asarray(decode_ui.decode(stem + '.rct')[0].convert('RGB'))
        m1 = 255 - np.asarray(decode_ui.decode(stem + '_.rc8')[0].convert('L'))
        same_1x = np.array_equal(a1, m1) and np.array_equal(rgb1[a1 > 0], g1[a1 > 0])   # the recipe makes the game's 1x exactly
        o4 = Image.fromarray(over_grey(rgb4, a4).round().astype(np.uint8)).resize((636, 38), Image.BOX)
        mad = float(np.abs(np.asarray(o4, np.float32) - over_grey(g1, m1)).mean())
        worst = max(worst, mad)
        Image.fromarray(rgb4).save(OUT / f'{key_of[stem + ".rct"]}.png')
        Image.fromarray((255 - a4).astype(np.uint8), 'L').save(OUT / f'{key_of[stem + "_.rc8"]}.png')
        rows.append(Image.fromarray(over_grey(rgb4, a4).round().astype(np.uint8)))
        print(f'  {stem}: size {size_1x(text)}x4, 1x recipe = game 1x {same_1x}, 4K reduced vs game 1x {mad:.2f}')
    sheet = Image.new('RGB', (rows[0].width, sum(r.height + 4 for r in rows)), (0, 0, 0))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 4
    sheet.save(QA / 'credit-4k-sheet.png')
    print(len(CREDITS), 'credit lines ->', OUT, '; worst difference', round(worst, 2))


if __name__ == '__main__':
    main()
