"""ED lyric raster/thread candidate. Original movie, audio, dialogue and staff timing preserved."""
from pathlib import Path
import sys,struct,json,zlib,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'tools'),str(R/'ui-opening-ending/tools')]
import build_trial as b
from inspect_majiro import Arc,sha,dump
from raster_codec import raw_image,encode_array
C=R/'builds/ed-lyrics-overlay-v1';assert not C.exists();C.mkdir()
for d in ['payloads','preview','evidence']:(C/d).mkdir()
auth=json.loads((R/'ui-opening-ending/translation/op-ed-lyrics-ko.json').read_text(encoding='utf-8'));rows=[r for r in auth['records'] if r['song']=='ed'];assert len(rows)==32
assert all(r['translator_model']=='Codex internal' for r in rows)
assert all(0<=r['start']<r['end']<=240 for r in rows)
assert all(a['end']<=bb['start'] for a,bb in zip(rows,rows[1:]))
dump(C/'semantic-inputs.json',{'translator_model':'Codex internal','records':rows,'uncertain_source_words':[r for r in auth['uncertain_source_words'] if r['id'].startswith('ed-')],'source_sha256':sha((R/'ui-opening-ending/translation/op-ed-lyrics-ko.json').read_bytes()),'review':'existing 48 OP/ED lyric semantic review reused; recovered source and synchronization require user review'})
# Alpha follows the proven staffrolla palette: opacity = 255 - palette[index].
_,cp,_=raw_image((R/'research/extracted/fastdata/staffrolla.rct').read_bytes())
_,mp,_=raw_image((R/'research/extracted/fastdata/staffrolla_.rc8').read_bytes())
palette=np.frombuffer(mp[20:788],dtype='uint8').reshape(256,3);assert np.all(palette[:,0]==palette[:,1]) and np.all(palette[:,0]==palette[:,2]);inv=np.empty(256,dtype='uint8');inv[palette[:,0]]=np.arange(256,dtype='uint8')
W,H=800,38
cp=bytearray(cp);mp=bytearray(mp);struct.pack_into('<II',cp,8,W,H);struct.pack_into('<II',mp,8,W,H)
fontpath=R/'research/fonts/NotoSansCJKkr-Regular.otf';font=ImageFont.truetype(str(fontpath),22);assets={};stats=[]
for j,row in enumerate(rows,1):
 im=Image.new('RGBA',(W,H));dr=ImageDraw.Draw(im);box=dr.textbbox((0,0),row['target'],font=font,stroke_width=2);tw,th=box[2]-box[0],box[3]-box[1];assert tw<=760 and th<=34
 dr.text(((W-tw)//2-box[0],(H-th)//2-box[1]),row['target'],font=font,fill=(255,255,255,255),stroke_width=2,stroke_fill=(0,0,0,255))
 ar=np.asarray(im);ink=ar[:,:,3]>0;yy,xx=np.nonzero(ink);assert xx.min()>0 and xx.max()<799 and yy.min()>0 and yy.max()<37
 base=f'kr_ed_{j:03d}';rgb=ar[:,:,:3].copy();mask=inv[255-ar[:,:,3]]
 for name,arr,prefix,channels in [(base+'.rct',rgb,cp,3),(base+'_.rc8',mask,mp,1)]:
  data=encode_array(arr,prefix,channels);assets[name]=data;(C/'payloads'/name).write_bytes(data);back,_,_=raw_image(data);assert np.array_equal(back,arr)
 im.save(C/'preview'/(base+'.png'));stats.append({'id':row['id'],'target':row['target'],'start_ms':round(row['start']*1000),'end_ms':round(row['end']*1000),'asset':base,'ink_bbox':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'placement':[0,8,W,H],'font_px':22,'target_containment_pass':True})
# Small assembler whose branches are resolved in the final bytes then independently decoded.
class Code:
 def __init__(self):self.code=bytearray();self.labels={};self.fix=[]
 def add(self,v):self.code.extend(v);return self
 def op(self,n):return self.add(b.op(n))
 def i(self,v):return self.add(b.op('ldc.i')+struct.pack('<I',v&0xffffffff))
 def string(self,v):return self.add(b.string_ins('ldstr',v))
 def types(self,n,ts):return self.add(b.op(n)+struct.pack('<H',len(ts))+bytes(ts))
 def var(self,n,h,index=-1,flags=0x20):return self.add(b.op(n)+struct.pack('<HIh',flags,h,index))
 def sys(self,h,n,discard=True):return self.add(b.op('syscallp' if discard else 'syscall')+struct.pack('<IH',h,n))
 def call(self,h,n=0):return self.add(b.op('callp')+struct.pack('<IIH',h,0,n))
 def label(self,n):assert n not in self.labels;self.labels[n]=len(self.code);return self
 def jump(self,op,n):self.add(b.op(op));self.fix.append((len(self.code),n));return self.add(bytes(4))
 def finish(self):
  for at,n in self.fix:struct.pack_into('<i',self.code,at,self.labels[n]-(at+4))
  return bytes(self.code)
h=lambda s:zlib.crc32(s.encode('cp932'))
WORKER=h('$kr_ed_lyrics_worker@STAFFROLL');STOP=h('$kr_ed_lyrics_stop@STAFFROLL');TID=h('@kr_ed_lyrics_thread@STAFFROLL');SPR=h('_kr_ed_lyric_sprite@');START=h('_kr_ed_lyric_start@')
source=(R/'research/extracted/scenario/staffroll.mjo').read_bytes();assert sha(source)=='c7ea1a7f43f8042ea85a16ac830a6c9ea71d94f85248e9b3b4272c07a8b33a5d'
s,raw=b.decode(source)
# Reject hash aliases against every existing script's function/variable hash.
used=set()
for p in (R/'research/extracted/scenario').glob('*.mjo'):
 ss,_=b.decode(p.read_bytes());used.update(f.name_hash for f in ss.functions);used.update(i.hash for i in ss.instructions if i.opcode.encoding in ['fho','h0a','ha'])
assert not ({WORKER,STOP,TID,SPR,START}&used)
# Cleanup pattern follows existing yazlib's effect threads and staffroll's image fade thread.
c=Code().types('argcheck',[0]).types('alloca',[0])
c.i(0).var('st.i',SPR,0,0x60).op('pop')
c.jump('bsel.5','cleanup').jump('br','body').label('cleanup').op('bsel.clr')
c.var('ld',SPR,0,0x60).jump('brfalse','cleared').var('ld',SPR,0,0x60).sys(0x58b31737,1).label('cleared')
c.i(0).var('st.i',TID).op('pop').i(0).op('ret').label('body')
def guard(c):
 c.var('ld',0x451d3082).var('ld',START,-2,0x60).op('cne.i').jump('brtrue','cleanup')
def until(c,ms,label,high=False):
 c.label(label);guard(c)
 c.sys(0x6584f13e,0,False).var('ld',START,-2,0x60).op('sub.i').i(ms).op('cge.i').jump('brtrue',label+'_done')
 if high:c.var('ld',SPR,0,0x60).sys(0x4a02d664,1)
 c.i(-2).sys(0xcf35f0e3,1).jump('br',label).label(label+'_done')
for j,r in enumerate(stats):
 until(c,r['start_ms'],f'start{j}')
 # A lagging/loaded worker must never flash an already expired line.
 c.sys(0x6584f13e,0,False).var('ld',START,-2,0x60).op('sub.i').i(r['end_ms']).op('cge.i').jump('brtrue',f'skip{j}')
 c.string(r['asset']).sys(0xc2c3c4f4,1,False).var('st.i',SPR,0,0x60).op('pop')
 c.var('ld',SPR,0,0x60).jump('brfalse',f'skip{j}')
 c.i(8).i(0).var('ld',SPR,0,0x60).sys(0xe119d5ba,3)
 c.i(0).var('ld',SPR,0,0x60).sys(0xff7c52e6,2)
 until(c,r['end_ms'],f'end{j}',True)
 c.var('ld',SPR,0,0x60).sys(0x58b31737,1).i(0).var('st.i',SPR,0,0x60).op('pop').label(f'skip{j}')
c.jump('br','cleanup');worker=c.finish()
# Existing sprite_alfa_set uses 0=fully visible /255=invisible in the source fade thread.
st=Code().types('argcheck',[]).types('alloca',[]).var('ld',TID).jump('brfalse','done')
st.var('ld',TID).sys(0x4ef903f3,1)
st.i(-2).sys(0xcf35f0e3,1).i(-2).sys(0xcf35f0e3,1)
st.i(0).var('st.i',TID).op('pop').label('done').i(0).op('ret');stop=st.finish()
# Invoke exclusively for original ED filename. Preserve original timer/music instructions.
inj=Code().var('ld',0xa0da8eec,-2,0x260).string('recon_ed').op('ceq.s').jump('brfalse','done')
inj.call(STOP).var('ld',0x451d3082).i(WORKER).sys(0xf2f9daa8,2,False).var('st.i',TID).op('pop').label('done')
i_start=next(i for i,x in enumerate(s.instructions) if x.offset==0x658)
i_stop=next(i for i,x in enumerate(s.instructions) if x.offset==0x91d)
base,reloc=b.rewrite(source,insertions={i_start:inj.finish(),i_stop:Code().call(STOP).finish()})
ss,code=b.decode(base);funcs=[(f.name_hash,f.offset) for f in ss.functions]+[(WORKER,len(code)),(STOP,len(code)+len(worker))]
newcode=code+worker+stop
# Header retains original signature/main/line flags; table enlarged by exactly two functions.
head=base[:24]+struct.pack('<I',len(funcs))+b''.join(struct.pack('<II',a,o) for a,o in funcs)+struct.pack('<I',len(newcode))
new=head+(b.crypt32(newcode) if ss.signature==ss.SIGNATURE_ENCRYPTED else newcode)
ns,nraw=b.decode(new);assert nraw==newcode;assert [(f.name_hash,f.offset) for f in ns.functions]==funcs
bounds={i.offset for i in ns.instructions}|{len(newcode)}
for x in ns.instructions:
 if x.opcode.encoding=='j':assert x.offset+x.size+x.jump_offset in bounds
assert nraw[:len(code)]==code
(C/'payloads/staffroll.mjo').write_bytes(new)
(C/'evidence/staffroll-patched.mjil').write_text('\n'.join(x.format_instruction() for x in ns.instructions)+'\n',encoding='utf-8')
dump(C/'evidence/layout.json',stats)
dump(C/'manifest.json',{'translator_model':'Codex internal','scope':'ED lyric overlay candidate','script':{'entry':'staffroll.mjo','source_sha256':sha(source),'output_sha256':sha(new),'original_functions':len(s.functions),'output_functions':len(ns.functions),'injection_report':reloc,'new_functions':{'worker':f'{WORKER:08x}','stop':f'{STOP:08x}'},'thread_global':f'{TID:08x}','all_branches_resolve':True,'original_relocated_body_verbatim':True,'last_ep_and_audio_and_original_music_timer_unchanged':True},'assets':[{'entry':n,'sha256':sha(v),'size':[W,H]} for n,v in assets.items()],'labels':32,'placement':[0,8,W,H],'layout_containment_pass':True,'visual_review':False,'independent_technical_review':False,'runtime_verified':False,'runtime_verification':'deferred_to_user','source_uncertainty':['ed-lyrics::014 褪せた時 provisional'],'limits':['Old saves already inside ED do not start the new helper until replay/restart','Timing from existing source transcription, no native playback verification'],'engine_evidence':['original staffroll.mjo song helper 0x534ba641 captures timer before music; credits helper stops after c83ce4e0 returns','staffroll.mjo 0xc42 bsel.5 sprite release cleanup pattern','yazlib.mjo 0x641c thread_end plus two wait(-2) before continuing','pic.mjo 0x3fbb sprite_priority_high(1)']})
print(json.dumps({'candidate':str(C),'assets':len(assets),'labels':len(rows),'script_sha256':sha(new),'functions':len(ns.functions)},ensure_ascii=False))