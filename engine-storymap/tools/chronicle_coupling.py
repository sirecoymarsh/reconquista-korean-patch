"""How much of the game leans on the 연표 script (the user, 10-26: 「게임에서 의존하는 함수가 얼마나 많아?」, before a
native replacement): the functions chronicle.mjo defines, every call into them from the other scripts (by function and by
script), and the global variables it shares with them. Read-only on build/scenario.arc.
python chronicle_coupling.py   -> build/chronicle-coupling.json and a summary on stdout
"""
import collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_runtime as M

core = M.core
arc = core.Arc(M.BUILD / 'scenario.arc')
raw = arc.path.read_bytes()
scripts = {}
for e in arc.entries:
    if e['name'].lower().endswith('.mjo'):
        s, _ = core.b.decode(raw[e['offset']:e['offset'] + e['size']])
        scripts[e['name']] = s
chron = scripts['chronicle.mjo']


def fname(h):
    """a name for a hash where the decoder knows one"""
    try:
        for x in chron.instructions:
            if x.hash == h:
                k = x.check_known_hash() if callable(getattr(x, 'check_known_hash', None)) else None
                if k:
                    return str(k)
    except Exception:
        pass
    return None


funcs = {}
for f in chron.functions:
    funcs[f.name_hash] = {'hash': f'{f.name_hash:08x}', 'offset': f.offset}
calls = collections.defaultdict(lambda: collections.Counter())
for name, s in scripts.items():
    if name == 'chronicle.mjo':
        continue
    for x in s.instructions:
        if x.is_call:
            if x.hash in funcs:
                calls[x.hash][name] += 1


def globals_of(s):
    out = collections.Counter()
    for x in s.instructions:
        if (x.is_load or x.is_store) and x.hash:
            scope = {'0': 'persistent#', '1': 'savefile@', '2': 'thread%'}.get(str(int(x.flags.scope)))   # mjotool MjoScope; 3 is local
            if scope:
                out[(x.hash, scope, 'store' if x.is_store else 'load')] += 1
    return out


cg = globals_of(chron)
chron_vars = {h for h, _, _ in cg}
shared = collections.defaultdict(lambda: collections.Counter())
for name, s in scripts.items():
    if name == 'chronicle.mjo':
        continue
    for (h, scope, kind), n in globals_of(s).items():
        if h in chron_vars:
            shared[(h, scope)][(name, kind)] += n
report = {
    'scripts': len(scripts),
    'chronicle_functions': len(funcs),
    'called_from_outside': [{'hash': f'{h:08x}', 'calls': sum(c.values()), 'scripts': len(c), 'by_script': dict(c.most_common(8))} for h, c in sorted(calls.items(), key=lambda kv: -sum(kv[1].values()))],
    'shared_globals': [{'hash': f'{h:08x}', 'scope': scope, 'chronicle_uses': {k: n for (hh, sc, k), n in cg.items() if hh == h},
                        'others': {f'{nm}:{k}': n for (nm, k), n in c.most_common(10)}} for (h, scope), c in shared.items()],
    'chronicle_globals': len(chron_vars),
}
(M.BUILD / 'chronicle-coupling.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', 'utf-8')
print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in report.items()}, ensure_ascii=False))
for c in report['called_from_outside']:
    print('call', c['hash'], c['calls'], 'calls from', c['scripts'], 'scripts', list(c['by_script'])[:5])
for g in report['shared_globals']:
    print('global', g['hash'], g['scope'], g['chronicle_uses'], list(g['others'].items())[:4])
