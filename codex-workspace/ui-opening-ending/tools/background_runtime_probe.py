"""Private-desktop probe for Reconquista UI only. No desktop switching or global input."""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import json, os, sys, time, hashlib, datetime, argparse, threading
from PIL import Image
U=Path('P:/AI/Codex/projects/reconquista-ko/ui-opening-ending').resolve()
R=U/'runtime-ui-bg'; E=U/'evidence/background-runtime'; E.mkdir(exist_ok=True)
STATE=U/'reports/background-runtime-state.json'
NAME='ReconquistaUI_BG_01a162df'; EXE=R/'レコンキスタ.exe'
EXEHASH='f67195682944663b9546665eb3b63a639ace3f910e2ebf6ffaccda001d625b50'
user=C.WinDLL('user32',use_last_error=True); kernel=C.WinDLL('kernel32',use_last_error=True); gdi=C.WinDLL('gdi32',use_last_error=True)
H=W.HANDLE; PTR=C.c_void_p; SZ=C.c_size_t; SSZ=C.c_ssize_t
def api(lib,n,restype,args):
 f=getattr(lib,n);f.restype=restype;f.argtypes=args;return f
createDesk=api(user,'CreateDesktopW',H,[W.LPCWSTR,PTR,PTR,W.DWORD,W.DWORD,PTR])
openDesk=api(user,'OpenDesktopW',H,[W.LPCWSTR,W.DWORD,W.BOOL,W.DWORD])
openInput=api(user,'OpenInputDesktop',H,[W.DWORD,W.BOOL,W.DWORD])
closeDesk=api(user,'CloseDesktop',W.BOOL,[H])
setDesk=api(user,'SetThreadDesktop',W.BOOL,[H])
getDesk=api(user,'GetThreadDesktop',H,[W.DWORD])
objInfo=api(user,'GetUserObjectInformationW',W.BOOL,[H,C.c_int,PTR,W.DWORD,C.POINTER(W.DWORD)])
tid=api(kernel,'GetCurrentThreadId',W.DWORD,[])
getFG=api(user,'GetForegroundWindow',W.HWND,[])
getPid=api(user,'GetWindowThreadProcessId',W.DWORD,[W.HWND,C.POINTER(W.DWORD)])
getText=api(user,'GetWindowTextW',C.c_int,[W.HWND,W.LPWSTR,C.c_int])
getClass=api(user,'GetClassNameW',C.c_int,[W.HWND,W.LPWSTR,C.c_int])
getRect=api(user,'GetWindowRect',W.BOOL,[W.HWND,C.POINTER(W.RECT)])
getClient=api(user,'GetClientRect',W.BOOL,[W.HWND,C.POINTER(W.RECT)])
isVisible=api(user,'IsWindowVisible',W.BOOL,[W.HWND])
isEnabled=api(user,'IsWindowEnabled',W.BOOL,[W.HWND])
controlID=api(user,'GetDlgCtrlID',C.c_int,[W.HWND])
post=api(user,'PostMessageW',W.BOOL,[W.HWND,W.UINT,SZ,SSZ])
getMenu=api(user,'GetMenu',H,[W.HWND]); menuCount=api(user,'GetMenuItemCount',C.c_int,[H]); subMenu=api(user,'GetSubMenu',H,[H,C.c_int]); menuID=api(user,'GetMenuItemID',W.UINT,[H,C.c_int]);menuText=api(user,'GetMenuStringW',C.c_int,[H,W.UINT,W.LPWSTR,C.c_int,W.UINT])
openProcess=api(kernel,'OpenProcess',H,[W.DWORD,W.BOOL,W.DWORD]); closeHandle=api(kernel,'CloseHandle',W.BOOL,[H])
queryPath=api(kernel,'QueryFullProcessImageNameW',W.BOOL,[H,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)])
wait=api(kernel,'WaitForSingleObject',W.DWORD,[H,W.DWORD])
class STARTUPINFO(C.Structure):
 _fields_=[('cb',W.DWORD),('lpReserved',W.LPWSTR),('lpDesktop',W.LPWSTR),('lpTitle',W.LPWSTR),('dwX',W.DWORD),('dwY',W.DWORD),('dwXSize',W.DWORD),('dwYSize',W.DWORD),('dwXCountChars',W.DWORD),('dwYCountChars',W.DWORD),('dwFillAttribute',W.DWORD),('dwFlags',W.DWORD),('wShowWindow',W.WORD),('cbReserved2',W.WORD),('lpReserved2',PTR),('hStdInput',H),('hStdOutput',H),('hStdError',H)]
class PROCESSINFO(C.Structure):
 _fields_=[('hProcess',H),('hThread',H),('dwProcessId',W.DWORD),('dwThreadId',W.DWORD)]
createProcess=api(kernel,'CreateProcessW',W.BOOL,[W.LPCWSTR,W.LPWSTR,PTR,PTR,W.BOOL,W.DWORD,PTR,W.LPCWSTR,C.POINTER(STARTUPINFO),C.POINTER(PROCESSINFO)])
CB=C.WINFUNCTYPE(W.BOOL,W.HWND,SSZ)
enumDesk=api(user,'EnumDesktopWindows',W.BOOL,[H,CB,SSZ]); enumChildren=api(user,'EnumChildWindows',W.BOOL,[W.HWND,CB,SSZ])
def check(v):
 if not v:raise C.WinError(C.get_last_error())
 return v
def name(h):
 b=C.create_unicode_buffer(256);needed=W.DWORD();check(objInfo(h,2,b,C.sizeof(b),C.byref(needed)));return b.value
def input_name():
 h=check(openInput(0,False,1))
 try:return name(h)
 finally:closeDesk(h)
def pidof(w):
 n=W.DWORD();getPid(w,C.byref(n));return n.value
def foreground():
 w=getFG();return {'hwnd':int(w or 0),'pid':pidof(w) if w else 0,'input_desktop':input_name()}
class FocusSampler:
 def __init__(self):
  self.stop=threading.Event();self.events=[];self.samples=0;self.errors=[];self.thread=threading.Thread(target=self.run,daemon=True)
 def run(self):
  last=None
  while not self.stop.is_set():
   try:
    value=foreground();self.samples+=1
    if value!=last:self.events.append({'monotonic':time.monotonic(),**value});last=value
   except Exception as exc:self.errors.append(str(exc))
   self.stop.wait(.05)
 def start(self):self.thread.start()
 def finish(self,pid):
  self.stop.set();self.thread.join(timeout=2)
  return {'sample_interval_ms':50,'samples':self.samples,'events':self.events,'errors':self.errors,'game_became_foreground':any(e['pid']==pid for e in self.events),'private_desktop_became_input':any(e['input_desktop']==NAME for e in self.events),'continuous_monitor':False,'scope':'50 ms samples during this command; gaps between commands not monitored'}

def txt(f,h):
 b=C.create_unicode_buffer(4096);f(h,b,len(b));return b.value
def rect(f,h):
 b=W.RECT();check(f(h,C.byref(b)));return [b.left,b.top,b.right,b.bottom]
def item(h):
 return {'hwnd':int(h),'pid':pidof(h),'text':txt(getText,h),'class':txt(getClass,h),'id':controlID(h),'rect':rect(getRect,h),'client':rect(getClient,h),'visible':bool(isVisible(h)),'enabled':bool(isEnabled(h))}
def windows(d,pid):
 out=[]
 @CB
 def cb(h,_):
  if pidof(h)==pid and isVisible(h) and not txt(getClass,h).startswith(('UAC','IME','MSCTF')):out.append(item(h))
  return True
 C.set_last_error(0);ok=enumDesk(d,cb,0)
 if not ok and C.get_last_error()!=0:raise C.WinError(C.get_last_error())
 return out
def children(h):
 out=[]
 @CB
 def cb(w,_):
  out.append(item(w));return True
 enumChildren(h,cb,0);return out
def menus(h):
 out=[]
 def walk(m,path):
  for i in range(max(0,menuCount(m))):
   b=C.create_unicode_buffer(512);menuText(m,i,b,len(b),0x400);sub=subMenu(m,i)
   rec={'path':path+[i],'text':b.value,'id':int(menuID(m,i))}
   out.append(rec)
   if sub:walk(sub,path+[i])
 m=getMenu(h)
 if m:walk(m,[])
 return out
def process_path(pid):
 h=check(openProcess(0x1000|0x100000,False,pid))
 try:
  b=C.create_unicode_buffer(32768);n=W.DWORD(len(b));check(queryPath(h,0,b,C.byref(n)))
  assert Path(b.value).resolve()==EXE.resolve(),b.value
  assert wait(h,0)==258,'Process has exited'
  return b.value
 finally:closeHandle(h)
def capture(w,tag):
 # WM_PRINT-compatible GDI capture; may be black on unsupported renderers.
 getDC=api(user,'GetWindowDC',H,[W.HWND]);releaseDC=api(user,'ReleaseDC',C.c_int,[W.HWND,H])
 createDC=api(gdi,'CreateCompatibleDC',H,[H]);createBmp=api(gdi,'CreateCompatibleBitmap',H,[H,C.c_int,C.c_int]);select=api(gdi,'SelectObject',H,[H,H]);deleteObj=api(gdi,'DeleteObject',W.BOOL,[H]);deleteDC=api(gdi,'DeleteDC',W.BOOL,[H])
 printW=api(user,'PrintWindow',W.BOOL,[W.HWND,H,W.UINT])
 class BI(C.Structure):
  _fields_=[('size',W.DWORD),('width',W.LONG),('height',W.LONG),('planes',W.WORD),('bits',W.WORD),('compression',W.DWORD),('imagesize',W.DWORD),('xppm',W.LONG),('yppm',W.LONG),('used',W.DWORD),('important',W.DWORD)]
 getBits=api(gdi,'GetDIBits',C.c_int,[H,H,W.UINT,W.UINT,PTR,C.POINTER(BI),W.UINT])
 x,y,x2,y2=w['rect'];width=x2-x;height=y2-y
 assert 0<width<=8192 and 0<height<=8192
 dc=check(getDC(w['hwnd']));mem=check(createDC(dc));bmp=check(createBmp(dc,width,height));old=check(select(mem,bmp))
 try:
  ok=bool(printW(w['hwnd'],mem,2));select(mem,old)
  bi=BI(C.sizeof(BI),width,-height,1,32,0,0,0,0,0,0);buf=C.create_string_buffer(width*height*4);check(getBits(mem,bmp,0,height,buf,C.byref(bi),0))
  im=Image.frombytes('RGB',(width,height),buf.raw,'raw','BGRX')
  p=E/(tag+'-'+str(w['hwnd'])+'.png');im.save(p)
  return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'print_window_return':ok,'size':list(im.size),'extrema':im.getextrema()}
 finally:deleteObj(bmp);deleteDC(mem);releaseDC(w['hwnd'],dc)
def save(report,tag):
 p=E/(tag+'.json');p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'report':str(p),'state':report.get('state'),'windows':[{'hwnd':w['hwnd'],'text':w['text'],'class':w['class'],'children':[{'id':c['id'],'text':c['text'],'class':c['class']} for c in w['children']],'capture':w['capture']} for w in report.get('windows',[])],'input_desktop_unchanged':report.get('input_desktop_unchanged'),'foreground_unchanged':report.get('foreground_unchanged')},ensure_ascii=False))
ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['start','snapshot','command','control','mouse','hover','press','release','close']);ap.add_argument('--id',type=int);ap.add_argument('--hwnd',type=int);ap.add_argument('--x',type=int);ap.add_argument('--y',type=int);ap.add_argument('--tag',default='probe');args=ap.parse_args()
before=foreground();originalDesk=getDesk(tid());sampler=FocusSampler();sampler.start()
assert before['input_desktop']!=NAME,'Private desktop must never be input desktop'
rights=0x0001|0x0002|0x0040|0x0080 # Explicitly omits DESKTOP_SWITCHDESKTOP.
d=check(createDesk(NAME,None,None,0,rights,None) if args.mode=='start' else openDesk(NAME,0,False,rights))
report={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':args.mode,'desktop':NAME,'before':before,'forbidden_APIs_used':[],'global_input_used':False,'desktop_switch_called':False}
try:
 check(setDesk(d));assert name(getDesk(tid()))==NAME
 if args.mode=='start':
  assert hashlib.sha256(EXE.read_bytes()).hexdigest()==EXEHASH
  if STATE.exists():
   previous=json.loads(STATE.read_text(encoding='utf-8'));assert not windows(d,previous['pid']),'Previous probe is still running'
  si=STARTUPINFO();si.cb=C.sizeof(si);si.lpDesktop='WinSta0\\'+NAME;si.dwFlags=0x1|0x80;si.wShowWindow=4
  pi=PROCESSINFO();cmd=C.create_unicode_buffer('"'+str(EXE)+'"')
  check(createProcess(str(EXE),cmd,None,None,False,0x400,None,str(R),C.byref(si),C.byref(pi)))
  state={'pid':pi.dwProcessId,'exe':str(EXE),'exe_sha256':EXEHASH,'desktop':NAME,'runtime':str(R),'created_utc':report['time_utc']}
  STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');closeHandle(pi.hThread);closeHandle(pi.hProcess);time.sleep(8)
 else:state=json.loads(STATE.read_text(encoding='utf-8'))
 report['state']=state;process_path(state['pid'])
 ws=windows(d,state['pid'])
 if args.mode in ['command','control','mouse','hover','press','release','close']:
  matches=[w for w in ws if w['hwnd']==args.hwnd];assert len(matches)==1,ws;w=matches[0];assert w['enabled'],'Target window is disabled by a modal dialog; re-observe before input'
  if args.mode=='command':
   allowed=[m['id'] for m in menus(w['hwnd']) if m['id']!=0xffffffff];assert args.id in allowed and args.id not in [40002,40039], 'Fullscreen and physical joystick paths are excluded from background probe'
   check(post(w['hwnd'],0x111,args.id,0))
  elif args.mode=='control':
   cs=[c for c in children(w['hwnd']) if c['id']==args.id];assert len(cs)==1
   check(post(cs[0]['hwnd'],0xf5,0,0)) # BM_CLICK to an observed control only.
  elif args.mode in ['mouse','hover','press','release']:
   assert 0<=args.x<w['client'][2] and 0<=args.y<w['client'][3]
   xy=(args.y<<16)|args.x
   if args.mode in ['mouse','hover']:check(post(w['hwnd'],0x200,0,xy));time.sleep(.3)
   if args.mode in ['mouse','press']:check(post(w['hwnd'],0x201,1,xy));time.sleep(.12)
   if args.mode in ['mouse','release']:check(post(w['hwnd'],0x202,0,xy))
  else:check(post(w['hwnd'],0x10,0,0))
  time.sleep(1.5);ws=windows(d,state['pid'])
 report['windows']=[]
 for w in ws:
  w['children']=children(w['hwnd']);w['menus']=menus(w['hwnd']);w['capture']=capture(w,args.tag);report['windows'].append(w)
finally:
 check(setDesk(originalDesk));report['after']=foreground();report['input_desktop_unchanged']=report['before']['input_desktop']==report['after']['input_desktop'];report['foreground_unchanged']=report['before']['hwnd']==report['after']['hwnd'];closeDesk(d)
 report['focus_sampler']=sampler.finish(report.get('state',{}).get('pid',-1))
 save(report,args.tag)
