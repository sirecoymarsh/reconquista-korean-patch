"""배포 꾸러미를 원본 디스크 파일로 만든 가짜 게임 폴더에 설치·실행·제거해 본다 (Claude, 2026-11-21).

python sim_install.py <꾸러미 out 폴더> <가짜 게임 폴더>
  1. 원본 디스크 파일로 게임 폴더(바뀌는 6개는 복사, 나머지 묶음은 하드 링크, 드라이브가 다르면 복사).
  2. 본 패치 압축 풀기 → 한국어패치_설치.bat(입력 없이) → 바뀐 파일·새 파일 해시가 manifest 와 같은지, 개인 파일이 없는지.
  3. 다시 설치 → 「이미 설치」로 멈추는지.
  4. 무음 실행(고화질 묶음 없이 / 있이): fastdata 만 잠시 시험용(설정 키 따로·음량 0)으로 바꿔 숨은 데스크톱에서
     타이틀 → 처음부터 → 첫 대사 → F11 지도 열고 닫기 → 정상 종료. 끝나면 배포 fastdata 로 되돌린다.
  5. 한국어패치_제거.bat → 6개가 원본 해시로 돌아오고 더한 파일이 없어졌는지, 세이브는 남았는지.
"""
import hashlib, json, os, shutil, subprocess, sys, time, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
sys.path.insert(0, str(PROJ / 'tools'))
sys.dont_write_bytecode = True
import make_runtime as M  # noqa: E402
import qa  # noqa: E402
from test_hitch import WM_APP  # noqa: E402
from PIL import Image  # noqa: E402

ORIG = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\research\disc')
EXE = 'レコンキスタ.exe'
PATCHED = {EXE: ORIG / 'bin' / EXE, 'scenario.arc': ORIG / 'scenario.arc', 'data.arc': ORIG / 'data.arc', 'data1.arc': ORIG / 'data1.arc',
           'fastdata.arc': ORIG / 'fastdata.arc', 'movie\\Recon_OP800_H.mpg': ORIG / 'movie' / 'Recon_OP800_H.mpg'}
UNCHANGED = ['data2.arc', 'slowdata.arc', 'stream.arc', 'voice.arc']
PERSONAL = ['savedata', 'storymap-read.bin', 'review-unlock.enabled', 'cg-quality.ini', 'chronicle-look.ini',
            'hires-runtime.log', 'BUILD-IDENTITY.json', 'hires-manifest.json', 'storymap-se-mute.flag']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def bat(game, name, env=None):
    r = subprocess.run(['cmd', '/c', str(Path(game) / name)], cwd=game, stdin=subprocess.DEVNULL, capture_output=True, env={**os.environ, **(env or {})})
    return r.returncode, (r.stdout + r.stderr).decode('cp949', 'replace')


def smoke(game, label, out):
    """muted, hidden: title -> 처음부터 -> 구하라 -> 3 lines -> F11 map -> Esc -> normal exit"""
    rel = game / 'fastdata.arc'
    keep = game / 'fastdata.release.arc'
    os.replace(rel, keep)
    M.env_fastdata(keep, rel, {'REG_LOCAL': 'ReconquistaReleaseSim' + label, 'MUSICVOL': '0', 'SOUNDVOL': '0', 'VOICEVOL': '0', 'ISPLAYMUSIC': '0'})
    (game / 'storymap-se-mute.flag').write_text('sim', 'utf-8')
    res = {'label': label}
    shots = game / 'qa'
    shots.mkdir(exist_ok=True)
    g = qa.Game(run=game, extra_env={'RECON_PERF': '2', 'RECON_FLOW_PROBE': None})
    n = [0]

    def cap(name):
        n[0] += 1
        k = n[0]
        g.post(g.hwnd, WM_APP + 80, 10 + k, 0)
        g.until(lambda: (shots / f'quality-{k:02d}-output.bmp').exists(), 20, name)
        time.sleep(.4)
        Image.open(shots / f'quality-{k:02d}-output.bmp').convert('RGB').resize((960, 540)).save(out / f'sim-{label}-{k:02d}-{name}.png')

    def click(x, y, wait):
        g.move(g.hwnd, x, y)
        time.sleep(.3)
        g.logical_click(g.hwnd, x, y)
        time.sleep(wait)
    try:
        g.until(lambda: 'asset 1de0628c ' in g.log() or 'load call title1_off' in g.log(), 90, 'title')
        g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
        time.sleep(2)
        if not qa.u.IsWindowVisible(g.hwnd):
            qa.u.ShowWindow(g.hwnd, 4)
        for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
            qa.u.SendMessageW(g.hwnd, m, a, 0)
        time.sleep(1)
        cap('title')
        click(638, 345, 6)
        click(398, 140, 8)
        for _ in range(3):
            g.logical_click(g.hwnd, 400, 300)
            time.sleep(2.5)
        cap('reading')
        nopen = g.count('inflow opened')
        g.key(g.hwnd, 0x7a)
        g.until(lambda: g.count('inflow opened') > nopen, 20, 'map')
        time.sleep(1)
        g.key(g.child(), 0x1b)
        g.until(lambda: 'inflow closed' in g.log(), 10, 'map closed')
        time.sleep(1.5)
        # the text box's 연표 tab: the game's 연표 opens and the new one is put over it (prepared then, if not at the title)
        t1 = time.time()
        while time.time() - t1 < 60 and 'chron_proto replace opened' not in g.log():
            g.logical_click(g.hwnd, 400, 520)
            time.sleep(1.2)
            g.move(g.hwnd, 770, 510)
            time.sleep(.4)
            g.logical_click(g.hwnd, 770, 510)
            end = time.time() + 2.5
            while time.time() < end and 'chron_proto replace opened' not in g.log():
                time.sleep(.1)
        g.until(lambda: 'chron_proto show' in g.log(), 15, 'new 연표 shows')
        time.sleep(1.5)
        proto = qa.u.FindWindowExW(g.hwnd, None, 'ReconChronicleProto', None)
        g.key(proto, 0x1b)
        g.until(lambda: 'chronicle_open=0' in g.log() or 'replace closed' in g.log(), 15, '연표 closed')
        time.sleep(1)
        log = g.log()
        res['chronicle'] = {'opened': 'chron_proto replace opened' in log, 'shown': [l[:110] for l in log.splitlines() if l.startswith('chron_proto show')][:1],
                            'closed': 'chronicle_open=0' in log or 'replace closed' in log, 'draw_errors': log.count('draw_error')}
        res.update(dialogs=[x['title'] for x in g.windows() if x['class'] == '#32770'],
                   hd_assets=sum(1 for l in log.splitlines() if l.startswith('asset ') and '-> 3200x2400' in l),
                   jxl_loads=log.count('src=jxl'), jxl_errors=log.count('jxl_error'), asset_errors=log.lower().count('asset error'),
                   chron_proto=[l[:90] for l in log.splitlines() if l.startswith('chron_proto open')][:1],
                   text4k=[l[:120] for l in log.splitlines() if l.startswith('text4k ') and 'fcd_skip' not in l][-1:],
                   map_opened=g.count('inflow opened'), title_key=('1de0628c' if 'asset 1de0628c ' in log else 'other'))
        res['ok'] = True
    except Exception as e:  # noqa: BLE001
        res['ok'] = False
        res['error'] = repr(e)[:400]
    finally:
        res['normal_exit'] = g.close_normally()
        os.replace(keep, rel)
        (game / 'storymap-se-mute.flag').unlink(missing_ok=True)
        shutil.rmtree(shots, ignore_errors=True)
    return res


def main():
    import psutil
    assert not [q for q in psutil.process_iter(['name']) if q.info['name'] == EXE], 'another Reconquista is running'
    pkg, game = Path(sys.argv[1]), Path(sys.argv[2])
    man = json.loads((pkg / 'manifest.json').read_text('utf-8'))
    out = game.parent / 'sim-evidence'
    out.mkdir(parents=True, exist_ok=True)
    res = {'steps': []}
    if game.exists():
        shutil.rmtree(game)
    (game / 'movie').mkdir(parents=True)
    for name, p in PATCHED.items():
        shutil.copy2(p, game / name)
    for name in UNCHANGED:
        try:
            os.link(ORIG / name, game / name)
        except OSError:                     # the disc files are on another drive
            shutil.copy2(ORIG / name, game / name)
    (game / 'savedata').mkdir()
    (game / 'savedata' / 'majiro_0101.sav').write_bytes(b'sim save, must survive')
    orig_hash = {n: sha(game / n) for n in PATCHED}

    zips = sorted(pkg.glob('*.zip'))
    main_zip = next(z for z in zips if z.name.endswith('_본패치.zip'))
    hd_zip = next(z for z in zips if z.name.endswith('_고화질묶음.zip'))
    with zipfile.ZipFile(main_zip) as z:
        z.extractall(game)
    rc, text = bat(game, '한국어패치_설치.bat')
    res['install'] = {'rc': rc, 'tail': text.strip().splitlines()[-6:], 'notices': [l for l in text.splitlines() if l.startswith(('[주의]', '[오류]', '[알림]')) or '구문이 잘못' in l or '인식되지 않' in l or 'not recognized' in l]}
    bad = {n: v['patched_sha256'][:12] for n, v in man['targets'].items() if sha(game / n) != v['patched_sha256']}
    missing = [n for n, h in man['files'].items() if not (game / n).exists() or sha(game / n) != h]
    personal = [n for n in PERSONAL if (game / n).exists() and n != 'savedata']
    res['after_install'] = {'patched_mismatch': bad, 'files_missing_or_wrong': missing[:10], 'personal_files_present': personal,
                            'save_kept': (game / 'savedata' / 'majiro_0101.sav').read_bytes() == b'sim save, must survive'}
    rc2, text2 = bat(game, '한국어패치_설치.bat')
    res['reinstall'] = {'rc': rc2, 'says_already': '이미 설치' in text2}
    print(json.dumps({k: res[k] for k in ('install', 'after_install', 'reinstall')}, ensure_ascii=False), flush=True)

    if '--no-smoke' not in sys.argv:
        res['smoke_main_only'] = smoke(game, 'main', out)
        print('main only', json.dumps(res['smoke_main_only'], ensure_ascii=False), flush=True)
    with zipfile.ZipFile(hd_zip) as z:
        z.extractall(game)
    time.sleep(3)
    if '--no-smoke' not in sys.argv:
        res['smoke_with_hd'] = smoke(game, 'hd', out)
        print('with hd', json.dumps(res['smoke_with_hd'], ensure_ascii=False), flush=True)

    rc3, text3 = bat(game, '한국어패치_제거.bat', {'RECON_KR_NOASK': '1'})
    left = [p.name for p in game.iterdir() if p.name not in set(UNCHANGED) | {EXE, 'scenario.arc', 'data.arc', 'fastdata.arc', 'movie', 'savedata',
                                                                             'KoreanPatch', '한국어패치_설치.bat', '한국어패치_제거.bat', '읽어보기.txt'}]
    res['uninstall'] = {'rc': rc3, 'tail': text3.strip().splitlines()[-3:], 'notices': [l for l in text3.splitlines() if l.startswith(('[주의]', '[오류]', '[알림]')) or '구문이 잘못' in l or '인식되지 않' in l], 'restored_mismatch': [n for n in PATCHED if sha(game / n) != orig_hash[n]],
                        'left_over': left, 'save_kept': (game / 'savedata' / 'majiro_0101.sav').exists(),
                        'savedata_files': sorted(p.name for p in (game / 'savedata').iterdir())}
    print('uninstall', json.dumps(res['uninstall'], ensure_ascii=False), flush=True)
    (out / 'sim-result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), 'utf-8')


if __name__ == '__main__':
    main()
