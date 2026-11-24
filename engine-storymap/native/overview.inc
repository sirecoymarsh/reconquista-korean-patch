// 연표 whole-table view (10-25, user: 「원본에서 작아지게」, 「원래 크기로 돌아오는 버튼도 만들어서」). The chronicle script only
// ever draws one screen of its table, so the first time the wheel goes below 1x the DLL walks the chronicle across its table
// (set straight into its scroll variables), copies the table part of each finished frame into one picture at 2 pixels a
// unit (about 115 MB, in strips), holding the last frame on screen and keeping input away meanwhile; then it shows that
// picture scaled in the table area with the frame around it live. Dragging pans, a click goes back to 1x with the clicked
// point under the cursor, the wheel keeps zooming, the button returns to 1x. The picture is dropped when the chronicle closes.
// OV_EDGE: the frame shades the outer pixels of the table window, so each position keeps only its inside and the positions
// overlap by that much; only the table's own outer edge keeps them (tools/test_chronicle_overview.py found the seams).
static const int OV_STRIP=64,OV_WAIT=1,OV_EDGE=12;   // canvas rows per strip; finished chronicle frames to wait at each position
struct OvCanvas {int w=0,h=0,pitch=0,xmax=0,ymax=0;std::vector<std::vector<unsigned char>> strips;
 unsigned char* Row(int y){return strips[size_t(y/OV_STRIP)].data()+size_t(y%OV_STRIP)*pitch;}};
static OvCanvas ovCanvas;static std::vector<POINT> ovTiles;static size_t ovNext=0;static int ovWaited=0,ovX0=0,ovY0=0;static LONGLONG ovT0=0;
static double ovPending[5]{};static uint64_t ovGeneration=0;static bool ovDrag=false,ovMoved=false;static POINT ovPress{};static double ovPressX=0,ovPressY=0;
static int OvTableW(){return TBL_X1-TBL_X0+ovCanvas.xmax;}static int OvTableH(){return TBL_Y1-TBL_Y0+ovCanvas.ymax;}
static double OvMinZoom(){return std::min(double(TBL_X1-TBL_X0)/OvTableW(),double(TBL_Y1-TBL_Y0)/OvTableH());}
static void OvClamp(){double vw=(TBL_X1-TBL_X0)/zoomLevel,vh=(TBL_Y1-TBL_Y0)/zoomLevel,W=OvTableW(),H=OvTableH();   // a part wider than the table is centred
 ovX=vw>=W?TBL_X0-(vw-W)/2:std::clamp(ovX,double(TBL_X0),TBL_X0+W-vw);ovY=vh>=H?TBL_Y0-(vh-H)/2:std::clamp(ovY,double(TBL_Y0),TBL_Y0+H-vh);}
static void OverviewFree(){ovCapturing=ovReady=ovDrag=false;std::vector<std::vector<unsigned char>>().swap(ovCanvas.strips);ovCanvas=OvCanvas{};ovTiles.clear();ovGeneration++;}
static void OverviewEnter(double zoom,double sx,double sy,double vx,double vy){if(!ovReady)return;zoomLevel=std::clamp(zoom,OvMinZoom(),0.999);zoomX=zoomY=0;
 ovX=vx-(sx-TBL_X0)/zoomLevel;ovY=vy-(sy-TBL_Y0)/zoomLevel;OvClamp();}
static void OverviewLeave(double x,double y){ChronicleMoveTo(int(lround(x)),int(lround(y)));zoomLevel=1;zoomX=zoomY=0;ovDrag=false;}
static void OverviewBegin(double zoom,double sx,double sy,double vx,double vy){
 int mx=0,my=0;if(ovCapturing||!ChroniclePosition(&ovX0,&ovY0,&mx,&my))return;
 OvCanvas c;c.xmax=std::max(0,mx);c.ymax=std::max(0,my);c.w=(TBL_X1-TBL_X0+c.xmax)*2;c.h=(TBL_Y1-TBL_Y0+c.ymax)*2;c.pitch=(c.w*3+3)&~3;
 try{for(int y=0;y<c.h;y+=OV_STRIP)c.strips.emplace_back(size_t(std::min(OV_STRIP,c.h-y))*c.pitch);}
 catch(const std::bad_alloc&){if(logFile){fprintf(logFile,"overview no_memory canvas=%dx%d\n",c.w,c.h);fflush(logFile);}return;}
 ovCanvas=std::move(c);ovTiles.clear();int bw=TBL_X1-BODY_X-2*OV_EDGE,bh=TBL_Y1-BODY_Y-2*OV_EDGE;std::vector<int> xs,ys;
 for(int x=0;x<ovCanvas.xmax;x+=bw)xs.push_back(x);xs.push_back(ovCanvas.xmax);for(int y=0;y<ovCanvas.ymax;y+=bh)ys.push_back(y);ys.push_back(ovCanvas.ymax);
 for(int y:ys)for(int x:xs)ovTiles.push_back({x,y});
 ovPending[0]=zoom;ovPending[1]=sx;ovPending[2]=sy;ovPending[3]=vx;ovPending[4]=vy;ovNext=0;ovWaited=-1;ovCapturing=true;ovT0=Now();ChronicleMoveTo(ovTiles[0].x,ovTiles[0].y);   // -1: this first move came between presents, so one more frame
 if(oldInput)oldInput(Game(),WM_MOUSEMOVE,0,MAKELPARAM(799,599));   // the cursor over the frame corner, so no cell lights up in the pictures (ToClient too)
 SyncZoomButton();
 if(logFile){fprintf(logFile,"overview capture start tiles=%zu canvas=%dx%d from=%d,%d\n",ovTiles.size(),ovCanvas.w,ovCanvas.h,ovX0,ovY0);fflush(logFile);}}
static void OverviewMore(int notches){ovPending[0]*=pow(1.25,notches);}   // wheel turned during the collecting; OverviewEnter clamps it
// Page rect x0..x1, y0..y1 (logical) of the 4x screen into the canvas at table point vx,vy: each canvas pixel the mean of 2x2.
static void OvCopy(Shadow*s,int x0,int y0,int x1,int y1,int vx,int vy){int cx=(vx-TBL_X0)*2,cy=(vy-TBL_Y0)*2,w=(x1-x0)*2,h=(y1-y0)*2;
 if(cx<0||cy<0||cx+w>ovCanvas.w||cy+h>ovCanvas.h)return;
 for(int r=0;r<h;r++){const unsigned char*a=s->pixels.data()+size_t(y0*4+r*2)*s->b.pitch+size_t(x0)*12,*b=a+s->b.pitch;unsigned char*d=ovCanvas.Row(cy+r)+size_t(cx)*3;
  for(int i=0;i<w;i++,a+=6,b+=6,d+=3)for(int k=0;k<3;k++)d[k]=(unsigned char)((a[k]+a[k+3]+b[k]+b[k+3]+2)>>2);}}
// At each present while capturing (Present): once the chronicle has drawn whole frames at this position, keep its table part.
static void OverviewStep(Shadow*s){
 if(!s||s->b.format||s->b.w!=3200||s->b.h!=2400){OverviewFree();ChronicleMoveTo(ovX0,ovY0);return;}
 if(chronicleShown)ovWaited++;if(ovWaited<OV_WAIT)return;
 POINT t=ovTiles[ovNext];int x0=BODY_X+(t.x>0?OV_EDGE:0),x1=TBL_X1-(t.x<ovCanvas.xmax?OV_EDGE:0),y0=BODY_Y+(t.y>0?OV_EDGE:0),y1=TBL_Y1-(t.y<ovCanvas.ymax?OV_EDGE:0);
 OvCopy(s,x0,y0,x1,y1,x0+t.x,y0+t.y);                                    // body
 if(t.y==0)OvCopy(s,x0,TBL_Y0,x1,BODY_Y,x0+t.x,TBL_Y0);                 // column titles (do not move with y)
 if(t.x==0)OvCopy(s,TBL_X0,y0,BODY_X,y1,TBL_X0,y0+t.y);                 // row titles (do not move with x)
 if(t.x==0&&t.y==0)OvCopy(s,TBL_X0,TBL_Y0,BODY_X,BODY_Y,TBL_X0,TBL_Y0);
 if(++ovNext<ovTiles.size()){ChronicleMoveTo(ovTiles[ovNext].x,ovTiles[ovNext].y);ovWaited=0;SyncZoomButton();return;}
 ChronicleMoveTo(ovX0,ovY0);ovCapturing=false;ovReady=true;ovGeneration++;
 if(logFile){fprintf(logFile,"overview capture done tiles=%zu ms=%.0f\n",ovTiles.size(),Ms(ovT0));fflush(logFile);}
 if(ovPending[0]<0.999)OverviewEnter(ovPending[0],ovPending[1],ovPending[2],ovPending[3],ovPending[4]);   // turned back up meanwhile: stay at 1x
 SyncZoomButton();InvalidateRect(Game(),nullptr,FALSE);}
// While capturing, the window keeps the last frame it showed.
static int OverviewHold(HDC dc,int x,int y,int w,int h,UINT usage){auto&c=outputCache;if(c.w!=w||c.h!=h||c.pixels.empty())return h;SetStretchBltMode(dc,COLORONCOLOR);return StretchDIBits(dc,x,y,w,h,0,0,w,h,c.pixels.data(),&c.info,usage,SRCCOPY);}
// A WIC source over a part of the canvas, read in place from its strips.
struct CanvasSource final:IWICBitmapSource{int x,y,w,h;LONG refs=1;
 CanvasSource(int xx,int yy,int ww,int hh):x(xx),y(yy),w(ww),h(hh){}
 HRESULT STDMETHODCALLTYPE QueryInterface(REFIID id,void**out)override{if(!out)return E_POINTER;if(id==__uuidof(IUnknown)||id==__uuidof(IWICBitmapSource)){*out=static_cast<IWICBitmapSource*>(this);AddRef();return S_OK;}*out=nullptr;return E_NOINTERFACE;}
 ULONG STDMETHODCALLTYPE AddRef()override{return ULONG(InterlockedIncrement(&refs));}
 ULONG STDMETHODCALLTYPE Release()override{return ULONG(InterlockedDecrement(&refs));}   // lives on the band's stack
 HRESULT STDMETHODCALLTYPE GetSize(UINT*a,UINT*b)override{*a=UINT(w);*b=UINT(h);return S_OK;}
 HRESULT STDMETHODCALLTYPE GetPixelFormat(WICPixelFormatGUID*f)override{*f=GUID_WICPixelFormat24bppBGR;return S_OK;}
 HRESULT STDMETHODCALLTYPE GetResolution(double*a,double*b)override{*a=*b=96;return S_OK;}
 HRESULT STDMETHODCALLTYPE CopyPalette(IWICPalette*)override{return WINCODEC_ERR_PALETTEUNAVAILABLE;}
 HRESULT STDMETHODCALLTYPE CopyPixels(const WICRect*r,UINT stride,UINT size,BYTE*out)override{WICRect a=r?*r:WICRect{0,0,w,h};
  if(a.X<0||a.Y<0||a.Width<0||a.Height<0||a.X+a.Width>w||a.Y+a.Height>h)return E_INVALIDARG;UINT row=UINT(a.Width)*3;
  if(a.Height&&(stride<row||size<stride*UINT(a.Height-1)+row))return E_INVALIDARG;
  for(INT i=0;i<a.Height;i++)memcpy(out+size_t(i)*stride,ovCanvas.Row(y+a.Y+i)+size_t(x+a.X)*3,row);return S_OK;}
};
static std::vector<unsigned char> ovImage;static int ovImgW=0,ovImgH=0,ovImgPitch=0;static double ovImgKey[3]{};static uint64_t ovImgGen=~0ull;
// The shown part of the table into a tw x th picture: dark where the part reaches past the table, the canvas scaled in
// parallel row bands (Fant down, cubic up) elsewhere.
static void OvRender(int tw,int th){ovImgPitch=(tw*3+3)&~3;ovImage.assign(size_t(ovImgPitch)*th,0);
 for(int y=0;y<th;y++){auto d=ovImage.data()+size_t(y)*ovImgPitch;for(int x=0;x<tw;x++){d[x*3]=18;d[x*3+1]=14;d[x*3+2]=14;}}
 double vw=(TBL_X1-TBL_X0)/zoomLevel,vh=(TBL_Y1-TBL_Y0)/zoomLevel,W=OvTableW(),H=OvTableH();
 double ix0=std::max(ovX,double(TBL_X0)),ix1=std::min(ovX+vw,TBL_X0+W),iy0=std::max(ovY,double(TBL_Y0)),iy1=std::min(ovY+vh,TBL_Y0+H);if(ix1<=ix0||iy1<=iy0)return;
 int ox0=int(lround((ix0-ovX)/vw*tw)),ox1=int(lround((ix1-ovX)/vw*tw)),oy0=int(lround((iy0-ovY)/vh*th)),oy1=int(lround((iy1-ovY)/vh*th));
 int cx0=std::clamp(int(lround((ix0-TBL_X0)*2)),0,ovCanvas.w),cx1=std::clamp(int(lround((ix1-TBL_X0)*2)),0,ovCanvas.w),cy0=std::clamp(int(lround((iy0-TBL_Y0)*2)),0,ovCanvas.h),cy1=std::clamp(int(lround((iy1-TBL_Y0)*2)),0,ovCanvas.h);
 int ow=std::min(ox1,tw)-ox0,oh=std::min(oy1,th)-oy0,cw=cx1-cx0,ch=cy1-cy0;if(ow<=0||oh<=0||cw<=0||ch<=0)return;bool cubic=ow>cw;
 int bands=std::clamp(oh/96,1,std::max(1,int(std::thread::hardware_concurrency())));std::vector<int> ids(static_cast<size_t>(bands));std::iota(ids.begin(),ids.end(),0);
 std::for_each(std::execution::par,ids.begin(),ids.end(),[&](int k){int y0=MulDiv(oh,k,bands),y1=MulDiv(oh,k+1,bands);if(y1<=y0)return;
  CanvasSource src(cx0,cy0,cw,ch);{Microsoft::WRL::ComPtr<IWICBitmapScaler> scale;if(FAILED(wic->CreateBitmapScaler(&scale)))return;
  HRESULT hr=scale->Initialize(&src,UINT(ow),UINT(oh),cubic?WICBitmapInterpolationModeHighQualityCubic:WICBitmapInterpolationModeFant);if(FAILED(hr)&&cubic)hr=scale->Initialize(&src,UINT(ow),UINT(oh),WICBitmapInterpolationModeFant);
  if(SUCCEEDED(hr)){WICRect band{0,y0,ow,y1-y0};size_t off=size_t(oy0+y0)*ovImgPitch+size_t(ox0)*3;scale->CopyPixels(&band,UINT(ovImgPitch),UINT(ovImage.size()-off),ovImage.data()+off);}}});}
static int OvBlit(HDC dc,int dx,int dy,const unsigned char*bits,int bufW,int pitch,int sx,int sy,int w,int h,UINT usage){if(w<=0||h<=0)return 0;BITMAPINFO bi{};bi.bmiHeader={sizeof(BITMAPINFOHEADER),bufW,-h,1,24,BI_RGB,DWORD(pitch)*DWORD(h),0,0,0,0};
 return StretchDIBits(dc,dx,dy,w,h,sx,0,w,h,bits+size_t(sy)*pitch,&bi,usage,SRCCOPY);}
// ScaledPresent's last step while the whole table is shown: the live frame around the table area, the table picture in it
// (no part drawn twice, so nothing of the hidden live chronicle flashes through).
static int OverviewDraw(HDC dc,int x,int y,int w,int h,UINT usage){auto&c=outputCache;int pitch=(w*3+3)&~3;
 int tx0=MulDiv(TBL_X0,w,800),ty0=MulDiv(TBL_Y0,h,600),tx1=MulDiv(TBL_X1,w,800),ty1=MulDiv(TBL_Y1,h,600),tw=tx1-tx0,th=ty1-ty0;
 if(ovImgW!=tw||ovImgH!=th||ovImgKey[0]!=zoomLevel||ovImgKey[1]!=ovX||ovImgKey[2]!=ovY||ovImgGen!=ovGeneration){auto t=Now();OvRender(tw,th);ovImgW=tw;ovImgH=th;ovImgKey[0]=zoomLevel;ovImgKey[1]=ovX;ovImgKey[2]=ovY;ovImgGen=ovGeneration;
  if(perf&&logFile){fprintf(logFile,"perf_overview_render ms=%.2f size=%dx%d zoom=%.4f\n",Ms(t),tw,th,zoomLevel);fflush(logFile);}}
 SetStretchBltMode(dc,COLORONCOLOR);const unsigned char*base=c.pixels.data();
 OvBlit(dc,x,y,base,w,pitch,0,0,w,ty0,usage);OvBlit(dc,x,y+ty1,base,w,pitch,0,ty1,w,h-ty1,usage);
 OvBlit(dc,x,y+ty0,base,w,pitch,0,ty0,tx0,th,usage);OvBlit(dc,x+tx1,y+ty0,base,w,pitch,tx1,ty0,w-tx1,th,usage);
 OvBlit(dc,x+tx0,y+ty0,ovImage.data(),tw,ovImgPitch,0,0,tw,th,usage);return h;}
// Mouse and arrows while the whole table is shown: they move the picture, never the hidden live chronicle under it.
static bool OverviewInput(UINT msg,WPARAM wp,LPARAM lp){
 if(zoomLevel>=1||!ovReady||!chronicleOpen)return false;HWND g=Game();
 if(msg==WM_KEYDOWN&&(wp==VK_LEFT||wp==VK_RIGHT||wp==VK_UP||wp==VK_DOWN)){ovX+=wp==VK_LEFT?-128:wp==VK_RIGHT?128:0;ovY+=wp==VK_UP?-88:wp==VK_DOWN?88:0;OvClamp();InvalidateRect(g,nullptr,FALSE);return true;}
 if(msg<WM_MOUSEMOVE||msg>WM_MBUTTONDBLCLK)return false;
 auto v=Viewport(g);int x=(short)LOWORD(lp),y=(short)HIWORD(lp);double sx=double(x-v.x)*800/std::max(1,v.w),sy=double(y-v.y)*600/std::max(1,v.h);
 bool inside=sx>=TBL_X0&&sx<TBL_X1&&sy>=TBL_Y0&&sy<TBL_Y1;
 if(msg==WM_LBUTTONDOWN&&inside){ovDrag=true;ovMoved=false;ovPress={x,y};ovPressX=ovX;ovPressY=ovY;return true;}
 if(msg==WM_MOUSEMOVE&&ovDrag){if(!(wp&MK_LBUTTON)){ovDrag=false;return inside;}if(std::abs(x-ovPress.x)+std::abs(y-ovPress.y)>6)ovMoved=true;
  ovX=ovPressX-double(x-ovPress.x)*800/std::max(1,v.w)/zoomLevel;ovY=ovPressY-double(y-ovPress.y)*600/std::max(1,v.h)/zoomLevel;OvClamp();InvalidateRect(g,nullptr,FALSE);return true;}
 if(msg==WM_LBUTTONUP&&ovDrag){ovDrag=false;if(ovMoved&&logFile){fprintf(logFile,"chronicle_overview drag overview=%.1f,%.1f\n",ovX,ovY);fflush(logFile);}if(!ovMoved&&inside){double vx=ovX+(sx-TBL_X0)/zoomLevel,vy=ovY+(sy-TBL_Y0)/zoomLevel;OverviewLeave(vx-sx,vy-sy);SyncZoomButton();InvalidateRect(g,nullptr,FALSE);
  if(logFile){fprintf(logFile,"chronicle_zoom click level=1 table=%.1f,%.1f\n",vx,vy);fflush(logFile);}}return true;}
 return inside;}
// The 「원래 크기로」 button: shown in the 연표 while it is zoomed either way (and as progress while the table is collected).
static WNDPROC oldZoomProc=nullptr;static HFONT zoomFont=nullptr;static int zoomFontPixels=0;
static LRESULT CALLBACK ZoomProc(HWND h,UINT m,WPARAM w,LPARAM l){if((m==WM_KEYDOWN||m==WM_KEYUP||m==WM_SYSKEYDOWN||m==WM_SYSKEYUP)&&w!=VK_SPACE)return SendMessageW(GetParent(h),m,w,l);auto r=CallWindowProcW(oldZoomProc,h,m,w,l);if((m==WM_LBUTTONUP||m==WM_CAPTURECHANGED||m==WM_CANCELMODE)&&GetFocus()==h)SetFocus(GetParent(h));return r;}
static void SyncZoomButton(){HWND parent=Game();if(!parent)return;bool wanted=chronicleOpen&&!fcOpen&&!cproto::Shown()&&(ovCapturing||std::abs(zoomLevel-1)>1e-3);
 if(!wanted){if(zoomButton&&(GetWindowLongW(zoomButton,GWL_STYLE)&WS_VISIBLE)){if(GetFocus()==zoomButton)SetFocus(parent);ShowWindow(zoomButton,SW_HIDE);}return;}
 if(!zoomButton){zoomButton=CreateWindowExW(0,L"BUTTON",L"",WS_CHILD|BS_OWNERDRAW,0,0,1,1,parent,(HMENU)(UINT_PTR)ZOOM_ID,GetModuleHandleW(nullptr),nullptr);if(zoomButton)oldZoomProc=(WNDPROC)SetWindowLongPtrW(zoomButton,GWLP_WNDPROC,(LONG_PTR)ZoomProc);}if(!zoomButton)return;
 if(!(GetWindowLongW(parent,GWL_STYLE)&WS_CLIPCHILDREN))SetWindowLongW(parent,GWL_STYLE,GetWindowLongW(parent,GWL_STYLE)|WS_CLIPCHILDREN);
 auto v=Viewport(parent);int x=v.x+MulDiv(262,v.w,800),y=v.y+MulDiv(26,v.h,600),w=MulDiv(124,v.w,800),h=MulDiv(24,v.h,600);RECT r{};GetWindowRect(zoomButton,&r);MapWindowPoints(nullptr,parent,(POINT*)&r,2);
 if(r.left!=x||r.top!=y||r.right-r.left!=w||r.bottom-r.top!=h){SetWindowPos(zoomButton,HWND_TOP,x,y,w,h,SWP_NOACTIVATE);int cut=std::max(3,h/5);POINT pts[]={{cut,0},{w-cut,0},{w,h/2},{w-cut,h},{cut,h},{0,h/2}};auto region=CreatePolygonRgn(pts,6,WINDING);if(region&&!SetWindowRgn(zoomButton,region,TRUE))DeleteObject(region);}
 int fp=std::max(12,MulDiv(12,v.h,600));if(fp!=zoomFontPixels){HFONT f=CreateFontW(-fp,0,0,0,FW_MEDIUM,FALSE,FALSE,FALSE,HANGUL_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"맑은 고딕");if(f){if(zoomFont)DeleteObject(zoomFont);zoomFont=f;zoomFontPixels=fp;InvalidateRect(zoomButton,nullptr,FALSE);}}
 wchar_t label[64],old[64]{};if(ovCapturing)swprintf_s(label,L"연표 모으는 중 %zu/%zu",ovNext,ovTiles.size());else swprintf_s(label,L"원래 크기로 · %d%%",int(lround(zoomLevel*100)));
 GetWindowTextW(zoomButton,old,64);if(wcscmp(old,label)){SetWindowTextW(zoomButton,label);InvalidateRect(zoomButton,nullptr,FALSE);}
 if(!(GetWindowLongW(zoomButton,GWL_STYLE)&WS_VISIBLE))ShowWindow(zoomButton,SW_SHOWNOACTIVATE);}
static void DrawZoomButton(const DRAWITEMSTRUCT* di){int saved=SaveDC(di->hDC);RECT r=di->rcItem;bool down=(di->itemState&ODS_SELECTED)!=0;
 auto brush=CreateSolidBrush(ovCapturing?RGB(40,34,40):down?RGB(126,57,70):RGB(103,37,54));auto pen=CreatePen(PS_SOLID,std::max<int>(1,r.bottom/25),RGB(185,128,135));FillRect(di->hDC,&r,brush);auto ob=SelectObject(di->hDC,brush),op=SelectObject(di->hDC,pen);
 int cut=std::max<int>(3,r.bottom/5);POINT pts[]={{cut,1},{r.right-cut-1,1},{r.right-1,r.bottom/2},{r.right-cut-1,r.bottom-1},{cut,r.bottom-1},{1,r.bottom/2}};Polygon(di->hDC,pts,6);SelectObject(di->hDC,op);SelectObject(di->hDC,ob);DeleteObject(pen);DeleteObject(brush);
 if(zoomFont)SelectObject(di->hDC,zoomFont);SetBkMode(di->hDC,TRANSPARENT);SetTextColor(di->hDC,RGB(249,228,214));wchar_t label[64]{};GetWindowTextW(di->hwndItem,label,64);DrawTextW(di->hDC,label,-1,&r,DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);RestoreDC(di->hDC,saved);}
static void ZoomButtonClick(){if(ovCapturing)return;
 if(zoomLevel>1){zoomLevel=1;zoomX=zoomY=0;}
 else if(zoomLevel<1){double vw=(TBL_X1-TBL_X0)/zoomLevel,vh=(TBL_Y1-TBL_Y0)/zoomLevel;OverviewLeave(ovX+vw/2-(TBL_X0+TBL_X1)/2.0,ovY+vh/2-(TBL_Y0+TBL_Y1)/2.0);}   // the middle of the shown part stays in the middle
 if(logFile){fprintf(logFile,"chronicle_zoom button level=1\n");fflush(logFile);}SyncZoomButton();InvalidateRect(Game(),nullptr,FALSE);}
// The switch for 연표 원래 화면 (10-26, the user: 「버튼이 F8이니 불편한데 연표창에 따로 스위치 하나 그려줘」): two halves, 4K and
// 원래, the shown one lit; a click on a half picks it (F8 still flips). In the empty space between the branch and the title
// (800x600: 122..196, 28..52), while the 연표 is open.
static WNDPROC oldOriginalProc=nullptr;static HFONT originalFont=nullptr;static int originalFontPixels=0,originalClickX=-1;static const int ORIGINAL_SPLIT=42;   // % for the 4K half
// the half is where the button itself was pressed (its own mouse message, not the cursor: tests post their clicks)
static LRESULT CALLBACK OriginalProc(HWND h,UINT m,WPARAM w,LPARAM l){if((m==WM_KEYDOWN||m==WM_KEYUP||m==WM_SYSKEYDOWN||m==WM_SYSKEYUP)&&w!=VK_SPACE)return SendMessageW(GetParent(h),m,w,l);if(m==WM_LBUTTONDOWN||m==WM_LBUTTONUP)originalClickX=(short)LOWORD(l);
 if(m==WM_ERASEBKGND)return 1;   // the owner draw paints all of it; no grey under the cut corners in a print, no flicker
 auto r=CallWindowProcW(oldOriginalProc,h,m,w,l);if((m==WM_LBUTTONUP||m==WM_CAPTURECHANGED||m==WM_CANCELMODE)&&GetFocus()==h)SetFocus(GetParent(h));return r;}
static void SyncOriginalButton(){HWND parent=Game();if(!parent)return;bool wanted=chronicleOpen&&!fcOpen&&!cproto::Shown();   // not over the new 연표 prototype
 if(!wanted){if(originalButton&&(GetWindowLongW(originalButton,GWL_STYLE)&WS_VISIBLE)){if(GetFocus()==originalButton)SetFocus(parent);ShowWindow(originalButton,SW_HIDE);}return;}
 if(!originalButton){originalButton=CreateWindowExW(0,L"BUTTON",L"",WS_CHILD|BS_OWNERDRAW,0,0,1,1,parent,(HMENU)(UINT_PTR)ORIGINAL_ID,GetModuleHandleW(nullptr),nullptr);if(originalButton)oldOriginalProc=(WNDPROC)SetWindowLongPtrW(originalButton,GWLP_WNDPROC,(LONG_PTR)OriginalProc);}if(!originalButton)return;
 if(!(GetWindowLongW(parent,GWL_STYLE)&WS_CLIPCHILDREN))SetWindowLongW(parent,GWL_STYLE,GetWindowLongW(parent,GWL_STYLE)|WS_CLIPCHILDREN);
 auto v=Viewport(parent);int x=v.x+MulDiv(122,v.w,800),y=v.y+MulDiv(28,v.h,600),w=MulDiv(74,v.w,800),h=MulDiv(24,v.h,600);RECT r{};GetWindowRect(originalButton,&r);MapWindowPoints(nullptr,parent,(POINT*)&r,2);
 if(r.left!=x||r.top!=y||r.right-r.left!=w||r.bottom-r.top!=h){SetWindowPos(originalButton,HWND_TOP,x,y,w,h,SWP_NOACTIVATE);int cut=std::max(3,h/5);POINT pts[]={{cut,0},{w-cut,0},{w,h/2},{w-cut,h},{cut,h},{0,h/2}};auto region=CreatePolygonRgn(pts,6,WINDING);if(region&&!SetWindowRgn(originalButton,region,TRUE))DeleteObject(region);}
 int fp=std::max(12,MulDiv(12,v.h,600));if(fp!=originalFontPixels){HFONT f=CreateFontW(-fp,0,0,0,FW_BOLD,FALSE,FALSE,FALSE,HANGUL_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"맑은 고딕");if(f){if(originalFont)DeleteObject(originalFont);originalFont=f;originalFontPixels=fp;InvalidateRect(originalButton,nullptr,FALSE);}}
 static int shown=-1;if(shown!=int(chronicleOriginal)){shown=int(chronicleOriginal);InvalidateRect(originalButton,nullptr,FALSE);}
 if(!(GetWindowLongW(originalButton,GWL_STYLE)&WS_VISIBLE))ShowWindow(originalButton,SW_SHOWNOACTIVATE);}
static void DrawOriginalButton(const DRAWITEMSTRUCT* di){int saved=SaveDC(di->hDC);HDC dc=di->hDC;RECT r=di->rcItem;int split=MulDiv(r.right,ORIGINAL_SPLIT,100);bool orig=chronicleOriginal;
 {int c=std::max<int>(3,r.bottom/5);POINT hex[]={{c,0},{r.right-c,0},{r.right,r.bottom/2},{r.right-c,r.bottom},{c,r.bottom},{0,r.bottom/2}};BeginPath(dc);Polygon(dc,hex,6);EndPath(dc);SelectClipPath(dc,RGN_AND);}   // as the window region (a print has none)
 RECT left{0,0,split,r.bottom},right{split,0,r.right,r.bottom};auto lit=CreateSolidBrush(RGB(150,52,72)),dim=CreateSolidBrush(RGB(44,18,26));FillRect(dc,orig?&right:&left,lit);FillRect(dc,orig?&left:&right,dim);DeleteObject(lit);DeleteObject(dim);
 auto pen=CreatePen(PS_SOLID,std::max<int>(1,r.bottom/25),RGB(185,128,135));auto op=SelectObject(dc,pen);auto ob=SelectObject(dc,GetStockObject(NULL_BRUSH));
 int cut=std::max<int>(3,r.bottom/5);POINT pts[]={{cut,1},{r.right-cut-1,1},{r.right-1,r.bottom/2},{r.right-cut-1,r.bottom-1},{cut,r.bottom-1},{1,r.bottom/2}};Polygon(dc,pts,6);MoveToEx(dc,split,1,nullptr);LineTo(dc,split,r.bottom-1);
 SelectObject(dc,ob);SelectObject(dc,op);DeleteObject(pen);if(originalFont)SelectObject(dc,originalFont);SetBkMode(dc,TRANSPARENT);
 SetTextColor(dc,orig?RGB(150,118,118):RGB(255,240,228));DrawTextW(dc,L"4K",-1,&left,DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);
 SetTextColor(dc,orig?RGB(255,240,228):RGB(150,118,118));DrawTextW(dc,L"원래",-1,&right,DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);RestoreDC(dc,saved);}
static void OriginalButtonClick(){if(!originalButton)return;RECT r{};GetClientRect(originalButton,&r);   // no press position (the space key): flip
 bool want=originalClickX<0?!chronicleOriginal:originalClickX*100>=r.right*ORIGINAL_SPLIT;originalClickX=-1;if(want!=chronicleOriginal)ToggleOriginal(false);InvalidateRect(originalButton,nullptr,FALSE);}
// perf only: the collected table as a 2x BMP (qa\overview-canvas.bmp), so tests can check it against direct captures.
static void OverviewDump(){if(!ovReady)return;wchar_t path[MAX_PATH];swprintf_s(path,L"%s\\qa",root);CreateDirectoryW(path,nullptr);swprintf_s(path,L"%s\\qa\\overview-canvas.bmp",root);FILE*f=nullptr;if(_wfopen_s(&f,path,L"wb")||!f)return;
 BITMAPINFOHEADER info{sizeof(BITMAPINFOHEADER),ovCanvas.w,-ovCanvas.h,1,24,BI_RGB,DWORD(ovCanvas.pitch)*DWORD(ovCanvas.h),0,0,0,0};BITMAPFILEHEADER head{};head.bfType=0x4d42;head.bfOffBits=sizeof(head)+sizeof(info);head.bfSize=head.bfOffBits+info.biSizeImage;
 fwrite(&head,sizeof(head),1,f);fwrite(&info,sizeof(info),1,f);for(int y=0;y<ovCanvas.h;y++)fwrite(ovCanvas.Row(y),1,size_t(ovCanvas.pitch),f);fclose(f);
 if(logFile){fprintf(logFile,"overview dumped %dx%d table=%d,%d\n",ovCanvas.w,ovCanvas.h,OvTableW(),OvTableH());fflush(logFile);}}
