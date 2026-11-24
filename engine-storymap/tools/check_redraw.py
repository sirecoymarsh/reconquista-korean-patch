"""Codex's redrawn 4K pictures, checked against what the 4K layer and the game need (the user, 10-25: 「네가 코덱스의
작업물을 계속 감독하면서 원본의 사이즈와 형식에 맞게 만드는지 봐주도록 해」; the order: to_codex/20261025-1558_*.md).
Per PNG in the delivery folder (named <4K key>.png; a picture name is mapped to its key and reported):
- format like Codex's hires PNGs: exactly 4x the original (3200x2400 for 800x600), 8-bit RGB (colour type 2), not interlaced
- layout and colour: scaled back to the original size it must match the original (the game lays figures and text over
  it): mean difference at full and 1/4 size, shift by phase correlation, share of the original's edges it keeps
- detail: sharpness (Laplacian variance at 4x) against the picture now in the play copy (the blend)
python check_redraw.py [folder] [out]   -> [out, else qa/redraw-check]/report.md, report.json, sheets/<key>.png (crops for Claude's review)
The report names only intro pictures (the user's progress, spoiler rule); others go by key.
"""
import json
import struct
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista-ko\tools')
import hires_assets  # noqa: E402  (Codex's decoder, read-only)

DELIVERY = Path(r'P:\AI\Codex\projects\reconquista-ko\deliverables\redraw-4k-20261025')
OUT = HERE / 'qa' / 'redraw-check'
MANIFEST = json.loads((HERE / 'runtime-play' / 'hires-manifest.json').read_text('utf-8-sig'))
KEY_OF = {e['name'].lower(): e.get('key') or e['file'][:8] for e in MANIFEST['entries'] if 'file' in e}
NAME_OF = {k: n for n, k in KEY_OF.items()}
INTRO = set((HERE / 'qa' / 'upscale-review' / 'intro-names.txt').read_text('utf-8').split())
LIMITS = {'mad_quarter': 6.0, 'shift_px': 0.75, 'edge_keep': 0.55}


def png_header(path):
    b = path.read_bytes()
    if b[:8] != b'\x89PNG\r\n\x1a\n':
        return None, []
    i, chunks, ihdr = 8, [], None
    while i + 8 <= len(b):
        n, = struct.unpack('>I', b[i:i + 4])
        t = b[i + 4:i + 8].decode('latin1')
        if t == 'IHDR':
            w, h, depth, colour, _, _, interlace = struct.unpack('>IIBBBBB', b[i + 8:i + 21])
            ihdr = {'w': w, 'h': h, 'depth': depth, 'colour': colour, 'interlace': interlace}
        chunks.append(t)
        i += 12 + n
    return ihdr, sorted(set(chunks))


def blend_now(key):
    """the picture in the play copy now: the blended JXL, else Codex's PNG"""
    f = HERE / 'build' / 'hires-jxl-blend' / f'{key}.jxl'
    if f.exists():
        sys.path.insert(0, str(HERE / 'build' / 'pylib'))
        import imagecodecs
        return imagecodecs.jpegxl_decode(f.read_bytes())[:, :, :3]
    p = HERE / 'runtime-play' / 'hires' / f'{key}.png'
    return cv2.imread(str(p), cv2.IMREAD_COLOR)[:, :, ::-1] if p.exists() else None


def sharpness(a):
    return float(cv2.Laplacian(cv2.cvtColor(np.ascontiguousarray(a), cv2.COLOR_RGB2GRAY), cv2.CV_32F).var())


def check(path):
    stem = path.stem.lower()
    row = {'file': path.name, 'problems': [], 'notes': []}
    key = stem if stem in NAME_OF else KEY_OF.get(stem if stem.endswith('.rct') else stem + '.rct')
    if not key:
        row['problems'].append('이름이 4K 키도, 그림 이름도 아님')
        return row
    if stem != key:
        row['notes'].append(f'파일 이름이 키가 아님(→ {key}.png로 받아야 함)')
    name = NAME_OF[key]
    row['key'] = key
    row['label'] = f'{name[:-4]}({key})' if name in INTRO else key
    row['intro'] = name in INTRO
    ihdr, chunks = png_header(path)
    if not ihdr:
        row['problems'].append('PNG가 아님')
        return row
    src = np.ascontiguousarray(hires_assets.decode(name)[:, :, :3]).astype(np.uint8)
    h0, w0 = src.shape[:2]
    row.update(size=[ihdr['w'], ihdr['h']], want=[w0 * 4, h0 * 4], depth=ihdr['depth'], colour=ihdr['colour'], interlace=ihdr['interlace'], chunks=chunks)
    if (ihdr['w'], ihdr['h']) != (w0 * 4, h0 * 4):
        row['problems'].append(f"크기 {ihdr['w']}×{ihdr['h']} (원본 {w0}×{h0}의 4배 {w0 * 4}×{h0 * 4}여야 함)")
    if ihdr['depth'] != 8 or ihdr['colour'] != 2:
        kind = {0: '회색', 2: 'RGB', 3: '팔레트', 4: '회색+알파', 6: 'RGBA'}.get(ihdr['colour'], str(ihdr['colour']))
        row['problems'].append(f"형식 {ihdr['depth']}비트 {kind} (8비트 RGB여야 함)")
    if ihdr['interlace']:
        row['problems'].append('인터레이스 PNG (아니어야 함)')
    odd = [c for c in chunks if c in ('iCCP', 'cHRM', 'PLTE', 'tRNS')]
    if odd:
        row['notes'].append('색 관련 덩어리 ' + ','.join(odd) + ' (지금 4K PNG에는 gAMA·sRGB만 있음)')
    art = np.asarray(Image.open(path).convert('RGB'))
    if art.shape[:2] != (h0 * 4, w0 * 4):
        art4 = cv2.resize(art, (w0 * 4, h0 * 4), interpolation=cv2.INTER_AREA)   # measure the rest anyway
    else:
        art4 = art
    small = cv2.resize(art4, (w0, h0), interpolation=cv2.INTER_AREA)
    mad = float(np.abs(small.astype(np.int16) - src.astype(np.int16)).mean())
    q = lambda a: cv2.resize(a, (w0 // 4, h0 // 4), interpolation=cv2.INTER_AREA).astype(np.int16)
    madq = float(np.abs(q(small) - q(src)).mean())
    g0 = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY).astype(np.float32)
    g1 = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY).astype(np.float32)
    win = cv2.createHanningWindow((w0, h0), cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(g0.copy(), g1.copy(), win)   # copies: it can window its inputs in place
    e0 = cv2.Canny(g0.astype(np.uint8), 60, 140) > 0
    e1 = cv2.dilate((cv2.Canny(g1.astype(np.uint8), 60, 140) > 0).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    keep = float((e0 & e1).sum() / max(1, e0.sum()))
    now = blend_now(key)
    sharp_now = sharpness(now) if now is not None and now.shape[:2] == art4.shape[:2] else None
    sharp_new = sharpness(art4)
    row.update(mad=round(mad, 2), mad_quarter=round(madq, 2), shift=[round(dx, 2), round(dy, 2)], shift_response=round(resp, 3),
               edge_keep=round(keep, 3), sharp_new=round(sharp_new, 1), sharp_now=round(sharp_now, 1) if sharp_now else None)
    if madq > LIMITS['mad_quarter']:
        row['problems'].append(f'줄였을 때 색·배치가 원본과 다름 (1/4 크기 평균 차이 {madq:.1f}, {LIMITS["mad_quarter"]} 이하여야 함)')
    if max(abs(dx), abs(dy)) > LIMITS['shift_px']:
        row['problems'].append(f'원본보다 밀림 ({dx:+.2f}, {dy:+.2f}) 1배 픽셀')
    if keep < LIMITS['edge_keep']:
        row['problems'].append(f'원본 테두리를 {keep:.0%}만 지킴 ({LIMITS["edge_keep"]:.0%} 이상이어야 함)')
    if sharp_now and sharp_new < sharp_now:
        row['notes'].append('지금 플레이판 그림보다 덜 선명함')
    sheet(key, src, now, art4)
    return row


def sheet(key, src, now, art4):
    """the busiest 640x480 region at 4x: original (nearest, 4x) | now | new; and the whole picture scaled down"""
    h, w = art4.shape[:2]
    g = cv2.cvtColor(art4, cv2.COLOR_RGB2GRAY)
    e = cv2.blur((cv2.Canny(g, 60, 140) > 0).astype(np.float32), (640, 480))
    y, x = np.unravel_index(int(np.argmax(e)), e.shape)
    x0, y0 = max(0, min(x - 320, w - 640)), max(0, min(y - 240, h - 480))
    up = cv2.resize(src, (w, h), interpolation=cv2.INTER_NEAREST)
    cells = [up[y0:y0 + 480, x0:x0 + 640]]
    if now is not None and now.shape[:2] == (h, w):
        cells.append(now[y0:y0 + 480, x0:x0 + 640])
    cells.append(art4[y0:y0 + 480, x0:x0 + 640])
    whole = [cv2.resize(src, (640, 480), interpolation=cv2.INTER_AREA), cv2.resize(art4, (640, 480), interpolation=cv2.INTER_AREA)]
    top = np.hstack([np.pad(c, ((0, 0), (0, 6), (0, 0))) for c in cells])
    bottom = np.hstack([np.pad(c, ((0, 0), (0, 6), (0, 0))) for c in whole])
    bottom = np.pad(bottom, ((0, 6), (0, top.shape[1] - bottom.shape[1]), (0, 0))) if bottom.shape[1] < top.shape[1] else bottom[:, :top.shape[1]]
    (OUT / 'sheets').mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.vstack([top, bottom]).astype(np.uint8)).save(OUT / 'sheets' / f'{key}.png')


if __name__ == '__main__':
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x40)   # idle: the user may be playing
    cv2.setNumThreads(2)
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else DELIVERY
    if len(sys.argv) > 2:
        OUT = Path(sys.argv[2])   # a second batch's report beside, not over, the first (big sheets: Y:/F:)
    OUT.mkdir(parents=True, exist_ok=True)
    # the deliveries: <key>.png at the top and in cloud\ (review\ holds Codex's comparison copies)
    files = (sorted(folder.glob('*.png')) + sorted((folder / 'cloud').glob('*.png'))) if folder.exists() else []
    rows = [check(p) for p in files]
    (OUT / 'report.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), 'utf-8')
    lines = [f'# 다시 그린 4K 검사 ({folder})', '', f'{len(rows)}장. 이름은 도입부 그림만, 나머지는 키로 적음.', '',
             '| 그림 | 크기·형식 | 줄였을 때 차이(1/4) | 밀림 | 테두리 | 선명도(새/지금) | 문제 |', '|---|---|---|---|---|---|---|']
    for r in rows:
        fmt = f"{r['size'][0]}×{r['size'][1]} {r['depth']}비트 c{r['colour']}" if 'size' in r else '-'
        sh = f"{r['sharp_new']:.0f}/{r['sharp_now']:.0f}" if r.get('sharp_now') else (f"{r['sharp_new']:.0f}/-" if 'sharp_new' in r else '-')
        lines.append(f"| {r.get('label', r['file'])} | {fmt} | {r.get('mad_quarter', '-')} | {r.get('shift', '-')} | {r.get('edge_keep', '-')} | {sh} | "
                     f"{'; '.join(r['problems'] + r['notes']) or '없음'} |")
    (OUT / 'report.md').write_text('\n'.join(lines) + '\n', 'utf-8')
    print(json.dumps([{k: r.get(k) for k in ('label', 'size', 'problems', 'notes', 'mad_quarter', 'shift', 'edge_keep')} for r in rows], ensure_ascii=False))
