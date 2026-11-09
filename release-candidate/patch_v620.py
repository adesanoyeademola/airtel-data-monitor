from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(old,new):
    global s
    n=s.count(old)
    if n!=1: raise RuntimeError("Expected one source anchor, got %d: %r"%(n,old[:160]))
    s=s.replace(old,new)

one('const string AppVersion = "6.19.0";','const string AppVersion = "6.20.0";')
one('Label status, statusDot, sampleAgeLabel, speedSourceLabel, wifi, adapter, signalStrength, last, today, down, up, week, downloadSpeed, uploadSpeed;',
    'Label status, statusDot, sampleAgeLabel, speedSourceLabel, wifi, adapter, signalStrength, last, today, down, up, week, monthly, downloadSpeed, uploadSpeed;')

# Header: separate zones for title / two live speeds / original status and actions.
# All 3 groups remain in the original top header; the former speed row is collapsed.
one('outer.RowStyles.Add(new RowStyle(SizeType.Absolute,92));',
    'outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));')
one('var head=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=2 }; head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,40));head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,60));',
'''var head=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=3 };
      head.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,130));
      head.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,208));
      head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));''')
one('head.Controls.Remove(status);head.Controls.Add(headerActions,1,0);',
    'head.Controls.Remove(status);head.Controls.Add(headerActions,2,0);')
one('''      outer.Controls.Add(head,0,0);
      var metrics=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=4};for(int i=0;i<4;i++)metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,25));
      today=Metric(metrics,"Today",0); down=Metric(metrics,"Downloaded",1); up=Metric(metrics,"Uploaded",2); week=Metric(metrics,"7-day usage",3);outer.Controls.Add(metrics,0,1);
      var rates = new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=2 };
      rates.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));rates.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
      downloadSpeed=SpeedMetric(rates,"Download speed",0);uploadSpeed=SpeedMetric(rates,"Upload speed",1);
      outer.Controls.Add(rates,0,2);''',
'''      var compactSpeeds=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,Margin=new Padding(0),Padding=new Padding(0)};
      compactSpeeds.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
      compactSpeeds.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
      downloadSpeed=HeaderSpeedMetric(compactSpeeds,"DOWNLOAD",0,Color.FromArgb(65,156,235));
      uploadSpeed=HeaderSpeedMetric(compactSpeeds,"UPLOAD",1,Color.FromArgb(52,180,137));
      head.Controls.Add(compactSpeeds,1,0);
      outer.Controls.Add(head,0,0);
      var metrics=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=5};
      for(int i=0;i<5;i++)metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,20));
      today=Metric(metrics,"Today",0); down=Metric(metrics,"Downloaded",1); up=Metric(metrics,"Uploaded",2);
      week=Metric(metrics,"7-day usage",3); monthly=Metric(metrics,"This month",4);
      outer.Controls.Add(metrics,0,1);''')
one('    Label SpeedMetric(TableLayoutPanel parent,string name,int col){',
'''    Label HeaderSpeedMetric(TableLayoutPanel parent,string name,int col,Color highlight){
      var surface=new Panel{Dock=DockStyle.Fill,Margin=new Padding(3,8,3,8),
        Padding=new Padding(8,6,6,4),BackColor=panel,Tag="tnet-header-speed"};
      surface.Resize+=(sender,e)=>RoundSurface(surface,9);
      surface.Controls.Add(new Label{
        Dock=DockStyle.Top,Height=19,Text=name,
        Font=new Font("Segoe UI",8,FontStyle.Bold),
        ForeColor=highlight,TextAlign=ContentAlignment.MiddleLeft});
      var value=new Label{
        Dock=DockStyle.Fill,Text="— Kbps",AutoEllipsis=true,
        Font=new Font("Segoe UI",11,FontStyle.Bold),
        ForeColor=ink,TextAlign=ContentAlignment.MiddleLeft};
      // Dock stacking: put the Top label before the fill label.
      surface.Controls.Add(value);
      value.BringToFront();
      parent.Controls.Add(surface,col,0);
      return value;
    }
    Label SpeedMetric(TableLayoutPanel parent,string name,int col){''')

# Monthly is calculated from existing (non-destructive) daily records in monitor.ps1.
one('week.Text=Bytes(Num(d,"sevenDayTotal"));',
    '''week.Text=Bytes(Num(d,"sevenDayTotal"));
        monthly.Text=Bytes(MonthTotalFromExistingDays(d));''')
one('    void SaveSettings(){',
'''    double MonthTotalFromExistingDays(Dictionary<string,object> data){
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
    void SaveSettings(){''')

# Rounded card corners, applied to the original panel dimensions, not extra padding.
one('''      // One-pixel inset outline gives white cards definition without
      // changing the established dashboard/card dimensions or padding.
      card.Paint+=(sender,e)=>{
        if(!appearanceIsLight)return;
        using(var pen=new Pen(Color.FromArgb(216,226,237),1)){
          Rectangle bounds=card.ClientRectangle;
          if(bounds.Width>1 && bounds.Height>1)
            e.Graphics.DrawRectangle(pen,0,0,bounds.Width-1,bounds.Height-1);
        }
      };''',
'''      card.Resize+=(sender,e)=>RoundSurface(card,15);
      card.Paint+=(sender,e)=>{
        if(!appearanceIsLight || card.Width<3 || card.Height<3)return;
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        using(var path=RoundedPath(new Rectangle(0,0,card.Width-1,card.Height-1),15))
        using(var pen=new Pen(Color.FromArgb(211,224,237),1))
          e.Graphics.DrawPath(pen,path);
      };''')
one('    void ShapeAppearanceButton(){',
'''    GraphicsPath RoundedPath(Rectangle bounds,int diameter){
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
    void ShapeAppearanceButton(){''')
one('''      // Behave like a Windows flyout: clicking away or pressing Esc closes it.''',
'''      signalTrayPopup.Resize+=(sender,e)=>RoundSurface(signalTrayPopup,18);
      RoundSurface(signalTrayPopup,18);
      // Behave like a Windows flyout: clicking away or pressing Esc closes it.''')
one('''      Invalidate(true);
    }
    GraphicsPath RoundedPath''',
'''      Invalidate(true);
    }
    GraphicsPath RoundedPath''')
one('''      foreach(Control child in rootControl.Controls)StyleAppearanceControls(child,light);''',
'''      foreach(Control child in rootControl.Controls)StyleAppearanceControls(child,light);''')

# Colour only numeric metric titles; retain normal accessibility/contrast for values.
one('''stack.Controls.Add(new Label {Text=name,Dock=DockStyle.Fill,ForeColor=muted,TextAlign=ContentAlignment.MiddleLeft},0,0);''',
'''Color labelColor=name=="Today"?Color.FromArgb(135,115,211):
        name=="Downloaded"?Color.FromArgb(66,149,220):
        name=="Uploaded"?Color.FromArgb(45,168,127):
        name=="This month"?Color.FromArgb(45,154,163):
        Color.FromArgb(207,149,55);
      stack.Controls.Add(new Label {Text=name,Dock=DockStyle.Fill,
        ForeColor=labelColor,TextAlign=ContentAlignment.MiddleLeft},0,0);''')

# Action controls stay the original size/position; keep current brand/status indicators.
for q in ['const string AppVersion = "6.20.0";',
          'new VScrollBar{','signalTrayPopup.Deactivate+=',
          'UpdateSignalTrayState(stat,Str(d,"adapterName"),Str(d,"wifiSignal"));',
          'TrackUsageCheckpoint(','downloadSpeed.Text=Rate(rateRx)',
          'uploadSpeed.Text=Rate(rateTx)','MonthTotalFromExistingDays(d)',
          'head.Controls.Add(compactSpeeds,1,0)',
          'RoundSurface(card,15)']:
    if q not in s:raise RuntimeError("Regression: expected retained feature missing "+q)
p.write_text(s,encoding="utf-8")
print("PASS v6.20 patch: header live speeds, calendar-month metric, rounded cards, restrained accents")
