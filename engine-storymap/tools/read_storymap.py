"""Parse storymap.bin (RKSM0002) the same way the DLL does; print checks and samples."""
import struct
import sys
from pathlib import Path

P = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'build' / 'storymap.bin'


class R:
    def __init__(self, data):
        self.d, self.at = data, 0

    def i(self, n=1):
        v = struct.unpack_from('<' + 'i' * n, self.d, self.at)
        self.at += 4 * n
        return v if n > 1 else v[0]

    def t(self):
        n = self.i()
        s = self.d[self.at:self.at + n].decode('utf8')
        self.at += n
        return s


def parse(path=P):
    d = path.read_bytes()
    assert d[:8] == b'RKSM0002'
    r = R(d)
    r.at = 8
    a, b, c, e, s = r.i(5)
    roots = r.i(3)
    info = [r.i(4) for _ in range(a)]
    chapters = [dict(id=r.t(), group=r.t(), label=r.t()) for _ in range(b)]
    nodes = []
    for _ in range(c):
        ch, gid, kind, order = r.i(4)
        nodes.append(dict(chapter=ch, gid=gid, kind=kind, order=order, id=r.t(), label=r.t(), preview=r.t()))
    edges = [r.i(2) for _ in range(e)]
    sels = []
    for _ in range(s):
        g, default, n = r.i(3)
        sels.append((g, default, [r.i(2) for _ in range(n)]))
    ns = r.i()
    scenes = []
    for _ in range(ns):
        ch, first, count, pages, choices, views = r.i(6)
        scenes.append(dict(chapter=ch, first=first, count=count, pages=pages, choices=choices, views=views, bg=r.t(), snippet=r.t()))
    for n in nodes:
        n['scene'], n['value'], n['owner'] = r.i(3)
        n['speaker'], n['text'] = r.t(), r.t()
    for ch in chapters:
        ch['page'] = r.i()
        ch['rect'] = r.i(4)
        ch['day'], ch['scene0'], ch['scenes'] = r.i(3)
        ch['cell'], ch['extra'], ch['title'] = r.t(), r.t(), r.t()
    nd = r.i()
    deco = []
    for _ in range(nd):
        page, kind = r.i(2)
        rect = r.i(4)
        color = r.i()
        deco.append(dict(page=page, kind=kind, rect=rect, color=color, main=r.t(), sub=r.t()))
    assert d[r.at:r.at + 8] == b'RKSMEND!' and r.at + 8 == len(d), (r.at, len(d))
    return dict(roots=roots, info=info, chapters=chapters, nodes=nodes, edges=edges, sels=sels, scenes=scenes, deco=deco)


if __name__ == '__main__':
    x = parse()
    nodes, chapters, scenes = x['nodes'], x['chapters'], x['scenes']
    print('nodes', len(nodes), 'chapters', len(chapters), 'scenes', len(scenes), 'deco', len(x['deco']))
    for n in nodes[:4]:
        print(' ', n['order'], repr(n['speaker']), n['text'][:40])
    cid = {c['id']: i for i, c in enumerate(chapters)}
    s2 = [n for n in nodes if n['chapter'] == cid['00_レコンキスタ_start_2'] and n['kind'] in (1, 2, 3)]
    for n in s2[:12]:
        own = nodes[n['owner']]['label'] if n['owner'] >= 0 else '-'
        print('  kind', n['kind'], n['label'], '| value', n['value'], '| text', n['text'], '| owner', own)
    empty = [n for n in nodes if n['kind'] == 0 and not n['text']]
    print('pages without text', len(empty), [e['id'] for e in empty[:8]])
    print('speakers with （ or ＠ left:', sum(1 for n in nodes if any(m in n['speaker'] for m in '（＠／[［')))
    bad = [c['id'] for c in chapters if not (0 <= c['rect'][0] < c['rect'][2] <= 7600 and 0 <= c['rect'][1] < c['rect'][3] <= 5700)]
    print('bad rects', bad)
    sc = [s for s in scenes if s['chapter'] == cid['00_レコンキスタ_start_2']]
    print('start_2 scenes', len(sc), [s['bg'] for s in sc[30:40]])
    print('scene 35', sc[34]['snippet'], sc[34]['pages'], sc[34]['choices'])
