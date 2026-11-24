# 2026-10-28 final localization fixes on Claude 2026-10-27 runtime-proto.
# 현재 최신 수정판(runtime-final-20261028). 검증한 대본·UI·4K 그림으로 실행한다.
# 메뉴·대사 창의 「연표」로 열면 새 연표가 뜬다. 모양은 연표 창 왼쪽 위 [새|원래], 설정 화면 맨 아래 단추, F8로 바꾼다.
# 열어 둔 동안 화면을 제때 그렸는지는 runtime-final-20261028\hires-runtime.log 의 "chron_proto session" 줄에 남는다(닫을 때마다 한 줄).
param([switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$runtimeDir = Join-Path $root 'runtime-final-20261028'
$exe = Join-Path $runtimeDir 'レコンキスタ.exe'
$iso = 'P:\GAME\Reqonquist Novel H\Reconquista.iso'
$identity = Get-Content -LiteralPath (Join-Path $runtimeDir 'BUILD-IDENTITY.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($entry in @(@('ReconquistaHD.dll',$identity.dll_sha256),@('scenario.arc',$identity.scenario_sha256),@('storymap.bin',$identity.storymap_sha256),@('data.arc',$identity.data_sha256),@('fastdata.arc',$identity.fastdata_sha256))) { if ((Get-FileHash -LiteralPath (Join-Path $runtimeDir $entry[0]) -Algorithm SHA256).Hash -ne $entry[1]) { throw ('검수본 파일 해시 불일치: '+$entry[0]) } }

if (-not (Test-Path -LiteralPath $exe)) { throw ('최신 실행본이 없습니다: ' + $exe) }
if (-not (Test-Path -LiteralPath (Join-Path $runtimeDir 'chronicle-new\frame_off.png'))) { throw '새 연표 그림 폴더(chronicle-new)가 없습니다.' }
$env:TEMP = Join-Path $root 'build\temp'
$env:TMP = $env:TEMP
if (-not (Test-Path -LiteralPath $env:TEMP)) { New-Item -ItemType Directory -Path $env:TEMP | Out-Null }
foreach ($name in 'RECON_PERF','RECON_FLOW_PROBE','RECON_HD_PROBE','RECON_REVIEW_PROBE','RECON_INPUT_PROBE','RECON_CONFIG_PROBE') { Remove-Item ('Env:' + $name) -ErrorAction SilentlyContinue }
$env:RECON_HD_START_FULLSCREEN = '1'
$env:RECON_CHRON_PROTO = '1'
$acp = (Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Nls\CodePage' -Name ACP).ACP
if ($acp -ne '949') { throw '이 실행본은 Windows 비유니코드 프로그램 언어가 한국어(ACP 949)여야 합니다. 현재 ACP: ' + $acp }
$disk = Get-DiskImage -ImagePath $iso
if (-not $disk.Attached) { $disk = Mount-DiskImage -ImagePath $iso -StorageType ISO -Access ReadOnly -PassThru }
if ($PrepareOnly) { Write-Output '검수본 준비 확인 완료: 파일 해시·한국어 ACP·디스크'; return }
$running = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('レコンキスタ.exe','Reconquista.exe') }
if ($running) { throw '다른 레콘키스타 실행 창을 저장하고 종료한 뒤 다시 실행해 주세요.' }
Start-Process -FilePath $exe -WorkingDirectory $runtimeDir -WindowStyle Normal

