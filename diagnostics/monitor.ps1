# Airtel Data Monitor v2 (Windows PowerShell 5.1, .NET Framework; no Python)
# Counts Wi-Fi adapter traffic while the specified hotspot SSID is connected.
# This is network traffic, not a live Airtel carrier-balance API.
param([switch]$Share, [switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$script:Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:DataDir = Join-Path $script:Root 'data'
$script:StatePath = Join-Path $script:DataDir 'usage.json'
$script:Port = 8787
$script:Sharing = [bool]$Share
$script:State = @{ version=2; targetSsid=''; adapterName='Wi-Fi'; daily=@{}; lastUpdated='' }
$script:Sample = @{ valid=$false; rx=[double]0; tx=[double]0; adapter=''; ssid=''; lastSample=(Get-Date).ToString('o') }
$script:Status = 'not-configured'
$script:Rate = @{ rxBps=[double]0; txBps=[double]0; valid=$false; sampleTime=''; sampleId=[long]0 }
$script:SampleTime = [datetime]::MinValue
$script:ErrorText = ''
$script:AccessCode = [string](Get-Random -Minimum 10000000 -Maximum 99999999)
$script:Sessions = @{}
$script:Failures = @{}
$script:LastSavedAt = [datetime]::MinValue
$script:Running = $true

function Make-Json($obj) { return ($obj | ConvertTo-Json -Depth 15 -Compress) }
function Write-State {
    try {
        if (-not (Test-Path -LiteralPath $script:DataDir)) { New-Item -ItemType Directory -Force -Path $script:DataDir | Out-Null }
        $tmp = "$script:StatePath.tmp"
        [System.IO.File]::WriteAllText($tmp, (Make-Json $script:State), ([System.Text.UTF8Encoding]::new($false)))
        Move-Item -LiteralPath $tmp -Destination $script:StatePath -Force
        $script:LastSavedAt = Get-Date
    } catch { Write-Host "Save warning: $($_.Exception.Message)" -ForegroundColor Yellow }
}
function Read-State {
    if (-not (Test-Path -LiteralPath $script:StatePath)) { return }
    try {
        $s = Get-Content -LiteralPath $script:StatePath -Encoding UTF8 -Raw | ConvertFrom-Json
        $script:State.targetSsid = [string]$s.targetSsid
        $script:State.adapterName = if ($s.adapterName) { [string]$s.adapterName } else { 'Wi-Fi' }
        $script:State.lastUpdated = [string]$s.lastUpdated
        if ($s.daily) {
            foreach ($p in $s.daily.PSObject.Properties) {
                $script:State.daily[$p.Name] = @{ rx=[double]$p.Value.rx; tx=[double]$p.Value.tx }
            }
        }
    } catch { Write-Host "Previous usage file could not be loaded: $($_.Exception.Message)" -ForegroundColor Yellow }
}
function Get-HotspotSSID {
    try {
        $netsh = & netsh wlan show interfaces 2>$null | Out-String
        $m = [regex]::Match($netsh, '(?m)^[ \t]*SSID[ \t]*:[ \t]*(.*?)[ \t]*$')
        if ($m.Success) { return $m.Groups[1].Value.Trim() }
    } catch { }
    try {
        $profile = Get-NetConnectionProfile -InterfaceAlias $script:State.adapterName -ErrorAction Stop | Select-Object -First 1
        if ($profile) { return [string]$profile.Name }
    } catch { }
    return ''
}
function Get-Adapters {
    try {
        return @(Get-NetAdapter -ErrorAction Stop | Where-Object { $_.Status -eq 'Up' } | ForEach-Object { [string]$_.Name })
    } catch { return @('Wi-Fi') }
}
function Get-LanAddress {
    try {
        $addresses = @(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias $script:State.adapterName -ErrorAction Stop |
            Where-Object { $_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)' -and $_.IPAddress -notmatch '^169\.254\.' })
        if ($addresses.Count -gt 0) { return [string]$addresses[0].IPAddress }
    } catch { }
    return ''
}
function Take-Sample {
    # Rates reset when disconnected, adapter counters reset, or the sampling interval is invalid.
    $script:Rate.valid = $false
    $script:Rate.rxBps = [double]0
    $script:Rate.txBps = [double]0
    $ssid = Get-HotspotSSID
    if ([string]::IsNullOrWhiteSpace($ssid)) {
        $script:Status = 'wrong-network'
        $script:SampleTime = [datetime]::MinValue
        $script:Sample.valid = $false
        $script:Sample.ssid = ''
        return
    }
    try {
        $stat = Get-NetAdapterStatistics -Name $script:State.adapterName -ErrorAction Stop
        $sampleAt = Get-Date
        $rx = [double]$stat.ReceivedBytes
        $tx = [double]$stat.SentBytes
        if ($rx -lt 0 -or $tx -lt 0) { throw 'Adapter counters unavailable.' }
        if ($script:Sample.valid -and $script:Sample.adapter -eq $script:State.adapterName -and $script:Sample.ssid -eq $ssid) {
            $drx = $rx - [double]$script:Sample.rx
            $dtx = $tx - [double]$script:Sample.tx
            $elapsed = if ($script:SampleTime -ne [datetime]::MinValue) { ($sampleAt - $script:SampleTime).TotalSeconds } else { 0 }
            # Reject negative/reset counters and intervals long enough to hide a disconnect.
            # Large valid transfers are not silently discarded solely because of a 2 GB threshold.
            if ($drx -ge 0 -and $dtx -ge 0 -and $elapsed -gt 0.2 -and $elapsed -le 15) {
                $script:Rate.rxBps = $drx / $elapsed
                $script:Rate.txBps = $dtx / $elapsed
                $script:Rate.valid = $true
                $day = (Get-Date).ToString('yyyy-MM-dd')
                if (-not $script:State.daily.ContainsKey($day)) { $script:State.daily[$day] = @{ rx=[double]0; tx=[double]0 } }
                $script:State.daily[$day].rx += $drx
                $script:State.daily[$day].tx += $dtx
                if (($drx + $dtx) -gt 0) { $script:State.lastUpdated = (Get-Date).ToString('o') }
            }
        }
        $script:Sample.valid = $true
        $script:Sample.rx = $rx
        $script:Sample.tx = $tx
        $script:Sample.adapter = $script:State.adapterName
        $script:Sample.ssid = $ssid
        $script:SampleTime = $sampleAt
        $script:Rate.sampleTime = $script:SampleTime.ToString('o')
        $script:Rate.sampleId = [long]$script:Rate.sampleId + 1
        $script:Status = 'tracking'; $script:ErrorText = ''
    } catch {
        $script:Sample.valid = $false
        $script:SampleTime = [datetime]::MinValue
        $script:Status = 'adapter-error'
        $script:ErrorText = $_.Exception.Message
    }
}
function Make-Summary($local) {
    $days = @()
    foreach ($date in @($script:State.daily.Keys | Sort-Object)) {
        $item = $script:State.daily[$date]
        $days += @{ date=$date; rx=[double]$item.rx; tx=[double]$item.tx; total=([double]$item.rx+[double]$item.tx) }
    }
    $today = (Get-Date).ToString('yyyy-MM-dd')
    $todayItem = if ($script:State.daily.ContainsKey($today)) { $script:State.daily[$today] } else { @{ rx=0; tx=0 } }
    $lastSeven = @($days | Where-Object { $_.date -ge (Get-Date).AddDays(-6).ToString('yyyy-MM-dd') })
    $weekTotal = [double]0
    foreach ($d in $lastSeven) { $weekTotal += [double]$d.total }
    return @{
        status=$script:Status; error=$script:ErrorText; currentSsid=$script:Sample.ssid
        targetSsid=$script:State.targetSsid; adapterName=$script:State.adapterName
        adapterChoices=@(Get-Adapters); todayRx=[double]$todayItem.rx; todayTx=[double]$todayItem.tx
        todayTotal=([double]$todayItem.rx+[double]$todayItem.tx); sevenDayTotal=$weekTotal
        days=$days; lastUpdated=$script:State.lastUpdated; now=(Get-Date).ToString('o')
        sharing=$script:Sharing; lanAddress=(Get-LanAddress); accessCode= $(if ($local -and $script:Sharing) { $script:AccessCode } else { '' })
        rateRxBps=[double]$script:Rate.rxBps; rateTxBps=[double]$script:Rate.txBps
        rateValid=[bool]$script:Rate.valid; rateSampleId=[long]$script:Rate.sampleId; rateSampleTime=[string]$script:Rate.sampleTime
        dataIs='Wi-Fi adapter traffic, not Airtel billing usage'
    }
}
function Read-Request($client) {
    $stream = $client.GetStream()
    $stream.ReadTimeout = 1500
    $buf = New-Object byte[] 8192
    $ms = New-Object System.IO.MemoryStream
    $headerEnd = -1
    while ($ms.Length -lt 65536 -and $headerEnd -lt 0) {
        $read = $stream.Read($buf, 0, $buf.Length)
        if ($read -le 0) { break }
        $ms.Write($buf, 0, $read)
        $s = [System.Text.Encoding]::ASCII.GetString($ms.ToArray())
        $headerEnd = $s.IndexOf("`r`n`r`n")
    }
    if ($headerEnd -lt 0) { throw 'Invalid HTTP request.' }
    $all = $ms.ToArray(); $head = [System.Text.Encoding]::ASCII.GetString($all,0,$headerEnd)
    $rows = $head -split "`r`n"
    $requestLine = $rows[0] -split ' '
    if ($requestLine.Count -lt 2) { throw 'Invalid request line.' }
    $headers = @{}
    foreach ($line in @($rows | Select-Object -Skip 1)) {
        $pos = $line.IndexOf(':')
        if ($pos -gt 0) { $headers[$line.Substring(0,$pos).Trim().ToLowerInvariant()] = $line.Substring($pos+1).Trim() }
    }
    $bodyStart = $headerEnd + 4
    $contentLen = 0
    if ($headers.ContainsKey('content-length')) { [void][int]::TryParse($headers['content-length'], [ref]$contentLen) }
    if ($contentLen -gt 16384) { throw 'Request body too large.' }
    $body = New-Object System.IO.MemoryStream
    if ($all.Length -gt $bodyStart) { $body.Write($all,$bodyStart,$all.Length-$bodyStart) }
    while ($body.Length -lt $contentLen) {
        $got = $stream.Read($buf,0,[Math]::Min($buf.Length, $contentLen-[int]$body.Length))
        if ($got -le 0) { break }
        $body.Write($buf,0,$got)
    }
    return @{ method=$requestLine[0].ToUpperInvariant(); path=($requestLine[1] -split '\?')[0]; headers=$headers; body=[System.Text.Encoding]::UTF8.GetString($body.ToArray()); stream=$stream }
}
function Reply($stream, [int]$status, [string]$contentType, [string]$body, [string]$cookie='') {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    $reason = switch ($status) { 200 {'OK'} 400 {'Bad Request'} 401 {'Unauthorized'} 403 {'Forbidden'} 404 {'Not Found'} 405 {'Method Not Allowed'} 429 {'Too Many Requests'} default {'Server Error'} }
    $h = "HTTP/1.1 $status $reason`r`nContent-Type: $contentType`r`nContent-Length: $($bytes.Length)`r`nCache-Control: no-store`r`nX-Content-Type-Options: nosniff`r`nX-Frame-Options: DENY`r`nReferrer-Policy: no-referrer`r`nConnection: close`r`n"
    if ($cookie) { $h += "Set-Cookie: $cookie`r`n" }
    $h += "`r`n"
    $bhead = [System.Text.Encoding]::ASCII.GetBytes($h)
    $stream.Write($bhead,0,$bhead.Length)
    $stream.Write($bytes,0,$bytes.Length)
    $stream.Flush()
}
function Allowed-Remote($address) {
    if ($address -eq '127.0.0.1' -or $address -eq '::1') { return $true }
    if (-not $script:Sharing) { return $false }
    if ($address -match '^10\.' -or $address -match '^192\.168\.' -or $address -match '^172\.(1[6-9]|2[0-9]|3[01])\.') { return $true }
    return $false
}
function New-SessionToken {
    $raw = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($raw) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($raw).TrimEnd('=').Replace('+','-').Replace('/','_')
}
function Handle-Client($client) {
    $remote = [string]$client.Client.RemoteEndPoint.Address
    if ($remote.StartsWith('::ffff:')) { $remote = $remote.Substring(7) }
    try {
        $req = Read-Request $client
        $st = $req.stream
        if (-not (Allowed-Remote $remote)) { Reply $st 403 'text/plain; charset=utf-8' 'Remote access is disabled.'; return }
        $local = ($remote -eq '127.0.0.1' -or $remote -eq '::1')
        $path = $req.path
        if ($path -eq '/favicon.svg' -and $req.method -eq 'GET') {
            $svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#e9354a"/><path d="M19 33c8-8 18-8 26 0M25 40c4-4 10-4 14 0" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/><circle cx="32" cy="47" r="3" fill="#fff"/></svg>'
            Reply $st 200 'image/svg+xml' $svg; return
        }
        if ($path -eq '/' -and $req.method -eq 'GET') {
            $p = Join-Path $script:Root 'web\index.html'
            Reply $st 200 'text/html; charset=utf-8' ([System.IO.File]::ReadAllText($p,[System.Text.Encoding]::UTF8)); return
        }
        if ($path -eq '/api/auth' -and $req.method -eq 'POST') {
            if ($local) { Reply $st 200 'application/json' '{"ok":true}'; return }
            $hits = @($script:Failures[$remote] | Where-Object { $_ -gt (Get-Date).AddMinutes(-5) })
            if ($hits.Count -ge 8) { Reply $st 429 'application/json' '{"error":"Too many attempts. Retry in five minutes."}'; return }
            $payload = $null
            try { $payload = $req.body | ConvertFrom-Json } catch { Reply $st 400 'application/json' '{"error":"Invalid JSON."}'; return }
            if ([string]$payload.code -cne $script:AccessCode) {
                $script:Failures[$remote] = @($hits) + @((Get-Date))
                Reply $st 401 'application/json' '{"error":"Incorrect access code."}'; return
            }
            $script:Failures.Remove($remote)
            $token = New-SessionToken
            $script:Sessions[$token] = (Get-Date).AddHours(12)
            Reply $st 200 'application/json' '{"ok":true}' "ADM_SESSION=$token; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200"; return
        }
        $authorized = $local
        if (-not $local) {
            $cookies = if ($req.headers.ContainsKey('cookie')) { [string]$req.headers['cookie'] } else { '' }
            $m = [regex]::Match($cookies,'(?:^|;\s*)ADM_SESSION=([A-Za-z0-9_-]+)')
            if ($m.Success -and $script:Sessions.ContainsKey($m.Groups[1].Value)) {
                $authorized = ($script:Sessions[$m.Groups[1].Value] -gt (Get-Date))
            }
        }
        if (-not $authorized) { Reply $st 401 'application/json; charset=utf-8' '{"error":"Pair your iPhone with the access code shown on Windows."}'; return }
        if ($req.method -eq 'POST' -and $req.headers['content-type'] -notmatch '^application/json(?:\s*;|\s*$)') {
            Reply $st 400 'application/json' '{"error":"Expected JSON body."}'; return
        }
        if ($path -eq '/api/summary' -and $req.method -eq 'GET') {
            Reply $st 200 'application/json; charset=utf-8' (Make-Json (Make-Summary $local)); return
        }
        if ($path -eq '/api/config' -and $req.method -eq 'POST') {
            if (-not $local) { Reply $st 403 'application/json' '{"error":"Change settings on the Windows laptop."}'; return }
            try { $payload = $req.body | ConvertFrom-Json } catch { Reply $st 400 'application/json' '{"error":"Invalid JSON."}'; return }
            $target = [string]$payload.targetSsid
            $adapter = [string]$payload.adapterName
            if ([string]::IsNullOrWhiteSpace($target) -or $target.Length -gt 100 -or [string]::IsNullOrWhiteSpace($adapter) -or $adapter.Length -gt 100) {
                Reply $st 400 'application/json' '{"error":"Select the hotspot name and Wi-Fi adapter."}'; return
            }
            if (@(Get-Adapters) -notcontains $adapter) { Reply $st 400 'application/json' '{"error":"The selected adapter is unavailable."}'; return }
            if (-not [string]::Equals($script:State.targetSsid, $target.Trim(), [System.StringComparison]::OrdinalIgnoreCase)) {
                $script:State.daily = @{}
            }
            $script:State.targetSsid = $target.Trim()
            $script:State.adapterName = $adapter
            $script:Sample.valid = $false
            $script:SampleTime = [datetime]::MinValue
            Write-State
            Reply $st 200 'application/json' '{"ok":true}'; return
        }
        if ($path -eq '/api/reset' -and $req.method -eq 'POST') {
            if (-not $local) { Reply $st 403 'application/json' '{"error":"Reset data only from Windows."}'; return }
            try { $payload = $req.body | ConvertFrom-Json } catch { Reply $st 400 'application/json' '{"error":"Invalid JSON."}'; return }
            if ([string]$payload.scope -eq 'today') {
                $script:State.daily.Remove((Get-Date).ToString('yyyy-MM-dd'))
            } elseif ([string]$payload.scope -eq 'all') {
                $script:State.daily = @{}
            } else { Reply $st 400 'application/json' '{"error":"Invalid reset scope."}'; return }
            $script:Sample.valid = $false
            $script:SampleTime = [datetime]::MinValue
            Write-State
            Reply $st 200 'application/json' '{"ok":true}'; return
        }
        if ($path -eq '/api/export' -and $req.method -eq 'GET') {
            $csv = "Date,Received bytes,Sent bytes,Total bytes`r`n"
            foreach ($d in @($script:State.daily.Keys | Sort-Object)) {
                $x = $script:State.daily[$d]
                $csv += "$d,$([math]::Round([double]$x.rx)),$([math]::Round([double]$x.tx)),$([math]::Round([double]$x.rx+[double]$x.tx))`r`n"
            }
            Reply $st 200 'text/csv; charset=utf-8' $csv; return
        }
        Reply $st 404 'application/json' '{"error":"Not found."}'
    } catch {
        Write-Host "Request warning: $($_.Exception.Message)" -ForegroundColor DarkYellow
    } finally { try { $client.Close() } catch { } }
}

Read-State
$bindIp = if ($script:Sharing) { [System.Net.IPAddress]::Any } else { [System.Net.IPAddress]::Loopback }
$listener = [System.Net.Sockets.TcpListener]::new($bindIp,[int]$script:Port)
try { $listener.Start() } catch {
    Write-Host "Could not start port $script:Port. Close any other Airtel Monitor window and try again." -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host 'Press Enter to close'
    exit 1
}
Write-Host ''
Write-Host '==================================================' -ForegroundColor Red
Write-Host '  AIRTEL DATA MONITOR - LIVE NETWORK USAGE' -ForegroundColor White
Write-Host '==================================================' -ForegroundColor Red
Write-Host 'No Python. No extra downloads. Leave this window open.'
Write-Host "On this laptop: http://127.0.0.1:$script:Port/" -ForegroundColor Cyan
if ($script:Sharing) {
    $ip = Get-LanAddress
    if ($ip) { Write-Host "On iPhone Safari (same reachable network): http://$($ip):$script:Port/" -ForegroundColor Cyan }
    else { Write-Host 'Cannot detect a local Wi-Fi address yet; check laptop Wi-Fi connection.' -ForegroundColor Yellow }
    Write-Host "iPhone pairing code (this launch): $script:AccessCode" -ForegroundColor Yellow
    Write-Host 'If iPhone cannot connect: Android hotspots can isolate clients; Windows Firewall may also block access.' -ForegroundColor Yellow
} else {
    Write-Host 'Private mode: iPhone access is off. Use the iPhone launcher to share.' -ForegroundColor DarkGray
}
Write-Host 'Traffic is recorded ONLY while your chosen hotspot SSID is connected.'
Write-Host 'Use Ctrl+C or close this window to stop monitoring.' -ForegroundColor Gray
if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$script:Port/" }
$nextPoll = Get-Date
try {
    while ($script:Running) {
        if ((Get-Date) -ge $nextPoll) {
            Take-Sample
            $nextPoll = (Get-Date).AddSeconds(5)
            if (((Get-Date) - $script:LastSavedAt).TotalSeconds -ge 15) { Write-State }
        }
        if ($listener.Pending()) {
            $client = $listener.AcceptTcpClient()
            Handle-Client $client
        } else { Start-Sleep -Milliseconds 120 }
    }
} finally {
    Write-State
    $listener.Stop()
}
