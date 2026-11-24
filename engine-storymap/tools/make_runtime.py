"""Assemble a runtime folder for the 이야기 지도 build.

python make_runtime.py test   -> runtime-test   (muted: audio dispatches removed in its own scenario copy, volumes 0,
                                                 private registry key; private-desktop QA only)
python make_runtime.py play   -> runtime-play   (normal sound and settings, for the user)
python make_runtime.py chron  -> runtime-chron  (as test, but start.mjo opens the chronicle at once: chronicle QA)
python make_runtime.py proto  -> runtime-proto  (as test, with its own registry key: the user's own try of the new 연표
                                                 prototype on the real screen, started by 「연표 시제품 써 보기.cmd」)

Read-only game data (archives except scenario/fastdata, movies, fonts, 4x art) are hard links to Codex's current runtime
(GAME, v19 since 10-24 14:20): the game never writes them. savedata, cg-quality.ini and every file this build changes are
independent copies; savedata and cg-quality.ini (the player's CG·menu quality choice) are never overwritten once present.
"""
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

import codex_model as CM

core = CM.core
HERE = Path(__file__).resolve().parents[1]
BUILD = HERE / 'build'
GAME = CM.CODEX / 'runtime-body-ui-20261024-v19-menus-4k'
AUDIO = {0x0dc634c4, 0x26dc6566, 0x32d0236c, 0x4311cfa6, 0x4980f82c, 0x708b0256, 0x884949e0, 0x8e8167f2, 0x90d5298a, 0xa79731a2,
         0xb268f04f, 0xd011ff32, 0xde1e2ed0, 0xed84e320, 0xf62e3ca7, 0xf86fc950}   # Codex background.silence() set
LINKED = ['data.arc', 'data1.arc', 'data2.arc', 'slowdata.arc', 'voice.arc', 'stream.arc', 'レコンキスタ.exe']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def link_file(p, q):
    if q.exists() and os.path.samefile(p, q):
        return
    q.unlink(missing_ok=True)
    os.link(p, q)


def link_tree(src, dst):
    """Mirror src as hard links: files changed in a newer Codex build are relinked, files it dropped are removed."""
    dst.mkdir(parents=True, exist_ok=True)
    names = set()
    for p in src.iterdir():
        names.add(p.name)
        q = dst / p.name
        if p.is_dir():
            link_tree(p, q)
        else:
            link_file(p, q)
    for q in dst.iterdir():
        if q.name not in names:
            shutil.rmtree(q) if q.is_dir() else q.unlink()


def link_jxl(run):
    """JPEG XL copies of the 4x art (tools/convert_jxl.py) as hard links, like the PNGs; the DLL prefers a .jxl that is
    not older than its PNG. Only finished .jxl files are linked, so a conversion in progress leaves no partial file."""
    src = BUILD / 'hires-jxl'
    if not src.exists():
        return
    dst = run / 'hires-jxl'
    dst.mkdir(exist_ok=True)
    keep = {p.name for p in src.glob('*.jxl')}
    for name in keep:
        link_file(src / name, dst / name)
    for q in dst.iterdir():
        if q.name not in keep:
            q.unlink()


BLEND = True   # 10-25: the AI pictures from tools/blend_art.py (False: Codex's art as it is, e.g. to compare)


def link_blend(run):
    """The 1,758 AI pictures re-made by tools/blend_art.py (the AI art kept on drawn lines, the source elsewhere) are linked
    over their plain JPEG XL copies; a key not (yet) blended keeps its copy of Codex's art."""
    src = BUILD / 'hires-jxl-blend'
    if not BLEND or not src.exists():
        return 0
    n = 0
    for p in src.glob('*.jxl'):
        link_file(p, run / 'hires-jxl' / p.name)
        n += 1
    return n


# 4x art that is worse than the original it stands for: left out of every copy, so the engine keeps the original picture
# (scaled up as any picture without 4x art). 10-27 the sound mode's credit lines were here for an hour (Codex's 4K had set them
# again in a dark sans), until tools/credit_4k.py drew them at 4K the original's way (build/hires-text, link_fixed_art).
WORSE_ART = []
def drop_worse_art(run):
    """removes the runtime's links to WORSE_ART's 4x files (PNG and JPEG XL); returns how many keys and files"""
    man = json.loads((GAME / 'hires-manifest.json').read_text('utf-8'))
    keys = {e['file'].split('.')[0] for e in man['entries'] if e.get('name') in WORSE_ART and 'file' in e}
    files = 0
    for d in ('hires', 'hires-jxl'):
        for k in keys:
            for p in (run / d).glob(k + '.*'):
                p.unlink()   # the copy's own link only; Codex's file stays
                files += 1
    return len(keys), files
FIXED_ART = ['hires-tc01',   # tools/fix_tc01_art.py: TC01 pictures whose red Codex's art kept, laid over their base
             'hires-text']   # tools/credit_4k.py: the sound mode's credit lines drawn at 4K the original's way
def link_fixed_art(run):
    """the 4K art fixed here (FIXED_ART folders under build) linked over the copy's PNG, and any JPEG XL of the same key taken
    away so the DLL reads the fixed PNG; returns how many per folder"""
    counts = {}
    for folder in FIXED_ART:
        src = BUILD / folder
        n = 0
        for p in (src.glob('*.png') if src.exists() else []):
            link_file(p, run / 'hires' / p.name)
            (run / 'hires-jxl' / (p.stem + '.jxl')).unlink(missing_ok=True)
            n += 1
        counts[folder] = n
    return counts
REDRAW = True   # 10-25: Codex's checked cloud repairs, then its redrawn pictures, over the blend (tools/pack_redraw.py)


def link_over(run, folder):
    """build/<folder>/<key>.jxl linked over the runtime's JPEG XL copies; returns how many"""
    src = BUILD / folder
    if not REDRAW or not src.exists():
        return 0
    n = 0
    for p in src.glob('*.jxl'):
        link_file(p, run / 'hires-jxl' / p.name)
        n += 1
    return n


SPRITES = True   # 10-25 night: standing pictures, tools/sprite_build.py (build/sprites/hires-sprites.txt, the DLL's index)


def link_sprites(run):
    """the standing pictures' 4x: bases and masks over hires-jxl, the expressions' face patches in hires-patch, and the
    DLL's index beside the DLL; returns (bases and masks, patches). Without an index the runtime has none of them."""
    index = BUILD / 'sprites' / 'hires-sprites.txt'
    patches = run / 'hires-patch'
    if not SPRITES or not index.exists():
        (run / 'hires-sprites.txt').unlink(missing_ok=True)
        if patches.exists():
            shutil.rmtree(patches)
        return 0, 0
    art = 0
    for p in (BUILD / 'hires-jxl-sprites').glob('*.jxl'):
        link_file(p, run / 'hires-jxl' / p.name)
        art += 1
    patches.mkdir(exist_ok=True)
    names = set()
    for p in (BUILD / 'hires-patch-sprites').glob('*.jxl'):
        link_file(p, patches / p.name)
        names.add(p.name)
    for q in patches.iterdir():
        if q.name not in names:
            q.unlink()
    shutil.copy2(index, run / 'hires-sprites.txt')
    return art, len(names)


def silence_scenario(src, dst):
    a = core.Arc(src)
    raw = a.path.read_bytes()
    payload = {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}
    hits = 0
    for n, data in payload.items():
        if not n.endswith('.mjo'):
            continue
        s, _ = core.b.decode(data)
        repl = {i: core.b.op('pop') * x.argument_count for i, x in enumerate(s.instructions) if x.opcode.mnemonic == 'syscallp' and x.hash in AUDIO}
        if repl:
            hits += len(repl)
            payload[n] = core.rewrite(data, repl, {}, {})
    dst.unlink(missing_ok=True)
    dst.write_bytes(a.rebuild(payload))
    return hits


def chronicle_entry(src, dst):
    """QA copy whose start script opens the chronicle (extra-menu mode) at once, as Codex's ui-rest-v1/runtime_qa.py does."""
    a = core.Arc(src)
    raw = a.path.read_bytes()
    payload = {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}
    s, _ = core.b.decode(payload['start.mjo'])
    anchor = next(i for i, x in enumerate(s.instructions) if x.offset >= s.main_offset and x.opcode.mnemonic == 'alloca') + 1
    init = core.put(core.FAST, 0) + core.put(core.MARK, 4155) + core.const(1) + core.syscall(0x62374297, 1) + core.const(1) + core.call(0x62a65754, 1)
    payload['start.mjo'] = core.rewrite(payload['start.mjo'], {}, {anchor: init}, {})   # $screen_mode(1); chronicle(1)
    dst.unlink(missing_ok=True)
    dst.write_bytes(a.rebuild(payload))


def env_fastdata(src, dst, settings):
    a = core.Arc(src)
    raw = a.path.read_bytes()
    payload = {e['name']: raw[e['offset']:e['offset'] + e['size']] for e in a.entries}
    env = payload['majiro.env']
    for key, val in settings.items():
        env, count = re.subn(rb'(?m)^(' + key.encode() + rb'[ \t]+)[^ \t\r\n]+', lambda m: m[1] + val.encode(), env)
        assert count == 1, key
    payload['majiro.env'] = env
    dst.unlink(missing_ok=True)   # a copy's own file, never the shared one through a hard link
    dst.write_bytes(a.rebuild(payload))


def main(kind):
    run = HERE / ('runtime-' + kind)
    run.mkdir(exist_ok=True)
    for name in LINKED:
        link_file(GAME / name, run / name)
    for d in ['hires', 'movie', 'font']:
        link_tree(GAME / d, run / d)
    link_jxl(run)
    blended = link_blend(run)
    repaired, redrawn = link_over(run, 'hires-jxl-cloud'), link_over(run, 'hires-jxl-redraw')   # later wins: redraws over cloud repairs
    sprite_art, sprite_patches = link_sprites(run)
    worse_keys, worse_files = drop_worse_art(run)
    fixed_art = link_fixed_art(run)
    proto = run / 'chronicle-proto'   # the 10-26 prototype's pictures: gone with the real view
    if proto.exists():
        shutil.rmtree(proto)
    view = run / 'chronicle-new'      # the new 연표's pictures and letter table (tools/chronicle_assets.py): test copies only for now
    if kind in ('test', 'chron', 'proto') and (BUILD / 'chronicle-new').exists():
        link_tree(BUILD / 'chronicle-new', view)
    elif view.exists():
        shutil.rmtree(view)
    shutil.copy2(GAME / 'hires-manifest.json', run / 'hires-manifest.json')
    if not (run / 'cg-quality.ini').exists():
        shutil.copy2(GAME / 'cg-quality.ini', run / 'cg-quality.ini')
    if not (run / 'savedata').exists():
        shutil.copytree(GAME / 'savedata', run / 'savedata')
    shutil.copy2(HERE / 'native' / 'ReconquistaHD.dll', run / 'ReconquistaHD.dll')
    shutil.copy2(BUILD / 'storymap.bin', run / 'storymap.bin')
    if (BUILD / 'prefetch.bin').exists():
        shutil.copy2(BUILD / 'prefetch.bin', run / 'prefetch.bin')   # pictures read ahead (build_prefetch.py)
    if (run / 'storymap').exists():
        shutil.rmtree(run / 'storymap')
    shutil.copytree(BUILD / 'storymap', run / 'storymap')
    proof = {'kind': kind, 'game': GAME.name, 'dll_sha256': sha(run / 'ReconquistaHD.dll'), 'storymap_sha256': sha(run / 'storymap.bin')}
    proof['blended_art'] = blended   # AI pictures linked from build/hires-jxl-blend
    proof['cloud_repaired_art'], proof['redrawn_art'] = repaired, redrawn   # Codex's, from build/hires-jxl-cloud and -redraw
    proof['sprite_art'], proof['sprite_patches'] = sprite_art, sprite_patches   # standing pictures (tools/sprite_build.py)
    proof['worse_art_left_out'] = {'keys': worse_keys, 'files': worse_files}   # WORSE_ART: the original picture is shown
    proof['fixed_art'] = fixed_art   # FIXED_ART: 4K art fixed here, over Codex's
    mute_flag = run / 'storymap-se-mute.flag'                    # the DLL plays the map's sounds at -100 dB when present
    if kind in ('test', 'chron'):
        mute_flag.write_text('QA runtime: story map sounds are queued at volume 0 (-100 dB).\n', 'utf-8')
        source = BUILD / 'scenario.arc'
        if kind == 'chron':
            source = run / 'scenario.chronicle-entry'
            chronicle_entry(BUILD / 'scenario.arc', source)
        proof['audio_dispatches_removed'] = silence_scenario(source, run / 'scenario.arc')
        env_fastdata(GAME / 'fastdata.arc', run / 'fastdata.arc', {'REG_LOCAL': 'ReconquistaStoryMapTest20261024', 'MUSICVOL': '0', 'SOUNDVOL': '0', 'VOICEVOL': '0', 'ISPLAYMUSIC': '0'})
    else:
        mute_flag.unlink(missing_ok=True)
        (run / 'scenario.arc').unlink(missing_ok=True)   # never written through a hard link
        shutil.copy2(BUILD / 'scenario.arc', run / 'scenario.arc')
        if kind == 'proto':
            # the user's hand-try copy sounds as the play copy (10-27: silenced, the sound mode's tracks "ended" at once and it
            # skipped through them without end, 「음악 감상 모드가 깨지고 작동을 안하는데」); its settings stay under a key of its own
            env_fastdata(GAME / 'fastdata.arc', run / 'fastdata.arc', {'REG_LOCAL': 'ReconquistaChronProto20261027'})
        else:
            link_file(GAME / 'fastdata.arc', run / 'fastdata.arc')
    proof['scenario_sha256'] = sha(run / 'scenario.arc')
    (run / 'BUILD-IDENTITY.json').write_text(json.dumps(proof, ensure_ascii=False, indent=1), 'utf-8')
    print(json.dumps(proof, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'test')
