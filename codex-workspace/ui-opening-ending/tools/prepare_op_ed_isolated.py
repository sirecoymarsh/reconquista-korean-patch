from pathlib import Path
import importlib.util,json,numpy as np
U=Path.cwd();sp=importlib.util.spec_from_file_location('isolate',r'P:\AI\Codex\skills\audio-lyrics-transcription\scripts\isolate_vocals.py');mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod);rows=[]
for name in ['op','ed']:
 vocal=U/'transcription_work'/('recon_op_full-mono16k.wav' if name=='op' else 'recon_ed-mono16k.wav');inst=U/'transcription_work'/f'recon_{name}_inst-mono16k.wav';sr,v=mod.read_wav(vocal);si,i=mod.read_wav(inst);assert sr==si
 lag=mod.best_lag(v,i,sr,5.0);res,scale=mod.subtract(v,i,lag);start=max(lag,0);out=np.zeros_like(v);out[start:start+len(res)]=res;dst=U/'transcription_work'/f'recon_{name}-isolated-timeline.wav';assert not dst.exists();mod.write_wav(dst,sr,out)
 rows.append({'id':f'stream::recon_{name}','vocal':str(vocal),'instrumental':str(inst),'lag_samples':lag,'lag_seconds':lag/sr,'subtraction_scale':scale,'isolated':str(dst),'original_timeline_preserved':True,'method':'Read-only reuse of skill isolate_vocals.py best_lag and subtract, then pad back to original vocal timeline. Source recovery only, never accepted translation.'})
(U/'research/op-ed/vocal-isolation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(rows,ensure_ascii=False))
