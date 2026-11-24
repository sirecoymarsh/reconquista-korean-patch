"""Eye-check sheets for lossy JPEG XL: one 320x240 crop of 4x pixels per tile, shown at 2x (nearest), original PNG and
three distances in a 2x2 grid. Only art the player has already seen: a 도입부 2 background, the title screen, the 연표 frame.
python jxl_sheets.py   -> qa/jxl_sheet_*.png
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'build' / 'pylib'))
import imagecodecs  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HIRES = HERE / 'runtime-play' / 'hires'
FONT = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 22)
SHEETS = [('배경', '181c0121', (1440, 1080)), ('타이틀_작은글씨', 'c1e942c6', (1730, 990)), ('연표_단추글씨', '6634c49a', (2000, 20))]
DISTANCES = [0.5, 1.0, 2.0]
CW, CH, Z, PAD, TOP = 320, 240, 2, 12, 40

for title, key, (x0, y0) in SHEETS:
    path = HIRES / f'{key}.png'
    ref = np.asarray(Image.open(path).convert('RGB'))
    tiles = [(f'원본 PNG  {path.stat().st_size / 2**20:.1f}MB', ref)]
    for d in DISTANCES:
        data = imagecodecs.jpegxl_encode(ref, distance=d, effort=7, numthreads=12)
        tiles.append((f'JPEG XL d={d}  {len(data) / 2**20:.2f}MB', imagecodecs.jpegxl_decode(data, numthreads=12)))
    tw, th = CW * Z, CH * Z
    sheet = Image.new('RGB', (2 * tw + 3 * PAD, 2 * (th + TOP) + PAD), (28, 28, 30))
    draw = ImageDraw.Draw(sheet)
    for i, (label, arr) in enumerate(tiles):
        cx, cy = PAD + (i % 2) * (tw + PAD), (i // 2) * (th + TOP)
        crop = Image.fromarray(arr[y0:y0 + CH, x0:x0 + CW]).resize((tw, th), Image.NEAREST)
        sheet.paste(crop, (cx, cy + TOP))
        draw.text((cx + 4, cy + 8), label, font=FONT, fill=(235, 235, 235))
    out = HERE / 'qa' / f'jxl_sheet_{title}.png'
    sheet.save(out)
    print(out)
