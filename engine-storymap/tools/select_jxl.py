"""Keep a JPEG XL copy only where the game gets the picture sooner than from its PNG. Input is the timing table from
jxlbench --csv (32-bit, the DLL's libjxl and thread count, decode from memory, best of N). A copy stays when its decode
takes no longer than the PNG's decode plus the read time its smaller file saves on this SATA SSD (about 500 MB/s, i.e.
2 ms per MB). The rest (small art, flat art, the lossless gray masks) move to build/hires-jxl-slower, so the DLL keeps
reading their PNGs; nothing is deleted.
python select_jxl.py qa/jxl_bench.csv   -> build/hires-jxl (kept), build/hires-jxl-slower (moved), qa/jxl_select.json
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
KEEP, SLOWER = HERE / 'build' / 'hires-jxl', HERE / 'build' / 'hires-jxl-slower'
MS_PER_MB = 2.0

rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8-sig')))   # PowerShell's Out-File adds a BOM
SLOWER.mkdir(exist_ok=True)
kept, moved = [], []
for r in rows:
    png_ms, jxl_ms = float(r['png_ms']), float(r['jxl_ms'])
    saved_read = (int(r['png_bytes']) - int(r['jxl_bytes'])) / 2**20 * MS_PER_MB
    (kept if 0 <= jxl_ms <= png_ms + saved_read else moved).append(r)
for r in moved:
    src = KEEP / f'{r["key"]}.jxl'
    if src.exists():
        src.replace(SLOWER / src.name)
total = lambda rs, k: sum(int(r[k]) for r in rs)  # noqa: E731
summary = {
    'kept': len(kept), 'moved': len(moved),
    'kept_png_gb': round(total(kept, 'png_bytes') / 2**30, 2), 'kept_jxl_gb': round(total(kept, 'jxl_bytes') / 2**30, 2),
    'moved_png_gb': round(total(moved, 'png_bytes') / 2**30, 2),
    'disk_after_gb': round((total(kept, 'jxl_bytes') + total(moved, 'png_bytes')) / 2**30, 2),
    'decode_ms_png_all': round(sum(float(r['png_ms']) for r in rows)),
    'decode_ms_after': round(sum(float(r['jxl_ms']) for r in kept) + sum(float(r['png_ms']) for r in moved)),
    'worst_png_ms': max(float(r['png_ms']) for r in rows),
    'worst_after_ms': max([float(r['jxl_ms']) for r in kept] + [float(r['png_ms']) for r in moved]),
}
(HERE / 'qa' / 'jxl_select.json').write_text(json.dumps({'summary': summary, 'moved': [r['key'] for r in moved]}, indent=1), 'utf-8')
print(json.dumps(summary))
