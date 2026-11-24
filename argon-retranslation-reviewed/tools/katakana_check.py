# 가타카나 외래어가 번역에 한글 외래어로 남았는지 대략 재기
# 가타카나 → 한글 음절 근사 변환 후, 번역(KO)에 앞 2~3음절이 (모음 ㅜ/ㅡ·ㅗ/ㅓ 를 같게 보고) 있는지 본다
import json, sys, re, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from common import *
BASE_K = {'ア':'아','イ':'이','ウ':'우','エ':'에','オ':'오','カ':'카','キ':'키','ク':'쿠','ケ':'케','コ':'코','ガ':'가','ギ':'기','グ':'구','ゲ':'게','ゴ':'고',
 'サ':'사','シ':'시','ス':'스','セ':'세','ソ':'소','ザ':'자','ジ':'지','ズ':'즈','ゼ':'제','ゾ':'조','タ':'타','チ':'치','ツ':'츠','テ':'테','ト':'토',
 'ダ':'다','ヂ':'지','ヅ':'즈','デ':'데','ド':'도','ナ':'나','ニ':'니','ヌ':'누','ネ':'네','ノ':'노','ハ':'하','ヒ':'히','フ':'후','ヘ':'헤','ホ':'호',
 'バ':'바','ビ':'비','ブ':'부','ベ':'베','ボ':'보','パ':'파','ピ':'피','プ':'푸','ペ':'페','ポ':'포','マ':'마','ミ':'미','ム':'무','メ':'메','モ':'모',
 'ヤ':'야','ユ':'유','ヨ':'요','ラ':'라','リ':'리','ル':'루','レ':'레','ロ':'로','ワ':'와','ヲ':'오','ヴ':'부','ァ':'아','ィ':'이','ゥ':'우','ェ':'에','ォ':'오'}
YO = {'ャ':'ㅑ','ュ':'ㅠ','ョ':'ㅛ'}
SMALLV = {'ァ':'ㅏ','ィ':'ㅣ','ゥ':'ㅜ','ェ':'ㅔ','ォ':'ㅗ'}
CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'; JUNG = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'; JONG = ' ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ'
def split(h):
    o = ord(h) - 0xac00; return CHO[o // 588], JUNG[(o % 588) // 28], JONG[o % 28]
def join(c, v, j=' '):
    return chr(0xac00 + CHO.index(c) * 588 + JUNG.index(v) * 28 + JONG.index(j))
def translit(w):
    out = []
    for ch in w:
        if ch in YO and out:
            c, v, j = split(out[-1]); out[-1] = join(c, YO[ch]); continue
        if ch in SMALLV and out:
            c, v, j = split(out[-1]); nv = SMALLV[ch]
            if c == 'ㅇ' and v == 'ㅜ': nv = {'ㅣ': 'ㅟ', 'ㅔ': 'ㅞ', 'ㅗ': 'ㅝ', 'ㅏ': 'ㅘ'}.get(nv, nv)
            out[-1] = join(c, nv); continue
        if ch == 'ン' and out: c, v, j = split(out[-1]); out[-1] = join(c, v, 'ㄴ'); continue
        if ch == 'ッ' and out: c, v, j = split(out[-1]); out[-1] = join(c, v, 'ㅅ'); continue
        if ch == 'ー' or ch == '・': continue
        if ch in BASE_K: out.append(BASE_K[ch])
    return ''.join(out)
VN = {'ㅜ': 'U', 'ㅡ': 'U', 'ㅗ': 'O', 'ㅓ': 'O', 'ㅔ': 'E', 'ㅐ': 'E', 'ㅖ': 'E', 'ㅒ': 'E'}
def skel(s, keep_final=False):
    r = []
    for ch in s:
        if HANGUL.match(ch):
            c, v, j = split(ch); c = {'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ'}.get(c, c); r.append(c + VN.get(v, v))
    return r
def present(word, ko):
    t = skel(translit(word)); k = skel(ko)
    if len(t) < 2: return True
    n = 2 if len(t) <= 3 else 3
    pat = t[:n]
    for i in range(len(k) - n + 1):
        if k[i:i + n] == pat: return True
    # 첫 음절만 같고 둘째가 ㅡ 탈락 등으로 다른 꼴: 앞 1 + 뒤 1 비교
    for i in range(len(k) - 1):
        if k[i] == t[0] and k[i + 1][:1] == t[1][:1]: return True
    return False

if __name__ == '__main__':
    F = [json.loads(l) for l in open(RV / '검수확정_번역필드.jsonl', encoding='utf-8')]
    byunit = collections.defaultdict(list)
    for o in F: byunit[o['unit']].append(o)
    KW = re.compile(r'[ァ-ヺー]{2,}')
    miss = collections.defaultdict(list); have = collections.Counter()
    for o in F:
        if o['translator_model'] == 'source retained': continue
        uko = ''.join(x['ko'] for x in byunit[o['unit']])
        for w in set(KW.findall(o['ja'])):
            if present(w, uko): have[w] += 1
            else: miss[w].append(o['id'])
    rows = sorted(((w, len(ids), have[w]) for w, ids in miss.items()), key=lambda x: -x[1])
    json.dump({w: ids for w, ids in miss.items()}, open(RV / 'work' / 'katakana_missing.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('words with misses', len(rows), 'miss occurrences', sum(r[1] for r in rows))
    print(' '.join(f'{w}:{m}/{m + h}' for w, m, h in rows))
