"""Standing pictures for 4K as a base and face patches (the user, 10-25: 「인물 그림 4K를 바탕+얼굴 조각 방식으로 하자. 너는
DLL을, 코덱스는 확대를 맡고 견본 몇 장부터.」).

The game keeps 12,084 of its 12,669 standing pictures as TC01 differences on a base: only the changed pixels (a face,
median 0.9% of the picture), the rest marked "take the base". Their masks are whole files, but 12,893 masks hold 978
pictures. So the 4K set is: each base whole, each variant as the 4K of its changed box (with a margin the patch blends
into the base, done by Codex), each distinct mask once. This writes what the DLL reads and what Codex works from:

python sprite_index.py <prefix> [<prefix> ...] [--out DIR]   e.g. momi_2a_  (a picture family)
-> DIR/sprite-index.txt   one line a picture, for the DLL (hires-sprites.txt in the runtime):
     P <variant key> <base key> <x> <y> <w> <h>   a variant: its base's 4K, then the patch (x,y,w,h: the 1x box)
     M <mask key> <file key>                      a mask: the 4K of <file key> (the first picture with those pixels)
   DIR/sprite-work.json   for Codex: per base, its variants (name, key, box) and masks (name, key, file key)
Keys are the 4K layer's (CRC32 of the lower-case name with its extension). Read-only on the game's archives.
"""
import argparse, hashlib, json, re, sys, zlib
from pathlib import Path
import numpy as np
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista-ko\tools')
from inspect_majiro import Arc
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista-ko\ui-opening-ending\tools')
from raster_codec import raw_image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_runtime as M

MARGIN = 8   # 1x pixels around the changed box: the patch's blend into the base


def key(name):
    return zlib.crc32(name.lower().encode('cp932')) & 0xffffffff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('prefix', nargs='+')
    ap.add_argument('--out', default=str(Path(__file__).resolve().parents[1] / 'build' / 'sprites'))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    arc = Arc(M.GAME / 'slowdata.arc')
    ent = {e['name'].lower(): e for e in arc.entries}
    names = sorted(n for n in ent if n.endswith('.rct') and any(n.startswith(p.lower()) for p in args.prefix))
    f = arc.path.open('rb')

    def blob(n):
        e = ent[n]
        f.seek(e['offset'])
        return f.read(e['size'])
    lines, work, masks = [], {}, {}
    for n in names:
        b = blob(n)
        img, head, _ = raw_image(b)
        h, w = img.shape[:2]
        if b[4:8] == b'TC01':
            base = head[22:].rstrip(b'\0').decode('cp932').lower()
            if not base.endswith('.rct'):
                base += '.rct'
            changed = ~np.all(img == [255, 0, 0], axis=2)
            ys, xs = np.nonzero(changed)
            if not len(ys):
                x0 = y0 = 0
                x1 = y1 = 1
            else:
                x0, x1 = max(0, xs.min() - MARGIN), min(w, xs.max() + 1 + MARGIN)
                y0, y1 = max(0, ys.min() - MARGIN), min(h, ys.max() + 1 + MARGIN)
            lines.append(f'P {key(n):08x} {key(base):08x} {x0} {y0} {x1 - x0} {y1 - y0}')
            work.setdefault(base, {'base': base, 'key': f'{key(base):08x}', 'size': None, 'variants': [], 'masks': []})
            work[base]['variants'].append({'name': n, 'key': f'{key(n):08x}', 'box': [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
                                           'changed_px': int(changed.sum())})
        else:
            work.setdefault(n, {'base': n, 'key': f'{key(n):08x}', 'size': None, 'variants': [], 'masks': []})
            work[n]['size'] = [w, h]
        m = n[:-4] + '_.rc8'
        if m in ent:
            digest = hashlib.sha1(blob(m)[8:]).hexdigest()
            first = masks.setdefault(digest, m)
            lines.append(f'M {key(m):08x} {key(first):08x}')
            owner = base if b[4:8] == b'TC01' else n
            work[owner]['masks'].append({'name': m, 'key': f'{key(m):08x}', 'file_key': f'{key(first):08x}', 'file_name': first})
    for w_ in work.values():
        if w_['size'] is None and w_['base'] in ent:
            img, _, _ = raw_image(blob(w_['base']))
            w_['size'] = [int(img.shape[1]), int(img.shape[0])]
    (out / 'sprite-index.txt').write_text('\n'.join(lines) + '\n', 'ascii')
    (out / 'sprite-work.json').write_text(json.dumps(list(work.values()), ensure_ascii=False, indent=1), 'utf-8')
    print(json.dumps({'pictures': len(names), 'bases': len(work), 'variants': sum(len(x['variants']) for x in work.values()),
                      'mask_files': sum(len(x['masks']) for x in work.values()), 'distinct_masks': len(masks), 'out': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
