"""Codex's 4x of standing pictures as they arrive, checked the way sprite_build.py will take them (size, not black, the
name: nearer its own input than each other picture of its family), without building anything.
python sprite_check_ai.py <job.json> <ai dir> [--workers N]   -> one line a failure, then a count
"""
import functools, json, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sprite_build import ai_of
from sprite_prep import filled


def check(task, ai_dir):
    b, patches, keys = task
    full = {b['key']: filled(b['name'])}
    for v in patches:
        full[v['key']] = filled(v['name'])
    W, H = b['size_1x']
    bad, ok = [], 0
    for item in [b] + patches:
        if item['key'] not in keys:
            continue
        x, y, w, h = item.get('crop_1x') or [0, 0, W, H]
        own = np.ascontiguousarray(full[item['key']][y:y + h, x:x + w])
        others = {k: a[y:y + h, x:x + w] for k, a in full.items() if k != item['key'] and a.shape == full[b['key']].shape}
        try:
            ai_of(ai_dir, item['key'], own, others)
            ok += 1
        except Exception as e:
            bad.append(f"{item['name']}: {e}")
    return ok, bad


def main():
    job = json.loads(Path(sys.argv[1]).read_text('utf-8'))
    ai_dir = Path(sys.argv[2])
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 1
    have = {p.stem for p in ai_dir.glob('*.png')}
    tasks = []
    for b in job['bases']:
        patches = [v for v in job['patches'] if v['base_key'] == b['key']]
        keys = have & ({b['key']} | {v['key'] for v in patches})
        if keys:
            tasks.append((b, patches, keys))
    run = functools.partial(check, ai_dir=ai_dir)
    if workers > 1:
        with Pool(workers) as pool:
            res = list(pool.imap_unordered(run, tasks))
    else:
        res = [run(t) for t in tasks]
    ok = sum(r[0] for r in res)
    bad = [x for r in res for x in r[1]]
    for x in bad[:30]:
        print('bad', x)
    print(json.dumps({'files': len(have), 'checked': ok + len(bad), 'ok': ok, 'bad': len(bad)}))


if __name__ == '__main__':
    main()
