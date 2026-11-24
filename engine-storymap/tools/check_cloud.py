"""Codex's cloud-edge repairs (cloud\<key>.png; the user, 10-25: 「하늘의 구름같은거에 기존 업스케일링은 희미하면 검은색
경계를 죽죽 그어댔는데 해결좀 하라 그래」), against the play copy's blend they started from: how many pixels changed, and the
thin dark lines the art has that the source's Lanczos enlargement has not (9x9 black top-hat more than 10 darker), split by
the source's edge strength (Sobel, 3x3 blurred: <40 soft, 40-120, >120 drawn), before and after.
python check_cloud.py   -> qa/redraw-check/cloud.md, cloud.json (names only for intro pictures)
"""
import ctypes
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x40)   # idle: the user may be playing
cv2.setNumThreads(2)
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
import audit_soft_lines as A  # noqa: E402
import check_redraw as C  # noqa: E402

KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
BANDS = ((0, 40), (40, 120), (120, 1 << 30))


def dark_lines(src, art, smooth_bh, bands):
    ba = cv2.morphologyEx(cv2.cvtColor(np.ascontiguousarray(art), cv2.COLOR_RGB2GRAY), cv2.MORPH_BLACKHAT, KERNEL).astype(np.int16)
    hit = (ba - smooth_bh) > 10
    return [round(100 * float((hit & b).sum()) / max(1, int(b.sum())), 3) for b in bands]


rows = []
for p in sorted((C.DELIVERY / 'cloud').glob('*.png')):
    key = p.stem.lower()
    name = C.NAME_OF.get(key)
    if not name:
        rows.append({'key': key, 'problem': '키가 아님'})
        continue
    src = np.ascontiguousarray(A.hires_assets.decode(name)[:, :, :3]).astype(np.uint8)
    h, w = src.shape[:2]
    now = C.blend_now(key)
    fixed = np.asarray(Image.open(p).convert('RGB'))
    if now is None or now.shape != fixed.shape:
        rows.append({'key': key, 'problem': f'크기 {fixed.shape} / 지금 {None if now is None else now.shape}'})
        continue
    g = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY).astype(np.float32)
    edge = cv2.GaussianBlur(cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)), (3, 3), 0)
    bands = [cv2.resize(((edge >= lo) & (edge < hi)).astype(np.uint8), (w * 4, h * 4), interpolation=cv2.INTER_NEAREST).astype(bool) for lo, hi in BANDS]
    smooth = cv2.resize(src, (w * 4, h * 4), interpolation=cv2.INTER_LANCZOS4)
    sbh = cv2.morphologyEx(cv2.cvtColor(smooth, cv2.COLOR_RGB2GRAY), cv2.MORPH_BLACKHAT, KERNEL).astype(np.int16)
    d = np.abs(fixed.astype(np.int16) - now.astype(np.int16)).max(axis=2)
    rows.append({'key': key, 'label': f'{name[:-4]}({key})' if name in C.INTRO else key, 'intro': name in C.INTRO,
                 'changed_pct': round(100 * float((d > 3).mean()), 3), 'max_diff': int(d.max()),
                 'before': dark_lines(src, now, sbh, bands), 'after': dark_lines(src, fixed, sbh, bands)})
    r = rows[-1]
    print(r['label'], r['changed_pct'], r['before'], '->', r['after'], flush=True)
ok = [r for r in rows if 'before' in r]
worse = [r['label'] for r in ok if any(a > b + 0.01 for a, b in zip(r['after'], r['before']))]
mean = lambda k, i: round(float(np.mean([r[k][i] for r in ok])), 3) if ok else None
summary = {'pictures': len(rows), 'checked': len(ok), 'problems': [r for r in rows if 'problem' in r], 'worse_after': worse,
           'changed_pct_max': max((r['changed_pct'] for r in ok), default=None),
           'dark_lines_mean_before': [mean('before', i) for i in range(3)], 'dark_lines_mean_after': [mean('after', i) for i in range(3)]}
out = C.OUT
out.mkdir(parents=True, exist_ok=True)
(out / 'cloud.json').write_text(json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1), 'utf-8')
lines = ['# 구름 가장자리 고침 검사', '', f"{summary['checked']}장. 어두운 가는 선 비율(%)은 원본 테두리 세기별 <40 / 40~120 / >120, 고치기 전 → 뒤.", '',
         f"평균: {summary['dark_lines_mean_before']} → {summary['dark_lines_mean_after']}, 바뀐 픽셀 최대 {summary['changed_pct_max']}%, 더 나빠진 그림 {len(worse)}장", '',
         '| 그림 | 바뀐 픽셀 | 전 | 뒤 |', '|---|---|---|---|']
for r in sorted(ok, key=lambda r: -r['before'][2]):
    lines.append(f"| {r['label']} | {r['changed_pct']}% | {r['before']} | {r['after']} |")
(out / 'cloud.md').write_text('\n'.join(lines) + '\n', 'utf-8')
print(json.dumps(summary, ensure_ascii=False))
