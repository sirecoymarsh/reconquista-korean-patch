from pathlib import Path
import sys,json,collections,numpy as np,cv2
U=Path.cwd().resolve();sys.path.insert(0,str(U/'tools'));from decode_ui import decode,sha
cv2.setNumThreads(2)
def rgba(stem):
 rgb=np.asarray(decode(stem+'.rct')[0]);alpha=255-np.asarray(decode(stem+'_.rc8')[0].convert('RGB'))[:,:,0];return np.dstack([rgb,alpha])
s=rgba('バックログ画面');t=rgba('サウンドモード_off');on=rgba('サウンドモード_on');push=rgba('サウンドモード_push');x,y,w,h=35,460,485,108;dx,dy=17,-19;src=s[y:y+h,x:x+w];dst=t[y+dy:y+dy+h,x+dx:x+dx+w];covered=((on[:,:,3]>0)|(push[:,:,3]>0)).astype('uint8');results=[]
for radius in [0,1,2]:
 mask=cv2.dilate(covered,np.ones((2*radius+1,2*radius+1),np.uint8)) if radius else covered;known=mask[y+dy:y+dy+h,x+dx:x+dx+w]==0;lut=collections.defaultdict(collections.Counter)
 for a,b in zip(src[known],dst[known]):lut[tuple(map(int,a))][tuple(map(int,b))]+=1
 fullcodes={tuple(map(int,a)) for a in src.reshape(-1,4)};ambig={k:v for k,v in lut.items() if len(v)>1};bad=sum(sum(v.values())-max(v.values()) for v in ambig.values());missing=fullcodes-set(lut);results.append({'excluded_glow_dilation_radius':radius,'unoccluded_pixel_count':int(known.sum()),'source_rgba_codes_total':len(fullcodes),'observed_mapping_codes':len(lut),'ambiguous_source_codes':len(ambig),'minority_mapping_pixels':bad,'missing_source_codes':list(missing),'ambiguous_examples':[{'source_rgba':k,'targets':v.most_common(8)} for k,v in list(ambig.items())[:12]],'accepted':not ambig and not missing})
out={'source':'バックログ画面.rct + alpha','target':'サウンドモード_off.rct + alpha','source_roi':[x,y,w,h],'shift':[dx,dy],'new_method':'Whole brand/quote region calibration, excluding source song ink and glow using union of original on/push alpha masks. Previous prefix study was contaminated by neighboring song pixels.','results':results,'asset_modified':False,'accepted':any(r['accepted'] for r in results)};(U/'reports/music-brand-masked-calibration.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
