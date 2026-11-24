# 아르곤 재번역 반입 시험 사본 실행 (2026-11-21 Claude). runtime-final-20261028 위에 새 번역·지도·글꼴을 얹은 사본.
# 저장은 사본 안 savedata(플레이판 저장을 새 오프셋으로 옮겨 적은 사본)라 원래 플레이판 저장과 섞이지 않는다.
param([switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$runtimeDir = Join-Path $root 'runtime-argon-test-20261121'
$exe = Join-Path $runtimeDir 'レコンキスタ.exe'
$iso = 'P:\GAME\Reqonquist Novel H\Reconquista.iso'
$identity = Get-Content -LiteralPath (Join-Path $runtimeDir 'ARGON-TEST-IDENTITY.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $identity.from_build.PSObject.Properties) {
  if ((Get-FileHash -LiteralPath (Join-Path $runtimeDir $p.Name) -Algorithm SHA256).Hash -ne $p.Value) { throw ('시험 사본 파일 해시 불일치: ' + $p.Name) }
}
$env:TEMP = Join-Path $root 'work\temp'
$env:TMP = $env:TEMP
if (-not (Test-Path -LiteralPath $env:TEMP)) { New-Item -ItemType Directory -Path $env:TEMP | Out-Null }
foreach ($name in 'RECON_PERF','RECON_FLOW_PROBE','RECON_HD_PROBE','RECON_REVIEW_PROBE','RECON_INPUT_PROBE','RECON_CONFIG_PROBE') { Remove-Item ('Env:' + $name) -ErrorAction SilentlyContinue }
$env:RECON_HD_START_FULLSCREEN = '1'
$env:RECON_CHRON_PROTO = '1'
$acp = (Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Nls\CodePage' -Name ACP).ACP
if ($acp -ne '949') { throw '이 실행본은 Windows 비유니코드 프로그램 언어가 한국어(ACP 949)여야 합니다. 현재 ACP: ' + $acp }
$disk = Get-DiskImage -ImagePath $iso
if (-not $disk.Attached) { $disk = Mount-DiskImage -ImagePath $iso -StorageType ISO -Access ReadOnly -PassThru }
if ($PrepareOnly) { Write-Output '시험 사본 준비 확인 완료: 파일 해시·한국어 ACP·디스크'; return }
$running = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('レコンキスタ.exe','Reconquista.exe') }
if ($running) { throw '다른 레콘키스타 실행 창을 저장하고 종료한 뒤 다시 실행해 주세요.' }
Start-Process -FilePath $exe -WorkingDirectory $runtimeDir -WindowStyle Normal
