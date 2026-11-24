# 숨은 시험용 사본: 대본은 새 빌드 그대로(소리 명령을 빼면 명령 길이가 바뀌어 세이브 시험이 안 됨),
# 소리는 fastdata 설정(음량 0·음악 끔)과 설정 키 따로(ReconquistaArgonQA20261121)로 끈다. 저장은 변환한 사본.
# 다른 세션의 make_compat_runtimes.py 와 같은 방식. 게임은 띄우지 않는다.
import os, sys, shutil, json
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8'); sys.dont_write_bytecode = True
R = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024'); S = R / 'runtime-final-20261028'
HERE = Path(__file__).resolve().parent; RVD = HERE.parent; B = RVD / 'build-20261121'
D = RVD / 'runtime-argon-qa-20261121'
sys.path.insert(0, str(R / 'tools')); import make_runtime as M
if D.exists(): shutil.rmtree(D)          # 이 폴더는 내 사본(하드 링크는 링크만 지워진다)
SMALL = {'.json', '.ini', '.bin', '.flag', '.enabled', '.txt', '.md'}
SKIP = {'storymap-read.bin', 'scenario.arc', 'fastdata.arc', 'review-unlock.enabled', 'storymap.bin', 'ReconquistaHD.dll'}
for root, dirs, files in os.walk(S):
    rel = Path(root).relative_to(S)
    dirs[:] = [x for x in dirs if x not in ('qa', 'savedata', 'font') and not x.startswith('savedata-review')]
    (D / rel).mkdir(parents=True, exist_ok=True)
    for f in files:
        p = Path(root) / f; q = D / rel / f
        if p.suffix.lower() in ('.log', '.bmp') or (rel == Path('.') and f in SKIP): continue
        if p.suffix.lower() in SMALL and rel == Path('.'): shutil.copy2(p, q)
        else: os.link(p, q)
os.link(B / 'scenario.arc', D / 'scenario.arc'); os.link(B / 'storymap.bin', D / 'storymap.bin'); shutil.copy2(B / 'ReconquistaHD.dll', D / 'ReconquistaHD.dll')
(D / 'font').mkdir()
for f in (S / 'font').iterdir():
    os.link(B / 'font' / f.name if (B / 'font' / f.name).exists() else f, D / 'font' / f.name)
shutil.copytree(B / 'savedata-play-converted', D / 'savedata')
(D / 'savedata' / 'save-conversion.json').unlink()
M.env_fastdata(B / 'fastdata.arc', D / 'fastdata.arc', {'REG_LOCAL': 'ReconquistaArgonQA20261121', 'MUSICVOL': '0', 'SOUNDVOL': '0', 'VOICEVOL': '0', 'ISPLAYMUSIC': '0'})
(D / 'storymap-se-mute.flag').write_text('QA', 'utf-8')
proof = {'run': str(D), 'scenario': M.sha(D / 'scenario.arc'), 'storymap': M.sha(D / 'storymap.bin'), 'fonts': {f.name: M.sha(f) for f in (D / 'font').glob('*.otf')},
         'registry': 'ReconquistaArgonQA20261121', 'volumes': 0, 'savedata': 'converted copy of runtime-play savedata (no fc_*.fcd)'}
(D / 'QA-IDENTITY.json').write_text(json.dumps(proof, ensure_ascii=False, indent=1), 'utf-8'); print(json.dumps(proof, ensure_ascii=False, indent=1))
