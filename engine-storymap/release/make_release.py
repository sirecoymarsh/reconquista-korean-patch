"""레콘키스타 한국어 패치 배포 꾸러미 만들기 (Claude, 2026-11-21).

길티 크라운 PC 패치(Y:\\AI\\gclx-release-1121)와 같은 꼴: 게임 폴더에 압축을 풀고 한국어패치_설치.bat.
  - 바뀐 원본 5개(exe·scenario.arc·data.arc·fastdata.arc·movie\\Recon_OP800_H.mpg)는 xdelta3 차분과 되돌림 차분.
    원작 자료를 통째로 싣지 않는다. 원본 크기가 다르면 경고만 하고 시도한다(사용자 방침).
  - 새 파일(DLL·글꼴·이야기 지도·새 연표·사용 허락 문서)은 KoreanPatch\\files 에서 복사.
  - 4K 그림(hires*·hires-sprites.txt·prefetch.bin)은 「고화질 묶음」 따로. 없어도 DLL은 1배 그림을 키워 쓴다.
  - 개인·개발 파일은 싣지 않는다: savedata, storymap-read.bin, review-unlock.enabled(검수용 개방은 꺼진 채 시작),
    chronicle-original.enabled, *.ini(없으면 기본값: CG 4K·새 연표 모양), 로그, BUILD-IDENTITY, hires-manifest.
  - 설정 저장 자리(REG_LOCAL)는 ReconquistaKR(시제품 사본 이름 대신). 원작 키를 쓰면 원작의 글꼴 설정이 섞인다.
  - hires\\ PNG 는 JXL 이 없는 것만(JXL 이 있으면 DLL 이 JXL 을 읽는다).

python make_release.py --src <실행본> --dll <ReconquistaHD.dll> --ver 1.0 --out Y:\\AI\\reconquista-release\\<이름>
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
sys.path.insert(0, str(PROJ / 'tools'))
sys.dont_write_bytecode = True
import make_runtime as M  # noqa: E402

ORIG = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\research\disc')   # 디스크 원본 그대로
XDELTA = Path(r'P:\AI\demonbane-ps2-kr\release\pkg\tools\xdelta3.exe')                         # 3.2.0, Apache-2.0
JXL_SRC = PROJ / 'build' / 'src-libjxl' / 'libjxl'
FONT_LICENSE = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\builds\body-ui-20261023-v16-ui-rest\font\LICENSE.txt')
EXE = 'レコンキスタ.exe'
REG = 'ReconquistaKR'
# (게임 폴더 안 이름, 원본 경로, 차분 이름)
TARGETS = [(EXE, ORIG / 'bin' / EXE, 'exe'), ('scenario.arc', ORIG / 'scenario.arc', 'scenario'), ('data.arc', ORIG / 'data.arc', 'data'),
           ('fastdata.arc', ORIG / 'fastdata.arc', 'fastdata'), ('movie\\Recon_OP800_H.mpg', ORIG / 'movie' / 'Recon_OP800_H.mpg', 'movie')]
UNCHANGED = ['data1.arc', 'data2.arc', 'slowdata.arc', 'stream.arc', 'voice.arc']
HD_ITEMS = ['hires-jxl', 'hires-patch', 'hires-sprites.txt', 'prefetch.bin']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def xd(*args):
    r = subprocess.run([str(XDELTA), *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f'xdelta3 {args}: {r.stderr}')


def window(*paths):
    n = max(os.path.getsize(p) for p in paths)
    b = 1 << 20
    while b < n:
        b <<= 1
    return min(b, 1 << 30)


def cp949(text):
    return text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp949')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--dll', required=True)
    ap.add_argument('--ver', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--trial', action='store_true', help='시험 꾸러미: 읽어보기 맨 위에 배포 금지 표시')
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    work, dist = out / 'work', out / 'out'
    for d in (work / 'delta', work / 'patched', dist):
        d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    man = {'version': a.ver, 'made': time.strftime('%Y-%m-%d %H:%M'), 'source_runtime': str(src), 'registry_key': REG, 'targets': {}, 'files': {}}

    for name in UNCHANGED:      # 원작 그대로여야 하는 묶음: 실행본과 디스크가 같은지
        assert sha(src / name) == sha(ORIG / name), name

    fast = work / 'patched' / 'fastdata.arc'
    M.env_fastdata(src / 'fastdata.arc', fast, {'REG_LOCAL': REG})
    patched = {EXE: src / EXE, 'scenario.arc': src / 'scenario.arc', 'data.arc': src / 'data.arc', 'fastdata.arc': fast,
               'movie\\Recon_OP800_H.mpg': src / 'movie' / 'Recon_OP800_H.mpg'}
    for name, orig, tag in TARGETS:
        new = patched[name]
        fwd, back = work / 'delta' / f'{tag}.vcdiff', work / 'delta' / f'{tag}.restore.vcdiff'
        B = window(orig, new)
        xd('-e', '-9', '-f', '-B', B, '-s', orig, new, fwd)
        xd('-e', '-9', '-f', '-B', B, '-s', new, orig, back)
        chk = work / 'chk.tmp'                       # 두 방향 모두 풀어서 바이트 대조
        xd('-d', '-f', '-B', B, '-s', orig, fwd, chk)
        assert sha(chk) == sha(new), name
        xd('-d', '-f', '-B', B, '-s', new, back, chk)
        assert sha(chk) == sha(orig), name
        chk.unlink()
        man['targets'][name] = {'original_size': orig.stat().st_size, 'original_sha256': sha(orig), 'patched_size': new.stat().st_size,
                                'patched_sha256': sha(new), 'delta_bytes': fwd.stat().st_size, 'restore_bytes': back.stat().st_size, 'window': B}
        print(f'delta {name}: {fwd.stat().st_size/1e6:.1f} MB (+ restore {back.stat().st_size/1e6:.1f} MB)', flush=True)

    # 본 패치에 들어갈 새 파일: 게임 폴더 안 이름 -> 원본 경로
    files = {'ReconquistaHD.dll': Path(a.dll), 'chronicle-new.enabled': None, 'storymap.bin': src / 'storymap.bin'}
    for d in ('font', 'storymap', 'chronicle-new'):
        for p in sorted((src / d).rglob('*')):
            if p.is_file():
                files[str(p.relative_to(src))] = p
    files['font\\LICENSE.txt'] = None
    lic = {'licenses\\libjxl-LICENSE.txt': JXL_SRC / 'LICENSE', 'licenses\\libjxl-PATENTS.txt': JXL_SRC / 'PATENTS',
           'licenses\\brotli-LICENSE.txt': JXL_SRC / 'third_party' / 'brotli' / 'LICENSE',
           'licenses\\highway-LICENSE.txt': JXL_SRC / 'third_party' / 'highway' / 'LICENSE',
           'licenses\\highway-LICENSE-BSD3.txt': JXL_SRC / 'third_party' / 'highway' / 'LICENSE-BSD3',
           'licenses\\skcms-LICENSE.txt': JXL_SRC / 'third_party' / 'skcms' / 'LICENSE'}
    files.update(lic)
    font_license = ('Reconquista KR / Reconquista KR Serif 글꼴은 Adobe 의 Source Han Sans · Source Han Serif 를 고친 것입니다.\n'
                    'Copyright 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name \'Source\'.\n'
                    'Copyright 2017-2024 Adobe (http://www.adobe.com/), with Reserved Font Name \'Source\'.\n\n').encode('utf-8') + FONT_LICENSE.read_bytes()
    generated = {'chronicle-new.enabled': b'1\r\n', 'font\\LICENSE.txt': font_license}

    hd = {}
    pngs_needed = 0
    jxl = {p.stem for p in (src / 'hires-jxl').glob('*.jxl')}
    for p in sorted((src / 'hires').glob('*.png')):
        if p.stem not in jxl:
            hd['hires\\' + p.name] = p
            pngs_needed += 1
    for item in HD_ITEMS:
        p = src / item
        if p.is_dir():
            for q in sorted(p.rglob('*')):
                if q.is_file():
                    hd[str(q.relative_to(src))] = q
        else:
            hd[item] = p
    man['hd_png_kept'] = pngs_needed

    texts = make_texts(a.ver, a.trial, man)
    tag = f'레콘키스타_한국어패치_{a.ver}'
    main_zip, hd_zip = dist / f'{tag}_본패치.zip', dist / f'{tag}_고화질묶음.zip'
    with zipfile.ZipFile(main_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, data in texts.items():
            z.writestr(name, data)
        z.write(XDELTA, 'KoreanPatch/tools/xdelta3.exe')
        for f in sorted((work / 'delta').glob('*.vcdiff')):
            z.write(f, 'KoreanPatch/delta/' + f.name, compress_type=zipfile.ZIP_STORED)
        for name, p in files.items():
            arc = 'KoreanPatch/files/' + name.replace('\\', '/')
            if p is None:
                z.writestr(arc, generated[name])
                man['files'][name] = hashlib.sha256(generated[name]).hexdigest()
            else:
                z.write(p, arc)
                man['files'][name] = sha(p)
    with zipfile.ZipFile(hd_zip, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
        for name, p in hd.items():
            z.write(p, name.replace('\\', '/'))
    man['hd_files'] = len(hd)
    man['zips'] = {x.name: {'bytes': x.stat().st_size, 'sha256': sha(x)} for x in (main_zip, hd_zip)}
    man['seconds'] = round(time.time() - t0)
    (dist / 'manifest.json').write_text(json.dumps(man, ensure_ascii=False, indent=1), 'utf-8')
    print(json.dumps(man['zips'], ensure_ascii=False, indent=1))


def make_texts(ver, trial, man):
    t = {k: v['original_size'] for k, v in man['targets'].items()}
    size_checks = '\n'.join(f'if exist "{n}" for %%A in ("{n}") do if not "%%~zA"=="{s}" echo [주의] {n} 크기가 원본과 다릅니다(%%~zA 바이트). 다른 판본일 수 있지만 그대로 시도합니다.'
                            for n, s in t.items())
    applies = '\n'.join(f'call :apply "{n}" "{tag}"' for n, _, tag in TARGETS)
    install = f'''@echo off
setlocal EnableExtensions
chcp 949 >nul
cd /d "%~dp0"
set "P=%~dp0KoreanPatch"
set "XD=%P%\\tools\\xdelta3.exe"
set "BK=%P%\\backup"
set "S32=%SystemRoot%\\System32"
set "EXE={EXE}"
set "FAILED="
echo ============================================================
echo  레콘키스타 한국어 패치 {ver} 설치
echo ============================================================
echo.
if not exist "%EXE%" goto :notgame
if not exist "scenario.arc" goto :notgame
if not exist "data.arc" goto :notgame
if not exist "fastdata.arc" goto :notgame
if not exist "%XD%" goto :nopatch
"%S32%\\tasklist.exe" /fi "imagename eq %EXE%" 2>nul | "%S32%\\find.exe" /i "%EXE%" >nul
if not errorlevel 1 goto :running
if exist "%BK%\\installed.txt" goto :already
set "ACP="
for /f "tokens=3" %%A in ('%S32%\\reg.exe query "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Nls\\CodePage" /v ACP 2^>nul ^| %S32%\\find.exe "ACP"') do set "ACP=%%A"
if not "%ACP%"=="949" echo [주의] Windows 「유니코드를 지원하지 않는 프로그램용 언어」가 한국어가 아닙니다(%ACP%). 일부 창·메뉴 글자가 깨질 수 있습니다.
{size_checks}
if not exist "movie\\Recon_OP800_H.mpg" echo [주의] movie\\Recon_OP800_H.mpg 가 없습니다. 오프닝 영상은 한국어판으로 바뀌지 않습니다.
if not exist "%BK%" mkdir "%BK%"
if exist "%BK%\\applied.txt" del "%BK%\\applied.txt"

echo [1/2] 바뀌는 원본 파일 5개를 고치는 중... 몇 분 걸리고 빈 공간이 1GB 이상 필요합니다.
{applies}

echo [2/2] 한국어 파일을 넣는 중...
"%S32%\\robocopy.exe" "%P%\\files" "." /E /NJH /NJS /NFL /NDL /NP >nul
if errorlevel 8 set "FAILED=%FAILED% 한국어파일"

echo installed %DATE% %TIME%> "%BK%\\installed.txt"
echo.
if defined FAILED goto :partial
echo 설치를 마쳤습니다.
goto :done
:partial
echo [알림] 다음은 적용하지 못했습니다:%FAILED%
echo        원본 파일이 이 패치가 기대하는 판과 다를 수 있습니다. 나머지는 설치되었습니다.
:done
echo 평소처럼 %EXE% 로 실행하면 됩니다. 원래처럼 디스크(또는 디스크 이미지)가 드라이브에 있어야 합니다.
echo 고화질 묶음은 이 폴더에 압축을 풀면 됩니다. 되돌리려면 한국어패치_제거.bat 을 실행하세요.
pause
exit /b 0

:apply
if not exist "%~1" (
  set "FAILED=%FAILED% %~1"
  exit /b 0
)
"%XD%" -d -f -B 1073741824 -s "%~1" "%P%\\delta\\%~2.vcdiff" "%~1.kr_tmp"
if errorlevel 1 (
  if exist "%~1.kr_tmp" del "%~1.kr_tmp"
  set "FAILED=%FAILED% %~1"
  exit /b 0
)
move /y "%~1.kr_tmp" "%~1" >nul
echo %~1^|%~2>> "%BK%\\applied.txt"
exit /b 0

:notgame
echo [오류] 게임 폴더, 곧 %EXE% 와 scenario.arc 가 있는 폴더에 압축을 풀어서 실행해야 합니다.
echo        지금 위치: %CD%
pause
exit /b 1
:nopatch
echo [오류] KoreanPatch 폴더가 없습니다. 압축을 통째로 게임 폴더에 풀어 주세요.
pause
exit /b 1
:running
echo [오류] 게임이 켜져 있습니다. 게임을 끄고 다시 실행해 주세요.
pause
exit /b 1
:already
echo 이미 설치되어 있습니다. 다시 설치하려면 먼저 한국어패치_제거.bat 을 실행하세요.
pause
exit /b 1
'''
    remove = f'''@echo off
setlocal EnableExtensions
chcp 949 >nul
cd /d "%~dp0"
set "P=%~dp0KoreanPatch"
set "XD=%P%\\tools\\xdelta3.exe"
set "BK=%P%\\backup"
set "S32=%SystemRoot%\\System32"
set "EXE={EXE}"
set "FAILED="
echo ============================================================
echo  레콘키스타 한국어 패치 제거
echo ============================================================
echo.
if not exist "%BK%\\installed.txt" goto :notinstalled
"%S32%\\tasklist.exe" /fi "imagename eq %EXE%" 2>nul | "%S32%\\find.exe" /i "%EXE%" >nul
if not errorlevel 1 goto :running
if not "%RECON_KR_NOASK%"=="1" (
  "%S32%\\choice.exe" /c YN /m "한국어 패치와 고화질 묶음을 지우고 원래 게임으로 되돌릴까요"
  if errorlevel 2 exit /b 0
)

echo [1/2] 고친 원본 파일을 되돌리는 중... 몇 분 걸립니다.
if exist "%BK%\\applied.txt" for /f "usebackq tokens=1,2 delims=|" %%A in ("%BK%\\applied.txt") do call :restore "%%A" "%%B"

echo [2/2] 패치가 더한 파일을 지우는 중...
for %%F in (ReconquistaHD.dll storymap.bin chronicle-new.enabled hires-sprites.txt prefetch.bin hires-runtime.log storymap-read.bin storymap-read.tmp storymap-defer.off storymap-se-mute.flag review-unlock.enabled chronicle-original.enabled chronicle-look.ini cg-quality.ini cg-quality.ini.new) do if exist "%%F" del /q "%%F"
for %%D in (storymap chronicle-new hires hires-jxl hires-patch licenses) do if exist "%%D" rd /s /q "%%D"
for %%F in (ReconquistaKR.otf ReconquistaKRLarge.otf ReconquistaKRSerif.otf ReconquistaKRSerifLarge.otf LICENSE.txt) do if exist "font\\%%F" del /q "font\\%%F"
rd "font" 2>nul
for /d %%D in (savedata-review-*) do rd /s /q "%%D"
if exist "savedata" for %%F in ("savedata\\fc_Reconquista KR*.fcd") do del /q "%%~F" 2>nul
del "%BK%\\installed.txt"
if exist "%BK%\\applied.txt" del "%BK%\\applied.txt"
echo.
if defined FAILED goto :partial
echo 원래 게임으로 되돌렸습니다. 세이브는 그대로 두었습니다. 이제 KoreanPatch 폴더와 한국어패치 파일들은 지워도 됩니다.
goto :done
:partial
echo [알림] 다음은 되돌리지 못했습니다:%FAILED%
:done
pause
exit /b 0

:restore
"%XD%" -d -f -B 1073741824 -s "%~1" "%P%\\delta\\%~2.restore.vcdiff" "%~1.orig_tmp"
if errorlevel 1 (
  if exist "%~1.orig_tmp" del "%~1.orig_tmp"
  set "FAILED=%FAILED% %~1"
  exit /b 0
)
move /y "%~1.orig_tmp" "%~1" >nul
exit /b 0

:notinstalled
echo 설치 기록이 없습니다. 한국어패치_설치.bat 으로 설치한 폴더에서 실행해 주세요.
pause
exit /b 1
:running
echo [오류] 게임이 켜져 있습니다. 게임을 끄고 다시 실행해 주세요.
pause
exit /b 1
'''
    banner = '※ 시험 꾸러미입니다. 배포하지 마세요(번역·만든 사람 등은 아직 정해지지 않았습니다).\n\n' if trial else ''
    readme = f'''{banner}레콘키스타 한국어 패치 {ver}
================================================================

■ 대상
  코튼소프트 「レコンキスタ」(2007) PC판 정품을 설치한 폴더(실행 파일 이름: {EXE})용입니다.

■ 필요한 것
  - 원래처럼 게임 디스크(또는 디스크 이미지)가 드라이브에 들어 있어야 게임이 켜집니다.
  - Windows 설정의 「유니코드를 지원하지 않는 프로그램용 언어」가 한국어여야 일부 창·메뉴 글자가 깨지지 않습니다.
  - 설치 폴더에 쓸 수 있어야 합니다(세이브·설정 파일을 게임 폴더에 씁니다).

■ 설치
  1. 「본 패치」 압축을 게임 폴더({EXE} 가 있는 곳)에 그대로 풉니다.
  2. 한국어패치_설치.bat 을 두 번 눌러 실행합니다. 몇 분 걸리고 빈 공간이 1GB 이상 필요합니다.
     원본 파일이 예상과 다르면 [주의]가 뜨지만 그대로 진행합니다. 적용하지 못한 파일은 끝에 알려 줍니다.
  3. (선택) 「고화질 묶음」 압축을 같은 게임 폴더에 풉니다. 배경·CG·인물을 4배 해상도로 보여 줍니다.
     없어도 대사·메뉴 글자와 화면은 고해상도 모니터에 맞춰 커집니다.

■ 실행
  평소처럼 {EXE} 로 실행하면 됩니다.

■ 한국어판에서 더한 것
  - 고해상도: 4K 모니터까지 화면을 키우고 대사 글자를 4배로 또렷하게 그립니다.
    설정 화면의 「CG·메뉴」 단추로 4K 그림과 원래 그림을 바꿉니다.
  - 이야기 지도: F11(또는 창 메뉴 「이야기 지도」). 날짜·갈래별 장 지도, 대사 찾기, 읽은 곳 표시.
    「이 대사부터 다시보기」는 회상처럼 보고 그 장이 끝나면(또는 Esc) 원래 자리로 돌아옵니다.
    「여기서부터 본편으로」는 그 자리부터 게임을 이어 가며, 그때부터 게임을 끌 때까지 저장은
    savedata-review-… 폴더로 따로 갑니다(원래 세이브는 그대로).
  - 새 연표: 메뉴의 「연표 보기」를 빠르게 다시 그린 화면입니다. 연표 창 왼쪽 위 [새|원래] 스위치,
    설정 화면 맨 아래 단추, F8 로 원래 연표 모양으로 바꿀 수 있습니다.
  - 모든 콘텐츠 개방(검수용): Ctrl+F10 또는 창 메뉴 「검수용 모든 콘텐츠 개방」. 원래 달성·CG 기록은
    바꾸지 않으며, 다시 누르면 원래 해금 상태로 돌아갑니다.

■ 되돌리기
  한국어패치_제거.bat 을 실행하면 원래 게임으로 돌아갑니다(고화질 묶음도 함께 지웁니다. 세이브는 남깁니다).

■ 알아 둘 것
  - 설정은 레지스트리의 「ReconquistaKR」 자리에 따로 저장됩니다. 원래 게임 설정과 섞이지 않습니다.
  - 게임을 켤 때마다 게임 폴더에 hires-runtime.log(고해상도 층 기록)를 새로 씁니다.

■ 함께 넣은 공개 소프트웨어
  - Reconquista KR 글꼴(Source Han Sans · Source Han Serif 를 고친 것): SIL Open Font License 1.1 (font\\LICENSE.txt)
  - libjxl · brotli · highway · skcms: 각 라이선스(licenses 폴더)
  - xdelta3: Apache License 2.0 (KoreanPatch\\tools)

■ 만든 사람
  [만든 사람]
'''
    return {'한국어패치_설치.bat': cp949(install), '한국어패치_제거.bat': cp949(remove), '읽어보기.txt': '\ufeff'.encode('utf-8') + readme.replace('\n', '\r\n').encode('utf-8')}


if __name__ == '__main__':
    main()
