from pathlib import Path
f=Path("work/AirtelMonitorNative.cs")
s=f.read_text(encoding="utf-8")

def once(old,new):
    global s
    n=s.count(old)
    if n!=1: raise RuntimeError("Expected exactly one match (%s): %r" % (n,old[:120]))
    s=s.replace(old,new)

once('const string AppVersion = "6.1.0";','const string AppVersion = "6.2.0";')
once('    Chart chart;','''    Chart chart, liveChart;
    Button graphToggle;
    Label chartTitle, chartCaption;
    bool showLiveChart = false;
    long lastRecordedGraphSampleId=-1;
    DateTime lastRecordedGraphTimeUtc=DateTime.MinValue;
    readonly List<LiveRateSample> liveRateHistory = new List<LiveRateSample>();
    class LiveRateSample {
      public DateTime AtUtc;
      public double DownloadKbps, UploadKbps;
      public bool Valid;
    }''')

start=s.index('      var chPanel=PanelCard();')
end=s.index('      settings=PanelCard();',start)
old=s[start:end]
assert 'new Series("Data")' in old and 'LabelText("Daily usage"' in old and 'outer.Controls.Add(middle,0,3);' in old, "Unexpected existing daily chart block"
new=r'''      var chPanel=PanelCard();
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
      graphToggle.Click+=(sender,e)=>{
        showLiveChart=!showLiveChart;
        chart.Visible=!showLiveChart;liveChart.Visible=showLiveChart;
        chartTitle.Text=showLiveChart?"Live speed":"Daily usage";
        graphToggle.Text=showLiveChart?"Daily usage":"Live speed";
        if(showLiveChart)RenderLiveSpeedGraph();
        else chartCaption.Text="Last 7 days  •  MB";
      };
      var graphHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1};
      graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,120));
      graphHeader.Controls.Add(chartTitle,0,0);graphHeader.Controls.Add(graphToggle,1,0);
      var graphSurface=new Panel{Dock=DockStyle.Fill};
      graphSurface.Controls.Add(chart);graphSurface.Controls.Add(liveChart);
      chartCaption=new Label{Text="Last 7 days  •  MB",Dock=DockStyle.Fill,ForeColor=muted,
        Font=new Font("Segoe UI",8),TextAlign=ContentAlignment.MiddleLeft};
      var graphLayout=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=3,ColumnCount=1};
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,40));
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,22));
      graphLayout.Controls.Add(graphHeader,0,0);
      graphLayout.Controls.Add(graphSurface,0,1);
      graphLayout.Controls.Add(chartCaption,0,2);
      chPanel.Controls.Add(graphLayout);middle.Controls.Add(chPanel,1,0);
      outer.Controls.Add(middle,0,3);
'''
s=s[:start]+new+s[end:]

# Render recent samples using their actual engine sample timestamps.
# Invalid samples are empty points, NEVER zeros; long gaps break the line.
anchor='    void RefreshUsage(){'
assert s.count(anchor)==1
methods=r'''    void CaptureLiveSpeedSample(string stat,long sampleId,DateTime sampleTime,
                                bool timeValid,bool fresh,bool rateValid,
                                double rxBytesPerSecond,double txBytesPerSecond){
      if(timeValid && sampleId>0 && (sampleId!=lastRecordedGraphSampleId ||
         sampleTime.ToUniversalTime()!=lastRecordedGraphTimeUtc)){
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
      if(showLiveChart)RenderLiveSpeedGraph();
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
'''
s=s.replace(anchor,methods+anchor)

once('''        currentSsid=Str(d,"currentSsid");''',
'''        CaptureLiveSpeedSample(stat,sampleId,sampleUtc,timestampValid,fresh,valid,
                               Num(d,"rateRxBps"),Num(d,"rateTxBps"));
        currentSsid=Str(d,"currentSsid");''')

# Validate no changes to engine or persisted usage logic.
assert 'chart.Series[0].Points.Clear()' in s
assert 'PulseIndicator()' in s and 'AutoRecoverEngine()' in s
assert 'const string AppVersion = "6.2.0";' in s
assert 'Last measured ' in s and 'Last 7 days  •  MB' in s
f.write_text(s,encoding="utf-8")
print("T-Net v6.2: 90-second measured upload/download chart with timestamped samples and preserved daily chart.")
