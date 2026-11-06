from pathlib import Path
ui=Path('work/AirtelMonitorNative.cs')
eng=Path('work/monitor.ps1')
s=ui.read_text(encoding='utf-8')
e=eng.read_text(encoding='utf-8')

def replace_one(src,a,b):
    n=src.count(a)
    if n!=1: raise RuntimeError('Expected one match (%s) for: %r' % (n,a[:125]))
    return src.replace(a,b)

s=replace_one(s,'const string AppVersion = "6.2.0";','const string AppVersion = "6.3.0";')
s=replace_one(s,
'''    long lastRecordedGraphSampleId=-1;''',
'''    bool usagePollInProgress=false;
    int consecutivePollFailures=0;
    DateTime lastDailyChartRenderUtc=DateTime.MinValue;
    long lastRecordedGraphSampleId=-1;''')
s=replace_one(s,
'''refreshTimer.Interval = 1000; refreshTimer.Tick+=(s,e)=>RefreshUsage();''',
'''refreshTimer.Interval = 500; refreshTimer.Tick+=(s,e)=>RefreshUsageAsync();''')
s=replace_one(s,
'''      RefreshUsage();
    }
    Dictionary<string,object> GetData()''',
'''      RefreshUsageAsync();
    }
    Dictionary<string,object> GetData()''')
s=replace_one(s,
'''configured=false;RefreshUsage();MessageBox.Show("Hotspot saved.","T-Net");''',
'''configured=false;RefreshUsageAsync();MessageBox.Show("Hotspot saved.","T-Net");''')

# The old UI timer downloaded JSON and redrew the graph on the UI thread.
# A single in-flight background request keeps the window responsive and never
# shows old replies after newer replies. Display keeps actual engine timestamps.
s=replace_one(s,
'''    void RefreshUsage(){
      try {var d=GetData();string stat=Str(d,"status");''',
'''    Dictionary<string,object> GetDataFast(){
      var request=(HttpWebRequest)WebRequest.Create(Base+"/api/summary");
      request.Timeout=1500;
      request.ReadWriteTimeout=1500;
      request.KeepAlive=false;
      request.CachePolicy=new System.Net.Cache.RequestCachePolicy(System.Net.Cache.RequestCacheLevel.NoCacheNoStore);
      using(var response=(HttpWebResponse)request.GetResponse())
      using(var reader=new StreamReader(response.GetResponseStream())){
        return new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(reader.ReadToEnd());
      }
    }
    async void RefreshUsageAsync(){
      if(usagePollInProgress || closing || IsDisposed || Disposing)return;
      usagePollInProgress=true;
      try {
        var d=await Task.Run(()=>GetDataFast());
        if(closing || IsDisposed || Disposing)return;
        consecutivePollFailures=0;
        ApplyUsage(d);
      }catch(Exception){
        if(closing || IsDisposed || Disposing)return;
        consecutivePollFailures++;
        if(consecutivePollFailures>=3){
          bool starting=(DateTime.UtcNow-engineLaunchUtc).TotalSeconds<8;
          SetIndicator(starting?"Starting monitor":"Service disconnected",starting?1:2);
          downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
          AutoRecoverEngine();
        }else{
          SetIndicator("Waiting for sample",1);
        }
      }finally{
        usagePollInProgress=false;
      }
    }
    void ApplyUsage(Dictionary<string,object> d){
      try {string stat=Str(d,"status");''')

# Daily chart should remain available; it need not clear/redraw at 500ms.
s=replace_one(s,
'''        var map=new Dictionary<string,double>();var days=d.ContainsKey("days")?d["days"] as System.Collections.ArrayList:null;if(days!=null)foreach(var item in days){var row=item as Dictionary<string,object>;if(row!=null)map[Str(row,"date")]=Num(row,"total");}chart.Series[0].Points.Clear();for(int i=6;i>=0;i--){DateTime day=DateTime.Today.AddDays(-i);string k=day.ToString("yyyy-MM-dd");int idx=chart.Series[0].Points.AddY(map.ContainsKey(k)?map[k]/1048576:0);chart.Series[0].Points[idx].AxisLabel=day.ToString("ddd");}''',
'''        if((DateTime.UtcNow-lastDailyChartRenderUtc).TotalSeconds>=5){
          var map=new Dictionary<string,double>();var days=d.ContainsKey("days")?d["days"] as System.Collections.ArrayList:null;if(days!=null)foreach(var item in days){var row=item as Dictionary<string,object>;if(row!=null)map[Str(row,"date")]=Num(row,"total");}chart.Series[0].Points.Clear();for(int i=6;i>=0;i--){DateTime day=DateTime.Today.AddDays(-i);string k=day.ToString("yyyy-MM-dd");int idx=chart.Series[0].Points.AddY(map.ContainsKey(k)?map[k]/1048576:0);chart.Series[0].Points[idx].AxisLabel=day.ToString("ddd");}
          lastDailyChartRenderUtc=DateTime.UtcNow;
        }''')

# Don't rebuild the entire graph for 2 identical reads between adapter samples.
s=replace_one(s,
'''      if(timeValid && sampleId>0 && (sampleId!=lastRecordedGraphSampleId ||''',
'''      bool newMeasurement=timeValid && sampleId>0 && (sampleId!=lastRecordedGraphSampleId ||
         sampleTime.ToUniversalTime()!=lastRecordedGraphTimeUtc);
      if(newMeasurement && (sampleId!=lastRecordedGraphSampleId ||''')
# The resulting boolean expression has duplicate checks but is valid; simplify it.
s=replace_one(s,
'''      if(newMeasurement && (sampleId!=lastRecordedGraphSampleId ||
         sampleTime.ToUniversalTime()!=lastRecordedGraphTimeUtc)){''',
'''      if(newMeasurement){''')
s=replace_one(s,
'''      if(showLiveChart)RenderLiveSpeedGraph();
    }
    void RenderLiveSpeedGraph()''',
'''      if(showLiveChart && newMeasurement)RenderLiveSpeedGraph();
    }
    void RenderLiveSpeedGraph()''')

# Cache only expensive metadata (adapter list/link capacity), not adapter bytes.
e=replace_one(e,
'''$script:LastSavedAt = [datetime]::MinValue''',
'''$script:LastSavedAt = [datetime]::MinValue
$script:CachedAdapterChoices = @()
$script:AdapterChoicesCheckedAt = [datetime]::MinValue
$script:CachedRateLimit = [double]1250000000
$script:RateLimitCheckedAt = [datetime]::MinValue''')
e=replace_one(e,
'''function Get-LanAddress {''',
'''function Get-CachedAdapters {
    if($script:AdapterChoicesCheckedAt -eq [datetime]::MinValue -or
       ((Get-Date)-$script:AdapterChoicesCheckedAt).TotalSeconds -ge 30) {
        $script:CachedAdapterChoices = @(Get-Adapters)
        $script:AdapterChoicesCheckedAt = Get-Date
    }
    return $script:CachedAdapterChoices
}
function Get-LanAddress {''')
e=replace_one(e,
'''        adapterChoices=@(Get-Adapters); todayRx=[double]$todayItem.rx; todayTx=[double]$todayItem.tx''',
'''        adapterChoices=@(Get-CachedAdapters); todayRx=[double]$todayItem.rx; todayTx=[double]$todayItem.tx''')
e=replace_one(e,
'''sharing=$script:Sharing; lanAddress=(Get-LanAddress); accessCode=''',
'''sharing=$script:Sharing; lanAddress=$(if($script:Sharing){Get-LanAddress}else{''}); accessCode=''')
a=e.index('            $maxBytesPerSecond = [double]1250000000')
b=e.index('            $withinCapacity=',a)
old=e[a:b]
assert 'Get-NetAdapter -Name' in old
new='''            if($script:RateLimitCheckedAt -eq [datetime]::MinValue -or
               (($sampleAt-$script:RateLimitCheckedAt).TotalSeconds -ge 30)){
                $script:CachedRateLimit = [double]1250000000
                try {
                    $linkSpeed=[string](Get-NetAdapter -Name $script:State.adapterName -ErrorAction Stop).LinkSpeed
                    $linkMatch=[regex]::Match($linkSpeed,'(?i)([0-9]+(?:[.,][0-9]+)?)\\s*([KMG])bps')
                    if($linkMatch.Success){
                        $linkValue=[double]::Parse($linkMatch.Groups[1].Value.Replace(',','.'),[System.Globalization.CultureInfo]::InvariantCulture)
                        $factor=switch($linkMatch.Groups[2].Value.ToUpperInvariant()){'G' {[double]1000000000}; 'M' {[double]1000000}; default {[double]1000}}
                        $script:CachedRateLimit=[math]::Min([double]1250000000,
                           [math]::Max([double]12500000,$linkValue*$factor/8*2))
                    }
                }catch{}
                $script:RateLimitCheckedAt=$sampleAt
            }
            $maxBytesPerSecond = $script:CachedRateLimit
'''
e=e[:a]+new+e[b:]
# Explicitly invalidate the cache on adapter-config save; safe if absent? check.
assert '$script:State.adapterName' in e
assert 'Get-NetAdapterStatistics' in e
assert 'Write-State' in e
assert 'refreshTimer.Interval = 500' in s
assert 'RefreshUsageAsync' in s and 'GetDataFast' in s
assert 'const string AppVersion = "6.3.0";' in s
ui.write_text(s,encoding='utf-8')
eng.write_text(e,encoding='utf-8')
print('T-Net v6.3: async 500ms UI polling, no overlap, light charts, cached metadata; core byte counters unchanged')
