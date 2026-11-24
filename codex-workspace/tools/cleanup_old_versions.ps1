param([switch]$Execute)
$ErrorActionPreference = 'Stop'
$expectedRoot = 'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타'
$rootItem = Get-Item -LiteralPath $expectedRoot -Force
if ($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Physical project root must not be a reparse point' }
$root = $rootItem.FullName.TrimEnd('\')
$reportDir = Join-Path $root 'reports\version-cleanup-20261023'
$plan = Get-Content -LiteralPath (Join-Path $reportDir 'plan.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($plan.workspace -ne $root) { throw 'Workspace mismatch' }
$allowedRoots = @($plan.candidate_runtime_directories + $plan.candidate_prototype_directories | ForEach-Object { [IO.Path]::GetFullPath((Join-Path $root $_)) })
function Assert-Boundary([string]$Path) {
 $full = [IO.Path]::GetFullPath($Path)
 if (-not $full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) { throw ('Outside project: '+$full) }
 if (-not ($allowedRoots | Where-Object { $full -eq $_ -or $full.StartsWith($_+'\',[StringComparison]::OrdinalIgnoreCase) })) { throw ('Outside retired runtime allowlist: '+$full) }
 return $full
}
function Assert-NoReparseAncestor([string]$Path) {
 $parent = [IO.Path]::GetDirectoryName($Path)
 while ($parent -and $parent -ne $root) {
  $item=Get-Item -LiteralPath $parent -Force
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw ('Reparse ancestor: '+$parent) }
  $parent=[IO.Path]::GetDirectoryName($parent)
 }
 if ($parent -ne $root) { throw 'Ancestor boundary failure' }
}
if (Test-Path -LiteralPath 'C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json') { throw 'Included usage stop signal' }
$running=Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('レコンキスタ.exe','Reconquista.exe') }
if ($running) { throw 'A game process is running; leave all runtime files untouched' }
$env:PYTHONDONTWRITEBYTECODE='1';$env:PYTHONIOENCODING='utf-8';$env:TEMP=Join-Path $root 'temp';$env:TMP=$env:TEMP
& 'C:\Users\CadriacLord\AppData\Local\Programs\Python\Python311\python.exe' (Join-Path $root 'tools\preflight_version_cleanup.py')
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed; nothing deleted' }
$execPlan=Get-Content -LiteralPath (Join-Path $reportDir 'execution-plan.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($row in $execPlan.delete_files) { $p=Assert-Boundary $row.path;Assert-NoReparseAncestor $p }
foreach ($row in $execPlan.remove_junction_nodes) { $p=Assert-Boundary $row.path;Assert-NoReparseAncestor $p }
if (-not $Execute) { Write-Output 'Prepared only; no files deleted'; return }
$journal=Join-Path $reportDir 'deletion-journal.jsonl'
if (Test-Path -LiteralPath $journal) { throw 'Existing journal: inspect partial execution before retrying' }
$plan.deletion_authorized=$true
$plan.status='executing_authorized_cleanup'
$plan | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath (Join-Path $reportDir 'plan.json') -Encoding UTF8
foreach ($row in $execPlan.remove_junction_nodes) {
 $p=Assert-Boundary $row.path;Assert-NoReparseAncestor $p;$item=Get-Item -LiteralPath $p -Force
 if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Expected junction changed' }
 # Delete the junction entry itself, without recursion. Its target is never enumerated or deleted.
 $item.Delete()
 @{kind='junction_node';path=$p;target_preserved=$row.target} | ConvertTo-Json -Compress | Add-Content -LiteralPath $journal -Encoding UTF8
}
foreach ($row in $execPlan.delete_files) {
 $p=Assert-Boundary $row.path;Assert-NoReparseAncestor $p;$item=Get-Item -LiteralPath $p -Force
 if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $item.Length -ne $row.bytes) { throw ('File changed after preflight: '+$p) }
 Remove-Item -LiteralPath $p -Force
 @{kind='file';path=$p} | ConvertTo-Json -Compress | Add-Content -LiteralPath $journal -Encoding UTF8
}
foreach ($p0 in $execPlan.remove_empty_directories) {
 $p=Assert-Boundary $p0
 if ($p -in $execPlan.keep_root_directories) { continue }
 Assert-NoReparseAncestor $p
 if (Test-Path -LiteralPath $p) {
  $item=Get-Item -LiteralPath $p -Force
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Unexpected reparse directory' }
  if (@(Get-ChildItem -LiteralPath $p -Force).Count -ne 0) { throw ('Unexpected remaining file: '+$p) }
  Remove-Item -LiteralPath $p -Force
 }
}
foreach ($p0 in $execPlan.old_launchers) {
 $p=[IO.Path]::GetFullPath($p0)
 if ([IO.Path]::GetDirectoryName($p) -ne $root -or [IO.Path]::GetFileName($p) -notin $plan.old_launchers) { throw 'Launcher allowlist mismatch' }
 Remove-Item -LiteralPath $p -Force
 @{kind='retired_launcher';path=$p} | ConvertTo-Json -Compress | Add-Content -LiteralPath $journal -Encoding UTF8
}
foreach ($row in $execPlan.keep_native) { if (-not (Test-Path -LiteralPath $row.path)) { throw 'Preserved native binary missing' } }
foreach ($row in $execPlan.remove_junction_nodes) { if (-not (Test-Path -LiteralPath $row.target)) { throw 'Junction target missing' } }
$freeAfter=(Get-PSDrive -Name P).Free
$result=@{status='complete';deleted_files=$execPlan.delete_files.Count;retired_runtime_directories=$plan.candidate_runtime_directories.Count;cleaned_prototypes=$plan.candidate_prototype_directories.Count;native_binaries_preserved=$execPlan.keep_native.Count;retired_launchers=$execPlan.old_launchers.Count;free_bytes_before=$execPlan.free_bytes_before;free_bytes_after=$freeAfter;estimated_freed_bytes=$execPlan.estimated_freed_bytes;backup='saves-and-evidence.zip';restore_map='restore-map.json';no_recursive_deletion=$true}
$result | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $reportDir 'result.json') -Encoding UTF8
$plan.status='completed';$plan | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath (Join-Path $reportDir 'plan.json') -Encoding UTF8
$result | ConvertTo-Json -Compress