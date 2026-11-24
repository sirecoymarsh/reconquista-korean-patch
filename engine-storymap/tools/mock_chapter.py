"""장 안 화면 mockup: the game's backlog panel + ⚜ banner header, scene cards (save-slot style) and lines.

python mock_chapter.py -> mock/chapter.png (1600x1200)
Sample: 도입부 2, scene 35 (the game's first choice). Read ✓ on earlier lines, 지금 = 마호코 「저, 저기…」,
cursor on the line two below it. Text comes from the approved Korean catalogue previews.
"""
import json

from PIL import Image, ImageDraw

import mock_lib as L

OUT = L.HERE / 'mock'
BG = json.loads((L.REF / 'bg_files.json').read_text('utf-8'))
HIRES = L.Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\runtime-body-ui-20261024-v18-cg-switch\hires')
SCREEN = L.CAND / 'ingame-flowchart-v1' / 'qa' / 'name-fixed-logical-after.png'   # 2일째 dialogue, behind the panel

SCENES = [  # (no, bg, first line, pages, choices)
    (32, 'bg_310a', '마키노 「자, 슬슬 하교 시간이구나」', 20, 0),
    (33, 'bg_270a', '모미지 「우와아…」', 45, 0),
    (34, 'bg_050a', '벌떡.', 63, 0),
    (35, 'bg_340b', '신야 「으아, 꽤 무겁네…」', 100, 1),
    (36, 'bg_260b', '거센 바닷바람을 받아 달각달각 돌아가는 얼레.', 35, 0),
    (37, 'bg_260b', '신야 「영차… 자, 빙글빙글빙글!」', 51, 0),
    (38, 'bg_300b', '마호코 「아…」 마호코가 쥐고 있던 장바구니.', 17, 0),
    (39, 'bg_130c', '마키노 「후우… 제법 정리가 됐네」', 69, 0),
]
LINES = [  # (speaker or None, text)
    (None, '아주 조금의 슬픔을 안고 나와 마호코 사이에 가로놓여 있었다.'),
    ('신야', '「………」'),
    (None, '나도 모르게 멍해진 나를 향해,'),
    ('마호코', '「저, 저기…」'),
    ('마호코', '「아하하… 옛날 같네, 오빠」'),
    (None, '옛날과 같은 호칭으로… 그리고 옛날과는 달리 쑥스러운 목소리로 나를 부른다.'),
    (None, '그런 마호코에게 나는…'),
]
READ_LINES, NOW_LINE, CURSOR_LINE = {0, 1, 2}, 3, 5
CHOICES = ['「…왜 그래, 마호 누나」', '못 들은 척한다']


def wrap(t, kind, px, width):
    out, cur = [], ''
    for ch in t:
        if L.text_width(cur + ch, kind, px) > width and cur:
            out.append(cur)
            cur = ch.lstrip() if ch == ' ' else ch
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def thumb(name, w=64, h=48):
    im = Image.open(HIRES / BG[name]).convert('RGBA')
    return im.resize((L.s(w), L.s(h)), Image.LANCZOS)


def build():
    img = Image.open(SCREEN).convert('RGBA').resize((L.W, L.H), Image.LANCZOS)
    img.alpha_composite(Image.new('RGBA', img.size, (0, 0, 0, 185)))     # extra dim: the list must read first
    img.alpha_composite(L.backlog_frame())
    # header: ⚜ banner, prompt, chevron plates
    banner = L.up(L.banner_blank())
    img.alpha_composite(banner, (0, L.s(22)))
    L.text(img, (124, 50), '도입부 2', 'serif', 19, L.WHITE, anchor='mm')
    L.text(img, (402, 50), '2일째 (목) · 장면 66 · 대사 2,013줄 · 선택지 4 · 시점 전환 1', 'serif', 13, L.PROMPT, anchor='mm')
    red, navy = L.chevron_plates()
    img.alpha_composite(L.up(red), (L.s(596), L.s(18)))
    img.alpha_composite(L.up(navy), (L.s(596), L.s(50)))
    L.text(img, (681, 33), '지도로 돌아가기', 'serif', 12, L.WHITE, anchor='mm')
    L.text(img, (681, 65), '대사 찾기', 'serif', 12, L.WHITE, anchor='mm')
    L.fill(img, (16, 86, 770, 86.5), (150, 146, 150, 255))
    scene_list(img)
    lines_panel(img)
    return img


def scene_list(img):
    x0, x1 = 20, 252
    L.text(img, (x0 + 2, 99), '장면', 'serif', 12, L.PROMPT, anchor='lm')
    L.text(img, (x1, 99), '66개 중 32~39', 'sans', 10, (150, 150, 160), anchor='rm', shadow=False)
    y = 110
    for no, bg, first, pages, choices in SCENES:
        sel = no == 35
        r = (x0, y, x1, y + 52)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle(L.box(*r), radius=L.s(4), fill=(112, 4, 22, 255) if sel else (46, 8, 14, 235),
                            outline=(214, 206, 206, 255) if sel else (98, 44, 52, 255), width=L.S if sel else 1)
        img.alpha_composite(thumb(bg), (L.s(x0 + 5), L.s(y + 2)))
        L.rect(img, (x0 + 5, y + 2, x0 + 69, y + 50), (170, 166, 170, 255))
        tx = x0 + 77
        if no < 35:
            L.check_icon(img, tx, y + 12, 11)
            tx += 12
        L.text(img, (tx, y + 12), f'장면 {no}', 'serif', 12, L.WHITE, anchor='lm')
        L.text(img, (x1 - 6, y + 12), f'{pages}줄', 'sans', 9, (178, 170, 176), anchor='rm', shadow=False)
        if choices:
            L.choice_icon(img, x1 - 44, y + 9.5, choices)
        if sel:
            lf = L.leaf(13)
            img.alpha_composite(lf, (L.s(x1 - 70), L.s(y + 5)))
        for k, ln in enumerate(wrap(first, 'sans', 10, x1 - x0 - 84)[:2]):
            L.text(img, (x0 + 77, y + 29 + k * 13), ln, 'sans', 10, (214, 210, 216), anchor='lm', shadow=False)
        y += 56


def lines_panel(img):
    x0, x1 = 262, 764
    tx = x0 + 22
    # search row
    L.text(img, (x0 + 4, 101), '찾기', 'serif', 11, L.PROMPT, anchor='lm')
    d = ImageDraw.Draw(img)
    d.rectangle(L.box(x0 + 30, 93, x0 + 300, 109), fill=(6, 6, 10, 255), outline=(126, 120, 128, 255), width=1)
    L.text(img, (x0 + 37, 101), '대사나 이름으로 찾기', 'sans', 10, (120, 120, 130), anchor='lm', shadow=False)
    L.text(img, (x1, 101), '장면 35 · 대사 100줄 · 선택지 1', 'sans', 10, (158, 156, 166), anchor='rm', shadow=False)
    L.fill(img, (x0, 115, x1, 115.5), (70, 66, 76, 255))
    y = 121
    bar_hover = L.choice_bars()[1]
    sel_tex = L.up(bar_hover.crop((40, 12, 520, 44)))
    for i, (spk, t) in enumerate(LINES):
        rows = wrap(t, 'sans', 12, x1 - tx - 30)
        h = (15 if spk else 0) + 17 * len(rows) + 9
        r = (x0, y, x1, y + h)
        if i == CURSOR_LINE:
            L.textured(img, (x0 + 1, y, x1 - 1, y + h), sel_tex, alpha=230)
            L.rect(img, (x0 + 1, y, x1 - 1, y + h), (214, 206, 206, 255))
        if i in READ_LINES:
            L.check_icon(img, x0 + 8, y + (15 if spk else 0) + 9, 11)
        yy = y + 5
        if spk:
            L.text(img, (tx, yy + 5), spk, 'serif', 11, L.NAME, anchor='lm')
            yy += 15
        for ln in rows:
            L.text(img, (tx, yy + 7), ln, 'sans', 12, L.WHITE if spk else (222, 220, 228), anchor='lm')
            yy += 17
        if i == NOW_LINE:
            lf = L.leaf(14)
            img.alpha_composite(lf, (L.s(x1 - 52), L.s(y + h / 2 - 7)))
            L.text(img, (x1 - 56, y + h / 2), '지금', 'sans', 10, L.LEAF, anchor='rm')
        L.fill(img, (x0 + 6, y + h, x1 - 6, y + h + 0.5), (52, 48, 58, 255))
        y += h + 1
    # choice block in the game's own choice-stand art
    y += 6
    L.text(img, (tx, y + 6), '선택지 1', 'serif', 11, L.PROMPT, anchor='lm')
    L.text(img, (tx + 50, y + 6.5), '고르면 그 갈래로 이어서 봅니다', 'sans', 9, (150, 150, 160), anchor='lm', shadow=False)
    y += 15
    normal = L.choice_bars()[0]
    for opt in CHOICES:
        bar = L.plate(normal, 380, 26, 22)
        bx = (x0 + x1) / 2 - 190
        img.alpha_composite(bar, (L.s(bx), L.s(y)))
        L.text(img, ((x0 + x1) / 2, y + 13), opt, 'sans', 12, L.WHITE, anchor='mm')
        y += 30
    # jump plate
    jump = L.plate(bar_hover, 300, 28, 22)
    img.alpha_composite(jump, (L.s((x0 + x1) / 2 - 150), L.s(524)))
    L.text(img, ((x0 + x1) / 2, 538), '이 대사부터 보기', 'serif', 14, L.WHITE, anchor='mm')
    L.text(img, ((x0 + x1) / 2 + 160, 538), 'Enter', 'sans', 9, (150, 150, 160), anchor='lm', shadow=False)
    L.text(img, ((x0 + x1) / 2, 562), '검수용 저장으로 이어집니다 · 원래 저장은 그대로', 'sans', 9, (140, 140, 150), anchor='mm', shadow=False)


if __name__ == '__main__':
    build().convert('RGB').save(OUT / 'chapter.png')
    print('ok')
