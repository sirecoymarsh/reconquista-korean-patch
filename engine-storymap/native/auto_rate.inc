// 자동 진행 배율 (11-25, the user: 「A키를 연속으로 누르면 자동 진행 속도가 5배까지 빨라지고, 그게 우측 대화창 위 자동 진행에
// 표시가 X1,2,3,4,5 식으로 표시되게 해줘」). A while auto runs steps the rate ×1 → ×5 → ×1 (ConsoleKey); with auto off, A turns
// it on at the rate it had. The script waits after each line for $get_autospeed (×0.8 after a voice, which itself plays to its
// end; ×3 without one, console.mjo 1fd318c6), so that syscall (0x432350, the setting at 0x566ac8) gives the setting over the
// rate. The engine's 「자동 진행」 sign (#auto_spr: auto.rc8, 74x16 at 669,440, console.mjo 0x095c0) is covered, while auto runs
// ([0x4948a0], $is_auto_mode), by 「자동 진행 ×N」 drawn into the frame as it is presented (ScaledPresent), at the screen's size.
static int autoRate=1;
static bool AutoOn(){return *(volatile int*)0x4948a0!=0;}
static void __cdecl AutoSpeedGet(){int base=*(volatile int*)0x566ac8,v=std::max(1,base/autoRate);((void(__cdecl*)(int))0x41c760)(v);
 if(logFile&&AutoOn()){fprintf(logFile,"auto_wait base=%d rate=%d value=%d%c",base,autoRate,v,10);fflush(logFile);}}
static void AutoRateStep(){autoRate=autoRate%5+1;if(logFile){fprintf(logFile,"auto_rate=%d%c",autoRate,10);fflush(logFile);}}
// The sign in the frame (24-bit, pitch bytes a row, w x h for the 800x600 screen): its box darkened as the game's sign is
// (black at 90% under its pulse, here held at 80%), the label in white. The pixels under it are kept in under and put back by
// AutoSignRestore, so the cached frame stays the game's.
static const int SIGN_X=637,SIGN_Y=440,SIGN_W=106,SIGN_H=16;
struct AutoSign{RECT r{};std::vector<BYTE> under;int pitch=0;};static AutoSign autoSign;
static void AutoSignDraw(BYTE*px,int pitch,int w,int h){autoSign.under.clear();if(!AutoOn())return;
 RECT r{MulDiv(SIGN_X,w,800),MulDiv(SIGN_Y,h,600),MulDiv(SIGN_X+SIGN_W,w,800),MulDiv(SIGN_Y+SIGN_H,h,600)};int rw=r.right-r.left,rh=r.bottom-r.top;if(rw<=0||rh<=0||r.right>w||r.bottom>h)return;
 static HFONT font=nullptr;static int fontPx=0;int px12=std::max(8,MulDiv(12,h,600));if(px12!=fontPx){if(font)DeleteObject(font);font=CreateFontW(-px12,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,HANGUL_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,L"맑은 고딕");fontPx=px12;}
 BITMAPINFO bi{};bi.bmiHeader={sizeof(BITMAPINFOHEADER),rw,-rh,1,32,BI_RGB,0,0,0,0,0};void*bits=nullptr;HDC mdc=CreateCompatibleDC(nullptr);HBITMAP dib=CreateDIBSection(mdc,&bi,DIB_RGB_COLORS,&bits,nullptr,0);
 if(!mdc||!dib||!bits){if(dib)DeleteObject(dib);if(mdc)DeleteDC(mdc);return;}
 auto old=SelectObject(mdc,dib);auto of=SelectObject(mdc,font);memset(bits,0,size_t(rw)*rh*4);SetBkMode(mdc,TRANSPARENT);SetTextColor(mdc,RGB(255,255,255));
 wchar_t label[16];swprintf_s(label,L"자동 진행 ×%d",autoRate);RECT tr{0,0,rw,rh};DrawTextW(mdc,label,-1,&tr,DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);GdiFlush();
 autoSign.r=r;autoSign.pitch=pitch;autoSign.under.resize(size_t(rw)*3*rh);
 for(int y=0;y<rh;y++){BYTE*d=px+size_t(r.top+y)*pitch+size_t(r.left)*3;memcpy(autoSign.under.data()+size_t(y)*rw*3,d,size_t(rw)*3);const BYTE*t=(const BYTE*)bits+size_t(y)*rw*4;
  for(int x=0;x<rw;x++){int cov=std::max({t[x*4],t[x*4+1],t[x*4+2]});for(int k=0;k<3;k++){int v=d[x*3+k]*51/255;d[x*3+k]=BYTE(v+(255-v)*cov/255);}}}   // 80% black, then the white letters by their coverage
 SelectObject(mdc,of);SelectObject(mdc,old);DeleteObject(dib);DeleteDC(mdc);}
static void AutoSignRestore(BYTE*px){if(autoSign.under.empty())return;RECT r=autoSign.r;int rw=r.right-r.left,rh=r.bottom-r.top;
 for(int y=0;y<rh;y++)memcpy(px+size_t(r.top+y)*autoSign.pitch+size_t(r.left)*3,autoSign.under.data()+size_t(y)*rw*3,size_t(rw)*3);autoSign.under.clear();}
