# Non-destructive simulated adapter-switch tests for T-Net monitor.ps1
# Loads function declarations only, without starting its listener or touching user data.
$ErrorActionPreference='Stop'
$engine=Join-Path $PSScriptRoot 'monitor.ps1'
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($engine,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
$want=@('Get-ConnectedWifi','Resolve-ActiveWifi','Take-Sample','Make-Summary','Get-CachedAdapters','Get-Adapters')
$definitions=$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]},$true)
foreach($node in $definitions){
  if($want -contains $node.Name){. ([scriptblock]::Create($node.Extent.Text))}
}
$script:State=@{targetSsid='GLOBAL';adapterName='WiFi';daily=@{};lastUpdated=''}
$script:Sample=@{valid=$false;rx=[double]0;tx=[double]0;adapter='';ssid=''}
$script:SampleTime=[datetime]::MinValue
$script:Status='not-configured'
$script:Rate=@{rxBps=[double]0;txBps=[double]0;valid=$false;sampleTime='';sampleId=[long]0}
$script:CachedRateLimit=[double]1250000000
$script:RateLimitCheckedAt=[datetime]::MinValue
$script:AdapterChoicesCheckedAt=[datetime]::MinValue
$script:CachedAdapterChoices=@()
$script:ErrorText=''
$script:ActiveAdapter=''
$script:WifiSignal=$null
$script:Sharing=$false
$script:connected='WiFi'
$script:route='WiFi'
$script:stats=@{
  WiFi=@{rx=[double]1000;tx=[double]2000}
  'WiFi 2'=@{rx=[double]30000000;tx=[double]75000000}
}
function netsh {
  "There are 2 interfaces on the system:"
  ""
  "    Name                   : WiFi"
  "    State                  : $(if($script:connected -eq 'WiFi'){'connected'}else{'disconnected'})"
  "    SSID                   : GLOBAL"
  "    Signal                 : 92%"
  ""
  "    Name                   : WiFi 2"
  "    State                  : $(if($script:connected -eq 'WiFi 2'){'connected'}else{'disconnected'})"
  "    SSID                   : GLOBAL"
  "    Signal                 : 54%"
}
function Get-NetRoute {
  param([string]$InterfaceAlias,[string]$AddressFamily,[string]$DestinationPrefix,[string]$ErrorAction)
  if($InterfaceAlias -eq $script:route){[pscustomobject]@{InterfaceAlias=$InterfaceAlias}}
}
function Get-NetAdapterStatistics {
  param([string]$Name,[string]$ErrorAction)
  if(-not $script:stats.ContainsKey($Name)){throw "Wrong adapter chosen: $Name"}
  [pscustomobject]@{ReceivedBytes=$script:stats[$Name].rx;SentBytes=$script:stats[$Name].tx}
}
function Get-NetAdapter {
  param([string]$Name,[string]$ErrorAction)
  if($Name){return [pscustomobject]@{Name=$Name;Status='Up';LinkSpeed='72 Mbps'}}
  @([pscustomobject]@{Name='WiFi';Status='Up';LinkSpeed='72 Mbps'},
    [pscustomobject]@{Name='WiFi 2';Status='Up';LinkSpeed='72 Mbps'})
}
function Check([bool]$ok,[string]$message){if(!$ok){throw "TEST FAIL: $message"}}
function Total {
  $date=(Get-Date).ToString('yyyy-MM-dd')
  if(!$script:State.daily.ContainsKey($date)){return [double]0}
  return [double]$script:State.daily[$date].rx+[double]$script:State.daily[$date].tx
}
$connectedList=@(Get-ConnectedWifi)
Check ($connectedList.Count -eq 1) 'one connected interface recognized'
Check ($connectedList[0].name -eq 'WiFi') 'Intel interface name'
Check ($connectedList[0].signal -eq 92) 'Intel reported Wi-Fi signal is 92'
Write-Host ('Observed SSID=['+$connectedList[0].ssid+'] Target=['+$script:State.targetSsid+']')
Write-Host ('Observed equality='+[string]::Equals($connectedList[0].ssid,$script:State.targetSsid,[System.StringComparison]::OrdinalIgnoreCase))
Write-Host ('Re-fetch count='+@(Get-ConnectedWifi).Count)
Write-Host ('Active before sample: '+((Resolve-ActiveWifi) | Out-String))
Take-Sample
Write-Host ('After sample: active=['+$script:ActiveAdapter+'] status=['+$script:Status+'] error=['+$script:ErrorText+'] SSID=['+$script:Sample.ssid+']')
Check ($script:ActiveAdapter -eq 'WiFi') 'Intel adapter selected'
Check ((Total) -eq 0) 'Intel first sample is baseline, no historical count'
$script:stats['WiFi'].rx += 700
$script:stats['WiFi'].tx += 300
$script:SampleTime=(Get-Date).AddSeconds(-1)
Take-Sample
Check ($script:Rate.valid) 'Intel sample valid'
Check ((Total) -eq 1000) 'Intel delta counted exactly once'
$script:connected='WiFi 2';$script:route='WiFi 2'
Take-Sample
Check ($script:ActiveAdapter -eq 'WiFi 2') 'Realtek switched without restart'
Check ($script:WifiSignal -eq 54) 'Realtek signal is actual 54%'
Check ((Total) -eq 1000) 'switch baseline does not count large Realtek pre-existing counters'
Check (!$script:Rate.valid) 'first Realtek reading is a baseline, not a speed spike'
$script:stats['WiFi 2'].rx += 2000
$script:stats['WiFi 2'].tx += 4000
$script:SampleTime=(Get-Date).AddSeconds(-1)
Take-Sample
Check ($script:Rate.valid) 'Realtek produces live rates'
Check ((Total) -eq 7000) 'Realtek additional 6000 bytes counted once'
$summary=Make-Summary $true
Check ($summary.adapterName -eq 'WiFi 2') 'summary follows Realtek adapter'
Check ($summary.wifiSignal -eq 54) 'summary exposes Windows signal strength'
Check ($summary.todayTotal -eq 7000) 'summary does not double count'
$script:connected='none';$script:route='none'
Take-Sample
Check ($script:Status -eq 'wrong-network') 'disconnect reported'
Check ($null -eq $script:WifiSignal) 'disconnected signal unavailable'
Check ((Total) -eq 7000) 'no usage on disconnect'
$script:connected='WiFi';$script:route='WiFi'
$script:stats['WiFi'].rx += 100000
Take-Sample
Check ((Total) -eq 7000) 'reconnection baseline skips missed switch traffic'
$script:stats['WiFi'].rx += 250
$script:stats['WiFi'].tx += 150
$script:SampleTime=(Get-Date).AddSeconds(-1)
Take-Sample
Check ((Total) -eq 7400) 'reconnected Intel counts only new 400 bytes'
Write-Host 'PASS: mocked Intel/Realtek switching, no spikes, no duplicates, Windows signal, disconnected/reconnected baselines.' -ForegroundColor Green
