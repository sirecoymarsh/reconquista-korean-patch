# 별도 UI 및 OP/ED 채팅 인계

사용자 요청(2026-10-22): 별도 프로젝트 채팅에서 UI 한국어화를 max 추론 강도로 진행하고, UI 완료 후 같은 채팅에서 오프닝·엔딩 한국어화를 진행한다. 추가 지시: 번역에 착수하기 전에 지침을 먼저 수립한다.

공통 지침: ../translation/LOCALIZATION_GUIDELINES.md. 첫 작업은 이를 읽고 UI/OP/ED의 소스·상태·완료 조건을 작업 계획으로 구체화하는 일이다. 이후 이 기준에 맞춰 번역한다. 기존 본문 초안이 완성본이라는 가정은 하지 않는다.

물리 작업 루트: P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타
P: ASCII 별칭: P:\AI\Codex\projects\reconquista-ko
이 채팅 전용 작업 폴더: P:\AI\Codex\projects\reconquista-ko\ui-opening-ending
앱 프로젝트 등록 경로는 아직 C:이나 실제 프로젝트 파일은 P:로 이전·검증 완료. C:에 작업 파일을 쓰지 말고 cwd/TEMP/TMP/cache/output을 P:로 명시한다.

원본: P:\GAME\Reqonquist Novel H\Reconquista.iso
추출 원본: ../research/disc
아카이브 목록: ../reports/archive_inventory
추출 scenario/fastdata: ../research/extracted
도구: ../tools/inspect_majiro.py의 Arc 클래스. 원본 scenario 및 181 MJO 바이트 동일 복원은 검증 완료되어 재사용한다.
엔진: Majiro, MajiroArcV2.000, CP932; Malie 아님.
주요 아카이브: fastdata.arc(UI/설정), scenario.arc(스크립트), data/data1/data2/slowdata(이미지 등), stream/voice(음성). 각 엔트리 종류는 목록 확인. OP 원본 movie/Recon_OP800_H.mpg. ED 자산 경로는 아직 미확정.

현재 본문 진행: 00_レコンキスタ_start.mjo 619개 단위, 일반 표시 889필드와 강조/루비 7필드 초안. 이름 내부 토큰 351개는 원문 유지. ../builds/trial-opening-0001-0619와 ../runtime-ko는 본문 채팅 소유. 새 채팅에서 직접 수정·종료·입력하지 않는다.
첫 대사 「드디어 만났네」의 실제 한글 출력은 2026-10-22 본문 채팅에서 관찰했다. 첫 스크립트 후반의 직접 MS 명조 호출 8곳은 아직 처리 전이다. 저장/불러오기, 지난 대사 및 전체 도입부 플레이는 미검증이다.

서로 겹치는 전체 아카이브를 덮어쓰지 않도록 자체 후보와 runtime-ui를 전용 폴더에 만든다. 의미 문자열 변경표(원문/번역/안정 ID/소비자)와 아카이브별 엔트리 페이로드를 함께 남긴다. 중앙 translation/hangul-cp932-map.json과 tools/build_trial.py, 본문 번역 TSV, progress.json은 읽기 전용으로 다룬다. 독립 글꼴 매핑을 확장한다면 별도 파일에 기록하고 통합 시 재인코딩할 수 있게 원래 한국어 문장을 반드시 보존한다.

원본 EXE SHA256: cd1c38ac20d9e502fbc58b7392ca77ec32e3d56f90d988580a3cf58cb6f95146
원본 scenario.arc SHA256: 95b6592ce3d9f4f94a4051bbbc217e26fbb9c63586a4e0b5bcd9932f961aeb99
원본 실행 파일명을 영어로 바꾸면 DVD의 bin 폴더에서 같은 이름을 못 찾아 제품 디스크 오류가 발생한다. 반드시 レコンキスタ.exe 유지. 현재 ISO는 G: COTTON_02로 읽기 전용 연결되어 있으나 문자는 동적으로 확인한다. 사용자가 원본 실행 오류 해결을 확인했다. crk/reconquista_nodvd.exe는 실행하지 않았고 작업에 필요하지 않다.

읽을 지침: P:\AI\Codex\AGENTS.md, contextual-game-localization/SKILL.md, shared translation-quality.md. 래스터에는 raster-asset-geometry-contract, Windows 결과물에는 windows-release-integrity 적용. 가사 원문이 음성뿐이면 audio-lyrics-transcription 스킬 검토. 번역은 해당 채팅의 Codex 내부 모델이 직접 수행하며 외부 MT/LLM은 금지. 서브에이전트는 독립 읽기 전용 리뷰만 허용.

포함 사용량 중지 정책과 C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json 신호를 준수한다. 최신 사용량은 새 채팅에서 직접 확인한다. 구매 크레딧으로 계속하지 않는다.

## 2026-10-23 엔딩 크레딧 신규 고정 후보

- `candidates/ending-credits-raster-v1/manifest.json`: fastdata.arc의 staffrolla.rct + staffrolla_.rc8 + staffrollb_001..011.rct, 총13페이로드. 개별 원본/출력 SHA-256과 의미 변경78항목 포함. 정적·저장본 육안 검토 PASS, 사용자 실제 재생 검토 대기.
- `candidates/ui-trial-v23/manifest.json`: v22를 읽기 전용 기반으로 위13개만 추가한 UI 단독 재현본. 중앙 본문·통합 맵을 대신하지 않으므로 중앙에서는 엔트리 페이로드를 병합할 것. 시나리오와 글꼴은 v22 그대로.
- 세로 이미지800×4664, 교체 이미지11장800×600, 원본 스크립트·시간·분기 그대로. 교체 화면 배경은 각 원본의 확인된 빈 행에서 같은 좌표 픽셀을 복사했고 모든 빈 기여본이 동일함을 확인. 생성/보간/블러 없음.
- 제작자·회사 이름은 기존 음악 크레딧 정책대로 원래 표기/독립 이름행 픽셀 보존. 등장인물은 본문 확정 표기 적용. `朋子`의 독음만 미확정으로 두 크레딧 행에 한자 유지. `矢嶋`은 명시적 ヤシマ 근거에 따라 야시마.
- OP·ED 음성 원문은 원본/반주차감과 small/large-v3 STT를 비교한 상태. STT는 일본어 복원에만 사용했으며 한국어 의미 번역은 Codex internal이 작성한다. OP 영상·ED 가사 자막은 아직 이 후보에 포함하지 않음.


## 2026-10-23 사용자 글꼴·로고 수정 반영

- 자막 선택: `research/typography/selected-font.json` — 을유1945 SemiBold, 원본 파일/해시 포함. 파일은 빌드용이며 최종 패치에는 래스터 결과만 포함.
- 신규 고정 로고: `candidates/brand-logo-ko-v1/manifest.json` — title1/2/3 × off/on/push 9 payloads, 원본 스타일 한글 `레콘키스타`와 성경 인용문4줄. 기존 한글 메뉴 보존, 원본 달 배경 donor 검증, 보호 영역0차이, 저장 재디코드·상태 종결·시각 검토 PASS. 실제 게임 확인은 사용자 유보.
- OP 영상 로고 및 새 자막은 아직 작업 중. 현재 OP v1 미리보기는 최종 후보가 아님.
- ED 게임 hook 및 console8버튼은 중앙 담당; 이 세션은 중복 수정하지 않음.


## 2026-10-23 레 윗획 국소 수정 v2

- `candidates/brand-logo-ko-v2/manifest.json` frozen, ready_for_integration:true. 9타이틀 페이로드의 base_candidate_sha256은 모두 v1 output_sha256에 결속. 의미 라벨 추가0, 기존5필드의 디자인 교체.
- 첫 레의 긴 윗획만 축소. master 국소 영역 이외 RGBA 동일, 실제 타이틀 차이 영역 title1/2 [54,100,106,220], title3 [386,18,439,138] 이내. 나머지 글자·인용문·메뉴는 픽셀 동일.
- 원본 donor 및 TC01 종결 증거는 v1 재사용, 변경 영역과 9저장본 재디코드만 검증. 정적·시각 PASS, 사용자 실제 재생 확인 대기.
- OP는 별도 `opening-video-ko-v2` 작업 중이며 아직 최종 MPG 없음. 복합 전환 구간 배경/로고 움직임 복원 품질이 미통과 상태이므로 통합 금지.


- OP 자막 ID 수정 완료: 제거 집합은 정확히 title-1/title-2 두 개, 인용문4개 원래 승인 번역 복구. ASS 실제37개/메타데이터37개 일치, 복구4cue 새 렌더·검은 여백 경계 검증 PASS. 나머지 기존 글꼴 검증 재사용.

- OP 91초 잔상 수정: 90.75–92.6초 원문 확장 윤곽 포함, 8새 표본은 `opening-video-ko-v2/preview/closing-halo-repair.png`. 기존 다른 구간 검토 재사용. 의미 입력 해시는 슬래시 경로 하나로 정규화. 최종 MPEG 재생성 중.


## 2026-10-23 OP 최종 고정 후보

- `candidates/opening-video-ko-v2/manifest.json`: frozen/ready_for_integration=true. 실제 페이로드는 `payloads/movie/Recon_OP800_H.mpg` 하나이며 내부 fonts와 build-source는 배포 제외.
- 출력 SHA256 `46f4c0f9bcccd5294fb01ac2040824cfe577634b6ac70091da9d30c3bfaf4dda`, 74,338,304바이트. 원본 SHA256 `6da04d09fd954c67b004b6cecfe22fd89da473cbf60fd74856d2170a1972995a`.
- 원본과 출력 모두 MPEG1 800×600 yuv420p, r60/avg30, 실제3037프레임. 전체 상대 videoPTS 최대차이0.000001초, video duration101.216667초 동일. 컨테이너/audio duration101.250611초 동일, 상대A/V시작차0.
- 원본 MP2 3876패킷 그대로복사. elementary SHA256 `8e0702cb615b9322e54e2636590afc1db1186fc24860bac3ad209cfbc0e0f4ad` 동일, audioPTS 반올림오차는 최대1/90000초.
- 을유1945 SemiBold, 자막37(크레딧21+가사16), 정확한2title ID만본문자막생략·로고로대체. 인용문4cue 보존. 실제저장영상63표본에37cue전체포함, 여백/잘림검증 PASS, 전체디코드오류0.
- 91초 원문암적색윤곽 수정후8표본 확인. 중앙의 기존17표본 검토 재사용. 최종저장본 contact2장과 native032/036/042 글꼴·fallback 확인.
- 영상배경은 원본프레임/도시자산을 사용한 연속복원이며, 불투명원문밑원래RGB와 완전동일하다는 주장은 하지 않음. 효과/기하와 색은 원본 관측값으로 복원. 상세manifest참고.
- 실제게임·청취검증은 사용자담당. 원문가사불확실2ID(OP007/ED014) 기존고지 유지. ED후크는중앙완료본사용.
- 중앙v7 다음본에 위MPG만추가하고 기존본문/ED/맵/폰트보존. 나머지UI정확한미완료파일/관찰상태/라벨수와근거는 `../reports/remaining-ui-handoff.json`, `../reports/남은-UI-인계.md` 참조. 이전실패donor탐색반복없음.

최종 검토용 이미지는 `opening-video-ko-v2/preview/encoded-font-and-logo.png`, `encoded-closing.png`, `encoded/`입니다. `logo-review-contact.png`는 91초 잔상 수정 전의 중간 검토표이므로 최종 증거로 사용하지 않습니다. 고정 후보의 manifest가 가리키는 encoded 검토 보고서를 기준으로 통합합니다.


## OP 최종 두 프레임 불일치 보고 확인

`reports/op-caption-discrepancy-20261023/report.json`: 최종 MPEG 해시가 frozen manifest와 동일하며, n300(10.0초)·n1695(56.5초)를 독립 추출한 PNG는 기존 encoded/004.png·036.png와 RGB 픽셀 차이0입니다. 두 시점 모두 상단/하단 자막이 있습니다. 흰 글자 픽셀은 10초 상단2813/하단1403, 56.5초 상단4514/하단1637입니다. 후보 파일은 수정하지 않았습니다. 새 이름의 full frame 및 caption-bands.png로 다시 확인할 수 있습니다. 검토 측에서 다르게 보인 원인은 아직 단정하지 않습니다.


## 2026-10-23 중앙 v8 통합 완료

`../reports/final-integration-20261023.json`을 읽어 완료 상태를 확인했습니다. `body-ui-20261023-v8` 및 `runtime-body-ui-20261023-v8`에 최종 OP가 반영됐고 `Start-Korean.cmd`의 기본 대상도 v8입니다. OP SHA256은 `46f4c0f9bcccd5294fb01ac2040824cfe577634b6ac70091da9d30c3bfaf4dda` 그대로입니다. 기존 본문·타이틀 v2·ED·폰트는 중앙의 검증된 결과를 보존했습니다. 새 통합 대기 후보는 없습니다.

두 프레임의 자막 누락 보고는 개별 재검토 후 철회됐습니다. 후보 변경이나 재인코딩은 하지 않았습니다. 추가 확인 기록은 `reports/op-caption-discrepancy-20261023/report.json`에 있습니다.

이번 글꼴·로고·오프닝 수정 요청은 통합까지 완료했습니다. 전체 UI에는 원본 유지 범위가 남아 있으며, 정확한 미완료 목록은 중앙 `remaining-ui-handoff.json`을 기준으로 합니다. 실제 게임 실행·청취·동기 확인은 사용자 담당으로 남깁니다.


## 2026-10-23 사용자 추가 요청 — OP v3

오프닝에 남은 일본어 전체 교체 작업을 새 v3에서 시작했습니다. v2 고정본은 유지합니다. 인물 소개, 성우, 주제가, 영상·디렉터 표기 및 상단 자막의 일본어 이름을 대상으로 하며, 새 후보는 아직 통합 불가입니다. 게임·GUI 실행 없이 파일로 검증합니다.


## 2026-10-23 OP v3 및 4K 감상용 최종 고정본

- `candidates/opening-video-ko-v3/manifest.json`: frozen/ready_for_integration=true. OP 제작·정적 검증 완료. 중앙 패키지에는 아직 이 v3를 설치하지 않았으며, 기존 v2 파일은 유지했습니다.
- 게임 페이로드 하나: `payloads/movie/Recon_OP800_H.mpg`, SHA256 `3bec1af99ce27ed85d006d0a2daff7dbe667e229d0e1089eba999cb589c1df6d`, 76,622,848바이트. MPEG1 800×600, 실제3037프레임/평균30fps. MP2 3876패킷 및 압축 음원 SHA256 원본과 동일, 상대A/V시작차0. 마지막 검은 프레임까지 PTS존재. PS duration추정치는101.224489초이나 실제 마지막 음원패킷끝101.250611초이며 음원누락없음.
- 별도 4K 감상용: `viewing/Reconquista_OP_KO_4K.mp4`, SHA256 `536d5b1335370881585e102717304ab7c0e137fc0aa27eacef78b05e1cea1555`, 1,017,556,605바이트. 사용자 선택대로16:9화면을 채운3840×2160/30fps. 원본SD를 복원·업스케일하고 한글·공유v3로고를4K에서 합성. AAC44.1kHz stereo, 영상·음원시작0, 모든3037프레임의 시각검증PASS. 원본대조5개PCM창 상관계수0.99884이상; 최종수정후 동일AAC압축해시로 기존음질검증재사용.
- 한글24의미항목, 영상 안12표기면, 자막26cue(상단10/가사16), 인명16개 대응. 그림속일본어와 겹치던 중복상단cue11개를 제거하고 실제한국어교체. `朋子`는 공식TOMOKO근거로도모코. 가사OP007의 기존원문청취유보는유지하며 ED범위는변경하지않음.
- 공통로고: `brand-logo-ko-v3/master/reconquista-ko.png`, SHA256 `81e8e88a31f70f84ab6bafbe33cfad19787b7e5079206c05f094d82eaa2f51ef`. 원본디자인의한글레콘키스타. 을유1945SemiBold를영상에래스터화했으며 fonts/build-source는배포대상이아님.
- 독립검토에서발견한도시세로띠·머리카락가로띠수정후재검토PASS. 붉은수평광선복원및n2161원화범위수정까지실제저장본으로확인. 원본/생성clean plate혼합복원975프레임, 숨겨진원본RGB와동일하다는주장은하지않음. 상세입력해시·영역·방법은manifest/evidence참고.
- 최종시각표본:게임93프레임,4K69프레임. 기존검증을재사용하고변경구간·연결점만추가확인. `preview/review.html`은휠포인터중심확대/축소·동기화·핏리셋·바깥스크롤을헤드리스Chrome에서실제검증했습니다.
- 게임·오디오재생·Explorer·전면창을실행하지않았습니다. 중앙통합은게임용MPG하나만대상이고4K는감상용입니다. 실제게임재생·청취확인은사용자담당입니다.


## 2026-10-23 OP v4 최종본

- 후보: candidates/opening-video-ko-v4/manifest.json. 기존 v3는 보존.
- 게임 MPEG: 8ad40abd04837b5b5e14c8911ecefcacb08a98ce6cf44955123eb8ef4ab763ef, 76,011,648bytes. 3037프레임/30fps, 원본 MP2 3876패킷 동일.
- 4K MP4: 89850e2555a1dd0c7d07892639f544b1b2a2ee46ba8aaa6c473de9cd38aed4c5, 1,012,242,883bytes. 3840×2160/30fps, 기존 검증 AAC 압축 해시 동일.
- 카스가이·타무라 방식 인명 표기, 영문 6면 제자리 한글 식자, STARRING=등장인물, 스태프·팀명 한글화. 두 줄 가사16쌍+기존 인용문4개=36cue.
- 영문 제거745프레임, 기존 v3 복원수정88프레임 재사용. 새 생성형 이미지 사용 없음. 모든 숨겨진 원본 RGB의 완벽한 복원은 주장하지 않음.
- 변경 저장본 표본 게임63장/4K51장 검토. 원본 음원/변경 없는 v3 검증은 재사용. 일반 휠 포인터 중심 확대·동기화·핏·바깥 스크롤을 헤드리스에서 확인.
- 가사 op-lyrics::007 기존 일본어 청취 추정은 미확정 유지. 실제 게임·청취·설치는 하지 않았음. 다음 중앙 통합에는 게임 MPEG만 사용하고 4K는 별도 감상용.


## 2026-10-23 음소거·백그라운드 검수 제약

- 이 세션 작업 경로/검수 프로필에 연결된 실행 중 소유 검수 프로세스: 0개. 종료·음소거할 대상 없음.
- v4 제작·검수에서 게임/오디오 재생 또는 수동 Defender 검사를 시작하지 않았음.
- 사용자가 다시 허용하기 전 유음 재생·전경 검수 금지. 런타임 검수는 프로세스 음소거가 실제 확인되고 포커스·입력 제어를 가져오지 않는 백그라운드 방식만 허용. 비공개 데스크톱만으로는 음소거를 보장하지 못함. 보장할 수 없으면 파일 작업만 진행.
- 원본 음원 트랙·시스템 전체 음량·Defender 실시간 보호 및 보안 설정은 변경하지 않음. 최종 v4 영상·명세는 그대로 보존.


## 2026-10-23 OP v5 게임용 별도 완료본

- `candidates/opening-video-ko-v5/game-manifest.json`: frozen / ready_for_integration. 4K 완료 여부와 별개로 게임용 MPEG 통합 가능.
- 파일: `candidates/opening-video-ko-v5/payloads/movie/Recon_OP800_H.mpg`, c8a8fa38cb35517285fc1fad7d1c09990f57199dae7b1f7915bcfd3e576cc719, 75,319,680바이트.
- 게임용 실제 저장본 변경/연결부 44장 검토 PASS. 3037프레임 및 원본 MP2 3876패킷 보존, 마지막 PTS와 상대 동기 검증 PASS. `technical-validation.json`, `native-visual-review.json`, `semantic-gate.json` 참조.
- 상단 인용 자막 4개 제거, 하단 작은 영어 문단을 선명한 한국어 4줄로 제자리 교체, 가사의 `in darkness` 원문 유지.
- 이 MPEG는 이후 4K 작업에서 수정하지 않음. 4K는 배열 메모리 부족을 해결하는 중이며 아직 미완료. 전체 `manifest.json`은 아직 생성하지 않음.
- 실제 게임 실행·오디오 재생·전경 조작·설치 없음. OP007 원문 청취 추정은 기존 유보 유지.


## 2026-10-23 OP v5 최종본

- candidates/opening-video-ko-v5/manifest.json — frozen, ready_for_integration.
- 게임 MPEG: c8a8fa38cb35517285fc1fad7d1c09990f57199dae7b1f7915bcfd3e576cc719
- 4K MP4: 9f5d21f41c6f028503136269eea6051fa19def4b9dcea63ad278c44f3b260dd4
- 앞뒤 로고 위 인용 자막4개 제거, 로고 아래 작은 원문 영어문단을 한국어4줄로 교체. 일본어/한국어 가사16쌍과 in darkness 원문보존.
- 변경 구간 실제저장본 게임44장·4K44장 검토. 원본MP2·기존AAC 보존과3037프레임 시각검증PASS. 변경없는v4 검증재사용.
- 원본·v4 보존. 게임·오디오재생·Explorer·전경조작·설치없음. OP007의원문청취추정유지.
