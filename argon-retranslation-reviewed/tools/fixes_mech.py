# 기계 점검에서 나온 구조·서식 고침 목록 → work/fixes_mech.json
import json, sys, re, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

T = json.load(open(RV / 'work' / 'table.json', encoding='utf-8'))
byid = {r['id']: r for r in T['rows']}; units = T['units']
fixes = {}   # id -> dict(old,new,kinds[],reasons[])
def put(fid, new, kind, reason):
    r = byid[fid]
    cur = fixes.get(fid, {}).get('new', r['ko'])
    if cur == new: return
    f = fixes.setdefault(fid, dict(id=fid, old=r['ko'], new=r['ko'], kinds=[], reasons=[], model=r['model']))
    f['new'] = new; f['kinds'].append(kind); f['reasons'].append(reason)
def cur(fid): return fixes.get(fid, {}).get('new', byid[fid]['ko'])

# 1) 루비칸: 원작은 ctrl s/o/f 로 작게 위에 그리는 읽기 text 명령. v20 은 모두 ' '. 들어간 낱말은 앞 칸으로 옮긴다.
R = '원작에서 작은 글씨 루비로 위에 그려지는 칸(v20 은 빈칸)에 본문 낱말이 들어가 게임에서 작게 겹쳐 보임 → 낱말을 앞 칸으로 옮기고 빈칸'
# 앞 칸 id 는 유닛 안 순서로 찾는다
def prev_field(fid):
    u = units[byid[fid]['unit']]; fs = u['fields']; i = fs.index(fid)
    return fs[i - 1] if i > 0 else None
def next_field(fid):
    u = units[byid[fid]['unit']]; fs = u['fields']; i = fs.index(fid)
    return fs[i + 1] if i + 1 < len(fs) else None
ruby_slots = [r['id'] for r in T['rows'] if r['fixed']]
special = {
    # maho_15 u0287: 아르곤이 루비칸에 원문에 없는 「그 『반혼』을 쓰는」을 넣고 앞 칸의 『 를 뺐다 → v20 과 같은 구조로
    'maho_15.mjo::003235': [('maho_15.mjo::003221', '「그렇다면 『'), ('maho_15.mjo::003235', ' '), ('maho_15.mjo::003248', '반혼술』이겠군」')],
    # maho_15 u0722: 루비칸 「죄를 씻고」가 뒤 칸 「속죄하는」과 같은 말을 겹쳐 씀(贖う 하나) → 루비칸 비움
    'maho_15.mjo::007626': [('maho_15.mjo::007626', ' ')],
    # maho_18 u0093: 빈 문자열 → v20 과 같은 ' '
    'maho_18.mjo::000960': [('maho_18.mjo::000960', ' ')],
}
for fid in ruby_slots:
    if fid in special:
        for tid, txt in special[fid]:
            if tid not in byid: raise SystemExit('missing ' + tid)
            put(tid, txt, '루비칸', R)
        continue
    ko = byid[fid]['ko']
    if ko == ' ': continue
    p = prev_field(fid)
    word = ko.strip()
    pv = cur(p)
    if pv.endswith(' ') or pv.endswith('　'):
        newp = pv + word + ' '
    else:
        newp = pv + ' ' + word
    # 뒤 칸이 공백으로 시작하면 앞 칸 끝 공백은 뺀다(겹 공백 방지)
    n = next_field(fid)
    if n and cur(n)[:1] in (' ', '　') and newp.endswith(' '): newp = newp[:-1]
    put(p, newp, '루비칸', R)
    put(fid, ' ', '루비칸', R)

# 2) 괄호
RB = '원문 「」 구조와 다름'
put('masa_16.mjo::000221', '「(저건, 시오미?)」', '괄호', '원문 「（…）」 속마음 대사의 「」가 빠짐(v20·주변 행과 같은 꼴로)')
put('masa_16.mjo::000243', '「(어쩜 저렇게 대담할 수가… 등잔 밑이 어둡다는 게 이런 건가?)」', '괄호', '원문 「（…）」 속마음 대사의 「」가 빠짐')
def unit_fields(uid): return [f for f in units[uid]['fields'] if f in byid]
f1, f2 = unit_fields('masa_16.mjo::u0105')[:2]
put(f1, '「(' + cur(f1)[1:] if cur(f1).startswith('(') else cur(f1), '괄호', '원문 「（…）」 속마음 대사의 「」가 빠짐')
put(f2, cur(f2).rstrip()[:-1] + ')」' if cur(f2).rstrip().endswith(')') else cur(f2), '괄호', '원문 「（…）」 속마음 대사의 「」가 빠짐')
f1, f2 = unit_fields('masa_16.mjo::u0108')[:2]
put(f1, '「(' + cur(f1)[1:] if cur(f1).startswith('(') else cur(f1), '괄호', '원문 「（…）」 속마음 대사의 「」가 빠짐')
put(f2, cur(f2).rstrip()[:-1] + ')」' if cur(f2).rstrip().endswith(')') else cur(f2), '괄호', '원문 「（…）」 속마음 대사의 「」가 빠짐')
for uid in ('last_gendai16.mjo::u0785', 'last_gendai16.mjo::u0788', 'last_gendai16.mjo::u0794', 'sina_17.mjo::u0575'):
    fl = unit_fields(uid)[-1]
    if not cur(fl).endswith('」'): put(fl, cur(fl) + '」', '괄호', '원문은 대사를 」로 닫는데 번역에 」가 빠짐')
for uid in ('maho_16.mjo::u0233', 'sina_19.mjo::u0070'):
    fl = unit_fields(uid)[-1]
    if cur(fl).endswith('」'): put(fl, cur(fl)[:-1] + ('.' if not cur(fl)[:-1].endswith(('…', '.', '?', '!')) else ''), '괄호', '원문은 다음 화면에서 같은 화자의 대사가 이어져 」로 닫지 않는데 번역이 닫아 버림(v20 과 같게)')
f1, f2 = unit_fields('maho_18.mjo::u0158')[:2]
put(f1, '「' + cur(f1), '괄호', '원문 대사 「」가 빠짐')
put(f2, '　' + cur(f2).lstrip(' 　') + '」', '괄호', '원문 대사 「」가 빠짐')

# 3) AG 가 서술·대사 속 『』 를 ‘’ 로 바꾼 칸 되돌림(v20·아르곤·같은 AG 의 다른 칸은 모두 『』)
for r in T['rows']:
    if r['model'] != 'antigravity-hybrid': continue
    ja, ko = r['ja'], cur(r['id'])
    if '『' in ja and '‘' in ko and '『' not in ko and ja.count('『') == ko.count('‘') and ja.count('』') == ko.count('’'):
        put(r['id'], ko.replace('‘', '『').replace('’', '』'), '『』', '원문 『』 를 ‘’ 로 바꿈(작품 전체는 『』 유지)')

# 4) 띄어쓰기
fs = unit_fields('maho_06.mjo::u0666')
for f in fs:
    if cur(f) == '이토록 체력과 기력을': put(f, '이토록 체력과 기력을 ', '띄어쓰기', '같은 줄에 이어지는 다음 칸(마모)과 붙어 「기력을마모」로 보임')

# 5) 용어: メール → 메일 (원문 외래어 유지 규칙, 같은 작품의 다른 칸 37곳은 메일)
for fid, a, b in [('00_レコンキスタ_start_2.mjo::013089', '문자 왔네', '메일 왔네'), ('00_レコンキスタ_start_2.mjo::013098', '문자 알림음', '메일 알림음'),
                  ('00_レコンキスタ_start_2.mjo::013219', '문자 본문', '메일 본문'), ('sina_12.mjo::000105', '문자 메시지가', '메일이'),
                  ('sina_12.mjo::000380', '문자에는', '메일에는')]:
    ko = cur(fid)
    if a in ko: put(fid, ko.replace(a, b), '용어', '원문 외래어 メール 는 메일로 살린다(사용자 규칙, 같은 작품 37곳 메일)')

# 6) 줄머리 전각 공백: 원문 이어지는 줄이 전각 공백으로 시작하면 번역도 전각 공백(v20 6,390곳·AG 전부 이 꼴)
n_indent = 0
for r in T['rows']:
    if r['role'] != 't' or r['model'] == 'source retained' or r['fixed']: continue
    ko = cur(r['id'])
    if r['ja'].startswith('　') and not ko.startswith('　') and ko.strip():
        put(r['id'], '　' + ko.lstrip(' '), '줄머리공백', '원문 줄머리 전각 공백(이어지는 대사 줄 맞춤)이 반각 공백이거나 빠짐')
        n_indent += 1

json.dump(list(fixes.values()), open(RV / 'work' / 'fixes_mech.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
c = collections.Counter((k, f['model'][:6]) for f in fixes.values() for k in set(f['kinds']))
print(c, 'fields', len(fixes))
for f in fixes.values():
    if '줄머리공백' not in f['kinds'] or len(f['kinds']) > 1:
        print(f['kinds'], f['id'], repr(f['old']), '->', repr(f['new']))
