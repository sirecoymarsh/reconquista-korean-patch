from pathlib import Path
import json,hashlib,datetime
U=Path.cwd(); source=U.parent/'research/disc/readme.txt'; raw=source.read_bytes(); text=raw.decode('cp932'); out=U/'candidates/installer-readme-v1'; assert not out.exists()
records=[
 ('readme::thanks','この度は『レコンキスタ』をご購入いただき、誠にありがとうございます。','『레콘퀴스타』를 구입해 주셔서 진심으로 감사합니다.'),
 ('readme::before-play','プレイされる前に、こちらのテキストをよくご覧頂きますよう、\r\n何卒、宜しくお願いいたします。','게임을 시작하기 전에 이 안내문을 꼭 읽어 주시기 바랍니다.'),
 ('readme::install-title','・インストール方法','· 설치 방법'),
 ('readme::install-step','　起動画面より、「インストール」を選択してくださいませ。','　실행 화면에서 「설치」를 선택해 주세요.'),
 ('readme::supported-os','・対応：Win98/Me/2000/XP/Vista','· 지원 운영체제: Win98/Me/2000/XP/Vista'),
 ('readme::site-info','コットンソフトでは、随時ホームページにて\r\n最新情報をお届けしております。','코튼소프트는 홈페이지에서 최신 소식을 전하고 있습니다.'),
 ('readme::site-invitation','ゲーム情報から開発室のアホな日記まで、\r\n色々なネタを盛りだくさんでお待ちしておりますので、\r\nぜひぜひ、お越しくださいませ。','게임 정보부터 개발진의 엉뚱한 일기까지 다양한 이야기를\r\n가득 준비해 두었으니 꼭 한번 들러 주세요.'),
 ('readme::brand','コットンソフト','코튼소프트'),
 ('readme::copyright','このゲームはコットンソフトの著作物であり、\r\n無断複製・掲載等は固くお断りいたします。','이 게임은 코튼소프트의 저작물이며,\r\n무단 복제 및 게재 등을 엄격히 금지합니다.'),
 ('readme::component-intro','このタイトルには以下のコンポーネントを使用しております。\r\nどうもありがとうございます。','이 게임에는 아래 구성 요소를 사용했습니다.\r\n제작자 여러분께 감사드립니다.')
]
# Replace longer phrases before the standalone brand, retaining every unmodified byte-equivalent line.
for stable,src,dst in sorted(records,key=lambda r:len(r[1]),reverse=True):
 assert text.count(src)==1,(stable,text.count(src));text=text.replace(src,dst,1)
protected=['http://www.cotton-soft.com/','cotton@cotton-soft.com','(C)2007 COTTON-SOFTWARE','Ogg Vorbis','Copyright (c) 2002, Xiph.org Foundation','libpng','Copyright (c) 1998-2001 Glenn Randers-Pehrson.','zlib','Copyright (C) 1995-1998 Jean-loup Gailly and Mark Adler.','Win98/Me/2000/XP/Vista']
for token in protected: assert text.count(token)==raw.decode('cp932').count(token)==1
assert not any((0x3041<=ord(c)<=0x3096 or 0x30a1<=ord(c)<=0x30fa) for c in text)
encoded=text.encode('cp949');assert encoded.decode('cp949')==text
(out/'payloads').mkdir(parents=True);(out/'payloads/readme.txt').write_bytes(encoded);(out/'readme-ko.utf8.txt').write_text(text,encoding='utf-8-sig',newline='')
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','source_path':str(source),'source_sha256':sha(raw),'output_hashes':{'readme.txt':sha(encoded)},'source_encoding':'cp932','target_encoding':'cp949','review_encoding':'UTF-8 BOM','semantic_fields':len(records),'records':[{'id':i,'source':s,'target':t} for i,s,t in records],'protected_tokens':protected,'structural_pass':True,'context_review_pass':True,'source_file_unchanged':source.read_bytes()==raw,'runtime_review':'pending; installer open action and target text viewer have not been executed','candidate_integration':'standalone payload; installer executables and UI archives unchanged','release_pass':False}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(U/'translation/installer-readme-ko.json').write_text(json.dumps({'translator_model':'Codex internal','task_id':manifest['task_id'],'records':manifest['records']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=U/'progress.json';s=json.loads(p.read_text(encoding='utf-8'));s['updated_local']=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat();s['completed'].append('installer-readme-v1:10 semantic fields authored; all source content covered, URL/email/OS list/component attributions preserved, CP949 roundtrip passes. Standalone payload only; installer-open runtime pending.');s['current_counts']['installer_readme_fields']=10;s['artifacts']+=['candidates/installer-readme-v1/manifest.json','translation/installer-readme-ko.json'];s['usage_checkpoint']={'remaining_percent':89,'used_percent':11,'limit_id':'codex','stop_marker_present':False,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'candidate':str(out),'fields':len(records),'sha256':sha(encoded),'protected_tokens':len(protected)},ensure_ascii=False))
