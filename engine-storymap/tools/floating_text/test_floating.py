"""The Korean floating lines in the running game (private desktop): for each target in test-targets.json, open the story
flow at the title, find the line just before the picture (찾기), replay from it, click on, and whenever one of the new
pictures is loaded (its 4x art in the log: 'asset <key> '), capture the frame the engine holds (perf capture WM_APP+80:
the 4x screen and the 1x screen). Captures go to <out>/<target>-<n>-{hd,base}.png (the 4x made 1600x1200); the BMPs
are removed at once (the P drive is nearly full).
python test_floating.py <runtime> <build out> <targets.json> <out> [target ...]
"""
import json
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, r'P:\AI\Codex\projects\reconquista_flowchart_20261024\tools')
import qa  # noqa: E402

VK = dict(F11=0x7a, RET=0x0d, DOWN=0x28)
WM_PERF = 0x8000 + 80


def boot(g):
    g.until(lambda: 'load call title' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    if not qa.u.IsWindowVisible(g.hwnd):
        qa.u.ShowWindow(g.hwnd, 4)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)


def capture(g, run, out, name, cid):
    n = g.count(f'quality_capture id={cid} ')
    g.post(g.hwnd, WM_PERF, 10 + cid, 0)
    g.until(lambda: g.count(f'quality_capture id={cid} ') > n, 30, 'capture')
    time.sleep(.5)
    for suffix in ('hd', 'base', 'output'):
        p = run / 'qa' / f'quality-{cid:02d}-{suffix}.bmp'
        if not p.exists():
            continue
        if suffix != 'output':
            im = Image.open(p).convert('RGB')
            if suffix == 'hd':
                im = im.resize((1600, 1200), Image.LANCZOS)
            im.save(out / f'{name}-{suffix}.png')
        p.unlink()


def one(run, keys, target, spec, out):
    g = qa.Game(run=run, extra_env={'RECON_PERF': '2'})
    result = {'target': target, 'order': spec['order'], 'query': spec['query'], 'seen': [], 'captures': []}
    try:
        boot(g)
        n = g.count('inflow opened')
        g.key(g.hwnd, VK['F11'])
        g.until(lambda: g.count('inflow opened') > n, 20, 'open')
        child = g.child()
        n = g.count('search_all')
        g.logical_click(child, 576, 20)                        # 대사 찾기: all chapters
        g.until(lambda: g.count('search_all') > n, 5, 'search all')
        time.sleep(.4)
        g.chars(g.edit(), spec['query'])
        g.until(lambda: f'search len={len(spec["query"])} ' in g.log(), 10, 'search typed')
        for _ in range(40):                                    # down to the found line
            n = g.count('item=')
            g.key(child, VK['DOWN'], 1, 0)
            g.until(lambda: g.count('item=') > n, 5, 'item step')
            tail = g.log().split('inflow item=')[-1][:80]
            if f'order={spec["order"]} ' in g.log().split('inflow item=')[-1].split('\n')[0] or f'order={spec["order"]}' in tail:
                break
        n = g.count('inflow jump order=')
        g.key(child, VK['RET'])                                # 이 대사부터 다시보기
        g.until(lambda: g.count('inflow jump order=') > n, 10, 'jump request')
        order = int(g.log().split('inflow jump order=')[-1].split()[0])
        result['jumped_order'] = order
        g.until(lambda: f'inflow arrived order={order} ' in g.log(), 150, 'arrival')
        mark = len(g.log())
        time.sleep(2)
        cid = 1
        for click in range(14):
            later = g.log()[mark:].lower()            # a picture as the engine loads it ('load call', the probe) or its 4x art
            new = [k for k in keys if (f'asset {k} ' in later or f'load call {keys[k].lower()}.rct' in later) and k not in result['seen']]
            for k in new:
                result['seen'].append(k)
                time.sleep(spec.get('wait', 1.0))              # the picture's own fade in
                name = f'{target}-{len(result["captures"]) + 1:02d}-{keys[k]}'
                capture(g, run, out, name, cid)
                result['captures'].append(name)
            if len(result['captures']) >= spec.get('max', 3):
                break
            g.logical_click(g.hwnd, 400, 300)
            time.sleep(1.4)
    except Exception as e:  # noqa: BLE001
        result['error'] = repr(e)[:300]
    finally:
        result['normal_exit'] = g.close_normally()
    return result


def main():
    run, build, targets, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    out.mkdir(parents=True, exist_ok=True)
    man = json.loads((build / 'manifest.json').read_text('utf-8'))
    keys = {p['key']: p['name'][:-4] for p in man['pictures']}
    spec = json.loads(targets.read_text('utf-8'))
    only = sys.argv[5:]
    results = []
    for t, s in spec.items():
        if only and t not in only:
            continue
        r = one(run, keys, t, s, out)
        print(json.dumps(r, ensure_ascii=False), flush=True)
        results.append(r)
    (out / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=1), 'utf-8')


if __name__ == '__main__':
    main()
