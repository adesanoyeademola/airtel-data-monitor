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
using Microsoft.Win32;
using System.Drawing.Drawing2D;
using System.Web.Script.Serialization;
using System.Windows.Forms.DataVisualization.Charting;

namespace AirtelMonitorNative {
  public class MainForm : Form {
    readonly string root = AppDomain.CurrentDomain.BaseDirectory;
    Process engine;
    NotifyIcon tray;
    // Tray mini-popup: presentation only. Reuses the main dashboard's
    // already-polled Wi-Fi signal and never starts another monitoring service.
    Form signalTrayPopup;
    Label signalTrayStatus,signalTrayAdapter,signalTrayPercent;
    Panel signalTrayTrack,signalTrayFill;
    string signalTrayLastAdapter="";
    string signalTrayLastStatus="Waiting for connection";
    int? signalTrayLastPercent=null;
    bool signalTrayConnected=false;
    DateTime signalTrayLastAutoHideUtc=DateTime.MinValue;
    System.Windows.Forms.Timer refreshTimer;
    JavaScriptSerializer json = new JavaScriptSerializer();
    Label status, statusDot, sampleAgeLabel, speedSourceLabel, wifi, adapter, signalStrength, last, today, down, up, downloadSpeed, uploadSpeed;
    Panel signalStrengthTrack, signalStrengthFill;
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
    const string AppVersion = "6.31.0";
    Button updateButton;
    const string UpdatesFileName = "updates.txt";
    TextBox hotspot;
    ComboBox adapters;
    Chart chart, liveChart;
    Button graphToggle,dayUsageButton,weekUsageButton,monthUsageButton;
    ComboBox chartViewDropdown;
    bool syncingChartViewDropdown=false;
    int currentUsageView=0; // 0 daily, 3 weekly, 4 monthly
    double latestTodayConsumed=0,latestSevenDayConsumed=0,latestMonthConsumed=0;
    Label downloadArrow,uploadArrow;
    bool downloadArrowMoving=false,uploadArrowMoving=false;
    int telemetryAnimationFrame=0;
    int pulseAnimationFrame=0;
    int? dashboardSignalPercent=null;
    Label nordicSignalMetric;
    Label nordicTodayStat,nordicWeekStat,nordicMonthStat;
    Panel nordicSidebar,nordicNetworkPanel;
    FlowLayoutPanel nordicAppearanceStrip;
    Button nordicLightButton,nordicDarkButton,nordicAutoButton;
    Button nordicSelectedNav;
    readonly List<Button> nordicNavButtons=new List<Button>();
    readonly Dictionary<string,double> existingDailyValues=new Dictionary<string,double>();
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
    string appearanceMode="light";
    bool appearanceIsLight=false;
    Button appearanceButton;
    ContextMenuStrip appearanceMenu;
    DateTime nextSystemThemeCheck=DateTime.MinValue;
    readonly string appearanceFile=Path.Combine(
      Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
      "AirtelDataMonitor","appearance.txt");
    static readonly Color darkBg=Color.FromArgb(8,20,41);
    static readonly Color darkPanel=Color.FromArgb(22,41,73);
    static readonly Color darkInk=Color.FromArgb(242,248,255);
    static readonly Color darkMuted=Color.FromArgb(185,203,230);
    static readonly Color lightBg=Color.FromArgb(242,246,252);
    static readonly Color lightPanel=Color.White;
    static readonly Color lightInk=Color.FromArgb(25,39,56);
    static readonly Color lightMuted=Color.FromArgb(94,110,133);
    public MainForm(bool shareMode) {
      share = shareMode;
      Text = "T-Net"; StartPosition = FormStartPosition.CenterScreen; MinimumSize = new Size(1120, 700); Size = new Size(1510, 840); BackColor = bg; ForeColor = ink; Font = new Font("Segoe UI", 10);
      try { string ico=Path.Combine(root,"airtel-monitor.ico"); if(File.Exists(ico)) Icon=new Icon(ico); }catch{}
      LoadAppearanceChoice();
      BuildUi();
      ApplyAppearance(true);
      LoadUsageLog();
      // The explicit "Restart service" warning is also an action users can click.
      downloadSpeed.Cursor=Cursors.Hand;uploadSpeed.Cursor=Cursors.Hand;
      downloadSpeed.Click+=(sender,e)=>{if(downloadSpeed.Text=="Restart service")RestartEngine();};
      uploadSpeed.Click+=(sender,e)=>{if(uploadSpeed.Text=="Restart service")RestartEngine();};
      tray = new NotifyIcon(); tray.Icon = Icon ?? SystemIcons.Application; tray.Text = "T-Net"; tray.Visible = true;
      var menu = new ContextMenuStrip(); menu.Items.Add("Open monitor", null, (s,e)=>ShowWindow()); menu.Items.Add("Restart monitoring service", null, (s,e)=>RestartEngine()); menu.Items.Add("Exit monitor", null, (s,e)=>Quit()); var appearanceItem=new ToolStripMenuItem("Appearance");
      appearanceItem.DropDownItems.Add("Light",null,(sender,e)=>SelectAppearance("light"));
      appearanceItem.DropDownItems.Add("Dark",null,(sender,e)=>SelectAppearance("dark"));
      appearanceItem.DropDownItems.Add("Follow Windows",null,(sender,e)=>SelectAppearance("system"));
      menu.Items.Insert(2,appearanceItem);
      tray.ContextMenuStrip=menu;
      tray.MouseClick+=(sender,e)=>{
        if(e.Button==MouseButtons.Left)ToggleSignalTrayPopup();
      };
      // Preserve the existing double-click shortcut for the main monitor.
      tray.DoubleClick+=(s,e)=>ShowWindow();
      FormClosing+=(s,e)=>{ if(!closing){e.Cancel=true; Hide();} };
      Shown+=(s,e)=>{RenameShortcuts();StartEngine();};
      // Silent release-feed check after startup, if the user has configured a trusted feed.
      var backgroundUpdateTimer = new System.Windows.Forms.Timer {Interval = 60000};
      backgroundUpdateTimer.Tick += async (sender,e)=> {backgroundUpdateTimer.Stop();await CheckUpdates(true);backgroundUpdateTimer.Interval=21600000;backgroundUpdateTimer.Start();};
      backgroundUpdateTimer.Start();
      refreshTimer = new System.Windows.Forms.Timer(); refreshTimer.Interval = 500; refreshTimer.Tick+=(s,e)=>{RefreshUsageAsync();CheckSystemAppearance();}; refreshTimer.Start();
      indicatorTimer = new System.Windows.Forms.Timer{Interval=100};
      indicatorTimer.Tick+=(s,e)=>{PulseIndicator();AnimateTelemetry();};indicatorTimer.Start();
      // PDH measurements are sampled off the UI thread. Failure is nonfatal
      // and automatically falls back to the existing direct adapter rates.
      liveCounterTimer=new System.Threading.Timer(SampleNativeCounters,null,350,1000);
    }
    Label LabelText(string s,int size=11,bool bold=false) { return new Label { Text=s, AutoSize=true, ForeColor=ink, Font=new Font("Segoe UI",size,bold?FontStyle.Bold:FontStyle.Regular), Margin=new Padding(0,0,0,4) }; }
    void PaintReferenceSidebar(Graphics g,Rectangle bounds){
      if(bounds.Width<2||bounds.Height<2)return;
      using(var brush=new LinearGradientBrush(bounds,
        appearanceIsLight?Color.FromArgb(238,245,255):Color.FromArgb(17,54,110),
        appearanceIsLight?Color.FromArgb(231,240,253):Color.FromArgb(9,33,73),90f))
        g.FillRectangle(brush,bounds);
    }
    Panel PanelCard() {
      var card=new Panel{BackColor=panel,Dock=DockStyle.Fill,
        Padding=new Padding(17),Margin=new Padding(7),Tag="tnet-card"};
      card.Resize+=(sender,e)=>RoundSurface(card,20);
      card.Paint+=(sender,e)=>{
        if(card.Width<5||card.Height<5)return;
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        using(var path=RoundedPath(new Rectangle(1,1,card.Width-3,card.Height-3),20))
        using(var pen=new Pen(appearanceIsLight?
          Color.FromArgb(219,230,247):Color.FromArgb(49,77,122),1.1f))
          e.Graphics.DrawPath(pen,path);
      };
      return card;
    }
    void BuildUi(){
      var outer=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=1,
        RowCount=6, Padding=new Padding(11,11,11,29), BackColor=bg };
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,76));
      outer.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,22));
      var shell=new TableLayoutPanel{
        Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,
        Margin=new Padding(0),Padding=new Padding(0),BackColor=bg
      };
      shell.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,228));
      shell.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      nordicSidebar=CreateNordicSidebar();
      shell.Controls.Add(nordicSidebar,0,0);
      shell.Controls.Add(outer,1,0);
      Controls.Add(shell);
      var head=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=2 };
      head.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,0));
      head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      head.Controls.Add(new Label {Text="",Dock=DockStyle.Fill,Margin=new Padding(0)},0,0);
      status=new Label {Text="Starting monitor...",Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleRight,ForeColor=muted};head.Controls.Add(status,1,0);
      statusDot=new Label{Text="●",AutoSize=true,ForeColor=Color.FromArgb(236,185,65),
         Font=new Font("Segoe UI",14,FontStyle.Bold),TextAlign=ContentAlignment.MiddleCenter,
         Margin=new Padding(2,9,2,0)};
      updateButton = new Button {Text="Check for updates",Width=136,Height=34,Anchor=AnchorStyles.None,Margin=new Padding(3,3,3,3),BackColor=Color.FromArgb(32,46,68),ForeColor=Color.White,FlatStyle=FlatStyle.Flat};
      updateButton.FlatAppearance.BorderColor=Color.FromArgb(49,65,86);
      var headerActions = new FlowLayoutPanel {Dock=DockStyle.Fill,FlowDirection=FlowDirection.RightToLeft,WrapContents=false};
      status.AutoSize=true;status.Dock=DockStyle.None;status.Margin=new Padding(2,11,7,0);headerActions.Controls.Add(updateButton);
      // Full-size, labeled rounded selector, aligned to Check for updates.
      // Do not reduce other app controls or use an ambiguous standalone icon.
      appearanceButton=new Button{
        Text="Appearance  ▾",Width=125,Height=34,
        BackColor=Color.FromArgb(32,46,68),ForeColor=ink,
        FlatStyle=FlatStyle.Flat,Margin=new Padding(3,3,3,3),
        TextAlign=ContentAlignment.MiddleCenter,
        Font=new Font("Segoe UI",9,FontStyle.Regular)
      };
      appearanceButton.FlatAppearance.BorderSize=1;
      appearanceButton.FlatAppearance.BorderColor=Color.FromArgb(49,65,86);
      appearanceButton.Resize+=(sender,e)=>ShapeAppearanceButton();
      var appearanceTip=new ToolTip();
      appearanceTip.SetToolTip(appearanceButton,"Choose Light, Dark or Follow Windows");
      appearanceButton.Click+=(sender,e)=>ShowAppearanceMenu();
      nordicAppearanceStrip=new FlowLayoutPanel{
        Width=246,Height=36,Margin=new Padding(4,2,4,2),
        WrapContents=false,FlowDirection=FlowDirection.LeftToRight,
        Padding=new Padding(3),BackColor=Color.FromArgb(229,238,251)
      };
      nordicLightButton=NordicModeButton("☀  Light","light");
      nordicDarkButton=NordicModeButton("☾  Dark","dark");
      nordicAutoButton=NordicModeButton("◐  Auto","system");
      nordicAppearanceStrip.Controls.Add(nordicLightButton);
      nordicAppearanceStrip.Controls.Add(nordicDarkButton);
      nordicAppearanceStrip.Controls.Add(nordicAutoButton);
      // Match the reference: one polished Appearance dropdown in the header.
      // Preserve the three existing mode choices inside that dropdown.
      appearanceButton.Text="◐ Appearance  ▾";
      appearanceButton.Width=147;
      headerActions.Controls.Add(appearanceButton);
      // Keep the update action visually readable even while checking.
      updateButton.BackColor=Color.FromArgb(38,57,81);
      updateButton.ForeColor=Color.White;
      updateButton.Font=new Font("Segoe UI",9,FontStyle.Regular);
      updateButton.Resize+=(sender,e)=>RoundSurface(updateButton,12);
      RoundSurface(updateButton,12);
      ShapeAppearanceButton();headerActions.Controls.Add(updateButton);
      var statusLine=new FlowLayoutPanel{
        FlowDirection=FlowDirection.LeftToRight,WrapContents=false,
        Width=152,Height=34,Margin=new Padding(3,3,1,3),Padding=new Padding(0)
      };
      status.AutoSize=true;status.Dock=DockStyle.None;
      status.Margin=new Padding(0,8,0,0);
      statusDot.Margin=new Padding(0,7,4,0);
      statusLine.Controls.Add(statusDot);
      statusLine.Controls.Add(status);
      headerActions.Controls.Add(statusLine);
      // Right-to-left layout: Appearance, then updates, then status.
      headerActions.Controls.SetChildIndex(statusLine,0);
      headerActions.Controls.SetChildIndex(updateButton,1);
      // RTL FlowLayoutPanel child ordering is reverse visual ordering.
      // Left-to-right result: Monitoring live | Appearance | Check for updates.
      headerActions.Controls.SetChildIndex(updateButton,0);
      headerActions.Controls.SetChildIndex(appearanceButton,1);
      headerActions.Controls.SetChildIndex(statusLine,2);
      head.Controls.Remove(status);head.Controls.Add(headerActions,1,0);
      updateButton.Click += async (sender,e)=>await CheckUpdates(false);
      // The speed values join Appearance and update controls in the same row.
      // Compact coloured direction arrows stay visible as values refresh.
      // Speed displays are now in their dashboard cards below.
      // No speed pills are inserted alongside Monitoring live.
      outer.Controls.Add(head,0,0);
      var metrics=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=3,
        Margin=new Padding(0),Padding=new Padding(0)};
      for(int i=0;i<3;i++)metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100f/3));
      // Keep the Today label as a hidden data target for the existing engine.
      // The reference uses a consumption caption beneath the chart instead.
      today=new Label{Visible=false};
      down=ArrowSpeedCard(metrics,"Download speed",0,"↓",Color.FromArgb(65,156,235));
      up=ArrowSpeedCard(metrics,"Upload speed",1,"↑",Color.FromArgb(52,180,137));
      downloadSpeed=down;uploadSpeed=up;
      nordicSignalMetric=Metric(metrics,"Wi-Fi signal",2);
      nordicSignalMetric.Font=new Font("Segoe UI",19,FontStyle.Bold);
      nordicSignalMetric.Text="—";
      nordicSignalMetric.ForeColor=ink;
      // Metrics now belong to the upper-left body cell, not a full-width row.
      var middle=new TableLayoutPanel{Dock=DockStyle.Fill,
        ColumnCount=2,RowCount=2,Margin=new Padding(0),Padding=new Padding(0)};
      middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,66));
      middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,34));
      middle.RowStyles.Add(new RowStyle(SizeType.Absolute,143));
      middle.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      middle.Controls.Add(metrics,0,0);
      var net=PanelCard();
      net.Padding=new Padding(15,16,14,16);
      nordicNetworkPanel=net;
      var layoutNetwork=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=4,Margin=new Padding(0)};
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,32));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,76));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      var networkTitle=LabelText("Network",17,true);
      networkTitle.Dock=DockStyle.Fill;
      networkTitle.Margin=new Padding(0);
      networkTitle.TextAlign=ContentAlignment.MiddleLeft;
      var networkHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,Margin=new Padding(0)};
      networkHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,42));
      networkHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,58));
      sampleAgeLabel=new Label{
        Text="Last sample: waiting",Dock=DockStyle.Fill,
        TextAlign=ContentAlignment.MiddleRight,ForeColor=muted,
        Font=new Font("Segoe UI",9),AutoEllipsis=true
      };
      networkHeader.Padding=new Padding(0);
      networkTitle.Padding=new Padding(0);
      networkHeader.Controls.Add(networkTitle,0,0);
      networkHeader.Controls.Add(sampleAgeLabel,1,0);
      layoutNetwork.Controls.Add(networkHeader,0,0);
      var hotspotHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=3,Margin=new Padding(0)};
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,25));
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,34));
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,27));
      var hotspotCaption=LabelText("Hotspot");
      hotspotCaption.Dock=DockStyle.Fill;
      hotspotCaption.Margin=new Padding(0);
      hotspotCaption.TextAlign=ContentAlignment.MiddleLeft;
      hotspotHeader.Padding=new Padding(0);
      hotspotCaption.Padding=new Padding(0);
      hotspotHeader.Controls.Add(hotspotCaption,0,0);
      wifi=LabelText("—",12,true);wifi.AutoEllipsis=true;wifi.AutoSize=false;wifi.Dock=DockStyle.Fill;
      wifi.Margin=new Padding(0);
      wifi.Padding=new Padding(0);
      hotspotHeader.Controls.Add(wifi,0,1);layoutNetwork.Controls.Add(hotspotHeader,0,1);
      // Pinned directly after the GLOBAL hotspot, immediately before Adapter.
      speedSourceLabel=new Label{
        Text="Live speed source: checking...",AutoSize=true,ForeColor=muted,
        Font=new Font("Segoe UI",9),Margin=new Padding(0,0,0,2)
      };
      hotspotHeader.Controls.Add(speedSourceLabel,0,2);
      // Keep the three essential live network readings permanently visible.
      // Only the lower, optional details remain in the original scroll area.
      var pinnedDetails=new TableLayoutPanel{
        Dock=DockStyle.Fill,ColumnCount=1,RowCount=6,
        AutoScroll=false,Margin=new Padding(0),Padding=new Padding(0),
        GrowStyle=TableLayoutPanelGrowStyle.FixedSize
      };
      pinnedDetails.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,23)); // Adapter label
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,28)); // Adapter value
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,24)); // Signal label
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,40)); // Pulse and percentage
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,32)); // Last update dropdown
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,0));  // Expanded timestamp
      var adapterCaption=LabelText("Adapter",11);
      adapterCaption.Margin=new Padding(0,1,0,1);
      adapterCaption.Dock=DockStyle.Fill;
      pinnedDetails.Controls.Add(adapterCaption,0,0);
      adapter=LabelText("—",13,true);adapter.Margin=new Padding(0);
      adapter.Dock=DockStyle.Fill;
      pinnedDetails.Controls.Add(adapter,0,1);
      var signalCaption=LabelText("Wi-Fi signal strength",11);
      signalCaption.Margin=new Padding(0,0,0,2);
      signalCaption.Dock=DockStyle.Fill;
      pinnedDetails.Controls.Add(signalCaption,0,2);
      // A thin, color-coded Wi-Fi quality line. The percentage still comes
      // exclusively from Windows via the existing monitor.ps1 API.
      var signalRow=new FlowLayoutPanel{
        Width=306,Height=25,AutoSize=false,WrapContents=false,
        FlowDirection=FlowDirection.LeftToRight,
        Margin=new Padding(0,1,0,1),Padding=new Padding(0)
      };
      signalStrengthTrack=new Panel{
        Width=210,Height=9,BackColor=Color.FromArgb(49,65,86),
        Margin=new Padding(5,8,7,0)
      };
      signalStrengthFill=new Panel{
        Width=0,Height=9,BackColor=Color.FromArgb(79,212,161),
        Location=new Point(0,0),Margin=new Padding(0)
      };
      signalStrengthTrack.Controls.Add(signalStrengthFill);
      signalStrengthFill.Visible=false;
      signalStrengthTrack.Height=25;
      signalStrengthTrack.Margin=new Padding(5,0,7,0);
      signalStrengthTrack.Paint+=(sender,e)=>
        DrawSignalPulse(e.Graphics,signalStrengthTrack.ClientRectangle,dashboardSignalPercent);
      signalStrength=LabelText("—",12,true);
      signalStrength.AutoSize=false;
      signalStrength.Width=68;
      signalStrength.Height=25;
      signalStrength.TextAlign=ContentAlignment.MiddleLeft;
      signalStrength.Margin=new Padding(0);
      signalRow.Controls.Add(signalStrengthTrack);
      signalRow.Controls.Add(signalStrength);
      Action fitNordicSignal=()=>{
        if(net==null || signalStrengthTrack==null)return;
        int usable=Math.Max(90,net.ClientSize.Width-net.Padding.Horizontal-90);
        signalStrengthTrack.Width=Math.Min(210,usable);
        signalRow.Width=Math.Max(175,signalStrengthTrack.Width+84);
      };
      net.SizeChanged+=(sender,e)=>fitNordicSignal();
      fitNordicSignal();
      signalRow.Height=38;
      signalRow.Margin=new Padding(0);
      signalStrengthTrack.Height=32;
      signalStrengthTrack.Margin=new Padding(5,1,7,0);
      signalStrength.Height=32;
      signalRow.Dock=DockStyle.Fill;
      signalRow.AutoScroll=false;
      pinnedDetails.Controls.Add(signalRow,0,3);
      layoutNetwork.Controls.Add(pinnedDetails,0,2);
      pinnedDetails.BringToFront();
      // Keep the scroll area intact for timestamp and further details.
      // Genuine, permanently visible WinForms scrollbar. AutoScroll alone
      // disappears when the parent layout is maximized or the viewport
      // becomes too small to expose its native scrolling area.
      var detailViewport=new Panel{
        Dock=DockStyle.Fill,AutoScroll=false,
        Margin=new Padding(0),Padding=new Padding(0)
      };
      var detailScroll=new FlowLayoutPanel{
        FlowDirection=FlowDirection.TopDown,WrapContents=false,
        AutoScroll=false,Margin=new Padding(0),Padding=new Padding(0),
        Location=new Point(0,0),AutoSize=false
      };
      detailViewport.Controls.Add(detailScroll);
      var detailBar=new VScrollBar{
        Width=SystemInformation.VerticalScrollBarWidth,
        Height=66,SmallChange=16,LargeChange=30,
        Minimum=0,Maximum=320,Visible=true,
        Anchor=AnchorStyles.Right|AnchorStyles.Bottom
      };
      // Real scrollbar movement updates the clipped detail content position.
      // Decorative scrollbar only. Network details no longer scroll.
      detailBar.Enabled=false;
      detailBar.ValueChanged+=(sender,e)=>{ /* intentionally non-interactive */ };
      Action syncDetails=()=>{
        int viewportWidth=Math.Max(1,detailViewport.ClientSize.Width);
        int viewportHeight=Math.Max(1,detailViewport.ClientSize.Height);
        detailScroll.Width=viewportWidth;
        detailScroll.Height=320;
        // The hidden legacy viewport is empty; no reveal spacer required.
        detailScroll.PerformLayout();
        int contentHeight=0;
        foreach(Control c in detailScroll.Controls)
          contentHeight=Math.Max(contentHeight,c.Bottom+c.Margin.Bottom);
        contentHeight=Math.Max(contentHeight,viewportHeight);
        detailScroll.Height=contentHeight;
        int scrollMax=Math.Max(0,contentHeight-viewportHeight);
        detailBar.LargeChange=Math.Max(1,Math.Min(30,viewportHeight));
        detailBar.Maximum=scrollMax+detailBar.LargeChange-1;
        if(detailBar.Value>scrollMax)detailBar.Value=scrollMax;
        detailScroll.Top=-detailBar.Value;
        // The real scrollbar stays visible, even when there is nothing
        // further to scroll. Do not fake or synthesize scrollable data.
        // Keep scrollbar permanently decorative even after resizing.
        detailBar.Enabled=false;
      };
      detailViewport.SizeChanged+=(sender,e)=>syncDetails();
      // This spacer is relative to the view height, so optional details
      // remain below the fold even when the window is maximized.
      // Previously used to keep Last update off-screen; no longer necessary.
      // No artificial blank scroll fold in the expanded Network card.
      var lastUpdateDisclosure=new Button{Text="▸ Last update",AutoSize=false,
        Width=224,Height=34,Margin=new Padding(0,12,0,0),
        TextAlign=ContentAlignment.MiddleLeft,FlatStyle=FlatStyle.Flat,
        BackColor=Color.FromArgb(32,46,68),ForeColor=ink,
        Font=new Font("Segoe UI",10)};
      lastUpdateDisclosure.FlatAppearance.BorderSize=0;
      last=LabelText("—",10);last.AutoSize=false;
      last.Width=224;last.Height=27;last.Visible=false;
      lastUpdateDisclosure.Click+=(sender,e)=>{
        last.Visible=!last.Visible;
        pinnedDetails.RowStyles[5].Height=last.Visible?27:0;
        lastUpdateDisclosure.Text=last.Visible?"▾ Last update":"▸ Last update";
        pinnedDetails.PerformLayout();
        pinnedDetails.Invalidate(true);
      };
      lastUpdateDisclosure.Dock=DockStyle.Fill;
      lastUpdateDisclosure.Margin=new Padding(0,1,0,1);
      lastUpdateDisclosure.Padding=new Padding(0);
      lastUpdateDisclosure.TabStop=true;
      last.Dock=DockStyle.Fill;
      last.Margin=new Padding(0);
      pinnedDetails.Controls.Add(lastUpdateDisclosure,0,4);
      pinnedDetails.Controls.Add(last,0,5);
      // Redundant "Scroll for more details" label removed; keep the real scrollbar.
      layoutNetwork.Controls.Add(detailViewport,0,3);
      net.Controls.Add(layoutNetwork);
      // Dock the actual vertical scroll control at the lower right of the
      // Network card, independent of the potentially clipped details row.
      net.Controls.Add(detailBar);
      Action positionDetailBar=()=>{
        detailBar.Location=new Point(
          Math.Max(0,net.ClientSize.Width-net.Padding.Right-detailBar.Width-4),
          Math.Max(0,net.ClientSize.Height-net.Padding.Bottom-detailBar.Height+3));
        detailBar.BringToFront();
        detailBar.TabStop=false;
      };
      net.SizeChanged+=(sender,e)=>{positionDetailBar();syncDetails();};
      positionDetailBar();
      syncDetails();
      var networkDock=new TableLayoutPanel{
        Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,
        Margin=new Padding(0),Padding=new Padding(0),
        BackColor=bg
      };
      networkDock.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      networkDock.RowStyles.Add(new RowStyle(SizeType.Absolute,330));
      networkDock.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      net.Dock=DockStyle.Fill;
      var usageSummary=PanelCard();
      usageSummary.Padding=new Padding(15,14,15,12);
      var summaryGrid=new TableLayoutPanel{
        Dock=DockStyle.Top,ColumnCount=2,RowCount=4,Height=186,
        Margin=new Padding(0),Padding=new Padding(0)
      };
      summaryGrid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,53));
      summaryGrid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,47));
      summaryGrid.RowStyles.Add(new RowStyle(SizeType.Absolute,42));
      for(int i=0;i<3;i++)summaryGrid.RowStyles.Add(new RowStyle(SizeType.Absolute,46));
      summaryGrid.Controls.Add(new Label{
        Text="Usage overview",Dock=DockStyle.Fill,
        Font=new Font("Segoe UI",14,FontStyle.Bold),
        ForeColor=ink,TextAlign=ContentAlignment.MiddleLeft},0,0);
      summaryGrid.SetColumnSpan(summaryGrid.GetControlFromPosition(0,0),2);
      string[] summaryTitles={"Today","Last 7 days","This month"};
      var summaryValues=new List<Label>();
      for(int i=0;i<3;i++){
        summaryGrid.Controls.Add(new Label{
          Text=summaryTitles[i],Dock=DockStyle.Fill,
          Font=new Font("Segoe UI",10),
          ForeColor=muted,TextAlign=ContentAlignment.MiddleLeft},0,i+1);
        var value=new Label{
          Text="0 B",Dock=DockStyle.Fill,
          Font=new Font("Segoe UI",11,FontStyle.Bold),
          ForeColor=ink,TextAlign=ContentAlignment.MiddleRight};
        summaryValues.Add(value);
        summaryGrid.Controls.Add(value,1,i+1);
      }
      nordicTodayStat=summaryValues[0];
      nordicWeekStat=summaryValues[1];
      nordicMonthStat=summaryValues[2];
      usageSummary.Controls.Add(summaryGrid);
      networkDock.Controls.Add(net,0,0);
      networkDock.Controls.Add(usageSummary,0,1);
      middle.Controls.Add(networkDock,1,0);
      middle.SetRowSpan(networkDock,2);
      Action fitNetworkCard=()=>{
        int available=Math.Max(300,networkDock.ClientSize.Height);
        networkDock.RowStyles[0].Height=Math.Max(260,Math.Min(380,available-205));
      };
      networkDock.SizeChanged+=(sender,e)=>fitNetworkCard();
      fitNetworkCard();
      var chPanel=PanelCard();
      chPanel.Padding=new Padding(14,15,14,13);
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
      for(int i=0;i<3;i++)graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100f/3));
      // Live speed and Usage log move to the chart footer dropdown.
      dayUsageButton=UsagePeriodButton("Daily usage",0);
      weekUsageButton=UsagePeriodButton("Weekly usage",3);
      monthUsageButton=UsagePeriodButton("Monthly usage",4);
      graphHeader.Controls.Add(dayUsageButton,0,0);
      graphHeader.Controls.Add(weekUsageButton,1,0);
      graphHeader.Controls.Add(monthUsageButton,2,0);
      foreach(var tab in new[]{dayUsageButton,weekUsageButton,monthUsageButton}){
        tab.Font=new Font("Segoe UI",9,FontStyle.Regular);
        tab.Margin=new Padding(3,3,3,3);
        tab.FlatAppearance.BorderSize=0;
        tab.Resize+=(sender,e)=>RoundSurface(tab,12);
        RoundSurface(tab,12);
      }
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
      chartCaption=new Label{Text="Today's usage: 0 B",Dock=DockStyle.Fill,ForeColor=muted,
        Font=new Font("Segoe UI",8),TextAlign=ContentAlignment.MiddleLeft};
      chartCaption.Click+=(sender,e)=>{
        if(!showUsageLog || !File.Exists(usageLogPath))return;
        try{Process.Start("explorer.exe","/select,\""+usageLogPath+"\"");}
        catch(Exception err){MessageBox.Show("Could not open usage log: "+err.Message);}
      };
      chartViewDropdown=new ComboBox{
        DropDownStyle=ComboBoxStyle.DropDownList,Width=132,
        Dock=DockStyle.Fill,Margin=new Padding(3,0,3,0),
        Font=new Font("Segoe UI",9),
        BackColor=panel,ForeColor=ink
      };
      chartViewDropdown.Items.AddRange(new object[]{"Usage chart","Live speed","Usage log"});
      chartViewDropdown.SelectedIndex=0;
      chartViewDropdown.SelectedIndexChanged+=(sender,e)=>{
        if(syncingChartViewDropdown)return;
        int selection=chartViewDropdown.SelectedIndex;
        SetGraphView(selection==1?1:selection==2?2:currentUsageView);
      };
      var chartFooter=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,
        Margin=new Padding(0)};
      chartFooter.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      chartFooter.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,139));
      chartFooter.Controls.Add(chartCaption,0,0);
      chartFooter.Controls.Add(chartViewDropdown,1,0);
      var graphLayout=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=3,ColumnCount=1};
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,40));
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,22));
      graphLayout.Controls.Add(graphHeader,0,0);
      graphLayout.Controls.Add(graphSurface,0,1);
      graphLayout.Controls.Add(chartFooter,0,2);
      graphLayout.RowStyles.Clear();
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,43));
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,40));
      chartFooter.Padding=new Padding(0,3,0,0);
      chartFooter.Margin=new Padding(0);
      chPanel.Controls.Add(graphLayout);middle.Controls.Add(chPanel,0,1);
      outer.Controls.Add(middle,0,1);
      settings=PanelCard();var section=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=4,RowCount=2};section.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,28));section.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,28));section.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,22));section.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,22));section.RowStyles.Add(new RowStyle(SizeType.Absolute,40));section.RowStyles.Add(new RowStyle(SizeType.Absolute,50));section.Controls.Add(LabelText("Hotspot settings",15,true),0,0);section.SetColumnSpan(section.GetControlFromPosition(0,0),4);
      hotspot=new TextBox{Dock=DockStyle.Fill,Margin=new Padding(5),BackColor=bg,ForeColor=ink,BorderStyle=BorderStyle.FixedSingle};section.Controls.Add(hotspot,0,1);
      adapters=new ComboBox{Dock=DockStyle.Fill,DropDownStyle=ComboBoxStyle.DropDownList,Margin=new Padding(5),BackColor=bg,ForeColor=ink};adapters.Items.Add("Wi-Fi");adapters.SelectedIndex=0;section.Controls.Add(adapters,1,1);
      var choose=new Button{Text="Use current Wi-Fi",Dock=DockStyle.Fill,Margin=new Padding(5)};choose.Click+=(s,e)=>{if(!String.IsNullOrEmpty(currentSsid))hotspot.Text=currentSsid;};section.Controls.Add(choose,2,1);
      var save=new Button{Text="Save hotspot",Dock=DockStyle.Fill,Margin=new Padding(5),BackColor=accent,ForeColor=Color.White,FlatStyle=FlatStyle.Flat};save.Click+=(s,e)=>SaveSettings();section.Controls.Add(save,3,1);settings.Controls.Add(section);
      outer.Controls.Add(new Label{Dock=DockStyle.Fill,Text="Monitoring runs while this app is open or minimized to the tray.",ForeColor=muted,TextAlign=ContentAlignment.MiddleLeft,Font=new Font("Segoe UI",9),Margin=new Padding(8,0,0,0)},0,5);
    }
    Label Metric(TableLayoutPanel parent,string name,int col) {var p=PanelCard();var stack=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=2};stack.RowStyles.Add(new RowStyle(SizeType.Percent,40));stack.RowStyles.Add(new RowStyle(SizeType.Percent,60));Color labelColor=name=="Today"?Color.FromArgb(135,115,211):
        name=="Download speed"?Color.FromArgb(66,149,220):
        name=="Upload speed"?Color.FromArgb(45,168,127):
        name=="Wi-Fi signal"?Color.FromArgb(33,167,135):
        Color.FromArgb(207,149,55);
      stack.Controls.Add(new Label {Text=name,Dock=DockStyle.Fill,
        ForeColor=labelColor,TextAlign=ContentAlignment.MiddleLeft},0,0);var val=new Label{Text="0 B",Dock=DockStyle.Fill,ForeColor=ink,Font=new Font("Segoe UI",22,FontStyle.Bold),TextAlign=ContentAlignment.MiddleLeft};stack.Controls.Add(val,0,1);p.Controls.Add(stack);parent.Controls.Add(p,col,0);return val;}
    Label ArrowSpeedCard(TableLayoutPanel parent,string name,int col,string arrow,Color color){
      var card=PanelCard();
      card.Padding=new Padding(18);
      var stack=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,
        Margin=new Padding(0),Padding=new Padding(0)};
      stack.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,75));
      stack.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      var circle=new Panel{Size=new Size(62,62),Anchor=AnchorStyles.Left,
        Margin=new Padding(0),BackColor=Color.Transparent};
      circle.Paint+=(sender,e)=>{
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        var shade=arrow=="↓"?Color.FromArgb(22,109,209):Color.FromArgb(24,129,77);
        using(var brush=new SolidBrush(shade))
          e.Graphics.FillEllipse(brush,1,1,59,59);
        using(var pen=new Pen(color,1.6f))
          e.Graphics.DrawEllipse(pen,1,1,59,59);
      };
      var arrowLabel=new Label{Text=arrow,Location=new Point(11,6),
        Size=new Size(40,48),Margin=new Padding(0,5,0,0),
        BackColor=Color.Transparent,ForeColor=Color.White,
        TextAlign=ContentAlignment.MiddleCenter,
        Font=new Font("Segoe UI",23,FontStyle.Bold)};
      circle.Controls.Add(arrowLabel);
      if(arrow=="↓")downloadArrow=arrowLabel;else uploadArrow=arrowLabel;
      var values=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=2,
        Margin=new Padding(0),Padding=new Padding(0)};
      values.RowStyles.Add(new RowStyle(SizeType.Percent,48));
      values.RowStyles.Add(new RowStyle(SizeType.Percent,52));
      values.Controls.Add(new Label{Text=name,Dock=DockStyle.Fill,
        ForeColor=muted,Font=new Font("Segoe UI",10),
        TextAlign=ContentAlignment.BottomLeft},0,0);
      var reading=new Label{Text="— Kbps",Dock=DockStyle.Fill,
        AutoEllipsis=true,ForeColor=ink,
        Font=new Font("Segoe UI",17,FontStyle.Bold),
        TextAlign=ContentAlignment.MiddleLeft};
      values.Controls.Add(reading,0,1);
      stack.Controls.Add(circle,0,0);
      stack.Controls.Add(values,1,0);
      card.Controls.Add(stack);
      parent.Controls.Add(card,col,0);
      return reading;
    }
    Label CompactSpeedPill(FlowLayoutPanel parent,string arrow,Color color){
      var pill=new Panel{Width=91,Height=34,Margin=new Padding(2,3,2,3),
        Padding=new Padding(0),BackColor=panel,Tag="tnet-speed-pill"};
      pill.Resize+=(sender,e)=>RoundSurface(pill,10);
      var arrowLabel=new Label{Text=arrow,Location=new Point(5,6),
        Size=new Size(17,21),TextAlign=ContentAlignment.MiddleCenter,
        Font=new Font("Segoe UI",12,FontStyle.Bold),ForeColor=color};
      var value=new Label{Text="— Kbps",Location=new Point(23,6),
        Size=new Size(65,21),AutoEllipsis=true,
        TextAlign=ContentAlignment.MiddleLeft,
        Font=new Font("Segoe UI",9,FontStyle.Bold),ForeColor=ink};
      pill.Controls.Add(arrowLabel);pill.Controls.Add(value);
      if(arrow=="↓")downloadArrow=arrowLabel;
      else if(arrow=="↑")uploadArrow=arrowLabel;
      parent.Controls.Add(pill);
      return value;
    }
    Label HeaderSpeedMetric(TableLayoutPanel parent,string name,int col,Color highlight){
      var surface=new Panel{Dock=DockStyle.Fill,Margin=new Padding(3,8,3,8),
        Padding=new Padding(8,6,6,4),BackColor=panel,Tag="tnet-header-speed"};
      surface.Resize+=(sender,e)=>RoundSurface(surface,9);
      var rows=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=2,ColumnCount=1,
        Margin=new Padding(0),Padding=new Padding(0)};
      rows.RowStyles.Add(new RowStyle(SizeType.Absolute,19));
      rows.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      rows.Controls.Add(new Label{
        Dock=DockStyle.Fill,Text=name,
        Font=new Font("Segoe UI",8,FontStyle.Bold),
        ForeColor=highlight,TextAlign=ContentAlignment.MiddleLeft},0,0);
      var value=new Label{
        Dock=DockStyle.Fill,Text="— Kbps",AutoEllipsis=true,
        Font=new Font("Segoe UI",11,FontStyle.Bold),
        ForeColor=ink,TextAlign=ContentAlignment.MiddleLeft};
      rows.Controls.Add(value,0,1);
      surface.Controls.Add(rows);
      parent.Controls.Add(surface,col,0);
      return value;
    }
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
      // Do not leave an old "Connected / 100%" visible after service failure.
      if(state!=0 && signalTrayPopup!=null){
        signalTrayConnected=false;signalTrayLastPercent=null;
        signalTrayLastAdapter="";signalTrayLastStatus=label;
        RenderSignalTrayPopup();
      }
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
    void AnimateTelemetry(){
      if(closing || IsDisposed)return;
      telemetryAnimationFrame++;
      // Zero transfer or unavailable samples leave both arrows completely still.
      if(downloadArrow!=null && !downloadArrow.IsDisposed)
        downloadArrow.Margin=new Padding(0,downloadArrowMoving?
          5+((telemetryAnimationFrame/2)%3):5,5,0);
      if(uploadArrow!=null && !uploadArrow.IsDisposed)
        uploadArrow.Margin=new Padding(0,uploadArrowMoving?
          7-((telemetryAnimationFrame/2)%3):5,5,0);
      // Decorative pulse uses only the currently reported Wi-Fi percentage.
      if(++pulseAnimationFrame%2==0){
        if(signalStrengthTrack!=null&&!signalStrengthTrack.IsDisposed)
          signalStrengthTrack.Invalidate();
        if(signalTrayTrack!=null&&!signalTrayTrack.IsDisposed && signalTrayPopup!=null
           && signalTrayPopup.Visible)signalTrayTrack.Invalidate();
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
          downloadArrowMoving=false;uploadArrowMoving=false;
          // The metric cards already show the unavailable speed state.
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
    Button UsagePeriodButton(string label,int view){
      var button=new Button{Text=label,Dock=DockStyle.Fill,Height=30,
        Margin=new Padding(3),BackColor=Color.FromArgb(32,46,68),
        ForeColor=ink,FlatStyle=FlatStyle.Flat,
        Font=new Font("Segoe UI",9,FontStyle.Regular)};
      button.FlatAppearance.BorderColor=Color.FromArgb(49,65,86);
      button.Click+=(sender,e)=>SetGraphView(view);
      return button;
    }
    void StyleSelectedUsagePeriod(){
      if(dayUsageButton==null)return;
      foreach(var pair in new[]{
        new{Button=dayUsageButton,View=0},
        new{Button=weekUsageButton,View=3},
        new{Button=monthUsageButton,View=4}}){
        if(pair.Button==null)continue;
        bool selected=!showLiveChart&&!showUsageLog&&currentUsageView==pair.View;
        pair.Button.BackColor=selected?
          (appearanceIsLight?Color.FromArgb(215,232,249):Color.FromArgb(12,130,245)):
          (appearanceIsLight?Color.FromArgb(228,234,243):Color.FromArgb(32,46,68));
        pair.Button.ForeColor=appearanceIsLight?lightInk:darkInk;
        pair.Button.FlatAppearance.BorderColor=selected?
          Color.FromArgb(70,148,217):
          (appearanceIsLight?Color.FromArgb(190,202,218):Color.FromArgb(49,65,86));
      }
    }
    void RenderUsagePeriod(){
      if(chart==null)return;
      var pts=chart.Series[0].Points;
      pts.Clear();
      double mb=1048576.0;
      DateTime now=DateTime.Today;
      if(currentUsageView==0){
        for(int i=6;i>=0;i--){
          DateTime day=now.AddDays(-i);
          string key=day.ToString("yyyy-MM-dd",CultureInfo.InvariantCulture);
          double total=existingDailyValues.ContainsKey(key)?existingDailyValues[key]:0;
          int index=pts.AddY(total/mb);
          pts[index].AxisLabel=day.ToString("ddd",CultureInfo.InvariantCulture);
        }
      }else if(currentUsageView==3){
        // Six calendar weeks, Monday to Sunday, including this week.
        int offset=((int)now.DayOfWeek+6)%7;
        DateTime monday=now.AddDays(-offset);
        for(int i=5;i>=0;i--){
          DateTime weekStart=monday.AddDays(-7*i);
          double sum=0;
          for(int d=0;d<7;d++){
            string key=weekStart.AddDays(d).ToString("yyyy-MM-dd",CultureInfo.InvariantCulture);
            if(existingDailyValues.ContainsKey(key))sum+=existingDailyValues[key];
          }
          int index=pts.AddY(sum/mb);
          pts[index].AxisLabel=weekStart.ToString("dd MMM",CultureInfo.InvariantCulture);
        }
      }else if(currentUsageView==4){
        // Last six calendar months, including current one.
        DateTime first=new DateTime(now.Year,now.Month,1);
        for(int i=5;i>=0;i--){
          DateTime month=first.AddMonths(-i);
          string prefix=month.ToString("yyyy-MM-",CultureInfo.InvariantCulture);
          double total=existingDailyValues.Where(x=>x.Key.StartsWith(prefix,StringComparison.Ordinal))
            .Sum(x=>x.Value);
          int index=pts.AddY(total/mb);
          pts[index].AxisLabel=month.ToString("MMM yy",CultureInfo.InvariantCulture);
        }
      }
    }
    void UpdateUsageCaption(){
      if(chartCaption==null)return;
      if(currentUsageView==3)
        chartCaption.Text="7-day usage: "+Bytes(latestSevenDayConsumed);
      else if(currentUsageView==4)
        chartCaption.Text="This month: "+Bytes(latestMonthConsumed);
      else
        chartCaption.Text="Today's usage: "+Bytes(latestTodayConsumed);
    }
    void SetGraphView(int view){
      showLiveChart=view==1;
      showUsageLog=view==2;
      if(view==0||view==3||view==4)currentUsageView=view;
      if(chartViewDropdown!=null){
        int index=view==1?1:view==2?2:0;
        if(chartViewDropdown.SelectedIndex!=index){
          syncingChartViewDropdown=true;
          chartViewDropdown.SelectedIndex=index;
          syncingChartViewDropdown=false;
        }
      }
      chart.Visible=!showLiveChart&&!showUsageLog;
      liveChart.Visible=showLiveChart;
      if(usageGrid!=null)usageGrid.Visible=showUsageLog;
      chartTitle.Text=showLiveChart?"Live speed":showUsageLog?"Usage log":
        currentUsageView==3?"Weekly usage":currentUsageView==4?"Monthly usage":"Daily usage";
      graphToggle.Text="Live speed";
      usageLogToggle.Text="Usage log";
      StyleSelectedUsagePeriod();
      if(showLiveChart)RenderLiveSpeedGraph();
      else if(!showUsageLog)RenderUsagePeriod();
      chartCaption.Cursor=showUsageLog?Cursors.Hand:Cursors.Default;
      UpdateUsageCaption();
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
    // The exact reported 0-100% WLAN signal quality is displayed directly.
    // No internet speed estimates, interpolation, or inferred readings.
    static Color SignalBarColor(int percentage){
      if(percentage>=80)return Color.FromArgb(79,212,161);    // green 80-100
      if(percentage>=50)return Color.FromArgb(236,185,65);    // yellow 50-79
      return Color.FromArgb(240,105,105);                    // red 0-49
    }
    void DrawSignalPulse(Graphics g,Rectangle bounds,int? signalPercent){
      if(bounds.Width<20 || bounds.Height<10)return;
      g.SmoothingMode=SmoothingMode.AntiAlias;
      bool active=signalPercent.HasValue;
      Color color=active?SignalBarColor(signalPercent.Value):muted;
      float mid=bounds.Top+bounds.Height*.54f;
      float height=bounds.Height*.32f;
      // ECG-shaped *visualization*, not a heart-rate measurement.
      // Colour reflects the real Windows WLAN quality thresholds.
      float[] x={0f,.12f,.21f,.29f,.34f,.39f,.445f,.50f,.545f,.59f,
                  .655f,.71f,.79f,.86f,1f};
      float[] y={0f,0f,0f,.12f,-.27f,.60f,-1.0f,1.0f,-.46f,.2f,
                  0f,0f,.10f,0f,0f};
      var pts=new PointF[x.Length];
      for(int i=0;i<x.Length;i++)
        pts[i]=new PointF(bounds.Left+4+x[i]*(bounds.Width-8),
          mid+y[i]*height);
      using(var pen=new Pen(color,2f)){
        pen.LineJoin=LineJoin.Round;
        g.DrawLines(pen,pts);
      }
      if(active){
        int idx=pulseAnimationFrame%((pts.Length-1)*2);
        int section=idx/2;
        float proportion=(idx%2)*.5f;
        float xx=pts[section].X+(pts[section+1].X-pts[section].X)*proportion;
        float yy=pts[section].Y+(pts[section+1].Y-pts[section].Y)*proportion;
        using(var b=new SolidBrush(color))
          g.FillEllipse(b,xx-2.5f,yy-2.5f,5f,5f);
      }
    }
    void UpdateSignalDisplay(string reportedSignal,bool connected){
      if(signalStrength==null || signalStrengthTrack==null || signalStrengthFill==null)return;
      int value=0;
      bool valid=connected &&
        Int32.TryParse(reportedSignal,NumberStyles.Integer,CultureInfo.InvariantCulture,out value) &&
        value>=0 && value<=100;
      if(!valid){
        signalStrength.Text="—";
        if(nordicSignalMetric!=null)nordicSignalMetric.Text="—";
        signalStrengthFill.Width=0;
        dashboardSignalPercent=null;
        signalStrengthTrack.Invalidate();
        signalStrengthTrack.AccessibleDescription="Wi-Fi signal unavailable";
        return;
      }
      // Reuse the same exact percentage shown in text. No made-up value.
      signalStrength.Text=value.ToString(CultureInfo.InvariantCulture)+"%";
      if(nordicSignalMetric!=null)nordicSignalMetric.Text=signalStrength.Text;
      signalStrengthFill.BackColor=SignalBarColor(value);
      signalStrengthFill.Width=0;
      dashboardSignalPercent=value;
      signalStrengthTrack.Invalidate();
      signalStrengthTrack.AccessibleDescription="Wi-Fi signal strength "+signalStrength.Text;
    }
    void ApplyUsage(Dictionary<string,object> d){
      try {string stat=Str(d,"status");if(stat=="tracking")SetIndicator("Monitoring live",0);
        else if(stat=="wrong-network")SetIndicator("Not connected",2);
        else if(stat=="adapter-error")SetIndicator("Adapter disconnected",2);
        else if(stat=="not-configured")SetIndicator("Monitoring paused",1);
        else SetIndicator("Starting monitor",1);
        double rx=Num(d,"todayRx"), tx=Num(d,"todayTx");
        latestTodayConsumed=Num(d,"todayTotal");
        latestSevenDayConsumed=Num(d,"sevenDayTotal");
        latestMonthConsumed=MonthTotalFromExistingDays(d);
        if(nordicTodayStat!=null)nordicTodayStat.Text=Bytes(latestTodayConsumed);
        if(nordicWeekStat!=null)nordicWeekStat.Text=Bytes(latestSevenDayConsumed);
        if(nordicMonthStat!=null)nordicMonthStat.Text=Bytes(latestMonthConsumed);
        today.Text=Bytes(latestTodayConsumed);
        UpdateUsageCaption();
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
        // These two metric cards are speeds, not cumulative download/upload.
        // The metric labels are the speed labels; no duplicated top header display.
        downloadArrowMoving=stat=="tracking" && !legacyService &&
          liveValid && liveFresh && PlausibleRate(rateRx) &&
          Rate(rateRx)!="0.0 Kbps" && rateRx>0;
        uploadArrowMoving=stat=="tracking" && !legacyService &&
          liveValid && liveFresh && PlausibleRate(rateTx) &&
          Rate(rateTx)!="0.0 Kbps" && rateTx>0;
        CaptureLiveSpeedSample(stat,liveSampleId,liveSampleUtc,
                               useNative || timestampValid,liveFresh,liveValid,
                               rateRx,rateTx);
        requestedCounterAdapter=stat=="tracking"?Str(d,"adapterName"):"";
        UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");
        // Same Windows-provided API data as the dashboard; no extra sampling.
        UpdateSignalTrayState(stat,Str(d,"adapterName"),Str(d,"wifiSignal"));
        currentSsid=Str(d,"currentSsid");wifi.Text=HotspotLabel(currentSsid);adapter.Text=Str(d,"adapterName");last.Text=Str(d,"rateSampleTime").Length>0?Str(d,"rateSampleTime"):"No sample yet";
        if(!configured) {hotspot.Text=Str(d,"targetSsid").Length>0?Str(d,"targetSsid"):currentSsid;var selected=Str(d,"adapterName");adapters.Items.Clear();var choices=d.ContainsKey("adapterChoices")?d["adapterChoices"] as System.Collections.ArrayList:null;if(choices!=null)foreach(var x in choices)adapters.Items.Add(Convert.ToString(x));if(adapters.Items.Count==0)adapters.Items.Add("Wi-Fi");adapters.SelectedItem=selected;if(adapters.SelectedIndex<0)adapters.SelectedIndex=0;configured=true;}
        if((DateTime.UtcNow-lastDailyChartRenderUtc).TotalSeconds>=5){
          existingDailyValues.Clear();
          var days=d.ContainsKey("days")?d["days"] as System.Collections.ArrayList:null;
          if(days!=null)foreach(var item in days){
            var record=item as Dictionary<string,object>;
            if(record!=null)existingDailyValues[Str(record,"date")]=Num(record,"total");
          }
          if(!showLiveChart&&!showUsageLog)RenderUsagePeriod();
          lastDailyChartRenderUtc=DateTime.UtcNow;
        }
      }catch {
        bool starting=(DateTime.UtcNow-engineLaunchUtc).TotalSeconds<8;
        SetIndicator(starting?"Starting monitor":"Service disconnected",starting?1:2);
        previousRateSampleId=-1;previousUsageRx=-1;previousUsageTx=-1;
        downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
        downloadArrowMoving=false;uploadArrowMoving=false;
        // The metric cards already show the unavailable speed state.
        AutoRecoverEngine();
      }
    }
    double MonthTotalFromExistingDays(Dictionary<string,object> data){
      if(data==null || !data.ContainsKey("days") || data["days"]==null)return 0;
      string month=DateTime.Now.ToString("yyyy-MM-",CultureInfo.InvariantCulture);
      double sum=0;
      var rows=data["days"] as System.Collections.IEnumerable;
      if(rows==null)return 0;
      foreach(object item in rows){
        var record=item as Dictionary<string,object>;
        if(record==null)continue;
        string date=Str(record,"date");
        if(date.StartsWith(month,StringComparison.Ordinal)){
          double value=Num(record,"total");
          if(value>0 && !Double.IsNaN(value) && !Double.IsInfinity(value))
            sum+=value;
        }
      }
      return sum;
    }
    void SaveSettings(){string name=hotspot.Text.Trim();if(name.Length==0){MessageBox.Show("Enter your hotspot name.");return;}try{var d=GetData();if(Str(d,"targetSsid").Length>0&&!String.Equals(name,Str(d,"targetSsid"),StringComparison.OrdinalIgnoreCase)){if(MessageBox.Show("Changing the hotspot clears recorded usage. Continue?","Confirm",MessageBoxButtons.YesNo)!=DialogResult.Yes)return;}string body=json.Serialize(new{targetSsid=name,adapterName=adapters.SelectedItem.ToString()});byte[] bytes=Encoding.UTF8.GetBytes(body);var request=(HttpWebRequest)WebRequest.Create(Base+"/api/config");request.Method="POST";request.ContentType="application/json";request.ContentLength=bytes.Length;using(var st=request.GetRequestStream())st.Write(bytes,0,bytes.Length);using(var response=request.GetResponse()){}configured=false;RefreshUsageAsync();MessageBox.Show("Hotspot saved.","T-Net");}catch(Exception ex){MessageBox.Show("Could not save: "+ex.Message);}}
    string FeedUrl() {
      string path=Path.Combine(root,UpdatesFileName);
      if(!File.Exists(path))return
        "https://raw.githubusercontent.com/adesanoyeademola/airtel-data-monitor/main/updates/stable.json";
      foreach(string line in File.ReadAllLines(path)){
        string t=line.Trim();if(t.StartsWith("https://",StringComparison.OrdinalIgnoreCase))return t;
      }
      return "https://raw.githubusercontent.com/adesanoyeademola/airtel-data-monitor/main/updates/stable.json";
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
      // A guard above prevents duplicate checks; don't fade the button during a check.
      checkingUpdates=true;
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
    // A small WinForms panel positioned by the clicked notification icon.
    // It displays the already-observed adapter and Wi-Fi signal values.
    void CreateSignalTrayPopup(){
      if(signalTrayPopup!=null && !signalTrayPopup.IsDisposed)return;
      signalTrayPopup=new Form{
        FormBorderStyle=FormBorderStyle.None,StartPosition=FormStartPosition.Manual,
        ShowInTaskbar=false,TopMost=true,Width=326,Height=226,
        BackColor=panel,ForeColor=ink,KeyPreview=true,
        Font=new Font("Segoe UI",10)
      };
      signalTrayPopup.Padding=new Padding(0);
      signalTrayPopup.Controls.Add(new Label{
        Text="T-Net",Location=new Point(18,12),Size=new Size(176,30),
        Font=new Font("Segoe UI",14,FontStyle.Bold),ForeColor=ink
      });
      signalTrayStatus=new Label{
        Text="Waiting for connection",Location=new Point(180,18),
        Size=new Size(128,23),TextAlign=ContentAlignment.MiddleRight,
        Font=new Font("Segoe UI",9),ForeColor=muted
      };
      signalTrayPopup.Controls.Add(signalTrayStatus);
      signalTrayPopup.Controls.Add(new Label{
        Text="Active adapter",Location=new Point(18,60),
        Size=new Size(280,19),ForeColor=muted,
        Font=new Font("Segoe UI",9)
      });
      signalTrayAdapter=new Label{
        Text="No active Wi-Fi",Location=new Point(18,80),
        Size=new Size(280,29),Font=new Font("Segoe UI",12,FontStyle.Bold),
        ForeColor=ink,AutoEllipsis=true
      };
      signalTrayPopup.Controls.Add(signalTrayAdapter);
      signalTrayPopup.Controls.Add(new Label{
        Text="Wi-Fi signal strength",Location=new Point(18,127),
        Size=new Size(215,22),ForeColor=ink,
        Font=new Font("Segoe UI",10)
      });
      signalTrayPercent=new Label{
        Text="—",Location=new Point(250,125),Size=new Size(58,26),
        TextAlign=ContentAlignment.MiddleRight,ForeColor=ink,
        Font=new Font("Segoe UI",12,FontStyle.Bold)
      };
      signalTrayPopup.Controls.Add(signalTrayPercent);
      signalTrayTrack=new Panel{
        Location=new Point(18,157),Size=new Size(290,9),
        BackColor=Color.FromArgb(49,65,86)
      };
      signalTrayFill=new Panel{
        Location=new Point(0,0),Size=new Size(0,9),
        BackColor=SignalBarColor(100)
      };
      signalTrayTrack.Controls.Add(signalTrayFill);
      signalTrayFill.Visible=false;
      signalTrayTrack.Height=25;
      signalTrayTrack.Paint+=(sender,e)=>
        DrawSignalPulse(e.Graphics,signalTrayTrack.ClientRectangle,signalTrayLastPercent);
      signalTrayPopup.Controls.Add(signalTrayTrack);
      signalTrayPopup.Controls.Add(new Label{
        Text="Windows-reported Wi-Fi signal",Location=new Point(18,184),
        Size=new Size(288,24),ForeColor=muted,
        Font=new Font("Segoe UI",9)
      });
      signalTrayPopup.Resize+=(sender,e)=>RoundSurface(signalTrayPopup,18);
      RoundSurface(signalTrayPopup,18);
      // Behave like a Windows flyout: clicking away or pressing Esc closes it.
      signalTrayPopup.Deactivate+=(sender,e)=>{
        if(signalTrayPopup!=null && signalTrayPopup.Visible){
          signalTrayPopup.Hide();
          signalTrayLastAutoHideUtc=DateTime.UtcNow;
        }
      };
      signalTrayPopup.KeyDown+=(sender,e)=>{
        if(e.KeyCode==Keys.Escape){signalTrayPopup.Hide();e.Handled=true;}
      };
      RenderSignalTrayPopup();
    }
    void UpdateSignalTrayState(string statusCode,string adapterName,string signal){
      bool connected=statusCode=="tracking";
      signalTrayConnected=connected;
      signalTrayLastAdapter=connected?adapterName:"";
      signalTrayLastStatus=connected?"Connected":
        statusCode=="wrong-network"?"Disconnected":
        statusCode=="adapter-error"?"Adapter unavailable":
        statusCode=="not-configured"?"Not configured":"Waiting for connection";
      int value;
      signalTrayLastPercent=(connected &&
        Int32.TryParse(signal,NumberStyles.Integer,CultureInfo.InvariantCulture,out value) &&
        value>=0 && value<=100)?(int?)value:null;
      RenderSignalTrayPopup();
    }
    void RenderSignalTrayPopup(){
      if(signalTrayPopup==null || signalTrayPopup.IsDisposed)return;
      if(signalTrayStatus==null || signalTrayAdapter==null ||
         signalTrayPercent==null || signalTrayFill==null)return;
      signalTrayStatus.Text=signalTrayLastStatus;
      signalTrayStatus.ForeColor=signalTrayConnected?
        Color.FromArgb(79,212,161):muted;
      signalTrayAdapter.Text=signalTrayConnected &&
        !String.IsNullOrWhiteSpace(signalTrayLastAdapter)?
        signalTrayLastAdapter:"No active Wi-Fi";
      if(!signalTrayLastPercent.HasValue){
        signalTrayPercent.Text="—";
        signalTrayFill.Width=0;
        signalTrayTrack.Invalidate();
      }else{
        int v=signalTrayLastPercent.Value;
        signalTrayPercent.Text=v.ToString(CultureInfo.InvariantCulture)+"%";
        signalTrayFill.BackColor=SignalBarColor(v);
        signalTrayFill.Width=0;
        signalTrayTrack.Invalidate();
      }
    }
    void ToggleSignalTrayPopup(){
      if(closing)return;
      CreateSignalTrayPopup();
      AppearanceControl(signalTrayPopup,appearanceIsLight);
      if(signalTrayPopup.Visible){signalTrayPopup.Hide();return;}
      // When a tray click first deactivates the flyout, don't reopen it
      // from that same click's MouseClick event.
      if((DateTime.UtcNow-signalTrayLastAutoHideUtc).TotalMilliseconds<300)return;
      RenderSignalTrayPopup();
      Point click=System.Windows.Forms.Cursor.Position;
      Rectangle area=Screen.FromPoint(click).WorkingArea;
      int x=Math.Max(area.Left,Math.Min(area.Right-signalTrayPopup.Width,
                       click.X-signalTrayPopup.Width+42));
      int preferredY=click.Y-signalTrayPopup.Height-12;
      if(click.Y>=area.Bottom)preferredY=area.Bottom-signalTrayPopup.Height-10;
      int y=Math.Max(area.Top,Math.Min(area.Bottom-signalTrayPopup.Height,
                       preferredY));
      signalTrayPopup.Location=new Point(x,y);
      signalTrayPopup.Show();
      signalTrayPopup.Activate();
    }
    void LoadAppearanceChoice(){
      try{
        if(File.Exists(appearanceFile)){
          string choice=File.ReadAllText(appearanceFile).Trim().ToLowerInvariant();
          if(choice=="light"||choice=="dark"||choice=="system")
            appearanceMode=choice;
        }
      }catch{/* Appearance is optional; monitoring must still start. */}
    }
    bool WindowsPrefersLight(){
      try{
        using(var key=Registry.CurrentUser.OpenSubKey(
          @"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")){
          object value=key==null?null:key.GetValue("AppsUseLightTheme");
          return value!=null && Convert.ToInt32(value,CultureInfo.InvariantCulture)!=0;
        }
      }catch{return false;}
    }
    void SelectAppearance(string choice){
      if(choice!="light"&&choice!="dark"&&choice!="system")return;
      appearanceMode=choice;
      try{
        Directory.CreateDirectory(Path.GetDirectoryName(appearanceFile));
        File.WriteAllText(appearanceFile,choice,Encoding.UTF8);
      }catch{/* Failure to save preference cannot interrupt monitoring. */}
      ApplyAppearance(true);
    }
    void CheckSystemAppearance(){
      if(appearanceMode!="system" || DateTime.UtcNow<nextSystemThemeCheck)return;
      nextSystemThemeCheck=DateTime.UtcNow.AddSeconds(2);
      if(appearanceIsLight!=WindowsPrefersLight())ApplyAppearance(true);
    }
    Color AppearanceColor(Color color,bool light){
      if(color==Color.Empty||color==Color.Transparent||color.A==0)return color;
      Color[] darkColors={
        darkBg,darkPanel,darkInk,darkMuted,
        Color.FromArgb(32,46,68),Color.FromArgb(49,65,86),
        Color.FromArgb(42,54,71),Color.FromArgb(48,60,76),
        Color.FromArgb(38,62,86),Color.FromArgb(34,47,66)
      };
      Color[] lightColors={
        lightBg,lightPanel,lightInk,lightMuted,
        Color.FromArgb(236,243,253),Color.FromArgb(197,214,234),
        Color.FromArgb(229,238,249),Color.FromArgb(227,237,249),
        Color.FromArgb(214,233,254),Color.FromArgb(236,243,252)
      };
      for(int i=0;i<darkColors.Length;i++)
        if(color.ToArgb()==darkColors[i].ToArgb()||
           color.ToArgb()==lightColors[i].ToArgb())
          return light?lightColors[i]:darkColors[i];
      return color; // Preserve signal status, coloured bars and chart series.
    }
    void AppearanceControl(Control control,bool light){
      control.BackColor=AppearanceColor(control.BackColor,light);
      control.ForeColor=AppearanceColor(control.ForeColor,light);
      // Keep neutral header buttons readable on light surfaces; retain
      // white text on the coloured Save hotspot button.
      if(control is Button && control.BackColor!=accent &&
         (control.ForeColor==Color.White || control.ForeColor==lightInk))
        control.ForeColor=light?lightInk:Color.White;
      if(control is Label && control.Text=="T-Net")
        control.ForeColor=light?lightInk:Color.White;
      var grid=control as DataGridView;
      if(grid!=null){
        grid.BackgroundColor=AppearanceColor(grid.BackgroundColor,light);
        grid.GridColor=AppearanceColor(grid.GridColor,light);
        foreach(DataGridViewCellStyle st in new[]{
          grid.DefaultCellStyle,grid.ColumnHeadersDefaultCellStyle,
          grid.RowHeadersDefaultCellStyle,grid.AlternatingRowsDefaultCellStyle}){
          st.BackColor=AppearanceColor(st.BackColor,light);
          st.ForeColor=AppearanceColor(st.ForeColor,light);
          st.SelectionBackColor=AppearanceColor(st.SelectionBackColor,light);
          st.SelectionForeColor=AppearanceColor(st.SelectionForeColor,light);
        }
      }
      var graph=control as Chart;
      if(graph!=null){
        foreach(ChartArea a in graph.ChartAreas){
          a.BackColor=AppearanceColor(a.BackColor,light);
          a.AxisX.LineColor=AppearanceColor(a.AxisX.LineColor,light);
          a.AxisY.LineColor=AppearanceColor(a.AxisY.LineColor,light);
          a.AxisX.LabelStyle.ForeColor=AppearanceColor(a.AxisX.LabelStyle.ForeColor,light);
          a.AxisY.LabelStyle.ForeColor=AppearanceColor(a.AxisY.LabelStyle.ForeColor,light);
          a.AxisY.TitleForeColor=AppearanceColor(a.AxisY.TitleForeColor,light);
          a.AxisX.MajorGrid.LineColor=AppearanceColor(a.AxisX.MajorGrid.LineColor,light);
          a.AxisY.MajorGrid.LineColor=AppearanceColor(a.AxisY.MajorGrid.LineColor,light);
        }
        foreach(Legend legend in graph.Legends){
          legend.BackColor=AppearanceColor(legend.BackColor,light);
          legend.ForeColor=AppearanceColor(legend.ForeColor,light);
        }
      }
      foreach(Control child in control.Controls)AppearanceControl(child,light);
    }
    void ApplyAppearance(bool force){
      bool useLight=appearanceMode=="light" ||
        (appearanceMode=="system"&&WindowsPrefersLight());
      if(!force&&appearanceIsLight==useLight)return;
      appearanceIsLight=useLight;
      AppearanceControl(this,useLight);
      bg=useLight?lightBg:darkBg;
      panel=useLight?lightPanel:darkPanel;
      ink=useLight?lightInk:darkInk;
      muted=useLight?lightMuted:darkMuted;
      BackColor=bg;ForeColor=ink;
      StyleAppearanceControls(this,useLight);
      StyleSelectedUsagePeriod();
      StyleNordicShell(useLight);
      if(chart!=null && chart.Series.Count>0){
        chart.Series[0].Color=useLight?Color.FromArgb(57,132,241):Color.FromArgb(12,143,255);
        chart.Series[0].BackGradientStyle=GradientStyle.TopBottom;
        chart.Series[0].BackSecondaryColor=useLight?Color.FromArgb(35,107,223):Color.FromArgb(20,94,242);
        var axis=chart.ChartAreas[0];
        axis.AxisX.MajorGrid.Enabled=false;
        axis.AxisY.MajorGrid.LineColor=useLight?
          Color.FromArgb(221,232,247):Color.FromArgb(48,60,76);
        axis.AxisX.LineColor=useLight?Color.FromArgb(213,226,245):muted;
        axis.AxisY.LineColor=useLight?Color.FromArgb(213,226,245):muted;
        axis.AxisX.LabelStyle.ForeColor=useLight?lightMuted:darkMuted;
        axis.AxisY.LabelStyle.ForeColor=useLight?lightMuted:darkMuted;
      }
      if(chartViewDropdown!=null){
        chartViewDropdown.BackColor=useLight?lightPanel:darkPanel;
        chartViewDropdown.ForeColor=useLight?lightInk:darkInk;
      }
      if(updateButton!=null){
        updateButton.BackColor=useLight?Color.FromArgb(218,231,245):
          Color.FromArgb(38,57,81);
        updateButton.ForeColor=useLight?lightInk:Color.White;
      }
      if(appearanceButton!=null){
        appearanceButton.Text="◐ Appearance  ▾";
        appearanceButton.BackColor=useLight?
          Color.FromArgb(231,239,248):Color.FromArgb(32,46,68);
        appearanceButton.ForeColor=useLight?lightInk:darkInk;
        ShapeAppearanceButton();
      }
      if(signalTrayPopup!=null&&!signalTrayPopup.IsDisposed){
        AppearanceControl(signalTrayPopup,useLight);
        signalTrayPopup.BackColor=panel;
        RenderSignalTrayPopup();
      }
      Invalidate(true);
    }
    GraphicsPath RoundedPath(Rectangle bounds,int diameter){
      int d=Math.Max(2,Math.Min(diameter,Math.Min(bounds.Width,bounds.Height)));
      var path=new GraphicsPath();
      path.AddArc(bounds.Left,bounds.Top,d,d,180,90);
      path.AddArc(bounds.Right-d,bounds.Top,d,d,270,90);
      path.AddArc(bounds.Right-d,bounds.Bottom-d,d,d,0,90);
      path.AddArc(bounds.Left,bounds.Bottom-d,d,d,90,90);
      path.CloseFigure();
      return path;
    }
    void RoundSurface(Control surface,int diameter){
      if(surface==null||surface.IsDisposed||surface.Width<4||surface.Height<4)return;
      using(var path=RoundedPath(new Rectangle(0,0,surface.Width,surface.Height),diameter)){
        Region previous=surface.Region;
        surface.Region=new Region(path);
        if(previous!=null)previous.Dispose();
      }
    }
    Button NordicModeButton(string title,string mode){
      var button=new Button{Text=title,Width=78,Height=28,
        Margin=new Padding(1,1,1,1),Padding=new Padding(0),
        FlatStyle=FlatStyle.Flat,Font=new Font("Segoe UI",8),
        TextAlign=ContentAlignment.MiddleCenter};
      button.FlatAppearance.BorderSize=0;
      button.Click+=(sender,e)=>SelectAppearance(mode);
      return button;
    }
    Button NordicNavButton(string label,int destination){
      var button=new Button{
        Text=label,Dock=DockStyle.Top,Height=54,
        TextAlign=ContentAlignment.MiddleLeft,FlatStyle=FlatStyle.Flat,
        Font=new Font("Segoe UI",12),Margin=new Padding(0,0,0,10),
        Padding=new Padding(16,0,0,0),TabStop=true
      };
      button.FlatAppearance.BorderSize=0;
      button.Click+=(sender,e)=>{
        nordicSelectedNav=button;
        StyleNordicShell(appearanceIsLight);
        if(destination==0)SetGraphView(0);
        else if(destination==1)SetGraphView(3);
        else if(destination==2){
          if(nordicNetworkPanel!=null)nordicNetworkPanel.Focus();
        }
        else if(destination==3)SetGraphView(2);
        else if(destination==4){
          if(nordicLightButton!=null)nordicLightButton.Focus();
        }
      };
      nordicNavButtons.Add(button);
      if(destination==0)nordicSelectedNav=button;
      return button;
    }
    Panel CreateNordicSidebar(){
      var aside=new Panel{Dock=DockStyle.Fill,Padding=new Padding(10,15,10,12),
        BackColor=Color.FromArgb(238,245,255),Tag="nordic-sidebar"};
      aside.Paint+=(sender,e)=>PaintReferenceSidebar(e.Graphics,aside.ClientRectangle);
      var brand=new Label{Text="▥  T-Net",Dock=DockStyle.None,
        Location=new Point(20,26),Size=new Size(192,70),
        Font=new Font("Segoe UI",22,FontStyle.Bold),
        ForeColor=Color.White,BackColor=Color.FromArgb(12,39,82),
        TextAlign=ContentAlignment.MiddleLeft,Tag="tnet-brand"};
      aside.Controls.Add(brand);
      var navigation=new Panel{Dock=DockStyle.None,
        Location=new Point(15,133),Size=new Size(197,330),
        Margin=new Padding(0),Padding=new Padding(0,8,0,0)};
      // Add in reverse for top dock stacking order.
      navigation.Controls.Add(NordicNavButton("⚙   Settings",4));
      navigation.Controls.Add(NordicNavButton("◷   History",3));
      navigation.Controls.Add(NordicNavButton("⌁   Network",2));
      navigation.Controls.Add(NordicNavButton("▥   Usage",1));
      navigation.Controls.Add(NordicNavButton("⌂   Dashboard",0));
      aside.Controls.Add(navigation);
      navigation.Tag="tnet-navigation";
      navigation.BringToFront();
      brand.BringToFront();
      aside.Controls.Add(new Label{Text="◉  v6.31.0",Dock=DockStyle.Bottom,Height=59,
        ForeColor=Color.FromArgb(188,216,250),
        BackColor=Color.FromArgb(12,39,82),
        Font=new Font("Segoe UI",10,FontStyle.Bold),
        TextAlign=ContentAlignment.MiddleCenter,Tag="tnet-version"});
      return aside;
    }
    void StyleNordicShell(bool light){
      Color blue=Color.FromArgb(24,126,251);
      if(nordicSidebar!=null){
        nordicSidebar.BackColor=light?Color.FromArgb(238,245,255):Color.FromArgb(12,39,82);
        nordicSidebar.Invalidate();
        foreach(Control c in nordicSidebar.Controls){
          string tag=c.Tag as string;
          if(tag=="tnet-brand"){
            c.ForeColor=light?Color.FromArgb(44,114,227):Color.White;
            c.BackColor=light?Color.FromArgb(238,245,255):Color.FromArgb(12,39,82);
          }
          if(tag=="tnet-version"){
            c.ForeColor=light?lightMuted:Color.FromArgb(188,217,255);
            c.BackColor=light?Color.FromArgb(238,245,255):Color.FromArgb(12,39,82);
          }
          if(tag=="tnet-navigation")
            c.BackColor=light?Color.FromArgb(238,245,255):Color.FromArgb(12,39,82);
        }
      }
      foreach(var nav in nordicNavButtons){
        if(nav==null)continue;
        bool selected=nav==nordicSelectedNav;
        nav.ForeColor=selected?(light?blue:Color.White):(light?lightInk:Color.FromArgb(227,238,255));
        nav.BackColor=selected?
          (light?Color.FromArgb(224,236,254):Color.FromArgb(10,112,240)):
          (light?Color.FromArgb(238,245,255):Color.FromArgb(12,39,82));
        nav.FlatAppearance.BorderSize=0;
        nav.Resize+=(sender,e)=>RoundSurface(nav,13);
        RoundSurface(nav,13);
        nav.FlatAppearance.MouseOverBackColor=light?
          Color.FromArgb(215,230,253):Color.FromArgb(25,73,137);
      }
      if(nordicAppearanceStrip!=null){
        nordicAppearanceStrip.BackColor=light?
          Color.FromArgb(229,238,251):Color.FromArgb(35,48,69);
        foreach(var button in new[]{nordicLightButton,nordicDarkButton,nordicAutoButton}){
          if(button==null)continue;
          string mode=button==nordicLightButton?"light":
            button==nordicDarkButton?"dark":"system";
          bool selected=appearanceMode==mode;
          button.ForeColor=selected?(light?blue:Color.FromArgb(152,188,255)):
            (light?lightMuted:darkMuted);
          button.BackColor=selected?
            (light?Color.White:Color.FromArgb(53,71,104)):
            (light?Color.FromArgb(229,238,251):Color.FromArgb(35,48,69));
        }
      }
    }
    void ShapeAppearanceButton(){
      if(appearanceButton==null||appearanceButton.IsDisposed||
         appearanceButton.Width<8||appearanceButton.Height<8)return;
      int radius=10,w=appearanceButton.Width,h=appearanceButton.Height;
      using(var path=new GraphicsPath()){
        path.AddArc(0,0,radius,radius,180,90);
        path.AddArc(w-radius-1,0,radius,radius,270,90);
        path.AddArc(w-radius-1,h-radius-1,radius,radius,0,90);
        path.AddArc(0,h-radius-1,radius,radius,90,90);
        path.CloseFigure();
        var old=appearanceButton.Region;
        appearanceButton.Region=new Region(path);
        if(old!=null)old.Dispose();
      }
    }
    void StyleAppearanceControls(Control rootControl,bool light){
      var button=rootControl as Button;
      if(button!=null){
        if(button==appearanceButton || button==updateButton ||
           button==graphToggle || button==usageLogToggle){
          button.FlatAppearance.BorderSize=1;
          button.FlatAppearance.BorderColor=light?
            Color.FromArgb(189,205,222):Color.FromArgb(49,65,86);
          button.FlatAppearance.MouseOverBackColor=light?
            Color.FromArgb(220,233,246):Color.FromArgb(43,60,82);
          button.FlatAppearance.MouseDownBackColor=light?
            Color.FromArgb(205,223,243):Color.FromArgb(51,72,96);
        }
      }
      foreach(Control child in rootControl.Controls)StyleAppearanceControls(child,light);
    }
    void ShowAppearanceMenu(){
      if(appearanceMenu!=null){appearanceMenu.Dispose();appearanceMenu=null;}
      appearanceMenu=new ContextMenuStrip{
        ShowImageMargin=false,ShowCheckMargin=false,
        Padding=new Padding(6),BackColor=appearanceIsLight?
          Color.White:darkPanel
      };
      var options=new FlowLayoutPanel{
        Size=new Size(266,42),Margin=new Padding(0),
        Padding=new Padding(4),WrapContents=false,
        FlowDirection=FlowDirection.LeftToRight,
        BackColor=appearanceIsLight?
          Color.FromArgb(230,240,252):Color.FromArgb(35,48,69)
      };
      foreach(string choice in new[]{"light","dark","system"}){
        string label=choice=="light"?"☀ Light":
          choice=="dark"?"☾ Dark":"◐ Auto";
        bool selected=appearanceMode==choice;
        var button=new Button{Text=label,
          Size=new Size(82,32),Margin=new Padding(1),
          FlatStyle=FlatStyle.Flat,
          Font=new Font("Segoe UI",9,selected?FontStyle.Bold:FontStyle.Regular),
          ForeColor=selected?Color.FromArgb(44,114,227):
            (appearanceIsLight?lightInk:darkInk),
          BackColor=selected?
            (appearanceIsLight?Color.White:Color.FromArgb(55,74,103)):
            (appearanceIsLight?Color.FromArgb(230,240,252):
              Color.FromArgb(35,48,69))
        };
        button.FlatAppearance.BorderSize=0;
        string mode=choice;
        button.Click+=(sender,e)=>{
          SelectAppearance(mode);
          if(appearanceMenu!=null)appearanceMenu.Close();
        };
        options.Controls.Add(button);
      }
      var host=new ToolStripControlHost(options){
        AutoSize=false,Size=new Size(266,42),
        Margin=new Padding(0),Padding=new Padding(0)
      };
      appearanceMenu.Items.Add(host);
      appearanceMenu.Show(appearanceButton,new Point(0,appearanceButton.Height+3));
    }
    void ShowWindow(){
      if(signalTrayPopup!=null && !signalTrayPopup.IsDisposed)signalTrayPopup.Hide();
      Show();WindowState=FormWindowState.Normal;Activate();
    }
    void Quit(){closing=true;refreshTimer.Stop();if(indicatorTimer!=null)indicatorTimer.Stop();
      if(signalTrayPopup!=null && !signalTrayPopup.IsDisposed){
        signalTrayPopup.Close();signalTrayPopup.Dispose();signalTrayPopup=null;
      }
      if(liveCounterTimer!=null){liveCounterTimer.Dispose();liveCounterTimer=null;}
      lock(liveCounterLock){DisposeNativeCounters();}try{if(engine!=null&&!engine.HasExited)engine.Kill();}catch{}tray.Visible=false;tray.Dispose();Close();}
    [STAThread] static void Main(string[] args){bool created;using(var mutex=new Mutex(true,"Local\\AirtelDataMonitorDesktopV3",out created)){if(!created){MessageBox.Show("T-Net is already running. Open it from the system tray.");return;}Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new MainForm(args.Any(a=>a=="--share")));}}
  }
}
