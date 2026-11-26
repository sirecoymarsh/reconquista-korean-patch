"""The game's pictures as the engine composes them (TC01 deltas over their bases, pure red -> base), 1x from the archives
and 4x from the HD layer's art (hires-jxl/<key>.jxl when current, else hires/<key>.png), for one runtime folder."""
import struct
import sys
import zlib
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.dont_write_bytecode = True
import make_runtime as M  # noqa: E402  (core: the Majiro archive reader)
CODEX = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타')
sys.path.insert(0, str(CODEX / 'ui-opening-ending' / 'tools'))
from raster_codec import raw_image  # noqa: E402
PROJECT = Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024')   # the working project: its build\pylib has imagecodecs (JPEG XL)
sys.path.insert(0, str(PROJECT / 'build' / 'pylib'))
import imagecodecs  # noqa: E402

core = M.core
# The engine's order for a picture's name: it registers its archives from the highest number down (exe 0x422c84: data12 ...
# data2, data1, data, then slowdata12 ... slowdata, stream ...) and the first that has the name wins. 26 names are in both
# data.arc and data1.arc (ev1132a/c/d, ev113a-c, netu06, ...): the game shows data1.arc's (11-27: a changed data.arc
# ev1132d still showed its Japanese line; Codex's 4x art was made from data1.arc's, hires-manifest).
ARCS = ('data2.arc', 'data1.arc', 'data.arc')
RED = np.array([255, 0, 0], np.uint8)


def key(name):
    return f'{zlib.crc32(name.lower().encode("cp932")):08x}'


class Game:
    def __init__(self, run):
        self.run = Path(run)
        self.entries = {}                      # stem (lower) -> (arc name, entry)
        self.arcs = {}
        for a in ARCS:
            arc = core.Arc(self.run / a)
            self.arcs[a] = arc
            for e in arc.entries:
                n = e['name']
                if n.lower().endswith('.rct'):
                    self.entries.setdefault(n.lower()[:-4], (a, e))

    def payload(self, stem):
        a, e = self.entries[stem.lower()]
        with open(self.arcs[a].path, 'rb') as f:
            f.seek(e['offset'])
            return f.read(e['size'])

    def name(self, stem):
        return self.entries[stem.lower()][1]['name']

    def arc_of(self, stem):
        return self.entries[stem.lower()][0]

    def base_of(self, stem):
        """the base picture a TC01 delta names (None for a TC00 picture)"""
        b = self.payload(stem)
        if b[4:8] != b'TC01':
            return None
        n = struct.unpack_from('<H', b, 20)[0]
        base = b[22:22 + n].split(b'\0')[0].decode('cp932')
        return base[:-4].lower() if base.lower().endswith('.rct') else base.lower()

    @lru_cache(maxsize=64)
    def raw(self, stem):
        a, prefix, ch = raw_image(self.payload(stem))
        return a

    @lru_cache(maxsize=64)
    def composed(self, stem):
        a = self.raw(stem)
        b = self.base_of(stem)
        if not b:
            return a
        base = self.composed(b)
        red = np.all(a == RED, axis=2)
        out = a.copy()
        out[red] = base[red]
        return out

    def art_paths(self, stem):
        k = key(self.name(stem))
        return self.run / 'hires' / f'{k}.png', self.run / 'hires-jxl' / f'{k}.jxl'

    @lru_cache(maxsize=24)
    def art(self, stem):
        """the 4x art the HD layer shows for this picture (as the DLL picks: the .jxl unless the .png is newer)"""
        png, jxl = self.art_paths(stem)
        if jxl.exists() and not (png.exists() and png.stat().st_mtime > jxl.stat().st_mtime):
            return imagecodecs.jpegxl_decode(jxl.read_bytes())[..., :3]
        return np.asarray(Image.open(png).convert('RGB'))


def runs(eq):
    """for each position, how many equal pixels follow from there (eq[i]: pixel i equals its copy source)"""
    n = len(eq)
    out = np.zeros(n + 1, np.int64)
    idx = np.flatnonzero(~eq)                    # positions that break a run
    nxt = np.full(n, n, np.int64)
    # the next breaking position at or after i
    if len(idx):
        pos = np.searchsorted(idx, np.arange(n))
        has = pos < len(idx)
        nxt[has] = idx[pos[has]]
    return nxt - np.arange(n)


def encode_rct(rgb, prefix):
    """RCT pixel data with the format's copy commands (GARbro's reading, decode_ui.unpack): a run equal to the pixel to
    the left (SH24 index 0) or the pixel above (index 9) is one command; anything else literal. The literal-only encoder
    made every picture its full 1.4 MB (the cards and deltas are mostly flat): this keeps the archive near its size."""
    h, w = rgb.shape[:2]
    px = rgb.reshape(-1, 3)
    n = len(px)
    eq_left = np.zeros(n, bool)
    eq_left[1:] = np.all(px[1:] == px[:-1], axis=1)
    eq_up = np.zeros(n, bool)
    eq_up[w:] = np.all(px[w:] == px[:-w], axis=1)
    run_left, run_up = runs(eq_left), runs(eq_up)
    raw = np.ascontiguousarray(px[:, ::-1]).tobytes()   # the file keeps B, G, R
    out = bytearray(raw[:3])
    lit = []                                        # pending literal pixel indices (consecutive)

    def flush():
        i0 = 0
        while i0 < len(lit):
            c = min(len(lit) - i0, 65663)
            if c < 128:
                out.append(c - 1)
            else:
                out.append(127)
                out.extend((c - 128).to_bytes(2, 'little'))
            a0 = lit[i0]
            out.extend(raw[a0 * 3:(a0 + c) * 3])
            i0 += c
        lit.clear()
    i = 1
    while i < n:
        L, idx = int(run_left[i]), 0
        U = int(run_up[i])
        if U > L:
            L, idx = U, 9
        if L >= 2:
            flush()
            while L > 0:
                c = min(L, 65539)
                k = c - 1
                if k < 3:
                    out.append(0x80 | (idx << 2) | k)
                else:
                    out.append(0x80 | (idx << 2) | 3)
                    out.extend((k - 3).to_bytes(2, 'little'))
                i += c
                L -= c
        else:
            lit.append(i)
            i += 1
    flush()
    header = bytearray(prefix)
    struct.pack_into('<I', header, 16, len(out))
    return bytes(header) + bytes(out)


def encode_payload(original_payload, rgb):
    """an RCT payload with the original's header (TC00, or TC01 with its base name) and these pixels"""
    _, prefix, ch = raw_image(original_payload)
    assert ch == 3
    out = encode_rct(rgb, prefix)
    back, p2, _ = raw_image(out)
    assert np.array_equal(back, rgb) and p2[:16] == prefix[:16] and p2[20:] == prefix[20:]
    return out


def jxl(rgb):
    """the 4x art as the HD layer's JPEG XL (tools/convert_jxl.py: distance 0.5, effort 7, decoding speed 3, >= 40 dB)"""
    for d in (0.5, 0.3):
        data = imagecodecs.jpegxl_encode(rgb, distance=d, effort=7, decodingspeed=3, numthreads=8)
        back = imagecodecs.jpegxl_decode(data, numthreads=8)[..., :3]
        mse = float(np.mean((back.astype(np.float64) - rgb.astype(np.float64)) ** 2))
        psnr = 99.0 if mse == 0 else 10 * np.log10(255 * 255 / mse)
        if psnr >= 40:
            return data, d, psnr
    raise ValueError(f'jxl only {psnr:.1f} dB')
