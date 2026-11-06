from pathlib import Path
f=Path("work/AirtelMonitorNative.cs")
s=f.read_text(encoding="utf-8")

def one(old,new):
    global s
    n=s.count(old)
    if n!=1:
        raise RuntimeError("Expected exactly one source match (%d) for %r"%(n,old[:125]))
    s=s.replace(old,new)

one('const string AppVersion = "6.8.0";','const string AppVersion = "6.9.0";')
one('''    bool showLiveChart = false;''',
'''    bool showLiveChart = false;
    bool showUsageLog = false;
    Button usageLogToggle;
    DataGridView usageGrid;
    DateTime logWindowStart=DateTime.MinValue;
    DateTime logLastObserved=DateTime.MinValue;
    double logWindowRx=0, logWindowTx=0, logLastRx=0, logLastTx=0;
    readonly string usageLogPath=Path.Combine(
      Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
      "AirtelDataMonitor","data","usage-timeline.csv");
    string usageLogError="";''')

one('''      BuildUi();
      // The explicit "Restart service"''',
'''      BuildUi();
      LoadUsageLog();
      // The explicit "Restart service"''')

# Position the speed-source line slightly higher, between the hotspot name
# and Adapter. Only the left Network detail padding and the label margin change.
one('''WrapContents=false,AutoScroll=true,Margin=new Padding(0),Padding=new Padding(0,8,0,0)};''',
    '''WrapContents=false,AutoScroll=true,Margin=new Padding(0),Padding=new Padding(0,0,0,0)};''')
one('''Font=new Font("Segoe UI",9),Margin=new Padding(0,1,0,9)''',
    '''Font=new Font("Segoe UI",9),Margin=new Padding(0,0,0,16)''')

# Add a third, readable timestamped view, without touching the existing
# Daily usage chart and Live speed graph drawing or rate selection.
start=s.index('      graphToggle.Click+=(sender,e)=>{')
end=s.index('      var graphSurface=new Panel{Dock=DockStyle.Fill};',start)
old=s[start:end]
assert 'showLiveChart=!showLiveChart;' in old
assert 'graphHeader.Controls.Add(graphToggle,1,0);' in old
s=s[:start]+'''      graphToggle.Click+=(sender,e)=>SetGraphView(showLiveChart?0:1);
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
''' +s[end:]

one('''      graphSurface.Controls.Add(chart);graphSurface.Controls.Add(liveChart);
      chartCaption=new Label''',
'''      graphSurface.Controls.Add(chart);graphSurface.Controls.Add(liveChart);
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
      usageGrid.Columns.Add("recorded","Recorded at");
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
      chartCaption=new Label''')

one('''        Font=new Font("Segoe UI",8),TextAlign=ContentAlignment.MiddleLeft};
      var graphLayout=''', 
'''        Font=new Font("Segoe UI",8),TextAlign=ContentAlignment.MiddleLeft};
      chartCaption.Click+=(sender,e)=>{
        if(!showUsageLog || !File.Exists(usageLogPath))return;
        try{Process.Start("explorer.exe","/select,\\\""+usageLogPath+"\\\"");}
        catch(Exception err){MessageBox.Show("Could not open usage log: "+err.Message);}
      };
      var graphLayout=''')

# Only UI presentation methods and separately persisted timeline are added.
anchor='    void ApplyUsage(Dictionary<string,object> d){'
methods=r'''    void SetGraphView(int view){
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
          "Timestamped checkpoints (about 1 min)  •  click to open CSV";
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
      int index=usageGrid.Rows.Insert(0,
        end.LocalDateTime.ToString("yyyy-MM-dd HH:mm:ss",CultureInfo.InvariantCulture),
        period,Bytes(received),Bytes(sent),Bytes(used),Bytes(running));
      usageGrid.Rows[index].Cells[0].ToolTipText=
        (baseline?"Starting checkpoint; no interval usage":
          "Measured interval: "+start.LocalDateTime.ToString("yyyy-MM-dd HH:mm:ss")+
          " to "+end.LocalDateTime.ToString("yyyy-MM-dd HH:mm:ss"))+
        " (PC local time)";
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
        start.ToString("yyyy-MM-ddTHH:mm:sszzz",CultureInfo.InvariantCulture),
        end.ToString("yyyy-MM-ddTHH:mm:sszzz",CultureInfo.InvariantCulture),
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
          chartCaption.Text="Saved "+end.ToString("HH:mm:ss")+
            "  •  checkpoints about every minute  •  click to open CSV";
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
      DateTime observed=sampleUtc.ToLocalTime();
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
'''
one(anchor,methods+anchor)

# The app polls cumulative engine counters on the UI thread after an async
# response, and only logs new, fresh service samples (not repeated 500ms reads).
one('''        bool legacyService = stat=="tracking" && !timestampValid;''',
'''        TrackUsageCheckpoint(stat,fresh,sampleId,sampleUtc,rx,tx);
        bool legacyService = stat=="tracking" && !timestampValid;''')

assert 'const string AppVersion = "6.9.0";' in s
assert 'downloadSpeed.Text=Rate(rateRx);' in s
assert 'uploadSpeed.Text=Rate(rateTx);' in s
assert 'CaptureLiveSpeedSample(stat,liveSampleId' in s
assert 'wifi.Text=HotspotLabel(currentSsid);' in s
assert 'Live speed source: Windows counters' in s
assert 'usage-timeline.csv' in s
f.write_text(s,encoding="utf-8")
print("T-Net v6.9: source label spacing and independently saved timestamped usage log; engine unchanged.")
