"""python test_console_keys.py <runtime>: the text box keys on a private desktop (11-25).

Gets to a text wait (story map jump to 도입부 2, as test_text_speed), then: S twice (the next empty slots, as the save
menu numbers them: majiro_<p*100+1+i>.sav), Q (majiro_9999.sav), A (auto on, the game stays up), a click (auto off).
The runtime's savedata is put back as it was at the end. Result: qa/console-keys.json.
"""
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa  # noqa: E402

VK = dict(F11=0x7a, RET=0x0d, RIGHT=0x27, UP=0x26, END=0x23, S=0x53, Q=0x51, A=0x41)
run = Path(sys.argv[1])
saves = run / 'savedata'
keep = qa.QA / 'console-keys-savedata'
if keep.exists():
    shutil.rmtree(keep)
shutil.copytree(saves, keep)
(run / 'storymap-read.bin').unlink(missing_ok=True)
result = {'steps': []}


def files():
    return {p.name for p in saves.glob('majiro_*.sav')}


g = qa.Game(run=run)
try:
    g.until(lambda: 'asset 1de0628c ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: 'inflow opened' in g.log(), 20, 'open')
    child = g.child()
    g.key(child, VK['RIGHT'])
    g.until(lambda: 'cursor=' in g.log(), 10, 'cursor move')
    g.key(child, VK['RET'])
    g.until(lambda: 'page=2 chapter=3' in g.log(), 10, 'chapter page')
    n = g.count('inflow snapshot')
    g.key(child, VK['RIGHT'], 34, .03)
    g.until(lambda: g.count('inflow snapshot') >= n + 34, 30, 'scene steps')
    time.sleep(.5)
    g.key(child, VK['END'])
    time.sleep(.5)
    g.key(child, VK['UP'])
    time.sleep(.4)
    g.story_jump(child)
    g.until(lambda: 'inflow jump order=' in g.log(), 10, 'jump request')
    order = int(g.log().split('inflow jump order=')[-1].split()[0])
    g.until(lambda: f'inflow arrived order={order} ' in g.log(), 120, 'arrival')
    time.sleep(3)
    result['before'] = sorted(files())
    for k, want in (('S', None), ('S', None), ('Q', 'majiro_9999.sav')):
        before = files()
        n = g.count('console_key ')
        g.key(g.hwnd, VK[k])
        g.until(lambda: g.count('console_key ') > n, 10, 'key ' + k)
        g.until(lambda: files() - before or (want and (saves / want).stat().st_mtime > time.time() - 5), 10, 'save ' + k)
        new = sorted(files() - before)
        result['steps'].append({'key': k, 'log': g.log().split('console_key ')[-1].split('\n')[0], 'new': new})
        time.sleep(1.5)
        g.logical_click(g.hwnd, 400, 300)                     # the message box
        time.sleep(1.5)
        assert g.poll() is None, 'game ended after ' + k
    n = g.count('console_key ')
    g.key(g.hwnd, VK['A'])
    g.until(lambda: g.count('console_key ') > n, 10, 'key A')
    result['steps'].append({'key': 'A', 'log': g.log().split('console_key ')[-1].split('\n')[0]})
    time.sleep(6)
    assert g.poll() is None, 'game ended in auto'
    g.logical_click(g.hwnd, 400, 300)
    time.sleep(2)
    assert g.poll() is None, 'game ended after auto off'
    result['ok'] = True
except Exception as e:  # noqa: BLE001
    result['error'] = repr(e)
finally:
    result['alive_at_end'] = g.poll() is None
    result['normal_exit'] = g.close_normally()
    result['after'] = sorted(files())
    shutil.rmtree(saves)
    shutil.copytree(keep, saves)
    qa.dump('console-keys', result)
    print(json.dumps(result, ensure_ascii=False, indent=1))
