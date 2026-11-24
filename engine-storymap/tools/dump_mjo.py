"""Disassemble one script of a scenario.arc to readable Majiro IL with known names (read-only; Codex's decoder + majiro-py).
python dump_mjo.py chronicle [scenario.arc]   -> build/<name>.mjo, build/<name>.mjil
"""
import sys
from pathlib import Path

import codex_model as CM

sys.path.insert(0, str(CM.CODEX / 'tools'))
sys.path.insert(0, str(CM.CODEX / 'research' / 'vendor' / 'majiro-py' / 'src'))
import build_trial  # noqa: E402,F401  (puts the decoder on the path)
from inspect_majiro import Arc  # noqa: E402
from mjotool.__main__ import disassemble_script, read_script  # noqa: E402
from mjotool.script import ILFormat  # noqa: E402

name = sys.argv[1] if len(sys.argv) > 1 else 'chronicle'
arc_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / 'runtime-play' / 'scenario.arc'
out = Path(__file__).resolve().parents[1] / 'build'
arc = Arc(arc_path)
raw = arc.path.read_bytes()
entry = next(e for e in arc.entries if e['name'] == name + '.mjo')
mjo = out / f'{name}.mjo'
mjo.write_bytes(raw[entry['offset']:entry['offset'] + entry['size']])
disassemble_script(str(mjo), read_script(str(mjo)), str(out / f'{name}.mjil'), options=ILFormat.DEFAULT)
print(out / f'{name}.mjil')
