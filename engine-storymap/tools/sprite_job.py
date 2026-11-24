"""The full standing-picture job from sprite_index.py's sprite-work.json, in sample.json's layout (sprite_prep.py,
sprite_build.py): every base whole, every expression as a face crop, every distinct mask once.
An expression is upscaled as its box (the changed pixels and sprite_index.MARGIN) with CONTEXT more 1x pixels of
picture around it (crop_1x): the AI sees enough of the face around the box, and the build keeps only the box. A whole
expression would be about 15 times the pixels (the user, 10-26: 「이런 다른 여유있는 드라이브에 작업물을 만들고 P에서
합치는게 좋겠군」: work files go to a roomy drive, only the game's files to P:).
python sprite_job.py <sprite-work.json> <job.json> [--only <base name> ...]   (--only: a test job of some families)
"""
import argparse, json
from pathlib import Path

CONTEXT = 24    # 1x pixels of picture around an expression's box in its crop (96 at 4x)


def crop_of(box, size):
    x, y, w, h = box
    W, H = size
    x0, y0 = max(0, x - CONTEXT), max(0, y - CONTEXT)
    return [x0, y0, min(W, x + w + CONTEXT) - x0, min(H, y + h + CONTEXT) - y0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('job')
    ap.add_argument('--only', nargs='*', default=None)
    args = ap.parse_args()
    work = json.loads(Path(args.work).read_text('utf-8'))
    if args.only:
        want = {n.lower() for n in args.only}
        work = [w for w in work if w['base'].lower() in want]
    bases, patches, masks, missing = [], [], {}, []
    for w in work:
        if w['size'] is None:            # a base the archive does not hold: its expressions cannot be built
            missing.append(w['base'])
            continue
        W, H = w['size']
        bases.append({'name': w['base'], 'key': w['key'], 'size_1x': [W, H], 'size_4k': [W * 4, H * 4], 'file': w['key'] + '.png'})
        mask_of = {m['name'][:-5] + '.rct': m['file_key'] for m in w['masks']}
        for v in w['variants']:
            x, y, bw, bh = v['box']
            patches.append({'name': v['name'], 'key': v['key'], 'base': w['base'], 'base_key': w['key'], 'box_1x': v['box'],
                            'box_4k': [x * 4, y * 4, bw * 4, bh * 4], 'crop_1x': crop_of(v['box'], w['size']),
                            'file': v['key'] + '.png', 'mask_file_key': mask_of.get(v['name'])})
        for m in w['masks']:
            e = masks.setdefault(m['file_key'], {'name': m['file_name'], 'key': m['file_key'], 'size_1x': [W, H],
                                                 'size_4k': [W * 4, H * 4], 'file': m['file_key'] + '.png', 'used_by': []})
            e['used_by'].append(m['name'][:-5] + '.rct')
    job = {'what': 'standing-picture 4K: bases whole, expressions as face crops, distinct masks (Claude, 10-26)', 'scale': 4,
           'margin_1x': 8, 'context_1x': CONTEXT, 'bases': bases, 'patches': patches, 'masks': list(masks.values()),
           'bases_missing': missing}
    Path(args.job).write_text(json.dumps(job, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    px_whole = sum(b['size_1x'][0] * b['size_1x'][1] for b in bases)
    px_crop = sum(p['crop_1x'][2] * p['crop_1x'][3] for p in patches)
    full = {b['key']: b['size_1x'][0] * b['size_1x'][1] for b in bases}
    px_expr_whole = sum(full[p['base_key']] for p in patches)
    print(json.dumps({'bases': len(bases), 'expressions': len(patches), 'masks': len(masks), 'bases_missing': len(missing),
                      'mpx_bases': round(px_whole / 1e6, 1), 'mpx_crops': round(px_crop / 1e6, 1),
                      'mpx_if_expressions_whole': round(px_expr_whole / 1e6, 1)}))


if __name__ == '__main__':
    main()
