"""The opened-up 연표 now (the play copy's DLL) and as the original engine draws it (build_hdoff.py: the 4x layer off),
in turns, on runtime-chron (the user, 10-26: 「연표가 오리지날에서 안 버벅인다면 아예 연표만은 오리지날 그대로 가져오는
방안을 생각해야할지도몰라」 → 「개방한 연표의 원래 속도를 지금 재 봐. 그동안 게임은 안 켤게.」).
Numbers only (the opened-up 연표 is past the user's progress). It stops if the play copy is running.
python ab_chronicle_original.py [rounds] [now]   -> qa/chronicle-original-ab.json ('now': only the play copy's DLL, -now.json)
"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUN = HERE / 'runtime-chron'
NOW = HERE / 'native' / 'ReconquistaHD.dll'
OFF = HERE / 'build' / 'hdoff' / 'ReconquistaHD.dll'
rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 2
now_only = 'now' in sys.argv[2:]
if 'old' in sys.argv[2:]:   # 10-26 「근데 왜 느려진거야」: the play copy's DLL against last night's (A44E43F2), in turns
    OFF = HERE / 'build' / 'backups' / 'ReconquistaHD-A44E43F2.dll'
OTHER = 'a44e' if 'old' in sys.argv[2:] else 'original'
MODE = 'mode' in sys.argv[2:]   # 10-26: one DLL, 4K against the 연표 원래 화면 (chronicle-original.enabled), in turns
if MODE:
    OFF, OTHER = NOW, 'orig'
FLAG = RUN / 'chronicle-original.enabled'
CHILD = dict(os.environ, PYTHONIOENCODING='utf-8')   # 10-26: a log line's U+FFFD broke the child's cp949 print and lost the result


def play_running():
    r = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                        "Get-Process | Where-Object { $_.Path -and $_.Path -like '*runtime-play*' } | Measure-Object | ForEach-Object Count"],
                       capture_output=True, text=True)
    return r.stdout.strip() not in ('', '0')


def one(label, dll):
    shutil.copy2(dll, RUN / 'ReconquistaHD.dll')
    if MODE and label.startswith('orig'):
        FLAG.write_text('1\r\n')
    else:
        FLAG.unlink(missing_ok=True)
    r = subprocess.run([sys.executable, '-B', str(HERE / 'tools' / 'test_chronicle_unlocked.py'), label], capture_output=True,
                       text=True, encoding='utf-8', errors='replace', env=CHILD)
    out = r.stdout
    m = re.search(r'\{\s*"label".*\}', out, re.S)
    try:
        return json.loads(m.group(0)) if m else {'label': label, 'error': 'no result', 'tail': out[-600:] + r.stderr[-600:]}
    except ValueError:
        return {'label': label, 'error': 'bad json', 'tail': out[-600:]}


results = []
try:
    for i in range(1, rounds + 1):
        for label, dll in ((f'now{i}', NOW),) + (() if now_only else ((f'{OTHER}{i}', OFF),)):
            if play_running():
                results.append({'label': label, 'skipped': 'the play copy is running'})
                raise SystemExit
            res = one(label, dll)
            results.append(res)
            print(json.dumps({k: res.get(k) for k in ('label', 'idle', 'arrows', 'zoomed_idle', 'zoomed_arrows', 'error', 'normal_exit')}, ensure_ascii=False), flush=True)
            if MODE:
                log = (RUN / 'hires-runtime.log').read_text('utf-8', 'replace')
                res['original_lines'] = [l for l in log.splitlines() if l.startswith('original ')][-1:]
finally:
    shutil.copy2(NOW, RUN / 'ReconquistaHD.dll')           # the test copy goes back to the build's own DLL
    FLAG.unlink(missing_ok=True)
    (HERE / 'qa' / ('chronicle-original-ab-now.json' if now_only else f'chronicle-{OTHER}-ab.json')).write_text(
        json.dumps(results, ensure_ascii=False, indent=1) + '\n', 'utf-8')
