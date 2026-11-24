param([switch]$PrepareOnly,[switch]$VerifyAssets)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtimeDir = Join-Path $projectRoot 'runtime-body-ui-20261025-v20-nuance'
$exe = Join-Path $runtimeDir 'レコンキスタ.exe'
$iso = 'P:\GAME\Reqonquist Novel H\Reconquista.iso'
$manifestPath = Join-Path $projectRoot 'builds\body-ui-20261025-v20-nuance\manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$env:TEMP = Join-Path $projectRoot 'temp'
$env:TMP = $env:TEMP
if (-not (Test-Path -LiteralPath $env:TEMP)) { New-Item -ItemType Directory -Path $env:TEMP | Out-Null }
if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne $manifest.exe_sha256) { throw '실행 파일이 검증된 통합본과 다릅니다.' }
foreach ($entry in $manifest.outputs.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $runtimeDir $entry.Name) -Algorithm SHA256).Hash -ne $entry.Value) { throw ('통합 패치 파일 해시가 맞지 않습니다: ' + $entry.Name) }
}
foreach ($entry in @(@('ReconquistaKR.otf', $manifest.font.output_sha256), @('ReconquistaKRSerif.otf', $manifest.serif_font.output_sha256))) {
    if ((Get-FileHash -LiteralPath (Join-Path $runtimeDir ('font\' + $entry[0])) -Algorithm SHA256).Hash -ne $entry[1]) { throw ('글꼴 해시가 맞지 않습니다: ' + $entry[0]) }
}
$assetManifest = Get-Content -LiteralPath (Join-Path $runtimeDir 'hires-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($asset in $assetManifest.entries) {
    $assetPath = Join-Path $runtimeDir ('hires\' + $asset.file)
    if (-not (Test-Path -LiteralPath $assetPath) -or (Get-Item -LiteralPath $assetPath).Length -ne $asset.bytes) { throw ('고해상도 파일 누락 또는 크기 불일치: ' + $asset.name) }
    if ($VerifyAssets -and (Get-FileHash -LiteralPath $assetPath -Algorithm SHA256).Hash -ne $asset.sha256) { throw ('고해상도 파일 해시 불일치: ' + $asset.name) }
}
Remove-Item Env:RECON_PERF -ErrorAction SilentlyContinue
Remove-Item Env:RECON_FLOW_PROBE -ErrorAction SilentlyContinue
Remove-Item Env:RECON_HD_PROBE -ErrorAction SilentlyContinue
Remove-Item Env:RECON_REVIEW_PROBE -ErrorAction SilentlyContinue
Remove-Item Env:RECON_INPUT_PROBE -ErrorAction SilentlyContinue
Remove-Item Env:RECON_CONFIG_PROBE -ErrorAction SilentlyContinue
$env:RECON_HD_START_FULLSCREEN = '1'
$acp = (Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Nls\CodePage' -Name ACP).ACP
if ($acp -ne '949') { throw '이 통합본의 네이티브 한국어 창은 Windows 비유니코드 프로그램 언어가 한국어(ACP 949)인 환경을 사용합니다. 현재 ACP: ' + $acp }
$disk = Get-DiskImage -ImagePath $iso
if (-not $disk.Attached) { $disk = Mount-DiskImage -ImagePath $iso -StorageType ISO -Access ReadOnly -PassThru }
$volume = $disk | Get-Volume
$discExe = Join-Path ($volume.DriveLetter + ':\') 'bin\レコンキスタ.exe'
if ((Get-FileHash -LiteralPath $discExe -Algorithm SHA256).Hash -ne $manifest.original_exe_sha256) { throw '연결된 제품 디스크가 검증된 원본과 다릅니다.' }
Write-Output ('통합 파일 및 제품 디스크 준비 완료: ' + $runtimeDir + ' / ' + $volume.DriveLetter + ':\')
if ($PrepareOnly) { return }
$running = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('レコンキスタ.exe','Reconquista.exe') }
if ($running) { throw '다른 레콘키스타 실행 창을 저장하고 종료한 뒤 다시 실행해 주세요.' }
Start-Process -FilePath $exe -WorkingDirectory $runtimeDir -WindowStyle Normal
