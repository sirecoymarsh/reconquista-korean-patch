"""Dark lines the 4x art drew where its source is soft (the user, 10-25: 「흐린 외곽선에 강제로 검은 색 경계를 만드는게
업스케일 문제야」). Soft = the source's Sobel magnitude (3x3 blurred) under 40, the same cut the blend uses; see soft_dark.
Pictures: the intro chapters' backgrounds and CGs (spoiler rule), worst first.
python audit_soft_lines.py [current|blend|<png dir>] [label]  -> qa/upscale-audit/soft-lines-<label>.json
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
DARK = 24
sys.path.insert(0, r'P:\AI\Codex\projects\reconquista-ko\tools')
import hires_assets  # noqa: E402  (Codex's decoder, read-only)

m = json.loads((HERE / 'runtime-play' / 'hires-manifest.json').read_text('utf-8-sig'))
FILE = {e['name'].lower(): e['file'] for e in m['entries']}


KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))


def soft_dark(src, art):
    """% of the source's soft area where the art has a thin dark line (black top-hat, 9x9) that the smooth enlargement
    does not have (by more than 10 levels): the invented outlines the user saw."""
    h, w = src.shape[:2]
    g = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY).astype(np.float32)
    edge = cv2.GaussianBlur(cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)), (3, 3), 0)
    soft = cv2.resize((edge < 40).astype(np.uint8), (w * 4, h * 4), interpolation=cv2.INTER_NEAREST).astype(bool)
    smooth = cv2.resize(src, (w * 4, h * 4), interpolation=cv2.INTER_LANCZOS4)
    ba = cv2.morphologyEx(cv2.cvtColor(np.ascontiguousarray(art), cv2.COLOR_RGB2GRAY), cv2.MORPH_BLACKHAT, KERNEL).astype(np.int16)
    bs = cv2.morphologyEx(cv2.cvtColor(smooth, cv2.COLOR_RGB2GRAY), cv2.MORPH_BLACKHAT, KERNEL).astype(np.int16)
    hit = ((ba - bs) > 10) & soft
    return round(100 * hit.sum() / max(1, soft.sum()), 4), hit


def load_art(art_dir, name):
    if art_dir == 'current':
        return cv2.imread(str(HERE / 'runtime-play' / 'hires' / FILE[name]), cv2.IMREAD_COLOR)[:, :, ::-1]
    if art_dir == 'blend':
        sys.path.insert(0, str(HERE / 'build' / 'pylib'))
        import imagecodecs
        f = HERE / 'build' / 'hires-jxl-blend' / f'{FILE[name][:8]}.jxl'
        return imagecodecs.jpegxl_decode(f.read_bytes()) if f.exists() else None
    f = Path(art_dir) / f'{name.split(".")[0]}.png'
    return cv2.imread(str(f), cv2.IMREAD_COLOR)[:, :, ::-1] if f.exists() else None


if __name__ == '__main__':
    art_dir = sys.argv[1] if len(sys.argv) > 1 else 'current'
    label = sys.argv[2] if len(sys.argv) > 2 else art_dir
    names = (HERE / 'qa' / 'upscale-review' / 'intro-names.txt').read_text('utf-8').split()
    rows = []
    for n in names:
        if n not in FILE:
            continue
        art = load_art(art_dir, n)
        if art is None:
            continue
        src = np.ascontiguousarray(hires_assets.decode(n)[:, :, :3]).astype(np.uint8)
        if art.shape[:2] != (src.shape[0] * 4, src.shape[1] * 4):
            continue
        pct, _ = soft_dark(src, art)
        rows.append({'name': n, 'soft_dark_pct': pct})
    rows.sort(key=lambda r: -r['soft_dark_pct'])
    out = HERE / 'qa' / 'upscale-audit'
    out.mkdir(parents=True, exist_ok=True)
    (out / f'soft-lines-{label}.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), 'utf-8')
    print(json.dumps(rows[:15], ensure_ascii=False))
