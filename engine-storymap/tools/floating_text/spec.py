"""What build.py makes: the game's floating Japanese lines and time cards in Korean (11-26).

Lines follow the body text's own translation of the same words where the story has them (argon-retranslation-reviewed
검수확정_번역필드.jsonl: kureha_14 「자, 치즈――」, last_kako04 「…네, 맹세합니다」, sina_19_2 「……오라버니!」, last_kako12 /
kureha_15 / masa_18 for Revelation 14:13, last_ep 오빠 for お兄ちゃん), the rest in the same voice (kureha_11: Kureha's call
from under the water, 차분한 반말; last_gendai16: Yue's 「おにいちゃん」 = 오빠).

Fonts: the time cards in a heavy serif like their Japanese (Noto Serif KR 900); the brush-hand lines (netu110g, netu125_)
in 궁서 (Gungsuh), the verses' book type (netu125b_) in the game's own Korean serif (Noto Serif CJK KR, = Reconquista KR
Serif); the rounded-gothic quotes with a halo in Noto Sans KR. Sizes and halos match the originals by eye (preview/).
"""
from pathlib import Path

CODEX = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타')
SERIF_CJK = CODEX / 'research' / 'fonts' / 'NotoSerifCJKkr-Regular.otf'
SANS_VF = Path(r'C:\Windows\Fonts\NotoSansKR-VF.ttf')
SERIF_VF = Path(r'C:\Windows\Fonts\NotoSerifKR-VF.ttf')
BATANG_TTC = Path(r'C:\Windows\Fonts\batang.ttc')          # face 2: Gungsuh (궁서)

STYLES = {
    # Kureha's call over the water (netu110g1-3): a thin brush hand, white, spread to the Japanese line's width
    'brush': dict(font=BATANG_TTC, index=2, size=29, fill=(250, 251, 252, 255), max_tracking=0.9, alt_font=SERIF_CJK, alt_chars='「」『』'),
    # the verse in the brush hand (netu125_0x)
    'brush_verse': dict(font=BATANG_TTC, index=2, size=25, tracking=0.1, fill=(238, 236, 236, 255), align='left', alt_font=SERIF_CJK, alt_chars='「」『』', max_tracking=0.5),
    # the verse in book type (netu125b_0x)
    'verse': dict(font=SERIF_CJK, size=23, tracking=0.17, fill=(232, 230, 230, 255), align='left', max_tracking=0.5),
    # 「어서 와… 오빠」, 「…네, 맹세합니다」: white rounded gothic, soft blue halo
    'soft_blue': dict(font=SANS_VF, weight=700, size=32, fill=(255, 255, 255, 255), halo=(60, 85, 140, 235, 2.6, 0.7), margin=3, max_tracking=0.55),
    # 『자, 치즈…』: white with a white glow
    'warm_glow': dict(font=SANS_VF, weight=600, size=40, fill=(255, 255, 252, 255), halo=(255, 252, 240, 215, 3.2, 1.2), margin=4, max_tracking=0.35),
    # 「……오라버니!」: small white with a soft grey shadow
    'gray_small': dict(font=SANS_VF, weight=700, size=20, fill=(255, 255, 255, 255), halo=(95, 95, 105, 230, 1.7, 0.5), margin=2, max_tracking=0.6),
    # 『…오빠…』: white with a soft grey shadow, wide apart
    'gray_wide': dict(font=SANS_VF, weight=650, size=30, fill=(255, 255, 255, 255), halo=(95, 95, 105, 230, 2.2, 0.6), margin=3, max_tracking=0.45),
    # time cards: 약 / 년 전 in the heavy serif of 約 / 年前, the number as large as the original's
    'card': dict(font=SERIF_VF, weight=900, size=40, fill=(255, 255, 255, 255)),
    'card_line': dict(font=SERIF_VF, weight=900, size=40, fill=(255, 255, 255, 255), max_tracking=0.5),
}

G_CALL = 'kureha_11: 水面の向こうから呼ぶ声 (暮葉, 차분한 반말)'
VERSE = 'Revelation 14:13 as last_kako12 / kureha_15 / masa_18 (검수확정)'


def single(name, clean, lines, style, source, **over):
    t = {'lines': lines, 'style': style}
    t.update({k: v for k, v in over.items() if k in ('dx', 'dy', 'x', 'y', 'style_over')})
    item = {'name': name, 'clean': clean, 'text': [t], 'source': source}
    if 'view' in over:
        item['view'] = over['view']
    return item


def sib(src, box, **kw):
    return {'kind': 'sibling', 'from': src, 'box': box, **kw}


def inp(box, **kw):
    return {'kind': 'inpaint', 'box': box, **kw}


ITEMS = []

# ---- Kureha's call from under the water (kureha_11)
G = {'kind': 'scaled', 'from': 'netu110f', 'k': 0.7098, 'box': [180, 280, 690, 332]}
ITEMS += [
    single('netu110g1', G, ['「이리 와…」'], 'brush', G_CALL + ' 「いらっしゃい…」'),
    single('netu110g2', G, ['「이쪽으로 와…」'], 'brush', G_CALL + ' 「こっちへいらっしゃい…」'),
    single('netu110g3', G, ['「자, 이쪽으로… 나와 함께…」'], 'brush', G_CALL + ' 「さぁ、こっちへ…私と一緒に…」'),
]

# ---- 「おかえりなさい…おにいちゃん」 (last_gendai16, Yue)
YUE = 'last_gendai16 悠絵 「おかえりなさい…おにいちゃん」 (おにいちゃん = 오빠, last_gendai16::010117)'
ITEMS += [
    single('ev5012', sib('ev501', [150, 255, 650, 318]), ['「어서 와… 오빠」'], 'soft_blue', YUE),
    single('ev501c', inp([150, 258, 650, 314], threshold=6, grow=3), ['「어서 와… 오빠」'], 'soft_blue', YUE,
           style_over={'opacity': 0.35, 'blur': 0.6}),
    single('ev501d', {'kind': 'clean_of', 'from': 'ev501c', 'box': [150, 255, 650, 318]}, ['「어서 와… 오빠」'], 'soft_blue', YUE),
]

# ---- 「…はい、誓います。」 (last_ep, the vow; last_kako04::003661 「…네, 맹세합니다」)
VOW = 'last_ep 「…はい、誓います。」 = last_kako04::003661 「…네, 맹세합니다」'
V = sib('ev5043c', [215, 232, 625, 296])
ITEMS += [
    single('ev5043c2', V, ['「…네, 맹세합니다」'], 'soft_blue', VOW),
    single('ev5043cc', V, ['「…네, 맹세합니다」'], 'soft_blue', VOW),
    single('ev5043cb', V, ['「…네, 맹세합니다」'], 'soft_blue', VOW, style_over={'blur': 2.2, 'opacity': 0.85}),
    single('ev5043ca', V, ['「…네, 맹세합니다」'], 'soft_blue', VOW, style_over={'blur': 6.0, 'opacity': 0.55}),
    single('ev5043cd', {'kind': 'scaled', 'from': 'ev5043c', 'k': 0.494, 'b': 128.7, 'box': [215, 232, 625, 296]}, ['「…네, 맹세합니다」'], 'soft_blue', VOW),
    single('ev5043ce', {'kind': 'flat', 'rgb': [255, 255, 255], 'box': [215, 232, 625, 296]}, ['「…네, 맹세합니다」'], 'soft_blue', VOW),
]

# ---- 『はい、チーズ…』 (kureha_19, the photo on the phone; kureha_14::002779 「자, 치즈――」)
CHEESE = 'kureha_19 『はい、チーズ…』 = kureha_14::002779 「자, 치즈――」'
ITEMS += [
    single('ev1132a', sib('ev113a', [225, 240, 605, 325]), ['『자, 치즈…』'], 'warm_glow', CHEESE, style_over={'blur': 4.0}),
    single('ev1132b', sib('ev113a', [225, 240, 605, 325]), ['『자, 치즈…』'], 'warm_glow', CHEESE),
    single('ev1132c', inp([225, 240, 605, 325], threshold=14, grow=3), ['『자, 치즈…』'], 'warm_glow', CHEESE),
    single('ev1132d', sib('ev113b', [225, 240, 605, 325]), ['『자, 치즈…』'], 'warm_glow', CHEESE),
]

# ---- 「……兄さんっ!」 (sina_19_2::000821 「……오라버니!」)
NII = 'nisan 「……兄さんっ!」 = sina_19_2::000821 「……오라버니!」'
N = sib('nisan03', [298, 308, 508, 350])
ITEMS += [
    single('nisan04', N, ['「……오라버니!」'], 'gray_small', NII, style_over={'opacity': 0.3}),
    single('nisan05', N, ['「……오라버니!」'], 'gray_small', NII),
    single('nisan06', inp([298, 308, 508, 350], threshold=8, grow=3), ['「……오라버니!」'], 'gray_small', NII),
    single('nisan07', inp([298, 308, 508, 350], threshold=8, grow=3), ['「……오라버니!」'], 'gray_small', NII),
    single('nisan08', inp([298, 308, 508, 350], threshold=8, grow=3), ['「……오라버니!」'], 'gray_small', NII),
    single('nisan09', {'kind': 'flat', 'rgb': [255, 255, 255], 'box': [298, 308, 508, 350]}, ['「……오라버니!」'], 'gray_small', NII),
]

# ---- 『…おにいちゃん…』 (maho_19; お兄ちゃん = 오빠 as last_ep)
MAHO = 'maho_19 『…おにいちゃん…』 (= 오빠, last_ep)'
ITEMS += [
    single('maho_tui03', sib('maho_tui02', [250, 295, 580, 345]), ['『…오빠…』'], 'gray_wide', MAHO, style_over={'blur': 3.5, 'opacity': 0.55}),
    single('maho_tui04', inp([250, 290, 580, 345], threshold=8, grow=3), ['『…오빠…』'], 'gray_wide', MAHO),
    single('maho_tui05', inp([250, 290, 580, 345], threshold=8, grow=3), ['『…오빠…』'], 'gray_wide', MAHO),
]

# ---- Revelation 14:13 (00_レコンキスタ_start_3): book type (b) and brush hand
RV = {'kind': 'sibling', 'from': 'img103'}
ITEMS.append({'name': 'netu125b_01', 'clean': {**RV, 'box': [80, 280, 720, 320]}, 'source': VERSE,
              'text': [{'lines': ['또 나는 하늘에서 이렇게 고하는 소리를 들었다.'], 'style': 'verse', 'style_over': {'align': 'center'}}]})
for b, style in (('netu125b', 'verse'), ('netu125', 'brush_verse')):
    if b == 'netu125':
        ITEMS.append({'name': 'netu125_01', 'clean': {**RV, 'box': [80, 278, 720, 322]}, 'source': VERSE,
                      'text': [{'lines': ['또 나는 하늘에서 이렇게 고하는 소리를 들었다.'], 'style': style, 'style_over': {'align': 'center'}}]})
    ITEMS.append({'name': f'{b}_02', 'clean': {**RV, 'box': [40, 240, 760, 330]}, 'source': VERSE, 'view': [40, 250, 760, 325],
                  'text': [{'lines': ['기록하여라.'], 'style': style, 'x': 56, 'y': 272 if b == 'netu125b' else 264},
                           {'lines': ['『이제부터 주님 안에서 죽는 사람은 복되도다』라고.'], 'style': style, 'x': 56, 'y': 311 if b == 'netu125b' else 299}]})
    ITEMS.append({'name': f'{b}_03', 'clean': {**RV, 'box': [70, 190, 730, 340]}, 'source': VERSE, 'view': [70, 200, 730, 335],
                  'text': [{'lines': ['성령도 말씀하신다.'], 'style': style, 'x': 85, 'y': 226 if b == 'netu125b' else 213},
                           {'lines': ['『그러하다. 그들은 노고에서 풀려나 안식을 얻으리니,'], 'style': style, 'x': 85, 'y': 284 if b == 'netu125b' else 284},
                           {'lines': ['그 행실이 보답을 받을 것이기 때문이라』'], 'style': style, 'x': 107, 'y': 314 if b == 'netu125b' else 318}]})
    ITEMS.append({'name': f'{b}_04', 'clean': {**RV, 'box': [330, 280, 470, 320]}, 'source': VERSE + ' 「アーメン」 = 「아멘」',
                  'text': [{'lines': ['아멘'], 'style': style, 'style_over': {'align': 'center', 'fit': False, 'tracking': 0.25}}]})

# ---- time cards over 04yb2 (約N年前 / 約N週間前), and two single cards
CARD_BOX = [250, 225, 524, 335]                 # the line; the [RECONQUISTA] block starts at x 525
YEARS = {'04yb2': 4, '1yb2': 1, '9yb': 9, '10yb2': 10, '11yb2': 11, '12yb': 12, '22yb': 22, '28yb': 28, '29yb': 29, '30yb': 30, '40yb': 40}
WEEKS = {'09wb': 9, '11wb': 11, '13wb2': 13}
CARDS = list(YEARS) + list(WEEKS)
for n, v in YEARS.items():
    ITEMS.append({'name': n, 'card': {'box': CARD_BOX, 'number': v, 'lines': ['약', '년 전']}, 'source': f'約{v}年前 → 약 {v}년 전'})
for n, v in WEEKS.items():
    ITEMS.append({'name': n, 'card': {'box': CARD_BOX, 'number': v, 'lines': ['약', '주 전']}, 'source': f'約{v}週間前 → 약 {v}주 전'})
ITEMS.append({'name': '01ma', 'card': {'box': [280, 250, 520, 330], 'style': 'card_line', 'lines': ['한 달 후'], 'whole': True}, 'source': '一ヶ月後 → 한 달 후'})
ITEMS.append({'name': 'netu404', 'card': {'box': [280, 250, 520, 330], 'style': 'card_line', 'lines': ['몇 시간 전'], 'whole': True},
              'source': '数時間前 → 몇 시간 전 (maho_09 「불과 몇 시간 전」)'})

# ---- the title cards (catch01-03) and the bus (img107): Codex's 4x redraws already say 레콘키스타 / 임해 뉴타운
# (deliverables/redraw-4k-20261025 translation-map); their own 1x pictures (no HD pack, or the 「원래 화면」 choice) did not
LOGO = 'Codex redraw-4k-20261025: レコンキスタ → 레콘키스타 (brand-logo-ko-v3 master)'
for n in ('catch01', 'catch02', 'catch03'):
    ITEMS.append({'name': n, 'from4k': {'boxes': [(440, 330, 800, 600)], 'threshold': 40, 'hull': True, 'grow': 4, 'soft': 5},
                  'view': [430, 330, 800, 600],
                  'source': LOGO, 'lines': ['레콘키스타']})
ITEMS.append({'name': 'img107', 'from4k': {'boxes': [(240, 76, 420, 118), (240, 368, 390, 404)], 'threshold': 30},
              'view': [230, 70, 430, 410], 'source': 'Codex redraw-4k-20261025: 臨海ニュータウン → 임해 뉴타운', 'lines': ['임해 뉴타운']})
