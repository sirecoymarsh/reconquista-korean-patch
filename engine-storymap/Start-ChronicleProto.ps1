# 새 연표를 직접 써 보는 사본(runtime-proto). 소리는 플레이판과 같고, 설정·저장은 플레이판과 따로(레지스트리 키도 따로).
# 메뉴·대사 창의 「연표」로 열면 새 연표가 뜬다. 모양은 연표 창 왼쪽 위 [새|원래], 설정 화면 맨 아래 단추, F8로 바꾼다.
# 열어 둔 동안 화면을 제때 그렸는지는 runtime-proto\hires-runtime.log 의 "chron_proto session" 줄에 남는다(닫을 때마다 한 줄).
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$runtimeDir = Join-Path $root 'runtime-proto'
$exe = Join-Path $runtimeDir 'レコンキスタ.exe'
$iso = 'P:\GAME\Reqonquist Novel H\Reconquista.iso'
if (-not (Test-Path -LiteralPath $exe)) { throw ('시제품 사본이 없습니다: ' + $exe) }
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
$running = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('レコンキスタ.exe','Reconquista.exe') }
if ($running) { throw '다른 레콘키스타 실행 창을 저장하고 종료한 뒤 다시 실행해 주세요.' }
Start-Process -FilePath $exe -WorkingDirectory $runtimeDir -WindowStyle Normal
