"""Offscreen GDI and bounded native branch checks for the large-text delta."""
import sys,json,ctypes as C,ctypes.wintypes as W,math,struct
from pathlib import Path
from PIL import Image,ImageChops
import numpy as np,pefile
import check_gdi_font as g
from inspect_majiro import sha,dump
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EIP
R=Path(__file__).resolve().parents[1];B=R/'builds/body-ui-20261023-v8';O=R/'candidates/large-text-v1'
M=json.loads((B/'font-map.json').read_text('utf-8'))['mapping'];glyphs=''.join(sorted(M));G=g.G
class SIZE(C.Structure):_fields_=[('cx',W.LONG),('cy',W.LONG)]
G.GetTextExtentPoint32W.argtypes=[W.HDC,W.LPCWSTR,C.c_int,C.POINTER(SIZE)];G.GetTextExtentPoint32W.restype=W.BOOL
rows=[];comparison=[]
for file,family in [('ReconquistaKR.otf','Reconquista KR Large1'),('ReconquistaKRSerif.otf','Reconquista KR Large Serif1')]:
 p=O/'font'/file;assert G.AddFontResourceExW(str(p),0x10,None)>0
 try:
  for height,width in [(23,11),(19,9)]:
   for scale in [1,4]:
    h=height*scale;w=width*scale+(scale//2 if height%2 else 0);dc=G.CreateCompatibleDC(None)
    f=G.CreateFontW(h,w,0,0,400,0,0,0,1,0,0,3,0,family);prevf=G.SelectObject(dc,f)
    face=C.create_unicode_buffer(128);G.GetTextFaceW(dc,128,face);assert face.value==family
    step=32*scale;cols=35;ww=cols*step;hh=math.ceil(len(glyphs)/cols)*step
    info=g.BMI();info.header=g.BIH(C.sizeof(g.BIH),ww,-hh,1,32,0,0,0,0,0,0);bits=C.c_void_p()
    bm=G.CreateDIBSection(dc,C.byref(info),0,C.byref(bits),None,0);prevbm=G.SelectObject(dc,bm);assert bits.value
    G.SetBkMode(dc,1);G.SetTextColor(dc,0)
    outputs=[]
    for ansi in [False,True]:
     C.memset(bits,255,ww*hh*4)
     for j,ch in enumerate(glyphs):
      x=(j%cols)*step+4*scale;y=(j//cols)*step+3*scale
      if ansi:
       enc=M[ch].encode('cp932');assert G.TextOutA(dc,x,y,enc,len(enc))
      else:assert G.TextOutW(dc,x,y,ch,1)
     G.GdiFlush();outputs.append(C.string_at(bits,ww*hh*4))
    assert outputs[0]==outputs[1],(file,height,scale)
    ar=np.frombuffer(outputs[0],dtype=np.uint8).reshape(hh,ww,4)[:,:,:3];missing=[];touch=[]
    for j,ch in enumerate(glyphs):
     cell=ar[(j//cols)*step:(j//cols+1)*step,(j%cols)*step:(j%cols+1)*step];ink=np.any(cell<240,axis=2)
     if not ink.any():missing.append(ch);continue
     yy,xx=np.nonzero(ink)
     if yy.min()<=0 or xx.min()<=0 or yy.max()>=step-1 or xx.max()>=step-1:touch.append(ch)
    assert not missing and not touch,(file,height,scale,missing,touch)
    sample='가나다라마바사아';sz=SIZE();assert G.GetTextExtentPoint32W(dc,sample,len(sample),C.byref(sz))
    rows.append({'family':family,'height':height,'width':width,'scale':scale,'actual_request':[h,w],'hangul_glyphs':len(glyphs),'mapped_ANSI_equals_Unicode':True,'missing':0,'cell_edge_contact':0,'sample_advance':sz.cx/scale,'sample_cell_height':sz.cy/scale,'pixels_sha256':sha(outputs[0])})
    G.SelectObject(dc,prevbm);G.DeleteObject(bm);G.SelectObject(dc,prevf);G.DeleteObject(f);G.DeleteDC(dc)
 finally:G.RemoveFontResourceExW(str(p),0x10,None)
# Same exact game GDI request: render a short body line for visual evidence at 4x then downsample.
for p,family in [(B/'font/ReconquistaKR.otf','Reconquista KR d00b8d76'),(O/'font/ReconquistaKR.otf','Reconquista KR Large1')]:
 assert G.AddFontResourceExW(str(p),0x10,None)>0
 dc=G.CreateCompatibleDC(None);f=G.CreateFontW(92,46,0,0,400,0,0,0,1,0,0,3,0,family);pf=G.SelectObject(dc,f)
 ww,hh=2800,160;info=g.BMI();info.header=g.BIH(C.sizeof(g.BIH),ww,-hh,1,32,0,0,0,0,0,0);bits=C.c_void_p();bm=G.CreateDIBSection(dc,C.byref(info),0,C.byref(bits),None,0);pb=G.SelectObject(dc,bm);C.memset(bits,255,ww*hh*4);G.SetBkMode(dc,1);G.SetTextColor(dc,0)
 sample='드디어 만났네. 마키노 모미지, 쿠레하.';G.TextOutW(dc,20,16,sample,len(sample));G.GdiFlush();im=Image.frombytes('RGB',(ww,hh),C.string_at(bits,ww*hh*4),'raw','BGRX');bbox=ImageChops.difference(im,Image.new('RGB',im.size,'white')).getbbox();comparison.append({'family':family,'ink_height_logical':(bbox[3]-bbox[1])/4,'ink_width_logical':(bbox[2]-bbox[0])/4,'image':im.resize((700,40),Image.Resampling.LANCZOS)})
 G.SelectObject(dc,pb);G.DeleteObject(bm);G.SelectObject(dc,pf);G.DeleteObject(f);G.DeleteDC(dc);G.RemoveFontResourceExW(str(p),0x10,None)
canvas=Image.new('RGB',(700,80),'white')
for j,c in enumerate(comparison):canvas.paste(c.pop('image'),(0,j*40))
canvas.save(O/'font-comparison.png')
# Execute only the changed native overflow guard using a mocked event dispatcher; no game process is launched.
blob=(O/'payloads/レコンキスタ.exe').read_bytes();pe=pefile.PE(data=blob);base=pe.OPTIONAL_HEADER.ImageBase;native=[]
for y,expected in [(0,False),(66,False),(71,False),(72,True),(99,True),(300,True)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(base,0x200000);u.mem_write(base,pe.get_memory_mapped_image());u.mem_map(0x800000,0x10000);sp=0x808000;u.reg_write(UC_X86_REG_ESP,sp)
 def put(at,val):u.mem_write(at,struct.pack('<I',val))
 put(0x495f7c,94);put(0x495f48,23);put(0x495f74,0);put(0x495f6c,y);put(0x495f70,38);put(0x56e1a4,0x56f000);put(0x56f000,1000);put(sp+0x660,4)
 events=[]
 def hook(uc,address,size,data):
  if address in [0x420f50,0x409460]:
   esp=uc.reg_read(UC_X86_REG_ESP)
   if address==0x409460:events.append(struct.unpack('<III',uc.mem_read(esp+4,12)))
   ret=struct.unpack('<I',uc.mem_read(esp,4))[0];uc.reg_write(UC_X86_REG_ESP,esp+4);uc.reg_write(UC_X86_REG_EIP,ret)
  elif address in [0x4165e0,0x4165f0]:uc.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x416582,0,count=100)
 assert bool(events)==expected and (not expected or events==[(0x53fb8d90,0,0)])
 native.append({'y':y,'height':94,'font_height':23,'overflow':expected,'events':[list(e) for e in events]})
report={'scope':'Offscreen GDI and isolated native branch emulation, not real game playback','gdi':rows,'comparison':comparison,'native_guard':native,'native_callbacks_mocked':True,'pass':True,'game_executed':False}
dump(O/'verification.json',report);print(json.dumps(report,ensure_ascii=False))
