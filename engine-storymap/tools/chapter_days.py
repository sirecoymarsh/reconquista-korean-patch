"""Day span of every catalogue chapter from the original day-transition plates (NNday.rct) in the disassembly.

start day = plate shown before the chapter's first text line, else the parent chapter's last day.
end day   = last plate inside the chapter, else start day.
Read-only; writes ref/chapter_days.json.
"""
import json, re
from pathlib import Path

DIS = Path(r'P:\AI\Codex\projects\reconquista-ko\research\disassembly')
REF = Path(__file__).resolve().parents[1] / 'ref'
summary = json.loads((REF / 'catalogue_summary.json').read_text('utf-8'))
chapters = [c['id'] for c in summary['chapters']]
parents = {}
for e in summary['edges']:
    parents.setdefault(e['to'], e['from'])

DAY = re.compile(r'ldstr\s+"(\d\d)day"')
TEXT = re.compile(r'^\s*[0-9a-f]+:\s+text\s')
events = {}
for ch in chapters:
    lines = (DIS / f'{ch}.mjo.mjil').read_text('utf-8').splitlines()
    first_text = next((i for i, l in enumerate(lines) if TEXT.match(l)), len(lines))
    plates = [(i, int(m.group(1))) for i, l in enumerate(lines) if (m := DAY.search(l))]
    events[ch] = {'first_text_line': first_text, 'plates': plates}

days = {}
def resolve(ch):
    if ch in days:
        return days[ch]
    ev = events[ch]
    before = [d for i, d in ev['plates'] if i < ev['first_text_line']]
    if before:
        start = before[-1]
    elif ch in parents:
        start = resolve(parents[ch])['end']
    else:
        start = None  # roots without plates (e.g. last_kako)
    end = ev['plates'][-1][1] if ev['plates'] else start
    days[ch] = {'start': start, 'end': end, 'plates': [d for _, d in ev['plates']]}
    return days[ch]

for ch in chapters:
    resolve(ch)
for ch in chapters:
    d = days[ch]
    print(f"{ch:<28} start={d['start']} end={d['end']} plates={d['plates']}")
(REF / 'chapter_days.json').write_text(json.dumps(days, ensure_ascii=False, indent=1), 'utf-8')
