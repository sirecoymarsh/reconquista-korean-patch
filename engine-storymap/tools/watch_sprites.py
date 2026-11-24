"""Waiting on Codex's standing-picture upscale (to_codex/20261026-0610_인물-그림-4K-전체.md), light and at idle priority:
every 30 s it looks for the crop test's 10 PNGs under Codex's sprites-full folder and at the session's log for a finished
turn. It exits, so the caller wakes, when the 10 are all there and held still for one more look ('crop'), when a turn
ended ('turn'), or after the time limit.
python watch_sprites.py [hours] [crop|turn]   (crop: wake for the crop test or the turn's end; turn: only the turn's end)
"""
import ctypes
import json
import sys
import time
from pathlib import Path

ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x40)   # IDLE_PRIORITY_CLASS
ROOT = Path(r'F:\AI\Codex\projects\reconquista-art-20261025\sprites-full')
ROLLOUT = Path(r'P:\AI\Codex\sessions\2026\10\25\rollout-2026-10-25T15-54-07-01a171d6-8876-7860-97fd-33aac354fca7.jsonl')
CROPS = ['a8c1f2cb', '95a1db7b', '5d41540b', '5efd08de', '292d39cf', '982134fc', 'a5411d4c', '1761c15c', '6da1923c', 'dc3d12f9']
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
mode = sys.argv[2] if len(sys.argv) > 2 else 'crop'
STARTED = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())   # rollout timestamps are UTC, ISO


def crop_folder():
    """a folder under ROOT with 'output' and 'crop' in its path that holds all 10, with their sizes and times (Codex copies
    the inputs to work\\input\\crop-test first: 10-26 that woke the watch early)"""
    if not ROOT.exists():
        return None, None
    for d in sorted({p.parent for p in ROOT.rglob('*.png') if 'crop' in str(p.parent).lower() and 'output' in str(p.parent).lower()}):
        files = [d / f'{k}.png' for k in CROPS]
        if all(f.exists() for f in files):
            return d, [(f.stat().st_size, int(f.stat().st_mtime)) for f in files]
    return None, None


def turns(offset):
    with ROLLOUT.open('rb') as f:
        f.seek(offset)
        chunk = f.read()
    done = []
    for line in chunk.splitlines():
        if b'task_complete' in line:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get('payload', {}).get('type') == 'task_complete' and o.get('timestamp', '') > STARTED:
                done.append((o['payload'].get('last_agent_message') or '')[:300])
    return done, offset + len(chunk)


start = time.time()
offset = ROLLOUT.stat().st_size if ROLLOUT.exists() else 0
seen = None
while time.time() - start < hours * 3600:
    time.sleep(30)
    if mode == 'crop':
        d, state = crop_folder()
        if d is not None:
            if state == seen:
                print(json.dumps({'crop_test_ready': str(d)}, ensure_ascii=False))
                sys.exit(0)
            seen = state
    if ROLLOUT.exists():
        done, offset = turns(offset)
        if done:
            n = len(list(ROOT.rglob('*.png'))) if ROOT.exists() else 0
            print(json.dumps({'codex_turn_done': done[-1], 'pngs_under_sprites_full': n}, ensure_ascii=False))
            sys.exit(0)
print(json.dumps({'timeout_hours': hours}))
