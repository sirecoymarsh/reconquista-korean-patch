# 일상 기본 낱말(KEEP_NATIVE)을 번역이 어떻게 옮겼는지 센다 → work/native_count.json (사용자 결정용)
import json, sys, re, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from common import *
from loan_scan import KEEP_NATIVE, KW, held
LOAN = {'ベッド':['베드'],'クラス':['클래스'],'ドア':['도어'],'コンビニ':['콘비니','컨비니언스'],'ポケット':['포켓'],'ネックレス':['네크리스','네클리스','넥클리스'],
 'スカート':['스커트'],'チャイム':['차임'],'フロア':['플로어'],'ランチ':['런치'],'ガラス':['글라스','글래스'],'プレゼント':['프레젠트','프레젠'],'タオル':['타월','타올'],
 'バスタオル':['타월','타올'],'パンツ':['팬티','팬츠','바지'],'デジカメ':['디카','디지털카메라','디지털 카메라','카메라'],'トイレ':['토일렛'],'フォロー':['팔로','폴로','커버'],
 'キッチン':['키친'],'ドアノブ':['도어노브','노브'],'ロック':['록','락'],'ハンカチ':['행커치프','손수건'],'バッグ':['백'],'スコップ':['스코프','스콥'],'コップ':['컵'],
 'アパート':['아파트'],'ズボン':['바지'],'クローゼット':['클로짓','클로젯'],'ビール':['비어'],'ナンバープレート':['넘버플레이트','넘버 플레이트'],'フローリング':['플로어링','플로링'],
 'キッチンカウンター':['키친'],'ナンパ':['헌팅','작업'],'エプロン':['에이프런','에이프론'],'リハビリ':['리허빌리테이션','재활'],'ノブ':['노브'],'パンティ':['팬티'],
 'リビング':['리빙'],'パソコン':['컴퓨터','PC','피시'],'デパート':['디파트먼트'],'ダンボール':['골판지','박스','상자'],'フェラ':['펠라'],'ペンキ':['페인트'],'ハンドル':['핸들'],
 'ボディタオル':['타월','타올'],'セックス':['섹스'],'ボロアパート':['아파트'],'ブラ':['브라'],'ブラジャー':['브래지어','브라'],'ペニス':['페니스'],'ストッキング':['스타킹'],
 'ビニール':['비닐'],'ブルマ':['블루머','블루마'],'ブルマー':['블루머','블루마'],'ノートパソコン':['노트북','컴퓨터','PC'],'ゴム':['고무']}
# 위에서 외래어 꼴이 이미 한국어 외래어(컵·팬티·컴퓨터·고무 등)인 것은 「외래어 꼴」로 센다
if __name__ == '__main__':
    F = [json.loads(l) for l in open(RV / '검수확정_번역필드.jsonl', encoding='utf-8')]
    byunit = collections.defaultdict(list)
    for o in F: byunit[o['unit']].append(o)
    loan = collections.Counter(); nat = collections.defaultdict(list)
    for o in F:
        if o['translator_model'] == 'source retained' or o['role'] != 't' or held(o): continue
        uko = ''.join(x['ko'] for x in byunit[o['unit']])
        for w in dict.fromkeys(x.strip('・') for x in KW.findall(o['ja'])):
            if w not in KEEP_NATIVE: continue
            if any(f in uko for f in LOAN.get(w, [])): loan[w] += 1
            else: nat[w].append(o['id'])
    json.dump({'native': nat, 'loan': loan}, open(RV / 'work' / 'native_count.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('우리말', sum(len(v) for v in nat.values()), '외래어 꼴', sum(loan.values()))
    print(' '.join(f'{w}:{len(v)}/{len(v) + loan[w]}' for w, v in sorted(nat.items(), key=lambda x: -len(x[1]))))
