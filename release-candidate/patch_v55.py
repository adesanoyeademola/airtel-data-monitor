from pathlib import Path
f=Path('work/AirtelMonitorNative.cs')
s=f.read_text(encoding='utf-8')
def swap(a,b):
 global s
 if s.count(a)!=1: raise RuntimeError('Expected one match: '+repr(a[:85])+' found '+str(s.count(a)))
 s=s.replace(a,b)
swap('const string AppVersion = "5.4.0";','const string AppVersion = "5.5.0";')
swap('''    string Rate(double bytesPerSecond){
      if(bytesPerSecond<0 || Double.IsNaN(bytesPerSecond) || Double.IsInfinity(bytesPerSecond))return "— KB/s";
      if(bytesPerSecond>=1048576)return (bytesPerSecond/1048576).ToString("0.0",CultureInfo.InvariantCulture)+" MB/s";
      return (bytesPerSecond/1024).ToString("0.0",CultureInfo.InvariantCulture)+" KB/s";
    }''','''    // Use decimal bits/sec, as Task Manager reports (1 Kbps = 1000 bits/sec).
    string Rate(double bytesPerSecond){
      if(bytesPerSecond<0 || Double.IsNaN(bytesPerSecond) || Double.IsInfinity(bytesPerSecond))return "— Kbps";
      double bitsPerSecond=bytesPerSecond*8.0;
      if(bitsPerSecond>=1000000)return (bitsPerSecond/1000000).ToString("0.0",CultureInfo.InvariantCulture)+" Mbps";
      return (bitsPerSecond/1000).ToString("0.0",CultureInfo.InvariantCulture)+" Kbps";
    }''')
swap('var value=new Label{Text="— KB/s",Dock=DockStyle.Fill','var value=new Label{Text="— Kbps",Dock=DockStyle.Fill')
# Old service has no rateSampleTime field. Don't misrepresent this as a valid zero speed.
swap('''        bool fresh = timestampValid && Math.Abs((DateTime.UtcNow - sampleUtc.ToUniversalTime()).TotalSeconds) <= 3;''','''        bool fresh = timestampValid && Math.Abs((DateTime.UtcNow - sampleUtc.ToUniversalTime()).TotalSeconds) <= 3;
        bool legacyService = stat=="tracking" && !timestampValid;''')
swap('''        if(stat!="tracking"){
          downloadSpeed.Text="— KB/s";uploadSpeed.Text="— KB/s";''','''        if(stat!="tracking"){
          downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";''')
swap('''        } else {
          if(valid && fresh){''','''        } else {
          if(legacyService){
            downloadSpeed.Text="Restart service";
            uploadSpeed.Text="Restart service";
            status.Text="●  Old monitoring service";
            status.ForeColor=Color.FromArgb(255,185,100);
          } else if(valid && fresh){''')
swap('''downloadSpeed.Text="— KB/s";uploadSpeed.Text="— KB/s";}''','''downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";}''')
f.write_text(s,encoding='utf-8')
print('Prepared v5.5 Kbps/Mbps display and legacy engine warning')
