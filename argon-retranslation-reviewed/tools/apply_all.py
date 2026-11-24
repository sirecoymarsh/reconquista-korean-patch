# 확정본 만들기: 원본 검수반영_번역필드.jsonl + 기계 고침 + 에이전트(채택분) + Claude 고침 + 용어 통일
# 출력: 검수확정_번역필드.jsonl, 검수기록.tsv  (results_reviewed_20261121 폴더)
import json, sys, csv, re, collections, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from common import *

SRC = BASE / 'results_complete' / '검수반영_번역필드.jsonl'
F = load_fields(SRC)
byid = {o['id']: o for o in F}
T = json.load(open(RV / 'work' / 'table.json', encoding='utf-8'))
units = T['units']
log = []          # (id, unit, model, 종류, 원래, 고친것, 이유, 출처)
cur = {o['id']: o['ko'] for o in F}
orig = dict(cur)
kinds = collections.defaultdict(list); reasons = collections.defaultdict(list); sources = collections.defaultdict(list)

def set_text(fid, new, kind, reason, source):
    old = cur[fid]
    if old == new: return False
    log.append((fid, byid[fid]['unit'], byid[fid]['translator_model'], kind, old, new, reason, source))
    cur[fid] = new; kinds[fid].append(kind); reasons[fid].append(reason); sources[fid].append(source)
    return True

def replace_once(fid, a, b, kind, reason, source):
    s = cur[fid]
    n = s.count(a)
    if n != 1: raise SystemExit(f'{source}: {fid} 「{a}」 {n}번 (현재 {s!r})')
    return set_text(fid, s.replace(a, b), kind, reason, source)

# 1) 기계 고침
KMAP = {'줄머리공백': '서식·줄머리 공백', '루비칸': '구조·루비칸', '괄호': '구조·괄호', '『』': '구조·『』', '띄어쓰기': '구조·띄어쓰기', '용어': '용어 통일'}
for f in json.load(open(RV / 'work' / 'fixes_mech.json', encoding='utf-8')):
    assert orig[f['id']] == f['old'], f['id']
    k = '+'.join(dict.fromkeys(KMAP[x] for x in f['kinds']))
    set_text(f['id'], f['new'], k, ' / '.join(dict.fromkeys(f['reasons'])), '기계 점검')

# 2) 에이전트 고침(채택 판정 반영)
SKIP_DUP = '기계 점검 고침과 같은 결함(이미 고침)'
OVERRIDE = {
    ('maho_15.mjo::003658', '될 수 있으면 그녀는'): 'SKIP:Claude 고침과 같음',
    ('last_gendai16.mjo::008449', '완전히 미라가 됩니다…'): 'SKIP:' + SKIP_DUP,
    ('last_gendai16.mjo::008486', '방법은 단 하나…'): 'SKIP:' + SKIP_DUP,
    ('last_gendai16.mjo::008534', '누군가 희생되어야만 합니다…'): 'SKIP:' + SKIP_DUP,
    ('sina_17.mjo::007144', '되살아났다고……'): 'SKIP:' + SKIP_DUP,
    ('maho_18.mjo::001649', '그전까지는,'): 'SKIP:' + SKIP_DUP,
    ('maho_18.mjo::001653', '지난 몇 년 동안 전혀 가까이 오려 하지 않았어…'): 'SKIP:' + SKIP_DUP,
    # 채택하되 고친 글을 조정
    ('masa_18.mjo::000434', '어딘가에 있는 그녀를'): '어딘가에 있는 그 사람을',
    ('maho_16.mjo::002283', '잃어버렸단 말야?'): '잃어버렸잖아?',
    ('sub_last.mjo::000088', '늦지 않고 잘 왔니?'): '늦지 않았지?',
}
SKIPPED = []
KIND_AGENT = {'기타': '외래어 살림'}
for o in json.load(open(RV / 'work' / 'agent_fixes_resolved.json', encoding='utf-8')):
    key = (o['id'], o['old'])
    new = o['new']; note = ''
    ov = OVERRIDE.get(key)
    if ov and ov.startswith('SKIP:'):
        SKIPPED.append((o['id'], o['old'], o['new'], ov[5:], o['packet'])); continue
    if ov: note = f' (에이전트 제안 「{o["new"]}」를 Claude 가 조정)'; new = ov
    kind = KIND_AGENT.get(o['kind'], o['kind'])
    replace_once(o['id'], o['old'], new, kind, o['why'] + note, f'검수 에이전트 {o["packet"]} → Claude 대조 채택')

# 3) Claude 고침 (work/fixes_claude.tsv)
for row in list(csv.reader(open(RV / 'work' / 'fixes_claude.tsv', encoding='utf-8-sig'), delimiter='\t'))[1:]:
    if not row or not row[0]: continue
    fid, kind, a, b, why = row[:5]
    replace_once(fid, a, b, kind, why, 'Claude')

# 4) 의문 목록에서 Claude 가 오류로 판정한 것
def unit_field(uid, idx): return [f for f in units[uid]['fields'] if f in byid][idx]
ex = [
    (unit_field('sub_last08.mjo::u0020', 0), '되살려 낸 딸의', '되살려 낸 딸이', '의미오류', '忘れ形見(죽은 이가 남긴 아이)를 「유복자」(아버지가 죽은 뒤 태어난 아이)로 비유해 뜻이 어긋남 — 같은 장면 sub_last u0861 처럼 「남기고 간 핏줄」로'),
    (unit_field('sub_last08.mjo::u0020', 1), '유복자나 다름없는 핏줄이니', '남기고 간 핏줄이니', '의미오류', '위와 같음'),
    (unit_field('sub_last03.mjo::u0097', 0), '「…몰라. 나는 아무것도 몰라」', '「…모릅니다. 저는 아무것도 몰라요」', '존댓말·반말', '같은 원문의 같은 장면 sub_last u0252 와 이 장면의 다른 줄은 존댓말인데 이 줄만 반말(같은 원문 행끼리 맞춤)'),
    (unit_field('sub_last03.mjo::u0103', 0), '「나는, 몰라…」', '「저는, 모릅니다…」', '존댓말·반말', '같은 원문의 sub_last u0258 과 맞춤'),
    (unit_field('sub_last03.mjo::u0105', 0), '그런 일이 있을 리가 없어」', '그럴 리가 없잖습니까」', '존댓말·반말', '같은 원문의 sub_last u0260 과 맞춤'),
    (unit_field('sub_last.mjo::u0163', 3), '가운데 상당수는', '가운데 일부는', '의미오류', '何割か(몇 할, 일부)를 「상당수」로 옮겨 수량이 커짐 — 같은 원문의 sub_last03 u0008 은 「일부」'),
    (unit_field('sub_last.mjo::u0876', 1), '자기 곁에', '곁에', '의미오류', '自分の傍 를 「자기 곁」으로 옮겨 누구 곁인지 흐리고 애칭으로도 읽힘 — 같은 원문의 sub_last08 u0035 처럼 생략'),
    (unit_field('kureha_19.mjo::u0478', 0), '내 자신도 매듭을', '나 자신에게도 매듭을', '오탈자·문법', '「내 자신」 비문, 自分自身にも始末をつける(자기 자신에게도 결말을 짓는다)'),
    (unit_field('last_gendai16.mjo::u0176', 0), '「시작할까요」', '「시작해 볼까」', '존댓말·반말', '이 대화에서 쿠레하(＊＊＊)는 줄곧 반말, 같은 원문의 maho_19 u0136·kureha_19 u0180 과 맞춤'),
    ('00_レコンキスタ_start_3.mjo::012606', '“그녀”가', '“그 여자”가', '대명사', '대사에 그녀 금지. 따옴표로 정체를 숨긴 彼女 는 지시어로 숨긴 채(검수 에이전트가 같은 꼴의 kureha_15 u0194 에 적용한 방식과 맞춤)'),
    ('shinya_kyoutu.mjo::002865', '“그녀”는', '“그 여자”는', '대명사', '위와 같음'),
    ('shinya_kyoutu.mjo::002883', '‘그녀’도', '‘그 여자’도', '대명사', '위와 같음'),
    ('00_レコンキスタ_start_2.mjo::020757', '고스트 타운', '고스트타운', '용어 통일', '고정 용어 고스트타운(같은 작품 표기와 맞춤)'),
    ('masa_09.mjo::002849', '고스트 타운', '고스트타운', '용어 통일', '고정 용어 고스트타운'),
    ('kureha_12.mjo::001433', '고스트 타운', '고스트타운', '용어 통일', '고정 용어 고스트타운'),
]
for i, (fid, a, b, kind, why) in enumerate(ex):
    replace_once(fid, a, b, kind, why, 'Claude(검수 에이전트 의문 판정)' if i < 9 else 'Claude')

# 5) 용어 통일: 禊ぎ → 정화 의식, おまじない → 주문
PART = {'라고': '이라고', '를': '을', '가': '이', '는': '은', '와': '과', '로': '으로', '라는': '이라는'}
def misogi(s):
    s = s.replace('미소기의 의식', '정화 의식')
    s = re.sub(r'『미소기』(라고|라는|를|가|는|와|로)?', lambda m: '『정화 의식』' + PART.get(m.group(1) or '', m.group(1) or ''), s)
    s = re.sub(r'미소기(라고|라는|를|가|는|와|로)?', lambda m: '정화 의식' + PART.get(m.group(1) or '', m.group(1) or ''), s)
    s = re.sub(r'『정화』(라고|라는|를|가|는|와|로)?', lambda m: '『정화 의식』' + PART.get(m.group(1) or '', m.group(1) or ''), s)
    s = s.replace('정화의 의식', '정화 의식')
    return s
for o in F:
    if '禊' in o['ja'] and o['translator_model'] != 'source retained':
        s = cur[o['id']]; n = misogi(s)
        if n != s: set_text(o['id'], n, '용어 통일', '禊ぎ 를 작품 대부분(v20·아르곤·AG 다수)과 같은 『정화 의식』으로 — 같은 원문 대사가 루트마다 『정화』·『미소기』로 갈려 있었음', 'Claude')
    if 'おまじない' in o['ja'] and '주술' in cur[o['id']]:
        set_text(o['id'], cur[o['id']].replace('주술', '주문'), '용어 통일', 'おまじない(유에·시이나의 괜찮아/기운 나는 주문)를 작품 대부분과 같은 「주문」으로', 'Claude')

# 5b) 외래어 되살리기 — 사용자 11-21 방침 「일본어에서 가타카나로 쓰인 외래어를 그냥 외래어인 채로 냅두는 정책이야.」
#     work/fixes_loan.json(외래어 검수 에이전트 L01~L04, 5단계까지 반영한 확정본 기준) 중 Claude 대조로 채택한 것
LOAN_SKIP = {}   # (id, 바꿀부분): 뺀 이유
# 사용자 11-21 다듬기 「좋아 사람의 말투가 아니라 일상어 가타카나는 그냥 번역하자.」 → 일상어(tools/loan_everyday.py)는 되돌린다
from loan_everyday import EVERYDAY
LOAN_REVERTED = []
LOAN_ADJ = {     # (id, 바꿀부분): Claude 가 고친 글
    ('00_レコンキスタ_start_2.mjo::001155', '보태 먹었으니'): '플러스해 먹었으니',        # 먹었다는 뜻을 살림
    ('00_レコンキスタ_start_2.mjo::006728', '가볍게 빗질을 하며'): '가볍게 브러시로 빗으며',  # 「브러시질」은 사전에 없는 꼴
    ('kureha_13.mjo::001000', '관계자와 접촉하고 싶었을'): '관계자와 콘택트하고 싶었을',     # 다른 곳(콘택트)과 표기 통일
    ('masa_17.mjo::002622', '충돌음이 들린'): '크래시 소리가 들린',                         # 「크래시음」은 낯선 합성
    ('kureha_18.mjo::002390', '충돌음'): '크래시 소리',
}
lf = RV / 'work' / 'fixes_loan.json'
if lf.exists():
    for o in json.load(open(lf, encoding='utf-8')):
        key = (o['id'], o['old'])
        if key in LOAN_SKIP: continue
        if o['word'] in EVERYDAY: LOAN_REVERTED.append(o); continue
        new = LOAN_ADJ.get(key, o['new'])
        note = f' (에이전트 제안 「{o["new"]}」를 Claude 가 조정)' if key in LOAN_ADJ else ''
        replace_once(o['id'], o['old'], new, '외래어 살림', f"{o['word']} 를 뜻풀이로 옮긴 것을 「{o['form']}」로: {o['why']}{note}",
                     f"외래어 검수 에이전트 {o['packet']} → Claude 대조 채택")
# (11-21 오전에 넣었던 ミネラルウォーター 「생수」→「미네랄워터」 2칸은 일상어라 뺐다 — 번역자의 「생수」가 그대로 남는다)

# 6) 출력
out = RV / '검수확정_번역필드.jsonl'
with open(out, 'w', encoding='utf-8', newline='\n') as f:
    for o in F:
        o2 = dict(o)
        if cur[o['id']] != orig[o['id']]:
            o2['ko'] = cur[o['id']]
            o2['claude_review'] = {'before': orig[o['id']], 'kinds': list(dict.fromkeys(kinds[o['id']])),
                                   'reasons': list(dict.fromkeys(reasons[o['id']])), 'sources': list(dict.fromkeys(sources[o['id']])),
                                   'date': '2026-11-21'}
        f.write(json.dumps(o2, ensure_ascii=False, separators=(',', ':')) + '\n')
with open(RV / '검수기록.tsv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['id', 'unit', '번역자', '종류', '원래', '고친것', '이유', '출처'])
    for r in log: w.writerow(r)
with open(RV / 'work' / '에이전트_제외.tsv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['id', '바꿀부분', '제안', '제외 이유', '묶음']); w.writerows(SKIPPED)
changed = sum(1 for k in cur if cur[k] != orig[k])
print('loan reverted (everyday)', len(LOAN_REVERTED), 'fields', len({o['id'] for o in LOAN_REVERTED}))
print('fields changed', changed, 'log rows', len(log), 'agent skipped', len(SKIPPED))
c = collections.Counter()
for fid in cur:
    if cur[fid] != orig[fid]:
        for k in dict.fromkeys(kinds[fid]): c[k] += 1
for k, n in c.most_common(): print(k, n)
print('by model', collections.Counter(byid[f]['translator_model'] for f in cur if cur[f] != orig[f]))
h = hashlib.sha256(out.read_bytes()).hexdigest(); print('sha256', h, out.stat().st_size)
