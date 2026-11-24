# 배포판(10-28 최신판) 숨은 시험 사본 — 11-22 「전부 해결해」: 고친 대본(scenario_postfix)·고친 DLL(movie.inc)을 최신판에 넣기 전에 시험한다.
# 게임이 읽기만 하는 큰 자료는 runtime-final 하드 링크, 게임이 쓰는 파일(세이브·읽음 표시·설정·기록)은 진짜 사본 → 원본 최신판은 안 바뀐다.
# 소리는 fastdata 설정(음량 0·음악 끔)과 설정 키 따로(ReconquistaRelQA20261122). make_qa_runtime.py 와 같은 방식. 게임은 띄우지 않는다.
# 사용: python -I tools\make_rel_qa_runtime.py <새 scenario.arc> <새 ReconquistaHD.dll>
import os, sys, shutil, json, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8'); sys.dont_write_bytecode = True
R = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024'); S = R / 'runtime-final-20261028'
HERE = Path(__file__).resolve().parent; RVD = HERE.parent; D = RVD / 'runtime-release-qa-20261122'
sys.path.insert(0, str(R / 'tools')); import make_runtime as M
NEW_ARC, NEW_DLL = Path(sys.argv[1]), Path(sys.argv[2])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
if D.exists(): shutil.rmtree(D)          # 내 사본(하드 링크는 링크만 지워진다)
WRITE_TOP = {'scenario.arc', 'fastdata.arc', 'ReconquistaHD.dll', 'storymap-read.bin', 'hires-runtime.log'}
for root, dirs, files in os.walk(S):
    rel = Path(root).relative_to(S)
    dirs[:] = [x for x in dirs if x not in ('qa', 'savedata') and not x.startswith('savedata-review')]
    (D / rel).mkdir(parents=True, exist_ok=True)
    for f in files:
        p = Path(root) / f; q = D / rel / f
        if p.suffix.lower() in ('.log', '.bmp') or (rel == Path('.') and f in WRITE_TOP): continue
        if rel == Path('.') and p.stat().st_size < 5 * 2**20: shutil.copy2(p, q)      # 맨 위 작은 파일(설정·표·신원)은 진짜 사본
        else: os.link(p, q)
os.link(NEW_ARC, D / 'scenario.arc'); shutil.copy2(NEW_DLL, D / 'ReconquistaHD.dll')
if (S / 'storymap-read.bin').exists(): shutil.copy2(S / 'storymap-read.bin', D / 'storymap-read.bin')
shutil.copytree(S / 'savedata', D / 'savedata')
M.env_fastdata(S / 'fastdata.arc', D / 'fastdata.arc', {'REG_LOCAL': 'ReconquistaRelQA20261122', 'MUSICVOL': '0', 'SOUNDVOL': '0', 'VOICEVOL': '0', 'ISPLAYMUSIC': '0'})
(D / 'storymap-se-mute.flag').write_text('QA', 'utf-8')
ident = {'base': str(S), 'scenario': sha(D / 'scenario.arc'), 'dll': sha(D / 'ReconquistaHD.dll'), 'storymap': sha(D / 'storymap.bin'),
         'fastdata_qa': sha(D / 'fastdata.arc'), 'note': 'release QA copy 11-22; large assets hard-linked to runtime-final, written files are real copies'}
(D / 'REL-QA-IDENTITY.json').write_text(json.dumps(ident, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps({k: (v[:8] if len(str(v)) == 64 else v) for k, v in ident.items()}, ensure_ascii=False))
