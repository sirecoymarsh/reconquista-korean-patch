// Native in-client 이야기 지도 (story map). Data storymap.bin (RKSM0002), art storymap\*.png (4x of 800x600).
// Jump preparation, review-save isolation, VM pause and the restart path are the v17 review chart's, unchanged.
// New: presentation in the game's chronicle/backlog idiom, 읽음 (pages actually shown) and 지금 자리.
// 10-27: 다시보기 beside the jump (the block after fcVars), and the jump's fast run under a cover (FCCover).
#include "flow_vars.inc"
#pragma comment(lib,"msimg32.lib")
struct FCInstruction {int parent,fall,taken,visual;};
struct FCChapter {std::wstring id,group,label,cell,extra,title;int page=0,day=0,scene0=0,scenes=0,choices=0,views=0,pages=0;float x0=0,y0=0,x1=0,y1=0;std::vector<int> nodes;};
struct FCNode {int chapter,gid,kind,order,scene=0,value=-1,owner=-1;std::wstring id,label,preview,speaker,text;};
struct FCSelect {int gid,fallback;std::vector<std::pair<int,int>> choices;};
struct FCScene {int chapter,first,count,pages,choices,views;std::wstring bg,snippet;};
struct FCDeco {int page,kind;float x0,y0,x1,y1;COLORREF color;std::wstring main,sub;};
static std::vector<FCInstruction> fcCode;static std::vector<FCChapter> fcChapters;static std::vector<FCNode> fcNodes;static std::vector<std::pair<int,int>> fcEdges;static std::vector<FCSelect> fcSelections;
static std::vector<FCScene> fcScenes;static std::vector<FCDeco> fcDecos;static std::vector<int> fcGidNode;static bool fcLoadTried=false;
// options of each choice/viewpoint node, one per value; a later branch can start in a later scene of the chapter
static std::unordered_map<int,std::vector<int>> fcOptions;
static int fcRoots[3]{},fcTarget=-1,fcVisual=-1,fcPending=-1;static std::unordered_map<int,int> fcRoute,fcValues;
static bool fcOpen=false,fcProtected=false,fcLoading=false,fcQueued=false;static HWND fcWindow=nullptr,fcSearch=nullptr;static std::wstring fcSaveDir,fcStatus;static DWORD fcOpenedTick=0;
static Variable fcVars[]={{FV_ACTIVE,0,0,0},{FV_HERE,0,0,0},{FV_BRANCH,0,0,0},{FV_SELECTION,0,0,0},{FV_ROOT0,0,0,0},{FV_ROOT1,0,0,0},{FV_ROOT2,0,0,0},{FV_BRANCH_VALID,0,0,0}};
// 다시보기 (10-27; the user: 「아니 해당 시나리오를 회상처럼 보려는 거였는데 생전 첨보는 방식이네」, then 「그 장이 끝나면」 and
// 「같이 두기」 for the old jump). The chosen line is reached with the jump below, its fast run under a cover; at the chapter's
// end (or Esc, or 「다시보기 끝내기」 in the map) the player is put back: before, the engine's own save-point snapshot is written
// as $do_save(9996) would (its writer 0x41e9b0); after, $do_load(9996)'s request is made (the file at 0x4fd6c0, 2 at 0x494888)
// and the map opens again on that chapter. Opened at the title, it goes back to the title ("start" without the map's flag).
// 「여기서부터 본편으로」 is the old jump, kept beside it.
static bool fcReplay=false,fcReplayHasSave=false,fcReplayWasProtected=false,fcCover=false,fcTitleQueued=false,fcReturnWait=false;
static int fcReplayChapter=-1,fcReplayStage=0,fcConvert=0,fcReopen=0,fcReopenChapter=-1,fcHereBefore=-1;   // stage: 1 going there, 2 playing, 3 coming back
static ULONGLONG fcCoverSince=0,fcStoryTick=0,fcReplayPlayTick=0,fcReopenArm=0;static std::wstring fcCoverText;static wchar_t fcTitleBefore[256]{};
static const char FC_RETURN[]="savedata\\majiro_9996.sav";static const UINT FC_COVER_TIMER=0x7e61,FC_REOPEN_TIMER=0x7e62,WM_FCREOPEN=WM_APP+0x7e0;
enum {FC_IN_VM,FC_IN_WAIT,FC_IN_STEP};   // where a return is asked from: a script variable write, a wait's message, between two steps
static void FCReplayReturn(const char*why,int ctx);static void FCCover(bool on,const wchar_t*text=nullptr);
static bool FCReplayLeft(int gid){int n=gid>=0&&gid<int(fcGidNode.size())?fcGidNode[gid]:-1;return n>=0&&fcNodes[n].chapter!=fcReplayChapter;}
static void FCLog(const char*msg){if(logFile){fprintf(logFile,"inflow %s pid=%lu hwnd=%p\n",msg,GetCurrentProcessId(),Game());fflush(logFile);}}
static std::wstring FCWide(const std::string&s){int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),int(s.size()),nullptr,0);std::wstring v(n,L' ');if(n)MultiByteToWideChar(CP_UTF8,0,s.data(),int(s.size()),&v[0],n);return v;}

// ------------------------------------------------------------------------------------------------ 읽음 / 지금
static std::vector<unsigned char> fcRead;static int fcHere=-1,fcReadDirty=0;static ULONGLONG fcReadSaved=0;
static bool FCIsRead(int n){return n>=0&&n<int(fcNodes.size())&&!fcRead.empty()&&((fcRead[n>>3]>>(n&7))&1);}
static void FCReadSave(){if(fcRead.empty()||!fcReadDirty)return;wchar_t p[MAX_PATH],t[MAX_PATH];swprintf_s(p,L"%s\\storymap-read.bin",root);swprintf_s(t,L"%s\\storymap-read.tmp",root);FILE*f=nullptr;if(_wfopen_s(&f,t,L"wb")||!f)return;int n=int(fcNodes.size());bool ok=fwrite("RKSR0001",1,8,f)==8&&fwrite(&n,4,1,f)==1&&fwrite(&fcHere,4,1,f)==1&&fwrite(fcRead.data(),1,fcRead.size(),f)==fcRead.size();fclose(f);if(ok&&MoveFileExW(t,p,MOVEFILE_REPLACE_EXISTING)){fcReadDirty=0;fcReadSaved=GetTickCount64();}}
static void FCReadLoad(){fcRead.assign((fcNodes.size()+7)/8,0);wchar_t p[MAX_PATH];swprintf_s(p,L"%s\\storymap-read.bin",root);FILE*f=nullptr;if(_wfopen_s(&f,p,L"rb")||!f)return;char magic[8]{};int n=0,here=-1;if(fread(magic,1,8,f)==8&&!memcmp(magic,"RKSR0001",8)&&fread(&n,4,1,f)==1&&n==int(fcNodes.size())&&fread(&here,4,1,f)==1){if(fread(fcRead.data(),1,fcRead.size(),f)==fcRead.size()&&here>=-1&&here<n)fcHere=here;else fcRead.assign(fcRead.size(),0);}fclose(f);}
static int fcHereChapterLogged=-1;
static void FCMark(int gid){if(gid<0||gid>=int(fcGidNode.size()))return;int n=fcGidNode[gid];if(n<0)return;fcHere=n;if(!FCIsRead(n)){fcRead[n>>3]|=(unsigned char)(1<<(n&7));fcReadDirty++;}
 if(logFile&&fcNodes[n].chapter!=fcHereChapterLogged){fcHereChapterLogged=fcNodes[n].chapter;fprintf(logFile,"inflow here chapter=%d order=%d\n",fcHereChapterLogged,fcNodes[n].order);fflush(logFile);}
 if(fcReadDirty>=40&&GetTickCount64()-fcReadSaved>15000)FCReadSave();}

// ------------------------------------------------------------------------------------------------ data
static bool FCLoad(){if(!fcNodes.empty())return true;if(fcLoadTried)return false;fcLoadTried=true;wchar_t path[MAX_PATH];swprintf_s(path,L"%s\\storymap.bin",root);FILE*f=nullptr;_wfopen_s(&f,path,L"rb");if(!f)return false;fseek(f,0,SEEK_END);long length=ftell(f);fseek(f,0,SEEK_SET);if(length<40||length>64*1024*1024){fclose(f);return false;}std::vector<unsigned char>d(length);bool ok=fread(d.data(),1,length,f)==size_t(length);fclose(f);if(!ok||memcmp(d.data(),"RKSM0002",8))return false;size_t at=8;
 auto integer=[&](){if(at+4>d.size())throw 1;int v;memcpy(&v,d.data()+at,4);at+=4;return v;};auto text=[&](){int n=integer();if(n<0||n>65536||at+n>d.size())throw 1;auto v=FCWide(std::string((char*)d.data()+at,n));at+=n;return v;};
 try{int a=integer(),b=integer(),c=integer(),e=integer(),s=integer();if(a<1||a>1000000||b!=103||c!=44020||e<0||e>500||s<0||s>1000)throw 1;for(auto&r:fcRoots)r=integer();fcCode.reserve(a);for(int i=0;i<a;i++){FCInstruction x{integer(),integer(),integer(),integer()};if(x.parent>=a||x.fall>=a||x.taken>=a)throw 1;fcCode.push_back(x);}
  for(int i=0;i<b;i++){FCChapter x;x.id=text();x.group=text();x.label=text();fcChapters.push_back(x);}
  fcNodes.reserve(c);for(int i=0;i<c;i++){FCNode x{integer(),integer(),integer(),integer()};x.id=text();x.label=text();x.preview=text();if(x.chapter<0||x.chapter>=b||x.gid<0||x.gid>=a||x.order!=i+1)throw 1;fcChapters[x.chapter].nodes.push_back(i);fcNodes.push_back(x);}
  for(int i=0;i<e;i++){int from=integer(),to=integer();if(from<0||from>=b||to<0||to>=b)throw 1;fcEdges.push_back({from,to});}
  for(int i=0;i<s;i++){FCSelect x;x.gid=integer();x.fallback=integer();int n=integer();if(n<0||n>200)throw 1;for(int j=0;j<n;j++){int g=integer(),v=integer();x.choices.push_back({g,v});}fcSelections.push_back(x);}
  int ns=integer();if(ns<1||ns>20000)throw 1;for(int i=0;i<ns;i++){FCScene x{integer(),integer(),integer(),integer(),integer(),integer()};x.bg=text();x.snippet=text();if(x.chapter<0||x.chapter>=b||x.first<0||x.first+x.count>c)throw 1;fcScenes.push_back(x);}
  for(auto&n:fcNodes){n.scene=integer();n.value=integer();n.owner=integer();n.speaker=text();n.text=text();if(n.scene<0||n.scene>=ns||n.owner>=c)throw 1;}
  for(auto&ch:fcChapters){ch.page=integer();ch.x0=integer()/10.f;ch.y0=integer()/10.f;ch.x1=integer()/10.f;ch.y1=integer()/10.f;ch.day=integer();ch.scene0=integer();ch.scenes=integer();ch.cell=text();ch.extra=text();ch.title=text();if(ch.scene0<0||ch.scene0+ch.scenes>ns)throw 1;}
  int nd=integer();if(nd<0||nd>4000)throw 1;for(int i=0;i<nd;i++){FCDeco x{};x.page=integer();x.kind=integer();x.x0=integer()/10.f;x.y0=integer()/10.f;x.x1=integer()/10.f;x.y1=integer()/10.f;int col=integer();x.color=RGB((col>>16)&255,(col>>8)&255,col&255);x.main=text();x.sub=text();fcDecos.push_back(x);}
  if(at+8!=d.size()||memcmp(d.data()+at,"RKSMEND!",8))throw 1;
 }catch(...){fcCode.clear();fcChapters.clear();fcNodes.clear();fcEdges.clear();fcSelections.clear();fcScenes.clear();fcDecos.clear();FCLog("catalogue_rejected");return false;}
 fcGidNode.assign(fcCode.size(),-1);for(int i=0;i<int(fcNodes.size());i++)fcGidNode[fcNodes[i].gid]=i;
 for(auto&ch:fcChapters)for(int i:ch.nodes){int k=fcNodes[i].kind;if(k==0)ch.pages++;else if(k==1)ch.choices++;else if(k==3)ch.views++;}
 for(int i=0;i<int(fcNodes.size());i++){auto&n=fcNodes[i];if(n.kind!=2||n.owner<0)continue;auto&v=fcOptions[n.owner];if(std::none_of(v.begin(),v.end(),[&](int j){return fcNodes[j].value==n.value;}))v.push_back(i);}
 FCReadLoad();FCLog("catalogue_loaded");return true;}
static Variable* FCVar(uint32_t hash,const Variable*write=nullptr){for(auto&v:fcVars)if(v.hash==hash){if(write){int id=write->value;if(hash==FV_BRANCH){auto it=fcRoute.find(id);fcVars[7].value=it!=fcRoute.end();v.value=(it!=fcRoute.end()&&id>=0&&id<int(fcCode.size())&&it->second!=fcCode[id].fall)?1:0;}
 else if(hash==FV_SELECTION){auto it=fcValues.find(id);v.value=it==fcValues.end()?0:it->second;}
 else if(hash==FV_HERE){v.value=id;fcStoryTick=GetTickCount64();
  // the fast run also sets the engine's own fast mode ($is_fast_mode sees 0x494894): the waits that only it skips (the CG
  // pauses' $pause_nodisp@CONSOLE) held every jump there for good (10-27, 00_レコンキスタ_start_3's netu125b_01)
  if(flowFast.value)*(int*)0x494894=1;
  if(!flowFast.value&&fcReplay&&fcReplayStage>=2&&FCReplayLeft(id)){if(fcReplayStage==2)FCReplayReturn("chapter_end",FC_IN_VM);return &v;}   // the replayed chapter is over; the next one's line is not read
  if(!flowFast.value){if(fcNodes.empty())FCLoad();FCMark(id);}if(flowFast.value&&id==fcVisual)flowFast.value=flowWarmStage=1;if(flowFast.value&&id==fcTarget){flowFast.value=flowWarmStage=0;fcVars[0].value=0;flowMark.value=fcPending+1;flowArriveTick=GetTickCount64();fcLoading=false;probeShots=0;FCMark(id);FCCover(false);
   *(int*)0x494894=*(int*)0x494898=*(int*)0x4948a0=0;   // as $reset_fast_mode: the line is read at the player's pace
   if(fcReplay){fcReplayStage=2;fcReplayPlayTick=GetTickCount64();if(!fcTitleBefore[0])GetWindowTextW(Game(),fcTitleBefore,256);SetWindowTextW(Game(),L"레콘키스타 · 다시보기 중 · Esc 끝내기 · F11 이야기 지도");}
   else SetWindowTextW(Game(),L"레콘키스타 · 검수 중 (저장 보호) · F11 이야기 지도");char buf[160];sprintf_s(buf,"arrived order=%d gid=%d protected=%d replay=%d",flowMark.value,id,fcProtected,int(fcReplay));FCLog(buf);}}
 else v.value=write->value;}return &v;}return nullptr;}

// ------------------------------------------------------------------------------------------------ review save isolation (v17)
static bool FCSavedPath(const wchar_t*input,std::wstring&out){if(!fcProtected||!input)return false;wchar_t absolute[1024],base[1024];if(!GetFullPathNameW(input,1024,absolute,nullptr))return false;swprintf_s(base,L"%s\\savedata\\",root);size_t n=wcslen(base);if(_wcsnicmp(absolute,base,n)!=0)return false;out=fcSaveDir+L"\\"+(absolute+n);return true;}
static std::string FCPath(const char*input){if(!fcProtected||!input)return input?input:"";wchar_t w[1024];if(!MultiByteToWideChar(CP_ACP,0,input,-1,w,1024))return input;std::wstring mapped;if(!FCSavedPath(w,mapped))return input;char v[2048];if(!WideCharToMultiByte(CP_ACP,0,mapped.c_str(),-1,v,2048,nullptr,nullptr))return input;return v;}
using FCOpenFn=void*(__cdecl*)(const char*,const char*);static FCOpenFn fcOldFopen;
static bool GlyphCacheOpen(const std::string& path,const char* mode,void* caller);   // text4k.inc: glyph cache files this layer never saw drawn
static void* __cdecl FCFopen(const char*p,const char*m){auto path=FCPath(p);if(fcProtected&&path!=p&&logFile&&m&&strpbrk(m,"wa+")){fprintf(logFile,"inflow savedata_write mode=%s redirected=1\n",m);fflush(logFile);}if(!GlyphCacheOpen(path,m,_ReturnAddress()))return nullptr;return fcOldFopen(path.c_str(),m);}
using FCPathFn=char*(__cdecl*)(char*);static FCPathFn fcOldPath;static char* __cdecl FCEnginePath(char*p){char*q=fcOldPath(p);static std::string mapped;auto v=FCPath(q);if(v==q)return q;mapped=std::move(v);return &mapped[0];}
static HANDLE WINAPI FCCreateFile(LPCSTR p,DWORD a,DWORD s,LPSECURITY_ATTRIBUTES t,DWORD d,DWORD f,HANDLE h){auto v=FCPath(p);return CreateFileA(v.c_str(),a,s,t,d,f,h);}
static BOOL WINAPI FCDeleteFile(LPCSTR p){auto v=FCPath(p);return DeleteFileA(v.c_str());}
static BOOL WINAPI FCCopyFile(LPCSTR a,LPCSTR b,BOOL fail){auto x=FCPath(a),y=FCPath(b);return CopyFileA(x.c_str(),y.c_str(),fail);}
static HANDLE WINAPI FCFindFirst(LPCSTR p,LPWIN32_FIND_DATAA d){auto v=FCPath(p);return FindFirstFileA(v.c_str(),d);}
static bool FCCopyTree(const std::wstring&from,const std::wstring&to){if(!CreateDirectoryW(to.c_str(),nullptr)&&GetLastError()!=ERROR_ALREADY_EXISTS)return false;WIN32_FIND_DATAW data{};HANDLE h=FindFirstFileW((from+L"\\*").c_str(),&data);if(h==INVALID_HANDLE_VALUE)return GetLastError()==ERROR_FILE_NOT_FOUND;bool ok=true;do{if(!wcscmp(data.cFileName,L".")||!wcscmp(data.cFileName,L".."))continue;if(data.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT){ok=false;break;}auto a=from+L"\\"+data.cFileName,b=to+L"\\"+data.cFileName;if(data.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)ok=FCCopyTree(a,b);else ok=CopyFileW(a.c_str(),b.c_str(),TRUE)!=FALSE;if(!ok)break;}while(FindNextFileW(h,&data));FindClose(h);return ok;}
static bool FCPrepare(int node,bool replay=false){if(node<0||node>=int(fcNodes.size()))return false;
 if(!fcProtected){if(!replay||fcSaveDir.empty()){wchar_t path[MAX_PATH];swprintf_s(path,L"%s\\savedata-review-%lu-%llu",root,GetCurrentProcessId(),GetTickCount64());fcSaveDir=path;if(!FCCopyTree(std::wstring(root)+L"\\savedata",fcSaveDir)){fcStatus=L"검수용 저장 폴더를 만들 수 없어 이동하지 않았습니다.";return false;}}   // a replay's saves go to this run's one copy
  fcProtected=true;FCLog(replay?"savedata_isolated replay":"savedata_isolated");}
 std::vector<int>path;int p=fcNodes[node].gid;while(p>=0&&path.size()<=fcCode.size()){path.push_back(p);p=fcCode[p].parent;}if(path.size()>fcCode.size())return false;std::reverse(path.begin(),path.end());fcRoute.clear();fcValues.clear();for(size_t i=0;i+1<path.size();i++)fcRoute[path[i]]=path[i+1];for(auto&s:fcSelections){int v=s.fallback;for(auto b:s.choices){auto it=fcRoute.find(b.first);if(it!=fcRoute.end()&&it->second==fcCode[b.first].fall){v=b.second;break;}}fcValues[s.gid]=v;}
 fcVisual=path.front();for(size_t i=0;i+1<path.size();i++)if(fcCode[path[i]].visual)fcVisual=path[i];fcTarget=fcNodes[node].gid;fcPending=node;for(int i=0;i<3;i++)fcVars[4+i].value=path.front()==fcRoots[i];if(!fcVars[4].value&&!fcVars[5].value&&!fcVars[6].value)return false;fcVars[0].value=1;fcLoading=true;fcQueued=true;return true;}
using FCLoopFn=int(__cdecl*)();static FCLoopFn fcOldLoop;
static int __cdecl FCLoop(){
 if(fcConvert){*(int*)0x494888=fcConvert;fcConvert=0;}   // a return asked between two steps (no wait broke): the request for this one
 if(fcReopen==2){fcReopen=3;fcReopenArm=GetTickCount64();SetTimer(fcWindow,FC_REOPEN_TIMER,150,nullptr);}   // loaded (or restarted): the map again once this step has rebuilt the screen (FCProc)
 if(fcReplay&&fcReplayStage==2&&titleShownTick>fcReplayPlayTick)FCReplayReturn("title_shown",FC_IN_STEP);   // the story went back to the title by itself
 int result=fcOldLoop();
 if(fcConvert&&result==5){result=fcConvert;fcConvert=0;*(int*)0x494888=result;}   // a return asked in a wait: the break it made becomes the request
 if(fcReopen==1&&(result==2||result==5))fcReopen=2;
 if(fcTitleQueued&&result==5){fcTitleQueued=false;strcpy_s((char*)0x513430,260,"start");fcVars[0].value=0;flowFast.value=flowWarmStage=0;configVisibleVar.value=0;FCLog("replay_to_title");return 5;}
 if(fcQueued&&fcPending>=0&&result==5){fcQueued=false;strcpy_s((char*)0x513430,260,"start");flowFast.value=flowWarmStage=2;flowMark.value=0;configVisibleVar.value=0;char b[120];sprintf_s(b,"scheduler_restart order=%d result=%d",fcPending+1,result);FCLog(b);return 5;}return result;}
static bool FCInputMessage(UINT m){return (m>=WM_KEYFIRST&&m<=WM_KEYLAST)||(m>=WM_MOUSEFIRST&&m<=WM_MOUSELAST)||m==WM_INPUT||m==WM_COMMAND||m==WM_TIMER;}

// ------------------------------------------------------------------------------------------------ 다시보기: save, cover, return
static bool FCFileThere(const char*rel){auto p=FCPath(rel);return GetFileAttributesA(p.c_str())!=INVALID_FILE_ATTRIBUTES;}
static bool FCAtTitle(){return titleShownTick>fcStoryTick;}   // a title picture drawn since the story's last line
static bool FCSaveReturn(){if(!*(int*)0x5123dc){FCLog("replay_return_save none");return false;}   // no save-point snapshot to write
 {auto p=FCPath(FC_RETURN);DeleteFileA(p.c_str());}   // an older one is never taken for this one
 *(int*)0x5123d0=0;((void(__cdecl*)(const char*))0x41e9b0)(FC_RETURN);*(int*)0x5123d0=0;   // what $do_save(9996) does
 bool ok=FCFileThere(FC_RETURN);char b[80];sprintf_s(b,"replay_return_save ok=%d protected=%d",int(ok),int(fcProtected));FCLog(b);return ok;}
// the map's window kept over the game while it runs to the line (or back): its last picture dimmed, a line of what happens
static void FCCover(bool on,const wchar_t*text){if(!fcWindow)return;
 if(on){fcCover=true;fcCoverSince=GetTickCount64();fcCoverText=text?text:L"";if(!IsWindowVisible(fcWindow)){RECT r{};GetClientRect(Game(),&r);MoveWindow(fcWindow,0,0,r.right,r.bottom,TRUE);ShowWindow(fcWindow,SW_SHOWNA);}
  SetWindowPos(fcWindow,HWND_TOP,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE);InvalidateRect(fcWindow,nullptr,FALSE);UpdateWindow(fcWindow);SetTimer(fcWindow,FC_COVER_TIMER,500,nullptr);return;}
 if(!fcCover)return;fcCover=false;KillTimer(fcWindow,FC_COVER_TIMER);fcCoverText.clear();if(!fcOpen){ShowWindow(fcWindow,SW_HIDE);SetFocus(Game());}}
static void FCReplayReturn(const char*why,int ctx){if(!fcReplay||fcReplayStage==3)return;fcReplayStage=3;fcProtected=fcReplayWasProtected;fcHere=fcHereBefore;   // saves where they were; 지금 자리 where the player is again
 bool load=fcReplayHasSave&&FCFileThere(FC_RETURN);FCCover(true,L"원래 자리로 돌아가는 중…");
 if(load){strcpy_s((char*)0x4fd6c0,260,FC_RETURN);*(int*)0x5123d0=1;*(int*)0x5123dc=1;*(int*)0x5123e0=1;*(int*)0x4f3a68=0;*(int*)0x4f3a60=0;   // $do_load(9996), but no script result
  for(uintptr_t p=*(uintptr_t*)0x5123d8;p;){uintptr_t next=*(uintptr_t*)(p+0x30);((void(__cdecl*)(void*))0x449ceb)((void*)p);p=next;}*(uintptr_t*)0x5123d8=0;((void(__cdecl*)())0x43ed20)();}
 else fcTitleQueued=true;
 int code=load?2:5;if(ctx==FC_IN_WAIT){*(int*)0x49467c=1;fcConvert=code;}else *(int*)0x494888=code;   // in the VM or before a step: the request itself; in a wait: a break that FCLoop turns into it
 fcReopen=1;fcReopenChapter=fcReplayChapter;if(fcTitleBefore[0]){SetWindowTextW(Game(),fcTitleBefore);fcTitleBefore[0]=0;}
 char b[120];sprintf_s(b,"replay_return why=%s load=%d ctx=%d chapter=%d",why,int(load),ctx,fcReplayChapter);FCLog(b);}

// ------------------------------------------------------------------------------------------------ sound
// The game's own system-SE channel: its menus call $sound3 (0x435290) with on / push / cancel, and the chronicle opens
// with on2. Channel 3 leaves the scene's sound effects alone, and the engine applies the player's SE volume (0 = none).
// The engine only queues the request; its sound thread plays it, so this works while the map holds the game loop.
// QA runtimes (RECON_FLOW_PROBE or storymap-se-mute.flag) zero the one-shot volume multiplier: queued and played at -100 dB.
using FCSeStatFn=int(__cdecl*)(int);static int fcSeMute=-1;
static void FCSound(const char*name,bool hover=false){auto stat=(FCSeStatFn)0x447bd0;int&channel=*(int*)0x569628;int prev=channel,prevState=prev?stat(prev):0;
 if(hover&&prevState)return;   // like the game's buttons: a hover sound only on an idle channel
 if(fcSeMute<0){wchar_t f[MAX_PATH];swprintf_s(f,L"%s\\storymap-se-mute.flag",root);fcSeMute=GetEnvironmentVariableW(L"RECON_FLOW_PROBE",nullptr,0)>0||GetFileAttributesW(f)!=INVALID_FILE_ATTRIBUTES;}
 uintptr_t oldTask=*(uintptr_t*)0x56e1a4,oldVm=*(uintptr_t*)0x56e1a8;int oldMul=*(int*)0x47f798;
 int task[16]{},vm[16]{};Variable stack[8]{};char str[64]{};strcpy_s(str+12,52,name);task[2]=1;vm[4]=8;vm[9]=(int)stack;stack[0]={0,2,3,(int)str};
 *(uintptr_t*)0x56e1a4=(uintptr_t)task;*(uintptr_t*)0x56e1a8=(uintptr_t)vm;if(fcSeMute)*(int*)0x47f798=0;
 ((void(__cdecl*)(int))0x435290)(1);
 *(uintptr_t*)0x56e1a4=oldTask;*(uintptr_t*)0x56e1a8=oldVm;if(fcSeMute)*(int*)0x47f798=oldMul;
 if(logFile){fprintf(logFile,"inflow se %s setting=%d muted=%d prev=%d prev_state=%d handle=%d state=%d\n",name,*(int*)0x566a78,fcSeMute,prev,prevState,channel,channel?stat(channel):0);fflush(logFile);}}

// ------------------------------------------------------------------------------------------------ art
static View fcView{};static float fcK=1;   // 4:3 game area inside the child window; physical px per game px
struct FCImage {HBITMAP bmp=nullptr;void*bits=nullptr;int w=0,h=0;};
// perf: where a map render's time goes (logged with inflow render)
static double fcMsBlend=0,fcMsDim=0,fcMsText=0,fcMsWrap=0,fcMsTile=0,fcMsArt=0;struct FCTimer{double&d;LONGLONG t;FCTimer(double&x):d(x),t(Now()){}~FCTimer(){d+=Ms(t);}};
static FCImage FCDib(int w,int h){FCImage r;BITMAPINFO bi{};bi.bmiHeader={sizeof(BITMAPINFOHEADER),w,-h,1,32,BI_RGB,0,0,0,0,0};r.bmp=CreateDIBSection(nullptr,&bi,DIB_RGB_COLORS,&r.bits,nullptr,0);if(r.bmp){r.w=w;r.h=h;}return r;}
static void FCFree(FCImage&i){if(i.bmp)DeleteObject(i.bmp);i=FCImage{};}
// Decoded once at native size (premultiplied BGRA), scaled copies cached per screen size.
static std::unordered_map<std::wstring,FCImage> fcNative,fcScaled;
static FCImage* FCNative(const std::wstring&name){auto it=fcNative.find(name);if(it!=fcNative.end())return it->second.bmp?&it->second:nullptr;FCTimer ft(fcMsArt);FCImage img;Init();if(wic){wchar_t path[MAX_PATH];swprintf_s(path,L"%s\\storymap\\%s",root,name.c_str());Microsoft::WRL::ComPtr<IWICBitmapDecoder> dec;Microsoft::WRL::ComPtr<IWICBitmapFrameDecode> fr;Microsoft::WRL::ComPtr<IWICFormatConverter> cv;UINT w=0,h=0;
 HRESULT hr=wic->CreateDecoderFromFilename(path,nullptr,GENERIC_READ,WICDecodeMetadataCacheOnLoad,&dec);if(SUCCEEDED(hr))hr=dec->GetFrame(0,&fr);if(SUCCEEDED(hr))hr=fr->GetSize(&w,&h);if(SUCCEEDED(hr))hr=wic->CreateFormatConverter(&cv);if(SUCCEEDED(hr))hr=cv->Initialize(fr.Get(),GUID_WICPixelFormat32bppPBGRA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom);
 if(SUCCEEDED(hr)&&w&&h&&w<=8192&&h<=8192){img=FCDib(int(w),int(h));if(img.bmp&&FAILED(cv->CopyPixels(nullptr,w*4,w*h*4,(BYTE*)img.bits)))FCFree(img);}
 if(!img.bmp&&logFile){fprintf(logFile,"inflow art_missing %ls hr=%08lx\n",name.c_str(),hr);fflush(logFile);}}
 auto&slot=fcNative[name];slot=img;return slot.bmp?&slot:nullptr;}
static FCImage FCResample(const FCImage&src,int sx,int sy,int sw,int sh,int w,int h){FCTimer ft(fcMsArt);FCImage out=FCDib(std::max(1,w),std::max(1,h));if(!out.bmp||!src.bmp)return out;
 // Area-weighted (box) downscale / bilinear upscale on premultiplied pixels; separable.
 auto S=(const unsigned char*)src.bits;auto D=(unsigned char*)out.bits;std::vector<float> tmp(size_t(w)*sh*4);
 auto pass=[&](int n,int m,auto get,auto put){double scale=double(n)/m;for(int o=0;o<m;o++){double a=o*scale,b=(o+1)*scale;if(scale<1){double c=(o+.5)*scale-.5;int i0=std::clamp(int(floor(c)),0,n-1),i1=std::min(i0+1,n-1);double t=std::clamp(c-floor(c),0.0,1.0);for(int ch=0;ch<4;ch++)put(o,ch,float(get(i0,ch)*(1-t)+get(i1,ch)*t));continue;}
  double acc[4]{};int i=int(floor(a));double wsum=0;for(;i<b&&i<n;i++){double lo=std::max(a,double(i)),hi=std::min(b,double(i+1)),wt=hi-lo;if(wt<=0)continue;for(int ch=0;ch<4;ch++)acc[ch]+=get(i,ch)*wt;wsum+=wt;}for(int ch=0;ch<4;ch++)put(o,ch,float(wsum>0?acc[ch]/wsum:0));}};
 // rows of the first pass and columns of the second are independent: each on its own core, same arithmetic (11-25: a page's
 // first draw at 4K resampled its plates one pixel at a time on one core)
 std::vector<int> rows(static_cast<size_t>(sh)),cols(static_cast<size_t>(w));std::iota(rows.begin(),rows.end(),0);std::iota(cols.begin(),cols.end(),0);
 std::for_each(std::execution::par,rows.begin(),rows.end(),[&](int y){auto row=S+size_t(sy+y)*src.w*4+size_t(sx)*4;pass(sw,w,[&](int i,int ch){return double(row[i*4+ch]);},[&](int o,int ch,float v){tmp[(size_t(y)*w+o)*4+ch]=v;});});
 std::for_each(std::execution::par,cols.begin(),cols.end(),[&](int x){pass(sh,h,[&](int i,int ch){return double(tmp[(size_t(i)*w+x)*4+ch]);},[&](int o,int ch,float v){D[(size_t(o)*w+x)*4+ch]=(unsigned char)std::clamp(int(v+.5f),0,255);});});
 return out;}
static FCImage* FCScaled(const std::wstring&name,int w,int h){wchar_t key[300];swprintf_s(key,L"%s|%d|%d",name.c_str(),w,h);auto it=fcScaled.find(key);if(it!=fcScaled.end())return it->second.bmp?&it->second:nullptr;auto n=FCNative(name);FCImage img;if(n)img=FCResample(*n,0,0,n->w,n->h,w,h);auto&slot=fcScaled[key];slot=img;return slot.bmp?&slot:nullptr;}
// A plate drawn wider than its art keeps both pointed ends; only the middle stretches.
static FCImage* FCPlate(const std::wstring&name,int w,int h,float capFrac){wchar_t key[300];swprintf_s(key,L"%s|p%d|%d|%.3f",name.c_str(),w,h,capFrac);auto it=fcScaled.find(key);if(it!=fcScaled.end())return it->second.bmp?&it->second:nullptr;auto n=FCNative(name);FCImage out;
 if(n){int cap=std::max(1,int(n->w*capFrac)),dcap=std::max(1,int(cap*double(h)/n->h));if(dcap*2>=w)dcap=w/3;out=FCDib(w,h);if(out.bmp){auto l=FCResample(*n,0,0,cap,n->h,dcap,h),m=FCResample(*n,cap,0,n->w-2*cap,n->h,w-2*dcap,h),r=FCResample(*n,n->w-cap,0,cap,n->h,dcap,h);
  auto D=(unsigned char*)out.bits;auto blit=[&](FCImage&s,int x0){for(int y=0;y<h;y++)memcpy(D+(size_t(y)*w+x0)*4,(unsigned char*)s.bits+size_t(y)*s.w*4,size_t(s.w)*4);};if(l.bmp&&m.bmp&&r.bmp){blit(l,0);blit(m,dcap);blit(r,w-dcap);}FCFree(l);FCFree(m);FCFree(r);}}
 auto&slot=fcScaled[key];slot=out;return slot.bmp?&slot:nullptr;}
// Interior granite of a plate, used as a fill texture (no outline, no pointed ends).
static FCImage* FCCrop(const std::wstring&name,int sx,int sy,int sw,int sh){int w=std::max(1,int(sw*fcK/4)),h=std::max(1,int(sh*fcK/4));wchar_t key[300];swprintf_s(key,L"%s|c%d,%d,%d,%d|%d|%d",name.c_str(),sx,sy,sw,sh,w,h);auto it=fcScaled.find(key);if(it!=fcScaled.end())return it->second.bmp?&it->second:nullptr;auto n=FCNative(name);FCImage img;if(n&&sx+sw<=n->w&&sy+sh<=n->h)img=FCResample(*n,sx,sy,sw,sh,w,h);auto&slot=fcScaled[key];slot=img;return slot.bmp?&slot:nullptr;}
static void FCClearArt(){for(auto&a:fcScaled)FCFree(a.second);fcScaled.clear();}
// The map's full-screen passes (the chapter page's two dims and its panel took 75 of its 106 ms at 4K through AlphaBlend)
// are done on the back buffer's own pixels, a row at a time on all cores, with AlphaBlend's premultiplied formula; other
// DCs, and a clip that is not one rectangle, keep AlphaBlend.
static FCImage* fcDraw=nullptr;static HDC fcDrawDC=nullptr;   // the back buffer while FCRender draws into it
static bool FCClip(HDC dc,RECT&r){if(dc!=fcDrawDC||!fcDraw||!fcDraw->bits)return false;RECT c{};int k=GetClipBox(dc,&c);if(k!=SIMPLEREGION)return false;
 RECT full{0,0,fcDraw->w,fcDraw->h};IntersectRect(&r,&r,&full);IntersectRect(&r,&r,&c);GdiFlush();return true;}
static inline unsigned FCMul(unsigned v,unsigned k){unsigned t=v*k+128;return (t+(t>>8))>>8;}   // v*k/255, rounded
template<class F> static void FCRows(const RECT&r,F&&row){std::vector<int> ys(size_t(r.bottom-r.top));std::iota(ys.begin(),ys.end(),int(r.top));std::for_each(std::execution::par,ys.begin(),ys.end(),row);}
static void FCBlend(HDC dc,FCImage*img,int x,int y,BYTE alpha=255){FCTimer ft(fcMsBlend);if(!img||!img->bmp)return;
 RECT r{x,y,x+img->w,y+img->h};if(img->bits&&FCClip(dc,r)){if(IsRectEmpty(&r))return;auto*t=fcDraw;
  FCRows(r,[&](int yy){auto s=(const unsigned char*)img->bits+(size_t(yy-y)*img->w+(r.left-x))*4;auto d=(unsigned char*)t->bits+(size_t(yy)*t->w+r.left)*4;
   for(LONG xx=r.left;xx<r.right;xx++,s+=4,d+=4){unsigned b=s[0],g=s[1],c=s[2],a=s[3];if(alpha!=255){b=FCMul(b,alpha);g=FCMul(g,alpha);c=FCMul(c,alpha);a=FCMul(a,alpha);}
    if(!(a|b|g|c))continue;unsigned k=255-a;d[0]=(unsigned char)std::min(255u,b+FCMul(d[0],k));d[1]=(unsigned char)std::min(255u,g+FCMul(d[1],k));d[2]=(unsigned char)std::min(255u,c+FCMul(d[2],k));d[3]=(unsigned char)std::min(255u,a+FCMul(d[3],k));}});return;}
HDC m=CreateCompatibleDC(dc);auto old=SelectObject(m,img->bmp);BLENDFUNCTION bf{AC_SRC_OVER,0,alpha,AC_SRC_ALPHA};AlphaBlend(dc,x,y,img->w,img->h,m,0,0,img->w,img->h,bf);SelectObject(m,old);DeleteDC(m);}
static void FCTile(HDC dc,FCImage*tex,RECT r,BYTE alpha=255){FCTimer ft(fcMsTile);if(!tex||!tex->bmp||r.right<=r.left||r.bottom<=r.top)return;HDC m=CreateCompatibleDC(dc);auto old=SelectObject(m,tex->bmp);BLENDFUNCTION bf{AC_SRC_OVER,0,alpha,AC_SRC_ALPHA};for(int y=r.top;y<r.bottom;y+=tex->h)for(int x=r.left;x<r.right;x+=tex->w){int w=std::min(tex->w,int(r.right-x)),h=std::min(tex->h,int(r.bottom-y));AlphaBlend(dc,x,y,w,h,m,0,0,w,h,bf);}SelectObject(m,old);DeleteDC(m);}

// ------------------------------------------------------------------------------------------------ screen geometry and text
static FCImage fcBack;static FCImage fcSceneShot;
static int PX(float x){return fcView.x+int(floor(x*fcK+.5f));}static int PY(float y){return fcView.y+int(floor(y*fcK+.5f));}
static RECT PR(float x0,float y0,float x1,float y1){return {PX(x0),PY(y0),PX(x1),PY(y1)};}
static float LX(int x){return (x-fcView.x)/fcK;}static float LY(int y){return (y-fcView.y)/fcK;}
static int fcFontsAdded=0;static std::unordered_map<int,HFONT> fcFonts;
static HFONT FCFont(bool serif,float px){if(!fcFontsAdded){fcFontsAdded=1;wchar_t p[MAX_PATH];swprintf_s(p,L"%s\\font\\ReconquistaKRSerif.otf",root);AddFontResourceExW(p,FR_PRIVATE,nullptr);swprintf_s(p,L"%s\\font\\ReconquistaKR.otf",root);AddFontResourceExW(p,FR_PRIVATE,nullptr);}
 int h=std::max(6,int(px*fcK+.5f));int key=(serif?1<<20:0)|h;auto it=fcFonts.find(key);if(it!=fcFonts.end())return it->second;HFONT f=CreateFontW(-h,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_TT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,serif?L"Reconquista KR Serif d00b8d76":L"Reconquista KR d00b8d76");fcFonts[key]=f;return f;}
static void FCClearFonts(){for(auto&f:fcFonts)DeleteObject(f.second);fcFonts.clear();}
static const COLORREF FC_WHITE=RGB(238,234,228),FC_DIM=RGB(156,156,164),FC_UNREAD=RGB(192,190,198),FC_PROMPT=RGB(236,202,176),FC_NAME=RGB(226,192,142),FC_LINE=RGB(118,116,124),FC_LEAF=RGB(244,150,52);
// anchor: 0 left/middle, 1 centre/middle, 2 right/middle
static int FCText(HDC dc,const std::wstring&t,float x,float y,bool serif,float px,COLORREF color,int anchor=0,bool shadow=true,float maxw=0){FCTimer ft(fcMsText);if(t.empty())return 0;auto old=SelectObject(dc,FCFont(serif,px));SetBkMode(dc,TRANSPARENT);SIZE sz{};GetTextExtentPoint32W(dc,t.c_str(),int(t.size()),&sz);int X=PX(x),Y=PY(y)-sz.cy/2;if(anchor==1)X-=sz.cx/2;else if(anchor==2)X-=sz.cx;
 RECT r{X,Y,X+sz.cx+2,Y+sz.cy+2};UINT flags=DT_SINGLELINE|DT_NOPREFIX|DT_TOP|DT_LEFT;if(maxw>0&&sz.cx>int(maxw*fcK)){r.right=X+int(maxw*fcK);flags|=DT_END_ELLIPSIS;}
 int sh=std::max(1,int(fcK*.9f));if(shadow){RECT s=r;OffsetRect(&s,sh,sh);SetTextColor(dc,RGB(0,0,0));DrawTextW(dc,t.c_str(),int(t.size()),&s,flags);}SetTextColor(dc,color);DrawTextW(dc,t.c_str(),int(t.size()),&r,flags);SelectObject(dc,old);return sz.cx;}
static float FCTextW(HDC dc,const std::wstring&t,bool serif,float px){auto old=SelectObject(dc,FCFont(serif,px));SIZE sz{};GetTextExtentPoint32W(dc,t.c_str(),int(t.size()),&sz);SelectObject(dc,old);return sz.cx/fcK;}
static int FCWrapHeight(HDC dc,const std::wstring&t,float w,float px){auto old=SelectObject(dc,FCFont(false,px));RECT r{0,0,int(w*fcK),0};DrawTextW(dc,t.c_str(),int(t.size()),&r,DT_CALCRECT|DT_WORDBREAK|DT_NOPREFIX|DT_EDITCONTROL);SelectObject(dc,old);return r.bottom;}
static void FCWrap(HDC dc,const std::wstring&t,float x,float y,float w,float px,COLORREF c,int maxLines=0){FCTimer ft(fcMsWrap);auto old=SelectObject(dc,FCFont(false,px));SetBkMode(dc,TRANSPARENT);RECT r{PX(x),PY(y),PX(x+w),PY(y)+30000};if(maxLines){TEXTMETRICW tm{};GetTextMetricsW(dc,&tm);r.bottom=r.top+tm.tmHeight*maxLines;}UINT f=DT_WORDBREAK|DT_NOPREFIX|DT_EDITCONTROL|(maxLines?DT_END_ELLIPSIS:0);RECT s=r;int sh=std::max(1,int(fcK*.9f));OffsetRect(&s,sh,sh);SetTextColor(dc,RGB(0,0,0));DrawTextW(dc,t.c_str(),int(t.size()),&s,f);SetTextColor(dc,c);DrawTextW(dc,t.c_str(),int(t.size()),&r,f);SelectObject(dc,old);}
static void FCFill(HDC dc,RECT r,COLORREF c){auto b=CreateSolidBrush(c);FillRect(dc,&r,b);DeleteObject(b);}
static void FCFrameRect(HDC dc,RECT r,COLORREF c,int width=1){auto b=CreateSolidBrush(c);for(int i=0;i<width;i++){FrameRect(dc,&r,b);InflateRect(&r,-1,-1);}DeleteObject(b);}
static void FCDim(HDC dc,RECT r,BYTE alpha){FCTimer ft(fcMsDim);if(FCClip(dc,r)){if(IsRectEmpty(&r))return;auto*t=fcDraw;unsigned k=255u-alpha;
 FCRows(r,[&](int yy){auto d=(unsigned char*)t->bits+(size_t(yy)*t->w+r.left)*4;for(LONG xx=r.left;xx<r.right;xx++,d+=4){d[0]=(unsigned char)FCMul(d[0],k);d[1]=(unsigned char)FCMul(d[1],k);d[2]=(unsigned char)FCMul(d[2],k);d[3]=(unsigned char)(alpha+FCMul(d[3],k));}});return;}
 FCImage one=FCDib(1,1);if(!one.bmp)return;*(DWORD*)one.bits=DWORD(alpha)<<24;HDC m=CreateCompatibleDC(dc);auto old=SelectObject(m,one.bmp);BLENDFUNCTION bf{AC_SRC_OVER,0,255,AC_SRC_ALPHA};AlphaBlend(dc,r.left,r.top,r.right-r.left,r.bottom-r.top,m,0,0,1,1,bf);SelectObject(m,old);DeleteDC(m);FCFree(one);}
static void FCChoiceIcon(HDC dc,float x,float y,int count){float w=12,h=5;POINT p[6]={{PX(x),PY(y+h/2)},{PX(x+2.5f),PY(y)},{PX(x+w-2.5f),PY(y)},{PX(x+w),PY(y+h/2)},{PX(x+w-2.5f),PY(y+h)},{PX(x+2.5f),PY(y+h)}};auto br=CreateSolidBrush(RGB(150,22,44));auto pen=CreatePen(PS_SOLID,std::max(1,int(fcK*.5f)),RGB(214,206,206));auto ob=SelectObject(dc,br);auto op=SelectObject(dc,pen);Polygon(dc,p,6);SelectObject(dc,op);SelectObject(dc,ob);DeleteObject(pen);DeleteObject(br);if(count>1)FCText(dc,std::to_wstring(count),x+w+2.5f,y+h/2,false,9,RGB(226,200,200),0,false);}
static void FCViewIcon(HDC dc,float x,float y,int count){float r=5;RECT b=PR(x,y,x+2*r,y+1.2f*r);int pw=std::max(2,int(fcK*1.4f));auto p1=CreatePen(PS_SOLID,pw,RGB(222,40,70)),p2=CreatePen(PS_SOLID,pw,RGB(110,60,230));auto old=SelectObject(dc,p1);Arc(dc,b.left,b.top,b.right,b.bottom,b.left,(b.top+b.bottom)/2,b.right,(b.top+b.bottom)/2);SelectObject(dc,p2);Arc(dc,b.left,b.top,b.right,b.bottom,b.right,(b.top+b.bottom)/2,b.left,(b.top+b.bottom)/2);SelectObject(dc,old);DeleteObject(p1);DeleteObject(p2);if(count>1)FCText(dc,std::to_wstring(count),x+2*r+2.5f,y+.6f*r,false,9,RGB(200,196,214),0,false);}
static void FCLeaf(HDC dc,float x,float y,float size){auto n=FCNative(L"leaf.png");if(!n)return;int w=int(size*fcK),h=int(size*fcK*n->h/n->w);FCBlend(dc,FCScaled(L"leaf.png",w,h),PX(x),PY(y));}
static void FCCheck(HDC dc,float x,float y,COLORREF c){FCText(dc,L"✓",x,y,false,11,c,0,false);FCText(dc,L"✓",x+.35f,y,false,11,c,0,false);}

// ------------------------------------------------------------------------------------------------ state
static int fcPage=0,fcCursor=-1,fcHover=-1,fcHotPlate=-1;static bool fcHelp=false;
// chapter page: scope -1 = 전체 찾기, else chapter index
static int fcScope=-1,fcSceneSel=0,fcSceneTop=0,fcItemSel=0,fcLineTop=0;static std::wstring fcQuery;static bool fcSearchShown=false;
struct FCItem {int kind,node,top,height;};  // 0 대사 1 선택지 머리 2 선택지 3 시점 머리 4 시점 5 조건 갈림
static std::vector<int> fcSceneList,fcSceneHits;static std::vector<FCItem> fcItems;static int fcItemsHeight=0;
static int ChapterPages(int c){return fcChapters[c].pages;}
static int ReadPages(int c){int n=0;for(int i:fcChapters[c].nodes)if(fcNodes[i].kind==0&&FCIsRead(i))n++;return n;}
static int ScenePagesRead(int s){int n=0;auto&sc=fcScenes[s];for(int i=sc.first;i<sc.first+sc.count;i++)if(fcNodes[i].kind==0&&FCIsRead(i))n++;return n;}
static const wchar_t* Weekday(int d){static const wchar_t* w[]={L"수",L"목",L"금",L"토",L"일",L"월",L"화"};return d>0?w[(d-1)%7]:L"";}
static std::wstring Num(int v){auto s=std::to_wstring(v);for(int i=int(s.size())-3;i>0;i-=3)s.insert(size_t(i),L",");return s;}
static std::wstring DayText(int d){if(d<=0||d>19)return L"";return std::to_wstring(d)+L"일째 ("+Weekday(d)+L")";}
static bool Matches(const FCNode&n){if(fcQuery.empty())return true;auto lower=[](std::wstring s){std::transform(s.begin(),s.end(),s.begin(),towlower);return s;};auto q=lower(fcQuery);return lower(n.speaker+L" "+n.text).find(q)!=std::wstring::npos;}
// what a search can hit: dialogue, choice/viewpoint option text, condition rows (headers carry no text of their own)
static bool NodeHit(const FCNode&n){return (n.kind==0||n.kind==2)&&Matches(n);}

// ------------------------------------------------------------------------------------------------ map page
static bool InCell(const FCChapter&c,float x,float y){return x>=c.x0&&x<c.x1&&y>=c.y0&&y<c.y1;}
static int MapHit(int px,int py){float x=LX(px),y=LY(py);for(int i=0;i<int(fcChapters.size());i++)if(fcChapters[i].page==fcPage&&InCell(fcChapters[i],x,y))return i;return -1;}
static const RECT* PlateRects(){static RECT r[4]={{398,14,494,56},{496,10,658,31},{496,38,658,59},{658,23,728,47}};return r;}
static int PlateHit(int px,int py){float x=LX(px),y=LY(py);auto r=PlateRects();for(int i=0;i<4;i++)if(x>=r[i].left&&x<r[i].right&&y>=r[i].top&&y<r[i].bottom)return i;return -1;}
static void DrawCell(HDC dc,int i){auto&c=fcChapters[i];RECT r=PR(c.x0,c.y0,c.x1,c.y1);FCFill(dc,r,RGB(0,0,0));int read=ReadPages(i),pages=ChapterPages(i);bool done=pages>0&&read==pages,touched=read>0;
 if(i==fcCursor){RECT s=r;InflateRect(&s,-1,-1);FCTile(dc,FCCrop(L"plate_crimson.png",40,30,444,112),s);FCFrameRect(dc,s,RGB(206,200,200),std::max(1,int(fcK*.6f)));}
 else if(i==fcHover){RECT s=r;InflateRect(&s,-1,-1);FCFrameRect(dc,s,RGB(176,170,176),std::max(1,int(fcK*.5f)));}
 float mid=(c.y0+c.y1)/2,tx=c.x0+7;if(done){FCCheck(dc,tx,mid,FC_WHITE);tx+=12;}float size=(c.x1-c.x0)>60?13.f:12.f;tx+=FCText(dc,c.cell,tx,mid,true,size,(touched||i==fcCursor)?FC_WHITE:FC_UNREAD,0,true,c.x1-tx-6)/fcK+6;
 if(!c.extra.empty())tx+=FCText(dc,c.extra,tx,mid+.5f,false,10,RGB(170,168,178),0,false)/fcK+6;
 float rx=c.x1-6;if(c.views){rx-=13+(c.views>1?6:0);FCViewIcon(dc,rx,mid-3.2f,c.views);rx-=4;}if(c.choices){rx-=12+(c.choices>1?2.5f+FCTextW(dc,std::to_wstring(c.choices),false,9):0);FCChoiceIcon(dc,rx,mid-2.5f,c.choices);rx-=4;}
 if(fcHere>=0&&fcNodes[fcHere].chapter==i){FCLeaf(dc,rx-17,mid-8,15);FCText(dc,L"지금",rx-19,mid,false,10,FC_LEAF,2);}
 FCFrameRect(dc,r,FC_LINE);}
static void DrawMap(HDC dc){auto f=FCScaled(L"frame.png",fcView.w,fcView.h);if(f)FCBlend(dc,f,fcView.x,fcView.y);
 FCText(dc,L"이야기 지도",225,44,true,21,FC_WHITE,1);static const wchar_t* plates[4]={nullptr,L"대사 찾기",L"지금 자리로",L"닫기"};float px[4]={445,576,576,693},py[4]={35,20.5f,48.5f,35},ps[4]={14,12,12,13};
 for(int k=0;k<4;k++){std::wstring t=k?plates[k]:(fcPage?L"본편으로":L"최종편으로");if(k==2&&fcReplay)t=L"다시보기 끝내기";FCText(dc,t,px[k],py[k],true,ps[k],k==fcHotPlate?RGB(255,236,200):FC_WHITE,1);}
 FCText(dc,L"갈래",70,79,true,11,FC_WHITE,1);FCText(dc,L"날짜",46,105,true,11,FC_WHITE,1);
 // kind 6 is the lane's thread: cells cover it, so its dots show only on days the lane has no chapter
 for(auto&d:fcDecos)if(d.page==fcPage&&d.kind==0)FCFill(dc,PR(d.x0,d.y0,d.x1,d.y1),FC_LINE);else if(d.page==fcPage&&d.kind==6){float cx=(d.x0+d.x1)/2;for(float y=d.y0+1;y+1<=d.y1;y+=3.5f)FCFill(dc,PR(cx-.5f,y,cx+.5f,y+1),d.color);}
 for(int i=0;i<int(fcChapters.size());i++)if(fcChapters[i].page==fcPage)DrawCell(dc,i);
 auto navy=FCScaled(L"stone_navy.png",int(296*fcK/4),int(1760*fcK/4)),gray=FCScaled(L"stone_gray.png",int(296*fcK/4),int(1760*fcK/4));
 for(auto&d:fcDecos){if(d.page!=fcPage)continue;RECT r=PR(d.x0,d.y0,d.x1,d.y1);float mid=(d.y0+d.y1)/2;
  if(d.kind==1||d.kind==2){FCTile(dc,d.kind==1?navy:gray,r);FCFrameRect(dc,r,RGB(40,36,58));FCText(dc,d.main,d.x0+7,mid,true,12,FC_WHITE);if(!d.sub.empty())FCText(dc,d.sub,d.x1-5,mid,false,10,d.color,2);}
  else if(d.kind==3||d.kind==4){int w=r.right-r.left,h=r.bottom-r.top;FCBlend(dc,FCPlate(d.kind==3?L"plate_crimson.png":L"plate_navy.png",w,h,.07f),r.left,r.top);FCText(dc,d.main,(d.x0+d.x1)/2,mid,true,15,FC_WHITE,1);}
  else if(d.kind==5)FCText(dc,d.main,(d.x0+d.x1)/2,mid,false,10,RGB(176,174,184),1,false);}
 // info strip
 FCFill(dc,PR(94,542,760,562),RGB(0,0,0));FCFill(dc,PR(94,542,760,542.5f),FC_LINE);std::wstring info;int c=fcHover>=0?fcHover:fcCursor;
 if(c>=0){auto&ch=fcChapters[c];info=ch.title;auto day=DayText(ch.day);if(!day.empty())info+=L"  ·  "+day;info+=L"  ·  장면 "+std::to_wstring(ch.scenes)+L"  ·  대사 "+Num(ch.pages)+L"줄";info+=ch.choices?L"  ·  선택지 "+std::to_wstring(ch.choices):L"  ·  선택지 없음";int rd=ReadPages(c);if(rd)info+=rd==ch.pages?L"  ·  다 읽음":L"  ·  읽음 "+Num(rd)+L"/"+Num(ch.pages)+L"줄";}
 if(!fcStatus.empty())info=fcStatus;FCText(dc,info,101,552,false,11,RGB(222,220,228),0,true,520);FCText(dc,fcPage?L"F1 도움말 · Tab 본편 · Enter 열기 · Esc 닫기":L"F1 도움말 · Tab 최종편 · Enter 열기 · Esc 닫기",753,552,false,10,RGB(150,150,160),2,false);}

// ------------------------------------------------------------------------------------------------ chapter page
static const float LX0=262,LX1=764,LTOP=121,LBOT=516,SX0=20,SX1=252,STOP=110,SCARD=52,SSTEP=56;
static void Rebuild(HDC dc){fcSceneList.clear();fcSceneHits.clear();
 int a=0,z=int(fcScenes.size());if(fcScope>=0){a=fcChapters[fcScope].scene0;z=a+fcChapters[fcScope].scenes;}
 for(int s=a;s<z;s++){int hits=0;auto&sc=fcScenes[s];if(!fcQuery.empty()){for(int i=sc.first;i<sc.first+sc.count;i++)if(NodeHit(fcNodes[i]))hits++;if(!hits)continue;}fcSceneList.push_back(s);fcSceneHits.push_back(hits);}
 fcSceneSel=std::clamp(fcSceneSel,0,std::max(0,int(fcSceneList.size())-1));fcItems.clear();fcItemsHeight=0;if(fcSceneList.empty())return;auto&sc=fcScenes[fcSceneList[fcSceneSel]];
 float tw=LX1-(LX0+22)-30;int y=0;auto add=[&](int kind,int node,int h){fcItems.push_back({kind,node,y,h});y+=h;};
 std::vector<int> blocks;
 auto block=[&](int head){if(std::find(blocks.begin(),blocks.end(),head)!=blocks.end())return;auto it=fcOptions.find(head);std::vector<int> opts=it==fcOptions.end()?std::vector<int>{}:it->second;bool hit=fcQuery.empty();for(int j:opts)hit=hit||Matches(fcNodes[j]);if(!hit)return;blocks.push_back(head);bool view=fcNodes[head].kind==3;add(view?3:1,head,int(17*fcK));for(int j:opts)add(view?4:2,j,int(30*fcK));add(-1,-1,int(6*fcK));};
 for(int i=sc.first;i<sc.first+sc.count;i++){auto&n=fcNodes[i];
  if(n.kind==0){if(!Matches(n))continue;int h=FCWrapHeight(dc,n.text.empty()?L"…":n.text,tw,12)+int(((n.speaker.empty()?0:15)+9)*fcK);add(0,i,h+int(fcK));}
  else if(n.kind==1||n.kind==3)block(i);
  else if(n.kind==2&&n.owner>=0){if(fcNodes[n.owner].scene!=n.scene)block(n.owner);}   // its header lives in an earlier scene
  else if(n.kind==2&&Matches(n))add(5,i,int(24*fcK));}
 fcItemsHeight=y;fcItemSel=std::clamp(fcItemSel,0,std::max(0,int(fcItems.size())-1));while(fcItemSel<int(fcItems.size())-1&&(fcItems[fcItemSel].kind<0||fcItems[fcItemSel].kind==1||fcItems[fcItemSel].kind==3))fcItemSel++;}
static int SelectableStep(int from,int d){int i=from;for(int g=0;g<int(fcItems.size());g++){i+=d;if(i<0||i>=int(fcItems.size()))return from;if(fcItems[i].kind==0||fcItems[i].kind==2||fcItems[i].kind==4||fcItems[i].kind==5)return i;}return from;}
static void EnsureItemVisible(){if(fcItems.empty())return;int top=fcItems[fcItemSel].top,bot=top+fcItems[fcItemSel].height,view=int((LBOT-LTOP)*fcK);if(top<fcLineTop)fcLineTop=top;if(bot>fcLineTop+view)fcLineTop=bot-view;fcLineTop=std::clamp(fcLineTop,0,std::max(0,fcItemsHeight-view));}
static void EnsureSceneVisible(){int rows=int((560-STOP)/SSTEP);if(fcSceneSel<fcSceneTop)fcSceneTop=fcSceneSel;if(fcSceneSel>=fcSceneTop+rows)fcSceneTop=fcSceneSel-rows+1;fcSceneTop=std::clamp(fcSceneTop,0,std::max(0,int(fcSceneList.size())-rows));}
static void CaptureScene(){SettleAll();FCFree(fcSceneShot);Bitmap*b=*(Bitmap**)0x56a6a8;if(!Valid(b)||fcView.w<=0)return;fcSceneShot=FCDib(fcView.w,fcView.h);if(!fcSceneShot.bmp)return;HDC screen=GetDC(nullptr),m=CreateCompatibleDC(screen);auto old=SelectObject(m,fcSceneShot.bmp);SetStretchBltMode(m,HALFTONE);SetBrushOrgEx(m,0,0,nullptr);
 auto it=shadows.find(b);if(it!=shadows.end()&&!it->second->pixels.empty())StretchDIBits(m,0,0,fcView.w,fcView.h,0,0,it->second->b.w,it->second->b.h,it->second->pixels.data(),&it->second->info,DIB_RGB_COLORS,SRCCOPY);else StretchDIBits(m,0,0,fcView.w,fcView.h,0,0,b->w,b->h,b->pixels,b->info,DIB_RGB_COLORS,SRCCOPY);
 for(int i=0;i<fcView.w*fcView.h;i++)((DWORD*)fcSceneShot.bits)[i]|=0xff000000u;SelectObject(m,old);DeleteDC(m);ReleaseDC(nullptr,screen);}
static void OpenChapter(int c,int focusNode){FCSound("push");fcPage=2;fcScope=c;fcQuery.clear();if(fcSearch)SetWindowTextW(fcSearch,L"");fcSearchShown=false;fcSceneSel=0;fcSceneTop=0;fcItemSel=0;fcLineTop=0;HDC dc=GetDC(fcWindow);Rebuild(dc);
 if(focusNode>=0){for(int k=0;k<int(fcSceneList.size());k++)if(fcSceneList[k]==fcNodes[focusNode].scene)fcSceneSel=k;Rebuild(dc);for(int k=0;k<int(fcItems.size());k++)if(fcItems[k].node==focusNode)fcItemSel=k;
  /* 11-21: 지금 자리 on a choice/viewpoint block lands on its header or spacer, where Enter and both jump plates did nothing: move to a pickable line */
  if(!fcItems.empty()){int k=fcItems[fcItemSel].kind;if(!(k==0||k==2||k==4||k==5)){int f=SelectableStep(fcItemSel,1);fcItemSel=f!=fcItemSel?f:SelectableStep(fcItemSel,-1);}}}
 ReleaseDC(fcWindow,dc);EnsureSceneVisible();EnsureItemVisible();char b[100];sprintf_s(b,"page=2 chapter=%d scene=%d item=%d",c,fcSceneList.empty()?-1:fcSceneList[fcSceneSel],fcItemSel);FCLog(b);}
static void OpenSearchAll(){FCSound("push");fcPage=2;fcScope=-1;fcQuery.clear();if(fcSearch)SetWindowTextW(fcSearch,L"");fcSceneSel=0;fcSceneTop=0;fcItemSel=0;fcLineTop=0;fcSearchShown=true;HDC dc=GetDC(fcWindow);Rebuild(dc);ReleaseDC(fcWindow,dc);FCLog("page=2 search_all");}
// The panel interior is 65% opaque; over the 185 dim alone the scene's white text still ghosts through the lists.
static void DrawChapter(HDC dc){if(fcSceneShot.bmp)FCBlend(dc,&fcSceneShot,fcView.x,fcView.y);FCDim(dc,PR(0,0,800,600),185);FCDim(dc,PR(16,24,769,576),200);FCBlend(dc,FCScaled(L"panel.png",fcView.w,fcView.h),fcView.x,fcView.y);
 // header: ⚜ banner, prompt line, chevron plates
 FCBlend(dc,FCScaled(L"banner.png",int(808*fcK/4),int(224*fcK/4)),PX(0),PY(22));std::wstring title=fcScope>=0?fcChapters[fcScope].title:L"대사 찾기";float tsize=19;while(tsize>12&&FCTextW(dc,title,true,tsize)>132)tsize-=1;FCText(dc,title,124,50,true,tsize,FC_WHITE,1);
 std::wstring prompt;if(fcScope>=0){auto&ch=fcChapters[fcScope];prompt=DayText(ch.day);auto add=[&](const std::wstring&s){if(!prompt.empty())prompt+=L" · ";prompt+=s;};add(L"장면 "+std::to_wstring(ch.scenes));add(L"대사 "+Num(ch.pages)+L"줄");if(ch.choices)add(L"선택지 "+std::to_wstring(ch.choices));if(ch.views)add(L"시점 전환 "+std::to_wstring(ch.views));}
 else{int hits=0;for(int h:fcSceneHits)hits+=h;prompt=fcQuery.empty()?L"찾을 말을 적으면 모든 장에서 찾습니다.":Num(hits)+L"곳 · 장면 "+Num(int(fcSceneList.size()))+L"개";}
 float psize=13;while(psize>10&&FCTextW(dc,prompt,true,psize)>336)psize-=.5f;FCText(dc,prompt,418,50,true,psize,FC_PROMPT,1,true,340);FCBlend(dc,FCScaled(L"chev_red.png",int(704*fcK/4),int(128*fcK/4)),PX(596),PY(18));FCBlend(dc,FCScaled(L"chev_navy.png",int(704*fcK/4),int(128*fcK/4)),PX(596),PY(50));
 FCText(dc,L"지도로 돌아가기",684,34,true,12,fcHotPlate==10?RGB(255,236,200):FC_WHITE,1);FCText(dc,fcScope>=0?L"이 장 처음부터 다시보기":L"이 장면 처음부터 다시보기",684,66,true,12,fcHotPlate==11?RGB(255,236,200):FC_WHITE,1);FCFill(dc,PR(16,86,770,86.5f),RGB(150,146,150));
 // scene cards (save-slot idiom)
 FCText(dc,fcQuery.empty()?L"장면":L"찾은 장면",22,99,true,12,FC_PROMPT);int rows=int((560-STOP)/SSTEP);if(!fcSceneList.empty()){wchar_t b[64];swprintf_s(b,L"%d개 중 %d~%d",int(fcSceneList.size()),fcSceneTop+1,std::min(int(fcSceneList.size()),fcSceneTop+rows));FCText(dc,b,SX1,99,false,10,RGB(150,150,160),2,false);}
 for(int k=0;k<rows&&fcSceneTop+k<int(fcSceneList.size());k++){int s=fcSceneList[fcSceneTop+k];auto&sc=fcScenes[s];float y=STOP+k*SSTEP;bool sel=fcSceneTop+k==fcSceneSel;RECT r=PR(SX0,y,SX1,y+SCARD);
  auto br=CreateSolidBrush(sel?RGB(112,4,22):RGB(46,8,14));auto pen=CreatePen(PS_SOLID,std::max(1,int(fcK*(sel?.8f:.5f))),sel?RGB(214,206,206):RGB(98,44,52));auto ob=SelectObject(dc,br);auto op=SelectObject(dc,pen);RoundRect(dc,r.left,r.top,r.right,r.bottom,int(8*fcK),int(8*fcK));SelectObject(dc,op);SelectObject(dc,ob);DeleteObject(pen);DeleteObject(br);
  if(!sc.bg.empty()){auto t=FCScaled(L"thumb\\"+sc.bg+L".jpg",int(64*fcK),int(48*fcK));if(t){FCBlend(dc,t,PX(SX0+5),PY(y+2));}}FCFrameRect(dc,PR(SX0+5,y+2,SX0+69,y+50),RGB(170,166,170));
  float tx=SX0+77;int rp=ScenePagesRead(s);if(sc.pages&&rp==sc.pages){FCCheck(dc,tx,y+12,FC_WHITE);tx+=12;}std::wstring name=fcScope>=0?L"장면 "+std::to_wstring(s-fcChapters[fcScope].scene0+1):fcChapters[sc.chapter].cell+L" · "+std::to_wstring(s-fcChapters[sc.chapter].scene0+1);
  FCText(dc,name,tx,y+12,true,12,rp?FC_WHITE:FC_UNREAD,0,true,SX1-tx-48);std::wstring right=fcQuery.empty()?std::to_wstring(sc.pages)+L"줄":std::to_wstring(fcSceneHits[fcSceneTop+k])+L"곳";FCText(dc,right,SX1-6,y+12,false,9,RGB(178,170,176),2,false);
  if(sc.choices)FCChoiceIcon(dc,SX1-44,y+9.5f,sc.choices);if(fcHere>=0&&fcNodes[fcHere].scene==s)FCLeaf(dc,SX1-70,y+5,13);
  FCWrap(dc,sc.snippet,SX0+77,y+23,SX1-SX0-84,10,RGB(214,210,216),2);}
 if(fcSceneList.empty()&&!fcQuery.empty())FCText(dc,L"찾은 곳이 없습니다.",SX0+8,STOP+20,false,11,FC_DIM,0,false);
 // search row + list
 FCText(dc,L"찾기",LX0+4,101,true,11,FC_PROMPT);RECT box=PR(LX0+30,93,LX0+300,109);FCFill(dc,box,RGB(6,6,10));FCFrameRect(dc,box,RGB(126,120,128));if(!fcQuery.empty())FCText(dc,fcQuery,LX0+35,101,false,10.5f,FC_WHITE,0,false,262);else if(GetFocus()!=fcSearch)FCText(dc,L"대사나 이름으로 찾기  (Ctrl+F)",LX0+37,101,false,10,RGB(120,120,130),0,false);
 if(!fcSceneList.empty()){auto&sc=fcScenes[fcSceneList[fcSceneSel]];wchar_t b[96];swprintf_s(b,L"%s · 장면 %d · 대사 %s줄%s",fcChapters[sc.chapter].cell.c_str(),fcSceneList[fcSceneSel]-fcChapters[sc.chapter].scene0+1,Num(sc.pages).c_str(),sc.choices?L" · 선택지 있음":L"");FCText(dc,b,LX1,101,false,10,RGB(158,156,166),2,false);}
 FCFill(dc,PR(LX0,115,LX1,115.5f),RGB(70,66,76));int saved=SaveDC(dc);RECT clip=PR(LX0,LTOP-1,LX1+1,LBOT);IntersectClipRect(dc,clip.left,clip.top,clip.right,clip.bottom);
 float tx=LX0+22,tw=LX1-tx-30;auto hover=FCCrop(L"bar1.png",160,40,1924,144);
 for(int k=0;k<int(fcItems.size());k++){auto&it=fcItems[k];int top=PY(LTOP)+it.top-fcLineTop,bot=top+it.height;if(bot<clip.top||top>clip.bottom||it.kind<0)continue;float y=LY(top);bool sel=k==fcItemSel;auto&n=fcNodes[it.node];
  if(it.kind==0){if(sel){RECT s{PX(LX0)+1,top,PX(LX1)-1,bot-1};FCTile(dc,hover,s,230);FCFrameRect(dc,s,RGB(214,206,206));}if(FCIsRead(it.node))FCCheck(dc,LX0+8,y+(n.speaker.empty()?0:15)+11,FC_WHITE);float yy=y+5;if(!n.speaker.empty()){FCText(dc,n.speaker,tx,yy+5,true,11,FC_NAME);yy+=15;}FCWrap(dc,n.text.empty()?L"…":n.text,tx,yy,tw,12,n.speaker.empty()?RGB(222,220,228):FC_WHITE);
   if(fcHere==it.node){FCLeaf(dc,LX1-52,y+(bot-top)/fcK/2-7,14);FCText(dc,L"지금",LX1-56,y+(bot-top)/fcK/2,false,10,FC_LEAF,2);}FCFill(dc,{PX(LX0+6),bot-1,PX(LX1-6),bot},RGB(52,48,58));}
  else if(it.kind==1||it.kind==3){FCText(dc,it.kind==1?n.label:L"시점 전환",tx,y+9,true,11,FC_PROMPT);FCText(dc,L"고르면 그 갈래로 이어서 봅니다",tx+(it.kind==1?50:56),y+9.5f,false,9,FC_DIM,0,false);}
  else if(it.kind==2||it.kind==4){bool chosen=FCIsRead(it.node);std::wstring art=sel?L"bar1.png":(it.kind==4?(n.value==0?L"bar0.png":L"bar2.png"):(chosen?L"bar2.png":L"bar0.png"));float bw=380,bh=26,bx=(LX0+LX1)/2-bw/2;FCBlend(dc,FCPlate(art,int(bw*fcK),int(bh*fcK),.04f),PX(bx),PY(y+2));FCText(dc,n.text,(LX0+LX1)/2,y+15,it.kind==4,12,FC_WHITE,1);
   if(chosen)FCText(dc,L"예전에 고른 쪽",bx+bw+6,y+15,false,9,RGB(150,170,230),0,false);if(fcHere==it.node)FCLeaf(dc,bx-18,y+7,14);}
  else if(it.kind==5){if(sel){RECT s{PX(LX0)+1,top,PX(LX1)-1,bot-1};FCTile(dc,hover,s,200);}FCText(dc,n.text,tx,y+12,false,11,RGB(176,174,184),0,false);FCFill(dc,{PX(LX0+6),bot-1,PX(LX1-6),bot},RGB(52,48,58));}}
 RestoreDC(dc,saved);if(fcItems.empty())FCText(dc,fcQuery.empty()?L"이 장면에는 대사가 없습니다.":L"찾은 대사가 없습니다.",LX0+22,LTOP+16,false,11,FC_DIM,0,false);
 // scrollbar thumb on the backlog panel's own red track
 int view=int((LBOT-LTOP)*fcK);if(fcItemsHeight>view){float t0=37+(560-37)*float(fcLineTop)/fcItemsHeight,t1=37+(560-37)*float(fcLineTop+view)/fcItemsHeight;FCFill(dc,PR(772.5f,t0,781.5f,t1),RGB(214,196,196));}
 // jump plate
 std::wstring see=L"이 대사부터 다시보기";if(!fcItems.empty()){int k=fcItems[fcItemSel].kind;if(k==2)see=L"이 선택으로 다시보기";else if(k==4)see=L"이 시점으로 다시보기";else if(k==5)see=L"이 갈래부터 다시보기";}
 FCBlend(dc,FCPlate(fcHotPlate==12?L"bar2.png":L"bar1.png",int(230*fcK),int(28*fcK),.04f),PX(363),PY(524));FCText(dc,see,472,538,true,13.5f,FC_WHITE,1);FCText(dc,L"Enter",563,538,false,9,RGB(150,150,160),0,false);
 FCBlend(dc,FCPlate(fcHotPlate==13?L"bar2.png":L"bar1.png",int(170*fcK),int(28*fcK),.04f),PX(600),PY(524));FCText(dc,L"여기서부터 본편으로",685,538,true,12,RGB(214,210,216),1);
 FCText(dc,fcStatus.empty()?(fcReplay?L"다시보기 중 · 이 장이 끝나면 지도로 돌아옵니다":fcProtected?L"본편 검수 중 · 저장은 검수용 폴더로 따로 갑니다":L"다시보기: 이 장이 끝나면 지도로 · 본편으로: 검수용 저장으로 이어짐"):fcStatus,566,562,false,9,RGB(140,140,150),1,false);}

// ------------------------------------------------------------------------------------------------ help (ボタン説明 idiom)
static void DrawHelp(HDC dc){FCDim(dc,PR(0,0,800,600),170);RECT panel=PR(190,118,610,486);FCFill(dc,panel,RGB(10,9,13));FCFrameRect(dc,panel,RGB(150,146,150),std::max(1,int(fcK*.6f)));RECT inner=PR(194,122,606,482);FCFrameRect(dc,inner,RGB(70,64,76));
 struct Row {const wchar_t*keys,*what;};static const Row map[]={{L"칸 누르기 · Enter",L"그 장 열기"},{L"방향키",L"칸 옮기기"},{L"Tab · 보라 판",L"본편 / 최종편"},{L"G · 금빛 판",L"지금 자리로"},{L"Esc · F11",L"닫고 원래 대사로"}};
 static const Row chap[]={{L"↑ ↓",L"대사 고르기"},{L"← →",L"장면 고르기"},{L"Enter · 두 번 누르기",L"그 자리부터 다시보기"},{L"Ctrl+F · 찾기 칸",L"대사 찾기"},{L"Esc · 오른쪽 클릭",L"지도로"}};
 auto block=[&](float y,const wchar_t*head,const Row*rows,int n){FCText(dc,head,214,y,true,13,FC_PROMPT);y+=22;for(int i=0;i<n;i++){FCText(dc,rows[i].keys,226,y,false,11.5f,FC_WHITE,0,false);FCText(dc,rows[i].what,392,y,false,11.5f,RGB(214,210,216),0,false);y+=20;}return y;};
 float y=block(144,L"지도",map,5);y=block(y+8,L"장 안",chap,5);FCFill(dc,PR(214,y+2,586,y+2.5f),RGB(70,64,76));
 FCLeaf(dc,216,y+10,13);FCText(dc,L"지금 자리",233,y+16,false,11,FC_WHITE,0,false);FCCheck(dc,312,y+16,FC_WHITE);FCText(dc,L"다 읽은 곳",326,y+16,false,11,FC_WHITE,0,false);FCBlend(dc,FCPlate(L"bar2.png",int(60*fcK),int(12*fcK),.06f),PX(410),PY(y+10));FCText(dc,L"예전에 고른 선택지",476,y+16,false,11,FC_WHITE,0,false);
 FCText(dc,L"아무 키나 누르면 닫힙니다",400,y+40,false,10,FC_DIM,1,false);}

// ------------------------------------------------------------------------------------------------ render, snapshot, actions
static void FCLayout(){RECT r{};GetClientRect(fcWindow,&r);View v{};int w=r.right,h=r.bottom;if(w*3>h*4)w=h*4/3;else h=w*3/4;v={(r.right-w)/2,(r.bottom-h)/2,w,h};if(v.w!=fcView.w||v.h!=fcView.h){FCClearArt();FCClearFonts();}fcView=v;fcK=std::max(.1f,v.w/800.f);}
static void FCRender(HWND,HDC target){LONGLONG t0=Now();fcMsBlend=fcMsDim=fcMsText=fcMsWrap=fcMsTile=fcMsArt=0;FCLayout();RECT r{};GetClientRect(fcWindow,&r);if(fcBack.w!=r.right||fcBack.h!=r.bottom){FCFree(fcBack);fcBack=FCDib(std::max(1,int(r.right)),std::max(1,int(r.bottom)));}if(!fcBack.bmp)return;HDC dc=CreateCompatibleDC(target);auto old=SelectObject(dc,fcBack.bmp);fcDraw=&fcBack;fcDrawDC=dc;FCFill(dc,r,RGB(0,0,0));
 if(fcPage<2)DrawMap(dc);else DrawChapter(dc);if(fcHelp)DrawHelp(dc);
 if(fcCover&&!fcOpen){FCDim(dc,PR(0,0,800,600),150);FCText(dc,fcCoverText,400,300,true,17,FC_WHITE,1);}   // going to the line / back: the map stays over the fast run
 fcDraw=nullptr;fcDrawDC=nullptr;BitBlt(target,0,0,r.right,r.bottom,dc,0,0,SRCCOPY);SelectObject(dc,old);DeleteDC(dc);
 if(logFile){fprintf(logFile,"inflow render page=%d ms=%.1f size=%ldx%ld blend=%.1f dim=%.1f text=%.1f wrap=%.1f tile=%.1f art=%.1f\n",fcPage,Ms(t0),r.right,r.bottom,fcMsBlend,fcMsDim,fcMsText,fcMsWrap,fcMsTile,fcMsArt);fflush(logFile);}}
static void FCSnapshot(){if(!probe||!GetEnvironmentVariableW(L"RECON_FLOW_PROBE",nullptr,0))return;RECT r{};GetClientRect(fcWindow,&r);if(r.right<1||r.bottom<1)return;BITMAPINFO info{};int stride=(r.right*3+3)&~3;info.bmiHeader={sizeof(BITMAPINFOHEADER),r.right,-r.bottom,1,24,BI_RGB,DWORD(stride*r.bottom),0,0,0,0};void*bits=nullptr;HDC screen=GetDC(fcWindow),dc=CreateCompatibleDC(screen);HBITMAP bitmap=CreateDIBSection(screen,&info,DIB_RGB_COLORS,&bits,nullptr,0);if(!bitmap||!dc){if(bitmap)DeleteObject(bitmap);if(dc)DeleteDC(dc);ReleaseDC(fcWindow,screen);return;}auto old=SelectObject(dc,bitmap);FCRender(fcWindow,dc);GdiFlush();static unsigned shot=0;wchar_t dir[MAX_PATH],path[MAX_PATH];swprintf_s(dir,L"%s\\qa",root);CreateDirectoryW(dir,nullptr);swprintf_s(path,L"%s\\inflow-%02u.bmp",dir,shot++);FILE*f=nullptr;if(!_wfopen_s(&f,path,L"wb")&&f){BITMAPFILEHEADER head{};head.bfType=0x4d42;head.bfOffBits=sizeof(head)+sizeof(BITMAPINFOHEADER);head.bfSize=head.bfOffBits+stride*r.bottom;fwrite(&head,sizeof(head),1,f);fwrite(&info.bmiHeader,sizeof(BITMAPINFOHEADER),1,f);fwrite(bits,1,stride*r.bottom,f);fclose(f);}SelectObject(dc,old);DeleteObject(bitmap);DeleteDC(dc);ReleaseDC(fcWindow,screen);char b[64];sprintf_s(b,"snapshot page=%d",fcPage);FCLog(b);}
static void FCRedraw(){InvalidateRect(fcWindow,nullptr,FALSE);FCSnapshot();}
// replay: 다시보기 (back here at the chapter's end); else 「여기서부터 본편으로」 (the old jump: the game goes on from there)
static void FCJumpNode(int node,bool replay=false){if(node<0)return;FCSound("push");bool fresh=replay&&!fcReplay;   // another scene picked during a replay keeps the first way back
 if(fresh){fcReplayWasProtected=fcProtected;fcHereBefore=fcHere;bool title=FCAtTitle();fcReplayHasSave=!title&&FCSaveReturn();char t[96];sprintf_s(t,"replay_start at_title=%d return_save=%d",int(title),int(fcReplayHasSave));FCLog(t);}
 char b[96];sprintf_s(b,"jump order=%d replay=%d",fcNodes[node].order,int(replay));FCLog(b);
 if(FCPrepare(node,replay)){if(replay){fcReplay=true;fcReplayChapter=fcNodes[node].chapter;fcReplayStage=1;}else if(fcReplay){fcReplay=false;fcReplayStage=0;fcTitleBefore[0]=0;}   // 본편으로 from a replay: the game goes on from there
  fcOpen=false;FCCover(true,replay?L"다시보기 준비 중…":L"그 자리로 가는 중…");}
 else FCRedraw();}
static void FCJump(bool replay=true){if(fcItems.empty())return;auto&it=fcItems[fcItemSel];if(it.kind==0||it.kind==2||it.kind==4||it.kind==5)FCJumpNode(it.node,replay);}
static void ShowSearch(bool show){fcSearchShown=show;if(!fcSearch)return;if(show){RECT b=PR(LX0+33,94.5f,LX0+298,107.5f);MoveWindow(fcSearch,b.left,b.top,b.right-b.left,b.bottom-b.top,TRUE);SendMessageW(fcSearch,WM_SETFONT,(WPARAM)FCFont(false,10.5f),TRUE);ShowWindow(fcSearch,SW_SHOW);SetFocus(fcSearch);}else{ShowWindow(fcSearch,SW_HIDE);SetFocus(fcWindow);}}
static void BackToMap(){FCSound("cancel");ShowSearch(false);if(fcScope>=0)fcCursor=fcScope;fcPage=fcCursor>=0?fcChapters[fcCursor].page:0;fcStatus.clear();FCLog("page=map");FCRedraw();}
static void GoCurrent(){if(fcHere<0){FCSound("cancel");fcStatus=L"아직 읽은 자리가 없습니다.";FCRedraw();return;}int c=fcNodes[fcHere].chapter;if(fcPage<2&&fcCursor==c){OpenChapter(c,fcHere);FCRedraw();return;}FCSound("push");fcCursor=c;fcPage=fcChapters[c].page;fcStatus.clear();FCRedraw();}
static void MoveCursor(int dx,int dy){if(fcCursor<0||fcChapters[fcCursor].page!=fcPage){for(int i=0;i<int(fcChapters.size());i++)if(fcChapters[i].page==fcPage){fcCursor=i;break;}FCSound("on",true);FCRedraw();return;}auto&c=fcChapters[fcCursor];float cx=(c.x0+c.x1)/2,cy=(c.y0+c.y1)/2;int best=-1;float score=1e9f;
 for(int i=0;i<int(fcChapters.size());i++){auto&o=fcChapters[i];if(i==fcCursor||o.page!=fcPage)continue;float ox=(o.x0+o.x1)/2,oy=(o.y0+o.y1)/2;float along=dx?(ox-cx)*dx:(oy-cy)*dy;if(along<=1)continue;
  // a neighbour must share the row (for ←→) or the column (for ↑↓); merged and split cells still overlap
  float overlap=dx?std::min(o.y1,c.y1)-std::max(o.y0,c.y0):std::min(o.x1,c.x1)-std::max(o.x0,c.x0);float cross=overlap>.5f?0.f:20.f-std::min(0.f,overlap);float s=along+cross*8+(dx?fabsf(oy-cy):fabsf(ox-cx))*.3f;if(s<score){score=s;best=i;}}
 if(best>=0){fcCursor=best;FCSound("on",true);}fcStatus.clear();char b[48];sprintf_s(b,"cursor=%d",fcCursor);FCLog(b);FCRedraw();}
static void PickScene(int k);
static void SceneStep(int d){if(fcSceneList.empty())return;PickScene(std::clamp(fcSceneSel+d,0,int(fcSceneList.size())-1));}
static void SearchChanged(){wchar_t q[256]{};if(fcSearch)GetWindowTextW(fcSearch,q,256);fcQuery=q;fcSceneSel=0;fcSceneTop=0;fcItemSel=0;fcLineTop=0;HDC dc=GetDC(fcWindow);Rebuild(dc);ReleaseDC(fcWindow,dc);int hits=0;for(int h:fcSceneHits)hits+=h;char b[96];sprintf_s(b,"search len=%d scenes=%d hits=%d items=%d",int(fcQuery.size()),int(fcSceneList.size()),hits,int(fcItems.size()));FCLog(b);FCRedraw();}
static void SetPage(int p){FCSound("push");fcPage=p;fcHover=-1;fcStatus.clear();char b[32];sprintf_s(b,"page=%d",fcPage);FCLog(b);FCRedraw();}
static void PickScene(int k){if(k!=fcSceneSel)FCSound("on",true);fcSceneSel=k;fcItemSel=0;fcLineTop=0;HDC dc=GetDC(fcWindow);Rebuild(dc);ReleaseDC(fcWindow,dc);EnsureSceneVisible();char b[64];sprintf_s(b,"scene=%d items=%d",fcSceneList.empty()?-1:fcSceneList[fcSceneSel],int(fcItems.size()));FCLog(b);FCRedraw();}
static WNDPROC fcOldEditProc=nullptr;
static bool fcComposing=false;
static bool FCComposing(HWND h){HIMC c=ImmGetContext(h);bool yes=fcComposing;if(c){yes=yes||ImmGetCompositionStringW(c,GCS_COMPSTR,nullptr,0)>0;ImmReleaseContext(h,c);}return yes;}
static LRESULT CALLBACK FCEditProc(HWND h,UINT m,WPARAM w,LPARAM l){
 if(m==WM_IME_STARTCOMPOSITION)fcComposing=true;
 if(m==WM_IME_ENDCOMPOSITION)fcComposing=false;
 if(m==WM_KEYDOWN&&!FCComposing(h)){
  // Enter in the search box commits/searches. It must never jump into a scene.
  if(w==VK_RETURN){SearchChanged();return 0;}
  if(w==VK_UP||w==VK_DOWN||w==VK_PRIOR||w==VK_NEXT||w==VK_ESCAPE||w==VK_F11||w==VK_F1)return SendMessageW(GetParent(h),m,w,l);
 }
 if(m==WM_CHAR&&(w==VK_RETURN||w==VK_ESCAPE||w=='\t'))return 0;
 return CallWindowProcW(fcOldEditProc,h,m,w,l);
}

static void FCClose(){if(fcOpen)FCSound("cancel");fcOpen=false;}
static LRESULT CALLBACK FCProc(HWND h,UINT m,WPARAM w,LPARAM l){int x=(short)LOWORD(l),y=(short)HIWORD(l);
 if(m==WM_TIMER&&w==FC_REOPEN_TIMER){ULONGLONG now=GetTickCount64();   // back from a replay: no picture asked for 0.7 s = the screen is rebuilt, the line waits
  if(fcReopen==3&&((now-lastLoadTick>700&&now-fcReopenArm>500)||now-fcReopenArm>8000)){KillTimer(h,FC_REOPEN_TIMER);fcReopen=0;PostMessageW(Game(),WM_FCREOPEN,0,0);}return 0;}
 if(fcCover&&!fcOpen){if(m==WM_TIMER&&w==FC_COVER_TIMER){if(GetTickCount64()-fcCoverSince>120000){FCLog("cover_timeout");FCCover(false);}return 0;}if(FCInputMessage(m)||m==WM_MOUSELEAVE)return 0;}   // a cover takes no input
 switch(m){case WM_ERASEBKGND:return 1;case WM_PAINT:{PAINTSTRUCT ps;HDC dc=BeginPaint(h,&ps);FCRender(h,dc);EndPaint(h,&ps);return 0;}case WM_PRINT:case WM_PRINTCLIENT:FCRender(h,(HDC)w);return 0;case WM_SIZE:FCLayout();if(fcSearchShown)ShowSearch(true);return 0;
 case WM_CTLCOLOREDIT:{static HBRUSH b=CreateSolidBrush(RGB(6,6,10));SetTextColor((HDC)w,FC_WHITE);SetBkColor((HDC)w,RGB(6,6,10));return (LRESULT)b;}
 case WM_COMMAND:if(HIWORD(w)==EN_CHANGE&&reinterpret_cast<HWND>(l)==fcSearch){SearchChanged();}return 0;
 case WM_KEYDOWN:{if(fcHelp){fcHelp=false;if(w!=VK_F11)FCSound("cancel");FCRedraw();if(w!=VK_F11)return 0;}if(w==VK_F11){FCClose();return 0;}if(w==VK_F1){FCSound("push");fcHelp=true;FCRedraw();return 0;}
  if(fcPage<2){if(w==VK_ESCAPE){FCClose();return 0;}if(w==VK_TAB){SetPage(1-fcPage);return 0;}if(w=='G'){GoCurrent();return 0;}
   if(w==VK_LEFT)MoveCursor(-1,0);else if(w==VK_RIGHT)MoveCursor(1,0);else if(w==VK_UP)MoveCursor(0,-1);else if(w==VK_DOWN)MoveCursor(0,1);else if(w==VK_RETURN&&fcCursor>=0){OpenChapter(fcCursor,fcHere>=0&&fcNodes[fcHere].chapter==fcCursor?fcHere:-1);FCRedraw();}else if(w=='F'&&(GetKeyState(VK_CONTROL)&0x8000)){OpenSearchAll();ShowSearch(true);FCRedraw();}return 0;}
  if(w==VK_ESCAPE){BackToMap();return 0;}if(w==VK_RETURN){FCJump();return 0;}if(w=='F'&&(GetKeyState(VK_CONTROL)&0x8000)){ShowSearch(true);FCRedraw();return 0;}
  if(w==VK_LEFT||w==VK_RIGHT){SceneStep(w==VK_LEFT?-1:1);return 0;}
  if(w==VK_UP||w==VK_DOWN||w==VK_PRIOR||w==VK_NEXT||w==VK_HOME||w==VK_END){if(w==VK_HOME)fcItemSel=SelectableStep(-1,1);else if(w==VK_END)fcItemSel=SelectableStep(int(fcItems.size()),-1);else{int steps=(w==VK_PRIOR||w==VK_NEXT)?8:1,d=(w==VK_UP||w==VK_PRIOR)?-1:1;for(int i=0;i<steps;i++)fcItemSel=SelectableStep(fcItemSel,d);}EnsureItemVisible();char b[80];sprintf_s(b,"item=%d kind=%d order=%d",fcItemSel,fcItems.empty()?-1:fcItems[fcItemSel].kind,fcItems.empty()?-1:fcNodes[fcItems[fcItemSel].node].order);FCLog(b);FCRedraw();return 0;}
  return 0;}
 case WM_MOUSEWHEEL:{POINT p{(short)LOWORD(l),(short)HIWORD(l)};ScreenToClient(h,&p);int delta=(short)HIWORD(w)/WHEEL_DELTA;if(fcPage==2){if(LX(p.x)<SX1+4){fcSceneTop=std::clamp(fcSceneTop-delta,0,std::max(0,int(fcSceneList.size())-int((560-STOP)/SSTEP)));}else{int view=int((LBOT-LTOP)*fcK);fcLineTop=std::clamp(fcLineTop-delta*int(48*fcK),0,std::max(0,fcItemsHeight-view));}FCLog("wheel");FCRedraw();}return 0;}
 case WM_MOUSEMOVE:{TRACKMOUSEEVENT t{sizeof(t),TME_LEAVE,h,0};TrackMouseEvent(&t);int hot=-1,hov=-1;if(fcPage<2){hot=PlateHit(x,y);hov=MapHit(x,y);}else{float lx=LX(x),ly=LY(y);if(lx>=596&&lx<772&&ly>=18&&ly<50)hot=10;else if(lx>=596&&lx<772&&ly>=50&&ly<82)hot=11;else if(lx>=363&&lx<593&&ly>=524&&ly<552)hot=12;else if(lx>=600&&lx<770&&ly>=524&&ly<552)hot=13;}
  if(hot!=fcHotPlate||hov!=fcHover){if(hov!=fcHover){char b[32];sprintf_s(b,"hover=%d",hov);FCLog(b);}if((hot>=0&&hot!=fcHotPlate)||(hov>=0&&hov!=fcHover))FCSound("on",true);fcHotPlate=hot;fcHover=hov;InvalidateRect(h,nullptr,FALSE);}return 0;}
 case WM_MOUSELEAVE:if(fcHotPlate!=-1||fcHover!=-1){fcHotPlate=-1;fcHover=-1;InvalidateRect(h,nullptr,FALSE);}return 0;
 case WM_RBUTTONUP:if(fcHelp){fcHelp=false;FCSound("cancel");FCRedraw();return 0;}if(fcPage==2)BackToMap();else FCClose();return 0;
 case WM_LBUTTONDOWN:SetFocus(fcSearchShown&&fcPage==2?fcSearch:h);return 0;
 case WM_LBUTTONUP:{if(fcHelp){fcHelp=false;FCSound("cancel");FCRedraw();return 0;}float lx=LX(x),ly=LY(y);
  if(fcPage<2){int p=PlateHit(x,y);if(p==0){SetPage(1-fcPage);return 0;}if(p==1){OpenSearchAll();ShowSearch(true);FCRedraw();return 0;}if(p==2){if(fcReplay){fcReturnWait=true;FCClose();}else GoCurrent();return 0;}/* 다시보기 끝내기 during a replay */if(p==3){FCClose();return 0;}int c=MapHit(x,y);if(c>=0){fcCursor=c;OpenChapter(c,fcHere>=0&&fcNodes[fcHere].chapter==c?fcHere:-1);FCRedraw();}return 0;}
  if(lx>=596&&lx<772&&ly>=18&&ly<50){BackToMap();return 0;}
  if(lx>=596&&lx<772&&ly>=50&&ly<82){if(fcScope>=0&&!fcChapters[fcScope].nodes.empty())FCJumpNode(fcChapters[fcScope].nodes.front(),true);else if(!fcSceneList.empty())FCJumpNode(fcScenes[fcSceneList[fcSceneSel]].first,true);return 0;}
  if(lx>=363&&lx<593&&ly>=524&&ly<552){FCJump(true);return 0;}if(lx>=600&&lx<770&&ly>=524&&ly<552){FCJump(false);return 0;}
  if(lx>=LX0+30&&lx<LX0+300&&ly>=93&&ly<109){ShowSearch(true);FCRedraw();return 0;}
  if(lx>=SX0&&lx<SX1&&ly>=STOP){int k=fcSceneTop+int((ly-STOP)/SSTEP);if(k<int(fcSceneList.size())&&ly-STOP-(k-fcSceneTop)*SSTEP<SCARD)PickScene(k);return 0;}
  if(lx>=LX0&&lx<LX1&&ly>=LTOP&&ly<LBOT){int py=y-PY(LTOP)+fcLineTop;for(int k=0;k<int(fcItems.size());k++)if(py>=fcItems[k].top&&py<fcItems[k].top+fcItems[k].height&&fcItems[k].kind!=1&&fcItems[k].kind!=3&&fcItems[k].kind>=0){fcItemSel=k;char b[80];sprintf_s(b,"item=%d kind=%d order=%d",k,fcItems[k].kind,fcNodes[fcItems[k].node].order);FCLog(b);FCRedraw();break;}}return 0;}
 case WM_LBUTTONDBLCLK:{float lx=LX(x),ly=LY(y);if(fcPage==2){if(lx>=LX0&&lx<LX1&&ly>=LTOP&&ly<LBOT){FCJump();return 0;}if(lx>=SX0&&lx<SX1&&ly>=STOP&&!fcSceneList.empty()){FCJumpNode(fcScenes[fcSceneList[fcSceneSel]].first,true);return 0;}}return 0;}
 case WM_CLOSE:FCClose();return 0;}return DefWindowProcW(h,m,w,l);}
static void FCDrainInput(){MSG m;while(PeekMessageW(&m,Game(),WM_KEYFIRST,WM_KEYLAST,PM_REMOVE)){}while(PeekMessageW(&m,Game(),WM_MOUSEFIRST,WM_MOUSELAST,PM_REMOVE)){}memset((void*)0x4e9afc,0,256);}
static void OpenFlowChart(){Init();LONGLONG topen=Now();FCLog("open_request");if(fcOpen||fcLoading)return;if(!FCLoad()){MessageBoxW(Game(),L"이야기 지도 자료를 읽을 수 없습니다.",L"이야기 지도",MB_OK|MB_ICONERROR);return;}game=Game();
 // The original engine disables IME on its main window. Save and restore that state
 // around the Unicode map, before creating/associating the native EDIT context.
 using EnableImeFn=BOOL(WINAPI*)(HWND,BOOL);
 auto enableIme=(EnableImeFn)GetProcAddress(GetModuleHandleW(L"user32.dll"),"WINNLSEnableIME");
 BOOL oldIme=enableIme?enableIme(game,TRUE):TRUE;
 if(!fcWindow){WNDCLASSW wc{};wc.lpfnWndProc=FCProc;wc.hInstance=GetModuleHandleW(L"ReconquistaHD.dll");wc.hCursor=LoadCursorW(nullptr,MAKEINTRESOURCEW(32512));wc.lpszClassName=L"ReconquistaInGameFlow";wc.style=CS_DBLCLKS;RegisterClassW(&wc);fcWindow=CreateWindowExW(0,wc.lpszClassName,L"이야기 지도",WS_CHILD|WS_CLIPCHILDREN,0,0,1,1,game,nullptr,wc.hInstance,nullptr);
  fcSearch=CreateWindowExW(0,L"EDIT",L"",WS_CHILD|ES_AUTOHSCROLL,0,0,1,1,fcWindow,(HMENU)0x7e51,wc.hInstance,nullptr);if(fcSearch)fcOldEditProc=(WNDPROC)SetWindowLongPtrW(fcSearch,GWLP_WNDPROC,(LONG_PTR)FCEditProc);}
 if(!fcWindow){if(enableIme)enableIme(game,oldIme);return;}if(fcSearch)ImmAssociateContextEx(fcSearch,nullptr,IACE_DEFAULT);fcComposing=false;fcOpen=true;fcOpenedTick=GetTickCount();RECT r{};GetClientRect(game,&r);MoveWindow(fcWindow,0,0,r.right,r.bottom,TRUE);FCLayout();CaptureScene();
 fcHelp=false;fcStatus.clear();fcHover=-1;fcHotPlate=-1;ShowSearch(false);if(fcReopenChapter>=0){fcCursor=fcReopenChapter;fcReopenChapter=-1;}else if(fcHere>=0){fcCursor=fcNodes[fcHere].chapter;}else if(fcCursor<0)fcCursor=0;fcPage=fcChapters[fcCursor].page;   // back from a replay: on its chapter
 ShowWindow(fcWindow,SW_SHOW);SetWindowPos(fcWindow,HWND_TOP,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE);SetFocus(fcWindow);FCSound("on2");char b[120];sprintf_s(b,"opened here=%d cursor=%d page=%d ms=%.1f",fcHere>=0?fcNodes[fcHere].order:-1,fcCursor,fcPage,Ms(topen));FCLog(b);FCSnapshot();
 MSG msg{};bool quit=false;while(fcOpen){BOOL got=GetMessageW(&msg,nullptr,0,0);if(got<=0){quit=got==0;break;}
  if(msg.hwnd!=fcSearch&&msg.message==WM_KEYDOWN&&(msg.wParam==VK_ESCAPE||msg.wParam==VK_F11||msg.wParam==VK_RETURN||msg.wParam==VK_F1)){if(msg.wParam!=VK_F11||!(msg.lParam&(1L<<30)))FCProc(fcWindow,msg.message,msg.wParam,msg.lParam);continue;}
  if(msg.hwnd==game&&FCInputMessage(msg.message))continue;if(msg.hwnd==game&&msg.message==WM_CLOSE){fcOpen=false;PostMessageW(game,WM_CLOSE,0,0);break;}if(msg.message==WM_TIMER)continue;TranslateMessage(&msg);DispatchMessageW(&msg);}
 fcOpen=false;ShowSearch(false);fcComposing=false;if(enableIme)enableIme(game,oldIme);if(fcReturnWait){fcReturnWait=false;FCReplayReturn("map",FC_IN_WAIT);}if(!fcCover)ShowWindow(fcWindow,SW_HIDE);ReleaseCapture();FCDrainInput();SetFocus(game);InvalidateRect(game,nullptr,FALSE);FCFree(fcSceneShot);FCReadSave();if(fcLoading)*(int*)0x49467c=1;FCLog(fcLoading?"closed_jump":fcCover?"closed_cover":"closed_resume");if(quit)PostQuitMessage((int)msg.wParam);}

static WNDPROC fcPreviousProc=nullptr;
static LRESULT CALLBACK FCGameProc(HWND h,UINT m,WPARAM w,LPARAM l){
 if(m==WM_FCREOPEN){if(!fcOpen){fcCover=false;KillTimer(fcWindow,FC_COVER_TIMER);fcCoverText.clear();fcReplay=false;fcReplayStage=0;FCLog("replay_reopen");OpenFlowChart();}return 0;}   // back from a replay
 if(fcCover&&!fcOpen&&((m>=WM_KEYFIRST&&m<=WM_KEYLAST)||(m>=WM_MOUSEFIRST&&m<=WM_MOUSELAST)))return 0;   // under the cover nothing reaches the game
 if(fcReplay&&fcReplayStage==2&&!fcOpen&&(m==WM_KEYDOWN||m==WM_KEYUP)&&w==VK_ESCAPE){if(m==WM_KEYDOWN&&!(l&(1L<<30)))FCReplayReturn("esc",FC_IN_WAIT);return 0;}   // Esc ends a replay
 if((m==WM_COMMAND&&LOWORD(w)==0x7e43)||((m==WM_KEYDOWN||m==WM_SYSKEYDOWN)&&w==VK_F11)){
  if(m==WM_COMMAND||!(l&(1L<<30))){if(fcOpen)fcOpen=false;else OpenFlowChart();}return 0;
 }
 if(m==WM_CLOSE||m==WM_QUERYENDSESSION)FCReadSave();
 if(fcOpen&&FCInputMessage(m))return 0;
 return CallWindowProcA(fcPreviousProc,h,m,w,l);
}
static void FCSubclass(HWND h){if(!fcPreviousProc){auto old=(WNDPROC)SetWindowLongPtrA(h,GWLP_WNDPROC,(LONG_PTR)FCGameProc);if(old){fcPreviousProc=old;FCLog("window_connected");}}FCLoad();}
