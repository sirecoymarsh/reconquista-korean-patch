"""After tools/blend_art.py: the intro chapters' AI pictures (spoiler rule) before and after the blend.
For each: invented thin dark lines in the source's soft areas (audit_soft_lines.soft_dark), and how far the picture is from
its source at source size (mean of the largest channel difference, 1/8 size, where colour drift shows).
A sheet of the pictures that changed most (whole picture, then the most-changed region at 1:1): current | blend.
python check_blend.py   -> qa/upscale-audit/blend-check.json, qa/upscale-audit/blend-sheet.png
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
import audit_soft_lines as A  # noqa: E402

OUT = HERE / 'qa' / 'upscale-audit'


def drift(src, art):
    h, w = src.shape[:2]
    a = cv2.resize(art, (w // 8, h // 8), interpolation=cv2.INTER_AREA).astype(np.int16)
    s = cv2.resize(src, (w // 8, h // 8), interpolation=cv2.INTER_AREA).astype(np.int16)
    return float(np.abs(a - s).max(axis=2).mean())


if __name__ == '__main__':
    names = (HERE / 'qa' / 'upscale-review' / 'intro-names.txt').read_text('utf-8').split()
    rows, keep = [], {}
    for n in names:
        if n not in A.FILE:
            continue
        cur, bl = A.load_art('current', n), A.load_art('blend', n)
        if cur is None or bl is None:
            continue
        src = np.ascontiguousarray(A.hires_assets.decode(n)[:, :, :3]).astype(np.uint8)
        if cur.shape[:2] != (src.shape[0] * 4, src.shape[1] * 4):
            continue
        lines_c, _ = A.soft_dark(src, cur)
        lines_b, _ = A.soft_dark(src, bl)
        diff = cv2.blur(np.abs(cur.astype(np.int16) - bl.astype(np.int16)).max(axis=2).astype(np.float32), (64, 64))
        y, x = np.unravel_index(int(np.argmax(diff)), diff.shape)
        rows.append({'name': n, 'lines_current': lines_c, 'lines_blend': lines_b, 'drift_current': round(drift(src, cur), 2),
                     'drift_blend': round(drift(src, bl), 2), 'changed_at': [int(x), int(y)], 'changed': round(float(diff.max()), 1)})
    summary = {'pictures': len(rows),
               'lines_current_mean': round(float(np.mean([r['lines_current'] for r in rows])), 3),
               'lines_blend_mean': round(float(np.mean([r['lines_blend'] for r in rows])), 3),
               'lines_current_max': max(r['lines_current'] for r in rows), 'lines_blend_max': max(r['lines_blend'] for r in rows),
               'drift_current_mean': round(float(np.mean([r['drift_current'] for r in rows])), 2),
               'drift_blend_mean': round(float(np.mean([r['drift_blend'] for r in rows])), 2)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'blend-check.json').write_text(json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1), 'utf-8')
    print(json.dumps(summary, ensure_ascii=False))
    top = sorted(rows, key=lambda r: -r['changed'])[:8]
    font = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 16)
    TW, TH = 400, 300
    sheet = Image.new('RGB', (4 * (TW + 6), len(top) * (TH + 26)), (28, 28, 28))
    d = ImageDraw.Draw(sheet)
    for i, r in enumerate(top):
        cur, bl = A.load_art('current', r['name']), A.load_art('blend', r['name'])
        x, y = r['changed_at']
        x0, y0 = max(0, min(x - TW // 2, cur.shape[1] - TW)), max(0, min(y - TH // 2, cur.shape[0] - TH))
        cells = [Image.fromarray(np.ascontiguousarray(cur)).resize((TW, TH), Image.LANCZOS), Image.fromarray(np.ascontiguousarray(bl)).resize((TW, TH), Image.LANCZOS),
                 Image.fromarray(np.ascontiguousarray(cur[y0:y0 + TH, x0:x0 + TW])), Image.fromarray(np.ascontiguousarray(bl[y0:y0 + TH, x0:x0 + TW]))]
        top_y = i * (TH + 26)
        d.text((4, top_y + 3), f"{r['name']}  지금 | 섞기 (전체)   ·   지금 | 섞기 (가장 많이 바뀐 곳 1:1)", fill=(250, 214, 160), font=font)
        for c, im in enumerate(cells):
            sheet.paste(im, (c * (TW + 6), top_y + 26))
    sheet.save(OUT / 'blend-sheet.png')
