"""Supervising Codex's redraws (the user, 10-25: 「네가 코덱스의 작업물을 계속 감독하면서 원본의 사이즈와 형식에 맞게 만드는지
봐주도록 해」). Light and at idle priority (the user plays on the same PC): every 60 s it looks at the delivery folder (PNG
names, sizes, times) and at the Codex session's log for a finished turn; it exits, so the caller wakes, when PNGs appeared
or changed and held still for one more look, when a turn ended, or after the time limit.
The second batch's final folder on F: is watched too (Codex moved its work there on 10-25 evening).
python watch_redraw.py [hours] [turn]   -> one line: what changed ('turn': only a finished Codex turn wakes)
"""
import ctypes
import json
import sys
import time
from pathlib import Path

ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x40)   # IDLE_PRIORITY_CLASS
DELIVERY = Path(r'P:\AI\Codex\projects\reconquista-ko\deliverables\redraw-4k-20261025')
BATCH2 = Path(r'F:\AI\Codex\projects\reconquista-art-20261025\priority2\final')   # 10-25 evening Codex moved its work to F:
ROLLOUT = Path(r'P:\AI\Codex\sessions\2026\10\25\rollout-2026-10-25T15-54-07-01a171d6-8876-7860-97fd-33aac354fca7.jsonl')
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
turn_only = len(sys.argv) > 2 and sys.argv[2] == 'turn'   # wake only when Codex's turn ends (its files are all there and still changing)


def pngs():
    found = {}
    for tag, folder in (('', DELIVERY), ('batch2/', BATCH2)):
        if folder.exists():
            found.update({tag + str(p.relative_to(folder)): (p.stat().st_size, int(p.stat().st_mtime)) for p in folder.rglob('*.png')})
    return found


def turns(offset):
    """turns that finished after this watch began (Codex can flush an older turn's end late), and the new offset"""
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


STARTED = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())   # rollout timestamps are UTC, ISO
start, before = time.time(), pngs()
offset = ROLLOUT.stat().st_size if ROLLOUT.exists() else 0
seen = None
while time.time() - start < hours * 3600:
    time.sleep(60)
    now = pngs()
    if now != before and not turn_only:
        if now == seen:                          # unchanged for one more look: written
            new = sorted(k for k in now if before.get(k) != now[k])
            print(json.dumps({'pngs_changed': new, 'total': len(now)}, ensure_ascii=False))
            sys.exit(0)
        seen = now
    if ROLLOUT.exists():
        done, offset = turns(offset)
        if done:
            print(json.dumps({'codex_turn_done': done[-1], 'pngs': len(now)}, ensure_ascii=False))
            sys.exit(0)
print(json.dumps({'timeout_hours': hours, 'pngs': len(pngs())}))
