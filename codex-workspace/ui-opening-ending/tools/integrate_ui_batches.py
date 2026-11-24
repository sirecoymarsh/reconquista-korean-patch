"""Integrate verified isolated raster batches into a fresh versioned UI trial."""
from pathlib import Path
import argparse,json,sys,shutil,re,datetime
U=Path(__file__).resolve().parents[1];B=U.parent;sys.path.insert(0,str(B/'tools'));from inspect_majiro import Arc,sha
ap=argparse.ArgumentParser();ap.add_argument('--base',required=True);ap.add_argument('--out',required=True);ap.add_argument('--batch',action='append',required=True);ap.add_argument('--remaining-percent',type=int,required=True);args=ap.parse_args()
assert all(re.fullmatch(r'[a-z0-9-]+',n) for n in [args.base,args.out]+args.batch)
base=U/'candidates'/args.base;out=U/'candidates'/args.out;assert not out.exists(),'Never overwrite a prior candidate'
m=json.loads((base/'manifest.json').read_text(encoding='utf-8-sig'));fr=next(x for x in m['archives'] if x['archive']=='fastdata.arc');sr=next(x for x in m['archives'] if x['archive']=='scenario.arc');a=Arc(base/'fastdata.arc');raw=a.path.read_bytes();assert sha(raw)==fr['output_sha256'];payload={e['name']:raw[e['offset']:e['offset']+e['size']] for e in a.entries};before=dict(payload);new={};labels=0
for n in args.batch:
 folder=U/'candidates'/n;bm=json.loads((folder/'manifest.json').read_text(encoding='utf-8-sig'));assert bm['structural_pass'] and bm['visual_pass'];labels+=bm['semantic_labels']
 actual={p.name:p.read_bytes() for p in (folder/'payloads').iterdir() if p.is_file()};assert set(actual)==set(bm['output_hashes'])
 for entry,data in actual.items():
  assert entry in payload and entry not in new and entry.endswith(('.rct','.rc8'));assert sha(data)==bm['output_hashes'][entry];payload[entry]=data;new[entry]=data
 assert '../'+n+'/manifest.json' not in m['raster_manifests'];m['raster_manifests'].append('../'+n+'/manifest.json')
assert {n for n in payload if payload[n]!=before[n]}==set(new)
out.mkdir();shutil.copytree(base/'font',out/'font');shutil.copytree(base/'payloads',out/'payloads');scenario=(base/'scenario.arc').read_bytes();assert sha(scenario)==sr['output_sha256'];(out/'scenario.arc').write_bytes(scenario);assert sha((out/'scenario.arc').read_bytes())==sr['output_sha256']
blob=a.rebuild(payload);(out/'fastdata.arc').write_bytes(blob);check=Arc(out/'fastdata.arc');assert [(e['name'],e['hash']) for e in a.entries]==[(e['name'],e['hash']) for e in check.entries];assert all(blob[e['offset']:e['offset']+e['size']]==payload[e['name']] for e in check.entries)
for n,b in new.items():(out/'payloads/fastdata.arc'/n).write_bytes(b)
changes={x['entry']:x for x in fr['changed']}
for n,b in new.items():changes[n]={'entry':n,'source_sha256':sha((B/'research/extracted/fastdata'/n).read_bytes()),'output_sha256':sha(b)}
fr.update(output_sha256=sha(blob),changed=list(changes.values()));m.update(inherits_static_evidence='../'+args.base+'/manifest.json',new_payloads_exactly=sorted(new),raster_entries=sum(n.endswith('.rct') for n in changes),raster_mask_entries_changed=sum(n.endswith('.rc8') for n in changes),raster_semantic_labels=m['raster_semantic_labels']+labels)
(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=U/'progress.json';g=json.loads(p.read_text(encoding='utf-8-sig'));g.update(phase='ui_headless_authoring',updated_local=datetime.datetime.now().astimezone().isoformat(),current_integrated_candidate='candidates/'+args.out);g['completed'].append(f'{args.out}: exact {len(new)} new payloads from '+', '.join(args.batch)+f'; {labels} new raster label instances');g['current_counts'].update(raster_entries_integrated=m['raster_entries'],mask_entries_integrated=m['raster_mask_entries_changed'],raster_labels_integrated=m['raster_semantic_labels']);g['usage_checkpoint']={'remaining_percent':args.remaining_percent,'limit_id':'codex','stop_marker_present':False,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};g['artifacts']+=['candidates/'+n+'/manifest.json' for n in args.batch+[args.out]];g['next_action']='Continue remaining raster UI: config, save/load, menu/console, nameplates, CG/recollection/music/history/chronicle; audit timeline CSV and native remaining surfaces; then OP/ED. Reuse all passed batches and private-desktop v5 modal proof.';p.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'out':str(out),'new_payloads':len(new),'total_raster_entries':m['raster_entries'],'total_mask_entries':m['raster_mask_entries_changed'],'total_raster_labels':m['raster_semantic_labels'],'fastdata_sha256':sha(blob)},ensure_ascii=False))
