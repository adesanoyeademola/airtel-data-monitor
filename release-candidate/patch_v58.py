from pathlib import Path
u=Path('work/AirtelMonitorNative.cs')
e=Path('work/monitor.ps1')
s=u.read_text(encoding='utf-8')
p=e.read_text(encoding='utf-8')
def one(src,before,after):
    found=src.count(before)
    if found != 1:
        raise AssertionError(f'Expected exactly one match ({found}): {before[:125]!r}')
    return src.replace(before,after)

s=one(s,'const string AppVersion = "5.7.0";','const string AppVersion = "5.8.0";')

# Core bug: JavaScriptSerializer delivers numeric values, but earlier code
# round-tripped them through the current UI culture as strings and re-parsed
# them using an invariant thousands separator. "1234,5" became "12345".
s=one(s,
'''    double Num(Dictionary<string,object> d,string k){double n;return double.TryParse(Str(d,k),System.Globalization.NumberStyles.Any,System.Globalization.CultureInfo.InvariantCulture,out n)?n:0;}''',
'''    double Num(Dictionary<string,object> d,string k){
      object raw;
      if(!d.TryGetValue(k,out raw) || raw==null)return 0;
      try {
        double n=0;
        if(raw is string){
          if(!double.TryParse((string)raw,NumberStyles.Float,CultureInfo.InvariantCulture,out n))return 0;
        }else{
          n=Convert.ToDouble(raw,CultureInfo.InvariantCulture);
        }
        return double.IsNaN(n)||double.IsInfinity(n)?0:n;
      }catch{return 0;}
    }''')

# UI always produces short, Task Manager-style rates; rejects absurd values
# rather than squeezing illegible 12-digit figures into the speed card.
s=one(s,
'''      if(bytesPerSecond<0 || Double.IsNaN(bytesPerSecond) || Double.IsInfinity(bytesPerSecond))return "— Kbps";''',
'''      if(!PlausibleRate(bytesPerSecond))return "Measuring...";
'''.rstrip('\n'))
s=one(s,
'''    string Rate(double bytesPerSecond){''',
'''    // Hard safety bound (10 Gbps per direction). The engine additionally
    // checks intervals against the physical adapter link speed when available.
    bool PlausibleRate(double bytesPerSecond){
      return !Double.IsNaN(bytesPerSecond) && !Double.IsInfinity(bytesPerSecond)
             && bytesPerSecond>=0 && bytesPerSecond<=1250000000.0;
    }
    string Rate(double bytesPerSecond){''')

# Separate the indicator dot from the text so only the dot pulses.
s=one(s,'    Label status, wifi, adapter, last, today, down, up, week, downloadSpeed, uploadSpeed;',
'''    Label status, statusDot, wifi, adapter, last, today, down, up, week, downloadSpeed, uploadSpeed;
    System.Windows.Forms.Timer indicatorTimer;
    int indicatorState=1; // 0=live (green), 1=paused/waiting (yellow), 2=disconnected (red)
    double indicatorPhase=0;
    DateTime engineLaunchUtc=DateTime.MinValue;''')

s=one(s,
'''      refreshTimer = new System.Windows.Forms.Timer(); refreshTimer.Interval = 1000; refreshTimer.Tick+=(s,e)=>RefreshUsage(); refreshTimer.Start();''',
'''      refreshTimer = new System.Windows.Forms.Timer(); refreshTimer.Interval = 1000; refreshTimer.Tick+=(s,e)=>RefreshUsage(); refreshTimer.Start();
      indicatorTimer = new System.Windows.Forms.Timer{Interval=100};
      indicatorTimer.Tick+=(s,e)=>PulseIndicator();indicatorTimer.Start();''')

s=one(s,
'''      status=new Label {Text="Starting monitor...",Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleRight,ForeColor=muted};head.Controls.Add(status,1,0);''',
'''      status=new Label {Text="Starting monitor...",Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleRight,ForeColor=muted};head.Controls.Add(status,1,0);
      statusDot=new Label{Text="●",AutoSize=true,ForeColor=Color.FromArgb(236,185,65),
         Font=new Font("Segoe UI",14,FontStyle.Bold),TextAlign=ContentAlignment.MiddleCenter,
         Margin=new Padding(2,1,2,0)};''')

s=one(s,
'''status.AutoSize=true;status.Dock=DockStyle.None;status.Margin=new Padding(8,6,0,0);headerActions.Controls.Add(updateButton);headerActions.Controls.Add(status);''',
'''status.AutoSize=true;status.Dock=DockStyle.None;status.Margin=new Padding(2,7,7,0);headerActions.Controls.Add(updateButton);headerActions.Controls.Add(status);headerActions.Controls.Add(statusDot);''')

# Status indicator has its own 100-ms timer. The dot gently oscillates in
# brightness while the sample heartbeat remains live. Yellow/red are static.
s=one(s,
'''    void RefreshUsage(){''',
'''    void SetIndicator(string label,int state){
      indicatorState=state;status.Text=label;
      status.ForeColor=state==0?Color.FromArgb(79,212,161):
        state==1?Color.FromArgb(236,185,65):Color.FromArgb(240,105,105);
      if(state!=0)statusDot.ForeColor=status.ForeColor;
    }
    void PulseIndicator(){
      if(statusDot==null||statusDot.IsDisposed)return;
      if(indicatorState!=0)return;
      indicatorPhase+=0.32;
      double brightness=(Math.Sin(indicatorPhase)+1.0)/2.0;
      statusDot.ForeColor=Color.FromArgb(
        (int)(38+41*brightness),(int)(115+97*brightness),(int)(81+80*brightness));
    }
    void RefreshUsage(){''')

s=one(s,
'''status.Text= stat=="tracking"?"●  Monitoring live":stat=="not-configured"?"Set your hotspot":stat=="wrong-network"?"Waiting for hotspot":stat=="adapter-error"?"Adapter error":"Monitoring";status.ForeColor=stat=="tracking"?Color.FromArgb(79,212,161):muted;''',
'''if(stat=="tracking")SetIndicator("Monitoring live",0);
        else if(stat=="wrong-network")SetIndicator("Not connected",2);
        else if(stat=="adapter-error")SetIndicator("Adapter disconnected",2);
        else if(stat=="not-configured")SetIndicator("Monitoring paused",1);
        else SetIndicator("Starting monitor",1);''')

s=one(s,
'''        bool legacyService = stat=="tracking" && !timestampValid;''',
'''        bool legacyService = stat=="tracking" && !timestampValid;
        if(stat=="tracking" && !fresh)SetIndicator("Monitoring paused",1);''')

s=one(s,
'''            status.Text="●  Old monitoring service";
            status.ForeColor=Color.FromArgb(255,185,100);''',
'''            SetIndicator("Old monitoring service",1);''')

s=one(s,
'''            downloadSpeed.Text=Rate(fallbackValid && fallbackRx>0 && directRx==0?fallbackRx:directRx);
            uploadSpeed.Text=Rate(fallbackValid && fallbackTx>0 && directTx==0?fallbackTx:directTx);''',
'''            double shownRx=fallbackValid && fallbackRx>0 && directRx==0?fallbackRx:directRx;
            double shownTx=fallbackValid && fallbackTx>0 && directTx==0?fallbackTx:directTx;
            downloadSpeed.Text=Rate(shownRx);
            uploadSpeed.Text=Rate(shownTx);''')

s=one(s,
'''          if(seconds>0.5 && seconds<30 && diffRx>=0 && diffTx>=0){''',
'''          if(seconds>0.5 && seconds<30 && diffRx>=0 && diffTx>=0 &&
             PlausibleRate(diffRx/seconds) && PlausibleRate(diffTx/seconds)){''')

s=one(s,
'''      }catch {status.Text="Connecting to monitor...";status.ForeColor=muted;previousRateSampleId=-1;previousUsageRx=-1;previousUsageTx=-1;downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";}''',
'''      }catch {
        bool starting=(DateTime.UtcNow-engineLaunchUtc).TotalSeconds<8;
        SetIndicator(starting?"Starting monitor":"Service disconnected",starting?1:2);
        previousRateSampleId=-1;previousUsageRx=-1;previousUsageTx=-1;
        downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
      }''')

s=one(s,
'''      try {var pi=new ProcessStartInfo("powershell.exe","-NoProfile -ExecutionPolicy Bypass -File \\""+ps+"\\" -NoBrowser"+(share?" -Share":""));''',
'''      engineLaunchUtc=DateTime.UtcNow;
      try {var pi=new ProcessStartInfo("powershell.exe","-NoProfile -ExecutionPolicy Bypass -File \\""+ps+"\\" -NoBrowser"+(share?" -Share":""));''')

s=one(s,
'''        status.Text="● Service restart blocked";
        status.ForeColor=Color.FromArgb(255,185,100);''',
'''        SetIndicator("Service restart blocked",1);''')

s=one(s,
'''    void Quit(){closing=true;refreshTimer.Stop();''',
'''    void Quit(){closing=true;refreshTimer.Stop();if(indicatorTimer!=null)indicatorTimer.Stop();''')

# The adapter-counter engine independently rejects implausibly high rates,
# so neither a malformed sample nor rollover can corrupt saved daily totals.
# Make the cap reflect the adapter's link speed when present, with a 10Gbps
# absolute ceiling and enough headroom for reporting differences.
marker='''            if ($drx -ge 0 -and $dtx -ge 0 -and $elapsed -gt 0.2 -and $elapsed -le 5) {'''
replacement='''            $maxBytesPerSecond = [double]1250000000
            try {
                $linkSpeed=[string](Get-NetAdapter -Name $script:State.adapterName -ErrorAction Stop).LinkSpeed
                $linkMatch=[regex]::Match($linkSpeed,'(?i)([0-9]+(?:[.,][0-9]+)?)\\s*([KMG])bps')
                if($linkMatch.Success){
                    $linkValue=[double]::Parse($linkMatch.Groups[1].Value.Replace(',','.'),[System.Globalization.CultureInfo]::InvariantCulture)
                    $factor=switch($linkMatch.Groups[2].Value.ToUpperInvariant()){'G' {[double]1000000000}; 'M' {[double]1000000}; default {[double]1000}}
                    # Twice the negotiated link speed accommodates sampling jitter.
                    $maxBytesPerSecond=[math]::Min($maxBytesPerSecond,[math]::Max([double]12500000,$linkValue*$factor/8*2))
                }
            }catch{}
            $withinCapacity=($elapsed -gt 0.2 -and $drx -ge 0 -and $dtx -ge 0 -and
                ($drx/$elapsed) -le $maxBytesPerSecond -and ($dtx/$elapsed) -le $maxBytesPerSecond)
            if ($withinCapacity -and $elapsed -le 5) {'''
p=one(p,marker,replacement)
u.write_text(s,encoding='utf-8')
e.write_text(p,encoding='utf-8')
assert 'NumberStyles.Float,CultureInfo.InvariantCulture' in s
assert 'indicatorTimer.Tick' in s and 'PlausibleRate(shownRx)' not in s
assert 'maxBytesPerSecond' in p
print('T-Net 5.8: culture-safe rates, adapter bounds, pulsing status colors')
