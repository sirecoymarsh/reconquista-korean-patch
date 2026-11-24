"""Which entries differ between two scenario.arc files (read-only).
python diff_arc.py old.arc new.arc
"""
import sys
from pathlib import Path

import codex_model as CM

sys.path.insert(0, str(CM.CODEX / 'tools'))
from inspect_majiro import Arc  # noqa: E402


def entries(p):
    a = Arc(Path(p))
    raw = a.path.read_bytes()
    return {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}


old, new = entries(sys.argv[1]), entries(sys.argv[2])
print('only old', sorted(set(old) - set(new)))
print('only new', sorted(set(new) - set(old)))
print('changed', sorted(n for n in old.keys() & new.keys() if old[n] != new[n]))
