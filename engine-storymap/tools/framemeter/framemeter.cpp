// framemeter: what actually reaches the screen. Desktop Duplication on the primary monitor; each new desktop frame's region
// (x y w h) is hashed (every 4th pixel), and a frame counts when the region changed. Optionally injects real input (SendInput)
// on the same clock: wheel notches or a drag. Prints a summary and writes every frame to frames.csv.
// framemeter <seconds> <x> <y> <w> <h> <idle|wheel|drag|keys> [cx cy]
#define NOMINMAX
#include <windows.h>
#include <cmath>
#include <d3d11.h>
#include <dxgi1_2.h>
#include <cstdio>
#include <cstdint>
#include <vector>
#include <thread>
#include <atomic>
#include <algorithm>
#include <string>
#pragma comment(lib,"d3d11.lib")
#pragma comment(lib,"dxgi.lib")
static LARGE_INTEGER F;static double Ms(LONGLONG t){return 1000.0*double(t)/double(F.QuadPart);}
static LONGLONG Q(){LARGE_INTEGER t;QueryPerformanceCounter(&t);return t.QuadPart;}
struct Frame{LONGLONG t;bool changed;};
struct Input{LONGLONG t;int kind;};   // 1 wheel, 2 move, 3 key
static std::atomic<bool> stop{false};static std::vector<Input> inputs;
static void Wheel(int d){INPUT in{};in.type=INPUT_MOUSE;in.mi.dwFlags=MOUSEEVENTF_WHEEL;in.mi.mouseData=DWORD(d);SendInput(1,&in,sizeof(in));}
static void MoveTo(int x,int y){INPUT in{};in.type=INPUT_MOUSE;in.mi.dx=LONG(double(x)*65535/(GetSystemMetrics(SM_CXSCREEN)-1));in.mi.dy=LONG(double(y)*65535/(GetSystemMetrics(SM_CYSCREEN)-1));in.mi.dwFlags=MOUSEEVENTF_MOVE|MOUSEEVENTF_ABSOLUTE;SendInput(1,&in,sizeof(in));}
static void Button(bool down){INPUT in{};in.type=INPUT_MOUSE;in.mi.dwFlags=down?MOUSEEVENTF_LEFTDOWN:MOUSEEVENTF_LEFTUP;SendInput(1,&in,sizeof(in));}
static void Key(WORD vk){INPUT in[2]{};in[0].type=in[1].type=INPUT_KEYBOARD;in[0].ki.wVk=in[1].ki.wVk=vk;in[1].ki.dwFlags=KEYEVENTF_KEYUP;SendInput(2,in,sizeof(INPUT));}
static void Driver(std::string mode,double seconds,int cx,int cy){
 LONGLONG t0=Q();auto el=[&]{return Ms(Q()-t0)/1000.0;};
 if(mode=="idle"){while(el()<seconds&&!stop)Sleep(5);return;}
 MoveTo(cx,cy);Sleep(300);
 if(mode=="wheel"){int n=0;while(el()<seconds-0.5&&!stop){int dir=((n/8)%2)?120:-120;inputs.push_back({Q(),1});Wheel(dir);n++;Sleep(250);}}
 else if(mode=="keys"){int n=0;while(el()<seconds-0.5&&!stop){WORD vk=((n/10)%2)?VK_UP:VK_DOWN;inputs.push_back({Q(),3});Key(vk);n++;Sleep(200);}}
 else if(mode=="drag"){Button(true);Sleep(50);double a=0;LONGLONG s=Q();while(el()<seconds-0.5&&!stop){double t=Ms(Q()-s)/1000.0;int y=cy+int(600*sin(t*2.0)),x=cx+int(300*sin(t*1.3));inputs.push_back({Q(),2});MoveTo(x,y);Sleep(4);}Button(false);(void)a;}
}
int main(int argc,char**argv){
 if(argc<7){printf("framemeter <seconds> <x> <y> <w> <h> <idle|wheel|drag|keys> [cx cy]\n");return 2;}
 SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);QueryPerformanceFrequency(&F);timeBeginPeriod(1);
 double seconds=atof(argv[1]);int rx=atoi(argv[2]),ry=atoi(argv[3]),rw=atoi(argv[4]),rh=atoi(argv[5]);std::string mode=argv[6];int cx=argc>8?atoi(argv[7]):rx+rw/2,cy=argc>8?atoi(argv[8]):ry+rh/2;
 ID3D11Device*dev=nullptr;ID3D11DeviceContext*ctx=nullptr;D3D_FEATURE_LEVEL fl;if(FAILED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_HARDWARE,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&dev,&fl,&ctx))){printf("d3d fail\n");return 1;}
 IDXGIDevice*dx=nullptr;dev->QueryInterface(__uuidof(IDXGIDevice),(void**)&dx);IDXGIAdapter*ad=nullptr;dx->GetAdapter(&ad);IDXGIOutput*out=nullptr;ad->EnumOutputs(0,&out);IDXGIOutput1*o1=nullptr;out->QueryInterface(__uuidof(IDXGIOutput1),(void**)&o1);
 IDXGIOutputDuplication*dup=nullptr;HRESULT hr=o1->DuplicateOutput(dev,&dup);if(FAILED(hr)){printf("duplicate fail %lx\n",hr);return 1;}
 DXGI_OUTDUPL_DESC dd;dup->GetDesc(&dd);printf("output %ux%u refresh=%u/%u\n",dd.ModeDesc.Width,dd.ModeDesc.Height,dd.ModeDesc.RefreshRate.Numerator,dd.ModeDesc.RefreshRate.Denominator);
 rw=std::min<int>(rw,int(dd.ModeDesc.Width)-rx);rh=std::min<int>(rh,int(dd.ModeDesc.Height)-ry);
 D3D11_TEXTURE2D_DESC sd{};sd.Width=UINT(rw);sd.Height=UINT(rh);sd.MipLevels=1;sd.ArraySize=1;sd.Format=DXGI_FORMAT_B8G8R8A8_UNORM;sd.SampleDesc.Count=1;sd.Usage=D3D11_USAGE_STAGING;sd.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
 ID3D11Texture2D*stage=nullptr;if(FAILED(dev->CreateTexture2D(&sd,nullptr,&stage))){printf("stage fail\n");return 1;}
 std::vector<Frame> frames;frames.reserve(100000);uint64_t last=0;int lost=0;
 std::thread drv(Driver,mode,seconds,cx,cy);LONGLONG t0=Q();
 while(Ms(Q()-t0)<seconds*1000){DXGI_OUTDUPL_FRAME_INFO fi{};IDXGIResource*res=nullptr;hr=dup->AcquireNextFrame(50,&fi,&res);
  if(hr==DXGI_ERROR_WAIT_TIMEOUT)continue;if(FAILED(hr)){lost++;dup->Release();dup=nullptr;Sleep(50);if(FAILED(o1->DuplicateOutput(dev,&dup))){printf("lost %lx\n",hr);break;}continue;}
  LONGLONG t=Q();if(fi.LastPresentTime.QuadPart){ID3D11Texture2D*tex=nullptr;res->QueryInterface(__uuidof(ID3D11Texture2D),(void**)&tex);D3D11_BOX b{UINT(rx),UINT(ry),0,UINT(rx+rw),UINT(ry+rh),1};ctx->CopySubresourceRegion(stage,0,0,0,0,tex,0,&b);tex->Release();
   D3D11_MAPPED_SUBRESOURCE m;if(SUCCEEDED(ctx->Map(stage,0,D3D11_MAP_READ,0,&m))){uint64_t h=1469598103934665603ull;for(int y=0;y<rh;y+=4){const uint32_t*p=(const uint32_t*)((const char*)m.pData+size_t(y)*m.RowPitch);for(int x=0;x<rw;x+=4){h^=p[x];h*=1099511628211ull;}}ctx->Unmap(stage,0);
    frames.push_back({fi.LastPresentTime.QuadPart?t:t,h!=last});last=h;}}
  res->Release();dup->ReleaseFrame();}
 stop=true;drv.join();
 FILE*f=nullptr;fopen_s(&f,"frames.csv","w");for(auto&x:frames)fprintf(f,"%.3f,%d\n",Ms(x.t-t0),int(x.changed));for(auto&i:inputs)fprintf(f,"input,%.3f,%d\n",Ms(i.t-t0),i.kind);fclose(f);
 std::vector<double> ch;for(auto&x:frames)if(x.changed)ch.push_back(Ms(x.t-t0));
 std::vector<double> gaps;for(size_t i=1;i<ch.size();i++)gaps.push_back(ch[i]-ch[i-1]);
 // only while input runs (from the first input to the last + 300 ms)
 double a=inputs.empty()?0:Ms(inputs.front().t-t0),z=inputs.empty()?seconds*1000:Ms(inputs.back().t-t0)+300;size_t inWin=0;std::vector<double> wg;double prev=-1;
 for(double c:ch)if(c>=a&&c<=z){inWin++;if(prev>=0)wg.push_back(c-prev);prev=c;}
 auto pct=[](std::vector<double> v,double p){if(v.empty())return 0.0;std::sort(v.begin(),v.end());return v[std::min(v.size()-1,size_t(p*double(v.size())))];};
 printf("desktop_frames=%zu changed=%zu lost=%d window_ms=%.0f..%.0f changed_in_window=%zu fps_in_window=%.1f gap_median=%.2f gap_p90=%.2f gap_p99=%.2f gap_max=%.2f over_25ms=%zu\n",frames.size(),ch.size(),lost,a,z,inWin,z>a?inWin*1000.0/(z-a):0,pct(wg,.5),pct(wg,.9),pct(wg,.99),pct(wg,1),size_t(std::count_if(wg.begin(),wg.end(),[](double g){return g>25;})));
 if(mode=="wheel"||mode=="keys"){std::vector<double> lat;size_t j=0;for(size_t k=0;k<inputs.size();k++){double ti=Ms(inputs[k].t-t0),tn=k+1<inputs.size()?Ms(inputs[k+1].t-t0):1e18;while(j<ch.size()&&ch[j]<ti)j++;if(j<ch.size()&&ch[j]<tn)lat.push_back(ch[j]-ti);}
  printf("input_to_first_change n=%zu of %zu median=%.1f p90=%.1f max=%.1f\n",lat.size(),inputs.size(),pct(lat,.5),pct(lat,.9),pct(lat,1));}
 return 0;}
