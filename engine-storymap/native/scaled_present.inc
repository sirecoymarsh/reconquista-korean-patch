struct OutputCache {Shadow* source=nullptr;uint64_t revision=0;int w=0,h=0;std::vector<BYTE> pixels;BITMAPINFO info{};};static OutputCache outputCache;
// A WIC source that reads the 4x backing store in place: no per-frame 23 MB copy, and one per band so workers share nothing.
struct MemorySource final:IWICBitmapSource{const BYTE*bits;UINT w,h,pitch;LONG refs=1;
 MemorySource(const BYTE*b,UINT ww,UINT hh,UINT p):bits(b),w(ww),h(hh),pitch(p){}
 HRESULT STDMETHODCALLTYPE QueryInterface(REFIID id,void**out)override{if(!out)return E_POINTER;if(id==__uuidof(IUnknown)||id==__uuidof(IWICBitmapSource)){*out=static_cast<IWICBitmapSource*>(this);AddRef();return S_OK;}*out=nullptr;return E_NOINTERFACE;}
 ULONG STDMETHODCALLTYPE AddRef()override{return ULONG(InterlockedIncrement(&refs));}
 ULONG STDMETHODCALLTYPE Release()override{return ULONG(InterlockedDecrement(&refs));}   // lives on the band's stack, outlives its scaler
 HRESULT STDMETHODCALLTYPE GetSize(UINT*a,UINT*b)override{*a=w;*b=h;return S_OK;}
 HRESULT STDMETHODCALLTYPE GetPixelFormat(WICPixelFormatGUID*f)override{*f=GUID_WICPixelFormat24bppBGR;return S_OK;}
 HRESULT STDMETHODCALLTYPE GetResolution(double*x,double*y)override{*x=*y=96;return S_OK;}
 HRESULT STDMETHODCALLTYPE CopyPalette(IWICPalette*)override{return WINCODEC_ERR_PALETTEUNAVAILABLE;}
 HRESULT STDMETHODCALLTYPE CopyPixels(const WICRect*r,UINT stride,UINT size,BYTE*out)override{WICRect a=r?*r:WICRect{0,0,INT(w),INT(h)};
  if(a.X<0||a.Y<0||a.Width<0||a.Height<0||UINT(a.X+a.Width)>w||UINT(a.Y+a.Height)>h)return E_INVALIDARG;UINT row=UINT(a.Width)*3;
  if(a.Height&&(stride<row||size<stride*UINT(a.Height-1)+row))return E_INVALIDARG;for(INT y=0;y<a.Height;y++)memcpy(out+size_t(y)*stride,bits+size_t(a.Y+y)*pitch+size_t(a.X)*3,row);return S_OK;}
};
// The same Fant scale as one CopyPixels over the area, cut into row bands scaled in parallel (a full 4K frame took ~23 ms on one core).
static HRESULT ScaleBands(Shadow*s,WICRect area,int w,int h,int pitch,BYTE*dst){
 int bands=std::clamp(area.Height/96,1,std::max(1,int(std::thread::hardware_concurrency())));std::vector<HRESULT> results(size_t(bands),S_OK);std::vector<int> ids(static_cast<size_t>(bands));std::iota(ids.begin(),ids.end(),0);
 std::for_each(std::execution::par,ids.begin(),ids.end(),[&](int k){int y0=area.Y+MulDiv(area.Height,k,bands),y1=area.Y+MulDiv(area.Height,k+1,bands);if(y1<=y0)return;
  MemorySource src(s->pixels.data(),UINT(s->b.w),UINT(s->b.h),UINT(s->b.pitch));HRESULT hr;{Microsoft::WRL::ComPtr<IWICBitmapScaler> scale;hr=wic->CreateBitmapScaler(&scale);
  if(SUCCEEDED(hr))hr=scale->Initialize(&src,UINT(w),UINT(h),WICBitmapInterpolationModeFant);WICRect band{area.X,y0,area.Width,y1-y0};size_t offset=size_t(y0)*pitch+size_t(area.X)*3;
  if(SUCCEEDED(hr))hr=scale->CopyPixels(&band,UINT(pitch),UINT(size_t(pitch)*h-offset),dst+offset);}results[size_t(k)]=hr;});
 for(auto hr:results)if(FAILED(hr))return hr;return S_OK;}
static bool ScaledPresent(HDC dc,int x,int y,int w,int h,int sx,int sy,int sw,int sh,Shadow*s,UINT usage,DWORD rop,int*result){
 // Nonstandard crops/effects retain the exact established engine/GDI behavior.
 if(!s||!wic||sx||sy||sw*4!=s->b.w||sh*4!=s->b.h||s->b.format||w<=0||h<=0||uint64_t(w)*h>40000000||rop!=SRCCOPY)return false;
 auto&c=outputCache;bool full=c.source!=s||c.w!=w||c.h!=h;bool changed=full||c.revision!=s->revision;
 if(changed){auto t=Now();int pitch=(w*3+3)&~3;WICRect area{0,0,w,h};if(!full&&s->dirty.w>0&&s->dirty.h>0){
  int left=std::max(0,MulDiv(s->dirty.x,w,sw)-2),top=std::max(0,MulDiv(s->dirty.y,h,sh)-2);int right=std::min(w,(int)ceil(double(s->dirty.x+s->dirty.w)*w/sw)+2),bottom=std::min(h,(int)ceil(double(s->dirty.y+s->dirty.h)*h/sh)+2);area={left,top,right-left,bottom-top};}
 try{c.pixels.resize(size_t(pitch)*h);}catch(const std::bad_alloc&){c.source=nullptr;return false;}
 HRESULT hr=ScaleBands(s,area,w,h,pitch,c.pixels.data());
 // once per perf run: the banded frame must equal the old single CopyPixels over the same area, byte for byte
 static bool parityChecked=false;if(parity&&SUCCEEDED(hr)&&!parityChecked&&area.Width>0&&area.Height>0){parityChecked=true;std::vector<BYTE> ref(c.pixels.size());Microsoft::WRL::ComPtr<IWICBitmap> bitmap;Microsoft::WRL::ComPtr<IWICBitmapScaler> scale;
  HRESULT h2=wic->CreateBitmapFromMemory(s->b.w,s->b.h,GUID_WICPixelFormat24bppBGR,s->b.pitch,UINT(s->pixels.size()),s->pixels.data(),&bitmap);if(SUCCEEDED(h2))h2=wic->CreateBitmapScaler(&scale);if(SUCCEEDED(h2))h2=scale->Initialize(bitmap.Get(),w,h,WICBitmapInterpolationModeFant);
  size_t offset=size_t(area.Y)*pitch+area.X*3;if(SUCCEEDED(h2))h2=scale->CopyPixels(&area,pitch,UINT(ref.size()-offset),ref.data()+offset);bool equal=SUCCEEDED(h2);
  for(int row=area.Y;equal&&row<area.Y+area.Height;row++)equal=!memcmp(c.pixels.data()+size_t(row)*pitch+area.X*3,ref.data()+size_t(row)*pitch+area.X*3,size_t(area.Width)*3);
  if(logFile){fprintf(logFile,"perf_scale_parity equal=%d area=%d,%d,%d,%d hr=%lx\n",equal,area.X,area.Y,area.Width,area.Height,h2);fflush(logFile);}}
 if(FAILED(hr)){c.source=nullptr;if(logFile)fprintf(logFile,"scale_fallback hr=%lx\n",hr);return false;}
 c.source=s;c.revision=s->revision;c.w=w;c.h=h;c.info.bmiHeader={sizeof(BITMAPINFOHEADER),w,-h,1,24,BI_RGB,DWORD(c.pixels.size()),0,0,0,0};s->dirty={};
 if(perf&&logFile){fprintf(logFile,"perf_scale full=%d dirty=%d,%d,%d,%d ms=%.3f revision=%llu\n",full,area.X,area.Y,area.Width,area.Height,Ms(t),c.revision);fflush(logFile);}
 }
 SetStretchBltMode(dc,COLORONCOLOR);*result=StretchDIBits(dc,x,y,w,h,0,0,w,h,c.pixels.data(),&c.info,usage,rop);return true;
}
