from pathlib import Path
import os,sys,json,time,argparse
U=Path.cwd();assert not Path(r'C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json').exists()
PK=Path(r'P:\AI\Codex\projects\sorairo_no_fuukin_ko\work\ui_video_integration_20260922\opening_final');sys.path.insert(0,str(PK/'stt_pkgs'))
DLL=Path(r'P:\AI\forge\venv\Lib\site-packages\torch\lib');handle=os.add_dll_directory(str(DLL));os.environ['PATH']=str(DLL)+os.pathsep+os.environ['PATH']
for k,v in {'TEMP':U/'tmp','TMP':U/'tmp','HF_HOME':U/'transcription_work/cache/hf','XDG_CACHE_HOME':U/'transcription_work/cache','NUMBA_CACHE_DIR':U/'transcription_work/cache/numba','TORCH_HOME':U/'transcription_work/cache/torch'}.items():os.environ[k]=str(v);v.mkdir(parents=True,exist_ok=True)
os.environ['HF_HUB_OFFLINE']='1'
from faster_whisper import WhisperModel
ap=argparse.ArgumentParser();ap.add_argument('--model',choices=['small','large'],default='small');ap.add_argument('--ids',nargs='+',default=['op-movie','ed-original','op-isolated','ed-isolated']);a=ap.parse_args()
mp=PK/('models/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120' if a.model=='small' else 'models/models--Systran--faster-whisper-large-v3/snapshots/edaa852ec7e145841d8ffdb056a99866b5f0a478')
model=WhisperModel(str(mp),device='cuda',compute_type='float16',cpu_threads=4,num_workers=1,local_files_only=True)
files={'op-movie':'Recon_OP800_H-mono16k.wav','ed-original':'recon_ed-mono16k.wav','op-isolated':'recon_op-isolated-timeline.wav','ed-isolated':'recon_ed-isolated-timeline.wav'}
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
for sid in a.ids:
 assert not Path(r'C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json').exists();out=U/'transcription_work'/f'{sid}-{a.model}';assert not out.with_suffix('.json').exists();start=time.time();src=U/'transcription_work'/files[sid]
 segs,info=model.transcribe(str(src),language='ja',task='transcribe',beam_size=5,condition_on_previous_text=False,word_timestamps=True,vad_filter=False,temperature=0.0,initial_prompt='日本語の歌詞。')
 result=[]
 for s in segs:
  row={'id':f'{sid}::{len(result)+1:03d}','start':s.start,'end':s.end,'text':s.text,'avg_logprob':s.avg_logprob,'no_speech_prob':s.no_speech_prob,'words':[{'start':w.start,'end':w.end,'word':w.word,'probability':w.probability} for w in (s.words or [])]};result.append(row)
 data={'source':str(src),'stt_model':f'Systran/faster-whisper-{a.model if a.model=="small" else "large-v3"}','model_path':str(mp),'language':'ja','task':'source_transcription_only','accepted_semantic_translation':False,'source_duration':info.duration,'elapsed_seconds':time.time()-start,'segments':result}
 out.with_suffix('.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');out.with_suffix('.tsv').write_text('id\tstart\tend\ttext\n'+''.join(f'{x["id"]}\t{x["start"]:.3f}\t{x["end"]:.3f}\t{x["text"]}\n' for x in result),encoding='utf-8');out.with_suffix('.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(x["start"])} --> {stamp(x["end"])}\n{x["text"]}' for i,x in enumerate(result))+'\n',encoding='utf-8');print(json.dumps({'id':sid,'model':a.model,'segments':len(result),'elapsed_seconds':round(time.time()-start,1),'output':str(out.with_suffix('.json'))}),flush=True)
