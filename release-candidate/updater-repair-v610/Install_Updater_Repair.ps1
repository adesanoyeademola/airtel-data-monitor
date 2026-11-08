# One-time repair of Apply_Update.ps1 only. Does not touch T-Net EXE, monitor.ps1, or data.
[CmdletBinding()]
param([string]$InstallDir=(Join-Path $env:LOCALAPPDATA 'AirtelDataMonitor'),
      [switch]$NonInteractive)
$ErrorActionPreference='Stop'
try {
  $root=[IO.Path]::GetFullPath($InstallDir)
  $exe=Join-Path $root 'AirtelDataMonitor.exe'
  $target=Join-Path $root 'Apply_Update.ps1'
  $replacement=Join-Path $PSScriptRoot 'Apply_Update.ps1'
  if(-not [IO.File]::Exists($exe)){throw "T-Net not found at: $exe. No files changed."}
  if(-not [IO.File]::Exists($replacement)){throw "Repair script missing: $replacement"}
  $backup=$null
  if([IO.File]::Exists($target)){
    $backup=Join-Path $root ('Apply_Update.backup.'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'.ps1')
    Copy-Item -LiteralPath $target -Destination $backup -ErrorAction Stop
  }
  try{Copy-Item -LiteralPath $replacement -Destination $target -Force -ErrorAction Stop}
  catch{
    if($backup){try{Copy-Item -LiteralPath $backup -Destination $target -Force}catch{}}
    throw
  }
  Write-Host 'UPDATER REPAIR INSTALLED.' -ForegroundColor Green
  Write-Host "Installed at: $target"
  if($backup){Write-Host "Original updater backup: $backup"}
  Write-Host 'No application executable, monitor.ps1, usage.json or usage-timeline.csv changed.'
  exit 0
} catch {
  Write-Host ('UPDATER REPAIR FAILED: '+$_.Exception.GetType().FullName+': '+$_.Exception.Message) -ForegroundColor Red
  if(-not $NonInteractive){[void](Read-Host 'Press Enter to close')}
  exit 1
}
