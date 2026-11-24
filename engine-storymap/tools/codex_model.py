"""Load Codex's read-only flowchart model (catalogue + CFG over the v13 base scripts) from its own sources.

Nothing in the Codex project is written. Codex's included-usage stop check is a Codex-session policy and is
not consulted here (this process spends no Codex usage).
"""
import sys
from pathlib import Path

CODEX = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타')
sys.path.insert(0, str(CODEX / 'candidates' / 'flowchart-v1'))
sys.dont_write_bytecode = True
import core  # noqa: E402

core.stop = lambda: None
_model = None


def model():
    global _model
    if _model is None:
        _model = core.Model()
    return _model


if __name__ == '__main__':
    import time
    t = time.time()
    m = model()
    print('chapters', len(m.chapters), 'nodes', len(m.nodes), 'reachable', len(m.parent), 'sec', round(time.time() - t, 1))
