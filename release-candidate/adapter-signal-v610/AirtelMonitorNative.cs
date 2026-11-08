using System;
using System.IO;
using System.Net;
using System.Text;
using System.Diagnostics;
using System.Net.NetworkInformation;
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
    Label status, statusDot, sampleAgeLabel, speedSourceLabel, wifi, adapter, signalStrength, last, today, down, up, week, downloadSpeed, uploadSpeed;
    DateTime mostRecentAdapterSampleUtc=DateTime.MinValue;
    System.Windows.Forms.Timer indicatorTimer;
    int indicatorState=1; // 0=live (green), 1=paused/waiting (yellow), 2=disconnected (red)
    double indicatorPhase=0;
    DateTime engineLaunchUtc=DateTime.MinValue;
    DateTime lastEngineAttemptUtc=DateTime.MinValue;
    long previousRateSampleId = -1;
    DateTime previousRateReceivedUtc = DateTime.MinValue;
    DateTime previousUsageReceivedUtc = DateTime.MinValue;
    double previousUsageRx = -1, previousUsageTx = -1;
    // Windows Network Interface performance counters are the preferred
    // LIVE speed source. The PowerShell adapter engine remains responsible
    // for ALL cumulative usage, saved history, hotspot connection and status.
    readonly object liveCounterLock=new object();
    System.Threading.Timer liveCounterTimer;
    PerformanceCounter nativeRxCounter, nativeTxCounter;
    string nativeCounterAdapter="";
    volatile string requestedCounterAdapter="";
    DateTime lastNativeSampleUtc=DateTime.MinValue;
    double nativeRxBytesPerSecond=0, nativeTxBytesPerSecond=0;
    long nativeSampleId=0;
    bool nativeCounterAvailable=false;
    DateTime nativeRetryUtc=DateTime.MinValue;
    bool checkingUpdates = false;
    const string AppVersion = "6.10.0";
    Button updateButton;
    const string UpdatesFileName = "updates.txt";
    TextBox hotspot;
    ComboBox adapters;
    Chart chart, liveChart;
    Button graphToggle;
    Label chartTitle, chartCaption;
    bool showLiveChart = false;
    bool showUsageLog = false;
    Button usageLogToggle;
    DataGridView usageGrid;
    static readonly TimeSpan UsageZoneOffset=TimeSpan.FromHours(1); // Nigeria WAT; no DST
    DateTime logLastMeasurementUtc=DateTime.MinValue;
    DateTime logWindowStart=DateTime.MinValue;
    DateTime logLastObserved=DateTime.MinValue;
    double logWindowRx=0, logWindowTx=0, logLastRx=0, logLastTx=0;
    readonly string usageLogPath=Path.Combine(
      Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
      "AirtelDataMonitor","data","usage-timeline.csv");
    string usageLogError="";
    bool usagePollInProgress=false;
    int consecutivePollFailures=0;
    DateTime lastDailyChartRenderUtc=DateTime.MinValue;
    long lastRecordedGraphSampleId=-1;
    DateTime lastRecordedGraphTimeUtc=DateTime.MinValue;
    readonly List<LiveRateSample> liveRateHistory = new List<LiveRateSample>();
    class LiveRateSample {
      public DateTime AtUtc;
      public double DownloadKbps, UploadKbps;
      public bool Valid;
    }
    Panel settings;
    string currentSsid = "";
    bool configured = false, closing = false, share = false;
    const string Base = "http://127.0.0.1:8787";
    Color bg = Color.FromArgb(13, 19, 30), panel = Color.FromArgb(25, 35, 53), ink = Color.FromArgb(239, 245, 252), muted = Color.FromArgb(171, 187, 207), accent = Color.FromArgb(235, 65, 86);
    public MainForm(bool shareMode) {
      share = shareMode;
      Text = "T-Net"; StartPosition = FormStartPosition.CenterScreen; MinimumSize = new Size(785, 660); Size = new Size(1000, 780); BackColor = bg; ForeColor = ink; Font = new Font("Segoe UI", 10);
      try { string ico=Path.Combine(root,"airtel-monitor.ico"); if(File.Exists(ico)) Icon=new Icon(ico); }catch{}
      BuildUi();
      LoadUsageLog();
      // The explicit "Restart service" warning is also an action users can click.
      downloadSpeed.Cursor=Cursors.Hand;uploadSpeed.Cursor=Cursors.Hand;
      downloadSpeed.Click+=(sender,e)=>{if(downloadSpeed.Text=="Restart service")RestartEngine();};
      uploadSpeed.Click+=(sender,e)=>{if(uploadSpeed.Text=="Restart service")RestartEngine();};
      tray = new NotifyIcon(); tray.Icon = Icon ?? SystemIcons.Application; tray.Text = "T-Net"; tray.Visible = true;
      var menu = new ContextMenuStrip(); menu.Items.Add("Open monitor", null, (s,e)=>ShowWindow()); menu.Items.Add("Restart monitoring service", null, (s,e)=>RestartEngine()); menu.Items.Add("Exit monitor", null, (s,e)=>Quit()); tray.ContextMenuStrip=menu; tray.DoubleClick+=(s,e)=>ShowWindow();
      FormClosing+=(s,e)=>{ if(!closing){e.Cancel=true; Hide();} };
      Shown+=(s,e)=>{RenameShortcuts();StartEngine();};
      // Silent release-feed check after startup, if the user has configured a trusted feed.
      var backgroundUpdateTimer = new System.Windows.Forms.Timer {Interval = 60000};
      backgroundUpdateTimer.Tick += async (sender,e)=> {backgroundUpdateTimer.Stop();await CheckUpdates(true);backgroundUpdateTimer.Interval=21600000;backgroundUpdateTimer.Start();};
      backgroundUpdateTimer.Start();
      refreshTimer = new System.Windows.Forms.Timer(); refreshTimer.Interval = 500; refreshTimer.Tick+=(s,e)=>RefreshUsageAsync(); refreshTimer.Start();
      indicatorTimer = new System.Windows.Forms.Timer{Interval=100};
      indicatorTimer.Tick+=(s,e)=>PulseIndicator();indicatorTimer.Start();
      // PDH measurements are sampled off the UI thread. Failure is nonfatal
      // and automatically falls back to the existing direct adapter rates.
      liveCounterTimer=new System.Threading.Timer(SampleNativeCounters,null,350,1000);
    }
    Label LabelText(string s,int size=11,bool bold=false) { return new Label { Text=s, AutoSize=true, ForeColor=ink, Font=new Font("Segoe UI",size,bold?FontStyle.Bold:FontStyle.Regular), Margin=new Padding(0,0,0,4) }; }
    Panel PanelCard() {return new Panel { BackColor=panel, Dock=DockStyle.Fill, Padding=new Padding(18), Margin=new Padding(7) };}
    void BuildUi(){
      var outer=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=1, RowCount=6, Padding=new Padding(18), BackColor=bg };
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,86));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,138));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,92));outer.RowStyles.Add(new RowStyle(SizeType.Percent,100));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,28)); Controls.Add(outer);
      var head=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=2 }; head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,64));head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,36));
      head.Controls.Add(new Label {Text="T-Net",Dock=DockStyle.Fill,AutoEllipsis=false,TextAlign=ContentAlignment.MiddleLeft,ForeColor=Color.White,Font=new Font("Segoe UI",24,FontStyle.Bold),Padding=new Padding(8,0,0,0)},0,0);
      status=new Label {Text="Starting monitor...",Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleRight,ForeColor=muted};head.Controls.Add(status,1,0);
      statusDot=new Label{Text="●",AutoSize=true,ForeColor=Color.FromArgb(236,185,65),
         Font=new Font("Segoe UI",14,FontStyle.Bold),TextAlign=ContentAlignment.MiddleCenter,
         Margin=new Padding(2,1,2,0)};
      updateButton = new Button {Text="Check for updates",Width=136,Height=29,Anchor=AnchorStyles.Right,BackColor=Color.FromArgb(32,46,68),ForeColor=Color.White,FlatStyle=FlatStyle.Flat};
      updateButton.FlatAppearance.BorderColor=Color.FromArgb(49,65,86);
      var headerActions = new FlowLayoutPanel {Dock=DockStyle.Fill,FlowDirection=FlowDirection.RightToLeft,WrapContents=false};
      status.AutoSize=true;status.Dock=DockStyle.None;status.Margin=new Padding(2,7,7,0);headerActions.Controls.Add(updateButton);headerActions.Controls.Add(status);headerActions.Controls.Add(statusDot);
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
      var networkHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,Margin=new Padding(0)};
      networkHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,42));
      networkHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,58));
      sampleAgeLabel=new Label{
        Text="Last sample: waiting",Dock=DockStyle.Fill,
        TextAlign=ContentAlignment.MiddleRight,ForeColor=muted,
        Font=new Font("Segoe UI",9),AutoEllipsis=true
      };
      networkHeader.Controls.Add(networkTitle,0,0);
      networkHeader.Controls.Add(sampleAgeLabel,1,0);
      layoutNetwork.Controls.Add(networkHeader,0,0);
      var hotspotHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,Margin=new Padding(0)};
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,25));
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,34));
      hotspotHeader.Controls.Add(LabelText("Hotspot"),0,0);
      wifi=LabelText("—",12,true);wifi.AutoEllipsis=true;wifi.AutoSize=false;wifi.Dock=DockStyle.Fill;
      hotspotHeader.Controls.Add(wifi,0,1);layoutNetwork.Controls.Add(hotspotHeader,0,1);
      var detailScroll=new FlowLayoutPanel{Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,AutoScroll=true,Margin=new Padding(0),Padding=new Padding(0,0,0,0)};
      detailScroll.AutoScrollMinSize=new Size(0,300);
      speedSourceLabel=new Label{
        Text="Live speed source: checking...",AutoSize=true,ForeColor=muted,
        Font=new Font("Segoe UI",9),Margin=new Padding(0,0,0,16)
      };
      detailScroll.Controls.Add(speedSourceLabel);
      detailScroll.Controls.Add(LabelText("Adapter"));adapter=LabelText("—",12,true);detailScroll.Controls.Add(adapter);
      detailScroll.Controls.Add(LabelText("Wi-Fi signal strength"));signalStrength=LabelText("—",12,true);detailScroll.Controls.Add(signalStrength);
      detailScroll.Controls.Add(LabelText("Last update"));last=LabelText("—");detailScroll.Controls.Add(last);
      detailScroll.Controls.Add(new Label{Text="Scroll for more details",AutoSize=true,ForeColor=muted,Padding=new Padding(0,12,0,5)});
      detailScroll.Controls.Add(new Label{Text="Measured Windows Wi-Fi traffic, not Airtel SIM balance.",AutoSize=false,Width=245,Height=75,ForeColor=muted,Padding=new Padding(0,8,0,0)});
      layoutNetwork.Controls.Add(detailScroll,0,2);net.Controls.Add(layoutNetwork);middle.Controls.Add(net,0,0);
      var chPanel=PanelCard();
      // Preserve the daily usage chart unchanged, in a separate graph surface.
      chart=new Chart{Dock=DockStyle.Fill,BackColor=panel,Palette=ChartColorPalette.None};
      var area=new ChartArea("usage");
      area.BackColor=panel;area.AxisX.LabelStyle.ForeColor=muted;area.AxisY.LabelStyle.ForeColor=muted;
      area.AxisX.LineColor=muted;area.AxisY.LineColor=muted;area.AxisX.MajorGrid.Enabled=false;
      area.AxisY.MajorGrid.LineColor=Color.FromArgb(48,60,76);area.AxisY.LabelStyle.Format="0.##";
      chart.ChartAreas.Add(area);
      var series=new Series("Data"){ChartType=SeriesChartType.Column,Color=accent,IsValueShownAsLabel=false};
      chart.Series.Add(series);

      // The live graph is display-only. The recording engine and usage.json
      // stay untouched. Points are sourced exclusively from timestamped
      // adapter speed samples, never from daily usage.
      liveChart=new Chart{Dock=DockStyle.Fill,BackColor=panel,Palette=ChartColorPalette.None,Visible=false};
      var liveArea=new ChartArea("rates");
      liveArea.BackColor=panel;
      liveArea.AxisX.LabelStyle.ForeColor=muted;liveArea.AxisY.LabelStyle.ForeColor=muted;
      liveArea.AxisX.LineColor=muted;liveArea.AxisY.LineColor=muted;
      liveArea.AxisX.MajorGrid.LineColor=Color.FromArgb(42,54,71);
      liveArea.AxisY.MajorGrid.LineColor=Color.FromArgb(42,54,71);
      liveArea.AxisX.LabelStyle.Format="HH:mm:ss";
      liveArea.AxisX.IntervalType=DateTimeIntervalType.Seconds;liveArea.AxisX.Interval=15;
      liveArea.AxisY.Minimum=0;liveArea.AxisY.LabelStyle.Format="0.##";
      liveArea.AxisY.Title="Kbps";liveArea.AxisY.TitleForeColor=muted;
      liveChart.ChartAreas.Add(liveArea);
      var incoming=new Series("Download"){ChartType=SeriesChartType.FastLine,
        XValueType=ChartValueType.DateTime,Color=Color.FromArgb(57,174,250),BorderWidth=2};
      var outgoing=new Series("Upload"){ChartType=SeriesChartType.FastLine,
        XValueType=ChartValueType.DateTime,Color=Color.FromArgb(93,217,151),BorderWidth=2};
      liveChart.Series.Add(incoming);liveChart.Series.Add(outgoing);
      var legend=new Legend("directions"){Docking=Docking.Bottom,Alignment=StringAlignment.Center,
        BackColor=panel,ForeColor=ink,Font=new Font("Segoe UI",8),LegendStyle=LegendStyle.Row};
      liveChart.Legends.Add(legend);

      chartTitle=LabelText("Daily usage",15,true);
      chartTitle.Dock=DockStyle.Fill;
      graphToggle=new Button{Text="Live speed",Dock=DockStyle.Right,Width=110,Height=30,
        BackColor=Color.FromArgb(32,46,68),ForeColor=ink,FlatStyle=FlatStyle.Flat,Margin=new Padding(3)};
      graphToggle.FlatAppearance.BorderColor=Color.FromArgb(49,65,86);
      graphToggle.Click+=(sender,e)=>SetGraphView(showLiveChart?0:1);
      usageLogToggle=new Button{Text="Usage log",Dock=DockStyle.Right,Width=100,Height=30,
        BackColor=Color.FromArgb(32,46,68),ForeColor=ink,FlatStyle=FlatStyle.Flat,
        Margin=new Padding(3)};
      usageLogToggle.FlatAppearance.BorderColor=Color.FromArgb(49,65,86);
      usageLogToggle.Click+=(sender,e)=>SetGraphView(showUsageLog?0:2);
      var graphHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=3,RowCount=1};
      graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,120));
      graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,110));
      graphHeader.Controls.Add(chartTitle,0,0);
      graphHeader.Controls.Add(graphToggle,1,0);
      graphHeader.Controls.Add(usageLogToggle,2,0);
      var graphSurface=new Panel{Dock=DockStyle.Fill};
      graphSurface.Controls.Add(chart);graphSurface.Controls.Add(liveChart);
      usageGrid=new DataGridView{
        Dock=DockStyle.Fill,Visible=false,ReadOnly=true,AllowUserToAddRows=false,
        AllowUserToDeleteRows=false,AllowUserToResizeRows=false,RowHeadersVisible=false,
        BackgroundColor=panel,BorderStyle=BorderStyle.None,GridColor=Color.FromArgb(42,54,71),
        AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill,
        ScrollBars=ScrollBars.Both,SelectionMode=DataGridViewSelectionMode.FullRowSelect,
        MultiSelect=false,EnableHeadersVisualStyles=false,
        ColumnHeadersHeight=27,RowTemplate={Height=27}
      };
      usageGrid.DefaultCellStyle.BackColor=panel;
      usageGrid.DefaultCellStyle.ForeColor=ink;
      usageGrid.DefaultCellStyle.SelectionBackColor=Color.FromArgb(38,62,86);
      usageGrid.DefaultCellStyle.SelectionForeColor=ink;
      usageGrid.DefaultCellStyle.Font=new Font("Segoe UI",8);
      usageGrid.ColumnHeadersDefaultCellStyle.BackColor=Color.FromArgb(34,47,66);
      usageGrid.ColumnHeadersDefaultCellStyle.ForeColor=ink;
      usageGrid.ColumnHeadersDefaultCellStyle.Font=new Font("Segoe UI",8,FontStyle.Bold);
      usageGrid.Columns.Add("recorded","Interval end (WAT)");
      usageGrid.Columns.Add("period","Period");
      usageGrid.Columns.Add("received","Down");
      usageGrid.Columns.Add("sent","Up");
      usageGrid.Columns.Add("used","Used");
      usageGrid.Columns.Add("running","Today total");
      foreach(DataGridViewColumn col in usageGrid.Columns)
        col.SortMode=DataGridViewColumnSortMode.NotSortable;
      usageGrid.Columns["recorded"].FillWeight=155;
      usageGrid.Columns["period"].FillWeight=65;
      usageGrid.Columns["used"].FillWeight=85;
      usageGrid.Columns["running"].FillWeight=110;
      graphSurface.Controls.Add(usageGrid);
      chartCaption=new Label{Text="Last 7 days  •  MB",Dock=DockStyle.Fill,ForeColor=muted,
        Font=new Font("Segoe UI",8),TextAlign=ContentAlignment.MiddleLeft};
      chartCaption.Click+=(sender,e)=>{
        if(!showUsageLog || !File.Exists(usageLogPath))return;
        try{Process.Start("explorer.exe","/select,\""+usageLogPath+"\"");}
        catch(Exception err){MessageBox.Show("Could not open usage log: "+err.Message);}
      };
      var graphLayout=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=3,ColumnCount=1};
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,40));
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,22));
      graphLayout.Controls.Add(graphHeader,0,0);
      graphLayout.Controls.Add(graphSurface,0,1);
      graphLayout.Controls.Add(chartCaption,0,2);
      chPanel.Controls.Add(graphLayout);middle.Controls.Add(chPanel,1,0);
      outer.Controls.Add(middle,0,3);
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
      var value=new Label{Text="— Kbps",Dock=DockStyle.Fill,ForeColor=ink,Font=new Font("Segoe UI",18,FontStyle.Bold),TextAlign=ContentAlignment.MiddleRight};
      stack.Controls.Add(value,1,0);p.Controls.Add(stack);parent.Controls.Add(p,col,0);return value;
    }
    // Use decimal bits/sec, as Task Manager reports (1 Kbps = 1000 bits/sec).
    // Hard safety bound (10 Gbps per direction). The engine additionally
    // checks intervals against the physical adapter link speed when available.
    bool PlausibleRate(double bytesPerSecond){
      return !Double.IsNaN(bytesPerSecond) && !Double.IsInfinity(bytesPerSecond)
             && bytesPerSecond>=0 && bytesPerSecond<=1250000000.0;
    }
    string Rate(double bytesPerSecond){
      if(!PlausibleRate(bytesPerSecond))return "Measuring...";
      double bitsPerSecond=bytesPerSecond*8.0;
      if(bitsPerSecond>=1000000)return (bitsPerSecond/1000000).ToString("0.0",CultureInfo.InvariantCulture)+" Mbps";
      return (bitsPerSecond/1000).ToString("0.0",CultureInfo.InvariantCulture)+" Kbps";
    }
    // Windows can leave a previous monitoring PowerShell running after an update.
    // Stop only processes running this exact monitor.ps1 script, never every
    // PowerShell process. This avoids port 8787 collisions and stale speed data.
    bool StopPriorMonitoringProcesses(){
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
    void RestartEngine(){
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
    }
    bool ServiceResponding(){
      try {
        var req=(HttpWebRequest)WebRequest.Create(Base+"/api/summary");
        req.Timeout=900;req.ReadWriteTimeout=900;req.KeepAlive=false;
        using(var response=(HttpWebResponse)req.GetResponse())
        using(var reader=new StreamReader(response.GetResponseStream())){
          string payload=reader.ReadToEnd();
          return response.StatusCode==HttpStatusCode.OK && payload.Contains("\"todayTotal\"");
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
      string ps=Path.Combine(root,"monitor.ps1");if(!File.Exists(ps)){MessageBox.Show("Monitoring engine missing. Existing installation files may be incomplete.");return;}
      engineLaunchUtc=DateTime.UtcNow;
      try {var pi=new ProcessStartInfo("powershell.exe","-NoProfile -ExecutionPolicy Bypass -File \""+ps+"\" -NoBrowser"+(share?" -Share":""));pi.CreateNoWindow=true;pi.UseShellExecute=false;pi.WorkingDirectory=root; engine=Process.Start(pi);}catch(Exception e){MessageBox.Show("Could not start monitoring: "+e.Message);}
      RefreshUsageAsync();
    }
    Dictionary<string,object> GetData(){ using(var wc=new WebClient()){wc.Encoding=Encoding.UTF8;wc.Headers[HttpRequestHeader.CacheControl]="no-cache";return json.Deserialize<Dictionary<string,object>>(wc.DownloadString(Base+"/api/summary"));}}
    string Str(Dictionary<string,object> d,string k){return d.ContainsKey(k)&&d[k]!=null?Convert.ToString(d[k]):"";}
    double Num(Dictionary<string,object> d,string k){
      object raw;
      if(!d.TryGetValue(k,out raw) || raw==null)return 0;
      try {
        double n=0;
        if(raw is string){
          if(!double.TryParse((string)raw,NumberStyles.Float,CultureInfo.InvariantCulture,out n))return 0;
        }else{
          n=Convert.ToDouble(raw,CultureInfo.InvariantCulture);
        }
        return double.IsNaN(n)||double.IsInfinity(n)?0:n;
      }catch{return 0;}
    }
    string Bytes(double n){if(n<1024)return Math.Round(n)+" B";if(n<1048576)return (n/1024).ToString("0.0",CultureInfo.InvariantCulture)+" KB";if(n<1073741824)return (n/1048576).ToString("0.0",CultureInfo.InvariantCulture)+" MB";return (n/1073741824).ToString("0.00",CultureInfo.InvariantCulture)+" GB";}
    void SetIndicator(string label,int state){
      indicatorState=state;status.Text=label;
      status.ForeColor=state==0?Color.FromArgb(79,212,161):
        state==1?Color.FromArgb(236,185,65):Color.FromArgb(240,105,105);
      if(state!=0)statusDot.ForeColor=status.ForeColor;
    }
    void RefreshSampleAgeIndicator(){
      if(sampleAgeLabel==null || sampleAgeLabel.IsDisposed)return;
      if(mostRecentAdapterSampleUtc==DateTime.MinValue){
        sampleAgeLabel.Text="Last sample: waiting";
        sampleAgeLabel.ForeColor=muted;
        return;
      }
      double age=(DateTime.UtcNow-mostRecentAdapterSampleUtc).TotalSeconds;
      if(Double.IsNaN(age) || age < -2.0){
        sampleAgeLabel.Text="Sample clock mismatch";
        sampleAgeLabel.ForeColor=Color.FromArgb(236,185,65);
        return;
      }
      age=Math.Max(0.0,age);
      if(age>3.0 && indicatorState==0){
        SetIndicator("Monitoring paused",1);
      }
      if(age>3.0){
        sampleAgeLabel.Text="Stale sample: "+age.ToString("0.0",CultureInfo.InvariantCulture)+"s ago";
        sampleAgeLabel.ForeColor=indicatorState==2?
          Color.FromArgb(240,105,105):Color.FromArgb(236,185,65);
      }else{
        sampleAgeLabel.Text="Last sample: "+age.ToString("0.0",CultureInfo.InvariantCulture)+"s ago";
        sampleAgeLabel.ForeColor=Color.FromArgb(162,191,216);
      }
    }
    void PulseIndicator(){
      RefreshSampleAgeIndicator();
      if(statusDot==null||statusDot.IsDisposed)return;
      if(indicatorState!=0)return;
      indicatorPhase+=0.32;
      double brightness=(Math.Sin(indicatorPhase)+1.0)/2.0;
      statusDot.ForeColor=Color.FromArgb(
        (int)(38+41*brightness),(int)(115+97*brightness),(int)(81+80*brightness));
    }
    void AutoRecoverEngine(){
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
    void CaptureLiveSpeedSample(string stat,long sampleId,DateTime sampleTime,
                                bool timeValid,bool fresh,bool rateValid,
                                double rxBytesPerSecond,double txBytesPerSecond){
      bool newMeasurement=timeValid && sampleId>0 && (sampleId!=lastRecordedGraphSampleId ||
         sampleTime.ToUniversalTime()!=lastRecordedGraphTimeUtc);
      if(newMeasurement){
        DateTime utc=sampleTime.ToUniversalTime();
        if(utc>lastRecordedGraphTimeUtc){
          bool valid=stat=="tracking" && fresh && rateValid &&
                     PlausibleRate(rxBytesPerSecond) && PlausibleRate(txBytesPerSecond);
          liveRateHistory.Add(new LiveRateSample{
            AtUtc=utc,Valid=valid,
            DownloadKbps=valid?rxBytesPerSecond*8.0/1000.0:0,
            UploadKbps=valid?txBytesPerSecond*8.0/1000.0:0
          });
        }else if(utc<lastRecordedGraphTimeUtc){
          // The measurement engine restarted its counter/timestamps.
          // Do not draw a misleading continuous line across that boundary.
          liveRateHistory.Clear();
        }
        lastRecordedGraphSampleId=sampleId;
        lastRecordedGraphTimeUtc=utc;
      }
      liveRateHistory.RemoveAll(x=>x.AtUtc<DateTime.UtcNow.AddSeconds(-100));
      if(showLiveChart && newMeasurement)RenderLiveSpeedGraph();
    }
    void RenderLiveSpeedGraph(){
      if(liveChart==null || !showLiveChart)return;
      var lower=DateTime.UtcNow.AddSeconds(-90);
      var list=liveRateHistory.Where(x=>x.AtUtc>=lower)
         .OrderBy(x=>x.AtUtc).ToList();
      var ca=liveChart.ChartAreas[0];
      double highest=list.Where(x=>x.Valid)
         .Select(x=>Math.Max(x.DownloadKbps,x.UploadKbps)).DefaultIfEmpty(0).Max();
      bool asMbps=highest>=1500.0;
      ca.AxisY.Title=asMbps?"Mbps":"Kbps";
      ca.AxisX.Minimum=DateTime.Now.AddSeconds(-90).ToOADate();
      ca.AxisX.Maximum=DateTime.Now.AddSeconds(2).ToOADate();
      ca.AxisY.Maximum=Double.NaN;
      foreach(var serie in liveChart.Series)serie.Points.Clear();
      LiveRateSample prior=null;
      foreach(var point in list){
        double x=point.AtUtc.ToLocalTime().ToOADate();
        bool gap=prior!=null && (point.AtUtc-prior.AtUtc).TotalSeconds>4;
        if(gap){
          var intermediate=prior.AtUtc.AddSeconds(2).ToLocalTime().ToOADate();
          foreach(var serie in liveChart.Series){
            int j=serie.Points.AddXY(intermediate,0);
            serie.Points[j].IsEmpty=true;
          }
        }
        double scale=asMbps?1000.0:1.0;
        int a=liveChart.Series["Download"].Points.AddXY(x,point.DownloadKbps/scale);
        int b=liveChart.Series["Upload"].Points.AddXY(x,point.UploadKbps/scale);
        if(!point.Valid){
          liveChart.Series["Download"].Points[a].IsEmpty=true;
          liveChart.Series["Upload"].Points[b].IsEmpty=true;
        }
        prior=point;
      }
      var lastValid=list.LastOrDefault(x=>x.Valid);
      chartCaption.Text=lastValid==null?"Waiting for a fresh sample  •  90 sec":
        "Last measured "+lastValid.AtUtc.ToLocalTime().ToString("HH:mm:ss")+
        "  •  last 90 sec  •  "+(asMbps?"Mbps":"Kbps");
    }
    Dictionary<string,object> GetDataFast(){
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
    // DISPLAY ONLY: never modify currentSsid, targetSsid, matching, saved
    // settings, network adapter selection, sampling or user usage history.
    // The user's visible "GLOBALðŸ¤-" is a broken text-decoding suffix.
    // Show the known readable GLOBAL prefix if it is followed by a broken,
    // non-surrogate Unicode tail. Intact UTF-16 emoji remain visible.
    static string HotspotLabel(string raw){
      if(String.IsNullOrWhiteSpace(raw))return "Not connected";
      string name=raw.Trim();

      // Work around variations in Windows code-page decoding of the
      // connected Android hotspot. The plain GLOBAL Wi-Fi label is the
      // requested fallback; this only affects this displayed label.
      if(name.StartsWith("GLOBAL",StringComparison.OrdinalIgnoreCase) &&
         name.Length>6 && name[6]>127 && !Char.IsHighSurrogate(name[6])){
        return name.Substring(0,6);
      }

      // Generic mojibake detection for other SSIDs: when Windows has decoded
      // UTF-8 bytes as ANSI, preserve the readable prefix only.
      int damaged=-1;
      for(int i=0;i<name.Length;i++){
        char c=name[i];
        if(Char.IsHighSurrogate(c)){
          if(i+1<name.Length && Char.IsLowSurrogate(name[i+1])){i++;continue;}
          damaged=i;break;
        }
        if(c=='\uFFFD' || (c>='\u0080' && c<='\u009F')){
          damaged=i;break;
        }
        if((c=='\u00F0' || c=='\u00C3' || c=='\u00E2' || c=='\u00EF') &&
           i+1<name.Length &&
           (name[i+1]>127 || name[i+1]=='?')){
          damaged=i;break;
        }
      }
      if(damaged>0){
        string prefix=name.Substring(0,damaged).TrimEnd();
        if(prefix.Length>0)return prefix;
      }
      return name;
    }
    // PerformanceCounter uses Windows Performance Monitor's per-interface
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
        string requested=requestedCounterAdapter;
        if(nativeCounterAvailable && !String.IsNullOrWhiteSpace(requested) &&
           !String.Equals(nativeCounterAdapter,requested,StringComparison.OrdinalIgnoreCase)){
          DisposeNativeCounters();nativeRetryUtc=DateTime.MinValue;
        }
        if(!nativeCounterAvailable && DateTime.UtcNow<nativeRetryUtc)return;
        if(!nativeCounterAvailable){
          DisposeNativeCounters();
          var adapterName=requested;
          if(String.IsNullOrWhiteSpace(adapterName)){
            nativeRetryUtc=DateTime.UtcNow.AddSeconds(2);return;
          }
          string instance=ResolveNativeInstance(adapterName);
          if(String.IsNullOrEmpty(instance)){
            nativeRetryUtc=DateTime.UtcNow.AddSeconds(20);return;
          }
          nativeRxCounter=new PerformanceCounter("Network Interface","Bytes Received/sec",instance,true);
          nativeTxCounter=new PerformanceCounter("Network Interface","Bytes Sent/sec",instance,true);
          // The first NextValue() only primes a rate counter; never use it.
          nativeRxCounter.NextValue();nativeTxCounter.NextValue();
          nativeCounterAdapter=adapterName;
          nativeCounterAvailable=true;
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
      }catch{
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
    void SetGraphView(int view){
      showLiveChart=view==1;
      showUsageLog=view==2;
      chart.Visible=view==0;
      liveChart.Visible=view==1;
      if(usageGrid!=null)usageGrid.Visible=view==2;
      chartTitle.Text=view==1?"Live speed":view==2?"Usage log":"Daily usage";
      graphToggle.Text=view==1?"Daily usage":"Live speed";
      usageLogToggle.Text=view==2?"Daily usage":"Usage log";
      if(view==1)RenderLiveSpeedGraph();
      else if(view==2){
        chartCaption.Text=usageLogError.Length>0?
          "Log saving error: "+usageLogError:
          "Interval end shown in WAT (UTC+01:00)  •  hover time for range  •  click to open CSV";
        chartCaption.Cursor=Cursors.Hand;
      }else{
        chartCaption.Text="Last 7 days  •  MB";
        chartCaption.Cursor=Cursors.Default;
      }
    }
    const string UsageLogHeader=
      "period_start_local,period_end_local,download_bytes,upload_bytes,total_bytes,today_total_bytes,kind";
    void LoadUsageLog(){
      if(usageGrid==null || !File.Exists(usageLogPath))return;
      try{
        var recent=new Queue<string>();
        foreach(string line in File.ReadLines(usageLogPath)){
          if(line.Length==0 || line==UsageLogHeader)continue;
          recent.Enqueue(line);
          if(recent.Count>150)recent.Dequeue();
        }
        foreach(string line in recent)ShowUsageLogRow(line);
      }catch(Exception ex){usageLogError=ex.Message;}
    }
    static string FormatUsageTime(DateTimeOffset time){
      // Always present the same WAT clock that the user uses in Nigeria.
      return time.ToOffset(UsageZoneOffset).ToString(
        "yyyy-MM-dd hh:mm:ss tt",CultureInfo.InvariantCulture)+" WAT";
    }
    void ShowUsageLogRow(string row){
      if(usageGrid==null)return;
      string[] parts=row.Split(',');
      if(parts.Length!=7)return;
      DateTimeOffset start,end;
      long received,sent,used,running;
      if(!DateTimeOffset.TryParse(parts[0],CultureInfo.InvariantCulture,
           DateTimeStyles.None,out start) ||
         !DateTimeOffset.TryParse(parts[1],CultureInfo.InvariantCulture,
           DateTimeStyles.None,out end) ||
         !long.TryParse(parts[2],NumberStyles.Integer,CultureInfo.InvariantCulture,out received) ||
         !long.TryParse(parts[3],NumberStyles.Integer,CultureInfo.InvariantCulture,out sent) ||
         !long.TryParse(parts[4],NumberStyles.Integer,CultureInfo.InvariantCulture,out used) ||
         !long.TryParse(parts[5],NumberStyles.Integer,CultureInfo.InvariantCulture,out running))return;
      bool baseline=parts[6]=="baseline";
      string period=baseline?"Start":
        Math.Max(0,(int)(end-start).TotalSeconds).ToString(CultureInfo.InvariantCulture)+"s";
      usageGrid.Rows.Insert(0,
        FormatUsageTime(end),
        period,Bytes(received),Bytes(sent),Bytes(used),Bytes(running));
      int index=0;
      usageGrid.Rows[index].Cells[0].ToolTipText=
        baseline?"Starting baseline at "+FormatUsageTime(end)+
          "; no interval usage attributed":
          "Usage measured from "+FormatUsageTime(start)+" to "+
          FormatUsageTime(end)+" (West Africa Time, UTC+01:00)";
      if(usageGrid.Rows.Count>150)
        usageGrid.Rows.RemoveAt(usageGrid.Rows.Count-1);
      usageGrid.ClearSelection();
    }
    void AppendUsageLog(DateTime start,DateTime end,
                        double rxDelta,double txDelta,double todayTotal,bool baseline){
      // The engine already owns usage.json; this is an independent append-only
      // checkpoint ledger based solely on its saved cumulative byte counters.
      long r=(long)Math.Round(Math.Max(0,rxDelta));
      long t=(long)Math.Round(Math.Max(0,txDelta));
      long running=(long)Math.Round(Math.Max(0,todayTotal));
      string entry=String.Join(",",new []{
        new DateTimeOffset(DateTime.SpecifyKind(start,DateTimeKind.Unspecified),
          UsageZoneOffset).ToString("yyyy-MM-ddTHH:mm:sszzz",CultureInfo.InvariantCulture),
        new DateTimeOffset(DateTime.SpecifyKind(end,DateTimeKind.Unspecified),
          UsageZoneOffset).ToString("yyyy-MM-ddTHH:mm:sszzz",CultureInfo.InvariantCulture),
        r.ToString(CultureInfo.InvariantCulture),
        t.ToString(CultureInfo.InvariantCulture),
        (r+t).ToString(CultureInfo.InvariantCulture),
        running.ToString(CultureInfo.InvariantCulture),
        baseline?"baseline":"interval"
      });
      try{
        Directory.CreateDirectory(Path.GetDirectoryName(usageLogPath));
        bool writeHeader=!File.Exists(usageLogPath) ||
           new FileInfo(usageLogPath).Length==0;
        using(var writer=new StreamWriter(usageLogPath,true,new UTF8Encoding(false))){
          if(writeHeader)writer.WriteLine(UsageLogHeader);
          writer.WriteLine(entry);
        }
        usageLogError="";
        ShowUsageLogRow(entry);
        if(showUsageLog)
          chartCaption.Text="Last interval ended "+end.ToString("hh:mm:ss tt",CultureInfo.InvariantCulture)+
            " WAT  •  about 1 minute per row  •  click to open CSV";
      }catch(Exception ex){
        usageLogError=ex.Message;
        if(showUsageLog)chartCaption.Text="Log saving error: "+usageLogError;
      }
    }
    void TrackUsageCheckpoint(string status,bool fresh,long sampleId,
                              DateTime sampleUtc,double rx,double tx){
      if(status!="tracking" || !fresh || sampleId<=0 ||
         sampleUtc==DateTime.MinValue || Double.IsNaN(rx) || Double.IsNaN(tx) ||
         rx<0 || tx<0)return;
      // Deduplicate by the engine's actual sample timestamp, while labeling
      // a checkpoint using the same sample instant in WAT (not repeatedly
      // converting the service timestamp between different timezone kinds).
      DateTime measurementUtc=sampleUtc.ToUniversalTime();
      if(logLastMeasurementUtc!=DateTime.MinValue &&
         measurementUtc<=logLastMeasurementUtc)return;
      logLastMeasurementUtc=measurementUtc;
      DateTime observed=new DateTimeOffset(measurementUtc).ToOffset(UsageZoneOffset).DateTime;
      if(logLastObserved!=DateTime.MinValue && observed<=logLastObserved)return;
      if(logWindowStart==DateTime.MinValue){
        logWindowStart=observed;logLastObserved=observed;
        logWindowRx=rx;logWindowTx=tx;logLastRx=rx;logLastTx=tx;
        AppendUsageLog(observed,observed,0,0,rx+tx,true);
        return;
      }
      if(observed.Date!=logWindowStart.Date){
        // Avoid attributing yesterday's bytes to today's new counters.
        if(logLastObserved>logWindowStart &&
           logLastRx>=logWindowRx && logLastTx>=logWindowTx)
          AppendUsageLog(logWindowStart,logLastObserved,
                         logLastRx-logWindowRx,logLastTx-logWindowTx,
                         logLastRx+logLastTx,false);
        logWindowStart=observed;logWindowRx=rx;logWindowTx=tx;
        logLastObserved=observed;logLastRx=rx;logLastTx=tx;
        AppendUsageLog(observed,observed,0,0,rx+tx,true);
        return;
      }
      if(rx+0.5<logWindowRx || tx+0.5<logWindowTx){
        // Usage was reset or reconfigured; start a new baseline instead of
        // generating a negative or misleading interval.
        logWindowStart=observed;logWindowRx=rx;logWindowTx=tx;
        logLastObserved=observed;logLastRx=rx;logLastTx=tx;
        AppendUsageLog(observed,observed,0,0,rx+tx,true);
        return;
      }
      logLastObserved=observed;logLastRx=rx;logLastTx=tx;
      if((observed-logWindowStart).TotalSeconds>=60.0){
        AppendUsageLog(logWindowStart,observed,rx-logWindowRx,
                       tx-logWindowTx,rx+tx,false);
        logWindowStart=observed;logWindowRx=rx;logWindowTx=tx;
      }
    }
    void ApplyUsage(Dictionary<string,object> d){
      try {string stat=Str(d,"status");if(stat=="tracking")SetIndicator("Monitoring live",0);
        else if(stat=="wrong-network")SetIndicator("Not connected",2);
        else if(stat=="adapter-error")SetIndicator("Adapter disconnected",2);
        else if(stat=="not-configured")SetIndicator("Monitoring paused",1);
        else SetIndicator("Starting monitor",1);
        double rx=Num(d,"todayRx"), tx=Num(d,"todayTx");
        today.Text=Bytes(Num(d,"todayTotal"));down.Text=Bytes(rx);up.Text=Bytes(tx);week.Text=Bytes(Num(d,"sevenDayTotal"));
        long sampleId = (long)Num(d,"rateSampleId");
        bool valid = d.ContainsKey("rateValid") && (Str(d,"rateValid").Equals("True",StringComparison.OrdinalIgnoreCase) || Str(d,"rateValid") == "true");
        DateTime sampleUtc;
        bool timestampValid = DateTime.TryParse(Str(d,"rateSampleTime"), CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out sampleUtc);
        if(timestampValid){
          mostRecentAdapterSampleUtc=sampleUtc.ToUniversalTime();
        }
        RefreshSampleAgeIndicator();
        bool fresh = timestampValid && Math.Abs((DateTime.UtcNow - sampleUtc.ToUniversalTime()).TotalSeconds) <= 3;
        TrackUsageCheckpoint(stat,fresh,sampleId,sampleUtc,rx,tx);
        bool legacyService = stat=="tracking" && !timestampValid;
        if(stat=="tracking" && !fresh)SetIndicator("Monitoring paused",1);
        // Both cards and graph use ONE source for this refresh:
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
        if(speedSourceLabel!=null){
          speedSourceLabel.Text=stat!="tracking"?"Live speed source: not connected":
            useNative?"Live speed source: Windows counters":
            "Live speed source: adapter fallback";
          speedSourceLabel.ForeColor=useNative?Color.FromArgb(79,212,161):
            Color.FromArgb(171,187,207);
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
        }
        if(stat!="tracking"){
          downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
          previousUsageRx=-1;previousUsageTx=-1;previousRateSampleId=-1;
        } else {
          if(legacyService){
            downloadSpeed.Text="Restart service";
            uploadSpeed.Text="Restart service";
            SetIndicator("Old monitoring service",1);
          } else if(liveValid && liveFresh){
            // A fresh measured zero is a real zero.
            downloadSpeed.Text=Rate(rateRx);
            uploadSpeed.Text=Rate(rateTx);
            previousRateSampleId=sampleId;
            previousRateReceivedUtc=nowUtc;
          } else {
            downloadSpeed.Text="Measuring...";
            uploadSpeed.Text="Measuring...";
          }
          previousUsageRx=rx;previousUsageTx=tx;previousUsageReceivedUtc=nowUtc;
        }
        CaptureLiveSpeedSample(stat,liveSampleId,liveSampleUtc,
                               useNative || timestampValid,liveFresh,liveValid,
                               rateRx,rateTx);
        requestedCounterAdapter=stat=="tracking"?Str(d,"adapterName"):"";
        if(signalStrength!=null){
          string strength=Str(d,"wifiSignal");
          signalStrength.Text=stat=="tracking" && !String.IsNullOrWhiteSpace(strength)?strength+"%":"—";
        }
        currentSsid=Str(d,"currentSsid");wifi.Text=HotspotLabel(currentSsid);adapter.Text=Str(d,"adapterName");last.Text=Str(d,"rateSampleTime").Length>0?Str(d,"rateSampleTime"):"No sample yet";
        if(!configured) {hotspot.Text=Str(d,"targetSsid").Length>0?Str(d,"targetSsid"):currentSsid;var selected=Str(d,"adapterName");adapters.Items.Clear();var choices=d.ContainsKey("adapterChoices")?d["adapterChoices"] as System.Collections.ArrayList:null;if(choices!=null)foreach(var x in choices)adapters.Items.Add(Convert.ToString(x));if(adapters.Items.Count==0)adapters.Items.Add("Wi-Fi");adapters.SelectedItem=selected;if(adapters.SelectedIndex<0)adapters.SelectedIndex=0;configured=true;}
        if((DateTime.UtcNow-lastDailyChartRenderUtc).TotalSeconds>=5){
          var map=new Dictionary<string,double>();var days=d.ContainsKey("days")?d["days"] as System.Collections.ArrayList:null;if(days!=null)foreach(var item in days){var row=item as Dictionary<string,object>;if(row!=null)map[Str(row,"date")]=Num(row,"total");}chart.Series[0].Points.Clear();for(int i=6;i>=0;i--){DateTime day=DateTime.Today.AddDays(-i);string k=day.ToString("yyyy-MM-dd");int idx=chart.Series[0].Points.AddY(map.ContainsKey(k)?map[k]/1048576:0);chart.Series[0].Points[idx].AxisLabel=day.ToString("ddd");}
          lastDailyChartRenderUtc=DateTime.UtcNow;
        }
      }catch {
        bool starting=(DateTime.UtcNow-engineLaunchUtc).TotalSeconds<8;
        SetIndicator(starting?"Starting monitor":"Service disconnected",starting?1:2);
        previousRateSampleId=-1;previousUsageRx=-1;previousUsageTx=-1;
        downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
        AutoRecoverEngine();
      }
    }
    void SaveSettings(){string name=hotspot.Text.Trim();if(name.Length==0){MessageBox.Show("Enter your hotspot name.");return;}try{var d=GetData();if(Str(d,"targetSsid").Length>0&&!String.Equals(name,Str(d,"targetSsid"),StringComparison.OrdinalIgnoreCase)){if(MessageBox.Show("Changing the hotspot clears recorded usage. Continue?","Confirm",MessageBoxButtons.YesNo)!=DialogResult.Yes)return;}string body=json.Serialize(new{targetSsid=name,adapterName=adapters.SelectedItem.ToString()});byte[] bytes=Encoding.UTF8.GetBytes(body);var request=(HttpWebRequest)WebRequest.Create(Base+"/api/config");request.Method="POST";request.ContentType="application/json";request.ContentLength=bytes.Length;using(var st=request.GetRequestStream())st.Write(bytes,0,bytes.Length);using(var response=request.GetResponse()){}configured=false;RefreshUsageAsync();MessageBox.Show("Hotspot saved.","T-Net");}catch(Exception ex){MessageBox.Show("Could not save: "+ex.Message);}}
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
    void RenameShortcuts(){
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
    void ShowWindow(){Show();WindowState=FormWindowState.Normal;Activate();}
    void Quit(){closing=true;refreshTimer.Stop();if(indicatorTimer!=null)indicatorTimer.Stop();
      if(liveCounterTimer!=null){liveCounterTimer.Dispose();liveCounterTimer=null;}
      lock(liveCounterLock){DisposeNativeCounters();}try{if(engine!=null&&!engine.HasExited)engine.Kill();}catch{}tray.Visible=false;tray.Dispose();Close();}
    [STAThread] static void Main(string[] args){bool created;using(var mutex=new Mutex(true,"Local\\AirtelDataMonitorDesktopV3",out created)){if(!created){MessageBox.Show("T-Net is already running. Open it from the system tray.");return;}Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new MainForm(args.Any(a=>a=="--share")));}}
  }
}
