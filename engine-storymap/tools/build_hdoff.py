"""Measurement-only DLL with the 4x layer switched off (never installed for play).

Copies native\ to build\hdoff\, patches three places so the engine draws and presents exactly as without the HD layer
(no shadows, no 4x loads, a 1:1 800x600 present at the viewport corner) and keeps the perf log, then builds it there.
python build_hdoff.py   -> build\hdoff\ReconquistaHD.dll
"""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'native'
OUT = ROOT / 'build' / 'hdoff'
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for p in SRC.iterdir():
    if p.suffix in ('.cpp', '.inc', '.h', '.json'):
        shutil.copy2(p, OUT / p.name)

cpp = OUT / 'ReconquistaHD.cpp'
s = cpp.read_text('utf-8')
edits = [
    # (10-26 spellings: Get took a blank flag, assets[] keeps the load result)
    ('static Shadow* Get(Bitmap* b,Box box,bool create,bool useMask=false,bool blank=false){',
     'static Shadow* Get(Bitmap* b,Box box,bool create,bool useMask=false,bool blank=false){return nullptr;'),
    ('w=MulDiv(dw,v.w,800),h=MulDiv(dh,v.h,600);',
     'w=MulDiv(dw,v.w,800),h=MulDiv(dh,v.h,600);x=v.x+dx;y=v.y+dy;w=dw;h=dh;'),
    ('if(Valid(b))assets[b]={n,fp,loaded};',
     'if(Valid(b))assets[b]={n,fp,loaded};if(Valid(b)&&logFile){fprintf(logFile,"asset %08x hdoff\\n",Key(n));fflush(logFile);}'),
]
for a, b in edits:
    assert s.count(a) == 1, (a, s.count(a))
    s = s.replace(a, b)
cpp.write_text(s, 'utf-8', newline='')

shutil.copy2(SRC / 'Build.cmd', OUT / 'Build.cmd')   # same compiler line; it builds in its own folder
r = subprocess.run(f'cmd /c "cd /d {OUT} && .\\Build.cmd"', cwd=OUT, capture_output=True, text=True, encoding='cp949', errors='replace')
log = r.stdout + r.stderr
(OUT / 'build.log').write_text(log, 'utf-8')
errors = [l for l in log.splitlines() if ' error ' in l]
print('exit', r.returncode, 'errors', len(errors), *errors[:5], sep='\n')
print(OUT / 'ReconquistaHD.dll', (OUT / 'ReconquistaHD.dll').exists())
