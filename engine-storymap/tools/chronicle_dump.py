"""chronicle.mjo as readable text, for the new 연표 (10-27): every instruction with its function, the Korean of the patch's
CP932 stand-ins put back (hangul-cp932-map.json), and the three CSVs as UTF-8. Read-only on build/scenario.arc.
python chronicle_dump.py [out_dir]   -> <out_dir>/chronicle.mjo.txt, <out_dir>/*.csv.txt (default F:/AI/reconquista-qa/chronicle-new)
Holds the whole 연표 text (spoilers): for Claude's reading only, never shown to the user.
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_runtime as M
import mjotool.known_hashes as K

core = M.core
MAP = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\translation\hangul-cp932-map.json')
BACK = {v: k for k, v in json.loads(MAP.read_text('utf-8'))['mapping'].items()}
KNOWN = {**K.VARIABLES, **K.FUNCTIONS, **K.SYSCALLS}   # hash -> name (syscalls last: they win where names clash)


def korean(s):
    s = ''.join(BACK.get(ch, ch) for ch in s)
    return re.sub(r'\$([0-9a-f]{8})\b', lambda m: KNOWN.get(int(m[1], 16), m[0]) + ('' if int(m[1], 16) not in KNOWN else f'<{m[1]}>'), s)


def entries():
    arc = core.Arc(M.BUILD / 'scenario.arc')
    raw = arc.path.read_bytes()
    return {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in arc.entries}


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    data = entries()
    s, _ = core.b.decode(data['chronicle.mjo'])
    starts = sorted((f.offset, f.name_hash) for f in s.functions)
    lines, cur = [], None
    for x in s.instructions:
        owner = max((p for p in starts if p[0] <= x.offset), default=(0, 0))[1]
        if owner != cur:
            cur = owner
            lines.append(f'\n===== function {owner:08x}')
        try:
            text = x.format_instruction()
        except Exception as e:
            text = f'{x.offset:05x}: {x.opcode.mnemonic} ?{e}'
        lines.append(korean(text))
    (out / 'chronicle.mjo.txt').write_text('\n'.join(lines), 'utf-8')
    for name in ('ホラー年表改.csv', 'exec_ホラー年表改.csv', 'alt_ホラー年表改.csv'):
        (out / (name + '.txt')).write_text(korean(data[name].decode('cp932', 'replace')), 'utf-8')
    print(len(s.instructions), 'instructions ->', out)


if __name__ == '__main__':
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r'F:\AI\reconquista-qa\chronicle-new'))
