param([switch]$PrepareOnly)
# 레콘키스타 v19 + 이야기 지도 (F11). Game data are Codex v19's (menus-4k); this folder adds the map DLL, data and art.
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$runtimeDir = Join-Path $root 'runtime-play'
$exe = Join-Path $runtimeDir 'レコンキスタ.exe'
$iso = 'P:\GAME\Reqonquist Novel H\Reconquista.iso'
if (-not (Test-Path -LiteralPath $exe)) { throw ('게임 실행 파일이 없습니다: ' + $exe) }
$identity = Get-Content -LiteralPath (Join-Path $runtimeDir 'BUILD-IDENTITY.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($pair in @(@('ReconquistaHD.dll', $identity.dll_sha256), @('storymap.bin', $identity.storymap_sha256), @('scenario.arc', $identity.scenario_sha256))) {
    if ((Get-FileHash -LiteralPath (Join-Path $runtimeDir $pair[0]) -Algorithm SHA256).Hash -ne $pair[1].ToUpper()) { throw ('이야기 지도 파일이 만든 것과 다릅니다: ' + $pair[0]) }
}
if (-not (Test-Path -LiteralPath (Join-Path $runtimeDir 'storymap\frame.png'))) { throw '이야기 지도 그림 폴더(storymap)가 없습니다.' }
$env:TEMP = Join-Path $root 'build\temp'
$env:TMP = $env:TEMP
if (-not (Test-Path -LiteralPath $env:TEMP)) { New-Item -ItemType Directory -Path $env:TEMP | Out-Null }
foreach ($name in 'RECON_PERF','RECON_FLOW_PROBE','RECON_HD_PROBE','RECON_REVIEW_PROBE','RECON_INPUT_PROBE','RECON_CONFIG_PROBE') { Remove-Item ('Env:' + $name) -ErrorAction SilentlyContinue }
$env:RECON_HD_START_FULLSCREEN = '1'
$acp = (Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Nls\CodePage' -Name ACP).ACP
if ($acp -ne '949') { throw '이 실행본은 Windows 비유니코드 프로그램 언어가 한국어(ACP 949)여야 합니다. 현재 ACP: ' + $acp }
$disk = Get-DiskImage -ImagePath $iso
if (-not $disk.Attached) { $disk = Mount-DiskImage -ImagePath $iso -StorageType ISO -Access ReadOnly -PassThru }
$volume = $disk | Get-Volume
Write-Output ('이야기 지도 실행본 준비 완료: ' + $runtimeDir + ' / 디스크 ' + $volume.DriveLetter + ':\')
if ($PrepareOnly) { return }
$running = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('レコンキスタ.exe','Reconquista.exe') }
if ($running) { throw '다른 레콘키스타 실행 창을 저장하고 종료한 뒤 다시 실행해 주세요.' }
Start-Process -FilePath $exe -WorkingDirectory $runtimeDir -WindowStyle Normal
