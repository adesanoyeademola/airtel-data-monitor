from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8")
def one(before,after):
    global s
    count=s.count(before)
    if count != 1: raise AssertionError(f"Expected one match; found {count}: {before[:110]!r}")
    s=s.replace(before,after)

one('const string AppVersion = "5.9.0";','const string AppVersion = "6.0.0";')
one('DateTime engineLaunchUtc=DateTime.MinValue;',
    'DateTime engineLaunchUtc=DateTime.MinValue;\n    DateTime lastEngineAttemptUtc=DateTime.MinValue;')

# Don't terminate a healthy monitor, including one started manually, at app startup.
# The old WMI process inspection could fail and prevent an engine starting at all.
one('''    void StartEngine(){
      if(!StopPriorMonitoringProcesses()){
        SetIndicator("Service restart blocked",1);
        MessageBox.Show("A previous T-Net monitoring process could not be closed safely. Exit T-Net from the system tray, then restart Windows to clear the old service. Your saved usage history will remain.","T-Net service",MessageBoxButtons.OK,MessageBoxIcon.Warning);
        return;
      }
      string ps=Path.Combine(root,"monitor.ps1");''',
'''    bool ServiceResponding(){
      try {
        var req=(HttpWebRequest)WebRequest.Create(Base+"/api/summary");
        req.Timeout=900;req.ReadWriteTimeout=900;req.KeepAlive=false;
        using(var response=(HttpWebResponse)req.GetResponse())
        using(var reader=new StreamReader(response.GetResponseStream())){
          string payload=reader.ReadToEnd();
          return response.StatusCode==HttpStatusCode.OK && payload.Contains("\\"todayTotal\\"");
        }
      }catch{return false;}
    }
    void StartEngine(){
      if(closing)return;
      if(ServiceResponding()){return;} // Attach to the healthy service without disruption.
      if((DateTime.UtcNow-lastEngineAttemptUtc).TotalSeconds<10)return;
      lastEngineAttemptUtc=DateTime.UtcNow;
      try {
        if(engine!=null && !engine.HasExited)return; // A new engine is still starting.
      }catch{}
      string ps=Path.Combine(root,"monitor.ps1");''')

one('''    void RestartEngine(){
      try{if(engine!=null&&!engine.HasExited){engine.Kill();engine.WaitForExit(2500);}}catch{}
      engine=null;
      StartEngine();
    }''',
'''    void RestartEngine(){
      // An explicit restart may stop an old instance using this exact script.
      try{if(engine!=null&&!engine.HasExited){engine.Kill();engine.WaitForExit(2500);}}catch{}
      engine=null;
      if(!StopPriorMonitoringProcesses()){
        if(ServiceResponding()){
          SetIndicator("Monitoring live",0); // Do not interrupt a service we cannot own.
          return;
        }
      }
      lastEngineAttemptUtc=DateTime.MinValue;
      StartEngine();
    }''')

one('''    void RefreshUsage(){''',
'''    void AutoRecoverEngine(){
      if(closing)return;
      // Recover only after startup has been given time and no new attempt is underway.
      if((DateTime.UtcNow-engineLaunchUtc).TotalSeconds<10)return;
      if((DateTime.UtcNow-lastEngineAttemptUtc).TotalSeconds<15)return;
      try {
        // If the child never established its API, stop only the child we created.
        if(engine!=null&&!engine.HasExited){
          engine.Kill();
          engine.WaitForExit(1200);
        }
      }catch{}
      engine=null;
      StartEngine();
    }
    void RefreshUsage(){''')

one('''        downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
      }
    }
    void SaveSettings(){''',
'''        downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
        AutoRecoverEngine();
      }
    }
    void SaveSettings(){''')

assert 'StopPriorMonitoringProcesses()){\\n        SetIndicator("Service restart blocked"' not in s
assert 'DateTime lastEngineAttemptUtc' in s
assert 'AutoRecoverEngine();' in s
assert 'ServiceResponding()' in s
p.write_text(s,encoding="utf-8")
print("T-Net 6.0: attach to healthy monitor, remove WMI startup gate, auto-recover failed child.")
