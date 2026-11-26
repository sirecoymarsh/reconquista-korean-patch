"""Put build.py's pictures into a runtime folder: its data.arc / data1.arc made again from the source runtime's (the
untouched ones build.py read) with the new payloads (every other entry byte for byte as it was, the entry order kept), so
an earlier install leaves nothing behind; and the new 4x art as hires-jxl\\<key>.jxl (newer than the old PNG, so the DLL
takes it; the release's HD bundle ships hires-jxl). Files that are hard links shared with other copies are replaced by
new files, never written through.
python install.py <build out> <source runtime> <runtime>
"""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assets as A  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def replace_file(path, data):
    """a new file at path (a hard link there is dropped, not written through). A file of our own (one link: an earlier
    install) goes first, so the full drive holds only one copy of it at a time."""
    if path.exists() and os.stat(path).st_nlink == 1:
        path.unlink()
    tmp = path.with_name(path.name + '.new')
    tmp.write_bytes(data)
    if path.exists():
        path.unlink()
    os.replace(tmp, path)


def main():
    out, src, run = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    report = {'runtime': str(run), 'source': str(src), 'archives': {}, 'art': []}
    for arc_dir in sorted((out / 'payloads').iterdir()):
        arc = A.core.Arc(src / arc_dir.name)
        raw = arc.path.read_bytes()
        before = {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in arc.entries}
        payload = dict(before)
        changed = {}
        for p in sorted(arc_dir.iterdir()):
            assert p.name in payload, (arc_dir.name, p.name)
            payload[p.name] = p.read_bytes()
            changed[p.name] = sha(payload[p.name])
        data = arc.rebuild(payload)
        del raw
        replace_file(run / arc_dir.name, data)
        check = A.core.Arc(run / arc_dir.name)
        raw = check.path.read_bytes()
        after = {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in check.entries}
        assert list(after) == list(before), 'entry order'
        for n in after:
            want = payload[n]
            assert after[n] == want, n
        report['archives'][arc_dir.name] = {'entries': len(after), 'changed': len(changed), 'sha256': sha(raw)}
        print(arc_dir.name, len(changed), 'entries changed of', len(after), flush=True)
    for p in sorted((out / 'hires-jxl').glob('*.jxl')):
        dst = run / 'hires-jxl' / p.name
        replace_file(dst, p.read_bytes())
        png = run / 'hires' / (p.stem + '.png')
        assert not png.exists() or png.stat().st_mtime < dst.stat().st_mtime, png     # the DLL must take the .jxl
        report['art'].append(p.name)
    print(len(report['art']), '4x art files')
    (out / 'installed.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), 'utf-8')


if __name__ == '__main__':
    main()
