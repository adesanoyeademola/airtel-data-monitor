from pathlib import Path
f=Path('work/AirtelMonitorNative.cs')
s=f.read_text(encoding='utf-8')
old='const string AppVersion = "5.5.0";'
if s.count(old)!=1: raise RuntimeError('Unexpected installed app version')
s=s.replace(old,'const string AppVersion = "5.6.0";')
if s.count('Airtel Data Monitor')<3: raise RuntimeError('Expected UI text not found')
s=s.replace('Airtel Data Monitor','T-Net')
needle='Shown+=(s,e)=>StartEngine();'
if s.count(needle)!=1: raise RuntimeError('Startup event not found')
s=s.replace(needle,'Shown+=(s,e)=>{RenameShortcuts();StartEngine();};')
marker='    void ShowWindow(){'
if s.count(marker)!=1: raise RuntimeError('Window method not found')
method='''    void RenameShortcuts(){
      // Rename shortcut labels only; leave installed executable, release feed,
      // settings and usage records at their original paths.
      try {
        string[] folders={Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                          Environment.GetFolderPath(Environment.SpecialFolder.Programs)};
        foreach(string folder in folders){
          if(String.IsNullOrWhiteSpace(folder)) continue;
          foreach(string item in new[]{""," - iPhone View"}){
            string oldName=Path.Combine(folder,"Airtel Data Monitor"+item+".lnk");
            string newName=Path.Combine(folder,"T-Net"+item+".lnk");
            if(File.Exists(oldName) && !File.Exists(newName))File.Move(oldName,newName);
          }
        }
      } catch { /* Shortcut update is optional; never prevent monitoring startup. */ }
    }
'''
s=s.replace(marker,method+marker)
assert 'Text="T-Net"' in s and 'Text = "T-Net"' in s
f.write_text(s,encoding='utf-8')
print('T-Net branding applied without moving usage history')
