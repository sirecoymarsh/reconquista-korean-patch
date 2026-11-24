# 시험 사본 조립(실행하지 않음): runtime-final-20261028 을 바탕으로 새 번역 빌드를 얹은 폴더를 만든다.
#  - 게임이 절대 쓰지 않는 큰 자료(아카이브·exe·고화질 그림·영상)는 하드 링크
#  - 새 빌드 파일(scenario.arc·storymap.bin·font 4벌)과 게임이 쓰는 파일(savedata·ini·DLL·로그 등)은 진짜 사본
#  - 새 폴더에서만 만든다(이미 있으면 멈춤) → 하드 링크된 원본에 쓰는 일이 없다
import os, sys, shutil, json, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
R = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024'); FINAL = R / 'runtime-final-20261028'
HERE = Path(__file__).resolve().parent; RVD = HERE.parent; BUILD = RVD / 'build-20261121'
DST = Path(sys.argv[1]) if len(sys.argv) > 1 else RVD / 'runtime-argon-test-20261121'
SAVES = BUILD / 'savedata-play-converted'
assert not DST.exists(), f'이미 있음: {DST}'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
LINK_FILES = {'data.arc', 'data1.arc', 'data2.arc', 'slowdata.arc', 'voice.arc', 'stream.arc', 'レコンキスタ.exe'}
LINK_DIRS = {'hires', 'hires-jxl', 'hires-patch', 'movie'}
FROM_BUILD = {'scenario.arc', 'storymap.bin', 'fastdata.arc', 'ReconquistaHD.dll'}
DST.mkdir(parents=True)
rep = {'base': str(FINAL), 'build': str(BUILD), 'linked': 0, 'copied': [], 'from_build': {}, 'savedata': str(SAVES)}
for p in FINAL.iterdir():
    q = DST / p.name
    if p.is_dir():
        if p.name in LINK_DIRS:
            for f in p.rglob('*'):
                t = q / f.relative_to(p)
                if f.is_dir(): t.mkdir(parents=True, exist_ok=True); continue
                t.parent.mkdir(parents=True, exist_ok=True); os.link(f, t); rep['linked'] += 1
        elif p.name == 'font':
            q.mkdir()
            for f in p.iterdir():
                src = BUILD / 'font' / f.name if (BUILD / 'font' / f.name).exists() else f
                shutil.copy2(src, q / f.name); rep['from_build' if src != f else 'copied'] and None
                if src != f: rep['from_build']['font/' + f.name] = sha(q / f.name)
                else: rep['copied'].append('font/' + f.name)
        elif p.name == 'savedata':
            shutil.copytree(SAVES, q); rep['copied'].append('savedata (converted copy of runtime-play savedata)')
        else:
            shutil.copytree(p, q); rep['copied'].append(p.name + '/')
    elif p.name in LINK_FILES:
        os.link(p, q); rep['linked'] += 1
    elif p.name in FROM_BUILD:
        shutil.copy2(BUILD / p.name, q); rep['from_build'][p.name] = sha(q)
    else:
        shutil.copy2(p, q); rep['copied'].append(p.name)
# 하드 링크가 실제로 같은 파일인지, 바뀐 파일은 진짜 사본인지
for n in LINK_FILES:
    if (DST / n).exists(): assert os.path.samefile(DST / n, FINAL / n)
for n in list(FROM_BUILD) + ['font/' + x for x in os.listdir(BUILD / 'font')]:
    assert not os.path.samefile(DST / n, BUILD / n) and sha(DST / n) == sha(BUILD / n)
assert not os.path.samefile(DST / 'savedata', FINAL / 'savedata')
(DST / 'ARGON-TEST-IDENTITY.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), 'utf-8')
print(json.dumps({k: (v if k != 'copied' else len(v)) for k, v in rep.items()}, ensure_ascii=False, indent=1))
