"""Diagnostic only: start the installed MCP runtime with P: temporary storage; no Sky/UI call."""
import subprocess,os,json,time,threading,queue
from pathlib import Path
root=Path(__file__).resolve().parents[1];temp=root/'temp/node-repl-diagnostic';temp.mkdir(parents=True,exist_ok=True)
base=Path(r'C:\Users\CadriacLord\AppData\Local\OpenAI\Codex\runtimes\cua_node\2fbcd108736f9c20\bin')
env=os.environ.copy();env.update(TEMP=str(temp),TMP=str(temp),CODEX_HOME=r'P:\AI\Codex',NODE_REPL_NODE_PATH=str(base/'node.exe'),NODE_REPL_NODE_MODULE_DIRS=str(base/'node_modules'))
p=subprocess.Popen([str(base/'node_repl.exe')],cwd=root,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=0x08000000)
q=queue.Queue();threading.Thread(target=lambda:[q.put(x) for x in p.stdout],daemon=True).start()
def call(msg):
 p.stdin.write(json.dumps(msg)+'\n');p.stdin.flush();deadline=time.monotonic()+25
 while time.monotonic()<deadline:
  try:r=json.loads(q.get(timeout=max(.1,deadline-time.monotonic())))
  except queue.Empty:raise TimeoutError('MCP runtime response timeout')
  if r.get('id')==msg.get('id'):return r
try:
 r=call({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'local-path-diagnostic','version':'1'}}});print('initialize', 'result' in r)
 p.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized','params':{}})+'\n');p.stdin.flush()
 r=call({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'js','arguments':{'code':"nodeRepl.write('local kernel start succeeded')"}}});print(json.dumps(r,ensure_ascii=False));(root/'reports/node-repl-isolated-diagnostic.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
finally:
 p.terminate()
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:p.kill();p.wait()
