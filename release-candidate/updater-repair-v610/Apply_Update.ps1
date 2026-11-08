# T-Net: updater-only repair. No application UI, monitoring or data files are changed.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Package,
    [int]$ParentPid = 0,
    [string]$InstallDir = '',
    [switch]$NoRestart,
    [switch]$NonInteractive
)
$ErrorActionPreference='Stop'
$root=if($InstallDir){[IO.Path]::GetFullPath($InstallDir)}else{$PSScriptRoot}
$exe=Join-Path $root 'AirtelDataMonitor.exe'
$engine=Join-Path $root 'monitor.ps1'
$errorLog=Join-Path $root 'update-last-error.log'
$stage=$null

function Is-InstalledApp([System.Diagnostics.Process]$process,[string]$expected) {
    if($null -eq $process -or $process.Id -eq $PID){return $false}
    try{
        if($process.HasExited){return $false}
        $actual=$process.MainModule.FileName
        return $actual -and [string]::Equals([IO.Path]::GetFullPath($actual),
             [IO.Path]::GetFullPath($expected),[StringComparison]::OrdinalIgnoreCase)
    }catch{
        # Protected unrelated processes are not identified by name alone.
        # Windows file-lock checks will still prevent unsafe replacement.
        return $false
    }
}
function Running-App-Pids {
    $found=@()
    foreach($proc in [Diagnostics.Process]::GetProcesses()){
        try{
            if(Is-InstalledApp $proc $exe){$found+=@([int]$proc.Id)}
        }catch{}finally{$proc.Dispose()}
    }
    return @($found)
}
function Wait-ForParent {
    if($ParentPid -le 0 -or $ParentPid -eq $PID){return}
    $limit=[DateTime]::UtcNow.AddSeconds(35)
    while([DateTime]::UtcNow -lt $limit){
        $parent=$null
        try{$parent=[Diagnostics.Process]::GetProcessById($ParentPid)}
        catch [ArgumentException]{return}
        try{
            if(-not (Is-InstalledApp $parent $exe)){return}
        }finally{if($null -ne $parent){$parent.Dispose()}}
        Start-Sleep -Milliseconds 250
    }
    throw "T-Net at $exe (PID $ParentPid) did not exit within 35 seconds."
}
function Assert-FileAvailable([string]$path) {
    if(-not [IO.File]::Exists($path)){throw "Required installed file not found: $path"}
    $file=$null
    try{
        $file=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    }catch{
        throw "Installed file is locked or cannot be replaced: $path. Windows error: $($_.Exception.Message)"
    }finally{
        if($null -ne $file){$file.Dispose()}
    }
}
function Assert-UpdateSafe {
    $pids=@(Running-App-Pids)
    if($pids.Count -gt 0){
        throw "T-Net is running from $exe (PID: $($pids -join ', ')); close it before updating."
    }
    Assert-FileAvailable $exe
    Assert-FileAvailable $engine
}
function Explain-Error([System.Management.Automation.ErrorRecord]$err){
    $parts=@()
    $reason=$err.Exception
    while($null -ne $reason){
        $parts+=($reason.GetType().FullName+': '+$reason.Message)
        $reason=$reason.InnerException
    }
    if($null -ne $err.InvocationInfo -and $err.InvocationInfo.ScriptLineNumber -gt 0){
        $parts+=("Updater line "+$err.InvocationInfo.ScriptLineNumber+": "+$err.InvocationInfo.Line.Trim())
    }
    return ($parts -join [Environment]::NewLine)
}

try{
    if(-not [IO.Directory]::Exists($root)){throw "Installation folder not found: $root"}
    if(-not [IO.File]::Exists($exe)){throw "Installed T-Net EXE missing: $exe"}
    if(-not [IO.File]::Exists($engine)){throw "Monitoring engine missing: $engine"}
    if(-not [IO.File]::Exists($Package)){throw "Downloaded update ZIP missing: $Package"}
    Wait-ForParent
    Assert-UpdateSafe

    $stage=Join-Path ([IO.Path]::GetTempPath()) ('TNet-update-'+[guid]::NewGuid().ToString('N'))
    $unpacked=Join-Path $stage 'unpacked'
    New-Item -ItemType Directory -Path $unpacked -Force | Out-Null
    Expand-Archive -LiteralPath $Package -DestinationPath $unpacked -Force -ErrorAction Stop
    foreach($name in @('AirtelMonitorNative.cs','monitor.ps1')){
        if(-not [IO.File]::Exists((Join-Path $unpacked $name))){throw "Update package missing $name"}
    }
    $compiled=Join-Path $stage 'AirtelDataMonitor.exe'
    Add-Type -Path (Join-Path $unpacked 'AirtelMonitorNative.cs') -OutputAssembly $compiled -OutputType WindowsApplication -ReferencedAssemblies @('System.dll','System.Core.dll','System.Drawing.dll','System.Windows.Forms.dll','System.Web.Extensions.dll','System.Windows.Forms.DataVisualization.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll') -ErrorAction Stop
    if(-not [IO.File]::Exists($compiled)){throw 'Windows compilation did not produce an EXE.'}

    # Re-check after compilation in case T-Net was opened meanwhile.
    Assert-UpdateSafe
    $backupDir=Join-Path $root ('update-backups\'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8))
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    $backupExe=Join-Path $backupDir 'AirtelDataMonitor.exe'
    $backupEngine=Join-Path $backupDir 'monitor.ps1'
    Copy-Item -LiteralPath $exe -Destination $backupExe -ErrorAction Stop
    Copy-Item -LiteralPath $engine -Destination $backupEngine -ErrorAction Stop
    if(-not [IO.File]::Exists($backupExe) -or -not [IO.File]::Exists($backupEngine)){throw 'Backup could not be verified.'}
    try{
        Copy-Item -LiteralPath (Join-Path $unpacked 'monitor.ps1') -Destination $engine -Force -ErrorAction Stop
        Copy-Item -LiteralPath $compiled -Destination $exe -Force -ErrorAction Stop
    }catch{
        $original=Explain-Error $_
        $rollbacks=@()
        try{Copy-Item -LiteralPath $backupEngine -Destination $engine -Force -ErrorAction Stop}
        catch{$rollbacks+=("monitor.ps1: "+$_.Exception.Message)}
        try{Copy-Item -LiteralPath $backupExe -Destination $exe -Force -ErrorAction Stop}
        catch{$rollbacks+=("AirtelDataMonitor.exe: "+$_.Exception.Message)}
        if($rollbacks.Count){
            throw "Update failed: $original; rollback incomplete: $($rollbacks -join '; '); original backups: $backupDir"
        }
        throw "Update failed and original files were restored: $original"
    }
    Write-Host "UPDATE COMPLETE: T-Net installed successfully; data and settings untouched." -ForegroundColor Green
    Write-Host "Original executable and monitoring engine backup: $backupDir"
    if(-not $NoRestart){
        try{Start-Process -FilePath $exe -ErrorAction Stop}
        catch{Write-Warning ("T-Net updated but automatic restart failed: "+(Explain-Error $_))}
    }
    exit 0
}catch{
    $message="UPDATE FAILED: "+(Explain-Error $_)
    Write-Host $message -ForegroundColor Red
    try{[IO.File]::WriteAllText($errorLog,([DateTime]::Now.ToString('o')+[Environment]::NewLine+$message),[Text.Encoding]::UTF8)}
    catch{Write-Warning ("Could not save update error log: "+$_.Exception.Message)}
    if(-not $NonInteractive){[void](Read-Host 'Press Enter to close')}
    exit 1
}finally{
    if($stage -and [IO.Directory]::Exists($stage)){
        Remove-Item -LiteralPath $stage -Force -Recurse -ErrorAction SilentlyContinue
    }
}
