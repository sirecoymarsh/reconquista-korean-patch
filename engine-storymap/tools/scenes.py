"""Group a chapter's catalogue pages into scenes by background changes ($disp_back@PIC), read-only.

usage: python scenes.py <chapter_id> [max_scenes_to_print]
Writes ref/scenes_<chapter>.json (scene -> bg, first page order, page count, first preview).
"""
import json, re, sys
from pathlib import Path

DIS = Path(r'P:\AI\Codex\projects\reconquista-ko\research\disassembly')
CAT = Path(r'P:\AI\Codex\projects\reconquista-ko\candidates\flowchart-v1\catalogue.json')
REF = Path(__file__).resolve().parents[1] / 'ref'

ch = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 999
lines = (DIS / f'{ch}.mjo.mjil').read_text('utf-8').splitlines()
INS = re.compile(r'^([0-9a-f]{5}):\s+(\S+)\s*(.*)$')
ins = [m for l in lines if (m := INS.match(l))]
bg_at = {}
for i, m in enumerate(ins):
    if m.group(2) == 'callp' and 'disp_back@PIC' in m.group(3):
        # nearest preceding ldstr is the background name
        for j in range(i - 1, max(-1, i - 4), -1):
            if ins[j].group(2) == 'ldstr':
                bg_at[i] = ins[j].group(3).strip('"')
                break
cat = json.loads(CAT.read_text('utf-8-sig'))
nodes = [n for n in cat['nodes'] if n['chapter'] == ch]
bg_points = sorted(bg_at)
# Scene break = a fade through black followed by a new picture; direct cuts and event CGs stay in the scene.
scenes, cur, faded, last_bg = [], None, True, None
k = 0
for n in nodes:
    new_after_fade = None
    while k < len(bg_points) and bg_points[k] <= n['index']:
        b = bg_at[bg_points[k]]
        if b in ('black', 'white', 'red'):
            faded = True
        else:
            if faded:
                new_after_fade = b
            faded = False
            last_bg = b
        k += 1
    if cur is None or new_after_fade is not None:
        cur = {'bg': last_bg, 'first_order': n['order'], 'first_id': n['id'], 'pages': 0, 'choices': 0, 'views': 0, 'first': ''}
        scenes.append(cur)
    if cur['bg'] is None or cur['bg'].startswith('ev'):
        if last_bg and not last_bg.startswith('ev'):
            cur['bg'] = last_bg
    if n['kind'] == 'page':
        cur['pages'] += 1
        if not cur['first']:
            cur['first'] = n['preview']
    elif n['kind'] == 'choice':
        cur['choices'] += 1
    elif n['kind'] == 'view':
        cur['views'] += 1
print(ch, 'scenes', len(scenes), 'pages', sum(s['pages'] for s in scenes))
for i, s in enumerate(scenes[:limit], 1):
    print(f"{i:3} {s['bg']!s:<14} p={s['pages']:<4} c={s['choices']} v={s['views']} | {s['first'][:60]}")
(REF / f'scenes_{ch}.json').write_text(json.dumps(scenes, ensure_ascii=False, indent=1), 'utf-8')
