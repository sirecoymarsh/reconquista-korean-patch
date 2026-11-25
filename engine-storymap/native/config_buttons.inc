// The config screen's own plain buttons (owner drawn as 「CG·메뉴」, shown only while its loop runs: ReviewButtonWanted):
//   「이야기 흐름」 (510,574): the map's menu command (0x7e43, handled as F11);
//   「기록 점프: 묻기 / 바로」 (318,574, where the 연표 look button was; 11-25, the user: 「두번 다시 묻지 않아도 옵션에서 다시
//   묻게 할 수 있어?」): the 기록's 「이 대사로 돌아갈까요?」 on or off (backlog.inc, backlog.ini).
static bool BacklogAsks();static void BacklogSetAsks(bool);   // backlog.inc
struct ConfigButton{UINT id;int x,y,w,h;const wchar_t*(*label)();bool(*lit)();void(*press)();HWND hwnd;WNDPROC old;};
static const wchar_t* BacklogAskLabel(){return BacklogAsks()?L"기록 점프: 묻고 가기":L"기록 점프: 바로 가기";}
static ConfigButton configButtons[]={
 {0x7e43,510,574,165,24,[]{return L"이야기 흐름";},[]{return false;},nullptr,nullptr,nullptr},
 {0x7e48,318,574,165,24,BacklogAskLabel,[]{return BacklogAsks();},[]{BacklogSetAsks(!BacklogAsks());},nullptr,nullptr},
};
static LRESULT CALLBACK ConfigButtonProc(HWND h,UINT m,WPARAM w,LPARAM l){WNDPROC old=nullptr;for(auto&b:configButtons)if(b.hwnd==h)old=b.old;if(!old)return DefWindowProcW(h,m,w,l);
 if((m==WM_KEYDOWN||m==WM_KEYUP||m==WM_SYSKEYDOWN||m==WM_SYSKEYUP)&&w!=VK_SPACE)return SendMessageW(GetParent(h),m,w,l);auto r=CallWindowProcW(old,h,m,w,l);
 if((m==WM_LBUTTONUP||m==WM_CAPTURECHANGED||m==WM_CANCELMODE)&&GetFocus()==h)SetFocus(GetParent(h));return r;}
static void SyncConfigButtons(){HWND parent=Game();if(!parent)return;bool wanted=ReviewButtonWanted();auto v=Viewport(parent);
 for(auto&b:configButtons){if(!wanted){if(b.hwnd){if(GetFocus()==b.hwnd)SetFocus(parent);ShowWindow(b.hwnd,SW_HIDE);}continue;}
  if(!b.hwnd){b.hwnd=CreateWindowExW(0,L"BUTTON",b.label(),WS_CHILD|WS_TABSTOP|BS_OWNERDRAW,0,0,1,1,parent,(HMENU)(UINT_PTR)b.id,GetModuleHandleW(nullptr),nullptr);if(b.hwnd)b.old=(WNDPROC)SetWindowLongPtrW(b.hwnd,GWLP_WNDPROC,(LONG_PTR)ConfigButtonProc);}if(!b.hwnd)continue;
  int x=v.x+MulDiv(b.x,v.w,800),y=v.y+MulDiv(b.y,v.h,600),w=MulDiv(b.w,v.w,800),h=MulDiv(b.h,v.h,600);RECT r{};GetWindowRect(b.hwnd,&r);MapWindowPoints(nullptr,parent,(POINT*)&r,2);
  if(r.left!=x||r.top!=y||r.right-r.left!=w||r.bottom-r.top!=h){SetWindowPos(b.hwnd,HWND_TOP,x,y,w,h,SWP_NOACTIVATE);int cut=std::max(3,h/5);POINT pts[]={{cut,0},{w-cut,0},{w,h/2},{w-cut,h},{cut,h},{0,h/2}};auto region=CreatePolygonRgn(pts,6,WINDING);if(region&&!SetWindowRgn(b.hwnd,region,TRUE))DeleteObject(region);}
  SendMessageW(b.hwnd,WM_SETFONT,(WPARAM)reviewFont,FALSE);if(!(GetWindowLongW(b.hwnd,GWL_STYLE)&WS_VISIBLE))ShowWindow(b.hwnd,SW_SHOWNOACTIVATE);}}
static void DrawConfigButton(const ConfigButton&b,const DRAWITEMSTRUCT* di){int saved=SaveDC(di->hDC);RECT r=di->rcItem;auto brush=CreateSolidBrush((di->itemState&ODS_SELECTED)?RGB(126,57,70):b.lit()?RGB(103,37,54):RGB(48,24,36));
 auto pen=CreatePen(PS_SOLID,std::max<int>(1,r.bottom/25),RGB(185,128,135));FillRect(di->hDC,&r,brush);auto ob=SelectObject(di->hDC,brush),op=SelectObject(di->hDC,pen);int cut=std::max<int>(3,r.bottom/5);
 POINT pts[]={{cut,1},{r.right-cut-1,1},{r.right-1,r.bottom/2},{r.right-cut-1,r.bottom-1},{cut,r.bottom-1},{1,r.bottom/2}};Polygon(di->hDC,pts,6);SelectObject(di->hDC,op);SelectObject(di->hDC,ob);DeleteObject(pen);DeleteObject(brush);
 if(reviewFont)SelectObject(di->hDC,reviewFont);SetBkMode(di->hDC,TRANSPARENT);SetTextColor(di->hDC,RGB(249,228,214));DrawTextW(di->hDC,b.label(),-1,&r,DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);
 if(di->itemState&ODS_FOCUS){InflateRect(&r,-cut,-4);DrawFocusRect(di->hDC,&r);}RestoreDC(di->hDC,saved);}
// the game window's messages for them (Layout): drawing, and a press of one with its own action (the map's goes on as its command)
static bool ConfigButtonMessage(HWND h,UINT msg,WPARAM wp,LPARAM lp){for(auto&b:configButtons){if(msg==WM_DRAWITEM&&wp==b.id&&lp){DrawConfigButton(b,(const DRAWITEMSTRUCT*)lp);return true;}
  if(msg==WM_COMMAND&&LOWORD(wp)==b.id&&HIWORD(wp)==BN_CLICKED&&(HWND)lp==b.hwnd&&b.press){b.press();SetWindowTextW(b.hwnd,b.label());InvalidateRect(b.hwnd,nullptr,FALSE);SetFocus(h);return true;}}return false;}
