using System;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Security.Cryptography;
using System.Diagnostics;
using System.Linq;
using System.Windows.Forms;
using System.Collections.Generic;

namespace TNetRepair {
  static class Program {
    const string PackageUrl="https://raw.githubusercontent.com/adesanoyeademola/airtel-data-monitor/main/releases/TNetUI-6.31.1-payload.zip";
    const string ExpectedSha256="__PAYLOAD_SHA256__";
    static readonly string[] Files={
      "AirtelDataMonitor.exe",
      "approved-ui-live.html",
      "Microsoft.Web.WebView2.Core.dll",
      "Microsoft.Web.WebView2.WinForms.dll",
      "WebView2Loader.dll"
    };
    static string Root {
      get {return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"AirtelDataMonitor");}
    }
    [STAThread]
    static int Main(string[] args) {
      Application.EnableVisualStyles();
      Application.SetCompatibleTextRenderingDefault(false);
      bool test=args.Length==2 && args[0]=="--selftest";
      try {
        if(test)return SelfTest(args[1]);
        string root=Root;
        if(!File.Exists(Path.Combine(root,"AirtelDataMonitor.exe")) ||
           !File.Exists(Path.Combine(root,"monitor.ps1")))
          throw new Exception("T-Net installation not found in AppData. No files changed.");
        if(Running(root))throw new Exception("Please close T-Net completely, including its tray icon, then run this repair again.");
        if(MessageBox.Show("Repair T-Net 6.31.1 using the existing AppData installation?\n\nOnly the application and interface files will be replaced. Monitoring history, settings, and monitor.ps1 stay untouched. A backup is created first.","T-Net — one-time repair",MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)return 0;
        ServicePointManager.SecurityProtocol=SecurityProtocolType.Tls12;
        byte[] zip;
        using(var wc=new WebClient()){
          wc.Headers[HttpRequestHeader.UserAgent]="T-Net-OneClick-Repair/6.31.1";
          zip=wc.DownloadData(PackageUrl);
        }
        if(Checksum(zip)!=ExpectedSha256)throw new Exception("Download checksum mismatch. No files changed.");
        Install(root,zip,false);
        MessageBox.Show("T-Net 6.31.1 repaired successfully. Future interface updates use the in-app Check for updates button. Your data and settings were preserved.","T-Net repaired",MessageBoxButtons.OK,MessageBoxIcon.Information);
        Process.Start(new ProcessStartInfo(Path.Combine(root,"AirtelDataMonitor.exe")){WorkingDirectory=root,UseShellExecute=true});
        return 0;
      } catch(Exception ex) {
        if(!test)MessageBox.Show(ex.Message,"T-Net repair could not finish",MessageBoxButtons.OK,MessageBoxIcon.Error);
        else Console.Error.WriteLine(ex.ToString());
        return 1;
      }
    }
    static bool Running(string root) {
      foreach(var proc in Process.GetProcessesByName("AirtelDataMonitor")){
        try{
          string path=proc.MainModule.FileName;
          if(String.Equals(Path.GetFullPath(path),Path.GetFullPath(Path.Combine(root,"AirtelDataMonitor.exe")),StringComparison.OrdinalIgnoreCase))return true;
        }catch{}finally{proc.Dispose();}
      }
      return false;
    }
    static string Checksum(byte[] data) {
      using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(data)).Replace("-","").ToLowerInvariant();
    }
    static void Install(string root,byte[] payload,bool selftest){
      if(!Directory.Exists(root))throw new Exception("Installation folder missing.");
      if(!File.Exists(Path.Combine(root,"monitor.ps1")))throw new Exception("Monitoring service missing. No files changed.");
      string stage=Path.Combine(Path.GetTempPath(),"tnet-6311-"+Guid.NewGuid().ToString("N"));
      string backup=Path.Combine(root,"update-backups","repair-6311-"+DateTime.UtcNow.ToString("yyyyMMddHHmmss")+"-"+Guid.NewGuid().ToString("N").Substring(0,6));
      var touched=new List<string>(); var existed=new Dictionary<string,bool>();
      Directory.CreateDirectory(stage);
      try{
        using(var stream=new MemoryStream(payload))
        using(var zip=new ZipArchive(stream,ZipArchiveMode.Read)){
          foreach(string name in Files){
            var entry=zip.GetEntry(name);
            if(entry==null || entry.Length<=0 || entry.Length>8*1024*1024)throw new Exception("Invalid payload: "+name);
            string output=Path.Combine(stage,name);
            using(var input=entry.Open())using(var target=File.Create(output))input.CopyTo(target);
          }
        }
        string ui=File.ReadAllText(Path.Combine(stage,"approved-ui-live.html"),System.Text.Encoding.UTF8);
        if(!ui.Contains("window.TNetBridgeUpdate")||!ui.Contains("appearance-switch")||!ui.Contains("function showPage(name)")||ui.Contains("class=\"version\""))
          throw new Exception("UI payload failed compatibility checks.");
        // All files are validated before any installed file is modified.
        Directory.CreateDirectory(backup);
        foreach(string name in Files){
          string target=Path.Combine(root,name);
          bool was=File.Exists(target);
          existed[name]=was;
          if(was)File.Copy(target,Path.Combine(backup,name),false);
        }
        try{
          foreach(string name in Files){
            string target=Path.Combine(root,name);
            File.Copy(Path.Combine(stage,name),target,true);
            touched.Add(name);
          }
        }catch(Exception ex){
          var failures=new List<string>();
          foreach(string name in touched.AsEnumerable().Reverse()){
            try{
              string target=Path.Combine(root,name);
              if(existed[name])File.Copy(Path.Combine(backup,name),target,true);
              else if(File.Exists(target))File.Delete(target);
            }catch(Exception rollback){failures.Add(name+": "+rollback.Message);}
          }
          if(failures.Count>0)throw new Exception("Repair failed; rollback incomplete. Backups at "+backup+"; "+String.Join("; ",failures),ex);
          throw new Exception("Repair failed. Previous application files restored from "+backup,ex);
        }
        // AppData data, monitor.ps1, appearance.txt, updates.txt, tray and preferences are untouched.
      }finally{
        try{Directory.Delete(stage,true);}catch{}
      }
    }
    static int SelfTest(string path) {
      if(!File.Exists(path))throw new Exception("Test package missing.");
      byte[] zip=File.ReadAllBytes(path);
      if(Checksum(zip)!=ExpectedSha256)throw new Exception("Self-test payload checksum mismatch.");
      string root=Path.Combine(Path.GetTempPath(),"tnet-test-"+Guid.NewGuid().ToString("N"));
      Directory.CreateDirectory(root);
      try{
        File.WriteAllText(Path.Combine(root,"monitor.ps1"),"ORIGINAL ENGINE");
        Directory.CreateDirectory(Path.Combine(root,"data"));
        File.WriteAllText(Path.Combine(root,"data","usage-timeline.csv"),"ORIGINAL HISTORY");
        File.WriteAllText(Path.Combine(root,"appearance.txt"),"dark");
        File.WriteAllText(Path.Combine(root,"AirtelDataMonitor.exe"),"OLD APP");
        Install(root,zip,true);
        if(File.ReadAllText(Path.Combine(root,"monitor.ps1"))!="ORIGINAL ENGINE" ||
           File.ReadAllText(Path.Combine(root,"data","usage-timeline.csv"))!="ORIGINAL HISTORY" ||
           File.ReadAllText(Path.Combine(root,"appearance.txt"))!="dark")
          throw new Exception("Protected files changed.");
        if(File.ReadAllText(Path.Combine(root,"AirtelDataMonitor.exe"))=="OLD APP")throw new Exception("EXE not replaced.");
        if(!Directory.Exists(Path.Combine(root,"update-backups")))throw new Exception("Backup missing.");
        Console.WriteLine("PASS one-click installer isolated data preservation and backup.");
        return 0;
      }finally{try{Directory.Delete(root,true);}catch{}}
    }
  }
}
