# 반입 빌드 5단계: 글꼴 이름 바꾸기 (build_patch.py 뒤에 돌린다)
# 까닭: 엔진이 font\*.otf 를 공개로 올리고 내리지 않아, 같은 이름의 옛 글꼴이 윈도 세션에 남으면 새 글꼴 대신 잡힌다
#       (11-21 숨은 시험: 새 글자 자리에 한자). 코덱스 설계대로 대응표 해시를 이름에 넣어 이름을 바꾼다.
# 같은 길이 이름으로 바꾸므로 대본 바이트 수·명령 위치·세이브 오프셋은 그대로다.
import sys, json, hashlib, struct, re
from pathlib import Path
sys.dont_write_bytecode = True; sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); from common import *
C = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타'); R = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024')
sys.path.insert(0, str(C / 'tools'))
import build_trial as b
from mjotool.crypt import crypt32
from inspect_majiro import Arc
from fontTools.ttLib import TTFont
FINAL = R / 'runtime-final-20261028'; OUT = RV / 'build-20261121'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
newmap = json.loads((OUT / 'font-map.json').read_text('utf-8'))['mapping']
rev = hashlib.sha256(json.dumps(newmap, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:8]
REN = {'Reconquista KR Serif d00b8d76': f'Reconquista KR Serif {rev}', 'Reconquista KR d00b8d76': f'Reconquista KR {rev}',
       'Reconquista KR Large Serif1': 'Reconquista KR Large Serif3', 'Reconquista KR Large1': 'Reconquista KR Large3'}
# 큰 글자 이름은 대응표가 바뀔 때마다 숫자를 올린다(2 = 11-21 첫 반입판 91자, 3 = 외래어 반영판). 옛 이름이 세션에 남아 있어도 새 글꼴이 잡히게
for a, z in REN.items(): assert len(a) == len(z)
def ren_text(s):
    for a, z in REN.items():
        s = s.replace(a, z); s = s.replace(a.replace(' ', ''), z.replace(' ', '')); s = s.replace(a.replace(' ', '|'), z.replace(' ', '|'))
    return s
def ren_bytes(d, enc):
    n = 0
    for a, z in REN.items():
        for x, y in [(a, z), (a.replace(' ', '|'), z.replace(' ', '|'))]:
            xb, yb = x.encode(enc), y.encode(enc); n += d.count(xb); d = d.replace(xb, yb)
    return d, n
proof = {'revision': rev, 'renames': REN}
def payload(p):
    a = Arc(p); raw = Path(p).read_bytes(); return a, {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}

# 1) 글꼴 4벌: name 표와 CFF 이름
fp = []
for f in sorted((OUT / 'font').glob('*.otf')):
    font = TTFont(f, recalcTimestamp=False)
    cmap_before = dict(font.getBestCmap()); glyphs_before = len(font['CFF '].cff.topDictIndex[0].CharStrings)
    for r in font['name'].names:
        s = r.toUnicode(); t = ren_text(s)
        if t != s: r.string = t.encode(r.getEncoding(), errors='strict')
    cff = font['CFF '].cff; cff.fontNames = [ren_text(x) for x in cff.fontNames]
    top = cff.topDictIndex[0]
    for k in ('FamilyName', 'FullName', 'FontName'):
        if hasattr(top, k) and isinstance(getattr(top, k), str): setattr(top, k, ren_text(getattr(top, k)))
    tmp = f.with_suffix('.tmp'); font.save(tmp); tmp.replace(f)
    chk = TTFont(f, recalcTimestamp=False)
    fam = chk['name'].getDebugName(1)
    assert fam in REN.values(), (f.name, fam)
    assert not any(a in r.toUnicode() for r in chk['name'].names for a in REN), f.name
    assert dict(chk.getBestCmap()) == cmap_before, f.name                                  # 글자 대응은 그대로
    assert len(chk['CFF '].cff.topDictIndex[0].CharStrings) == glyphs_before, f.name
    fp.append({'font': f.name, 'family': fam, 'sha256': sha(f)})
proof['fonts'] = fp

# 2) 대본: 암호를 풀어 같은 길이 문자열만 바꾸고 다시 감싼다
arc_a, pl = payload(OUT / 'scenario.arc'); sp = []
for n, d in list(pl.items()):
    if not n.endswith('.mjo'): continue
    count = struct.unpack_from('<I', d, 24)[0]; off = 32 + count * 8
    enc = d[:10] == b'MajiroObjX'
    code = crypt32(d[off:]) if enc else d[off:]
    new, k = ren_bytes(code, 'cp932')
    if not k: continue
    d2 = d[:off] + (crypt32(new) if enc else new); assert len(d2) == len(d)
    try:
        s0 = b.decode(d)[0].instructions; s1 = b.decode(d2)[0].instructions
        assert [x.offset for x in s0] == [x.offset for x in s1] and [x.opcode.mnemonic for x in s0] == [x.opcode.mnemonic for x in s1]
        diffs = [(x.string, y.string) for x, y in zip(s0, s1) if x.string != y.string]
        assert all(ren_text(a) == bb for a, bb in diffs), n
        how = 'decoded'
    except UnicodeDecodeError:
        how = 'cp949 script: raw same-length byte replace'
    pl[n] = d2; sp.append({'entry': n, 'strings_renamed': k, 'check': how})
blob = arc_a.rebuild(pl); (OUT / 'scenario.arc').write_bytes(blob); _, back = payload(OUT / 'scenario.arc'); assert back == pl
proof['scenario'] = {'sha256': sha(OUT / 'scenario.arc'), 'entries': sp}

# 3) fastdata.arc: 설정 파일·majiro.env FC_NAME
fa, fd = payload(FINAL / 'fastdata.arc'); fpz = []
for n, d in list(fd.items()):
    d2, k = ren_bytes(d, 'cp932')
    if k: fd[n] = d2; fpz.append({'entry': n, 'renamed': k})
(OUT / 'fastdata.arc').write_bytes(fa.rebuild(fd)); _, back = payload(OUT / 'fastdata.arc'); assert back == fd
proof['fastdata'] = {'sha256': sha(OUT / 'fastdata.arc'), 'entries': fpz}

# 4) 지도 DLL: UTF-16 이름(지도·연표 그리기용)
dll = (FINAL / 'ReconquistaHD.dll').read_bytes(); dll2, k = ren_bytes(dll, 'utf-16-le'); assert len(dll2) == len(dll)
(OUT / 'ReconquistaHD.dll').write_bytes(dll2); proof['dll'] = {'source_sha256': sha(FINAL / 'ReconquistaHD.dll'), 'sha256': sha(OUT / 'ReconquistaHD.dll'), 'utf16_names_renamed': k}

bp = json.loads((OUT / 'build-proof.json').read_text('utf-8')); bp['font_rename'] = proof
bp['scenario']['sha256_after_font_rename'] = proof['scenario']['sha256']
(OUT / 'build-proof.json').write_text(json.dumps(bp, ensure_ascii=False, indent=1), 'utf-8')
print(json.dumps(proof, ensure_ascii=False, indent=1))
