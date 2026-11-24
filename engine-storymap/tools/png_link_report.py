"""Where the 4x PNGs live and what deleting each place would free. Read-only: nothing is moved or deleted.

Every runtime-play/hires/*.png is one file with many names (NTFS hard links). For each of them the names are listed
with FindFirstFileNameW, grouped by folder; the folder that holds a hires directory is one "place". For a place, "freed
alone" counts the files whose every name is inside that place (a file still named elsewhere frees nothing). Junctions
and other reparse points are not followed.
python png_link_report.py   -> qa/png_links.json and a printed table
"""
import ctypes
import json
import os
import stat
from collections import defaultdict
from ctypes import wintypes as w
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
k = ctypes.WinDLL('kernel32', use_last_error=True)
k.FindFirstFileNameW.argtypes = [w.LPCWSTR, w.DWORD, ctypes.POINTER(w.DWORD), w.LPWSTR]
k.FindFirstFileNameW.restype = w.HANDLE
k.FindNextFileNameW.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD), w.LPWSTR]
k.FindNextFileNameW.restype = w.BOOL
k.FindClose.argtypes = [w.HANDLE]
INVALID = w.HANDLE(-1).value
names_cache = {}


def names(path, st):
    """All names of the file, as full paths on its drive (cached by file id)."""
    key = (st.st_dev, st.st_ino)
    if key in names_cache:
        return names_cache[key]
    drive = os.path.splitdrive(os.path.abspath(path))[0]
    buf = ctypes.create_unicode_buffer(32768)
    n = w.DWORD(32768)
    h = k.FindFirstFileNameW(str(path), 0, ctypes.byref(n), buf)
    out = []
    if h != INVALID:
        out.append(drive + buf.value)
        while True:
            n = w.DWORD(32768)
            if not k.FindNextFileNameW(h, ctypes.byref(n), buf):
                break
            out.append(drive + buf.value)
        k.FindClose(h)
    names_cache[key] = out
    return out


def walk(root):
    """Files under root without entering junctions or symlinks."""
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            try:
                st = e.stat(follow_symlinks=False)
                if st.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    continue
                if stat.S_ISDIR(st.st_mode):
                    stack.append(e.path)
                else:
                    yield e.path, os.stat(e.path, follow_symlinks=False)   # DirEntry.stat leaves st_ino/st_nlink 0 on Windows
            except OSError:
                continue


def inside(p, root):
    p, root = os.path.normcase(p), os.path.normcase(root.rstrip('\\')) + '\\'
    return p.startswith(root)


pngs = sorted((HERE / 'runtime-play' / 'hires').glob('*.png'))
dirs = defaultdict(set)   # folder holding links -> file ids
size_of = {}
for p in pngs:
    st = p.stat()
    size_of[(st.st_dev, st.st_ino)] = st.st_size
    for n in names(p, st):
        dirs[os.path.dirname(n)].add((st.st_dev, st.st_ino))
places = {}
for d, ids in dirs.items():
    place = os.path.dirname(d) if os.path.basename(d).lower().startswith('hires') else d
    places.setdefault(place, {'link_dirs': [], 'pngs': set()})
    places[place]['link_dirs'].append(d)
    places[place]['pngs'] |= ids
rows = []
for place, info in places.items():
    total = freed = 0
    seen = set()
    for path, st in walk(place):
        fid = (st.st_dev, st.st_ino)
        if fid in seen:
            continue
        seen.add(fid)
        total += st.st_size
        if st.st_nlink <= 1 or all(inside(n, place) for n in names(path, st)):
            freed += st.st_size
    png_bytes = sum(size_of[i] for i in info['pngs'])
    rows.append({'place': place, 'mine': inside(place, str(HERE)), 'png_links': len(info['pngs']), 'png_gb': round(png_bytes / 2**30, 2),
                 'folder_gb': round(total / 2**30, 2), 'freed_alone_gb': round(freed / 2**30, 2), 'link_dirs': sorted(info['link_dirs'])})
rows.sort(key=lambda r: (r['mine'], -r['freed_alone_gb'], r['place']))
# deleting every Codex place together: files whose names all sit in Codex places
codex = [r['place'] for r in rows if not r['mine']]
freed_all = 0
seen = set()
for place in codex:
    for path, st in walk(place):
        fid = (st.st_dev, st.st_ino)
        if fid in seen:
            continue
        seen.add(fid)
        if st.st_nlink <= 1 or all(any(inside(n, c) for c in codex) for n in names(path, st)):
            freed_all += st.st_size


def freed_together(group):
    total, seen = 0, set()
    for place in group:
        for path, st in walk(place):
            fid = (st.st_dev, st.st_ino)
            if fid in seen:
                continue
            seen.add(fid)
            if st.st_nlink <= 1 or all(any(inside(n, c) for c in group) for n in names(path, st)):
                total += st.st_size
    return total


# the older Codex copies: everything but Codex's current v19 runtime and build and the 4x art's first folder
KEEP = ('runtime-body-ui-20261024-v19-menus-4k', 'builds\\body-ui-20261024-v19-menus-4k', 'candidates\\hires-v1\\assets')
older = [p for p in codex if not p.endswith(KEEP)]
# what all 33 places take on the disk together, each file counted once
union = {}
for r in rows:
    for path, st in walk(r['place']):
        union[(st.st_dev, st.st_ino)] = st.st_size
png_names = defaultdict(int)
for fid in size_of:
    png_names[len(names_cache[fid])] += 1
summary = {'pngs': len(pngs), 'png_gb': round(sum(size_of.values()) / 2**30, 2), 'places': len(rows), 'codex_places': len(codex),
           'all_places_on_disk_gb': round(sum(union.values()) / 2**30, 2),
           'all_places_as_explorer_adds_up_gb': round(sum(r['folder_gb'] for r in rows), 1),
           'freed_if_all_codex_places_deleted_gb': round(freed_all / 2**30, 2),
           'older_codex_places': len(older), 'freed_if_older_codex_places_deleted_gb': round(freed_together(older) / 2**30, 2),
           'pngs_by_name_count': dict(sorted(png_names.items()))}
(HERE / 'qa' / 'png_links.json').write_text(json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1), 'utf-8')
print(json.dumps(summary, ensure_ascii=False))
for r in rows:
    print(f"{'mine ' if r['mine'] else 'codex'} {r['png_links']:5d} png {r['png_gb']:6.2f} GB | folder {r['folder_gb']:7.2f} GB | alone {r['freed_alone_gb']:6.2f} GB | {r['place']}")
