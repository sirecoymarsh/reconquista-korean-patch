import json,sys,collections,re
from pathlib import Path
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
BASE=Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\api-carbon-argon-20261117')
RV=BASE/'results_reviewed_20261121'
def load_fields(p=None):
    p=p or BASE/'results_complete'/'검수반영_번역필드.jsonl'
    return [json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
def load_v20():
    return json.loads((RV/'work'/'v20_text.json').read_text(encoding='utf-8'))
KANA=re.compile(r'[\u3041-\u3096\u30a1-\u30fa\u31f0-\u31ff\uff66-\uff9f]')
HAN=re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')
HANGUL=re.compile(r'[\uac00-\ud7a3]')
