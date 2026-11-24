from pathlib import Path
import sys,json,struct,zlib,shutil,hashlib
R=Path.cwd();C=R/'candidates/config-completion-v1';N=C/'native';old=R/'candidates/input-fix-v1/native'
sys.path.insert(0,str(R/'tools'));import build_trial as b
from inspect_majiro import Arc
# The installed script contains audited CP949 native-dialog leaves. Decode only
# their diagnostic display tolerantly; rewrite() retains every original raw byte.
import inspect,textwrap,mjotool.script as ms
ns=dict(vars(ms));reader_source=textwrap.dedent(inspect.getsource(ms.Instruction.read_instruction)).replace(".decode('cp932')", ".decode('cp932',errors='replace')")
exec(reader_source,ns);ms.Instruction.read_instruction=ns['read_instruction']

h=zlib.crc32(b'#kr_config_visible@CONFIG')
a=Arc(R/'builds/body-ui-20261023-v12-input-logo/scenario.arc');raw=a.path.read_bytes();e=next(e for e in a.entries if e['name']=='config.mjo');source=raw[e['offset']:e['offset']+e['size']];s,code=b.decode(source)
assert h not in {x.hash for x in s.instructions if x.opcode.encoding in ['fho','h0a','ha']}
def value(v):return b.op('ldc.i')+struct.pack('<i',v)+b.op('st.i')+struct.pack('<HIh',0,h,-1)+b.op('pop')
anchors={1162:0,1444:1,1638:0}
insert={}
for line,v in anchors.items():
 hits=[i for i,x in enumerate(s.instructions) if x.opcode.mnemonic=='line' and x.format_instruction().split('#')[-1]==str(line)]
 assert len(hits)==1,(line,hits)
 insert[hits[0]]=value(v)
data,report=b.rewrite(source,insertions=insert);(C/'payloads/config.mjo').write_bytes(data)
ns,ncode=b.decode(data)
(C/'config-script-proof.json').write_text(json.dumps({'hash':f'{h:08x}','private_virtual_variable':True,'source_sha256':hashlib.sha256(source).hexdigest(),'output_sha256':hashlib.sha256(data).hexdigest(),'anchors':anchors,'relocation':report,'flag_scope':'Set0 on config entry,1 immediately before event loop,0 before exit cleanup. Native hook virtualizes it so no save-table record is added.'},indent=2)+'\n','utf-8')
(C/'config-patched.mjil').write_text('\n'.join(x.format_instruction() for x in ns.instructions)+'\n','utf-8')
for name in ['hooks.json','hooks.inc','Build.cmd']:shutil.copy2(old/name,N/name)
src=(old/'ReconquistaHD.cpp').read_text('utf-8-sig')
src=src.replace('static bool inputProbe=false;','static bool inputProbe=false;static bool configProbe=false;static HWND reviewButton=nullptr;static HFONT reviewFont=nullptr;static int reviewFontPixels=0;static const UINT REVIEW_BUTTON_ID=0x7e42;')
src=src.replace('inputProbe=probe&&GetEnvironmentVariableW(L"RECON_INPUT_PROBE",probeValue,8)>0;','inputProbe=probe&&GetEnvironmentVariableW(L"RECON_INPUT_PROBE",probeValue,8)>0;configProbe=probe&&GetEnvironmentVariableW(L"RECON_CONFIG_PROBE",probeValue,8)>0;')
src=src.replace('static Variable reviewVars[6]{};',f'static Variable reviewVars[6]{{}};static Variable configVisibleVar{{0x{h:08x}u,0,0,0}};')
src=src.replace('if(v&&v->scope==0)if(auto p=ReviewVar(v->hash))return p;','if(v&&v->scope==0){if(v->hash==configVisibleVar.hash)return &configVisibleVar;if(auto p=ReviewVar(v->hash))return p;}')
src=src.replace('if(auto p=ReviewVar(hash))return p;return oldVarHash(hash);','if(hash==configVisibleVar.hash)return &configVisibleVar;if(auto p=ReviewVar(hash))return p;return oldVarHash(hash);')
src=src.replace('VarWrite(Variable*v,short*index){if(v&&v->scope==0){if(v->hash==configVisibleVar.hash)return &configVisibleVar;', 'VarWrite(Variable*v,short*index){if(v&&v->scope==0){if(v->hash==configVisibleVar.hash){configVisibleVar.value=v->value;return &configVisibleVar;}')
src=src.replace('reviewEnabled=enabled;if(reviewMenu)','reviewEnabled=enabled;if(reviewButton)InvalidateRect(reviewButton,nullptr,FALSE);if(reviewMenu)')
src=src.replace('if(reviewProbe)return;MessageBoxW','if(reviewProbe||configProbe)return;MessageBoxW')
code=r'''
// A native owner-drawn child button consumes its own press/release/capture events.
// Config's private VM flag is emitted only while its event loop is active.
static bool ReviewButtonWanted(){return configVisibleVar.value!=0;}
static WNDPROC oldReviewButtonProc=nullptr;
static LRESULT CALLBACK ReviewButtonProc(HWND h,UINT msg,WPARAM wp,LPARAM lp){
 if((msg==WM_KEYDOWN||msg==WM_KEYUP||msg==WM_SYSKEYDOWN||msg==WM_SYSKEYUP)&&wp!=VK_SPACE)return SendMessageW(GetParent(h),msg,wp,lp);
 LRESULT result=CallWindowProcW(oldReviewButtonProc,h,msg,wp,lp);
 if((msg==WM_LBUTTONUP||msg==WM_CAPTURECHANGED||msg==WM_CANCELMODE)&&GetFocus()==h)SetFocus(GetParent(h));
 return result;
}
static void SyncReviewButton(){
 HWND parent=Game();if(!parent)return;
 bool wanted=ReviewButtonWanted();
 if(!wanted){if(reviewButton&&(GetWindowLongW(reviewButton,GWL_STYLE)&WS_VISIBLE)){if(GetFocus()==reviewButton)SetFocus(parent);ShowWindow(reviewButton,SW_HIDE);}return;}
 if(!reviewButton){
  if(!(GetWindowLongW(parent,GWL_STYLE)&WS_CLIPCHILDREN))SetWindowLongW(parent,GWL_STYLE,GetWindowLongW(parent,GWL_STYLE)|WS_CLIPCHILDREN);
  reviewButton=CreateWindowExW(0,L"BUTTON",L"검수용 모든 콘텐츠 개방",WS_CHILD|WS_TABSTOP|BS_OWNERDRAW,0,0,1,1,parent,(HMENU)(UINT_PTR)REVIEW_BUTTON_ID,GetModuleHandleW(nullptr),nullptr);
  if(reviewButton)oldReviewButtonProc=(WNDPROC)SetWindowLongPtrW(reviewButton,GWLP_WNDPROC,(LONG_PTR)ReviewButtonProc);
 }
 if(!reviewButton)return;
 if(!(GetWindowLongW(parent,GWL_STYLE)&WS_CLIPCHILDREN))SetWindowLongW(parent,GWL_STYLE,GetWindowLongW(parent,GWL_STYLE)|WS_CLIPCHILDREN);
 auto v=Viewport(parent);int x=v.x+MulDiv(263,v.w,800),y=v.y+MulDiv(55,v.h,600),w=MulDiv(274,v.w,800),h=MulDiv(25,v.h,600);
 RECT r{};GetWindowRect(reviewButton,&r);MapWindowPoints(nullptr,parent,(POINT*)&r,2);
 if(r.left!=x||r.top!=y||r.right-r.left!=w||r.bottom-r.top!=h){
  SetWindowPos(reviewButton,HWND_TOP,x,y,w,h,SWP_NOACTIVATE);
  int cut=std::max(3,h/5);POINT pts[6]={{cut,0},{w-cut,0},{w,h/2},{w-cut,h},{cut,h},{0,h/2}};
  HRGN region=CreatePolygonRgn(pts,6,WINDING);if(region&&!SetWindowRgn(reviewButton,region,TRUE))DeleteObject(region);
 }
 int fp=std::max(12,MulDiv(14,v.h,600));
 if(fp!=reviewFontPixels){HFONT f=CreateFontW(-fp,0,0,0,FW_MEDIUM,FALSE,FALSE,FALSE,HANGUL_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"맑은 고딕");if(f){SendMessageW(reviewButton,WM_SETFONT,(WPARAM)f,FALSE);if(reviewFont)DeleteObject(reviewFont);reviewFont=f;reviewFontPixels=fp;}}
 if(!(GetWindowLongW(reviewButton,GWL_STYLE)&WS_VISIBLE))ShowWindow(reviewButton,SW_SHOWNOACTIVATE);
}
static void DrawReviewButton(const DRAWITEMSTRUCT* di){
 int saved=SaveDC(di->hDC);RECT r=di->rcItem;
 bool down=(di->itemState&ODS_SELECTED)!=0;
 COLORREF fill=reviewEnabled?RGB(103,37,54):RGB(48,24,36);if(down)fill=RGB(126,57,70);
 HBRUSH brush=CreateSolidBrush(fill);HPEN pen=CreatePen(PS_SOLID,std::max<int>(1,(r.bottom-r.top)/25),RGB(185,128,135));
 FillRect(di->hDC,&r,brush);HGDIOBJ ob=SelectObject(di->hDC,brush),op=SelectObject(di->hDC,pen);
 int cut=std::max<int>(3,(r.bottom-r.top)/5);POINT pts[6]={{cut,1},{r.right-cut-1,1},{r.right-1,r.bottom/2},{r.right-cut-1,r.bottom-1},{cut,r.bottom-1},{1,r.bottom/2}};Polygon(di->hDC,pts,6);
 SelectObject(di->hDC,op);SelectObject(di->hDC,ob);DeleteObject(pen);DeleteObject(brush);
 if(reviewFont)SelectObject(di->hDC,reviewFont);SetBkMode(di->hDC,TRANSPARENT);SetTextColor(di->hDC,RGB(249,228,214));
 const wchar_t* label=reviewEnabled?L"개방 취소  ·  현재 켜짐":L"모든 콘텐츠 개방  ·  현재 꺼짐";
 DrawTextW(di->hDC,label,-1,&r,DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);
 if(di->itemState&ODS_FOCUS){InflateRect(&r,-cut,-4);DrawFocusRect(di->hDC,&r);}
 RestoreDC(di->hDC,saved);
}
static void CALLBACK ReviewButtonTimer(HWND,UINT,UINT_PTR,DWORD){SyncReviewButton();}
'''
src=src.replace('static void CALLBACK ProbeTimer(HWND,UINT,UINT_PTR,DWORD);',code+'\nstatic void CALLBACK ProbeTimer(HWND,UINT,UINT_PTR,DWORD);')
src=src.replace('if(msg==WM_COMMAND&&LOWORD(wp)==REVIEW_ID)', 'if(msg==WM_DRAWITEM&&wp==REVIEW_BUTTON_ID&&lp){DrawReviewButton((const DRAWITEMSTRUCT*)lp);return 1;}\n  if(msg==WM_COMMAND&&LOWORD(wp)==REVIEW_BUTTON_ID&&HIWORD(wp)==BN_CLICKED&&(HWND)lp==reviewButton){ToggleReview();SyncReviewButton();InvalidateRect(reviewButton,nullptr,FALSE);UpdateWindow(reviewButton);SetFocus(h);return 1;}\n  if(msg==WM_COMMAND&&LOWORD(wp)==REVIEW_ID)')
src=src.replace('AddReviewMenu();fullscreen=', 'AddReviewMenu();SetTimer(game,0x4845,50,ReviewButtonTimer);fullscreen=')
src=src.replace('if(!reviewProbe&&!inputProbe)ProbeAssets();','if(!reviewProbe&&!inputProbe&&!configProbe)ProbeAssets();')
probe=r'''
static void ProbeConfig(){
 if(!configProbe||!titleReady)return;static int phase=0,checks=0,failures=0,tries=0,settle=0;if(phase>=6)return;
 auto check=[&](bool ok,const char*name){checks++;if(!ok)failures++;if(logFile){fprintf(logFile,"config_probe %s %s\n",name,ok?"PASS":"FAIL");fflush(logFile);}};
 auto mouse=[&](UINT msg,int x,int y,WPARAM state=0){auto v=Viewport(Game());LPARAM lp=MAKELPARAM(v.x+(int)ceil(double(x)*v.w/800),v.y+(int)ceil(double(y)*v.h/600));SendMessageW(Game(),msg,state,lp);};
 if(phase==0){if(settle++<3)return;check(!ReviewButtonWanted(),"hidden_on_title");SendMessageW(Game(),WM_ACTIVATEAPP,TRUE,0);SendMessageW(Game(),WM_ACTIVATE,WA_ACTIVE,0);SendMessageW(Game(),WM_SETFOCUS,0,0);mouse(WM_MOUSEMOVE,640,430);mouse(WM_LBUTTONDOWN,640,430,MK_LBUTTON);phase=1;return;}
 if(phase==1){mouse(WM_LBUTTONUP,640,430);phase=2;return;}
 if(phase==2){
  if(!ReviewButtonWanted()&&tries++<7){if(tries==2){probeShots=0;SendMessageW(Game(),WM_KEYDOWN,VK_F9,0);SendMessageW(Game(),WM_KEYUP,VK_F9,0);}if(logFile){fprintf(logFile,"config_probe_wait mx=%d my=%d left=%d focus=%p\n",*(int*)0x4e980c,*(int*)0x4e9808,*(unsigned char*)(0x4e9afc+0x82),GetFocus());fflush(logFile);}return;}
  check(ReviewButtonWanted(),"real_config_script_sets_flag");
  check(reviewButton&&(GetWindowLongW(reviewButton,GWL_STYLE)&WS_VISIBLE),"config_button_exists_visible_style");
  if(!reviewButton){phase=5;return;}
  RECT rect{};GetClientRect(reviewButton,&rect);POINT pt{rect.right/2,rect.bottom/2};
  SetReview(false);int flags=*(unsigned char*)(0x4e9afc+0x82),mx=*(int*)0x4e980c,my=*(int*)0x4e9808;
  SendMessageW(reviewButton,WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(pt.x,pt.y));SendMessageW(reviewButton,WM_LBUTTONUP,0,MAKELPARAM(pt.x,pt.y));
  check(reviewEnabled,"child_mouse_click_enables");check(flags==*(unsigned char*)(0x4e9afc+0x82)&&mx==*(int*)0x4e980c&&my==*(int*)0x4e9808,"child_click_not_delivered_to_game_input");
  SendMessageW(reviewButton,WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(pt.x,pt.y));SendMessageW(reviewButton,WM_MOUSEMOVE,MK_LBUTTON,MAKELPARAM(rect.right+20,rect.bottom+20));SendMessageW(reviewButton,WM_LBUTTONUP,0,MAKELPARAM(rect.right+20,rect.bottom+20));check(reviewEnabled,"drag_release_outside_does_not_toggle");check(GetFocus()!=reviewButton,"drag_cancel_focus_returned");
  SendMessageW(reviewButton,WM_KEYDOWN,VK_SPACE,0);SendMessageW(reviewButton,WM_KEYUP,VK_SPACE,0);check(!reviewEnabled,"child_keyboard_space_disables");
  HDC dc=GetDC(reviewButton);HGDIOBJ f=SelectObject(dc,reviewFont);SIZE size{};const wchar_t* text=L"모든 콘텐츠 개방  ·  현재 꺼짐";GetTextExtentPoint32W(dc,text,(int)wcslen(text),&size);SelectObject(dc,f);ReleaseDC(reviewButton,dc);check(size.cx<rect.right-12&&size.cy<rect.bottom,"korean_label_fits_button");
  mouse(WM_MOUSEMOVE,760,580);mouse(WM_RBUTTONDOWN,760,580,MK_RBUTTON);phase=3;return;
 }
 if(phase==3){mouse(WM_RBUTTONUP,760,580);phase=4;tries=0;return;}
 if(phase==4){if(ReviewButtonWanted()&&tries++<5)return;check(!ReviewButtonWanted(),"config_exit_clears_flag");check(!(GetWindowLongW(reviewButton,GWL_STYLE)&WS_VISIBLE),"button_hidden_after_config");phase=5;}
 if(phase==5){SetReview(false);if(logFile){fprintf(logFile,"config_probe_result checks=%d failures=%d\n",checks,failures);fflush(logFile);}phase=6;}
}
'''
src=src.replace('static BOOL WINAPI WindowShow',probe+'\nstatic BOOL WINAPI WindowShow')
src=src.replace('if(inputProbe)ProbeInput();','if(inputProbe)ProbeInput();if(configProbe)ProbeConfig();')
# Keep config lifecycle probe alive until its finite state machine finishes; screenshots stay capped.
src=src.replace('if(probeShots>=12)KillTimer(hwnd,0x4844);','if(probeShots>=12&&!configProbe)KillTimer(hwnd,0x4844);')
(N/'ReconquistaHD.cpp').write_text(src,'utf-8')
(C/'button-design.json').write_text(json.dumps({'private_hash':f'{h:08x}','logical_rect':[263,55,274,25],'visibility':'Only config.mjo interactive loop via private nonpersistent VM record','input':'Native owner-drawn child BUTTON; consumes press/release/drag; original game Input untouched','state':'same reversible SetReview and review-unlock.enabled persistence','labels':['모든 콘텐츠 개방  ·  현재 꺼짐','개방 취소  ·  현재 켜짐'],'translator_model':'Codex internal','existing_Ctrl_F10_retained':True},ensure_ascii=False,indent=2)+'\n','utf-8')
print('config flag',hex(h),'script inserts',len(insert),'native source prepared')

