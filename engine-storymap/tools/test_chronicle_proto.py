"""The new 연표 prototype's bench (native/chronicle_proto.inc): runtime-test with RECON_CHRON_PROTO=bench; the prototype
opens over the title by itself, scrolls 10 s without waiting for the screen, and logs its frame costs.
python test_chronicle_proto.py [label] [runs] [bench|benchgpu]   -> qa/chron-proto-<label>.json
benchgpu draws on the graphics card into a picture off the screen (the hidden desktop gives the window path no card).
"""
import json, re, shutil, sys, time
import qa

label = sys.argv[1] if len(sys.argv) > 1 else 'now'
runs = int(sys.argv[2]) if len(sys.argv) > 2 else 1
mode = sys.argv[3] if len(sys.argv) > 3 else 'bench'
res = {'label': label, 'mode': mode, 'runs': []}
shot = qa.RUN / 'chron-proto-shot.png'   # benchgpu writes its last frame here
for i in range(runs):
    shot.unlink(missing_ok=True)
    g = qa.Game(extra_env={'RECON_CHRON_PROTO': mode, 'RECON_HD_START_FULLSCREEN': '1'})
    one = {}
    try:
        g.until(lambda: 'chron_proto bench' in g.log() or 'chron_proto open ok=0' in g.log(), 120, 'bench')
        time.sleep(1)
        log = g.log()
        one['open'] = [l for l in log.splitlines() if l.startswith('chron_proto open')][-1:]
        line = [l for l in log.splitlines() if l.startswith('chron_proto bench')][-1:]
        one['bench'] = line
        if line:
            one['values'] = {k: float(v) for k, v in re.findall(r'(\w+)=([\d.]+)', line[0])}
        one['problems'] = [l for l in log.splitlines() if 'recreate_target' in l][:3]
    except Exception as e:
        one['error'] = repr(e)
    finally:
        one['normal_exit'] = g.close_normally()
    if shot.exists():
        one['shot'] = str(shutil.copy2(shot, qa.QA / f'chron-proto-{label}-{i + 1}.png'))
    res['runs'].append(one)
    print(json.dumps(one, ensure_ascii=False), flush=True)
qa.dump(f'chron-proto-{label}.json', res)
