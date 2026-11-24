"""Does an expression upscaled as its face crop (sprite_job.py) give the patch the whole picture gave? The sample's 10
expressions, built both ways from Codex's high-fidelity-4x: the whole pictures (build/, 10-25) and the crops.
python sprite_crop_test.py <AI dir of the 10 crops>   -> F:/AI/reconquista-qa/sprites-sample1/crop-test/ (build, report.json)
"""
import json, math, os, subprocess, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'build' / 'pylib'))
import imagecodecs

S = Path(r'F:\AI\reconquista-qa\sprites-sample1')
WHOLE = Path(r'F:\AI\Codex\projects\reconquista-art-20261025\sprites-sample1\candidates\high-fidelity-4x')   # names checked 10-25
crops = Path(sys.argv[1])
out = S / 'crop-test'
ai = out / 'ai'                       # the two bases' whole 4x and the ten crops' 4x, as hard links (all on F:)
ai.mkdir(parents=True, exist_ok=True)
job = json.loads((S / 'sample-crop.json').read_text('utf-8'))
for b in job['bases']:
    q = ai / f"{b['key']}.png"
    q.unlink(missing_ok=True)
    os.link(WHOLE / f"{b['key']}.png", q)
for p in job['patches']:
    q = ai / f"{p['key']}.png"
    q.unlink(missing_ok=True)
    os.link(crops / f"{p['key']}.png", q)
r = subprocess.run([sys.executable, '-B', str(HERE / 'tools' / 'sprite_build.py'), str(S / 'sample-crop.json'), str(ai),
                    '--index', str(S / 'sprite-index.txt'), '--out', str(out / 'build')], capture_output=True, text=True)
print(r.stdout.strip()[-400:], r.stderr.strip()[-800:])
rows, worst = [], 99.0
for p in job['patches']:
    a = imagecodecs.jpegxl_decode((HERE / 'build' / 'hires-patch-sprites' / f"{p['key']}.jxl").read_bytes()).astype(np.float64)
    b = imagecodecs.jpegxl_decode((out / 'build' / 'hires-patch-sprites' / f"{p['key']}.jxl").read_bytes()).astype(np.float64)
    if a.shape != b.shape:
        rows.append({'name': p['name'], 'error': f'shape {a.shape} vs {b.shape}'})
        worst = 0
        continue
    d = np.abs(a - b)
    mse = float((d ** 2).mean())
    psnr = 99.0 if mse == 0 else 10 * math.log10(255 * 255 / mse)
    worst = min(worst, psnr)
    rows.append({'name': p['name'], 'box_1x': p['box_1x'], 'mean_diff': round(float(d.mean()), 2), 'max_diff': int(d.max()),
                 'over_16_pct': round(100 * float((d.max(axis=2) > 16).mean()), 2), 'psnr': round(psnr, 1)})
report = {'what': 'face-crop patches vs whole-picture patches (the same AI, the same blend)', 'worst_psnr': round(worst, 1),
          'pass': worst >= 38, 'rows': rows}
(out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', 'utf-8')
for x in rows:
    print(json.dumps(x, ensure_ascii=False))
print('worst psnr', round(worst, 1), 'pass' if worst >= 38 else 'FAIL')
