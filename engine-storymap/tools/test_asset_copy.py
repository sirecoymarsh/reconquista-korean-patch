"""The layer's own picture check (probe mode 1, no story map): 13 pictures are loaded and each is copied whole onto a fresh
bitmap; the two 4x copies must be byte-identical. This runs the picture load and a Copy over a whole new bitmap, the two
paths that take a shadow blank. Numbers only, nothing captured. python test_asset_copy.py
"""
import qa

g = qa.Game(extra_env={'RECON_HD_PROBE': '1', 'RECON_FLOW_PROBE': None})
error = None
try:
    g.until(lambda: g.count('probe asset_copy') >= 13, 180, 'asset copies')
except Exception as e:  # noqa: BLE001
    error = repr(e)
finally:
    ok = g.close_normally()
lines = [l for l in g.log().splitlines() if l.startswith('probe asset_copy') or 'shadow_limit' in l or 'asset error' in l]
print('\n'.join(lines))
print('pass', sum(l.endswith('PASS') for l in lines), 'of', sum(l.startswith('probe asset_copy') for l in lines), 'normal_exit', ok, 'error', error)
