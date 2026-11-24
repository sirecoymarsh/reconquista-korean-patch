"""Boards for the user: 비교 (current Codex chart vs new map) and 한눈에 (three screens + 표시 규칙 legend).

python mock_board.py -> mock/비교_지금과_새시안.png, mock/표시규칙.png, mock/한눈에.png
"""
from PIL import Image, ImageDraw

import mock_lib as L
import mock_map as M

OUT = L.HERE / 'mock'
CURRENT = L.CAND / 'ingame-flowchart-v1' / 'qa' / 'chart-first.png'
BG = (24, 24, 28, 255)


def caption(img, xy, t, px=26, fill=(236, 232, 226)):
    d = ImageDraw.Draw(img)
    d.text(xy, t, font=L.ImageFont.truetype(L.SANS, px), fill=fill)


def legend():
    """표시 규칙, drawn with the same cell renderer as the map (1600x1200 tile)."""
    img = Image.new('RGBA', (L.W, L.H), (0, 0, 0, 255))
    L.text(img, (40, 40), '칸 표시 규칙', 'serif', 21, L.WHITE, anchor='lm')
    L.text(img, (40, 64), '상태는 「표시가 있고 없음」과 밝기로, 빛깔 하나에 뜻 하나', 'sans', 11, L.PROMPT, anchor='lm', shadow=False)
    rows = [
        ('안 읽은 장', dict(items=[('07', 'kureha_07', None)])),
        ('읽은 장 — ✓와 밝은 글자', dict(items=[('07', 'kureha_07', None)], read=('kureha_07',))),
        ('지금 자리 — 단풍잎(주황은 이 뜻에만)', dict(items=[('07', 'kureha_07', None)], current='kureha_07')),
        ('고른 칸 — 이름판과 같은 진홍 돌결', dict(items=[('07', 'kureha_07', None)], cursor='kureha_07')),
        ('선택지가 있는 장 — 선택지 받침 모양 + 개수', dict(items=[('13', 'maho_13', None)])),
        ('시점 전환이 있는 장 — 시점 변경 화면의 고리 화살표', dict(items=[('도입부 3', '00_レコンキスタ_start_3', None)])),
        ('같은 날 여러 장 — 칸을 나눔', dict(items=[('18', 'maho_18', None), ('18-2', 'maho_18_2ero', None), ('18-3', 'maho_18_3', None)])),
    ]
    y = 96
    for text, kw in rows:
        r = (40, y, 206, y + 21)
        M.cell(img, r, kw['items'], kw.get('cursor'), kw.get('read', ()), kw.get('current'))
        L.rect(img, r, L.LINE + (255,))
        L.text(img, (222, y + 10.5), text, 'sans', 12, (222, 220, 228), anchor='lm', shadow=False)
        y += 32
    # states that only appear in some modes
    y += 8
    L.text(img, (40, y), '켜는 방식에 따라 나오는 것', 'serif', 14, L.PROMPT, anchor='lm')
    y += 20
    noise = L.hidden_noise()
    L.textured(img, (40, y, 206, y + 21), noise)
    L.rect(img, (40, y, 206, y + 21), L.LINE + (255,))
    L.text(img, (222, y + 10.5), '일반 플레이에서 아직 못 본 장 — 연표의 「정보 가림」 무늬 그대로', 'sans', 12, (222, 220, 228), anchor='lm', shadow=False)
    y += 32
    bars = L.choice_bars()
    for k, (bar, t) in enumerate([(bars[0], '선택지 — 평소'), (bars[1], '선택지 — 고르는 중'), (bars[2], '선택지 — 예전에 고른 쪽(설정 「선택한 선택지 → 색상 변경」과 같은 파랑)')]):
        p = L.plate(bar, 166, 21, 18)
        L.paste(img, p, 40, y)
        L.text(img, (123, y + 10.5), '못 들은 척한다', 'sans', 11, L.WHITE, anchor='mm')
        L.text(img, (222, y + 10.5), t, 'sans', 12, (222, 220, 228), anchor='lm', shadow=False)
        y += 30
    y += 8
    L.text(img, (40, y), '세로줄 머리판', 'serif', 14, L.PROMPT, anchor='lm')
    y += 22
    for k, (pl, name, t) in enumerate([(L.name_plate_crimson(), '쿠레하', '마키노 시점 쪽 — 시점 변경 화면의 「마키노 게이고」 판, 마키노 대사창과 같은 진홍'),
                                       (L.name_plate_navy(), '마호코', '신야 시점 쪽 — 시점 변경 화면의 「미사와 신야」 판, 신야 대사창과 같은 남색')]):
        p = L.plate(pl, 120, 30, 8)
        L.paste(img, p, 40, y)
        L.text(img, (100, y + 15), name, 'serif', 13, L.WHITE, anchor='mm')
        L.text(img, (176, y + 15), t, 'sans', 12, (222, 220, 228), anchor='lm', shadow=False)
        y += 38
    return img


def board_compare(new):
    cur = Image.open(CURRENT).convert('RGBA')
    cur = cur.resize((int(cur.width * 1200 / cur.height), 1200), Image.LANCZOS)
    gap, top = 40, 90
    img = Image.new('RGBA', (cur.width + gap + new.width + 80, 1200 + top + 40), BG)
    caption(img, (40, 28), '지금 (v18 F11 차트, 4096×2160 창 전체)', 30)
    caption(img, (40 + cur.width + gap, 28), '새 시안 · 이야기 지도 본편 (게임 4:3 화면 안)', 30)
    img.alpha_composite(cur, (40, top))
    img.alpha_composite(new, (40 + cur.width + gap, top))
    return img


def board_all(main, final, chap, leg):
    pad, top = 40, 70
    w, h = main.width, main.height
    img = Image.new('RGBA', (pad * 3 + 2 * w, top * 2 + pad + 2 * h), BG)
    spots = [(main, '① 이야기 지도 · 본편 — 19일 날짜 줄 × 네 갈래 (원작 「연표」 틀)'),
             (final, '② 이야기 지도 · 최종편 — 현재는 같은 날짜 줄, 과거는 날짜 없는 줄기'),
             (chap, '③ 장 안 — 장면 카드(저장 칸 꼴) + 대사 목록(대사 기록 화면 꼴)'),
             (leg, '④ 칸 표시 규칙')]
    for k, (im, t) in enumerate(spots):
        x = pad + (k % 2) * (w + pad)
        y = top + (k // 2) * (h + top + pad // 2)
        caption(img, (x, y - 52), t, 30)
        img.alpha_composite(im, (x, y))
    return img


if __name__ == '__main__':
    main = M.main_page()
    final = M.final_page()
    chap = Image.open(OUT / 'chapter.png').convert('RGBA')
    leg = legend()
    leg.convert('RGB').save(OUT / '표시규칙.png')
    board_compare(main).convert('RGB').save(OUT / '비교_지금과_새시안.png')
    board_all(main, final, chap, leg).convert('RGB').save(OUT / '한눈에.png', optimize=True)
    print('ok')
