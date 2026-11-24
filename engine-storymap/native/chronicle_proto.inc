// The new 연표 (10-27; from the prototype of 10-26). The game's own 연표 (chronicle.mjo) still opens and keeps all its logic;
// the moment its first frame is drawn this view shows over it, drawn by the graphics card on its own thread, and the 연표 under
// it costs nothing more while covered (Covered: no 4x drawing, no present). The contents are the 연표 script's own arrays in the
// engine's memory (ReadTable), so they are the game's at that moment, the review unlock included. Two looks over the same
// table, switched with the 연표 window's own [새|원래] switch, the config screen's button or F8 (chronicle-look.ini):
//   새 모양: grey empty cells, event plates, the cursor cell's person and event opened in a panel (cells are text only: the
//            game holds no picture per event; the user chose 「칸은 글만」);
//   원래 모양: as the script draws it (情報隠蔽, the sub-episode frame, ▲, the breathing NEW, the blue hover, the navy box).
// Both keep the original frame and its buttons. What changes the game (going into a scene, 도움말, closing) is handed to the
// 연표 under it as the user would do it: its scroll set and the same cell or button clicked, a right click to close.
// The user (10-27): 「좋아 완성품을 보고 싶어. 색감은 지금 레콘키스타 스타일이 아닌거 같은데 원래 연표를 다시 가져다 써도
// 좋아. 애초에 중요한건 안 버벅이는거였으니까.」, 「빈칸을 회색으로 만들고 그림을 넣는 등의 변화는 유지해도 좋아. 다만
// 옵션에서 원본 연표처럼 보이는거랑 스위칭 가능하도록. 그 연표도 느리게 만들란 말은 아니야 겉만 같아 보이게 만들어달란거지」,
// 「그 후에 연표를 원래 내용에 맞게 채워줘」.
// RECON_CHRON_PROTO=1 or <runtime>\chronicle-new.enabled turns it on; =bench opens it at the title and scrolls it by itself for
// 10 s (benchgpu: drawn off the screen, timed until the card is done). Pictures: tools/chronicle_assets.py -> chronicle-new\.
#include <d2d1_1.h>
#include <dwrite_3.h>
#pragma comment(lib,"d2d1.lib")
#pragma comment(lib,"dwrite.lib")
#include <d3d11.h>
#pragma comment(lib,"d3d11.lib")
namespace cproto {
using Microsoft::WRL::ComPtr;
// ---------------------------------------------------------------- the 연표 as its script holds it (800x600 units)
static const float BX=95,BY=71,BW=675,BH=503,HH=43,DX=19,DW=76,COL=128;
struct Cell{std::vector<std::wstring> lines,raw,alt,altRaw;std::wstring exec;int state=0;bool fresh=false;bool Event()const{return !lines.empty();}};
struct Table{int rows=0,maxX=0,maxY=0,sx=0,sy=0,curRow=-1,curCol=-1;bool ok=false,chronicle=false;std::vector<int> top,h;std::vector<std::vector<std::wstring>> dates;
 std::vector<bool> dateHidden;std::vector<Cell> cells;bool personHidden[12]{};
 const Cell& At(int r,int c)const{return cells[size_t(r)*12+size_t(c)];}};
static std::wstring Dir(){wchar_t p[MAX_PATH];swprintf_s(p,L"%s\\chronicle-new\\",root);return p;}
static std::unordered_map<wchar_t,wchar_t> hangul;static bool hangulRead=false;
static void ReadHangul(){if(hangulRead)return;hangulRead=true;std::wstring p=Dir()+L"hangul.txt";FILE*f=nullptr;if(_wfopen_s(&f,p.c_str(),L"rb")||!f)return;
 unsigned a=0,b=0;while(fscanf_s(f,"%x %x",&a,&b)==2)hangul[wchar_t(a)]=wchar_t(b);fclose(f);}
static std::wstring Decode(const char*s,int n){if(n<=0)return L"";int m=MultiByteToWideChar(932,0,s,n,nullptr,0);if(m<=0)return L"";std::wstring w(size_t(m),L'\0');
 MultiByteToWideChar(932,0,s,n,w.data(),m);for(auto&c:w){auto it=hangul.find(c);if(it!=hangul.end())c=it->second;}return w;}
// a VM array: 5 dwords of header (dims at 3 and 4), then the elements row by row; a string element points at {refs, ?, length
// with its 0, cp932 letters} (found with the WM_APP+84/85 probes, 사용법.md 「새 연표 본 제작」)
static const int* Arr(uint32_t hash,int&d0,int&d1){Variable*v=oldVarHash?oldVarHash(hash):nullptr;const int*p=v?(const int*)(uintptr_t)unsigned(v->value):nullptr;
 if(!Readable(p,20))return nullptr;d0=p[3];d1=p[4];if(d0<=0||d1<=0||d0>4096||d1>4096||!Readable(p+5,size_t(d0)*size_t(d1)*4))return nullptr;return p+5;}
static int Int(uint32_t hash,int def=0){Variable*v=oldVarHash?oldVarHash(hash):nullptr;return v?v->value:def;}
static std::wstring Str(const int*a,size_t i){const char*s=(const char*)(uintptr_t)unsigned(a[i]);if(!Readable(s,12))return L"";int len=((const int*)s)[2];
 if(len<=1||len>8192||!Readable(s+12,size_t(len)))return L"";return Decode(s+12,len-1);}
// the script pads each line to n letters (its wrap, 0b9ee0a1); the padding is dropped, or kept (keep) for the original look,
// which centres each padded line as the engine's fontout does
static std::vector<std::wstring> Lines(const std::wstring&s,size_t n,bool keep=false){std::vector<std::wstring> out;for(size_t i=0;i<s.size();i+=n){std::wstring l=s.substr(i,n),t=l;
  while(!t.empty()&&(t.back()==L'\x3000'||t.back()==L' '))t.pop_back();while(!t.empty()&&(t.front()==L'\x3000'||t.front()==L' '))t.erase(0,1);out.push_back(keep&&!t.empty()?l:t);}
 while(!out.empty()&&out.back().find_first_not_of(L"\x3000 ")==std::wstring::npos)out.pop_back();return out;}
// engine thread
static bool ReadTable(Table&t){ReadHangul();int d0=0,d1=0,a0=0,a1=0,b0=0,b1=0,c0=0,c1=0,e0=0,e1=0,h0=0,h1=0,p0=0,p1=0;
 const int*st=Arr(0xaa2e632du,d0,d1),*nw=Arr(0x89a5f304u,a0,a1),*ti=Arr(0xcb8a8240u,b0,b1),*al=Arr(0x67a5944bu,c0,c1),*ex=Arr(0xe750647cu,e0,e1),*hh=Arr(0xc4c743b7u,h0,h1),*tp=Arr(0x0ff9be7eu,p0,p1);
 if(!st||!nw||!ti||!al||!ex||!hh||!tp||d1<13||a1<13||b1<13||c1<13||e1<13)return false;
 t.rows=std::clamp(Int(0x7d8495a3u),0,std::min({d0,a0,b0,c0,e0,h0*h1,p0*p1}));if(t.rows<=2)return false;int mask=reviewEnabled?~3:-1;
 t.top.resize(size_t(t.rows));t.h.resize(size_t(t.rows));t.dates.resize(size_t(t.rows));t.dateHidden.resize(size_t(t.rows));t.cells.assign(size_t(t.rows)*12,Cell{});
 for(int r=0;r<t.rows;r++){t.top[size_t(r)]=tp[r];t.h[size_t(r)]=hh[r];t.dates[size_t(r)]=Lines(Str(ti,size_t(r)*b1),13);t.dateHidden[size_t(r)]=(st[size_t(r)*d1]&mask&1)!=0;
  for(int c=0;c<12;c++){Cell&x=t.cells[size_t(r)*12+size_t(c)];{auto tt=Str(ti,size_t(r)*b1+c+1),aa=Str(al,size_t(r)*c1+c+1);x.lines=Lines(tt,7);x.raw=Lines(tt,7,true);x.alt=Lines(aa,13);x.altRaw=Lines(aa,13,true);}x.exec=Str(ex,size_t(r)*e1+c+1);
   x.state=st[size_t(r)*d1+c+1]&mask;x.fresh=nw[size_t(r)*a1+c+1]!=0;if(r<2)x.exec.clear();}}
 for(int c=0;c<12;c++)t.personHidden[c]=(st[c+1]&mask&1)!=0;
 t.maxX=std::max(0,Int(0x704d8d29u));t.maxY=std::max(0,Int(0xd95c0a13u));int gx=Int(0x1d19c016u,-99),gy=Int(0xdc971fd6u,-99);   // where the 연표 is gliding to (a new cell), else where it is
 t.sx=gx>=0?gx:Int(0x4d7f11eeu);t.sy=gy>=0?gy:Int(0xb1fffe23u);int cr=Int(0xd4bb03e2u,-1),cc=Int(0x1535dc22u,-1);if(cr>=2&&cr<t.rows&&cc>=1&&cc<=12){t.curRow=cr;t.curCol=cc-1;}
 t.chronicle=chronicleOpen;t.ok=true;return true;}
// ---------------------------------------------------------------- state shared by the two threads
static HWND wnd=nullptr;static std::atomic<bool> running{false},shown{false},classic{false},inputHeld{false};static bool bench=false,enabled=false,checked=false,benchDone=false;
static bool readyTried=false,parentGone=false,selfDestroy=false,lost=false,gpu=false;static char adapter[128]="";
static std::mutex tableMutex;static std::shared_ptr<Table> pending;   // engine thread -> view thread
static std::atomic<int> request{0};static int reqRow=0,reqCol=0;     // view thread -> engine thread: 1 a scene, 2 도움말, 3 close
static std::wstring LookPath(){wchar_t p[MAX_PATH];swprintf_s(p,L"%s\\chronicle-look.ini",root);return p;}
static void ReadLook(){classic=GetPrivateProfileIntW(L"chronicle",L"original_look",0,LookPath().c_str())!=0;}
static void WriteLook(){WritePrivateProfileStringW(L"chronicle",L"original_look",classic?L"1":L"0",LookPath().c_str());}
// ---------------------------------------------------------------- drawing (view thread)
static ComPtr<ID2D1Factory1> fac;static ComPtr<IDWriteFactory5> dwf;static ComPtr<IDWriteFontCollection1> fonts;static ComPtr<IWICImagingFactory> wicf;
static ComPtr<ID2D1RenderTarget> rt;static ComPtr<ID2D1HwndRenderTarget> hrt;static ComPtr<ID2D1DeviceContext> dctx;
static ComPtr<ID3D11Device> d3d;static ComPtr<ID3D11DeviceContext> d3dc;static ComPtr<ID2D1Device> d2dev;static ComPtr<ID2D1Bitmap1> offscreen;static ComPtr<ID3D11Query> doneQ;
static ComPtr<ID2D1Bitmap> frameOff,frameOn,hiddenArt,graybar,bluebar,subframe,triDark,triLight,handOpen,handGrab,markArt,thumbH,thumbV,plateQ,plates[12],busts[12];
static ComPtr<IDWriteTextFormat> fCell,fDate,fDateNew,fAlt,fPanelTitle,fPanelDesc,fToast,fNewCell,fBadge,fSwitch;
static ComPtr<ID2D1PathGeometry> swAll,swLeft,swRight;   // the look switch's outline and halves
static ComPtr<ID2D1SolidColorBrush> brush;
static std::unordered_map<std::wstring,ComPtr<IDWriteTextLayout>> layouts;
static Table tbl;static float sx=0,sy=0,tx=0,ty=0;static int crow=-1,ccol=-1,hrow=-1,hcol=-1,hbutton=0,pressButton=0,pressSwitch=0;static bool mouseIn=false,dragging=false,dragMoved=false,thumbDrag=false,thumbVert=false,byKeys=false;
static float mx=-1,my=-1,dragX=0,dragY=0,dragSX=0,dragSY=0;static double hoverAt=0,toastUntil=0,lookUntil=0,openedAt=0;static std::wstring toast;static int closing=0;
static LARGE_INTEGER freq0;static double Now2(){LARGE_INTEGER t;QueryPerformanceCounter(&t);return 1000.0*double(t.QuadPart)/double(freq0.QuadPart);}
static std::vector<double> drawMs,gapMs,buildMs;static double openMs=0;static LONGLONG lastFrame=0;
static double segCells=0,segPanel=0,worst[5]{};   // the slowest frame: total, cells, panel, build, EndDraw
static const char* failedAt="";static HRESULT failedHr=S_OK;static bool hwRT=false;static double tStart=0,tRT=0,tFonts=0,tPics=0;
static bool Fail(const char*w,HRESULT hr){failedAt=w;failedHr=hr;return false;}
static ComPtr<ID2D1Bitmap> Load(const wchar_t*name){ComPtr<IWICBitmapDecoder> dec;ComPtr<IWICBitmapFrameDecode> fr;ComPtr<IWICFormatConverter> cv;ComPtr<ID2D1Bitmap> bm;
 std::wstring p=Dir()+name+L".png";if(FAILED(wicf->CreateDecoderFromFilename(p.c_str(),nullptr,GENERIC_READ,WICDecodeMetadataCacheOnDemand,&dec))||FAILED(dec->GetFrame(0,&fr))||FAILED(wicf->CreateFormatConverter(&cv)))return nullptr;
 if(FAILED(cv->Initialize(fr.Get(),GUID_WICPixelFormat32bppPBGRA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeMedianCut)))return nullptr;rt->CreateBitmapFromWicBitmap(cv.Get(),nullptr,&bm);return bm;}
static ComPtr<IDWriteTextFormat> Format(const wchar_t*family,float size,DWRITE_TEXT_ALIGNMENT align=DWRITE_TEXT_ALIGNMENT_LEADING,DWRITE_FONT_WEIGHT weight=DWRITE_FONT_WEIGHT_NORMAL,bool system=false){ComPtr<IDWriteTextFormat> f;
 dwf->CreateTextFormat(family,system?nullptr:fonts.Get(),weight,DWRITE_FONT_STYLE_NORMAL,DWRITE_FONT_STRETCH_NORMAL,size,L"ko-kr",&f);if(f){f->SetTextAlignment(align);f->SetWordWrapping(DWRITE_WORD_WRAPPING_WRAP);}return f;}
static IDWriteTextLayout* Text(const std::wstring&s,IDWriteTextFormat*f,float w,float h){std::wstring k=s+L"\x1f"+std::to_wstring((uintptr_t)f)+L"\x1f"+std::to_wstring(int(w*4));
 auto it=layouts.find(k);if(it!=layouts.end())return it->second.Get();ComPtr<IDWriteTextLayout> l;dwf->CreateTextLayout(s.c_str(),UINT32(s.size()),f,w,h,&l);if(layouts.size()>6000)layouts.clear();return (layouts[k]=l).Get();}
static bool Assets(){HRESULT hr;
 D2D1_FACTORY_OPTIONS o{};if(FAILED(hr=D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED,__uuidof(ID2D1Factory1),&o,(void**)fac.GetAddressOf())))return Fail("d2d_factory",hr);
 if(FAILED(hr=DWriteCreateFactory(DWRITE_FACTORY_TYPE_SHARED,__uuidof(IDWriteFactory5),(IUnknown**)dwf.GetAddressOf())))return Fail("dwrite_factory",hr);
 if(FAILED(hr=CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&wicf))))return Fail("wic",hr);
 RECT r{};GetClientRect(wnd,&r);
 if(gpu){D3D_FEATURE_LEVEL fl{};if(FAILED(hr=D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_HARDWARE,nullptr,D3D11_CREATE_DEVICE_BGRA_SUPPORT,nullptr,0,D3D11_SDK_VERSION,&d3d,&fl,&d3dc)))return Fail("d3d11_device",hr);
  ComPtr<IDXGIDevice> dx;if(FAILED(hr=d3d.As(&dx)))return Fail("dxgi_device",hr);if(FAILED(hr=fac->CreateDevice(dx.Get(),&d2dev)))return Fail("d2d_device",hr);
  if(FAILED(hr=d2dev->CreateDeviceContext(D2D1_DEVICE_CONTEXT_OPTIONS_NONE,&dctx)))return Fail("d2d_context",hr);
  if(FAILED(hr=dctx->CreateBitmap(D2D1::SizeU(UINT32(r.right),UINT32(r.bottom)),nullptr,0,D2D1::BitmapProperties1(D2D1_BITMAP_OPTIONS_TARGET|D2D1_BITMAP_OPTIONS_CANNOT_DRAW,D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM,D2D1_ALPHA_MODE_PREMULTIPLIED)),&offscreen)))return Fail("offscreen",hr);
  dctx->SetTarget(offscreen.Get());rt=dctx;D3D11_QUERY_DESC qd{D3D11_QUERY_EVENT,0};d3d->CreateQuery(&qd,&doneQ);
  ComPtr<IDXGIAdapter> ad;DXGI_ADAPTER_DESC desc{};if(SUCCEEDED(dx->GetAdapter(&ad))&&SUCCEEDED(ad->GetDesc(&desc)))WideCharToMultiByte(CP_UTF8,0,desc.Description,-1,adapter,int(sizeof(adapter)),nullptr,nullptr);hwRT=true;}
 else{if(FAILED(hr=fac->CreateHwndRenderTarget(D2D1::RenderTargetProperties(D2D1_RENDER_TARGET_TYPE_DEFAULT,D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM,D2D1_ALPHA_MODE_PREMULTIPLIED),96,96),
  D2D1::HwndRenderTargetProperties(wnd,D2D1::SizeU(UINT32(r.right),UINT32(r.bottom)),bench?D2D1_PRESENT_OPTIONS_IMMEDIATELY:D2D1_PRESENT_OPTIONS_NONE),&hrt)))return Fail("render_target",hr);
  rt=hrt;hrt.As(&dctx);hwRT=rt->IsSupported(D2D1::RenderTargetProperties(D2D1_RENDER_TARGET_TYPE_HARDWARE))!=FALSE;}   // the device context (Windows 8+) for cubic scaling
 tRT=Now2();
 {ComPtr<IDWriteFontSetBuilder1> sb;if(SUCCEEDED(dwf->CreateFontSetBuilder(&sb))){for(auto n:{L"ReconquistaKR.otf",L"ReconquistaKRLarge.otf",L"ReconquistaKRSerif.otf",L"ReconquistaKRSerifLarge.otf"}){wchar_t p[MAX_PATH];swprintf_s(p,L"%s\\font\\%s",root,n);ComPtr<IDWriteFontFile> ff;if(SUCCEEDED(dwf->CreateFontFileReference(p,nullptr,&ff)))sb->AddFontFile(ff.Get());}
  ComPtr<IDWriteFontSet> set;if(SUCCEEDED(sb->CreateFontSet(&set)))dwf->CreateFontCollectionFromFontSet(set.Get(),&fonts);}}
 const wchar_t*gameFont=L"Reconquista KR d00b8d76",*serif=L"Reconquista KR Serif d00b8d76";   // the 연표's own font (fontout_font 16 / 14)
 // the engine's GDI fonts (fontout_font 16,8 for cells and the description box, 14,7 for dates): a cell height of 16 / 14 in this
 // font is an em of 11.1 / 9.7, the width argument squeezes it across to 74.7% / 73.9% (measured on the game's 연표, 10-27)
 fCell=Format(gameFont,11.1f);fDate=Format(gameFont,9.7f);fDateNew=Format(gameFont,11.5f);fAlt=Format(gameFont,11.1f);fNewCell=Format(gameFont,13.f,DWRITE_TEXT_ALIGNMENT_CENTER);fPanelTitle=Format(serif,19.f);fPanelDesc=Format(gameFont,14.f);
 fToast=Format(serif,17.f,DWRITE_TEXT_ALIGNMENT_CENTER);fBadge=Format(gameFont,9.f,DWRITE_TEXT_ALIGNMENT_CENTER,DWRITE_FONT_WEIGHT_BOLD);
 fSwitch=Format(L"Malgun Gothic",12.f,DWRITE_TEXT_ALIGNMENT_CENTER,DWRITE_FONT_WEIGHT_BOLD,true);   // as the DLL's buttons (맑은 고딕 12, bold as the old switch)
 if(fSwitch){fSwitch->SetParagraphAlignment(DWRITE_PARAGRAPH_ALIGNMENT_CENTER);fSwitch->SetWordWrapping(DWRITE_WORD_WRAPPING_NO_WRAP);}
 if(fCell)fCell->SetWordWrapping(DWRITE_WORD_WRAPPING_NO_WRAP);if(fDate)fDate->SetWordWrapping(DWRITE_WORD_WRAPPING_NO_WRAP);if(fDateNew)fDateNew->SetWordWrapping(DWRITE_WORD_WRAPPING_NO_WRAP);if(fAlt)fAlt->SetWordWrapping(DWRITE_WORD_WRAPPING_NO_WRAP);if(fNewCell)fNewCell->SetWordWrapping(DWRITE_WORD_WRAPPING_NO_WRAP);
 if(!fonts||!fCell)return Fail("fonts",E_FAIL);tFonts=Now2();
 frameOff=Load(L"frame_off");frameOn=Load(L"frame_on");hiddenArt=Load(L"hidden");graybar=Load(L"graybar");bluebar=Load(L"bluebar");subframe=Load(L"subframe");triDark=Load(L"tri_dark");triLight=Load(L"tri_light");
 handOpen=Load(L"hand_open");handGrab=Load(L"hand_grab");markArt=Load(L"mark");thumbH=Load(L"thumb_h");thumbV=Load(L"thumb_v");plateQ=Load(L"plate_q");
 for(int i=0;i<12;i++){wchar_t n[16];swprintf_s(n,L"plate_%02d",i);plates[i]=Load(n);swprintf_s(n,L"bust_%02d",i);busts[i]=Load(n);}
 rt->CreateSolidColorBrush(D2D1::ColorF(1,1,1),&brush);tPics=Now2();if(!frameOff||!hiddenArt||!brush)return Fail("pictures",E_FAIL);return true;}
static D2D1_COLOR_F Rgb(int r,int g,int b,float a=1){return D2D1::ColorF(r/255.f,g/255.f,b/255.f,a);}
static void Fill(float x,float y,float w,float h,D2D1_COLOR_F c){if(w<=0||h<=0)return;brush->SetColor(c);rt->FillRectangle(D2D1::RectF(x,y,x+w,y+h),brush.Get());}
static void Box(float x,float y,float w,float h,D2D1_COLOR_F c,float t=1){brush->SetColor(c);rt->DrawRectangle(D2D1::RectF(x+t/2,y+t/2,x+w-t/2,y+h-t/2),brush.Get(),t);}
// a picture of 4x the units it covers: its part (sx,sy,sw,sh in units) into x,y,w,h. Nothing for an empty size: a bitmap drawn
// with a negative part puts the target in its error state, and the rest of the frame is dropped (10-27: row 0, 2 high, with a
// hidden person's cell left only the bars of the new look on screen)
static void Pic(ID2D1Bitmap*b,float x,float y,float w,float h,float px=0,float py=0,float pw=-1,float ph=-1,float opacity=1){if(!b||w<=0||h<=0)return;auto sz=b->GetSize();if(pw<0){pw=sz.width/4;ph=sz.height/4;}if(pw<=0||ph<=0)return;
 D2D1_RECT_F d=D2D1::RectF(x,y,x+w,y+h),s=D2D1::RectF(px*4,py*4,(px+pw)*4,(py+ph)*4);
 if(dctx)dctx->DrawBitmap(b,&d,opacity,D2D1_INTERPOLATION_MODE_HIGH_QUALITY_CUBIC,&s,nullptr);else rt->DrawBitmap(b,d,opacity,D2D1_BITMAP_INTERPOLATION_MODE_LINEAR,s);}
static const float KCELL=.747f,KDATE=.739f;
static float Width(const std::wstring&s,IDWriteTextFormat*f){if(s.empty()||!f)return 0;DWRITE_TEXT_METRICS m{};Text(s,f,4000,400)->GetMetrics(&m);return m.widthIncludingTrailingWhitespace;}
static float LineH(IDWriteTextFormat*f){if(!f)return 0;DWRITE_TEXT_METRICS m{};Text(L"가",f,4000,400)->GetMetrics(&m);return m.height;}
// a line squeezed across by k from its left edge (the engine's narrow GDI font), its padding counted as the engine counts it
static void Squeezed(const std::wstring&s,IDWriteTextFormat*f,float x,float y,float k,D2D1_COLOR_F c){if(s.empty()||!f)return;D2D1_MATRIX_3X2_F base;rt->GetTransform(&base);
 rt->SetTransform(D2D1::Matrix3x2F::Scale(k,1,D2D1::Point2F(x,y))*base);brush->SetColor(c);rt->DrawTextLayout(D2D1::Point2F(x,y),Text(s,f,4000,400),brush.Get());rt->SetTransform(base);}
static void Say(const std::wstring&s,IDWriteTextFormat*f,float x,float y,float w,float h,D2D1_COLOR_F c){if(s.empty()||!f)return;brush->SetColor(c);rt->DrawTextLayout(D2D1::Point2F(x,y),Text(s,f,w,h),brush.Get(),D2D1_DRAW_TEXT_OPTIONS_CLIP);}
static float CellX(int c){return BX+COL*float(c)-sx;}static float CellY(int r){return BY+float(tbl.top[size_t(r)])-sy;}
static bool Open(const Cell&x){return (x.state&1)==0;}static bool Linked(const Cell&x){return (x.state&3)==0&&!x.exec.empty()&&x.Event();}
static int VisibleRow0(){int r=0;while(r<tbl.rows&&tbl.top[size_t(r)]+tbl.h[size_t(r)]<sy)r++;return r;}
static double Breath(){double t=fmod(Now2()/1000.0,2.0);return t<1?t:2-t;}   // the NEW layer's alpha: 0 -> 1 -> 0 over 2 s (sprite_alfa_define 0..255, 1000 ms)
struct Button{float x,y,w,h;};static const Button buttons[5]={{0,0,0,0},{494,7,165,26},{494,35,165,26},{394,9,101,52},{659,18,70,36}};   // 1 새 항목, 2 추가 이야기, 3 도움말, 4 닫기
// the 연표 window's own look switch, where the old [4K|원래] one was (the user, 10-26: 「버튼이 F8이니 불편한데 연표창에 따로
// 스위치 하나 그려줘」): 새 | 원래, the shown one lit; a click on a half picks it (F8 and the config screen's button still flip)
static const float SWX=122,SWY=28,SWW=74,SWH=24,SWSPLIT=SWX+SWW*.42f;
static int SwitchAt(float x,float y){return x>=SWX&&x<SWX+SWW&&y>=SWY&&y<SWY+SWH?(x<SWSPLIT?1:2):0;}
static ComPtr<ID2D1PathGeometry> Poly(std::initializer_list<D2D1_POINT_2F> pts){ComPtr<ID2D1PathGeometry> g;ComPtr<ID2D1GeometrySink> k;if(FAILED(fac->CreatePathGeometry(&g))||FAILED(g->Open(&k)))return nullptr;
 auto it=pts.begin();k->BeginFigure(*it,D2D1_FIGURE_BEGIN_FILLED);for(++it;it!=pts.end();++it)k->AddLine(*it);k->EndFigure(D2D1_FIGURE_END_CLOSED);return SUCCEEDED(k->Close())?g:nullptr;}
static void DrawSwitch(){float c=SWH/5,x0=SWX,x1=SWX+SWW,y0=SWY,y1=SWY+SWH,ym=SWY+SWH/2;
 if(!swAll){swAll=Poly({{x0+c,y0},{x1-c,y0},{x1,ym},{x1-c,y1},{x0+c,y1},{x0,ym}});swLeft=Poly({{x0+c,y0},{SWSPLIT,y0},{SWSPLIT,y1},{x0+c,y1},{x0,ym}});swRight=Poly({{SWSPLIT,y0},{x1-c,y0},{x1,ym},{x1-c,y1},{SWSPLIT,y1}});}
 if(!swAll||!swLeft||!swRight)return;bool o=classic;int hv=mouseIn&&!dragging&&!thumbDrag?SwitchAt(mx,my):0;
 auto half=[&](ID2D1PathGeometry*g,bool lit,bool over){brush->SetColor(lit?Rgb(150,52,72):over?Rgb(86,34,46):Rgb(44,18,26));rt->FillGeometry(g,brush.Get());};
 half(swLeft.Get(),!o,hv==1);half(swRight.Get(),o,hv==2);
 brush->SetColor(Rgb(185,128,135));rt->DrawGeometry(swAll.Get(),brush.Get(),.85f);rt->DrawLine(D2D1::Point2F(SWSPLIT,y0),D2D1::Point2F(SWSPLIT,y1),brush.Get(),.85f);
 Say(L"새",fSwitch.Get(),x0,y0,SWSPLIT-x0,SWH,o?Rgb(150,118,118):Rgb(255,240,228));Say(L"원래",fSwitch.Get(),SWSPLIT,y0,x1-SWSPLIT,SWH,o?Rgb(255,240,228):Rgb(150,118,118));}
static void SetLook(bool original,const char*by){if(classic==original)return;classic=original;WriteLook();if(logFile){fprintf(logFile,"chron_proto look=%s by=%s\n",original?"original":"new",by);fflush(logFile);}}
static void DrawPopupClassic(int r,int c,double age){const Cell&x=tbl.At(r,c);if(x.alt.empty()||!x.exec.empty()||!Open(x))return;size_t letters=0;for(auto&l:x.altRaw)letters+=l.size();
 float w=float(std::min<size_t>(letters,13))*16+18,h=float(x.altRaw.size())*20+16,cx=CellX(c),cy=CellY(r)-4,px=cx+COL+8;if(px+w>=750)px=cx-w-8;float a=float(std::min(1.0,age/300.0));
 rt->PushAxisAlignedClip(D2D1::RectF(0,0,800,600),D2D1_ANTIALIAS_MODE_ALIASED);Fill(px,cy,w,h,Rgb(53,61,86,a));Fill(px+1,cy+1,w-2,h-2,Rgb(97,107,139,a));
 for(size_t i=0;i<x.altRaw.size();i++)Squeezed(x.altRaw[i],fAlt.Get(),px+8,cy+10+20*float(i),KCELL,Rgb(186,190,204,a));rt->PopAxisAlignedClip();}
// the script's lines as one text: its full-width padding dropped. A line that stops short of its width (len letters, the last
// one a pad or a kinsoku mark) broke because the CSV text itself breaks there (a newline in a quoted field): brk goes there.
// The quotes of a quoted field (kept by the script) are dropped.
static std::wstring Joined(const std::vector<std::wstring>&raw,size_t len,const wchar_t*brk){std::wstring s;
 for(size_t i=0;i<raw.size();i++){std::wstring l=raw[i];while(!l.empty()&&l.back()==L'\x3000')l.pop_back();s+=l;if(i+1<raw.size()&&l.size()+1<len)s+=brk;}
 if(!s.empty()&&s.front()==L'"')s.erase(0,1);if(!s.empty()&&s.back()==L'"')s.pop_back();return s;}
// 새 모양: the cursor cell's person and event opened over the half of the table away from it; the person's bust (only for one
// the 연표 shows, not ???) at its right (the user: 그림은 펼친 머리줄의 인물 사진에만)
static const float PW=470,PH=124;
struct PanelText{std::wstring title,desc;float bustW=0,bw=0;};   // bustW: the bust's width; bw: what it takes from the text
static PanelText PanelOf(int r,int c){const Cell&x=tbl.At(r,c);PanelText p;if(!tbl.personHidden[c]&&busts[c]){auto sz=busts[c]->GetSize();p.bustW=(PH-8)*sz.width/sz.height;p.bw=p.bustW+8;}
 p.title=Joined(x.raw,7,L" ");if(!Open(x))p.title=L"아직 모르는 사건";if(!x.Event())p.title.clear();
 p.desc=Joined(x.altRaw,13,L"\n");if(!Open(x))p.desc.clear();if(Linked(x))p.desc+=(p.desc.empty()?L"":L"  ")+std::wstring(L"▶ 추가 이야기: Enter·클릭");return p;}
static void DrawPanel(int r,int c){bool cursorLow=CellY(r)>BY+BH/2;float px=std::clamp(CellX(c)+COL/2-PW/2,BX+4,BX+BW-PW-4),py=cursorLow?BY+HH+6:BY+BH-PH-6;auto p=PanelOf(r,c);
 Fill(px,py,PW,PH,Rgb(18,6,10,.95f));Box(px,py,PW,PH,Rgb(176,150,140));Box(px+3,py+3,PW-6,PH-6,Rgb(88,30,40));
 if(p.bustW>0){Pic(busts[c].Get(),px+PW-p.bustW-4,py+4,p.bustW,PH-8);Fill(px+PW-p.bustW-4,py+4,1,PH-8,Rgb(88,30,40));}
 Pic(tbl.personHidden[c]?plateQ.Get():plates[c].Get(),px+10,py+10,131*.8f,43*.8f);
 Say(p.title,fPanelTitle.Get(),px+124,py+12,PW-134-p.bw,48,Rgb(240,230,218));
 Say(p.desc,fPanelDesc.Get(),px+14,py+54,PW-28-p.bw,PH-58,Rgb(196,180,172));}
static void DrawCellNew(int r,int c,float x,float y,float h){const Cell&e=tbl.At(r,c);if(h<6)return;   // row 0: the header's edge (2 high), nothing of its own here
 if(!e.Event()){Fill(x+2,y+2,COL-4,h-4,Rgb(46,46,50,.9f));return;}   // 「빈칸을 회색으로」
 if(!Open(e)){Pic(hiddenArt.Get(),x+2,y+2,COL-4,h-4,0,0,COL-4,std::min(h-4,337.f));Say(L"?",fToast.Get(),x,y+h/2-12,COL,24,Rgb(120,110,108));Box(x+2,y+2,COL-4,h-4,Rgb(70,60,60));return;}
 bool link=Linked(e);Fill(x+2,y+2,COL-4,h-4,link?Rgb(52,40,12):Rgb(42,12,20));Box(x+2,y+2,COL-4,h-4,link?Rgb(206,170,84):Rgb(140,116,108));
 for(size_t i=0;i<e.lines.size();i++)Say(e.lines[i],fNewCell.Get(),x+4,y+6+20*float(i),COL-8,22,Rgb(236,226,214));
 if(link){float s=7;brush->SetColor(Rgb(226,190,96));ComPtr<ID2D1PathGeometry> g;ComPtr<ID2D1GeometrySink> k;if(SUCCEEDED(fac->CreatePathGeometry(&g))&&SUCCEEDED(g->Open(&k))){
  k->BeginFigure(D2D1::Point2F(x+COL-8-s,y+h-8-s*1.6f),D2D1_FIGURE_BEGIN_FILLED);k->AddLine(D2D1::Point2F(x+COL-8,y+h-8-s*.8f));k->AddLine(D2D1::Point2F(x+COL-8-s,y+h-8));k->EndFigure(D2D1_FIGURE_END_CLOSED);k->Close();rt->FillGeometry(g.Get(),brush.Get());}}
 if(!e.alt.empty()&&!link)Pic(triDark.Get(),x+COL-13,y+2,10,10);
 if(e.fresh){Fill(x+4,y+h-16,26,12,Rgb(170,22,44));Say(L"NEW",fBadge.Get(),x+4,y+h-16,26,12,Rgb(255,240,236));}}
static void DrawCellClassic(int r,int c,float x,float y,float h){const Cell&e=tbl.At(r,c);
 Fill(x+COL-1,y,1,h,Rgb(192,192,192));Fill(x,y+h-1,COL,1,Rgb(192,192,192));
 if(!Open(e)){Pic(hiddenArt.Get(),x,y,COL-1,h-1,0,0,COL-1,std::min(h-1,337.f));return;}
 if(Linked(e)&&subframe){Pic(subframe.Get(),x,y,64,18,0,0,64,18);Pic(subframe.Get(),x+64,y,63,18,73,0,63,18);if(h>36){Pic(subframe.Get(),x,y+18,64,h-36,0,24,64,1);Pic(subframe.Get(),x+64,y+18,63,h-36,73,24,63,1);}
  Pic(subframe.Get(),x,y+h-18,64,18,0,34,64,18);Pic(subframe.Get(),x+64,y+h-18,63,18,73,34,63,18);}
 float lh=LineH(fCell.Get());for(size_t i=0;i<e.lines.size();i++){const std::wstring&l=e.lines[i];
  float tw=Width(l,fCell.Get())*KCELL;Squeezed(l,fCell.Get(),x+(COL-tw)/2,y+7+20*float(i)+(20-lh)/2,KCELL,Rgb(192,192,192));}
 if(!e.alt.empty()&&e.exec.empty())Pic(r==hrow&&c==hcol?triLight.Get():triDark.Get(),x+COL-11,y,10,10);}
static void Render(){
 double t0=Now2();RECT cr{};GetClientRect(wnd,&cr);float s=float(cr.right)/800.f;rt->BeginDraw();rt->SetTransform(D2D1::Matrix3x2F::Scale(s,s));rt->Clear(D2D1::ColorF(0,0,0));bool old=classic;
 if(tbl.ok){int r0=VisibleRow0(),c0=std::max(0,int(sx/COL)),c1=std::min(11,int((sx+BW)/COL));double breath=Breath();
  // under the table: the NEW glow, the mark, the blue bar behind the dates (the script's sprite order)
  rt->PushAxisAlignedClip(D2D1::RectF(BX,BY,BX+BW,BY+BH),D2D1_ANTIALIAS_MODE_ALIASED);
  for(int r=r0;r<tbl.rows&&CellY(r)<BY+BH;r++)for(int c=c0;c<=c1;c++)if(tbl.At(r,c).fresh)Fill(CellX(c),CellY(r),COL,float(tbl.h[size_t(r)]),Rgb(96,0,0,float(old?breath:breath*.8)));
  rt->PopAxisAlignedClip();
  if(markArt)Pic(markArt.Get(),70,438,492,147,0,0,-1,-1,.5f);if(bluebar)Pic(bluebar.Get(),0,0,118,600);
  // dates
  rt->PushAxisAlignedClip(D2D1::RectF(DX,BY,DX+DW,BY+BH),D2D1_ANTIALIAS_MODE_ALIASED);
  for(int r=r0;r<tbl.rows&&CellY(r)<BY+BH;r++){float y=CellY(r),h=float(tbl.h[size_t(r)]);
   if(tbl.dateHidden[size_t(r)]){rt->PushAxisAlignedClip(D2D1::RectF(DX,y,DX+DW,y+h),D2D1_ANTIALIAS_MODE_ALIASED);Pic(graybar.Get(),0,0,118,600);rt->PopAxisAlignedClip();}
   else{auto&ls=tbl.dates[size_t(r)];IDWriteTextFormat*df=old?fDate.Get():fDateNew.Get();float k=old?KDATE:1.f,lh=LineH(df),yy=y+(h-lh*float(ls.size()))/2;
    for(auto&l:ls){float tw=Width(l,df)*k;Squeezed(l,df,DX+(DW-tw)/2,yy,k,old?Rgb(192,192,192):Rgb(226,214,204));yy+=lh;}}
   Fill(DX,y+h-1,DW,1,Rgb(131,131,131));}
  rt->PopAxisAlignedClip();
  // cells
  double tc0=Now2();
  rt->PushAxisAlignedClip(D2D1::RectF(BX,BY,BX+BW,BY+BH),D2D1_ANTIALIAS_MODE_ALIASED);
  for(int r=r0;r<tbl.rows&&CellY(r)<BY+BH;r++)for(int c=c0;c<=c1;c++){float x=CellX(c),y=CellY(r),h=float(tbl.h[size_t(r)]);if(old)DrawCellClassic(r,c,x,y,h);else DrawCellNew(r,c,x,y,h);}
  int fr=byKeys?crow:hrow,fc=byKeys?ccol:hcol;
  if(fr>=1&&fc>=0&&fr<tbl.rows){float x=CellX(fc),y=CellY(fr),h=float(tbl.h[size_t(fr)]);
   if(old){Fill(x+COL-1,y,1,h,Rgb(0,0,255));Fill(x,y+h-1,COL,1,Rgb(0,0,255));Fill(x-1,y,1,h,Rgb(0,0,255));Fill(x,y-1,COL,1,Rgb(0,0,255));}
   else{float L=14,T=2.5f;brush->SetColor(Rgb(250,244,240));struct K{float ax,ay,dx,dy;} ks[4]={{x-1,y-1,1,1},{x+COL+1,y-1,-1,1},{x-1,y+h+1,1,-1},{x+COL+1,y+h+1,-1,-1}};
    for(auto&k:ks){rt->DrawLine(D2D1::Point2F(k.ax,k.ay),D2D1::Point2F(k.ax+k.dx*L,k.ay),brush.Get(),T);rt->DrawLine(D2D1::Point2F(k.ax,k.ay),D2D1::Point2F(k.ax,k.ay+k.dy*L),brush.Get(),T);}}}
  rt->PopAxisAlignedClip();
  segCells=Now2()-tc0;
  // people across
  rt->PushAxisAlignedClip(D2D1::RectF(BX,BY,BX+BW,BY+HH),D2D1_ANTIALIAS_MODE_ALIASED);
  for(int c=c0;c<=c1;c++){float x=CellX(c)-2;Pic(tbl.personHidden[c]?plateQ.Get():plates[c].Get(),x,BY,131,43);if(!old&&c==fc&&fr>=1){Box(x+2,BY+1,COL-2,HH-2,Rgb(250,244,240,.9f),1.5f);}}
  rt->PopAxisAlignedClip();
  double tp0=Now2();if(fr>=1&&fc>=0&&fr<tbl.rows){if(old)DrawPopupClassic(fr,fc,Now2()-hoverAt);else if(tbl.At(fr,fc).Event())DrawPanel(fr,fc);}segPanel=Now2()-tp0;}
 // the frame, a lit button, the scroll thumbs
 Pic(frameOff.Get(),0,0,800,600);if(hbutton>0&&frameOn){auto&b=buttons[hbutton];Pic(frameOn.Get(),b.x,b.y,b.w,b.h,b.x,b.y,b.w,b.h);}DrawSwitch();
 if(tbl.ok){float hx=103+(tbl.maxX>0?sx*648/float(tbl.maxX):0),vy=115+(tbl.maxY>0?sy*444/float(tbl.maxY):0);Pic(thumbH.Get(),hx-19.5f,575-8.5f,39,17);Pic(thumbV.Get(),770-7.5f,vy-11.5f,15,23);}
 else Say(L"연표를 읽지 못했습니다",fToast.Get(),95,300,675,30,Rgb(220,200,190));
 if(Now2()<toastUntil){float w=360,h=46,x=400-w/2,y=300-h/2;Fill(x,y,w,h,Rgb(16,6,10,.94f));Box(x,y,w,h,Rgb(176,150,140));Say(toast,fToast.Get(),x,y+11,w,26,Rgb(236,226,214));}
 if(Now2()<lookUntil){float w=220,h=34,x=572,y=548;Fill(x,y,w,h,Rgb(16,6,10,.92f));Box(x,y,w,h,Rgb(176,150,140));Say(old?L"연표: 원래 모양 (F8)":L"연표: 새 모양 (F8)",fToast.Get(),x,y+6,w,24,Rgb(236,226,214));}
 if(mouseIn&&mx>=BX&&mx<BX+BW&&my>=BY&&my<BY+BH&&!thumbDrag)Pic(dragging?handGrab.Get():handOpen.Get(),mx-12,my-12,24,24);
 double tb=Now2();HRESULT hr=rt->EndDraw();   // by hand EndDraw also waits for the screen: tb-t0 is what the frame cost to build
 if(gpu&&doneQ){d3dc->End(doneQ.Get());BOOL done=FALSE;while(d3dc->GetData(doneQ.Get(),&done,sizeof(done),0)==S_FALSE){}}
 double t1=Now2();if(hr==D2DERR_RECREATE_TARGET){lost=true;if(logFile){fprintf(logFile,"chron_proto recreate_target\n");fflush(logFile);}}
 else if(FAILED(hr)){static int told=0;if(told++<3&&logFile){fprintf(logFile,"chron_proto draw_error hr=%08lx look=%s scroll=%.0f,%.0f\n",(unsigned long)hr,old?"original":"new",sx,sy);fflush(logFile);}}   // a dropped frame, said
 if(lastFrame)gapMs.push_back(t0-double(lastFrame)/1000.0);lastFrame=LONGLONG(t0*1000);drawMs.push_back(t1-t0);buildMs.push_back(tb-t0);
 if(t1-t0>worst[0]){worst[0]=t1-t0;worst[1]=segCells;worst[2]=segPanel;worst[3]=tb-t0;worst[4]=t1-tb;}}
// ---------------------------------------------------------------- moving about (view thread)
static void ClampTarget(){tx=std::clamp(tx,0.f,float(tbl.maxX));ty=std::clamp(ty,0.f,float(tbl.maxY));}
static void CentreOn(int r,int c){tx=COL*float(c)-(BW-COL)/2;ty=float(tbl.top[size_t(r)])-(BH-float(tbl.h[size_t(r)]))/2;ClampTarget();}   // as the script's 14663d7f
static void KeepInView(){if(crow<1||ccol<0)return;float x=COL*float(ccol),y=float(tbl.top[size_t(crow)]),h=float(tbl.h[size_t(crow)]);
 if(x<tx)tx=x;if(x+COL>tx+BW)tx=x+COL-BW;if(y<ty+HH)ty=y-HH;if(y+h>ty+BH)ty=y+h-BH;ClampTarget();}
static void Hit(float x,float y,int&r,int&c){r=c=-1;if(!tbl.ok||x<BX||x>=BX+BW||y<BY+HH||y>=BY+BH)return;c=int((x-BX+sx)/COL);if(c>11){c=-1;return;}float ty2=y-BY+sy;
 for(int i=1;i<tbl.rows;i++)if(float(tbl.top[size_t(i)])<=ty2&&ty2<float(tbl.top[size_t(i)]+tbl.h[size_t(i)])){r=i;return;}c=-1;}
static int ButtonAt(float x,float y){for(int i=1;i<=4;i++){auto&b=buttons[i];if(x>=b.x&&x<b.x+b.w&&y>=b.y&&y<b.y+b.h)return i;}return 0;}
static void Toast(const wchar_t*s){toast=s;toastUntil=Now2()+2200;}
// the script's two finders: the next cell after the cursor, column by column (a person's events in order), wrapping once
static void FindNext(bool sub){int c0=ccol>=0?ccol:0,r0=crow>=1?crow:0;for(int k=1;k<=12*tbl.rows;k++){int i=(c0*tbl.rows+r0+k)%(12*tbl.rows),c=i/tbl.rows,r=i%tbl.rows;if(r<2)continue;
  const Cell&e=tbl.At(r,c);if(sub?Linked(e):e.fresh){crow=r;ccol=c;byKeys=true;hoverAt=Now2();toastUntil=0;CentreOn(r,c);return;}}
 Toast(sub?L"서브 에피소드가 없습니다":L"새로 갱신된 정보가 없습니다");}
static void Ask(int what,int r=0,int c=0){if(!tbl.chronicle||request.load()){if(!tbl.chronicle&&what!=3)Toast(L"게임의 연표 화면에서 열어야 합니다");if(what==3&&!tbl.chronicle)shown=false;return;}
 reqRow=r;reqCol=c;request=what;closing=what;}
static void Activate(int r,int c){if(r>=1&&c>=0&&Linked(tbl.At(r,c)))Ask(1,r,c);}
static void Press(int b){if(b==1)FindNext(false);else if(b==2)FindNext(true);else if(b==3)Ask(2);else if(b==4)Ask(3);}
static void ShotView(int n);
static LRESULT CALLBACK Proc(HWND h,UINT m,WPARAM w,LPARAM l){
 auto logical=[&](float&x,float&y){RECT r{};GetClientRect(h,&r);float s=float(r.right)/800.f;x=float(short(LOWORD(l)))/s;y=float(short(HIWORD(l)))/s;};
 if(closing&&(m==WM_KEYDOWN||m==WM_LBUTTONDOWN||m==WM_RBUTTONUP||m==WM_MOUSEWHEEL))return 0;   // handed to the 연표 under it: nothing more
 if(m==WM_MOUSEWHEEL){bool shift=(GetKeyState(VK_SHIFT)&0x8000)!=0;float n=float(short(HIWORD(w)))/WHEEL_DELTA;if(shift)tx-=n*COL;else ty-=n*88;ClampTarget();return 0;}   // the script's PgUp step
 if(m==WM_MOUSEHWHEEL){tx+=float(short(HIWORD(w)))/WHEEL_DELTA*COL;ClampTarget();return 0;}
 if(m==WM_KEYDOWN){if(w==VK_F7||(bench&&w==VK_ESCAPE)){if(bench)running=false;else Ask(3);return 0;}
  if(w==VK_F8){SetLook(!classic,"f8");lookUntil=Now2()+1800;return 0;}   // the text layouts of both looks stay (made ready in Warm)
  if(w==VK_RETURN||w==VK_SPACE){Activate(crow,ccol);return 0;}
  if(crow<1||ccol<0){crow=std::max(2,hrow);ccol=std::max(0,hcol);}
  if(w==VK_UP)crow=std::max(1,crow-1);if(w==VK_DOWN)crow=std::min(tbl.rows-1,crow+1);if(w==VK_LEFT)ccol=std::max(0,ccol-1);if(w==VK_RIGHT)ccol=std::min(11,ccol+1);
  if(w==VK_PRIOR){ty-=BH-HH;ClampTarget();}if(w==VK_NEXT){ty+=BH-HH;ClampTarget();}if(w==VK_HOME){crow=1;}if(w==VK_END){crow=tbl.rows-1;}
  if(w==VK_UP||w==VK_DOWN||w==VK_LEFT||w==VK_RIGHT||w==VK_HOME||w==VK_END){byKeys=true;hoverAt=Now2();KeepInView();}return 0;}
 if(m==WM_KEYUP&&w==VK_ESCAPE&&!bench){Ask(3);return 0;}
 if(m==WM_RBUTTONUP&&!bench){Ask(3);return 0;}   // a right click closes, as in the game
 if(m==WM_MOUSEMOVE){float x,y;logical(x,y);mouseIn=true;mx=x;my=y;TRACKMOUSEEVENT te{sizeof(te),TME_LEAVE,h,0};TrackMouseEvent(&te);
  if(thumbDrag){if(thumbVert)sy=ty=std::clamp((y-115)/444*float(tbl.maxY),0.f,float(tbl.maxY));else sx=tx=std::clamp((x-103)/648*float(tbl.maxX),0.f,float(tbl.maxX));return 0;}
  if(dragging){if(fabsf(x-dragX)+fabsf(y-dragY)>3)dragMoved=true;if(dragMoved){sx=tx=std::clamp(dragSX+(dragX-x),0.f,float(tbl.maxX));sy=ty=std::clamp(dragSY+(dragY-y),0.f,float(tbl.maxY));}return 0;}
  int r,c;Hit(x,y,r,c);if(r!=hrow||c!=hcol){hrow=r;hcol=c;hoverAt=Now2();}if(r>=1){byKeys=false;crow=r;ccol=c;}hbutton=ButtonAt(x,y);return 0;}
 if(m==WM_MOUSELEAVE){mouseIn=false;hbutton=0;return 0;}
 if(m==WM_LBUTTONDOWN){float x,y;logical(x,y);SetFocus(h);SetCapture(h);pressSwitch=SwitchAt(x,y);if(pressSwitch)return 0;pressButton=ButtonAt(x,y);if(pressButton)return 0;
  float hx=103+(tbl.maxX>0?sx*648/float(tbl.maxX):0),vy=115+(tbl.maxY>0?sy*444/float(tbl.maxY):0);
  if(fabsf(x-hx)<22&&fabsf(y-575)<12){thumbDrag=true;thumbVert=false;return 0;}if(fabsf(x-770)<10&&fabsf(y-vy)<14){thumbDrag=true;thumbVert=true;return 0;}
  if(x>=BX&&x<BX+BW&&y>=BY&&y<BY+BH){dragging=true;dragMoved=false;dragX=x;dragY=y;dragSX=sx;dragSY=sy;}return 0;}
 if(m==WM_LBUTTONUP){float x,y;logical(x,y);ReleaseCapture();if(pressSwitch){int s=pressSwitch;pressSwitch=0;if(SwitchAt(x,y)==s)SetLook(s==2,"switch");return 0;}if(pressButton){int b=pressButton;pressButton=0;if(ButtonAt(x,y)==b)Press(b);return 0;}
  if(thumbDrag){thumbDrag=false;return 0;}bool click=dragging&&!dragMoved;dragging=false;if(click){int r,c;Hit(x,y,r,c);if(r>=1){crow=r;ccol=c;Activate(r,c);}}return 0;}
 if(m==WM_SETCURSOR&&LOWORD(l)==HTCLIENT){bool overTable=mouseIn&&mx>=BX&&mx<BX+BW&&my>=BY&&my<BY+BH;SetCursor(overTable?nullptr:LoadCursorW(nullptr,MAKEINTRESOURCEW(32512)));return TRUE;}
 if(m==WM_APP+1)return 0;   // F7 in the game window or a new table: wakes the loop
 if(m==WM_APP+3){ShotView(int(w));return 0;}   // tests: this frame as a picture
 if(m==WM_APP+4){sx=tx=float(std::clamp(int(w),0,tbl.maxX));sy=ty=float(std::clamp(int(l),0,tbl.maxY));return 0;}   // tests: put the table at x,y
 if(m==WM_APP+5){classic=w!=0;layouts.clear();return 0;}   // tests: the look (not remembered)
 if(m==WM_APP+6){int k=int(w);for(int r=2;r<tbl.rows;r++)for(int c=0;c<12;c++)if(Linked(tbl.At(r,c))&&k--==0){crow=r;ccol=c;byKeys=true;CentreOn(r,c);   // tests: into the k-th sub-episode cell
    if(logFile){fprintf(logFile,"chron_proto test_activate row=%d col=%d\n",r,c+1);fflush(logFile);}Activate(r,c);return 0;}return 0;}
 if(m==WM_APP+7){Press(int(w));if(logFile){fprintf(logFile,"chron_proto test_press button=%d cursor=%d,%d toast=%d\n",int(w),crow,ccol+1,int(Now2()<toastUntil));fflush(logFile);}return 0;}   // tests: a frame button
 if(m==WM_PAINT){ValidateRect(h,nullptr);return 0;}if(m==WM_ERASEBKGND)return 1;if(m==WM_DESTROY){if(!selfDestroy)parentGone=true;running=false;return 0;}
 return DefWindowProcW(h,m,w,l);}
// ---------------------------------------------------------------- reports
static double Pct(std::vector<double> v,double p){if(v.empty())return 0;std::sort(v.begin(),v.end());return v[std::min(v.size()-1,size_t(p*double(v.size())))];}
static void Report(){if(!logFile)return;double sum=0;for(double d:drawMs)sum+=d;RECT r{};GetClientRect(wnd,&r);
 fprintf(logFile,"chron_proto bench frames=%zu seconds=10 fps=%.1f draw_mean=%.3f draw_median=%.3f draw_p95=%.3f draw_p99=%.3f draw_max=%.3f gap_p99=%.3f gap_max=%.3f over_8ms=%zu over_16ms=%zu over_20ms=%zu open_ms=%.1f rows=%d look=%s worst=%.3f worst_cells=%.3f worst_panel=%.3f worst_build=%.3f worst_end=%.3f size=%ldx%ld hardware=%d gpu=%d adapter=%s\n",
  drawMs.size(),double(drawMs.size())/10.0,drawMs.empty()?0:sum/double(drawMs.size()),Pct(drawMs,.5),Pct(drawMs,.95),Pct(drawMs,.99),Pct(drawMs,1),Pct(gapMs,.99),Pct(gapMs,1),
  size_t(std::count_if(drawMs.begin(),drawMs.end(),[](double d){return d>8;})),size_t(std::count_if(gapMs.begin(),gapMs.end(),[](double d){return d>16.7;})),size_t(std::count_if(gapMs.begin(),gapMs.end(),[](double d){return d>20;})),openMs,tbl.rows,
  classic?"original":"new",worst[0],worst[1],worst[2],worst[3],worst[4],long(r.right),long(r.bottom),int(hwRT),int(gpu),adapter[0]?adapter:"-");fflush(logFile);}
static int Refresh(){HMONITOR mon=MonitorFromWindow(wnd,MONITOR_DEFAULTTONEAREST);MONITORINFOEXW mi{};mi.cbSize=sizeof(mi);DEVMODEW dm{};dm.dmSize=sizeof(dm);
 return GetMonitorInfoW(mon,(MONITORINFO*)&mi)&&EnumDisplaySettingsW(mi.szDevice,ENUM_CURRENT_SETTINGS,&dm)&&dm.dmDisplayFrequency>1?int(dm.dmDisplayFrequency):0;}
static void Session(double frameMs,size_t moving,size_t movingMissed,size_t slept,double ms){if(!logFile||buildMs.empty())return;double sum=0;for(double d:buildMs)sum+=d;
 size_t missed=size_t(std::count_if(gapMs.begin(),gapMs.end(),[&](double d){return d>frameMs*1.5;}));RECT r{};GetClientRect(wnd,&r);
 fprintf(logFile,"chron_proto session seconds=%.1f frames=%zu fps=%.1f refresh_ms=%.2f gap_median=%.2f gap_p99=%.2f gap_max=%.2f missed=%zu moving_frames=%zu moving_missed=%zu build_mean=%.3f build_max=%.3f slept=%zu open_ms=%.1f look=%s hardware=%d size=%ldx%ld\n",
  ms/1000,buildMs.size(),double(buildMs.size())*1000/std::max(ms,1.0),frameMs,Pct(gapMs,.5),Pct(gapMs,.99),Pct(gapMs,1),missed,moving,movingMissed,sum/double(buildMs.size()),Pct(buildMs,1),slept,openMs,classic?"original":"new",int(hwRT),long(r.right),long(r.bottom));fflush(logFile);}
static HANDLE pace=nullptr;
static bool Pace(double frameStart,double frameMs){double el=Now2()-frameStart;if(el>=frameMs*.6)return false;double waitMs=frameMs*.95-el;
 if(!pace)pace=CreateWaitableTimerExW(nullptr,nullptr,0x00000002,TIMER_ALL_ACCESS);   // CREATE_WAITABLE_TIMER_HIGH_RESOLUTION (Windows 10 1803+)
 LARGE_INTEGER due;due.QuadPart=-LONGLONG(waitMs*10000);if(pace&&SetWaitableTimer(pace,&due,0,nullptr,nullptr,FALSE))WaitForSingleObject(pace,100);else Sleep(DWORD(waitMs));return true;}
// ---------------------------------------------------------------- the view's thread
void Abandon(){(void)new auto(std::move(layouts));layouts.clear();
 for(auto*p:{std::addressof(frameOff),std::addressof(frameOn),std::addressof(hiddenArt),std::addressof(graybar),std::addressof(bluebar),std::addressof(subframe),std::addressof(triDark),std::addressof(triLight),std::addressof(handOpen),std::addressof(handGrab),std::addressof(markArt),std::addressof(thumbH),std::addressof(thumbV),std::addressof(plateQ)})p->Detach();for(auto&p:plates)p.Detach();for(auto&p:busts)p.Detach();
 for(auto*p:{std::addressof(fCell),std::addressof(fDate),std::addressof(fDateNew),std::addressof(fAlt),std::addressof(fPanelTitle),std::addressof(fPanelDesc),std::addressof(fToast),std::addressof(fNewCell),std::addressof(fBadge),std::addressof(fSwitch)})p->Detach();brush.Detach();swAll.Detach();swLeft.Detach();swRight.Detach();
 rt.Detach();hrt.Detach();dctx.Detach();offscreen.Detach();d2dev.Detach();doneQ.Detach();d3dc.Detach();d3d.Detach();fonts.Detach();dwf.Detach();fac.Detach();wicf.Detach();}
// tests (WM_APP+3 to the view): the frame as it is drawn now, into <runtime>\qa\chron-view-<n>.png (the view's device context
// drawn into a picture of its own, then read back)
static void ShotView(int n){if(!dctx||!wicf)return;RECT cr{};GetClientRect(wnd,&cr);ComPtr<ID2D1Image> old;dctx->GetTarget(&old);ComPtr<ID2D1Bitmap1> tgt,cpu;auto fmt=D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM,D2D1_ALPHA_MODE_PREMULTIPLIED);
 auto sz=D2D1::SizeU(UINT32(cr.right),UINT32(cr.bottom));if(FAILED(dctx->CreateBitmap(sz,nullptr,0,D2D1::BitmapProperties1(D2D1_BITMAP_OPTIONS_TARGET|D2D1_BITMAP_OPTIONS_CANNOT_DRAW,fmt),&tgt)))return;
 dctx->SetTarget(tgt.Get());size_t keep=buildMs.size();Render();buildMs.resize(keep);drawMs.resize(keep);dctx->SetTarget(old.Get());D2D1_MAPPED_RECT m{};
 if(FAILED(dctx->CreateBitmap(sz,nullptr,0,D2D1::BitmapProperties1(D2D1_BITMAP_OPTIONS_CPU_READ|D2D1_BITMAP_OPTIONS_CANNOT_DRAW,fmt),&cpu))||FAILED(cpu->CopyFromBitmap(nullptr,tgt.Get(),nullptr))||FAILED(cpu->Map(D2D1_MAP_OPTIONS_READ,&m)))return;
 wchar_t p[MAX_PATH];swprintf_s(p,L"%s\\qa",root);CreateDirectoryW(p,nullptr);swprintf_s(p,L"%s\\qa\\chron-view-%d.png",root,n);ComPtr<IWICStream> st;ComPtr<IWICBitmapEncoder> en;ComPtr<IWICBitmapFrameEncode> fr;bool ok=false;
 if(SUCCEEDED(wicf->CreateStream(&st))&&SUCCEEDED(st->InitializeFromFilename(p,GENERIC_WRITE))&&SUCCEEDED(wicf->CreateEncoder(GUID_ContainerFormatPng,nullptr,&en))&&SUCCEEDED(en->Initialize(st.Get(),WICBitmapEncoderNoCache))
  &&SUCCEEDED(en->CreateNewFrame(&fr,nullptr))&&SUCCEEDED(fr->Initialize(nullptr))){WICPixelFormatGUID f=GUID_WICPixelFormat32bppBGRA;
  ok=SUCCEEDED(fr->SetSize(sz.width,sz.height))&&SUCCEEDED(fr->SetPixelFormat(&f))&&SUCCEEDED(fr->WritePixels(sz.height,m.pitch,m.pitch*sz.height,m.bits))&&SUCCEEDED(fr->Commit())&&SUCCEEDED(en->Commit());}
 cpu->Unmap();if(logFile){fprintf(logFile,"chron_proto shot n=%d ok=%d look=%s scroll=%.0f,%.0f\n",n,int(ok),classic?"original":"new",sx,sy);fflush(logFile);}}
static bool TakeTable(){std::shared_ptr<Table> t;{std::lock_guard<std::mutex> g(tableMutex);t.swap(pending);}if(!t)return false;tbl=std::move(*t);
 sx=tx=float(std::clamp(tbl.sx,0,tbl.maxX));sy=ty=float(std::clamp(tbl.sy,0,tbl.maxY));crow=tbl.curRow;ccol=tbl.curCol;byKeys=crow>=1;hrow=hcol=-1;closing=0;layouts.clear();return true;}
static void Warm(){double w0=Now2();float s0=sx,t0=sy;size_t n=0;for(int look=0;look<2&&tbl.ok;look++){classic=look==1;for(float y=0;;y+=BH-HH){sx=0;sy=std::min(y,float(tbl.maxY));Render();n++;sx=float(tbl.maxX);Render();n++;if(lost||sy>=float(tbl.maxY))break;}}
 // the panel once in each column (its plate and bust drawn for the first time here, not under the user's cursor)
 if(tbl.ok){classic=false;bool keys=byKeys;int r0=crow,c0=ccol;for(int c=0;c<12;c++){for(int r=2;r<tbl.rows;r++)if(tbl.At(r,c).Event()){crow=r;ccol=c;byKeys=true;sx=COL*float(c);sy=float(tbl.top[size_t(r)]);Render();n++;break;}}
  crow=r0;ccol=c0;byKeys=keys;}
 // and what only shows under the cursor: the panel's text (새 모양) and the description box's lines (원래 모양)
 size_t lay=0;for(int r=1;r<tbl.rows&&tbl.ok;r++)for(int c=0;c<12;c++){const Cell&e=tbl.At(r,c);if(!e.Event())continue;auto p=PanelOf(r,c);Text(p.title,fPanelTitle.Get(),PW-134-p.bw,48);Text(p.desc,fPanelDesc.Get(),PW-28-p.bw,PH-58);
  for(auto&l:e.altRaw)Text(l,fAlt.Get(),4000,400);lay++;}
 ReadLook();sx=s0;sy=t0;drawMs.clear();buildMs.clear();gapMs.clear();lastFrame=0;if(logFile){fprintf(logFile,"chron_proto warm frames=%zu cells=%zu ms=%.1f\n",n,lay,Now2()-w0);fflush(logFile);}}
static void Interactive(HWND gw){bool vis=false;double last=Now2(),shownAt=0,frameMs=1000.0/60;size_t moving=0,movingMissed=0,slept=0;View at{};bool warmed=false;
 while(running){MSG msg;while(PeekMessageW(&msg,nullptr,0,0,PM_REMOVE)){if(msg.message==WM_QUIT)running=false;TranslateMessage(&msg);DispatchMessageW(&msg);}if(!running)break;
  if(TakeTable()&&!warmed&&!vis){Warm();warmed=true;}
  if(shown!=vis){vis=shown;
   if(vis){TakeTable();shownAt=Now2();int hz=Refresh();frameMs=1000.0/(hz>0?hz:60);drawMs.clear();buildMs.clear();gapMs.clear();lastFrame=0;moving=movingMissed=slept=0;at=View{};ReadLook();}
   else{if(GetFocus()==wnd)SetFocus(gw);ShowWindow(wnd,SW_HIDE);Session(frameMs,moving,movingMissed,slept,Now2()-shownAt);dragging=thumbDrag=false;closing=0;}}
  if(!vis||IsIconic(gw)){MsgWaitForMultipleObjects(0,nullptr,FALSE,50,QS_ALLINPUT);last=Now2();continue;}
  auto v=Viewport(gw);if(v.x!=at.x||v.y!=at.y||v.w!=at.w||v.h!=at.h){bool first=at.w==0;at=v;if(hrt)hrt->Resize(D2D1::SizeU(UINT32(v.w),UINT32(v.h)));
   SetWindowPos(wnd,HWND_TOP,v.x,v.y,v.w,v.h,SWP_SHOWWINDOW|SWP_NOACTIVATE);if(first)SetFocus(wnd);}
  double now=Now2(),dt=(now-last)/1000.0;last=now;bool mv=fabsf(tx-sx)+fabsf(ty-sy)>0.5f;float k=float(1-std::exp(-dt/0.07));sx+=(tx-sx)*k;sy+=(ty-sy)*k;size_t g=gapMs.size();Render();
  if(buildMs.size()==1){openMs=Now2()-shownAt;if(logFile){fprintf(logFile,"chron_proto show open_ms=%.1f refresh_hz=%.0f size=%dx%d focus=%d rows=%d look=%s from_chronicle=%d\n",openMs,1000.0/frameMs,v.w,v.h,int(GetFocus()==wnd),tbl.rows,classic?"original":"new",int(tbl.chronicle));fflush(logFile);}}
  if(mv){moving++;if(gapMs.size()>g&&gapMs.back()>frameMs*1.5)movingMissed++;}
  if(Pace(now,frameMs))slept++;
  if(lost)running=false;}   // the card's drawing surface is gone: let go of everything; the next opening starts afresh
 if(vis)Session(frameMs,moving,movingMissed,slept,Now2()-shownAt);}
// RECON_CHRON_PACE=<hz> (benchpace): the bench held to that many frames a second, as a screen of that rate would; the report then
// counts the frames that came late (more than 1.5 refreshes after the one before)
static double paceHz=0;
static void Bench(){double start=Now2();for(auto&v:worst)v=0;drawMs.clear();buildMs.clear();gapMs.clear();lastFrame=0;
 while(running){MSG msg;while(PeekMessageW(&msg,nullptr,0,0,PM_REMOVE)){if(msg.message==WM_QUIT)running=false;TranslateMessage(&msg);DispatchMessageW(&msg);}if(!running)break;
  double now=Now2(),t=(now-start)/1000.0;if(t>=10){Report();if(paceHz>0&&logFile){double fm=1000.0/paceHz;fprintf(logFile,"chron_proto paced hz=%.0f frames=%zu late=%zu gap_max=%.3f\n",paceHz,gapMs.size(),
    size_t(std::count_if(gapMs.begin(),gapMs.end(),[&](double d){return d>fm*1.5;})),Pct(gapMs,1));fflush(logFile);}benchDone=true;break;}
  sy=ty=float(tbl.maxY)*float(t<4?t/4:t<8?1-(t-4)/4:0);sx=tx=float(tbl.maxX)*float(0.5-0.5*cos(t*0.9));
  crow=std::clamp(int(t*7)%tbl.rows,1,tbl.rows-1);ccol=int(t/0.35)%12;byKeys=true;hoverAt=Now2()-1000;Render();if(paceHz>0)Pace(now,1000.0/paceHz);}}
static void Run(){
 CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);QueryPerformanceFrequency(&freq0);double open0=Now2();parentGone=selfDestroy=lost=false;ReadLook();
 WNDCLASSW wc{};wc.lpfnWndProc=Proc;wc.hInstance=GetModuleHandleW(L"ReconquistaHD.dll");wc.lpszClassName=L"ReconChronicleProto";wc.hCursor=LoadCursorW(nullptr,MAKEINTRESOURCEW(32512));   // IDC_ARROW (this build is not UNICODE)
 ATOM cls=RegisterClassW(&wc);DWORD clsErr=cls?0:GetLastError();if(!cls&&clsErr!=ERROR_CLASS_ALREADY_EXISTS&&logFile){fprintf(logFile,"chron_proto register_class error=%lu\n",clsErr);fflush(logFile);}
 HWND gw=Game();auto v=Viewport(gw);if(!(GetWindowLongW(gw,GWL_STYLE)&WS_CLIPCHILDREN))SetWindowLongW(gw,GWL_STYLE,GetWindowLongW(gw,GWL_STYLE)|WS_CLIPCHILDREN);
 wnd=CreateWindowExW(WS_EX_NOPARENTNOTIFY,wc.lpszClassName,L"",WS_CHILD|WS_CLIPSIBLINGS|(bench?WS_VISIBLE:0),v.x,v.y,v.w,v.h,gw,nullptr,wc.hInstance,nullptr);   // made ready hidden
 bool ok=wnd&&Assets();if(!wnd)Fail("window",HRESULT_FROM_WIN32(GetLastError()));
 if(logFile){fprintf(logFile,"chron_proto open ok=%d bench=%d assets_ms=%.1f failed=%s hr=%08lx viewport=%d,%d,%d,%d hardware=%d rt_ms=%.1f fonts_ms=%.1f pictures_ms=%.1f letters=%zu\n",ok,bench,Now2()-open0,failedAt,(unsigned long)failedHr,v.x,v.y,v.w,v.h,
  hwRT,tRT-open0,tFonts-tRT,tPics-tFonts,hangul.size());fflush(logFile);}
 if(ok&&!bench)Interactive(gw);
 else if(ok){for(int i=0;i<100&&running&&!TakeTable();i++)Sleep(20);SetWindowPos(wnd,HWND_TOP,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE);Warm();double w0=Now2();Render();openMs=Now2()-w0;Bench();}   // ready as by hand
 if(logFile){fprintf(logFile,"chron_proto closed parent_gone=%d\n",int(parentGone));fflush(logFile);}
 if(parentGone){Abandon();wnd=nullptr;running=false;return;}   // the game window is going: nothing released while the game closes
 layouts.clear();for(auto*p:{std::addressof(frameOff),std::addressof(frameOn),std::addressof(hiddenArt),std::addressof(graybar),std::addressof(bluebar),std::addressof(subframe),std::addressof(triDark),std::addressof(triLight),std::addressof(handOpen),std::addressof(handGrab),std::addressof(markArt),std::addressof(thumbH),std::addressof(thumbV),std::addressof(plateQ)})p->Reset();for(auto&p:plates)p.Reset();for(auto&p:busts)p.Reset();
 for(auto*p:{std::addressof(fCell),std::addressof(fDate),std::addressof(fDateNew),std::addressof(fAlt),std::addressof(fPanelTitle),std::addressof(fPanelDesc),std::addressof(fToast),std::addressof(fNewCell),std::addressof(fBadge),std::addressof(fSwitch)})p->Reset();brush.Reset();swAll.Reset();swLeft.Reset();swRight.Reset();
 rt.Reset();hrt.Reset();dctx.Reset();offscreen.Reset();d2dev.Reset();doneQ.Reset();d3dc.Reset();d3d.Reset();fonts.Reset();dwf.Reset();fac.Reset();wicf.Reset();
 tbl=Table{};if(wnd){if(GetFocus()==wnd)SetFocus(gw);selfDestroy=true;DestroyWindow(wnd);wnd=nullptr;}running=false;CoUninitialize();}
static void Launch(){if(running)return;running=true;readyTried=true;std::thread(Run).detach();}
// ---------------------------------------------------------------- engine thread
static void Hand(std::shared_ptr<Table> t){{std::lock_guard<std::mutex> g(tableMutex);pending=std::move(t);}if(HWND h=wnd)PostMessageW(h,WM_APP+1,0,0);}
static bool Fresh(){auto t=std::make_shared<Table>();bool ok=ReadTable(*t);if(logFile){fprintf(logFile,"chron_proto table ok=%d rows=%d events=%d review=%d\n",int(ok),t->rows,
  int(std::count_if(t->cells.begin(),t->cells.end(),[](const Cell&c){return c.Event();})),int(reviewEnabled));fflush(logFile);}Hand(t);return ok;}
// a logical point of the game screen as the window's own (the input hook turns it back into 800x600 for the engine)
static LPARAM At(HWND g,float x,float y){auto v=Viewport(g);return MAKELPARAM(v.x+int(lroundf(x*float(v.w)/800.f)),v.y+int(lroundf(y*float(v.h)/600.f)));}
// what the view asked for, done to the 연표 under it as the user would: a scene (its scroll set so the cell is on screen, then
// the cell hovered and clicked), 도움말 (its button hovered and clicked), closing (a right click); the view goes when the 연표 does
static void Act(){static int phase=0;static ULONGLONG next=0,since=0;static LPARAM lp=0;int what=request.load();HWND g=Game();ULONGLONG now=GetTickCount64();
 if(!what){phase=0;return;}if(!g)return;
 if(!chronicleOpen||now-since>5000&&phase){if(logFile){fprintf(logFile,"chron_proto act=%d done=%d ms=%llu\n",what,int(!chronicleOpen),phase?now-since:0ull);fflush(logFile);}request=0;phase=0;shown=false;if(HWND h=wnd)PostMessageW(h,WM_APP+1,0,0);return;}
 if(!phase){phase=1;since=now;next=now;}if(now<next)return;
 if(what==1){if(phase==1){int x=0,y=0,xm=0,ym=0;int row=reqRow,col=reqCol;Variable*tv=oldVarHash(0x0ff9be7eu);(void)tv;int d0=0,d1=0;const int*tp=Arr(0x0ff9be7eu,d0,d1),*hh=Arr(0xc4c743b7u,d0,d1);
   if(!tp||!hh){request=0;phase=0;return;}ChroniclePosition(nullptr,nullptr,&xm,&ym);int wantX=std::clamp(int(COL)*col-int(BW-COL)/2,0,std::max(0,xm)),wantY=std::clamp(tp[row]-(int(BH)-hh[row])/2,0,std::max(0,ym));
   ChronicleMoveTo(wantX,wantY);ChroniclePosition(&x,&y,nullptr,nullptr);float cx=std::clamp(BX+COL*float(col)-float(x)+COL/2,BX+4,BX+BW-4),cy=std::clamp(BY+float(tp[row]-y)+float(hh[row])/2,BY+HH+4,BY+BH-4);
   lp=At(g,cx,cy);PostMessageW(g,WM_MOUSEMOVE,0,lp);phase=2;next=now+80;if(logFile){fprintf(logFile,"chron_proto act=scene row=%d col=%d scroll=%d,%d at=%.0f,%.0f\n",row,col+1,x,y,cx,cy);fflush(logFile);}}
  else if(phase==2){PostMessageW(g,WM_LBUTTONDOWN,MK_LBUTTON,lp);phase=3;next=now+60;}else if(phase==3){PostMessageW(g,WM_LBUTTONUP,0,lp);phase=4;}}
 else if(what==2){if(phase==1){lp=At(g,444,35);PostMessageW(g,WM_MOUSEMOVE,0,lp);phase=2;next=now+350;}else if(phase==2){PostMessageW(g,WM_LBUTTONDOWN,MK_LBUTTON,lp);phase=3;next=now+60;}
  else if(phase==3){PostMessageW(g,WM_LBUTTONUP,0,lp);phase=4;}}
 else if(what==3){if(phase==1){lp=At(g,400,330);PostMessageW(g,WM_MOUSEMOVE,0,lp);phase=2;next=now+120;}else if(phase==2){PostMessageW(g,WM_RBUTTONDOWN,MK_RBUTTON,lp);PostMessageW(g,WM_RBUTTONUP,0,lp);phase=4;}}}
// the game's 연표 opened (its menu button, the text box tab...): this view over it, its contents read now
static void Replace(){static bool was=false;if(chronicleOpen&&!was){Fresh();shown=true;request=0;if(!running)Launch();else if(HWND h=wnd)PostMessageW(h,WM_APP+1,0,0);
  if(logFile){fprintf(logFile,"chron_proto replace opened\n");fflush(logFile);}}
 if(!chronicleOpen&&was&&shown&&!request.load()){shown=false;if(HWND h=wnd)PostMessageW(h,WM_APP+1,0,0);if(logFile){fprintf(logFile,"chron_proto replace closed_by_game\n");fflush(logFile);}}
 was=chronicleOpen;}
static void Check(){if(checked)return;checked=true;wchar_t v[16]{};if(GetEnvironmentVariableW(L"RECON_CHRON_PROTO",v,16)){enabled=true;gpu=!wcscmp(v,L"benchgpu");bench=gpu||!wcscmp(v,L"bench")||!wcscmp(v,L"benchpace");if(!wcscmp(v,L"benchpace")){wchar_t hz[16]{};paceHz=GetEnvironmentVariableW(L"RECON_CHRON_PACE",hz,16)?_wtof(hz):120;}}
 wchar_t p[MAX_PATH];swprintf_s(p,L"%s\\chronicle-new.enabled",root);if(GetFileAttributesW(p)!=INVALID_FILE_ATTRIBUTES)enabled=true;ReadLook();}
void SyncLookButton();
// engine thread, every 50 ms (the buttons' timer)
void Tick(){Check();SyncLookButton();if(!enabled)return;
 static ULONGLONG readyAt=0;if(bench&&titleReady&&!benchDone&&!running){if(!readyAt)readyAt=GetTickCount64();else if(GetTickCount64()-readyAt>3000){benchDone=true;Fresh();Launch();}}
 if(!bench&&titleReady&&!readyTried&&!running){shown=false;Fresh();Launch();}   // made ready hidden once the title is up
 if(!bench){Replace();Act();}}
// F7 in the game window: the view over whatever is there (tests; at the title it cannot go into scenes)
bool Key(WPARAM vk){if(!enabled||bench||vk!=VK_F7)return false;if(shown){if(!chronicleOpen)shown=false;else request=3;}else{Fresh();shown=true;}if(!running)Launch();else if(HWND h=wnd)PostMessageW(h,WM_APP+1,0,0);return true;}
bool Shown(){return enabled&&!bench&&running&&shown;}
bool Covered(){return Shown()&&chronicleOpen;}   // the game's 연표 under the view: not drawn at 4x, not presented
// ---------------------------------------------------------------- the config screen's look button (as 「CG·메뉴」, drawn the same)
// Under the sound panel, in the middle: the row of 「CG·메뉴」 and 「모든 콘텐츠 개방」 has no room for a third (their labels),
// and the right column is the game's 「이전 화면으로」/「설정 초기화」 (its first place, 596,55, lay over 설정 초기화).
static HWND lookButton=nullptr;static WNDPROC oldLookProc=nullptr;static const UINT LOOK_ID=0x7e47;
HWND LookButton(){return lookButton;}   // quality_probe.inc's capture prints it with the other buttons
static const wchar_t* LookLabel(){return classic?L"연표: 원래 모양":L"연표: 새 모양";}
static LRESULT CALLBACK LookProc(HWND h,UINT m,WPARAM w,LPARAM l){if((m==WM_KEYDOWN||m==WM_KEYUP||m==WM_SYSKEYDOWN||m==WM_SYSKEYUP)&&w!=VK_SPACE)return SendMessageW(GetParent(h),m,w,l);
 auto r=CallWindowProcW(oldLookProc,h,m,w,l);if((m==WM_LBUTTONUP||m==WM_CAPTURECHANGED||m==WM_CANCELMODE)&&GetFocus()==h)SetFocus(GetParent(h));return r;}
void SyncLookButton(){HWND parent=Game();if(!parent)return;if(!enabled||!ReviewButtonWanted()){if(lookButton&&(GetWindowLongW(lookButton,GWL_STYLE)&WS_VISIBLE)){if(GetFocus()==lookButton)SetFocus(parent);ShowWindow(lookButton,SW_HIDE);}return;}
 if(!lookButton){lookButton=CreateWindowExW(0,L"BUTTON",LookLabel(),WS_CHILD|WS_TABSTOP|BS_OWNERDRAW,0,0,1,1,parent,(HMENU)(UINT_PTR)LOOK_ID,GetModuleHandleW(nullptr),nullptr);if(lookButton)oldLookProc=(WNDPROC)SetWindowLongPtrW(lookButton,GWLP_WNDPROC,(LONG_PTR)LookProc);}if(!lookButton)return;
 auto v=Viewport(parent);int x=v.x+MulDiv(318,v.w,800),y=v.y+MulDiv(574,v.h,600),w=MulDiv(165,v.w,800),h=MulDiv(24,v.h,600);RECT r{};GetWindowRect(lookButton,&r);MapWindowPoints(nullptr,parent,(POINT*)&r,2);
 if(r.left!=x||r.top!=y||r.right-r.left!=w||r.bottom-r.top!=h){SetWindowPos(lookButton,HWND_TOP,x,y,w,h,SWP_NOACTIVATE);int cut=std::max(3,h/5);POINT pts[]={{cut,0},{w-cut,0},{w,h/2},{w-cut,h},{cut,h},{0,h/2}};auto region=CreatePolygonRgn(pts,6,WINDING);if(region&&!SetWindowRgn(lookButton,region,TRUE))DeleteObject(region);}
 SendMessageW(lookButton,WM_SETFONT,(WPARAM)reviewFont,FALSE);if(!(GetWindowLongW(lookButton,GWL_STYLE)&WS_VISIBLE)){ShowWindow(lookButton,SW_SHOWNOACTIVATE);
  if(logFile){SIZE most{};HDC dc=GetDC(lookButton);auto of=SelectObject(dc,reviewFont);for(auto s:{L"연표: 새 모양",L"연표: 원래 모양"}){SIZE z{};GetTextExtentPoint32W(dc,s,int(wcslen(s)),&z);most.cx=std::max(most.cx,z.cx);most.cy=std::max(most.cy,z.cy);}
   SelectObject(dc,of);ReleaseDC(lookButton,dc);fprintf(logFile,"chron_proto look_button shown look=%s at=%d,%d,%d,%d label=%ldx%ld fit=%d\n",classic?"original":"new",x,y,w,h,most.cx,most.cy,int(most.cx<w-12&&most.cy<h));fflush(logFile);}}}
static void DrawLookButton(const DRAWITEMSTRUCT* di){int saved=SaveDC(di->hDC);RECT r=di->rcItem;auto br=CreateSolidBrush((di->itemState&ODS_SELECTED)?RGB(126,57,70):classic?RGB(48,24,36):RGB(103,37,54));auto pen=CreatePen(PS_SOLID,std::max<int>(1,r.bottom/25),RGB(185,128,135));
 FillRect(di->hDC,&r,br);auto ob=SelectObject(di->hDC,br),op=SelectObject(di->hDC,pen);int cut=std::max<int>(3,r.bottom/5);POINT pts[]={{cut,1},{r.right-cut-1,1},{r.right-1,r.bottom/2},{r.right-cut-1,r.bottom-1},{cut,r.bottom-1},{1,r.bottom/2}};Polygon(di->hDC,pts,6);
 SelectObject(di->hDC,op);SelectObject(di->hDC,ob);DeleteObject(pen);DeleteObject(br);if(reviewFont)SelectObject(di->hDC,reviewFont);SetBkMode(di->hDC,TRANSPARENT);SetTextColor(di->hDC,RGB(249,228,214));
 DrawTextW(di->hDC,LookLabel(),-1,&r,DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);if(di->itemState&ODS_FOCUS){InflateRect(&r,-cut,-4);DrawFocusRect(di->hDC,&r);}RestoreDC(di->hDC,saved);}
// the game window's messages for the button (Layout): drawing it and its click
bool LookMessage(HWND h,UINT msg,WPARAM wp,LPARAM lp){if(!lookButton)return false;if(msg==WM_DRAWITEM&&wp==LOOK_ID&&lp){DrawLookButton((const DRAWITEMSTRUCT*)lp);return true;}
 if(msg==WM_COMMAND&&LOWORD(wp)==LOOK_ID&&HIWORD(wp)==BN_CLICKED&&(HWND)lp==lookButton){classic=!classic;WriteLook();SetWindowTextW(lookButton,LookLabel());InvalidateRect(lookButton,nullptr,FALSE);SetFocus(h);
  if(logFile){fprintf(logFile,"chron_proto look=%s by=config\n",classic?"original":"new");fflush(logFile);}return true;}return false;}
}
