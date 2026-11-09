from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(a,b):
    global s
    n=s.count(a)
    if n!=1:raise RuntimeError("Expected exactly one source anchor, got %d: %r"%(n,a[:150]))
    s=s.replace(a,b)

one('const string AppVersion = "6.20.0";','const string AppVersion = "6.21.0";')

# Keep the right header a single flex layout: no giant speed cards.
one('''var head=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=3 };
      head.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,130));
      head.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,208));
      head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));''',
'''var head=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=2 };
      head.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,120));
      head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));''')
one('head.Controls.Remove(status);head.Controls.Add(headerActions,2,0);',
    'head.Controls.Remove(status);head.Controls.Add(headerActions,1,0);')
one('''      var compactSpeeds=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,Margin=new Padding(0),Padding=new Padding(0)};
      compactSpeeds.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
      compactSpeeds.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
      downloadSpeed=HeaderSpeedMetric(compactSpeeds,"DOWNLOAD",0,Color.FromArgb(65,156,235));
      uploadSpeed=HeaderSpeedMetric(compactSpeeds,"UPLOAD",1,Color.FromArgb(52,180,137));
      head.Controls.Add(compactSpeeds,1,0);''',
'''      // The speed values join Appearance and update controls in the same row.
      // Compact coloured direction arrows stay visible as values refresh.
      downloadSpeed=CompactSpeedPill(headerActions,"↓",Color.FromArgb(65,156,235));
      uploadSpeed=CompactSpeedPill(headerActions,"↑",Color.FromArgb(52,180,137));''')
one('''      headerActions.Controls.Add(appearanceButton);
      ShapeAppearanceButton();''',
'''      headerActions.Controls.Add(appearanceButton);
      ShapeAppearanceButton();''')
# Right-to-left flow: update, appearance, download, upload, status-dot+text.
one('''headerActions.Controls.Add(status);headerActions.Controls.Add(statusDot);''',
'''headerActions.Controls.Add(updateButton);
      var statusLine=new FlowLayoutPanel{
        FlowDirection=FlowDirection.LeftToRight,WrapContents=false,
        Width=152,Height=34,Margin=new Padding(3,3,1,3),Padding=new Padding(0)
      };
      status.AutoSize=true;status.Dock=DockStyle.None;
      status.Margin=new Padding(0,8,0,0);
      statusDot.Margin=new Padding(0,7,4,0);
      statusLine.Controls.Add(statusDot);
      statusLine.Controls.Add(status);
      headerActions.Controls.Add(statusLine);''')
# Insert two compact status readouts without modifying live rate data update.
one('    Label HeaderSpeedMetric(TableLayoutPanel parent,string name,int col,Color highlight){',
'''    Label CompactSpeedPill(FlowLayoutPanel parent,string arrow,Color color){
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
      parent.Controls.Add(pill);
      return value;
    }
    Label HeaderSpeedMetric(TableLayoutPanel parent,string name,int col,Color highlight){''')

# Declare the captured spacer before syncDetails; initialize it in the details area.
one('''      Action syncDetails=()=>{''','''      Panel detailsRevealSpacer=null;
      Action syncDetails=()=>{''')

# Scroll-only information: the native scrollbar still operates normally.
one('''      detailScroll.Controls.Add(LabelText("Last update"));''',
'''      // This spacer is relative to the view height, so optional details
      // remain below the fold even when the window is maximized.
      detailsRevealSpacer=new Panel{Width=1,Height=320,Margin=new Padding(0),
        BackColor=Color.Transparent,Tag="tnet-detail-fold"};
      detailScroll.Controls.Add(detailsRevealSpacer);
      detailScroll.Controls.Add(LabelText("Last update"));''')
one('''        detailScroll.Width=viewportWidth;
        detailScroll.Height=320;
        detailScroll.PerformLayout();''',
'''        detailScroll.Width=viewportWidth;
        detailScroll.Height=320;
        if(detailsRevealSpacer!=null)detailsRevealSpacer.Height=viewportHeight+12;
        detailScroll.PerformLayout();''')

# Chart buttons: one row for Live speed and Usage log, a second for three
# adjacent data-period controls. No historical data is fabricated.
one('''    Button graphToggle;''','''    Button graphToggle,dayUsageButton,weekUsageButton,monthUsageButton;
    int currentUsageView=0; // 0 daily, 3 weekly, 4 monthly
    readonly Dictionary<string,double> existingDailyValues=new Dictionary<string,double>();''')
one('''      var graphSurface=new Panel{Dock=DockStyle.Fill};''',
'''      var usagePeriods=new TableLayoutPanel{Dock=DockStyle.Fill,
        ColumnCount=3,RowCount=1,Margin=new Padding(0)};
      for(int i=0;i<3;i++)usagePeriods.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100f/3));
      dayUsageButton=UsagePeriodButton("Daily usage",0);
      weekUsageButton=UsagePeriodButton("Weekly usage",3);
      monthUsageButton=UsagePeriodButton("Monthly usage",4);
      usagePeriods.Controls.Add(dayUsageButton,0,0);
      usagePeriods.Controls.Add(weekUsageButton,1,0);
      usagePeriods.Controls.Add(monthUsageButton,2,0);
      var graphSurface=new Panel{Dock=DockStyle.Fill};''')
one('''      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,40));''',
    '''      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,78));''')
one('''      graphLayout.Controls.Add(graphHeader,0,0);''',
'''      var graphTop=new TableLayoutPanel{Dock=DockStyle.Fill,
        RowCount=2,ColumnCount=1,Margin=new Padding(0)};
      graphTop.RowStyles.Add(new RowStyle(SizeType.Absolute,39));
      graphTop.RowStyles.Add(new RowStyle(SizeType.Absolute,39));
      graphTop.Controls.Add(graphHeader,0,0);
      graphTop.Controls.Add(usagePeriods,0,1);
      graphLayout.Controls.Add(graphTop,0,0);''')
# Replace function in one contiguous segment, preserving existing usage log.
start=s.index('    void SetGraphView(int view){')
end=s.index('    const string UsageLogHeader=',start)
s=s[:start]+'''    Button UsagePeriodButton(string label,int view){
      var button=new Button{Text=label,Dock=DockStyle.Fill,Height=31,
        Margin=new Padding(2),BackColor=Color.FromArgb(32,46,68),
        ForeColor=ink,FlatStyle=FlatStyle.Flat,
        Font=new Font("Segoe UI",8,FontStyle.Regular)};
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
          (appearanceIsLight?Color.FromArgb(215,232,249):Color.FromArgb(48,83,116)):
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
    void SetGraphView(int view){
      showLiveChart=view==1;
      showUsageLog=view==2;
      if(view==0||view==3||view==4)currentUsageView=view;
      chart.Visible=!showLiveChart&&!showUsageLog;
      liveChart.Visible=showLiveChart;
      if(usageGrid!=null)usageGrid.Visible=showUsageLog;
      chartTitle.Text=showLiveChart?"Live speed":showUsageLog?"Usage log":
        currentUsageView==3?"Weekly usage":currentUsageView==4?"Monthly usage":"Daily usage";
      graphToggle.Text=showLiveChart?"Daily usage":"Live speed";
      usageLogToggle.Text=showUsageLog?"Daily usage":"Usage log";
      StyleSelectedUsagePeriod();
      if(showLiveChart)RenderLiveSpeedGraph();
      else if(showUsageLog){
        chartCaption.Text=usageLogError.Length>0?
          "Log saving error: "+usageLogError:
          "Interval end shown in WAT (UTC+01:00)  •  hover time for range  •  click to open CSV";
        chartCaption.Cursor=Cursors.Hand;
      }else{
        chartCaption.Text=currentUsageView==3?"Last six calendar weeks  •  MB":
          currentUsageView==4?"Last six calendar months  •  MB":"Last 7 days  •  MB";
        chartCaption.Cursor=Cursors.Default;
        RenderUsagePeriod();
      }
    }
''' + s[end:]
# Rewrite existing chart polling renderer, maintaining the five-second rate.
start=s.index('''        if((DateTime.UtcNow-lastDailyChartRenderUtc).TotalSeconds>=5){''')
end=s.index('''          lastDailyChartRenderUtc=DateTime.UtcNow;
        }''',start)+len('''          lastDailyChartRenderUtc=DateTime.UtcNow;
        }''')
s=s[:start]+'''        if((DateTime.UtcNow-lastDailyChartRenderUtc).TotalSeconds>=5){
          existingDailyValues.Clear();
          var days=d.ContainsKey("days")?d["days"] as System.Collections.ArrayList:null;
          if(days!=null)foreach(var item in days){
            var record=item as Dictionary<string,object>;
            if(record!=null)existingDailyValues[Str(record,"date")]=Num(record,"total");
          }
          if(!showLiveChart&&!showUsageLog)RenderUsagePeriod();
          lastDailyChartRenderUtc=DateTime.UtcNow;
        }''' + s[end:]
# Keep light/dark look and selected period in sync.
one('''      StyleAppearanceControls(this,useLight);
      if(appearanceButton!=null){''',
'''      StyleAppearanceControls(this,useLight);
      StyleSelectedUsagePeriod();
      if(appearanceButton!=null){''')
# Buttons in the graph should not adopt incorrect system-default hover backgrounds.
one('''      if(button!=null && button!=null && button!=null){''','''      if(button!=null){''')
for value in ['const string AppVersion = "6.21.0";','new VScrollBar{',
              'signalTrayPopup.Deactivate+=','TrackUsageCheckpoint(',
              'downloadSpeed.Text=Rate(rateRx)','uploadSpeed.Text=Rate(rateTx)',
              'MonthTotalFromExistingDays(d)','if(detailsRevealSpacer!=null)detailsRevealSpacer.Height=viewportHeight+12;',
              'CompactSpeedPill(headerActions,"↓"','CompactSpeedPill(headerActions,"↑"',
              'Status','Weekly usage','Monthly usage','void RenderUsagePeriod()',
              'void CheckSystemAppearance()']:
    if value not in s and value!='Status':
        raise RuntimeError("Missing expected source fragment: "+value)
p.write_text(s,encoding="utf-8")
print("PASS v6.21 layout: compact header arrows, aligned live dot, daily/weekly/monthly tabs, scroll-only details")
