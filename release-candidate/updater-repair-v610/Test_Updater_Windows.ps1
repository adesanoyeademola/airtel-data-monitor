$ErrorActionPreference='Stop'
$base=Join-Path $env:RUNNER_TEMP ('tnet-update-test-'+[guid]::NewGuid().ToString('N'))
$install=Join-Path $base 'install'
$other=Join-Path $base 'other'
New-Item -ItemType Directory -Force $install,$other | Out-Null
$updater=(Resolve-Path 'release-candidate/updater-repair-v610/Apply_Update.ps1').Path
$package=(Resolve-Path 'releases/AirtelMonitor-6.11.0.zip').Path
$stub=Join-Path $base 'dummy.exe'
$exe=Join-Path $install 'AirtelDataMonitor.exe'
$engine=Join-Path $install 'monitor.ps1'
Add-Type -TypeDefinition 'using System; using System.Threading; public class Dummy { [STAThread] public static void Main(){ Thread.Sleep(120000); }}' -OutputAssembly $stub -OutputType WindowsApplication -ReferencedAssemblies @('System.dll') -ErrorAction Stop
Copy-Item $stub $exe
Copy-Item $stub (Join-Path $other 'AirtelDataMonitor.exe')
[IO.File]::WriteAllText($engine,'ORIGINAL ENGINE')
New-Item -ItemType Directory (Join-Path $install 'data') -Force | Out-Null
$usage=Join-Path $install 'data/usage.json'
$timeline=Join-Path $install 'data/usage-timeline.csv'
[IO.File]::WriteAllText($usage,'{"test":"keep"}')
[IO.File]::WriteAllText($timeline,'2026-11-08,12345')
function Check([bool]$ok,[string]$note){if(!$ok){throw "FAIL: $note"};Write-Host "PASS: $note"}
function RunUpdater([string]$pkg,[int]$parent=0){
  $out=Join-Path $base ([guid]::NewGuid().ToString('N')+'.out')
  $err=Join-Path $base ([guid]::NewGuid().ToString('N')+'.err')
  $cmd='-NoProfile -ExecutionPolicy Bypass -File "'+$updater+'" -Package "'+$pkg+'" -InstallDir "'+$install+'" -ParentPid '+$parent+' -NoRestart -NonInteractive'
  $p=Start-Process 'powershell.exe' -ArgumentList $cmd -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
  return @{ Code=$p.ExitCode; Output=((Get-Content $out -Raw -ErrorAction SilentlyContinue)+' '+(Get-Content $err -Raw -ErrorAction SilentlyContinue)) }
}
$rogue=$null
$running=$null
$locked=$null
try {
  $bad=RunUpdater (Join-Path $base 'missing.zip')
  Check ($bad.Code -ne 0 -and $bad.Output -match 'Downloaded update ZIP missing') 'Actual missing-package error displayed'
  Check (Test-Path (Join-Path $install 'update-last-error.log')) 'Error log written'
  Check ([IO.File]::ReadAllText($engine) -eq 'ORIGINAL ENGINE') 'No modifications on preflight failure'
  $rogue=Start-Process (Join-Path $other 'AirtelDataMonitor.exe') -PassThru
  Start-Sleep -Milliseconds 1000
  Check (!$rogue.HasExited) 'Same-named unrelated app is running'
  $firstHash=(Get-FileHash $exe -Algorithm SHA256).Hash
  $good=RunUpdater $package $rogue.Id
  Write-Host $good.Output
  Check ($good.Code -eq 0 -and $good.Output -match 'UPDATE COMPLETE') 'Closed-app update succeeds despite unrelated name'
  Check ((Get-FileHash $exe -Algorithm SHA256).Hash -ne $firstHash) 'Compiled EXE installed'
  Check ([IO.File]::ReadAllText($engine) -ne 'ORIGINAL ENGINE') 'Monitoring source updated'
  Check (@(Get-ChildItem (Join-Path $install 'update-backups') -Directory).Count -gt 0) 'Rollback backups created'
  Check ([IO.File]::ReadAllText($usage) -eq '{"test":"keep"}') 'Usage data unchanged'
  Check ([IO.File]::ReadAllText($timeline) -eq '2026-11-08,12345') 'Usage timeline unchanged'
  Copy-Item $stub $exe -Force
  $running=Start-Process $exe -PassThru
  Start-Sleep -Milliseconds 1000
  Check (!$running.HasExited) 'Installed app is running'
  $blocked=RunUpdater $package
  Check ($blocked.Code -ne 0 -and $blocked.Output -match 'running|locked') 'Actual installed app correctly blocks update'
  Check ((Get-FileHash $exe -Algorithm SHA256).Hash -eq $firstHash) 'Running executable preserved'
  Stop-Process -Id $running.Id -Force
  $running.WaitForExit(); $running.Dispose(); $running=$null
  $locked=[IO.File]::Open($engine,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
  $blocked2=RunUpdater $package
  Check ($blocked2.Code -ne 0 -and $blocked2.Output -match 'locked|cannot be replaced') 'Locked monitoring engine correctly blocks update'
  $locked.Dispose(); $locked=$null
  $retry=RunUpdater $package $PID
  Write-Host $retry.Output
  Check ($retry.Code -eq 0) 'Retry succeeds when locks released; own updater not mistaken for app'
  Check ([IO.File]::ReadAllText($usage) -eq '{"test":"keep"}') 'Usage retained after retries'
  Check ([IO.File]::ReadAllText($timeline) -eq '2026-11-08,12345') 'Timeline retained after retries'
  Write-Host 'ALL UPDATER INTEGRATION TESTS PASSED'
}finally {
 if($locked){$locked.Dispose()}
 foreach($p in @($running,$rogue)) {
   if($p){try{if(!$p.HasExited){Stop-Process -Id $p.Id -Force}}catch{};try{$p.Dispose()}catch{}}
 }
}
