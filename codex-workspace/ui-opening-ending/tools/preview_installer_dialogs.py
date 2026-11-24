"""Render installer dialog templates on a non-input desktop without executing either EXE."""
from pathlib import Path
import json,os,re,time,ctypes as C
# Reuse audited private-desktop/capture definitions, excluding the argument parser and main action.
p=Path('tools/background_runtime_probe.py');prefix=p.read_text(encoding='utf-8').split('ap=argparse.ArgumentParser();',1)[0];assert 'ap=argparse.ArgumentParser()' not in prefix;exec(compile(prefix,'private_desktop_helpers','exec'))
E=U/'evidence/installer-dialogs';E.mkdir(exist_ok=True);NAME='ReconquistaInstallerUI_BG_01a162df';m=json.loads((U/'candidates/installer-ui-v1/manifest.json').read_bytes());targets=json.loads((U/'translation/installer-ui-ko.json').read_bytes());targets={r['id']:r['target'] for r in targets['records']};dll=C.WinDLL('comctl32',use_last_error=True)
class ICC(C.Structure):_fields_=[('size',W.DWORD),('flags',W.DWORD)]
init=api(dll,'InitCommonControlsEx',W.BOOL,[C.POINTER(ICC)]);check(init(C.byref(ICC(C.sizeof(ICC),0x20|0x80))))
module=api(kernel,'GetModuleHandleW',H,[W.LPCWSTR]);DP=C.WINFUNCTYPE(SSZ,W.HWND,W.UINT,SZ,SSZ)
@DP
def proc(h,msg,wp,lp):return 1 if msg==0x110 else 0
create=api(user,'CreateDialogIndirectParamW',W.HWND,[H,PTR,W.HWND,DP,SSZ]);show=api(user,'ShowWindow',W.BOOL,[W.HWND,C.c_int]);update=api(user,'UpdateWindow',W.BOOL,[W.HWND]);destroy=api(user,'DestroyWindow',W.BOOL,[W.HWND]);peek=api(user,'PeekMessageW',W.BOOL,[C.POINTER(W.MSG),W.HWND,W.UINT,W.UINT,W.UINT]);translate=api(user,'TranslateMessage',W.BOOL,[C.POINTER(W.MSG)]);dispatch=api(user,'DispatchMessageW',SSZ,[C.POINTER(W.MSG)]);send=api(user,'SendMessageW',SSZ,[W.HWND,W.UINT,SZ,SSZ]);getDC=api(user,'GetDC',H,[W.HWND]);releaseDC=api(user,'ReleaseDC',C.c_int,[W.HWND,H]);select=api(gdi,'SelectObject',H,[H,H]);drawtext=api(user,'DrawTextW',C.c_int,[H,W.LPCWSTR,C.c_int,C.POINTER(W.RECT),W.UINT])
def pump(seconds):
 end=time.monotonic()+seconds;msg=W.MSG()
 while time.monotonic()<end:
  while peek(C.byref(msg),None,0,0,1):translate(C.byref(msg));dispatch(C.byref(msg))
  time.sleep(.02)
before=foreground();original=getDesk(tid());assert before['input_desktop']!=NAME;sampler=FocusSampler();sampler.start();desktop=check(createDesk(NAME,None,None,0,0x1|0x2|0x40|0x80,None));result=[];live=[]
try:
 check(setDesk(desktop))
 for up in m['updates']:
  if up['file']!='setup.exe' or up['type']!=5:continue
  twin=next(v for v in m['updates'] if v['file']=='install.exe' and v['type']==5 and v['name']==up['name']);assert up['output_sha256']==twin['output_sha256'];path=U/'candidates/installer-ui-v1/resources'/f'setup.exe-{up["name"]}.bin';data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==up['output_sha256'];buf=C.create_string_buffer(data);hwnd=check(create(module(None),C.cast(buf,PTR),None,proc,0));live.append(hwnd);show(hwnd,4);update(hwnd);pump(.25);window=item(hwnd);cs=children(hwnd);layout=[]
  for ctrl in up['structure']['controls']:
   key=f'setup.exe::type5::{up["name"]}::{up["language"]}::control:{ctrl["id"]}:{ctrl["index"]}'
   if key not in targets:continue
   found=[c for c in cs if c['id']==ctrl['id'] and c['text']==targets[key]];assert len(found)==1,(key,cs);c=found[0];width,height=c['client'][2:];font=send(c['hwnd'],0x31,0,0);dc=check(getDC(c['hwnd']));old=select(dc,font) if font else None;button=c['class']=='Button';checktype=ctrl['style']&15;pad=22 if button and checktype in [2,3,5,6,9] else (12 if button else 0);s=targets[key].replace('&','');rr=W.RECT(0,0,max(1,width-pad),0);flags=0x400|(0x20 if button else 0x10);needed=drawtext(dc,s,len(s),C.byref(rr),flags)
   if old:select(dc,old)
   releaseDC(c['hwnd'],dc);fit=rr.right<=width-pad and needed<=height;layout.append({'id':key,'window_text_matches':True,'control_pixels':[width,height],'required_text_pixels':[rr.right,needed],'reserved_indicator_padding':pad,'fits':bool(fit)})
  cap=capture(window,'installer-'+up['name'].lower());result.append({'resource':up['name'],'template_sha256':up['output_sha256'],'reused_for_identical_install_exe_resource':True,'caption':window['text'],'window':window,'capture':cap,'layout':layout});check(destroy(hwnd));live.remove(hwnd);pump(.03)
finally:
 for hwnd in live:destroy(hwnd)
 check(setDesk(original));closeDesk(desktop);sample=sampler.finish(os.getpid())
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate':'installer-ui-v1','host_pid':os.getpid(),'installer_executed':False,'host_behavior':'CreateDialogIndirectParamW with inert Python callback; no installer initialization/commands/filesystem operation was invoked. All private-desktop windows destroyed.','input_before':before,'input_after':foreground(),'focus_sampler':sample,'dialog_count':len(result),'dialogs':result,'all_translated_control_text_matches':all(v['window_text_matches'] for r in result for v in r['layout']),'all_measured_text_fits':all(v['fits'] for r in result for v in r['layout']),'runtime_pass':False,'scope':'Native resource-layout proof only; real installer logic and dynamic text remain pending.'};(U/'reports/installer-ui-v1-native-layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'dialogs':len(result),'all_measured_text_fits':report['all_measured_text_fits'],'focus_samples':sample['samples'],'host_foreground':sample['game_became_foreground'],'private_input':sample['private_desktop_became_input'],'failures':[v for r in result for v in r['layout'] if not v['fits']],'captures':[r['capture']['path'] for r in result]},ensure_ascii=False))
