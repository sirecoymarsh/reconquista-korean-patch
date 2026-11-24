from pathlib import Path
import json,datetime,re
U=Path.cwd().resolve();assert not Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists();src=json.loads((U/'source/installer-data-string-candidates.json').read_bytes())
mp={
'[%s]にインストールします':'[%s]에 설치합니다.',
'ルートにはインストールできません':'루트에는 설치할 수 없습니다.',
'ネットワークドライブには対応していません。\nローカルドライブを選択して下さい。':'네트워크 드라이브는 지원하지 않습니다.\n로컬 드라이브를 선택해 주세요.',
'フォルダを作成する場所を選択してください':'폴더를 만들 위치를 선택해 주세요.',
'起動に必要なファイルが不足しています。\nインストールの異常終了、起動するフォルダ異常、等を確認してください。':'실행에 필요한 파일이 누락됐습니다.\n설치가 중단됐거나 실행 폴더가 잘못됐는지 확인해 주세요.',
'インストール先ディレクトリが不明です。\n再インストールしてください。':'설치 폴더를 찾을 수 없습니다.\n다시 설치해 주세요.',
'プログラムの起動に失敗しました。\n再インストールしてください。':'프로그램을 실행하지 못했습니다.\n다시 설치해 주세요.',
'インストール先ディレクトリが不明です。':'설치 폴더를 찾을 수 없습니다.',
'アンインストーラの起動に失敗しました。':'삭제 프로그램을 실행할 수 없습니다.',
'[OK]を押した後、次のディスクを挿入して下さい\n\n(*)ディスクを挿入しても自動起動しない場合は、\nドライブのアイコンをダブルクリックして下さい':'[확인]을 누르고 다음 디스크를 넣어 주세요.\n\n(*) 디스크를 넣어도 자동 실행되지 않으면\n드라이브 아이콘을 두 번 클릭해 주세요.',
'- メディア交換 -':'- 디스크 교체 -',
'ファイルの検査中...':'파일 검사 중...',
'インストールを終了しました。':'설치가 완료됐습니다.',
'指定された場所には書き込み出来ません。':'지정한 위치에 쓸 수 없습니다.',
'インストールを中止しました':'설치를 취소했습니다.',
'インストールを継続します。宜しいですか？':'설치를 계속할까요?',
'ファイル[%s]のコピーに失敗しました。\nインストール先の容量を確認してください。':'파일[%s]을 복사하지 못했습니다.\n설치 위치의 여유 공간을 확인해 주세요.',
'ファイル[%s]のコピーを中止しました。':'파일[%s] 복사를 취소했습니다.',
'ドライブ容量が不足しています。\nドライブ容量を増やすか、他のドライブを選択してください。':'드라이브의 공간이 부족합니다.\n여유 공간을 확보하거나 다른 드라이브를 선택해 주세요.',
'ファイル[ %s ]が[ %s ]と[ %s ]に存在します':'파일[ %s ]이 [ %s ]과 [ %s ]에 있습니다',
'ファイル[%s]が破損しています。再インストールしてください':'파일[%s]이 손상됐습니다. 다시 설치해 주세요.',
'Ffopen : ファイル[%s]の読み込みで失敗しました':'Ffopen : 파일[%s]을 읽지 못했습니다',
'メモリ容量が不足しています。処理を中断します。':'메모리가 부족하여 작업을 중단합니다.',
'指定された場所には書き込み出来ません。\nインストールにはAdministrator権限が必要です。':'지정한 위치에 쓸 수 없습니다.\n설치하려면 관리자 권한이 필요합니다.',
'インストールにはAdministrator権限が必要です。':'설치하려면 관리자 권한이 필요합니다.',
}
records=[]
for r in src['records']:
 if r['source'] not in mp:continue
 target=mp[r['source']];assert r['source'].count('\n')==target.count('\n');assert re.findall(r'%[a-zA-Z]',r['source'])==re.findall(r'%[a-zA-Z]',target);n=len(target.encode('cp949'));records.append({**r,'target':target,'translator_model':'Codex internal','status':'authored_consumer_and_build_pending','target_byte_length':n,'fits_source_slot':n<=r['byte_length'],'source_display_context':'Installer path/status/copy/error/confirmation string inferred from literal; concrete references recorded but all consumers not yet audited.'})
assert set(mp)=={r['source'] for r in records}
out={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':src['sources'],'records':records,'unique_sources':len(mp),'field_count':len(records),'semantic_review':'Codex-authored Korean; source arguments and actual newline counts preserved. Error/status context only; no external translation engine used.','consumer_review_pending':True,'build_applied':False,'runtime_pass':False,'release_ready':False,'protected_exclusions':['Startup/uninstall title and mutex formats','Next-disc comparison token','Font-family identifiers','Default application name','Shortcut names until consumers audited','Non-string false positives']};(U/'translation/installer-messages-ko.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'fields':len(records),'unique_sources':len(mp),'overlong':[(r['id'],r['byte_length'],r['target_byte_length'],r['target']) for r in records if not r['fits_source_slot']],'build_applied':False},ensure_ascii=False))
