// 기록에서 대사로 (11-25, the user: 「백로그 점프가 가능해?」, 「기능 추가좀 해줘」): in the game's 기록 (history.mjo), Enter or
// a double click goes back to the line shown, through the story map's own way to a line (flow.inc FCPrepare), the saves
// staying the player's own (no review folder): it is play, not review.
// The history: the console's buffer (0x41d570) holds its records backwards from 0x9c40, each ending in its 2-byte length; a
// record starting with \p begins a page. history.mjo moves with $console_hist_pos(n) (0x415b70, called at 0x412015): the
// n-th page back, its result the offset of that page's record. That call is wrapped (HistPos) so the shown page is known.
static int histArg=-1,histAt=-1,histLogged=-1;
struct HistRecord{int start,end;};
static std::vector<HistRecord> HistRecords(){std::vector<HistRecord> out;auto obj=((const unsigned char*(__cdecl*)())0x41d570)();if(!Readable(obj,0x9c40))return out;
 int p=0x9c40;for(int guard=0;guard<20000;guard++){int len=*(const uint16_t*)(obj+p-2);if(len<=0||p-len<0)break;int s=p-len;out.push_back({s,p-2});p=s;if(p<2)break;}return out;}   // newest first
// the page whose record starts at `at`: its records from there up to the next page's, as text without the engine's codes
static std::wstring HistPage(int at){cproto::ReadHangul();auto obj=((const unsigned char*(__cdecl*)())0x41d570)();auto recs=HistRecords();std::string raw;
 int i=-1;for(int k=0;k<int(recs.size());k++)if(recs[k].start==at){i=k;break;}if(i<0)return L"";
 for(int k=i;k>=0;k--){auto r=recs[k];const char*t=(const char*)obj+r.start;int n=r.end-r.start;if(k!=i&&n>=2&&t[0]=='\\'&&t[1]=='p')break;if(n>=1&&t[0]=='\\')continue;raw.append(t,size_t(n));}   // the codes' own records (\n \w \p \f with its font) carry no text
 std::string clean;for(size_t k=0;k<raw.size();k++){unsigned char c=(unsigned char)raw[k];if(c=='\\'&&k+1<raw.size()){k++;continue;}if(c<0x20)continue;clean+=char(c);if(((c>=0x81&&c<=0x9f)||(c>=0xe0&&c<=0xfc))&&k+1<raw.size())clean+=raw[++k];}
 return cproto::Decode(clean.data(),int(clean.size()));}
// 0x41c740 is the VM stack's top (the argument before, the result after); the stack is left as the engine leaves it
static void __cdecl HistPos(){auto top=(Variable*(__cdecl*)())0x41c740;
 Variable*a=top();int n=a?a->value:0;((void(__cdecl*)())0x415b70)();Variable*r=top();int at=r?r->value:-1;histArg=n;histAt=at;
 if(logFile&&histLogged!=at){histLogged=at;auto t=HistPage(at);char u[512]{};WideCharToMultiByte(CP_UTF8,0,t.c_str(),int(std::min<size_t>(t.size(),120)),u,511,nullptr,nullptr);fprintf(logFile,"hist_pos n=%d at=%d text=%s%c",n,at,u,10);fflush(logFile);}}
// the 기록 is up from its first page (HistPos) until the text box's pause loop waits again (ChoiceAtWait: it reads @is_select 0)
static bool HistOpen(){return histAt>=0;}
static void BacklogLeft(){histAt=-1;}
// The shown page's line: a line of the story whose text the page starts with (letters and digits only; its speaker's name
// before it too, in case the page carries it), the read one nearest before where the player is, else any read, else any.
static std::wstring Letters(const std::wstring&s){std::wstring o;for(wchar_t c:s)if(iswalnum(c)||(c>=0xAC00&&c<=0xD7A3))o+=c;return o;}
static int BacklogNode(){if(!FCLoad())return -1;auto page=Letters(HistPage(histAt));if(page.size()<2)return -1;int here=fcHere>=0?fcNodes[fcHere].order:INT_MAX;int best=-1;long long bestScore=LLONG_MAX;
 for(int i=0;i<int(fcNodes.size());i++){auto&n=fcNodes[i];if(n.kind!=0)continue;bool hit=false;for(auto t:{Letters(n.text),Letters(n.speaker+n.text)}){if(t.size()<2)continue;
   if(page.compare(0,t.size(),t)==0||(t.size()>page.size()&&t.compare(0,page.size(),page)==0)){hit=true;break;}}if(!hit)continue;
  long long d=(long long)here-n.order,score=(FCIsRead(i)?0:4000000000LL)+(d>=0?d:2000000000LL-d);if(score<bestScore){bestScore=score;best=i;}}
 return best;}
static bool backlogNoAsk=false,backlogAskRead=false;
static std::wstring BacklogIni(){wchar_t p[MAX_PATH];swprintf_s(p,L"%s\\backlog.ini",root);return p;}
// asked or not: 「두 번 다시 묻지 않기」 turns it off, the config screen's 「기록 점프」 button either way (config_buttons.inc)
static bool BacklogAsks(){if(!backlogAskRead){backlogAskRead=true;backlogNoAsk=GetPrivateProfileIntW(L"backlog",L"ask",1,BacklogIni().c_str())==0;}return !backlogNoAsk;}
static void BacklogSetAsks(bool ask){backlogAskRead=true;backlogNoAsk=!ask;WritePrivateProfileStringW(L"backlog",L"ask",ask?L"1":L"0",BacklogIni().c_str());if(logFile){fprintf(logFile,"backlog ask=%d%c",int(ask),10);fflush(logFile);}}
// 「이 대사로 돌아갈까요?」 over the game's picture, with 「두 번 다시 묻지 않기」 (backlog.ini) — the user's standard
static bool BacklogAsk(){if(!BacklogAsks())return true;
 fcAsk=L"이 대사로 돌아갈까요?";fcAskNever=false;fcAskHot=-1;ShowWindow(fcWindow,SW_SHOW);SetWindowPos(fcWindow,HWND_TOP,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE);SetFocus(fcWindow);InvalidateRect(fcWindow,nullptr,FALSE);UpdateWindow(fcWindow);
 auto hit=[&](LPARAM l){float x=LX((short)LOWORD(l)),y=LY((short)HIWORD(l));const RECT*r[3]={&fcAskYes,&fcAskNo,&fcAskBox};for(int k=0;k<3;k++)if(x>=r[k]->left&&x<r[k]->right&&y>=r[k]->top&&y<r[k]->bottom)return k;return -1;};
 int answer=-1;MSG msg{};while(answer<0){BOOL got=GetMessageW(&msg,nullptr,0,0);if(got<=0){if(got==0)PostQuitMessage((int)msg.wParam);answer=0;break;}
  bool ours=msg.hwnd==fcWindow||msg.hwnd==game;
  if(ours&&msg.message==WM_KEYDOWN){if(msg.wParam==VK_RETURN||msg.wParam=='Y')answer=1;else if(msg.wParam==VK_ESCAPE||msg.wParam=='N')answer=0;else if(msg.wParam==VK_SPACE){fcAskNever=!fcAskNever;InvalidateRect(fcWindow,nullptr,FALSE);}continue;}
  if(msg.hwnd==fcWindow&&msg.message==WM_MOUSEMOVE){int k=hit(msg.lParam);if(k!=fcAskHot){fcAskHot=k;InvalidateRect(fcWindow,nullptr,FALSE);}continue;}
  if(msg.hwnd==fcWindow&&msg.message==WM_LBUTTONUP){int k=hit(msg.lParam);if(k==0)answer=1;else if(k==1)answer=0;else if(k==2){fcAskNever=!fcAskNever;InvalidateRect(fcWindow,nullptr,FALSE);}continue;}
  if(ours&&msg.message==WM_RBUTTONUP){answer=0;continue;}
  if(ours&&(FCInputMessage(msg.message)||msg.message==WM_TIMER))continue;
  TranslateMessage(&msg);DispatchMessageW(&msg);}
 fcAsk=nullptr;if(answer==1&&fcAskNever)BacklogSetAsks(false);FCDrainInput();return answer==1;}
// Enter or a double click in the 기록: the page's line, asked, then the way there (as the map's 「여기서부터 본편으로」, the
// saves the player's own), the window over the game's picture until the line is reached (FCCover).
static void BacklogJump(){game=Game();int node=BacklogNode();char b[96];sprintf_s(b,"backlog node=%d at=%d",node>=0?fcNodes[node].order:-1,histAt);FCLog(b);
 if(node<0||fcLoading||fcOpen){if(node<0)FCSound("cancel");return;}
 FCEnsureWindow();if(!fcWindow)return;RECT r{};GetClientRect(game,&r);MoveWindow(fcWindow,0,0,r.right,r.bottom,TRUE);FCLayout();CaptureScene();fcOverScene=true;
 if(!BacklogAsk()||!FCPrepare(node,false,false)){fcOverScene=false;ShowWindow(fcWindow,SW_HIDE);SetFocus(game);FCFree(fcSceneShot);FCLog("backlog no");return;}
 if(fcReplay){fcReplay=false;fcReplayStage=0;fcTitleBefore[0]=0;}FCSound("push");FCCover(true,L"그 대사로 가는 중…");*(int*)0x49467c=1;FCLog("backlog go");}
// the game window's input (Input): in the 기록, Enter and the second click of a double click are the jump's
static bool BacklogKey(UINT msg,WPARAM wp,LPARAM lp){if(!HistOpen())return false;static ULONGLONG lastDown=0;static LPARAM lastAt=0;
 if(msg==WM_KEYDOWN&&wp==VK_RETURN&&!(lp&(1L<<30))){PostMessageW(Game(),WM_APP+82,0,0);return true;}
 if(msg==WM_LBUTTONDOWN){ULONGLONG now=GetTickCount64();bool twice=now-lastDown<=GetDoubleClickTime()&&abs(short(LOWORD(lp))-short(LOWORD(lastAt)))<6&&abs(short(HIWORD(lp))-short(HIWORD(lastAt)))<6;
  lastDown=twice?0:now;lastAt=lp;if(twice){PostMessageW(Game(),WM_APP+82,0,0);return true;}}
 if(msg==WM_LBUTTONUP&&lastDown==0){lastDown=1;return true;}   // the double click's release
 return false;}
