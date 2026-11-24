"""Where the Reconquista folders' disk space goes (read-only). A file counts as 'own' when no other path links to it
(st_nlink == 1); shared hard links are counted once, under 'shared'.
python space_report.py   -> printed table
"""
import os
from collections import defaultdict
from pathlib import Path

ROOTS = [Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타'), Path(r'P:\AI\Codex\projects\reconquista_flowchart_20261024')]
own = defaultdict(int)
seen_shared = {}
for root in ROOTS:
    for top in sorted(p for p in root.iterdir()):
        label = f'{root.name}\\{top.name}'
        stack = [top]
        while stack:
            p = stack.pop()
            try:
                if p.is_dir():
                    stack.extend(p.iterdir())
                    continue
                st = p.stat()
            except OSError:
                continue
            if st.st_nlink <= 1:
                own[label] += st.st_size
            else:
                seen_shared.setdefault((st.st_dev, st.st_ino), st.st_size)
rows = sorted(own.items(), key=lambda kv: -kv[1])
total_own = sum(own.values())
print(f'own (unshared) total {total_own / 2**30:.2f} GB; shared hard-linked data counted once {sum(seen_shared.values()) / 2**30:.2f} GB')
for label, size in rows[:30]:
    if size > 50 * 2**20:
        print(f'{size / 2**30:7.2f} GB  {label}')
