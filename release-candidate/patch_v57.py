from pathlib import Path
p=Path('work/AirtelMonitorNative.cs')
s=p.read_text(encoding='utf-8')
def replace_one(a,b):
    global s
    n=s.count(a)
    if n!=1: raise RuntimeError(f'Expected one occurrence, found {n}: {a[:95]!r}')
    s=s.replace(a,b)
replace_one('using System.IO.Compression;','using System.IO.Compression;\nusing System.Management;')
replace_one('const string AppVersion = "5.6.0";','const string AppVersion = "5.7.0";')
replace_one(
  'menu.Items.Add("Open monitor", null, (s,e)=>ShowWindow()); menu.Items.Add("Exit monitor", null, (s,e)=>Quit());',
  'menu.Items.Add("Open monitor", null, (s,e)=>ShowWindow()); menu.Items.Add("Restart monitoring service", null, (s,e)=>RestartEngine()); menu.Items.Add("Exit monitor", null, (s,e)=>Quit());'
)
replace_one('      BuildUi();\n      tray = new NotifyIcon();',
'''      BuildUi();
      // The explicit "Restart service" warning is also an action users can click.
      downloadSpeed.Cursor=Cursors.Hand;uploadSpeed.Cursor=Cursors.Hand;
      downloadSpeed.Click+=(sender,e)=>{if(downloadSpeed.Text=="Restart service")RestartEngine();};
      uploadSpeed.Click+=(sender,e)=>{if(uploadSpeed.Text=="Restart service")RestartEngine();};
      tray = new NotifyIcon();''')
replace_one('    void StartEngine(){',
'''    // Windows can leave a previous monitoring PowerShell running after an update.
    // Stop only processes running this exact monitor.ps1 script, never every
    // PowerShell process. This avoids port 8787 collisions and stale speed data.
    bool StopPriorMonitoringProcesses(){
      string scriptPath=Path.GetFullPath(Path.Combine(root,"monitor.ps1"));
      bool ok=true;
      try {
        using(var query=new ManagementObjectSearcher("SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name = 'powershell.exe' OR Name = 'pwsh.exe'")){
          foreach(ManagementObject item in query.Get()){
            string command=Convert.ToString(item["CommandLine"])??"";
            if(command.IndexOf("-File",StringComparison.OrdinalIgnoreCase)<0 ||
               command.IndexOf(scriptPath,StringComparison.OrdinalIgnoreCase)<0)continue;
            int pid=Convert.ToInt32(item["ProcessId"]);
            try {
              using(var previous=Process.GetProcessById(pid)){
                if(previous.SessionId!=Process.GetCurrentProcess().SessionId)continue;
                if(engine!=null && pid==engine.Id)continue;
                previous.Kill();
                if(!previous.WaitForExit(2500))ok=false;
              }
            }catch(ArgumentException){/* already stopped */}
            catch(Exception ex){ok=false;Debug.WriteLine("Could not stop old T-Net engine: "+ex.Message);}
          }
        }
      }catch(Exception ex){ok=false;Debug.WriteLine("T-Net service inspection unavailable: "+ex.Message);}
      return ok;
    }
    void RestartEngine(){
      try{if(engine!=null&&!engine.HasExited){engine.Kill();engine.WaitForExit(2500);}}catch{}
      engine=null;
      StartEngine();
    }
    void StartEngine(){
      if(!StopPriorMonitoringProcesses()){
        status.Text="● Service restart blocked";
        status.ForeColor=Color.FromArgb(255,185,100);
        MessageBox.Show("A previous T-Net monitoring process could not be closed safely. Exit T-Net from the system tray, then restart Windows to clear the old service. Your saved usage history will remain.","T-Net service",MessageBoxButtons.OK,MessageBoxIcon.Warning);
        return;
      }''')
p.write_text(s,encoding='utf-8')
assert 'const string AppVersion = "5.7.0"' in s
assert 'StopPriorMonitoringProcesses' in s
assert 'Restart monitoring service' in s
print('T-Net v5.7 source patched for safe legacy engine cleanup and restart')
