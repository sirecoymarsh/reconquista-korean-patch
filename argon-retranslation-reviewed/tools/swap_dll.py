# 지도 DLL 바꿔 넣기: 다른 세션이 고친 DLL(글꼴 이름이 원래 d00b8d76 그대로인 것)에 이 판의 글꼴 이름을 같은 길이로 바꿔 build-20261121 에 넣는다
# 사용: python -I tools\swap_dll.py <원본 DLL> <기대 sha256 앞 8자리>
# 그 뒤 make_test_runtime.py(시험 사본 폴더를 먼저 지움)·make_qa_runtime.py 를 다시 돌린다
import sys, json, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
RV = Path(__file__).resolve().parent.parent; OUT = RV / 'build-20261121'
src = Path(sys.argv[1]); want = sys.argv[2].lower()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(src).startswith(want), ('원본 DLL 해시가 다름', sha(src))
newmap = json.loads((OUT / 'font-map.json').read_text('utf-8'))['mapping']
rev = hashlib.sha256(json.dumps(newmap, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:8]
proof = json.loads((OUT / 'build-proof.json').read_text('utf-8'))
fn = proof.get('font_names') or proof.get('fontnames') or {}
REN = {'Reconquista KR Serif d00b8d76': f'Reconquista KR Serif {rev}', 'Reconquista KR d00b8d76': f'Reconquista KR {rev}',
       'Reconquista KR Large Serif1': 'Reconquista KR Large Serif3', 'Reconquista KR Large1': 'Reconquista KR Large3'}
d = src.read_bytes(); n = 0
for a, z in REN.items():
    assert len(a) == len(z)
    for x, y in [(a, z), (a.replace(' ', '|'), z.replace(' ', '|'))]:
        xb, yb = x.encode('utf-16-le'), y.encode('utf-16-le'); n += d.count(xb); d = d.replace(xb, yb)
assert n == 2, n                                            # 지도·연표 그리기용 이름 두 곳
assert not any(a.encode('utf-16-le') in d for a in REN)
old = OUT / 'ReconquistaHD.dll'; prev = sha(old)
old.write_bytes(d)
proof['dll'] = {'source': str(src), 'source_sha256': sha(src), 'sha256': sha(old), 'utf16_names_renamed': n, 'replaced_sha256': prev}
(OUT / 'build-proof.json').write_text(json.dumps(proof, ensure_ascii=False, indent=1), 'utf-8')
print(json.dumps(proof['dll'], ensure_ascii=False, indent=1))
