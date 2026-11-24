// 게임 안 영상(MCIWnd, 오프닝 Recon_OP800_H.mpg 등) — 11-22 아르곤 검수 세션 고침.
// ① 엔진은 영상 창을 원래 게임의 800×600 좌표로 MoveWindow 한다(레콘키스타.exe 0x43ede7·0x43eed5·0x43effe).
//    HD DLL 은 게임 창만 4K 로 바꾸므로 영상 창이 4K 창 왼쪽 위 800×600 에 남았다 → 영상 창만 4:3 화면 칸으로 옮긴다.
// ② 지도 이동(빨리 감기, flowFast) 중에는 영상 창을 만들지 않는다. 엔진의 영상 함수들은 창(0x56ac28)이 없으면 그냥 넘어가고,
//    「재생 중인가」(0x43f050)도 「아님」을 돌려주므로 영상 뒤 자리로 가는 이동이 약 100초 빨라진다. 대본은 안 건드린다(세이브 위치 그대로).
// MCIWndCreateA 는 VFWAPIV = __cdecl(호출한 쪽이 스택을 치움 — 엔진도 부른 뒤 add esp,0x10). WINAPI 로 두면 스택이 16바이트 어긋난다(11-22 첫 빌드 결함).
static HWND (__cdecl* oldMciCreate)(HWND,HINSTANCE,DWORD,LPCSTR)=nullptr;
static HWND movieWnd=nullptr;struct MovieBox{int x,y,w,h;};static MovieBox movieLogical{0,0,800,600};static View movieView{-1,-1,-1,-1};
static bool IsMovieWindow(HWND h){char c[32]{};HWND g=Game();return h&&g&&GetParent(h)==g&&GetClassNameA(h,c,32)&&!_stricmp(c,"MCIWndClass");}
static BOOL FitMovie(bool force=false){HWND g=Game();if(!movieWnd||!g||!IsWindow(movieWnd)){movieWnd=nullptr;return FALSE;}auto v=Viewport(g);
 if(!force&&v.x==movieView.x&&v.y==movieView.y&&v.w==movieView.w&&v.h==movieView.h)return TRUE;movieView=v;
 int x=v.x+MulDiv(movieLogical.x,v.w,800),y=v.y+MulDiv(movieLogical.y,v.h,600),w=MulDiv(movieLogical.w,v.w,800),h=MulDiv(movieLogical.h,v.h,600);
 BOOL ok=MoveWindow(movieWnd,x,y,w,h,TRUE);
 if(logFile){fprintf(logFile,"movie_fit logical=%d,%d,%d,%d physical=%d,%d,%d,%d ok=%d\n",movieLogical.x,movieLogical.y,movieLogical.w,movieLogical.h,x,y,w,h,ok);fflush(logFile);}return ok;}
static BOOL WINAPI MovieMove(HWND h,int x,int y,int w,int ht,BOOL repaint){
 if(IsMovieWindow(h)){movieWnd=h;movieLogical={x,y,w,ht};return FitMovie(true);}return MoveWindow(h,x,y,w,ht,repaint);}
static HWND __cdecl MovieCreate(HWND parent,HINSTANCE inst,DWORD style,LPCSTR file){
 if(flowFast.value){if(logFile){fprintf(logFile,"movie_skipped_in_jump fast=%d\n",flowFast.value);fflush(logFile);}return nullptr;}
 HWND h=oldMciCreate?oldMciCreate(parent,inst,style,file):nullptr;if(h)movieWnd=h;
 if(logFile){fprintf(logFile,"movie_create hwnd=%p style=%08lx\n",h,(unsigned long)style);fflush(logFile);}return h;}
