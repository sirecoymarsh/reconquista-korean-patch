from pathlib import Path
import sys,inspect,json
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));import build_trial as b
p=R/'tools/build_integrated.py';s=p.read_text(encoding='utf-8-sig')
start=s.index('NAMES=');end=s.index('\n',start)
s=s[:start]+"NAMES=json.loads((ROOT/'translation/integration/recovery-full-20261023-v1/names.json').read_text(encoding='utf-8'))['mapping']"+s[end:]
a=s.index('def integrate(label):');z=s.index('def main():',a)
fm=inspect.getsource(b.font_mapping).replace('def font_mapping(targets):','def isolated_font_mapping(targets,registry):').replace("    registry=ROOT/'translation/hangul-cp932-map.json'","    registry=Path(registry)")
s=s[:a]+fm+'\n'+s[z:]
s=s.replace('label=sys.argv[1];d=integrate(label)',"label=sys.argv[1];folder=ROOT/'translation/integration'/label;d=json.loads((folder/'integrated-targets.json').read_text(encoding='utf-8'));assert label=='recovery-full-20261023-v1';assert sha((folder/'integrated-targets.json').read_bytes())==json.loads((folder/'integration-report.json').read_text(encoding='utf-8'))['snapshot_sha256']")
s=s.replace("    mapping=b.font_mapping([r['target'] for r in d['records']+d['inline_records']]+list(NAMES.values()))","    shutil.copyfile(folder/'fontmap-seed.json',out/'font-map.json')\n    mapping=isolated_font_mapping([r['target'] for r in d['records']+d['inline_records']]+list(NAMES.values()),out/'font-map.json')")
s=s.replace("17403,17415,17427}}","17403,17415,17427}, 'テスト用.mjo':{1033,1045,1057}}")
needle="    dump(out/'manifest.json',manifest);dump(ROOT/'reports/latest-build.json',{'path':str(out),**manifest})"
replace="    manifest.update(font_map='font-map.json',font_map_sha256=sha((out/'font-map.json').read_bytes()),body_pending=d['pending_at_snapshot'],read_history_compatibility='Translated choice strings change their CRC read-history keys; old read/skip state may not transfer for choices. Saves and story branching untouched.');dump(out/'manifest.json',manifest);dump(ROOT/'reports/latest-recovery-build.json',{'path':str(out),**manifest})"
assert needle in s;s=s.replace(needle,replace)
s=s.replace('"""Build only a frozen, coordinator-reviewed + root-integrated snapshot."""','"""Build frozen recovery snapshot with isolated font registry; no mutation of worker snapshots."""')
(R/'tools/build_recovery_full.py').write_text(s,encoding='utf-8')
print('Created dedicated recovery builder; isolated font mapping and all19 audited serif consumers.')
