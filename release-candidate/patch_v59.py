from pathlib import Path
f=Path("work/AirtelMonitorNative.cs")
s=f.read_text(encoding="utf-8")
def replace_one(before,after):
    global s
    n=s.count(before)
    if n!=1:
        raise RuntimeError(f"Expected one occurrence, found {n}: {before[:100]!r}")
    s=s.replace(before,after)
replace_one('const string AppVersion = "5.8.0";','const string AppVersion = "5.9.0";')
replace_one('using System.Management;\n','')
start=s.index('    bool StopPriorMonitoringProcesses(){')
end=s.index('    void RestartEngine(){',start)
original=s[start:end]
replacement=r'''    bool StopPriorMonitoringProcesses(){
      // The already-installed updater compiles without a System.Management.dll
      // reference. Load WMI via reflection at runtime, not as a compile dependency.
      string scriptPath=Path.GetFullPath(Path.Combine(root,"monitor.ps1"));
      bool ok=true;
      try {
        var library=System.Reflection.Assembly.Load("System.Management");
        Type queryType=library.GetType("System.Management.ManagementObjectSearcher",true);
        object query=Activator.CreateInstance(queryType,new object[]{
          "SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name = 'powershell.exe' OR Name = 'pwsh.exe'"
        });
        try {
          object results=queryType.GetMethod("Get",Type.EmptyTypes).Invoke(query,null);
          try {
            foreach(object item in (System.Collections.IEnumerable)results){
              try {
                var indexer=item.GetType().GetProperty("Item",new Type[]{typeof(string)});
                if(indexer==null){ok=false;continue;}
                string command=Convert.ToString(indexer.GetValue(item,new object[]{"CommandLine"}))??"";
                if(command.IndexOf("-File",StringComparison.OrdinalIgnoreCase)<0 ||
                   command.IndexOf(scriptPath,StringComparison.OrdinalIgnoreCase)<0)continue;
                int pid=Convert.ToInt32(indexer.GetValue(item,new object[]{"ProcessId"}));
                try {
                  using(var previous=Process.GetProcessById(pid)){
                    if(previous.SessionId!=Process.GetCurrentProcess().SessionId)continue;
                    if(engine!=null && pid==engine.Id)continue;
                    previous.Kill();
                    if(!previous.WaitForExit(2500))ok=false;
                  }
                }catch(ArgumentException){/* already stopped */}
                catch(Exception ex){
                  ok=false;
                  Debug.WriteLine("Could not stop old T-Net monitor: "+ex.Message);
                }
              }finally{
                var disposable=item as IDisposable;
                if(disposable!=null)disposable.Dispose();
              }
            }
          }finally{
            var disposable=results as IDisposable;
            if(disposable!=null)disposable.Dispose();
          }
        }finally{
          var disposable=query as IDisposable;
          if(disposable!=null)disposable.Dispose();
        }
      }catch(Exception ex){
        ok=false;
        Debug.WriteLine("T-Net monitor inspection unavailable: "+ex.Message);
      }
      return ok;
    }
'''
assert original.count('ManagementObjectSearcher')==1
s=s[:start]+replacement+s[end:]
assert 'using System.Management;' not in s
assert 'foreach(ManagementObject ' not in s
assert 'new ManagementObjectSearcher(' not in s
assert 'const string AppVersion = "5.9.0";' in s
f.write_text(s,encoding="utf-8")
print("T-Net v5.9: removed compile-time System.Management dependency; WMI inspection retained through reflection.")
