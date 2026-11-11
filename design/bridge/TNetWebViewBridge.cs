using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Linq;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace AirtelMonitorNative {
  // Presentation-only shell. The original monitor, history, counters,
  // adapter selection, auto-updater and tray handling remain in MainForm.
  public partial class MainForm {
    WebView2 approvedDashboard;
    bool approvedDashboardReady = false;
    Dictionary<string,object> lastApprovedSample;
    DateTime lastHistorySentUtc=DateTime.MinValue;
    DateTime lastLogSentUtc=DateTime.MinValue;

    async void StartApprovedWebView() {
      string path=Path.Combine(root,"approved-ui-live.html");
      if(!File.Exists(path))return; // Native dashboard remains available.
      try {
        approvedDashboard=new WebView2{Dock=DockStyle.Fill,
          DefaultBackgroundColor=System.Drawing.Color.FromArgb(9,23,44)};
        approvedDashboard.Visible=false;
        Controls.Add(approvedDashboard);
        approvedDashboard.BringToFront();
        // A missing WebView2 Runtime triggers the native fallback.
        // Store WebView2 browser data in the user's writable profile.
        string profile=Path.Combine(Environment.GetFolderPath(
          Environment.SpecialFolder.LocalApplicationData),"T-Net","WebView2");
        Directory.CreateDirectory(profile);
        var environment=await CoreWebView2Environment.CreateAsync(null,profile);
        await approvedDashboard.EnsureCoreWebView2Async(environment);
        approvedDashboard.CoreWebView2.Settings.AreDevToolsEnabled=false;
        approvedDashboard.CoreWebView2.Settings.AreDefaultContextMenusEnabled=false;
        approvedDashboard.CoreWebView2.Settings.IsStatusBarEnabled=false;
        approvedDashboard.CoreWebView2.WebMessageReceived+=ApprovedMessage;
        approvedDashboard.NavigationCompleted+=async (sender,args)=>{
          if(!args.IsSuccess)return;
          approvedDashboardReady=true;
          approvedDashboard.Visible=true;
          approvedDashboard.BringToFront();
          PostApprovedTheme();
          if(lastApprovedSample!=null)PushApprovedTelemetry(lastApprovedSample,true);
          // Build-only review hook; disabled in normal installations.
          string screenshot=Environment.GetEnvironmentVariable("TNET_DESIGN_CAPTURE_PATH");
          if(!String.IsNullOrWhiteSpace(screenshot)){
            try{
              await System.Threading.Tasks.Task.Delay(1000);
              Directory.CreateDirectory(Path.GetDirectoryName(screenshot));
              using(var output=File.Create(screenshot)){
                await approvedDashboard.CoreWebView2.CapturePreviewAsync(
                  CoreWebView2CapturePreviewImageFormat.Png,output);
              }
              // Capture every page in the same actual embedded Windows UI.
              // No simulated network measurements are inserted.
              string folder=Path.GetDirectoryName(screenshot);
              foreach(string page in new[]{"Usage","Network","History","Settings","Dashboard"}){
                string escaped=json.Serialize(page);
                await approvedDashboard.CoreWebView2.ExecuteScriptAsync(
                  "window.TNetShowPage("+escaped+");");
                await System.Threading.Tasks.Task.Delay(250);
                string pagePath=Path.Combine(folder,"approved-page-"+page.ToLowerInvariant()+".png");
                using(var output=File.Create(pagePath)){
                  await approvedDashboard.CoreWebView2.CapturePreviewAsync(
                    CoreWebView2CapturePreviewImageFormat.Png,output);
                }
              }
            }catch(Exception ex){
              System.Diagnostics.Debug.WriteLine("Design QA screenshot failed: "+ex.Message);
            }
          }
        };
        approvedDashboard.Source=new Uri(path);
      }catch(Exception ex){
        approvedDashboardReady=false;
        if(approvedDashboard!=null){
          Controls.Remove(approvedDashboard);
          approvedDashboard.Dispose();
          approvedDashboard=null;
        }
        // Continue running the existing native dashboard and monitoring.
        System.Diagnostics.Debug.WriteLine("Modern UI unavailable: "+ex.Message);
      }
    }
    async void ApprovedMessage(object sender,CoreWebView2WebMessageReceivedEventArgs e){
      try {
        // Only the app's own local HTML is used. Enforce a small allowlist.
        string message=e.TryGetWebMessageAsString();
        if(String.IsNullOrWhiteSpace(message)||message.Length>1500)return;
        var request=json.Deserialize<Dictionary<string,object>>(message);
        string action=Str(request,"action"),value=Str(request,"value");
        switch(action){
          case "ready":
            PostApprovedTheme();
            if(lastApprovedSample!=null)PushApprovedTelemetry(lastApprovedSample,true);
            break;
          case "checkUpdates":
            // Update the WebView2 HTML in place; do not invoke legacy native updater for UI assets.
            if(!await TryUpdateWebUiAsync(false))await CheckUpdates(false);
            break;
          case "appearance":
            if(value=="light"||value=="dark"||value=="system")
              SelectAppearance(value);
            break;
          case "usagePeriod":
            SetGraphView(value=="weekly"?3:value=="monthly"?4:0);
            break;
          case "chartMode":
            if(value=="speed")SetGraphView(1);
            else if(value=="log")SetGraphView(2);
            else SetGraphView(currentUsageView);
            break;
          case "navigate":
            // Sidebar pages are owned by the approved WebView2 presentation.
            // Do not open native dialogs or switch hidden native chart modes.
            // The original monitor continues collecting in every section.
            break;
        }
      }catch(Exception ex){
        System.Diagnostics.Debug.WriteLine("UI command ignored: "+ex.Message);
      }
    }
    // UI-only updates are downloaded and verified by the running application.
    // No PowerShell, installer, file selection, monitoring engine changes or restart.
    async Task<bool> TryUpdateWebUiAsync(bool silent){
      const string manifestUrl="https://raw.githubusercontent.com/adesanoyeademola/airtel-data-monitor/main/updates/ui.json";
      string target=Path.Combine(root,"approved-ui-live.html");
      if(!File.Exists(target))return false;
      string temp=null;
      try{
        ServicePointManager.SecurityProtocol=SecurityProtocolType.Tls12;
        string payload=await Task.Run(()=>{
          using(var wc=new WebClient()){
            wc.Headers[HttpRequestHeader.UserAgent]="T-Net/6.31";
            return wc.DownloadString(manifestUrl);
          }
        });
        var manifest=json.Deserialize<Dictionary<string,object>>(payload);
        if(manifest==null)return false;
        string url=Str(manifest,"uiUrl");
        string expected=Str(manifest,"uiSha256").ToLowerInvariant();
        if(!url.StartsWith("https://raw.githubusercontent.com/adesanoyeademola/airtel-data-monitor/",StringComparison.Ordinal)
           || !System.Text.RegularExpressions.Regex.IsMatch(expected,"^[0-9a-f]{64}$"))
          throw new Exception("UI release manifest did not pass security checks.");
        byte[] existing=File.ReadAllBytes(target);
        string currentHash;
        using(var hash=SHA256.Create())currentHash=BitConverter.ToString(hash.ComputeHash(existing)).Replace("-","").ToLowerInvariant();
        if(currentHash==expected)return false; // UI already current; check full updates instead.
        if(!silent && MessageBox.Show("A T-Net interface improvement is available. Apply it now? Your monitoring data and settings will remain unchanged.",
             "T-Net UI update",MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)return true;
        byte[] downloaded=await Task.Run(()=>{
          using(var wc=new WebClient()){
            wc.Headers[HttpRequestHeader.UserAgent]="T-Net/6.31";
            return wc.DownloadData(url);
          }
        });
        if(downloaded.Length<5000||downloaded.Length>4*1024*1024)throw new Exception("Unexpected UI update size.");
        string actual;
        using(var hash=SHA256.Create())actual=BitConverter.ToString(hash.ComputeHash(downloaded)).Replace("-","").ToLowerInvariant();
        if(actual!=expected)throw new Exception("UI update checksum mismatch; nothing changed.");
        string html=new UTF8Encoding(false,true).GetString(downloaded);
        foreach(string required in new[]{"window.TNetBridgeUpdate","function showPage(name)","appearance-switch","id=\"live-down\"","id=\"live-signal\""})
          if(!html.Contains(required))throw new Exception("UI update failed compatibility validation: "+required);
        temp=Path.Combine(root,".tnet-ui-"+Guid.NewGuid().ToString("N")+".tmp");
        File.WriteAllBytes(temp,downloaded);
        string backup=Path.Combine(root,"approved-ui-live.backup-"+DateTime.UtcNow.ToString("yyyyMMddHHmmss")+".html");
        File.Replace(temp,target,backup,false);
        temp=null;
        if(approvedDashboard!=null && !approvedDashboard.IsDisposed && approvedDashboard.CoreWebView2!=null){
          approvedDashboardReady=false;
          approvedDashboard.CoreWebView2.Reload();
        }
        if(!silent)MessageBox.Show("T-Net interface updated. Monitoring history and counters were not changed.","Update complete");
        return true;
      }catch(WebException){
        // The optional UI feed may not yet be published. Keep checking existing release feed.
        return false;
      }catch(Exception ex){
        if(!silent)MessageBox.Show("The UI update was not installed: "+ex.Message,"T-Net update");
        return true; // Stop: do not accidentally start a second updater after a failed UI update.
      }finally{
        if(temp!=null)try{File.Delete(temp);}catch{}
      }
    }
    void PostApprovedTheme(){
      if(!approvedDashboardReady||approvedDashboard==null||
         approvedDashboard.CoreWebView2==null)return;
      PostApproved(new Dictionary<string,object>{{"theme",appearanceMode}});
    }
    void PostApproved(Dictionary<string,object> payload){
      if(!approvedDashboardReady||approvedDashboard==null||
         approvedDashboard.IsDisposed||approvedDashboard.CoreWebView2==null)return;
      try{approvedDashboard.CoreWebView2.PostWebMessageAsJson(json.Serialize(payload));}
      catch(Exception ex){System.Diagnostics.Debug.WriteLine(ex.Message);}
    }
    void PushApprovedTelemetry(Dictionary<string,object> d,bool forceHistory=false){
      if(d==null)return;
      lastApprovedSample=d;
      if(!approvedDashboardReady)return;
      var payload=new Dictionary<string,object>{
        {"downloadSpeed",downloadSpeed==null?"—":downloadSpeed.Text},
        {"uploadSpeed",uploadSpeed==null?"—":uploadSpeed.Text},
        {"signalPercent",dashboardSignalPercent.HasValue?
            (object)dashboardSignalPercent.Value:null},
        {"ssid",wifi==null?"—":wifi.Text},
        {"adapter",adapter==null?"—":adapter.Text},
        {"status",status==null?"Starting monitor":status.Text},
        {"sampleAge",sampleAgeLabel==null?"Last sample: waiting":sampleAgeLabel.Text},
        {"timestamp",last==null?"Waiting for a sample":last.Text},
        {"todayTotal",latestTodayConsumed},
        {"sevenDayTotal",latestSevenDayConsumed},
        {"monthTotal",latestMonthConsumed},
        {"theme",appearanceMode}
      };
      if(forceHistory || (DateTime.UtcNow-lastHistorySentUtc).TotalSeconds>=5){
        var records=new List<Dictionary<string,object>>();
        var days=d.ContainsKey("days")?d["days"] as ArrayList:null;
        if(days!=null)foreach(var obj in days){
          var row=obj as Dictionary<string,object>;
          if(row==null)continue;
          records.Add(new Dictionary<string,object>{
            {"date",Str(row,"date")},{"total",Num(row,"total")}
          });
        }
        payload["days"]=records;
        lastHistorySentUtc=DateTime.UtcNow;
      }
      if(forceHistory || (DateTime.UtcNow-lastLogSentUtc).TotalSeconds>=15){
        var logRows=new List<Dictionary<string,object>>();
        try{
          if(File.Exists(usageLogPath)){
            var recent=new Queue<string>();
            foreach(var line in File.ReadLines(usageLogPath)){
              if(String.IsNullOrWhiteSpace(line) || line==UsageLogHeader)continue;
              recent.Enqueue(line);
              if(recent.Count>20)recent.Dequeue();
            }
            foreach(string line in recent){
              string[] parts=line.Split(',');
              if(parts.Length!=7)continue;
              double down,up;
              if(!Double.TryParse(parts[2],NumberStyles.Float,
                 CultureInfo.InvariantCulture,out down))continue;
              if(!Double.TryParse(parts[3],NumberStyles.Float,
                 CultureInfo.InvariantCulture,out up))continue;
              DateTimeOffset timestamp;
              string label=parts[1];
              if(DateTimeOffset.TryParse(parts[1],CultureInfo.InvariantCulture,
                 DateTimeStyles.RoundtripKind,out timestamp))
                label=timestamp.ToOffset(TimeSpan.FromHours(1)).ToString(
                  "dd MMM HH:mm",CultureInfo.InvariantCulture)+" WAT";
              logRows.Add(new Dictionary<string,object>{
                {"time",label},{"download",down},{"upload",up}
              });
            }
          }
        }catch(Exception ex){
          System.Diagnostics.Debug.WriteLine("UI log view: "+ex.Message);
        }
        payload["usageLog"]=logRows;
        lastLogSentUtc=DateTime.UtcNow;
      }
      PostApproved(payload);
    }
  }
}
