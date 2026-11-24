"""Summarize the Codex flowchart catalogue (read-only): chapters, groups, edges, choices, viewpoints."""
import json, collections, sys
from pathlib import Path

CAT = Path(r'P:\AI\Codex\projects\reconquista-ko\candidates\flowchart-v1\catalogue.json')
OUT = Path(__file__).resolve().parents[1] / 'ref' / 'catalogue_summary.json'

cat = json.loads(CAT.read_text('utf-8-sig'))
print('keys', list(cat))
print('counts', cat['counts'])
nodes = {n['id']: n for n in cat['nodes']}
rows = []
for ch in cat['chapters']:
    kinds = collections.Counter(nodes[i]['kind'] for i in ch['nodes'])
    rows.append({'id': ch['id'], 'group': ch['group'], 'label': ch['label'],
                 'pages': kinds.get('page', 0), 'choices': kinds.get('choice', 0),
                 'branches': kinds.get('branch', 0), 'views': kinds.get('view', 0)})
groups = collections.OrderedDict()
for r in rows:
    groups.setdefault(r['group'], []).append(r)
for g, rs in groups.items():
    print(f"\n[{g}] {len(rs)} chapters, pages={sum(r['pages'] for r in rs)}")
    for r in rs:
        print(f"  {r['id']:<28} {r['label']:<18} p={r['pages']:<5} c={r['choices']} b={r['branches']} v={r['views']}")
# chapter-level edges (dedupe)
edges = collections.OrderedDict()
for e in cat['edges']:
    edges.setdefault((e['from'], e['to']), 0)
    edges[(e['from'], e['to'])] += 1
print('\nedges', len(cat['edges']), 'unique', len(edges))
outdeg = collections.Counter(f for f, t in edges)
indeg = collections.Counter(t for f, t in edges)
for (f, t), c in edges.items():
    print(f"  {f} -> {t}" + (f" x{c}" if c > 1 else ''))
# choice / branch / view nodes in detail
print('\nchoice/branch/view nodes')
for n in cat['nodes']:
    if n['kind'] in ('choice', 'branch', 'view'):
        print(f"  {n['id']:<26} {n['kind']:<7} {n['label']:<22} {n['preview'][:40]!r} switch={n['switch']}")
OUT.write_text(json.dumps({'chapters': rows, 'edges': [{'from': f, 'to': t, 'count': c} for (f, t), c in edges.items()]},
                          ensure_ascii=False, indent=1), 'utf-8')
