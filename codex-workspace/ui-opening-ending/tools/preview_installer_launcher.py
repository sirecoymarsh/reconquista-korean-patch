from pathlib import Path
import json,os,time,ctypes as C,struct,pefile
U=Path.cwd().resolve();assert not Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists()
s=(U/'tools/preview_installer_dialogs.py').read_text(encoding='utf-8-sig').split('before=foreground();',1)[0].replace('candidates/installer-ui-v1/manifest.json','candidates/installer-ui-v2/manifest.json');exec(compile(s,'inert_installer_host_helpers','exec'))
getACP=api(kernel,'GetACP',W.UINT,[]);acp=getACP();assert acp==949,('CP949 launcher default requires ACP949',acp)
setA=api(user,'SetDlgItemTextA',W.BOOL,[W.HWND,C.c_int,C.c_char_p]);getItem=api(user,'GetDlgItem',W.HWND,[W.HWND,C.c_int]);up=next(u for u in m['updates'] if u['file']=='setup.exe' and u['name']=='MAINDIALOG');data=(U/'candidates/installer-ui-v2/resources/setup.exe-MAINDIALOG.bin').read_bytes();assert hashlib.sha256(data).hexdigest()==up['output_sha256'];payload=(U/'candidates/installer-ui-v2/setup.exe').read_bytes();pe=pefile.PE(data=payload);off=pe.get_offset_from_rva(0x414128-pe.OPTIONAL_HEADER.ImageBase);ids=list(struct.unpack_from('<9I',payload,off));assert sorted(ids)==list(range(1000,1009));tr=json.loads((U/'translation/installer-launcher-ko.json').read_bytes());byva={r['va']:r for r in tr['records']}
scenarios=[('before-install',[0x414548,0x41452c,0x41450c]),('installed',[0x414548,0x41452c,0x4144f8,0x4144e4,0x4144d8])]
before=foreground();original=getDesk(tid());assert before['input_desktop']!=NAME;sampler=FocusSampler();sampler.start();desktop=check(createDesk(NAME,None,None,0,0x1|0x2|0x40|0x80,None));live=[];results=[]
try:
 check(setDesk(desktop))
 for scenario_name,vas in scenarios:
  buf=C.create_string_buffer(data);hwnd=check(create(module(None),C.cast(buf,PTR),None,proc,0));live.append(hwnd);expected={}
  for cid,va in zip(ids,vas):
   r=byva[va];fo=pe.get_offset_from_rva(va-pe.OPTIONAL_HEADER.ImageBase);raw=payload[fo:payload.index(0,fo)];assert raw.decode('cp949')==r['target'];check(setA(hwnd,cid,raw));expected[cid]=r
  for cid in ids[len(vas):]:check(destroy(check(getItem(hwnd,cid))))
  show(hwnd,4);update(hwnd);pump(.25);window=item(hwnd);cs=children(hwnd);layout=[]
  for cid,r in expected.items():
   c=next(c for c in cs if c['id']==cid);assert c['text']==r['target'];width,height=c['client'][2:];font=send(c['hwnd'],0x31,0,0);dc=check(getDC(c['hwnd']));old=select(dc,font) if font else None;rr=W.RECT(0,0,width-12,0);needed=drawtext(dc,r['target'],len(r['target']),C.byref(rr),0x400|0x20)
   if old:select(dc,old)
   releaseDC(c['hwnd'],dc);layout.append({'id':r['id'],'control_id':cid,'window_text_matches':True,'control_pixels':[width,height],'required_text_pixels':[rr.right,needed],'fits':rr.right<=width-12 and needed<=height})
  cap=capture(window,'installer-v2-launcher-'+scenario_name);results.append({'scenario':scenario_name,'caption':window['text'],'capture':cap,'layout':layout});check(destroy(hwnd));live.remove(hwnd);pump(.03)
finally:
 for hwnd in live:destroy(hwnd)
 check(setDesk(original));closeDesk(desktop);sample=sampler.finish(os.getpid())
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate':'installer-ui-v2','setup_sha256':hashlib.sha256(payload).hexdigest(),'host_pid':os.getpid(),'installer_executed':False,'system_acp':acp,'display_path':'Patched CP949 bytes read from candidate and SetDlgItemTextA into Unicode native dialog; GetWindowTextW and DrawTextW checked.','host_behavior':'Inert Python dialog host on private desktop; no installer initializer, install/uninstall operation, global input or desktop switching invoked. All host windows destroyed.','scenarios':results,'assumptions':['DirectX optional button included; optional configuration-defined README button excluded. Background/branding initialization is not simulated.','Actual installer execution and all dynamic text not covered.'],'input_before':before,'input_after':foreground(),'focus_sampler':sample,'all_measured_text_fits':all(v['fits'] for r in results for v in r['layout']),'unique_labels_checked':len({v['id'] for r in results for v in r['layout']}),'runtime_pass':False,'layout_visual_pass':False}
(U/'reports/installer-ui-v2-launcher-layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'acp':acp,'unique_labels':report['unique_labels_checked'],'all_fit':report['all_measured_text_fits'],'focus':sample,'captures':[r['capture']['path'] for r in results]},ensure_ascii=False))
