from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8")
def once(a,b):
    global s
    n=s.count(a)
    if n!=1: raise RuntimeError("Expected one match (%d): %r"%(n,a[:110]))
    s=s.replace(a,b)
once('const string AppVersion = "6.6.0";','const string AppVersion = "6.7.0";')
once('using System.Diagnostics;','using System.Diagnostics;\nusing System.Net.NetworkInformation;')

once('''    bool checkingUpdates = false;''',
'''    // Windows Network Interface performance counters are the preferred
    // LIVE speed source. The PowerShell adapter engine remains responsible
    // for ALL cumulative usage, saved history, hotspot connection and status.
    readonly object liveCounterLock=new object();
    System.Threading.Timer liveCounterTimer;
    PerformanceCounter nativeRxCounter, nativeTxCounter;
    string nativeCounterInstance="";
    string nativeCounterAdapter="";
    DateTime lastNativeSampleUtc=DateTime.MinValue;
    double nativeRxBytesPerSecond=0, nativeTxBytesPerSecond=0;
    long nativeSampleId=0;
    bool nativeCounterAvailable=false;
    int nativeCounterErrors=0;
    DateTime nativeRetryUtc=DateTime.MinValue;
    long lastDisplayedNativeSampleId=-1;
    bool checkingUpdates = false;''')
once('''      indicatorTimer.Tick+=(s,e)=>PulseIndicator();indicatorTimer.Start();''',
'''      indicatorTimer.Tick+=(s,e)=>PulseIndicator();indicatorTimer.Start();
      // PDH measurements are sampled off the UI thread. Failure is nonfatal
      // and automatically falls back to the existing direct adapter rates.
      liveCounterTimer=new System.Threading.Timer(SampleNativeCounters,null,350,1000);''')

anchor='    void ApplyUsage(Dictionary<string,object> d){'
native=r'''    // PerformanceCounter uses Windows Performance Monitor's per-interface
    // "Bytes Received/sec" and "Bytes Sent/sec" rates. Task Manager may
    // sample with a different interval; equality at every instant is not
    // guaranteed. Matching is by Windows adapter description, not SSID.
    static string CounterKey(string value){
      return new string((value??"").ToLowerInvariant().Where(Char.IsLetterOrDigit).ToArray());
    }
    string ResolveNativeInstance(string adapterName){
      NetworkInterface chosen=NetworkInterface.GetAllNetworkInterfaces()
        .FirstOrDefault(a=>String.Equals(a.Name,adapterName,StringComparison.OrdinalIgnoreCase));
      if(chosen==null)return null;
      var category=new PerformanceCounterCategory("Network Interface");
      var instances=category.GetInstanceNames();
      string name=CounterKey(chosen.Name);
      string description=CounterKey(chosen.Description);
      var matches=instances.Select(instance=>new{
        Instance=instance,
        Key=CounterKey(instance)
      }).Select(x=>new{
        x.Instance,
        Score=x.Key==description?100:
          x.Key==name?90:
          (description.Length>7 && (x.Key.Contains(description)||description.Contains(x.Key)))?80:
          (name.Length>7 && (x.Key.Contains(name)||name.Contains(x.Key)))?70:0
      }).Where(x=>x.Score>0).OrderByDescending(x=>x.Score).ToArray();
      // Don't guess if multiple physical network interfaces match equally.
      if(matches.Length==0 || (matches.Length>1 && matches[0].Score==matches[1].Score))return null;
      return matches[0].Instance;
    }
    void SampleNativeCounters(object ignored){
      if(closing)return;
      // Timer callbacks must never overlap when Windows performance counters
      // stall. Hold the short lock only around the counter state.
      if(!Monitor.TryEnter(liveCounterLock))return;
      try{
        if(!nativeCounterAvailable &&
           DateTime.UtcNow<nativeRetryUtc)return;
        if(!nativeCounterAvailable){
          DisposeNativeCounters();
          var adapterName="WiFi";
          try{
            // The user's Windows adapter is named WiFi; use that exact name
            // first. If different, select the active physical wireless device.
            var adapters=NetworkInterface.GetAllNetworkInterfaces();
            var preferred=adapters.FirstOrDefault(x=>x.NetworkInterfaceType==NetworkInterfaceType.Wireless80211
              && x.OperationalStatus==OperationalStatus.Up);
            if(preferred!=null)adapterName=preferred.Name;
          }catch{}
          string instance=ResolveNativeInstance(adapterName);
          if(String.IsNullOrEmpty(instance)){
            nativeRetryUtc=DateTime.UtcNow.AddSeconds(20);return;
          }
          nativeRxCounter=new PerformanceCounter("Network Interface","Bytes Received/sec",instance,true);
          nativeTxCounter=new PerformanceCounter("Network Interface","Bytes Sent/sec",instance,true);
          // The first NextValue() only primes a rate counter; never use it.
          nativeRxCounter.NextValue();nativeTxCounter.NextValue();
          nativeCounterInstance=instance;
          nativeCounterAdapter=adapterName;
          nativeCounterAvailable=true;
          nativeCounterErrors=0;
          lastNativeSampleUtc=DateTime.MinValue;
          return;
        }
        double rx=nativeRxCounter.NextValue();
        double tx=nativeTxCounter.NextValue();
        if(!PlausibleRate(rx) || !PlausibleRate(tx)){
          throw new InvalidOperationException("Implausible network performance counter rate");
        }
        nativeRxBytesPerSecond=rx;nativeTxBytesPerSecond=tx;
        lastNativeSampleUtc=DateTime.UtcNow;
        nativeSampleId++;
        nativeCounterErrors=0;
      }catch{
        nativeCounterErrors++;
        // Missing/disabled/localized performance counters are optional:
        // keep direct PowerShell rates and never interfere with usage.json.
        DisposeNativeCounters();
        nativeRetryUtc=DateTime.UtcNow.AddSeconds(20);
      }finally{Monitor.Exit(liveCounterLock);}
    }
    void DisposeNativeCounters(){
      nativeCounterAvailable=false;
      if(nativeRxCounter!=null){try{nativeRxCounter.Dispose();}catch{}nativeRxCounter=null;}
      if(nativeTxCounter!=null){try{nativeTxCounter.Dispose();}catch{}nativeTxCounter=null;}
    }
    bool TryNativeRates(string adapterName,out double rx,out double tx,
                        out DateTime time,out long id){
      rx=0;tx=0;time=DateTime.MinValue;id=-1;
      lock(liveCounterLock){
        if(!nativeCounterAvailable ||
           !String.Equals(nativeCounterAdapter,adapterName,StringComparison.OrdinalIgnoreCase) ||
           lastNativeSampleUtc==DateTime.MinValue ||
           (DateTime.UtcNow-lastNativeSampleUtc).TotalSeconds>2.5)return false;
        rx=nativeRxBytesPerSecond;tx=nativeTxBytesPerSecond;
        time=lastNativeSampleUtc;id=nativeSampleId;
        return true;
      }
    }
'''
once(anchor,native+anchor)

old='''        // Speeds originate only from the engine's latest adapter-counter
        // sampling interval, never from delayed daily-usage totals.
        DateTime nowUtc=DateTime.UtcNow;'''
new='''        // Both cards and graph use ONE source for this refresh:
        // Windows Network Interface performance counters when available,
        // otherwise the existing engine's direct adapter sample.
        DateTime nowUtc=DateTime.UtcNow;
        double rateRx=Num(d,"rateRxBps"),rateTx=Num(d,"rateTxBps");
        DateTime liveSampleUtc=sampleUtc;
        long liveSampleId=sampleId;
        bool useNative=false;
        DateTime nativeTime; long nativeId;
        double nativeRx,nativeTx;
        if(stat=="tracking" && TryNativeRates(Str(d,"adapterName"),
                          out nativeRx,out nativeTx,out nativeTime,out nativeId)){
          useNative=true;
          rateRx=nativeRx;rateTx=nativeTx;
          liveSampleUtc=nativeTime;liveSampleId=nativeId;
        }
        bool liveFresh=useNative || fresh;
        bool liveValid=useNative || valid;
        if(useNative){
          // Preserve the engine's sampling-age indicator: it refers to
          // measurement freshness for cumulative usage collection.
          downloadSpeed.Text=Rate(rateRx);
          uploadSpeed.Text=Rate(rateTx);
          downloadSpeed.Tag="Windows Network Interface counters";
          uploadSpeed.Tag=downloadSpeed.Tag;
        }else{
          downloadSpeed.Tag="T-Net adapter counters (fallback)";
          uploadSpeed.Tag=downloadSpeed.Tag;
        }'''
once(old,new)
once('''          } else if(valid && fresh){
            // Fresh interval: a measured zero is a real zero.
            downloadSpeed.Text=Rate(Num(d,"rateRxBps"));
            uploadSpeed.Text=Rate(Num(d,"rateTxBps"));''',
'''          } else if(liveValid && liveFresh){
            // A fresh measured zero is a real zero.
            downloadSpeed.Text=Rate(rateRx);
            uploadSpeed.Text=Rate(rateTx);''')
once('''        CaptureLiveSpeedSample(stat,sampleId,sampleUtc,timestampValid,fresh,valid,
                               Num(d,"rateRxBps"),Num(d,"rateTxBps"));''',
'''        CaptureLiveSpeedSample(stat,liveSampleId,liveSampleUtc,
                               useNative || timestampValid,liveFresh,liveValid,
                               rateRx,rateTx);''')

once('''    void Quit(){closing=true;refreshTimer.Stop();if(indicatorTimer!=null)indicatorTimer.Stop();''',
'''    void Quit(){closing=true;refreshTimer.Stop();if(indicatorTimer!=null)indicatorTimer.Stop();
      if(liveCounterTimer!=null){liveCounterTimer.Dispose();liveCounterTimer=null;}
      lock(liveCounterLock){DisposeNativeCounters();}
'''.rstrip('\n'))

assert 'Get-NetAdapterStatistics' not in s
assert s.count('CaptureLiveSpeedSample(stat,liveSampleId')==1
assert 'wifi.Text=HotspotLabel(currentSsid);' in s
assert 'const string AppVersion = "6.7.0";' in s
p.write_text(s,encoding="utf-8")
print('T-Net v6.7 native Windows network counter live speeds; cumulative engine unchanged.')
