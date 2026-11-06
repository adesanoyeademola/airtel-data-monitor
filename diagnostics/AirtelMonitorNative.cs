using System;
using System.IO;
using System.Net;
using System.Text;
using System.Diagnostics;
using System.Drawing;
using System.Linq;
using System.Collections.Generic;
using System.Globalization;
using System.Threading;
using System.Security.Cryptography;
using System.IO.Compression;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Web.Script.Serialization;
using System.Windows.Forms.DataVisualization.Charting;

namespace AirtelMonitorNative {
  public class MainForm : Form {
    readonly string root = AppDomain.CurrentDomain.BaseDirectory;
    Process engine;
    NotifyIcon tray;
    System.Windows.Forms.Timer refreshTimer;
    JavaScriptSerializer json = new JavaScriptSerializer();
    Label status, wifi, adapter, last, today, down, up, week, downloadSpeed, uploadSpeed;
    long previousRateSampleId = -1;
    DateTime previousRateReceivedUtc = DateTime.MinValue;
    DateTime previousUsageReceivedUtc = DateTime.MinValue;
    double previousUsageRx = -1, previousUsageTx = -1;
    bool checkingUpdates = false;
    const string AppVersion = "5.3.0";
    Button updateButton;
    const string UpdatesFileName = "updates.txt";
    TextBox hotspot;
    ComboBox adapters;
    Chart chart;
    Panel settings;
    string currentSsid = "";
    bool configured = false, closing = false, share = false;
    const string Base = "http://127.0.0.1:8787";
    Color bg = Color.FromArgb(13, 19, 30), panel = Color.FromArgb(25, 35, 53), ink = Color.FromArgb(239, 245, 252), muted = Color.FromArgb(171, 187, 207), accent = Color.FromArgb(235, 65, 86);
    public MainForm(bool shareMode) {
      share = shareMode;
      Text = "Airtel Data Monitor"; StartPosition = FormStartPosition.CenterScreen; MinimumSize = new Size(785, 660); Size = new Size(1000, 780); BackColor = bg; ForeColor = ink; Font = new Font("Segoe UI", 10);
      try { string ico=Path.Combine(root,"airtel-monitor.ico"); if(File.Exists(ico)) Icon=new Icon(ico); }catch{}
      BuildUi();
      tray = new NotifyIcon(); tray.Icon = Icon ?? SystemIcons.Application; tray.Text = "Airtel Data Monitor"; tray.Visible = true;
      var menu = new ContextMenuStrip(); menu.Items.Add("Open monitor", null, (s,e)=>ShowWindow()); menu.Items.Add("Exit monitor", null, (s,e)=>Quit()); tray.ContextMenuStrip=menu; tray.DoubleClick+=(s,e)=>ShowWindow();
      FormClosing+=(s,e)=>{ if(!closing){e.Cancel=true; Hide();} };
      Shown+=(s,e)=>StartEngine();
      // Silent release-feed check after startup, if the user has configured a trusted feed.
      var backgroundUpdateTimer = new System.Windows.Forms.Timer {Interval = 60000};
      backgroundUpdateTimer.Tick += async (sender,e)=> {backgroundUpdateTimer.Stop();await CheckUpdates(true);backgroundUpdateTimer.Interval=21600000;backgroundUpdateTimer.Start();};
      backgroundUpdateTimer.Start();
      refreshTimer = new System.Windows.Forms.Timer(); refreshTimer.Interval = 3000; refreshTimer.Tick+=(s,e)=>RefreshUsage(); refreshTimer.Start();
    }
    Label LabelText(string s,int size=11,bool bold=false) { return new Label { Text=s, AutoSize=true, ForeColor=ink, Font=new Font("Segoe UI",size,bold?FontStyle.Bold:FontStyle.Regular), Margin=new Padding(0,0,0,4) }; }
    Panel PanelCard() {return new Panel { BackColor=panel, Dock=DockStyle.Fill, Padding=new Padding(18), Margin=new Padding(7) };}
    void BuildUi(){
      var outer=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=1, RowCount=6, Padding=new Padding(18), BackColor=bg };
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,86));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,138));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,92));outer.RowStyles.Add(new RowStyle(SizeType.Percent,100));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,28)); Controls.Add(outer);
      var head=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=2 }; head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,64));head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,36));
      head.Controls.Add(new Label {Text="Airtel Data Monitor",Dock=DockStyle.Fill,AutoEllipsis=false,TextAlign=ContentAlignment.MiddleLeft,ForeColor=Color.White,Font=new Font("Segoe UI",24,FontStyle.Bold),Padding=new Padding(8,0,0,0)},0,0);
      status=new Label {Text="Starting monitor...",Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleRight,ForeColor=muted};head.Controls.Add(status,1,0);
      updateButton = new Button {Text="Check for updates",Width=136,Height=29,Anchor=AnchorStyles.Right,BackColor=Color.FromArgb(32,46,68),ForeColor=Color.White,FlatStyle=FlatStyle.Flat};
      updateButton.FlatAppearance.BorderColor=Color.FromArgb(49,65,86);
      var headerActions = new FlowLayoutPanel {Dock=DockStyle.Fill,FlowDirection=FlowDirection.RightToLeft,WrapContents=false};
      status.AutoSize=true;status.Dock=DockStyle.None;status.Margin=new Padding(8,6,0,0);headerActions.Controls.Add(updateButton);headerActions.Controls.Add(status);
      head.Controls.Remove(status);head.Controls.Add(headerActions,1,0);
      updateButton.Click += async (sender,e)=>await CheckUpdates(false);
      outer.Controls.Add(head,0,0);
      var metrics=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=4};for(int i=0;i<4;i++)metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,25));
      today=Metric(metrics,"Today",0); down=Metric(metrics,"Downloaded",1); up=Metric(metrics,"Uploaded",2); week=Metric(metrics,"7-day usage",3);outer.Controls.Add(metrics,0,1);
      var rates = new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=2 };
      rates.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));rates.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
      downloadSpeed=SpeedMetric(rates,"Download speed",0);uploadSpeed=SpeedMetric(rates,"Upload speed",1);
      outer.Controls.Add(rates,0,2);
      var middle=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2};middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,48));middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,52));
      var net=PanelCard();
      var layoutNetwork=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=3,Margin=new Padding(0)};
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,34));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,66));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      var networkTitle=LabelText("Network",15,true);networkTitle.Dock=DockStyle.Fill;
      layoutNetwork.Controls.Add(networkTitle,0,0);
      var hotspotHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,Margin=new Padding(0)};
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,25));
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,34));
      hotspotHeader.Controls.Add(LabelText("Hotspot"),0,0);
      wifi=LabelText("—",12,true);wifi.AutoEllipsis=true;wifi.AutoSize=false;wifi.Dock=DockStyle.Fill;
      hotspotHeader.Controls.Add(wifi,0,1);layoutNetwork.Controls.Add(hotspotHeader,0,1);
      var detailScroll=new FlowLayoutPanel{Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,AutoScroll=true,Margin=new Padding(0),Padding=new Padding(0,8,0,0)};
      detailScroll.AutoScrollMinSize=new Size(0,300);
      detailScroll.Controls.Add(LabelText("Adapter"));adapter=LabelText("—",12,true);detailScroll.Controls.Add(adapter);
      detailScroll.Controls.Add(LabelText("Last update"));last=LabelText("—");detailScroll.Controls.Add(last);
      detailScroll.Controls.Add(new Label{Text="Scroll for more details",AutoSize=true,ForeColor=muted,Padding=new Padding(0,12,0,5)});
      detailScroll.Controls.Add(new Label{Text="Measured Windows Wi-Fi traffic, not Airtel SIM balance.",AutoSize=false,Width=245,Height=75,ForeColor=muted,Padding=new Padding(0,8,0,0)});
      layoutNetwork.Controls.Add(detailScroll,0,2);net.Controls.Add(layoutNetwork);middle.Controls.Add(net,0,0);
      var chPanel=PanelCard();chart=new Chart{Dock=DockStyle.Fill,BackColor=panel,Palette=ChartColorPalette.None};var area=new ChartArea("usage");area.BackColor=panel;area.AxisX.LabelStyle.ForeColor=muted;area.AxisY.LabelStyle.ForeColor=muted;area.AxisX.LineColor=muted;area.AxisY.LineColor=muted;area.AxisX.MajorGrid.Enabled=false;area.AxisY.MajorGrid.LineColor=Color.FromArgb(48,60,76);area.AxisY.LabelStyle.Format="0.##";chart.ChartAreas.Add(area);var series=new Series("Data") {ChartType=SeriesChartType.Column,Color=accent,IsValueShownAsLabel=false};chart.Series.Add(series);chart.Dock=DockStyle.Fill;var title=LabelText("Daily usage",15,true);var layout=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=2,ColumnCount=1};layout.RowStyles.Add(new RowStyle(SizeType.Absolute,38));layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.Controls.Add(title,0,0);layout.Controls.Add(chart,0,1);chPanel.Controls.Add(layout);middle.Controls.Add(chPanel,1,0);outer.Controls.Add(middle,0,3);
      settings=PanelCard();var section=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=4,RowCount=2};section.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,28));section.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,28));section.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,22));section.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,22));section.RowStyles.Add(new RowStyle(SizeType.Absolute,40));section.RowStyles.Add(new RowStyle(SizeType.Absolute,50));section.Controls.Add(LabelText("Hotspot settings",15,true),0,0);section.SetColumnSpan(section.GetControlFromPosition(0,0),4);
      hotspot=new TextBox{Dock=DockStyle.Fill,Margin=new Padding(5),BackColor=bg,ForeColor=ink,BorderStyle=BorderStyle.FixedSingle};section.Controls.Add(hotspot,0,1);
      adapters=new ComboBox{Dock=DockStyle.Fill,DropDownStyle=ComboBoxStyle.DropDownList,Margin=new Padding(5),BackColor=bg,ForeColor=ink};adapters.Items.Add("Wi-Fi");adapters.SelectedIndex=0;section.Controls.Add(adapters,1,1);
      var choose=new Button{Text="Use current Wi-Fi",Dock=DockStyle.Fill,Margin=new Padding(5)};choose.Click+=(s,e)=>{if(!String.IsNullOrEmpty(currentSsid))hotspot.Text=currentSsid;};section.Controls.Add(choose,2,1);
      var save=new Button{Text="Save hotspot",Dock=DockStyle.Fill,Margin=new Padding(5),BackColor=accent,ForeColor=Color.White,FlatStyle=FlatStyle.Flat};save.Click+=(s,e)=>SaveSettings();section.Controls.Add(save,3,1);settings.Controls.Add(section);
      outer.Controls.Add(new Label{Dock=DockStyle.Fill,Text="Monitoring runs while this app is open or minimized to the tray.",ForeColor=muted,TextAlign=ContentAlignment.MiddleLeft,Font=new Font("Segoe UI",9)},0,5);
    }
    Label Metric(TableLayoutPanel parent,string name,int col) {var p=PanelCard();var stack=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=2};stack.RowStyles.Add(new RowStyle(SizeType.Percent,40));stack.RowStyles.Add(new RowStyle(SizeType.Percent,60));stack.Controls.Add(new Label {Text=name,Dock=DockStyle.Fill,ForeColor=muted,TextAlign=ContentAlignment.MiddleLeft},0,0);var val=new Label{Text="0 B",Dock=DockStyle.Fill,ForeColor=ink,Font=new Font("Segoe UI",22,FontStyle.Bold),TextAlign=ContentAlignment.MiddleLeft};stack.Controls.Add(val,0,1);p.Controls.Add(stack);parent.Controls.Add(p,col,0);return val;}
    Label SpeedMetric(TableLayoutPanel parent,string name,int col){
      var p=PanelCard();var stack=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2};
      stack.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,45));stack.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,55));
      stack.Controls.Add(new Label{Text=name,Dock=DockStyle.Fill,ForeColor=muted,TextAlign=ContentAlignment.MiddleLeft},0,0);
      var value=new Label{Text="— KB/s",Dock=DockStyle.Fill,ForeColor=ink,Font=new Font("Segoe UI",18,FontStyle.Bold),TextAlign=ContentAlignment.MiddleRight};
      stack.Controls.Add(value,1,0);p.Controls.Add(stack);parent.Controls.Add(p,col,0);return value;
    }
    string Rate(double bytesPerSecond){
      if(bytesPerSecond<0 || Double.IsNaN(bytesPerSecond) || Double.IsInfinity(bytesPerSecond))return "— KB/s";
      if(bytesPerSecond>=1048576)return (bytesPerSecond/1048576).ToString("0.0",CultureInfo.InvariantCulture)+" MB/s";
      return (bytesPerSecond/1024).ToString("0.0",CultureInfo.InvariantCulture)+" KB/s";
    }
    void StartEngine(){
      string ps=Path.Combine(root,"monitor.ps1");if(!File.Exists(ps)){MessageBox.Show("Monitoring engine missing. Existing installation files may be incomplete.");return;}
      try {var pi=new ProcessStartInfo("powershell.exe","-NoProfile -ExecutionPolicy Bypass -File \""+ps+"\" -NoBrowser"+(share?" -Share":""));pi.CreateNoWindow=true;pi.UseShellExecute=false;pi.WorkingDirectory=root; engine=Process.Start(pi);}catch(Exception e){MessageBox.Show("Could not start monitoring: "+e.Message);}
      RefreshUsage();
    }
    Dictionary<string,object> GetData(){ using(var wc=new WebClient()){wc.Encoding=Encoding.UTF8;wc.Headers[HttpRequestHeader.CacheControl]="no-cache";return json.Deserialize<Dictionary<string,object>>(wc.DownloadString(Base+"/api/summary"));}}
    string Str(Dictionary<string,object> d,string k){return d.ContainsKey(k)&&d[k]!=null?Convert.ToString(d[k]):"";}
    double Num(Dictionary<string,object> d,string k){double n;return double.TryParse(Str(d,k),System.Globalization.NumberStyles.Any,System.Globalization.CultureInfo.InvariantCulture,out n)?n:0;}
    string Bytes(double n){if(n<1024)return Math.Round(n)+" B";if(n<1048576)return (n/1024).ToString("0.0",CultureInfo.InvariantCulture)+" KB";if(n<1073741824)return (n/1048576).ToString("0.0",CultureInfo.InvariantCulture)+" MB";return (n/1073741824).ToString("0.00",CultureInfo.InvariantCulture)+" GB";}
    void RefreshUsage(){
      try {var d=GetData();string stat=Str(d,"status");status.Text= stat=="tracking"?"●  Monitoring live":stat=="not-configured"?"Set your hotspot":stat=="wrong-network"?"Waiting for hotspot":stat=="adapter-error"?"Adapter error":"Monitoring";status.ForeColor=stat=="tracking"?Color.FromArgb(79,212,161):muted;
        double rx=Num(d,"todayRx"), tx=Num(d,"todayTx");
        today.Text=Bytes(Num(d,"todayTotal"));down.Text=Bytes(rx);up.Text=Bytes(tx);week.Text=Bytes(Num(d,"sevenDayTotal"));
        long sampleId = (long)Num(d,"rateSampleId");
        bool valid = d.ContainsKey("rateValid") && (Str(d,"rateValid").Equals("True",StringComparison.OrdinalIgnoreCase) || Str(d,"rateValid") == "true");
        DateTime sampleUtc;
        bool timestampValid = DateTime.TryParse(Str(d,"rateSampleTime"), CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out sampleUtc);
        bool fresh = timestampValid && Math.Abs((DateTime.UtcNow - sampleUtc.ToUniversalTime()).TotalSeconds) <= 14;
        // Use native byte-counter rates first, then recorded usage deltas if the
        // sample validity/timestamp is unavailable. No invented traffic values.
        DateTime nowUtc=DateTime.UtcNow;
        bool fallbackValid=false;
        double fallbackRx=0,fallbackTx=0;
        if(stat=="tracking" && previousUsageRx>=0 && previousUsageTx>=0){
          double seconds=(nowUtc-previousUsageReceivedUtc).TotalSeconds;
          double diffRx=rx-previousUsageRx,diffTx=tx-previousUsageTx;
          if(seconds>0.5 && seconds<30 && diffRx>=0 && diffTx>=0){
            fallbackRx=diffRx/seconds;fallbackTx=diffTx/seconds;fallbackValid=true;
          }
        }
        if(stat!="tracking"){
          downloadSpeed.Text="— KB/s";uploadSpeed.Text="— KB/s";
          previousUsageRx=-1;previousUsageTx=-1;previousRateSampleId=-1;
        } else {
          if(valid && fresh){
            downloadSpeed.Text=Rate(Num(d,"rateRxBps"));
            uploadSpeed.Text=Rate(Num(d,"rateTxBps"));
            previousRateSampleId=sampleId;previousRateReceivedUtc=nowUtc;
          } else if(fallbackValid){
            downloadSpeed.Text=Rate(fallbackRx);
            uploadSpeed.Text=Rate(fallbackTx);
          } else {
            downloadSpeed.Text="Measuring...";uploadSpeed.Text="Measuring...";
          }
          previousUsageRx=rx;previousUsageTx=tx;previousUsageReceivedUtc=nowUtc;
        }
        currentSsid=Str(d,"currentSsid");wifi.Text=(currentSsid.Length>0?currentSsid:"Not connected");adapter.Text=Str(d,"adapterName");last.Text=Str(d,"lastUpdated").Length>0?Str(d,"lastUpdated"):"No activity";
        if(!configured) {hotspot.Text=Str(d,"targetSsid").Length>0?Str(d,"targetSsid"):currentSsid;var selected=Str(d,"adapterName");adapters.Items.Clear();var choices=d.ContainsKey("adapterChoices")?d["adapterChoices"] as System.Collections.ArrayList:null;if(choices!=null)foreach(var x in choices)adapters.Items.Add(Convert.ToString(x));if(adapters.Items.Count==0)adapters.Items.Add("Wi-Fi");adapters.SelectedItem=selected;if(adapters.SelectedIndex<0)adapters.SelectedIndex=0;configured=true;}
        var map=new Dictionary<string,double>();var days=d.ContainsKey("days")?d["days"] as System.Collections.ArrayList:null;if(days!=null)foreach(var item in days){var row=item as Dictionary<string,object>;if(row!=null)map[Str(row,"date")]=Num(row,"total");}chart.Series[0].Points.Clear();for(int i=6;i>=0;i--){DateTime day=DateTime.Today.AddDays(-i);string k=day.ToString("yyyy-MM-dd");int idx=chart.Series[0].Points.AddY(map.ContainsKey(k)?map[k]/1048576:0);chart.Series[0].Points[idx].AxisLabel=day.ToString("ddd");}
      }catch {status.Text="Connecting to monitor...";status.ForeColor=muted;previousRateSampleId=-1;previousUsageRx=-1;previousUsageTx=-1;downloadSpeed.Text="— KB/s";uploadSpeed.Text="— KB/s";}
    }
    void SaveSettings(){string name=hotspot.Text.Trim();if(name.Length==0){MessageBox.Show("Enter your hotspot name.");return;}try{var d=GetData();if(Str(d,"targetSsid").Length>0&&!String.Equals(name,Str(d,"targetSsid"),StringComparison.OrdinalIgnoreCase)){if(MessageBox.Show("Changing the hotspot clears recorded usage. Continue?","Confirm",MessageBoxButtons.YesNo)!=DialogResult.Yes)return;}string body=json.Serialize(new{targetSsid=name,adapterName=adapters.SelectedItem.ToString()});byte[] bytes=Encoding.UTF8.GetBytes(body);var request=(HttpWebRequest)WebRequest.Create(Base+"/api/config");request.Method="POST";request.ContentType="application/json";request.ContentLength=bytes.Length;using(var st=request.GetRequestStream())st.Write(bytes,0,bytes.Length);using(var response=request.GetResponse()){}configured=false;RefreshUsage();MessageBox.Show("Hotspot saved.","Airtel Data Monitor");}catch(Exception ex){MessageBox.Show("Could not save: "+ex.Message);}}
    string FeedUrl() {
      string path=Path.Combine(root,UpdatesFileName);
      if(!File.Exists(path))return "";
      foreach(string line in File.ReadAllLines(path)){
        string t=line.Trim();if(t.StartsWith("https://",StringComparison.OrdinalIgnoreCase))return t;
      }
      return "";
    }
    async Task CheckUpdates(bool silent) {
      if(checkingUpdates)return;
      string url=FeedUrl();
      if(String.IsNullOrWhiteSpace(url)){
        if(!silent)MessageBox.Show("Automatic updates need an HTTPS release feed. No feed has been configured yet.\n\nYour existing monitor will keep working. Future releases can be published to a trusted feed and its URL saved in updates.txt in the installation folder.","Updates not configured");
        return;
      }
      // GitHub HTTPS requires TLS 1.2 on older .NET Framework defaults.
      ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
      checkingUpdates=true;if(updateButton!=null)updateButton.Enabled=false;
      try{
        string manifest=await Task.Run(()=>{using(var wc=new WebClient()){wc.Headers[HttpRequestHeader.UserAgent]="AirtelDataMonitor/5";return wc.DownloadString(url);}});
        var d=json.Deserialize<Dictionary<string,object>>(manifest);
        if(d!=null && Str(d,"status")=="no-release") { if(!silent)MessageBox.Show("No newer update has been published yet.","Updates");return; }
        if(d==null || !d.ContainsKey("version") || !d.ContainsKey("packageUrl") || !d.ContainsKey("sha256"))throw new Exception("Invalid release manifest.");
        string version=Str(d,"version"),packageUrl=Str(d,"packageUrl"),sha=Str(d,"sha256").ToLowerInvariant();
        Uri releaseUri;
        if(!Uri.TryCreate(packageUrl,UriKind.Absolute,out releaseUri)||releaseUri.Scheme!="https")throw new Exception("Release must use HTTPS.");
        if(!System.Text.RegularExpressions.Regex.IsMatch(sha,"^[0-9a-f]{64}$"))throw new Exception("Invalid release checksum.");
        Version newest,current;
        if(!Version.TryParse(version,out newest)||!Version.TryParse(AppVersion,out current))throw new Exception("Invalid version.");
        if(newest<=current){if(!silent)MessageBox.Show("You're up to date (v"+AppVersion+").","Updates");return;}
        if(MessageBox.Show("Version "+version+" is available. Download and install it now?\nThe app will restart and your data will be kept.","Update available",MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)return;
        string temp=Path.Combine(Path.GetTempPath(),"AirtelMonitor-"+version+".zip");
        await Task.Run(()=>{
          using(var wc=new WebClient()){wc.Headers[HttpRequestHeader.UserAgent]="AirtelDataMonitor/5";wc.DownloadFile(packageUrl,temp);}
          using(var file=File.OpenRead(temp))using(var h=SHA256.Create()){
            string actual=BitConverter.ToString(h.ComputeHash(file)).Replace("-","").ToLowerInvariant();
            if(!String.Equals(actual,sha,StringComparison.Ordinal))throw new Exception("Checksum mismatch. Update rejected.");
          }
          using(var zip=ZipFile.OpenRead(temp)){
            if(!zip.Entries.Any(z=>z.FullName=="AirtelMonitorNative.cs")||!zip.Entries.Any(z=>z.FullName=="monitor.ps1"))throw new Exception("Update files missing.");
            foreach(var entry in zip.Entries){if(entry.FullName.Contains("..")||entry.FullName.StartsWith("/")||entry.FullName.Contains("\\"))throw new Exception("Unsafe archive entry.");}
          }
        });
        var pi=new ProcessStartInfo("powershell.exe","-NoProfile -ExecutionPolicy Bypass -File \""+Path.Combine(root,"Apply_Update.ps1")+"\" -Package \""+temp+"\" -ParentPid "+Process.GetCurrentProcess().Id);
        pi.UseShellExecute=true;pi.WindowStyle=ProcessWindowStyle.Normal;
        Process.Start(pi);
        Quit();
      }catch(Exception ex){if(!silent)MessageBox.Show("Could not check or download updates: "+ex.Message,"Update error");}
      finally{checkingUpdates=false;if(updateButton!=null&&!updateButton.IsDisposed)updateButton.Enabled=true;}
    }
    void ShowWindow(){Show();WindowState=FormWindowState.Normal;Activate();}
    void Quit(){closing=true;refreshTimer.Stop();try{if(engine!=null&&!engine.HasExited)engine.Kill();}catch{}tray.Visible=false;tray.Dispose();Close();}
    [STAThread] static void Main(string[] args){bool created;using(var mutex=new Mutex(true,"Local\\AirtelDataMonitorDesktopV3",out created)){if(!created){MessageBox.Show("Airtel Data Monitor is already running. Open it from the system tray.");return;}Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new MainForm(args.Any(a=>a=="--share")));}}
  }
}
