"""One sheet for the user to choose the 4x method from: intro pictures only (spoiler rule), the trouble spots in rows,
the methods in columns (qa/upscale-compare outputs of upscale_compare.py). python upscale_choice_sheet.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
Q = Path(__file__).resolve().parents[1] / 'qa' / 'upscale-compare'
# picture, x, y in 4x pixels, what the row shows
ROWS = [('ev102_04', 2840, 40, '흐린 천 무늬 → 지금은 갈라진 선'), ('netu101a', 420, 620, '칠한 풀밭 → 지금은 모래알 무늬'),
        ('img107', 1780, 560, '버스 옆면 → 지금은 붓질·종이결'), ('img107', 920, 1400, '버스 앞 글자판'),
        ('ev102_04', 1360, 480, '얼굴·머리카락(선명한 선)'), ('ev116_01', 1290, 700, '어깨의 흐린 외곽선')]
COLS = [('lanczos', '원본을 부드럽게 키움(AI 없음)'), ('current', '지금 4K(high-fidelity)'), ('hybrid-lanczos', '섞기(추천): 선은 지금, 흐린 곳은 원본'), ('swinir', 'SwinIR(원본 충실형 AI)')]
TW, TH, GAP, HEAD, LABEL = 400, 300, 6, 30, 26
font = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 17)
cache = {}


def picture(name, tag):
    if (name, tag) not in cache:
        if tag == 'lanczos':
            s = Image.open(Q / 'src' / f'{name}.png').convert('RGB')
            cache[(name, tag)] = s.resize((s.width * 4, s.height * 4), Image.LANCZOS)
        else:
            cache[(name, tag)] = Image.open(Q / f'{name}.{tag}.png').convert('RGB')
    return cache[(name, tag)]


sheet = Image.new('RGB', (len(COLS) * (TW + GAP), HEAD + len(ROWS) * (TH + LABEL + GAP)), (28, 28, 28))
d = ImageDraw.Draw(sheet)
for c, (_, label) in enumerate(COLS):
    d.text((c * (TW + GAP) + 4, 6), label, fill=(240, 240, 240), font=font)
for r, (name, x, y, what) in enumerate(ROWS):
    top = HEAD + r * (TH + LABEL + GAP)
    d.text((4, top + 3), f'{name} · {what}', fill=(250, 214, 160), font=font)
    for c, (tag, _) in enumerate(COLS):
        im = picture(name, tag)
        x0, y0 = min(x, im.width - TW), min(y, im.height - TH)
        sheet.paste(im.crop((x0, y0, x0 + TW, y0 + TH)), (c * (TW + GAP), top + LABEL))
sheet.save(Q / 'choice-sheet.png')
print(sheet.size)
