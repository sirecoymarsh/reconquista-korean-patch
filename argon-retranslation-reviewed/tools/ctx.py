# 사용: python ctx.py <unit 또는 field id> ... [-n 앞뒤행수]
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from common import *
T=json.load(open(RV/'work'/'table.json',encoding='utf-8')); byid={r['id']:r for r in T['rows']}; units=T['units']; order=T['order']
B=json.load(open(RV/'work'/'boundaries.json',encoding='utf-8'))
pos={k:i for i,k in enumerate(order)}
args=sys.argv[1:]; n=0
if '-n' in args: i=args.index('-n'); n=int(args[i+1]); del args[i:i+2]
for a in args:
    u = a if a in units else byid[a]['unit']
    i=pos[u]
    print('='*20,u)
    for k in order[max(0,i-n):i+n+1]:
        un=units[k]; bk=B.get(k,[])
        mark='>>' if k==u else '  '
        parts=[]
        for j,f in enumerate(un['fields']):
            r=byid.get(f)
            sep='' if j==0 else {'NL':' ⏎ ','INLINE':' ‖ ','PAGE':' ¶ '}.get(bk[j-1] if j-1<len(bk) else '?','?')
            if r is None: parts.append(sep+'[없음]'); continue
            parts.append(sep+f"{un['roles'][f]}{'*' if r['fixed'] else ''}:{r['ja']!r}=>{r['ko']!r}")
        mdl=byid[un['fields'][0]]['model'][:6] if un['fields'] and un['fields'][0] in byid else ''
        print(mark,k.split('::')[1],mdl,'sp=',un['sp'],''.join(parts))
        v=[byid[f]['v20'] for f in un['fields'] if f in byid and byid[f]['v20'] is not None]
        if v: print('      v20:',' ⏎ '.join(v))
