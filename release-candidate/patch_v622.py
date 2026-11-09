from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(a,b):
    global s
    n=s.count(a)
    if n!=1: raise RuntimeError("Expected exactly one source anchor (%d): %r"%(n,a[:165]))
    s=s.replace(a,b)

one('const string AppVersion = "6.21.0";','const string AppVersion = "6.22.0";')
one('''    int currentUsageView=0; // 0 daily, 3 weekly, 4 monthly''',
'''    int currentUsageView=0; // 0 daily, 3 weekly, 4 monthly
    double latestTodayConsumed=0,latestSevenDayConsumed=0,latestMonthConsumed=0;
    Label downloadArrow,uploadArrow;
    bool downloadArrowMoving=false,uploadArrowMoving=false;
    int telemetryAnimationFrame=0;
    int pulseAnimationFrame=0;
    int? dashboardSignalPercent=null;''')

# The existing 5 usage cards become 3, reflecting today's usage and two
# live speed counters. Period totals are displayed under the chart instead.
one('''      var metrics=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=5};
      for(int i=0;i<5;i++)metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,20));
      today=Metric(metrics,"Today",0); down=Metric(metrics,"Downloaded",1); up=Metric(metrics,"Uploaded",2);
      week=Metric(metrics,"7-day usage",3); monthly=Metric(metrics,"This month",4);''',
'''      var metrics=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=3};
      for(int i=0;i<3;i++)metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100f/3));
      today=Metric(metrics,"Today",0);
      down=Metric(metrics,"Download speed",1);
      up=Metric(metrics,"Upload speed",2);''')
one('''Color labelColor=name=="Today"?Color.FromArgb(135,115,211):
        name=="Downloaded"?Color.FromArgb(66,149,220):
        name=="Uploaded"?Color.FromArgb(45,168,127):
        name=="This month"?Color.FromArgb(45,154,163):
        Color.FromArgb(207,149,55);''',
'''Color labelColor=name=="Today"?Color.FromArgb(135,115,211):
        name=="Download speed"?Color.FromArgb(66,149,220):
        name=="Upload speed"?Color.FromArgb(45,168,127):
        Color.FromArgb(207,149,55);''')
one('''        today.Text=Bytes(Num(d,"todayTotal"));down.Text=Bytes(rx);up.Text=Bytes(tx);week.Text=Bytes(Num(d,"sevenDayTotal"));
        monthly.Text=Bytes(MonthTotalFromExistingDays(d));''',
'''        latestTodayConsumed=Num(d,"todayTotal");
        latestSevenDayConsumed=Num(d,"sevenDayTotal");
        latestMonthConsumed=MonthTotalFromExistingDays(d);
        today.Text=Bytes(latestTodayConsumed);
        UpdateUsageCaption();''')
one('''        CaptureLiveSpeedSample(stat,liveSampleId,liveSampleUtc,''',
'''        // These two metric cards are speeds, not cumulative download/upload.
        down.Text=downloadSpeed.Text;
        up.Text=uploadSpeed.Text;
        downloadArrowMoving=stat=="tracking" && !legacyService &&
          liveValid && liveFresh && rateRx>0 && PlausibleRate(rateRx);
        uploadArrowMoving=stat=="tracking" && !legacyService &&
          liveValid && liveFresh && rateTx>0 && PlausibleRate(rateTx);
        CaptureLiveSpeedSample(stat,liveSampleId,liveSampleUtc,''')
# Ensure icons freeze when service errors, rather than showing stale motion.
one('''          downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
          AutoRecoverEngine();''',
'''          downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
          downloadArrowMoving=false;uploadArrowMoving=false;
          if(down!=null)down.Text=downloadSpeed.Text;
          if(up!=null)up.Text=uploadSpeed.Text;
          AutoRecoverEngine();''')
one('''        previousRateSampleId=-1;previousUsageRx=-1;previousUsageTx=-1;
        downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
        AutoRecoverEngine();''',
'''        previousRateSampleId=-1;previousUsageRx=-1;previousUsageTx=-1;
        downloadSpeed.Text="— Kbps";uploadSpeed.Text="— Kbps";
        downloadArrowMoving=false;uploadArrowMoving=false;
        if(down!=null)down.Text=downloadSpeed.Text;
        if(up!=null)up.Text=uploadSpeed.Text;
        AutoRecoverEngine();''')
one('''      pill.Controls.Add(arrowLabel);pill.Controls.Add(value);''',
'''      pill.Controls.Add(arrowLabel);pill.Controls.Add(value);
      if(arrow=="↓")downloadArrow=arrowLabel;
      else if(arrow=="↑")uploadArrow=arrowLabel;''')
one('''indicatorTimer.Tick+=(s,e)=>PulseIndicator();indicatorTimer.Start();''',
'''indicatorTimer.Tick+=(s,e)=>{PulseIndicator();AnimateTelemetry();};indicatorTimer.Start();''')
one('''    void PulseIndicator(){''',
'''    void AnimateTelemetry(){
      if(closing || IsDisposed)return;
      telemetryAnimationFrame++;
      // Zero transfer or unavailable samples leave both arrows completely still.
      if(downloadArrow!=null && !downloadArrow.IsDisposed)
        downloadArrow.Top=downloadArrowMoving?
          (6+((telemetryAnimationFrame/2)%3)):6;
      if(uploadArrow!=null && !uploadArrow.IsDisposed)
        uploadArrow.Top=uploadArrowMoving?
          (8-((telemetryAnimationFrame/2)%3)):6;
      // Decorative pulse uses only the currently reported Wi-Fi percentage.
      if(++pulseAnimationFrame%2==0){
        if(signalStrengthTrack!=null&&!signalStrengthTrack.IsDisposed)
          signalStrengthTrack.Invalidate();
        if(signalTrayTrack!=null&&!signalTrayTrack.IsDisposed && signalTrayPopup!=null
           && signalTrayPopup.Visible)signalTrayTrack.Invalidate();
      }
    }
    void PulseIndicator(){''')

# All five toolbar buttons share one row, font, shape, dimensions, and border.
# The redundant chartTitle label is not added to the panel.
one('''      var graphHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=3,RowCount=1};
      graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,120));
      graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,110));
      graphHeader.Controls.Add(chartTitle,0,0);
      graphHeader.Controls.Add(graphToggle,1,0);
      graphHeader.Controls.Add(usageLogToggle,2,0);''',
'''      var graphHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=5,RowCount=1};
      for(int i=0;i<5;i++)graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,20));
      graphToggle.Dock=DockStyle.Fill;
      graphToggle.Width=0;graphToggle.Font=new Font("Segoe UI",9);
      usageLogToggle.Dock=DockStyle.Fill;
      usageLogToggle.Width=0;usageLogToggle.Font=new Font("Segoe UI",9);
      graphHeader.Controls.Add(graphToggle,3,0);
      graphHeader.Controls.Add(usageLogToggle,4,0);''')
one('''      var usagePeriods=new TableLayoutPanel{Dock=DockStyle.Fill,
        ColumnCount=3,RowCount=1,Margin=new Padding(0)};
      for(int i=0;i<3;i++)usagePeriods.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100f/3));
      dayUsageButton=UsagePeriodButton("Daily usage",0);
      weekUsageButton=UsagePeriodButton("Weekly usage",3);
      monthUsageButton=UsagePeriodButton("Monthly usage",4);
      usagePeriods.Controls.Add(dayUsageButton,0,0);
      usagePeriods.Controls.Add(weekUsageButton,1,0);
      usagePeriods.Controls.Add(monthUsageButton,2,0);''',
'''      dayUsageButton=UsagePeriodButton("Daily usage",0);
      weekUsageButton=UsagePeriodButton("Weekly usage",3);
      monthUsageButton=UsagePeriodButton("Monthly usage",4);
      graphHeader.Controls.Add(dayUsageButton,0,0);
      graphHeader.Controls.Add(weekUsageButton,1,0);
      graphHeader.Controls.Add(monthUsageButton,2,0);''')
one('''      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,78));''',
    '''      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,40));''')
one('''      var graphTop=new TableLayoutPanel{Dock=DockStyle.Fill,
        RowCount=2,ColumnCount=1,Margin=new Padding(0)};
      graphTop.RowStyles.Add(new RowStyle(SizeType.Absolute,39));
      graphTop.RowStyles.Add(new RowStyle(SizeType.Absolute,39));
      graphTop.Controls.Add(graphHeader,0,0);
      graphTop.Controls.Add(usagePeriods,0,1);
      graphLayout.Controls.Add(graphTop,0,0);''',
'''      graphLayout.Controls.Add(graphHeader,0,0);''')
one('''      var button=new Button{Text=label,Dock=DockStyle.Fill,Height=31,
        Margin=new Padding(2),BackColor=Color.FromArgb(32,46,68),
        ForeColor=ink,FlatStyle=FlatStyle.Flat,
        Font=new Font("Segoe UI",8,FontStyle.Regular)};''',
'''      var button=new Button{Text=label,Dock=DockStyle.Fill,Height=30,
        Margin=new Padding(3),BackColor=Color.FromArgb(32,46,68),
        ForeColor=ink,FlatStyle=FlatStyle.Flat,
        Font=new Font("Segoe UI",9,FontStyle.Regular)};''')
# Active styling only: same WinForms flat button, no tabs with special shapes.
one('''      graphToggle.Text=showLiveChart?"Daily usage":"Live speed";
      usageLogToggle.Text=showUsageLog?"Daily usage":"Usage log";''',
'''      graphToggle.Text="Live speed";
      usageLogToggle.Text="Usage log";''')
one('''        chartCaption.Text=currentUsageView==3?"Last six calendar weeks  •  MB":
          currentUsageView==4?"Last six calendar months  •  MB":"Last 7 days  •  MB";
        chartCaption.Cursor=Cursors.Default;
        RenderUsagePeriod();''',
'''        chartCaption.Cursor=Cursors.Default;
        RenderUsagePeriod();
        UpdateUsageCaption();''')
# Cache exact existing usage totals; do not compute totals from arbitrary chart width.
one('''    void SetGraphView(int view){''',
'''    void UpdateUsageCaption(){
      if(chartCaption==null || showLiveChart || showUsageLog)return;
      if(currentUsageView==3)
        chartCaption.Text="7-day usage: "+Bytes(latestSevenDayConsumed);
      else if(currentUsageView==4)
        chartCaption.Text="This month: "+Bytes(latestMonthConsumed);
      else
        chartCaption.Text="Today's usage: "+Bytes(latestTodayConsumed);
    }
    void SetGraphView(int view){''')
one('''chartCaption=new Label{Text="Last 7 days  •  MB"''',
    '''chartCaption=new Label{Text="Today's usage: 0 B"''')

# Keep existing exact Windows-reported signal percentage; only its
# presentation changes from length bar to an ECG-like decorative waveform.
one('''    int? dashboardSignalPercent=null;''',
'''    int? dashboardSignalPercent=null;''')
one('''      signalStrengthTrack.Controls.Add(signalStrengthFill);''',
'''      signalStrengthTrack.Controls.Add(signalStrengthFill);
      signalStrengthFill.Visible=false;
      signalStrengthTrack.Height=25;
      signalStrengthTrack.Margin=new Padding(5,0,7,0);
      signalStrengthTrack.Paint+=(sender,e)=>
        DrawSignalPulse(e.Graphics,signalStrengthTrack.ClientRectangle,dashboardSignalPercent);''')
one('''      signalTrayTrack.Controls.Add(signalTrayFill);''',
'''      signalTrayTrack.Controls.Add(signalTrayFill);
      signalTrayFill.Visible=false;
      signalTrayTrack.Height=25;
      signalTrayTrack.Paint+=(sender,e)=>
        DrawSignalPulse(e.Graphics,signalTrayTrack.ClientRectangle,signalTrayLastPercent);''')
one('''        signalStrengthFill.Width=0;
        signalStrengthTrack.AccessibleDescription="Wi-Fi signal unavailable";''',
'''        signalStrengthFill.Width=0;
        dashboardSignalPercent=null;
        signalStrengthTrack.Invalidate();
        signalStrengthTrack.AccessibleDescription="Wi-Fi signal unavailable";''')
one('''      signalStrengthFill.Width=(signalStrengthTrack.ClientSize.Width*value+50)/100;
      signalStrengthTrack.AccessibleDescription="Wi-Fi signal strength "+signalStrength.Text;''',
'''      signalStrengthFill.Width=0;
      dashboardSignalPercent=value;
      signalStrengthTrack.Invalidate();
      signalStrengthTrack.AccessibleDescription="Wi-Fi signal strength "+signalStrength.Text;''')
one('''        signalTrayFill.Width=0;''',
'''        signalTrayFill.Width=0;
        signalTrayTrack.Invalidate();''')
one('''        signalTrayFill.Width=(signalTrayTrack.ClientSize.Width*v+50)/100;''',
'''        signalTrayFill.Width=0;
        signalTrayTrack.Invalidate();''')
one('''    void UpdateSignalDisplay(string reportedSignal,bool connected){''',
'''    void DrawSignalPulse(Graphics g,Rectangle bounds,int? signalPercent){
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
    void UpdateSignalDisplay(string reportedSignal,bool connected){''')

for q in ['const string AppVersion = "6.22.0";','new VScrollBar{',
          'signalTrayPopup.Deactivate+=','TrackUsageCheckpoint(',
          'downloadSpeed.Text=Rate(rateRx)','uploadSpeed.Text=Rate(rateTx)',
          'MonthTotalFromExistingDays(d)',
          'void RenderUsagePeriod()',
          'void DrawSignalPulse(Graphics g,Rectangle bounds,int? signalPercent)',
          'graphHeader.Controls.Add(dayUsageButton,0,0)',
          'graphHeader.Controls.Add(weekUsageButton,1,0)',
          'graphHeader.Controls.Add(monthUsageButton,2,0)',
          '7-day usage: ','This month: ',
          'down.Text=downloadSpeed.Text','up.Text=uploadSpeed.Text']:
    if q not in s:raise RuntimeError('Missing source guarantee: '+q)
p.write_text(s,encoding='utf-8')
print("PASS: 3 matched usage controls, 3 cards, context totals, ECG Wi-Fi indication and activity-dependent speed arrows")
