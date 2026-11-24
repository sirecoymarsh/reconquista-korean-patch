# 전체 칸 기계 점검. 입력 work/table.json, 출력 work/machine_findings.tsv, work/machine_summary.json
import json, sys, re, collections, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

import os
T = json.load(open(os.environ.get('RV_TABLE') or (RV / 'work' / 'table.json'), encoding='utf-8'))
OUTP = os.environ.get('RV_OUT') or 'machine'
rows = T['rows']; units = T['units']
byid = {r['id']: r for r in rows}
fontmap = json.loads((Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타') / 'builds' / 'body-ui-20261025-v20-nuance' / 'font-map.json').read_text('utf-8-sig'))['mapping']

findings = []
def add(r, check, detail=''):
    findings.append((r['id'], r['unit'], r['model'], check, detail, r['sp'] or '', r['ja'], r['ko'], r['v20'] or ''))

def cp932_ok(ch):
    try: ch.encode('cp932'); return True
    except UnicodeEncodeError: return False

def width(s):
    w = 0
    for ch in s:
        if ch in fontmap or HANGUL.match(ch): w += 2
        else:
            try: w += len(ch.encode('cp932'))
            except UnicodeEncodeError: w += 2
    return w

hangul_only = lambda s: ''.join(HANGUL.findall(s or ''))
def bigrams(s):
    s = hangul_only(s)
    return collections.Counter(s[i:i+2] for i in range(len(s)-1))
def dice(a, b):
    A, B = bigrams(a), bigrams(b)
    if not A or not B: return 0.0
    inter = sum((A & B).values())
    return 2 * inter / (sum(A.values()) + sum(B.values()))

# ---------- 1~3 칸 단위 구조 ----------
missing_chars = collections.Counter(); missing_char_ids = collections.defaultdict(list)
for r in rows:
    ja, ko = r['ja'], r['ko']
    if r['model'] == 'source retained':
        if ko != ja: add(r, 'SOURCE_RETAINED_CHANGED')
        continue
    if not ko.strip() and ja.strip() and r['role'] != 'r':
        add(r, 'EMPTY')
    if KANA.search(ko): add(r, 'KANA_LEFT', ''.join(sorted(set(KANA.findall(ko)))))
    if HAN.search(ko): add(r, 'KANJI_LEFT', ''.join(sorted(set(HAN.findall(ko)))))
    if r['fixed'] and ko != ja: add(r, 'FIXED_CHANGED')
    if '\n' in ko or '\t' in ko or '\r' in ko: add(r, 'CTRL_CHAR')
    for ch in ko:
        if HANGUL.match(ch) and ch not in fontmap:
            missing_chars[ch] += 1; missing_char_ids[ch].append(r['id'])
        elif not HANGUL.match(ch) and ch not in fontmap and not cp932_ok(ch):
            missing_chars[ch] += 1; missing_char_ids[ch].append(r['id'])

# ---------- 4~7 행(유닛) 단위 괄호·기호 ----------
def norm_br(s):
    return s.replace('（', '(').replace('）', ')')
PAIRS = ['「', '」', '『', '』', '(', ')', '【', '】', '《', '》', '“', '”']
SYMS = ['＊＊＊', '***', '♪', '★', '☆', '♥', '♡', '※', '■', '●']
unit_fields = collections.defaultdict(list)
for r in rows: unit_fields[r['unit']].append(r)
for u, fs in unit_fields.items():
    fs.sort(key=lambda r: r['id'])
    if all(f['model'] == 'source retained' for f in fs): continue
    model = collections.Counter(f['model'] for f in fs if f['model'] != 'source retained').most_common(1)[0][0]
    tfs = [f for f in fs if f['role'] in ('t', 'b', 'e', 'f')]
    ja = norm_br(''.join(f['ja'] for f in tfs)); ko = norm_br(''.join(f['ko'] for f in tfs))
    head = fs[0]
    for p in PAIRS:
        if ja.count(p) != ko.count(p):
            add(dict(head, ja=ja, ko=ko, model=model), 'BRACKET_COUNT', f'{p} ja{ja.count(p)} ko{ko.count(p)}')
    for s in SYMS:
        if s in ('＊＊＊', '***'):
            if ja.count(s) != ko.count(s): add(dict(head, ja=ja, ko=ko, model=model), 'HIDDEN_MARK', f'{s} ja{ja.count(s)} ko{ko.count(s)}')
        elif ja.count(s) != ko.count(s):
            add(dict(head, ja=ja, ko=ko, model=model), 'SYMBOL', f'{s} ja{ja.count(s)} ko{ko.count(s)}')
    if ja.startswith('「') != ko.startswith('「') or ja.endswith('」') != ko.endswith('」'):
        add(dict(head, ja=ja, ko=ko, model=model), 'QUOTE_EDGE')
    # 줄머리 전각 공백
    for f in tfs[1:]:
        if f['role'] != 't': continue
        if f['ja'].startswith('　') != f['ko'].startswith('　'):
            add(f, 'INDENT', 'ja' + ('有' if f['ja'].startswith('　') else '無'))

# ---------- 8 길이 ----------
wj = [width(r['ja']) for r in rows if r['role'] == 't']
wv = [width(r['v20']) for r in rows if r['role'] == 't' and r['v20']]
def pct(a, q): a = sorted(a); return a[int(len(a) * q) - 1]
LIMIT = max(max(wj), pct(wv, 0.999))
len_stats = dict(ja_max=max(wj), ja_p99=pct(wj, 0.99), v20_max=max(wv), v20_p999=pct(wv, 0.999), v20_p99=pct(wv, 0.99), limit=LIMIT)
for r in rows:
    if r['role'] != 't' or r['model'] == 'source retained': continue
    w = width(r['ko'])
    if w > LIMIT: add(r, 'TOO_WIDE', f'{w}>{LIMIT}')
    hv = hangul_only(r['v20']); hk = hangul_only(r['ko'])
    if len(hv) >= 10:
        ratio = len(hk) / len(hv)
        if ratio < 0.45 or ratio > 2.3: add(r, 'LEN_RATIO_V20', f'{ratio:.2f}')

# ---------- 9 대사 속 그/그녀 ----------
PRON = re.compile(r'(?<![가-힣])(그녀[가-힣]{0,3}|그(?:는|가|를|의|에게|한테|와|랑|도|만큼은|더러)(?![가-힣]))')
for r in rows:
    if r['model'] == 'source retained' or r['role'] != 't': continue
    u = units.get(r['unit'])
    dialog = bool(u and u['sp'] and u['sp'].strip()) or r['ko'].lstrip('　').startswith('「')
    if not dialog: continue
    for m in PRON.finditer(r['ko']):
        tok = m.group(1)
        if tok.startswith('그') and not tok.startswith('그녀') and tok in ('그도', '그와', '그랑', '그만큼은'):
            # 그도/그와 는 지시어일 때가 많아 원문 彼 있을 때만
            if '彼' not in r['ja']: continue
        add(r, 'PRONOUN_DIALOG', tok + (' (ja彼)' if '彼' in r['ja'] else ''))

# ---------- 10 따옴표 앞 마침표 ----------
period_q = collections.Counter()
for r in rows:
    if re.search(r'(?<![.…])\.[」』]', r['ko']): period_q[r['model']] += 1
v20_period = sum(1 for r in rows if r['v20'] and re.search(r'(?<![.…])\.[」』]', r['v20']))

# ---------- 11 존댓말 계열 v20 대비 ----------
END_STRIP = re.compile(r'[\s…!?！？~～♪★☆♥♡」』)\-―—、。,.・ー]+$')
def speech_class(s):
    s = s.replace('　', ' ')
    s = END_STRIP.sub('', s)
    s = re.sub(r'\(.*?\)$', '', s).rstrip()
    s = END_STRIP.sub('', s)
    if not s: return None
    if re.search(r'(니다|니까|십시오|습니다|옵니다|소서|나이다)$', s): return 'H'
    if re.search(r'(요|죠|세요|에요|예요|군요|네요|지요|래요|까요|가요|나요|데요|어요|아요|해요|게요|걸요)$', s): return 'Y'
    if re.search(r'[가-힣]$', s): return 'B'
    return None
for u, fs in unit_fields.items():
    un = units.get(u)
    if not un or not un['sp'] or not un['sp'].strip(): continue
    tfs = [f for f in fs if f['role'] == 't' and f['model'] != 'source retained' and f['v20']]
    if not tfs: continue
    last = tfs[-1]
    a, b = speech_class(last['ko']), speech_class(last['v20'])
    if a and b and a != b and ('B' in (a, b)):
        add(last, 'POLITENESS_VS_V20', f'new{a} v20{b}')

# ---------- 12 한 칸 밀림 (v20 이웃과 비교) ----------
script_ids = collections.defaultdict(list)
for r in rows:
    if r['role'] == 't' and r['v20']: script_ids[r['id'].split('::')[0]].append(r['id'])
for sc, ids in script_ids.items():
    ids.sort()
    for i, x in enumerate(ids):
        r = byid[x]
        if r['model'] == 'source retained' or len(hangul_only(r['ko'])) < 8: continue
        same = dice(r['ko'], r['v20'])
        best = 0; bi = None
        for j in (i - 2, i - 1, i + 1, i + 2):
            if 0 <= j < len(ids):
                d = dice(r['ko'], byid[ids[j]]['v20'])
                if d > best: best, bi = d, ids[j]
        if best > 0.55 and best > same + 0.3:
            add(r, 'SHIFT_SUSPECT', f'same{same:.2f} nb{best:.2f} {bi}')

# ---------- 13 이름·용어 ----------
TERMS = [
    ('トオル', ['도오루'], ['토오루']),
    ('悠絵', ['유에'], []),
    ('暮葉', ['쿠레하'], []), ('クレハ', ['쿠레하'], []),
    ('真帆子', ['마호코'], []), ('まほこ', ['마호코'], []),
    ('詩菜', ['시이나'], ['시나 ']), ('しーな', ['시이나'], []),
    ('麻咲', ['마사키'], []),
    ('信哉', ['신야'], []),
    ('槙野', ['마키노'], []), ('槇野', ['마키노'], []),
    ('慶吾', ['게이고'], []),
    ('上条', ['가미조'], ['카미조']),
    ('汐見', ['시오미'], []),
    ('矢嶋', ['야시마'], []),
    ('一ノ瀬', ['이치노세'], []),
    ('秋月', ['아키즈키'], []),
    ('秋月さん', ['아키즈키 씨'], ['아키즈키 양']),
    ('羽鳥', ['하토리'], []), ('三沢', ['미사와'], []), ('吉森', ['요시모리'], []), ('春日井', ['가스가이'], []),
    ('マッキー', ['맛키'], []),
    ('首刈り女', ['목 베는 여자'], []),
    ('反魂', ['반혼'], []),
    ('レコンキスタ', ['레콘퀴스타'], ['레콘키스타']),
    ('ゴーストタウン', ['고스트타운'], []),
    ('人工島', ['인공섬'], []),
    ('霊園', ['공원묘지'], []),
    ('臨海公園', ['해안 공원'], []),
    ('チャンス', ['찬스'], []),
    ('ショック', ['쇼크'], []),
    ('パニック', ['패닉'], []),
    ('メール', ['메일'], ['문자']),
    ('廃マンション', ['폐아파트'], []),
    ('シロ', ['시로'], []),
    ('依り代', ['매개체'], []),
    ('祟り', ['저주'], []),
]
term_stats = {}
for jt, good, bad in TERMS:
    st = collections.Counter()
    for r in rows:
        if jt not in r['ja'] or r['model'] == 'source retained': continue
        okk = any(g in r['ko'] for g in good)
        badk = [b for b in bad if b in r['ko']]
        st[(r['model'], 'ok' if okk else 'miss')] += 1
        if badk: add(r, 'TERM_BAD', f'{jt}->{badk}')
        elif not okk:
            # 이름은 한국어에서 생략될 수 있음: 같은 유닛 다른 칸에 있으면 통과
            uko = ''.join(x['ko'] for x in unit_fields[r['unit']])
            if not any(g in uko for g in good):
                add(r, 'TERM_MISS', f'{jt}->{good}')
        v = r['v20'] or ''
        if v and jt in r['ja']:
            st[('v20', 'ok' if any(g in v for g in good) else 'miss')] += 1
    term_stats[jt] = {f'{a}/{b}': n for (a, b), n in sorted(st.items())}

# ---------- 출력 ----------
import csv
with open(RV / 'work' / (OUTP + '_findings.tsv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['id', 'unit', 'model', 'check', 'detail', 'sp', 'ja', 'ko', 'v20'])
    for x in findings: w.writerow(x)
summ = collections.Counter((x[3], x[2]) for x in findings)
out = dict(counts={f'{a}|{b}': n for (a, b), n in sorted(summ.items())},
           missing_chars={'distinct': len(missing_chars), 'uses': sum(missing_chars.values()),
                          'hangul_distinct': sum(1 for c in missing_chars if HANGUL.match(c)),
                          'hangul_uses': sum(n for c, n in missing_chars.items() if HANGUL.match(c)),
                          'list': ''.join(c for c, _ in missing_chars.most_common()),
                          'by_char': {c: n for c, n in missing_chars.most_common()},
                          'model_uses': dict(collections.Counter(byid[i]['model'] for c in missing_char_ids for i in missing_char_ids[c]))},
           period_before_quote=dict(period_q, v20=v20_period), len_stats=len_stats, term_stats=term_stats)
json.dump(out, open(RV / 'work' / (OUTP + '_summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump({c: ids for c, ids in missing_char_ids.items()}, open(RV / 'work' / (OUTP + '_missing_char_ids.json'), 'w', encoding='utf-8'), ensure_ascii=False)
for k, n in sorted(summ.items()): print(k, n)
print(json.dumps({k: v for k, v in out.items() if k not in ('term_stats',)}, ensure_ascii=False)[:3000])
