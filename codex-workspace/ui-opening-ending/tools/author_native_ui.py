from pathlib import Path
import json,hashlib,re
u=Path('P:/AI/Codex/projects/reconquista-ko/ui-opening-ending').resolve();d=json.loads((u/'source/pe-visible-catalog.json').read_text(encoding='utf-8'))
lines='''ファイル/設定(&F)|파일/설정(&F)
ファイル(&F)|파일(&F)
セーブ(&S)\tF2|저장(&S)\tF2
名前を付けてセーブ(&A)\tAlt+F2|다른 이름으로 저장(&A)\tAlt+F2
ロード(&O)\tF3|불러오기(&O)\tF3
名前で指定してロード(&L)\tAlt+F3|이름을 지정해 불러오기(&L)\tAlt+F3
画面の保存(&T)...\tF5|화면 저장(&T)...\tF5
ジョイスティック使用(&J)|조이스틱 사용(&J)
ムービーを禁止(&M)|동영상 재생 안 함(&M)
スピード設定(&P)...|속도 설정(&P)...
サウンド設定(&V)...|소리 설정(&V)...
音声個別設定(&C)...|인물별 음성 설정(&C)...
フォント設定(&F)...|글꼴 설정(&F)...
タイトルへ戻る(&B)|타이틀로 돌아가기(&B)
終了(&X)\tAlt+F4|종료(&X)\tAlt+F4
スクリーン(&S)|화면(&S)
フルスクリーン(&F)\tF4|전체 화면(&F)\tF4
ウインドウ(&W)\tAlt+Enter|창 모드(&W)\tAlt+Enter
スクリーン詳細設定(&O)...|화면 세부 설정(&O)...
オートプレイ(F6)|자동 진행(F6)
既読スキップ(F7)|읽은 부분 넘기기(F7)
強制スキップ(F8)|모두 넘기기(F8)
ヘルプ(&H)|도움말(&H)
バージョン情報(&A)...|버전 정보(&A)...
エラーログを開く(&E)|오류 기록 열기(&E)
コンフィグ(F9)|설정(F9)
自動進行(&P)\tF6|자동 진행(&P)\tF6
読んだ所はスキップ(&R)\tF7|읽은 부분 넘기기(&R)\tF7
強制スキップ(&N)\tF8|모두 넘기기(&N)\tF8
常に手前に表示(&T)|항상 위에 표시(&T)
バージョン情報|버전 정보
OK|확인
音声抜けをDialogBoxにて表示|누락된 음성을 대화상자로 알림
画像抜けをDialogBoxにて表示|누락된 이미지를 대화상자로 알림
音声再生の倍速化(16bit/Monoのみ)|음성 배속 재생(16bit/Mono 전용)
エラー行を自動で開く|오류가 난 줄을 자동으로 열기
エディタ設定|편집기 설정
ソースフォルダ|소스 폴더
BOOTING MAJIRO...|MAJIRO 시작 중...
フォルダ情報の読み込み中…|폴더 정보를 읽는 중…
スクリーン詳細設定|화면 세부 설정
ｷｬﾝｾﾙ|취소
全画面モード|전체 화면 모드
常に手前に表示|항상 위에 표시
DirectDrawを使用|DirectDraw 사용
フォント選択|글꼴 선택
フォント名|글꼴 이름
スピード設定|속도 설정
初期化|기본값
画面効果|화면 효과
文字表示|글자 표시
高速|빠름
低速|느림
オートモード|자동 진행
CTRLキーのスキップ動作は既読のみ|Ctrl 키로 읽은 부분만 넘기기
音声個別設定|인물별 음성 설정
音声は全てOFF|모든 음성 끄기
ＯＦＦにする音声をチェックしてください|끄려는 음성을 선택해 주세요
サウンド設定|소리 설정
音楽|음악
音声|음성
最小|최소
最大|최대
効果音|효과음
男性の音声をＯＦＦ|남성 음성 끄기
女性の音声をＯＦＦ|여성 음성 끄기
音楽をＯＦＦ|음악 끄기
効果音をOFF|효과음 끄기'''
mp=dict(l.split('|',1) for l in lines.splitlines())
mp['\r\nＭＡＪＩＲＯ　スクリプトエンジン\r\nInternalVersion1.00\r\n\r\nCopyright (C) 越畑 声太']='\r\nMAJIRO 스크립트 엔진\r\nInternalVersion1.00\r\n\r\nCopyright (C) 越畑 声太'
mp[' スクリプトエンジン MAJIRO (C) 2004-2005 越畑声太']=' 스크립트 엔진 MAJIRO (C) 2004-2005 越畑声太'
mp['ソースフォルダ、エディタの設定をすると、[F11]にて\r\n実行中のソース位置をエディタで開くことが出来ます。\r\nエディタ設定の%fn%はファイル名に%line%はライン数に\r\n変換されます。']='소스 폴더와 편집기를 설정하면 [F11] 키로\r\n실행 중인 소스 위치를 편집기에서 열 수 있습니다.\r\n편집기 설정의 %fn%은 파일 이름, %line%은 줄 번호로\r\n바뀝니다.'
mp['変数ウオッチ : ステータスバーに変数を表示できます(@と#のみ)\r\nスペースで区切って入れて下さい 例)@flag_a #flag_a @page_back@PIC']='변수 보기: 상태 표시줄에 변수를 표시합니다(@와 #만 지원).\r\n공백으로 구분해 입력하세요. 예)@flag_a #flag_a @page_back@PIC'
mp={k.replace('\r\n','\n'):v.replace('\r\n','\n') for k,v in mp.items()}
records=[];excluded=[]
for r in d['records']:
 s=r['source']
 if 'MAJIRO_MAIN_NEKO' in r['id']:excluded.append({**r,'reason':'Unselected alternate mahjong engine menu; NEKOMENU=0. NOCONFIG menu observed at runtime.'});continue
 if s=='SYSTEM_ICON' or s.startswith('http') or re.fullmatch(r'(Check|Slider)\d+',s):excluded.append({**r,'reason':'icon resource key, preserved URL, or dynamic control placeholder'});continue
 assert s in mp,(r['id'],repr(s))
 t=mp[s];assert re.findall(r'\(&[A-Za-z0-9]\)|%fn%|%line%|Alt\+F\d|F\d+',s)==re.findall(r'\(&[A-Za-z0-9]\)|%fn%|%line%|Alt\+F\d|F\d+',t)
 records.append({**r,'target':t,'translator_model':'Codex internal','status':'authored_native_resource','provenance':'Codex task 01a162df-720c-77d2-96ed-6429e90b3333'})
out={'translator_model':'Codex internal','source_exe_sha256':d['source_exe_sha256'],'records':records,'excluded':excluded,'notes':['UTF-16 resource strings; never encoded with CP932 glyph mapping.','Keep command/control IDs and menu flags.','Use Malgun Gothic for native dialog display.','Copyright contributor names and URLs preserved.']}
(u/'translation/native-ui-ko.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('native semantic authored',len(records),'excluded',len(excluded))
