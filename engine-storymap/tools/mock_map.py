"""이야기 지도 mockups: 본편 page (19-day grid) and 최종편 page, drawn on the game's own chronicle frame.

python mock_map.py  ->  mock/map_main.png, mock/map_final.png (1600x1200 = 2x of the 800x600 screen)
Sample states: 도입부 1 read (✓), 지금 = 도입부 2 (단풍잎), cursor = 쿠레하 05 / 현재 09.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

import mock_lib as L

OUT = L.HERE / 'mock'
OUT.mkdir(exist_ok=True)
summary = json.loads((L.REF / 'catalogue_summary.json').read_text('utf-8'))
CH = {c['id']: c for c in summary['chapters']}
DAYS = json.loads((L.REF / 'chapter_days.json').read_text('utf-8'))
WEEK = ['수', '목', '금', '토', '일', '월', '화']          # day 1 = Wednesday (01day: 18日前 水曜日)


def weekday(d):
    return WEEK[(d - 1) % 7]


def wcolor(d):
    w = weekday(d)
    return L.SUN if w == '일' else L.SAT if w == '토' else (214, 212, 220)


def label(cid):
    tail = cid.split('_', 1)[1]
    if tail in ('ep', 'epi'):
        return '후일담'
    return tail.replace('_2ero', '-2').replace('_3', '-3').replace('_2', '-2')


GRID_X = [94, 260, 427, 594, 760]
BODY_TOP, INFO_TOP, INFO_BOT = 114, 542, 562
crimson_tex = L.up(L.name_plate_crimson().crop((10, 8, 121, 35)))
navy_tex = L.navy_stone()
gray_tex = L.gray_stone()
LEAF = L.leaf(15)


def frame_common(title, switch_label, emblem_bottom):
    img = L.chronicle_frame()
    L.text(img, (225, 44), title, 'serif', 21, L.WHITE, anchor='mm')
    L.text(img, (445, 35), switch_label, 'serif', 14, L.WHITE, anchor='mm')
    L.text(img, (576, 20.5), '대사 찾기', 'serif', 12, L.WHITE, anchor='mm')
    L.text(img, (576, 48.5), '지금 자리로', 'serif', 12, L.WHITE, anchor='mm')
    L.text(img, (693, 35), '닫기', 'serif', 13, L.WHITE, anchor='mm')
    L.text(img, (70, 79), '갈래', 'serif', 11, L.WHITE, anchor='mm')
    L.text(img, (46, 105), emblem_bottom, 'serif', 11, L.WHITE, anchor='mm')
    return img


def header_plates(img, cols, names, plates):
    for (x0, x1), name, pl in zip(cols, names, plates):
        w = min(150, x1 - x0 - 12)
        p = L.plate(pl, w, 36, 9)
        L.paste(img, p, (x0 + x1) / 2 - w / 2, 74.5)
        L.text(img, ((x0 + x1) / 2, 92.5), name, 'serif', 15, L.WHITE, anchor='mm')


def axis_cell(img, y0, y1, main, sub=None, sub_color=None, tex=None):
    L.textured(img, (20, y0, 92, y1), tex or navy_tex)
    L.rect(img, (20, y0, 92, y1), (40, 36, 58, 255))
    mid = (y0 + y1) / 2
    L.text(img, (27, mid), main, 'serif', 12, L.WHITE, anchor='lm')
    if sub:
        L.text(img, (87, mid), sub, 'sans', 10, sub_color, anchor='rm')


def cell(img, rect, items, cursor=None, read=(), current=None, thread=False):
    """items: [(label, chapter_id, extra_text)] split horizontally."""
    x0, y0, x1, y1 = rect
    L.fill(img, rect, (0, 0, 0, 255))
    n = max(1, len(items))
    seg = (x1 - x0) / n
    for k, (lab, cid, extra) in enumerate(items):
        sx0, sx1 = x0 + k * seg, x0 + (k + 1) * seg
        if cid == cursor:
            L.textured(img, (sx0 + 1, y0 + 1, sx1 - 1, y1 - 1), crimson_tex)
            L.rect(img, (sx0 + 1, y0 + 1, sx1 - 1, y1 - 1), (206, 200, 200, 255))
        mid = (y0 + y1) / 2
        tx = sx0 + 7
        bright = cid in read or cid == cursor
        if cid in read:
            L.check_icon(img, tx, mid, 11, L.WHITE)
            tx += 12
        L.text(img, (tx, mid), lab, 'serif', 13 if seg > 60 else 12, L.WHITE if bright else (192, 190, 198), anchor='lm')
        tx += L.text_width(lab, 'serif', 13 if seg > 60 else 12) + 6
        if extra:
            L.text(img, (tx, mid + 0.5), extra, 'sans', 10, (170, 168, 178), anchor='lm', shadow=False)
        c = CH[cid]
        rx = sx1 - 6
        if c['views']:
            rx -= 13
            L.view_icon(img, rx, mid - 3.2, 5)
            if c['views'] > 1:
                L.text(img, (rx + 12.5, mid), str(c['views']), 'sans', 9, (200, 196, 214), anchor='lm', shadow=False)
            rx -= 6
        if c['choices']:
            wdt = 12 + (2.5 + L.text_width(str(c['choices']), 'sans', 9) if c['choices'] > 1 else 0)
            rx -= wdt
            L.choice_icon(img, rx, mid - 2.5, c['choices'])
            rx -= 4
        if cid == current:
            img.alpha_composite(LEAF, (L.s(rx - 17), L.s(mid - 8)))
            L.text(img, (rx - 19, mid), '지금', 'sans', 10, L.LEAF, anchor='rm', shadow=True)
        if k:
            L.fill(img, (sx0, y0 + 3, sx0 + 0.5, y1 - 3), (80, 78, 88, 255))


def grid_lines(img, rects):
    for r in rects:
        L.rect(img, r, L.LINE + (255,))


def threads(img, col_spans):
    d = ImageDraw.Draw(img)
    for x, y0, y1 in col_spans:
        d.line((L.s(x), L.s(y0), L.s(x), L.s(y1)), fill=(64, 62, 72, 255), width=L.S)


def info_strip(img, left, right):
    L.fill(img, (94, INFO_TOP, 760, INFO_BOT), (0, 0, 0, 255))
    L.fill(img, (94, INFO_TOP, 760, INFO_TOP + 0.5), L.LINE + (255,))
    L.text(img, (101, (INFO_TOP + INFO_BOT) / 2), left, 'sans', 11, (222, 220, 228), anchor='lm')
    L.text(img, (753, (INFO_TOP + INFO_BOT) / 2), right, 'sans', 10, (150, 150, 160), anchor='rm', shadow=False)


LV = 21
INTRO_TOP, INTRO_BOT = BODY_TOP, BODY_TOP + 26


def day_rows():
    """Shared row geometry: both pages put day N on the same screen row (days 4·5 are two levels tall)."""
    y = {4: INTRO_BOT}
    y[5] = y[4] + 2 * LV
    y[6] = y[5] + 2 * LV
    for d in range(7, 21):
        y[d] = y[d - 1] + LV          # y[20] = '그 뒤' top
    return y, y[20] + LV


def day_axis(img, y):
    for d in range(4, 20):
        h = 2 * LV if d in (4, 5) else LV
        axis_cell(img, y[d], y[d] + h, f'{d}일째', weekday(d), wcolor(d))
    axis_cell(img, y[20], y[20] + LV, '그 뒤', tex=gray_tex)


# ------------------------------------------------------------------ 본편

def main_page(cursor='kureha_05', current='00_レコンキスタ_start_2', read=('00_レコンキスタ_start',)):
    img = frame_common('이야기 지도', '최종편으로', '날짜')
    cols = list(zip(GRID_X[:-1], GRID_X[1:]))
    plate_c, plate_n = L.name_plate_crimson(), L.name_plate_navy()
    header_plates(img, cols, ['쿠레하', '마사키', '마호코', '시이나'], [plate_c, plate_c, plate_n, plate_n])
    intro_top, intro_bot = INTRO_TOP, INTRO_BOT
    y, body_bot = day_rows()
    rects = []
    # the chronicle sheet: every day row and column ruled, merged cells drawn over it
    sheet = [(GRID_X[0], y[d], GRID_X[-1], y[d] + 0.5) for d in range(4, 21)] + [(GRID_X[0], body_bot - 0.5, GRID_X[-1], body_bot)]
    sheet += [(x, y[4], x + 0.5, body_bot) for x in GRID_X]
    for r in sheet:
        L.fill(img, r, L.LINE + (255,))
    routes = ['kureha', 'masa', 'maho', 'sina']
    placed = {}
    for cid, c in CH.items():
        pre = cid.split('_', 1)[0]
        if pre not in routes:
            continue
        day = 20 if cid.endswith(('_ep', '_epi')) else DAYS[cid]['end']
        placed.setdefault((routes.index(pre), day), []).append(cid)
    # thin thread through a route's empty days, drawn under every cell
    spans = []
    for ci in range(4):
        x0, x1 = cols[ci]
        spans.append(((x0 + x1) / 2, y[4], y[20]))
    threads(img, spans)
    # intro band: three days left to right
    third = (GRID_X[-1] - GRID_X[0]) / 3
    for k, cid in enumerate(['00_レコンキスタ_start', '00_レコンキスタ_start_2', '00_レコンキスタ_start_3']):
        r = (GRID_X[0] + k * third, intro_top, GRID_X[0] + (k + 1) * third, intro_bot)
        d = k + 1
        cell(img, r, [(f'도입부 {d}', cid, f'{d}일째 {weekday(d)}')], cursor, read, current)
        rects.append(r)
    # commons
    r = (GRID_X[0], y[4], GRID_X[2], y[5] + LV)
    cell(img, r, [('마키노 공통', 'makino_kyoutu', '4~5일째')], cursor, read, current)
    rects.append(r)
    r = (GRID_X[2], y[4], GRID_X[4], y[4] + LV)
    cell(img, r, [('신야 공통', 'shinya_kyoutu', '4일째')], cursor, read, current)
    rects.append(r)
    # route columns
    for (ci, day), ids in sorted(placed.items()):
        x0, x1 = cols[ci]
        if day == 4:
            r = (x0, y[4] + LV, x1, y[5])
        elif day == 5 and ci in (0, 1):
            r = (x0, y[5] + LV, x1, y[6])
        else:
            r = (x0, y[day], x1, y[day] + (2 * LV if day == 5 else LV))
        ids.sort(key=lambda i: [int(p) if p.isdigit() else 0 for p in label(i).split('-')])
        cell(img, r, [(label(i), i, None) for i in ids], cursor, read, current)
        rects.append(r)
    grid_lines(img, rects)
    day_axis(img, y)
    c = CH[cursor]
    info_strip(img, f'쿠레하 05 · 5일째 (일) · 장면 10 · 대사 {c["pages"]}줄 · 선택지 없음',
               'F1 도움말 · Enter 열기 · Esc 닫기')
    assert body_bot <= INFO_TOP, body_bot
    return img


# ------------------------------------------------------------------ 최종편

def final_page(cursor='last_gendai09'):
    """현재 sits on the same day rows as 본편; 과거 has no dates, so it is a separate, evenly divided strand."""
    img = frame_common('이야기 지도', '본편으로', '날짜')
    split = 470
    cols = [(GRID_X[0], split), (split + 16, GRID_X[-1])]
    pl = L.name_plate_crimson()
    header_plates(img, cols, ['현재', '과거'], [pl, pl])
    y, body_bot = day_rows()
    x0, x1 = cols[0]
    for r in [(x0, y[d], x1, y[d] + 0.5) for d in range(4, 21)] + [(x0, body_bot - 0.5, x1, body_bot), (x0, y[4], x0 + 0.5, body_bot), (x1, y[4], x1 + 0.5, body_bot)]:
        L.fill(img, r, L.LINE + (255,))
    threads(img, [((x0 + x1) / 2, INTRO_TOP, y[20])])
    rects = []
    for i in range(1, 17):
        cid = f'last_gendai{i:02d}'
        d = DAYS[cid]['end']
        if d <= 3:
            r = (x0, INTRO_TOP, x1, INTRO_BOT)
        else:
            r = (x0, y[d], x1, y[d] + (2 * LV if d in (4, 5) else LV))
        cell(img, r, [(f'현재 {i:02d}', cid, f'{d}일째 {weekday(d)}' if d <= 3 else None)], cursor)
        rects.append(r)
    r = (x0, y[20], x1, y[20] + LV)
    cell(img, r, [('결말 후일담', 'last_ep', None)], cursor)
    rects.append(r)
    grid_lines(img, rects)
    # 과거: twelve equal cells over the whole body, deliberately off the day rules
    px0, px1 = cols[1]
    L.text(img, ((px0 + px1) / 2, INTRO_TOP + 9), '날짜 없이 이어지는 이야기', 'sans', 10, (176, 174, 184), anchor='mm', shadow=False)
    top = INTRO_TOP + 20
    hgt = (body_bot - top) / 12
    for i in range(1, 13):
        r = (px0, top + (i - 1) * hgt, px1, top + i * hgt)
        cell(img, r, [(f'과거 {i:02d}', f'last_kako{i:02d}', None)], cursor)
        rects.append(r)
        L.rect(img, r, L.LINE + (255,))
    day_axis(img, y)
    c = CH[cursor]
    info_strip(img, f'현재 09 · 12일째 (일) · 대사 {c["pages"]}줄 · 선택지 없음', 'Tab 본편 · Enter 열기 · Esc 닫기')
    return img


if __name__ == '__main__':
    main_page().convert('RGB').save(OUT / 'map_main.png')
    final_page().convert('RGB').save(OUT / 'map_final.png')
    print('ok')
