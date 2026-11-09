from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def replace_one(old,new):
    global s
    n=s.count(old)
    if n!=1: raise RuntimeError("Expected exactly one source anchor (%d): %r"%(n,old[:150]))
    s=s.replace(old,new)

replace_one('const string AppVersion = "6.29.0";','const string AppVersion = "6.30.0";')

# Screenshot review at 1649x900: the chart footer sat against the Windows
# taskbar. Reserve a real lower safe area instead of allowing it to be clipped.
replace_one('''      var outer=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=1,
        RowCount=6, Padding=new Padding(11), BackColor=bg };''',
'''      var outer=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=1,
        RowCount=6, Padding=new Padding(11,11,11,29), BackColor=bg };''')

# The Network card was vertically stretched to the entire chart height,
# leaving a vast artificial white rectangle. Preserve content and inactive
# scroll decoration but let the card wrap its actual content height.
replace_one('''      middle.Controls.Add(net,1,0);
      middle.SetRowSpan(net,2);''',
'''      var networkDock=new TableLayoutPanel{
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
      fitNetworkCard();''')


replace_one('''    Label nordicSignalMetric;''',
'''    Label nordicSignalMetric;
    Label nordicTodayStat,nordicWeekStat,nordicMonthStat;''')
replace_one('''        latestMonthConsumed=MonthTotalFromExistingDays(d);
        today.Text=Bytes(latestTodayConsumed);''',
'''        latestMonthConsumed=MonthTotalFromExistingDays(d);
        if(nordicTodayStat!=null)nordicTodayStat.Text=Bytes(latestTodayConsumed);
        if(nordicWeekStat!=null)nordicWeekStat.Text=Bytes(latestSevenDayConsumed);
        if(nordicMonthStat!=null)nordicMonthStat.Text=Bytes(latestMonthConsumed);
        today.Text=Bytes(latestTodayConsumed);''')

# Let a no-data reading show a neutral dash, but don't obscure real Wi-Fi
# values or the existing ECG status. The distinct activity colors remain.
replace_one('''      nordicSignalMetric.Font=new Font("Segoe UI",16,FontStyle.Bold);
      nordicSignalMetric.Text="—";''',
'''      nordicSignalMetric.Font=new Font("Segoe UI",16,FontStyle.Bold);
      nordicSignalMetric.Text="—";
      nordicSignalMetric.ForeColor=ink;''')

# Keep the table/footer controls in a clearly allocated bottom row, with
# a readable minimum 34px height regardless of chart contents.
replace_one('''      graphLayout.Controls.Add(chartFooter,0,2);''',
'''      graphLayout.Controls.Add(chartFooter,0,2);
      graphLayout.RowStyles.Clear();
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,43));
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,40));
      chartFooter.Padding=new Padding(0,3,0,0);
      chartFooter.Margin=new Padding(0);''')

for expected in [
    'const string AppVersion = "6.30.0";',
    'Padding=new Padding(11,11,11,29)',
    'middle.SetRowSpan(networkDock,2);',
    'nordicMonthStat.Text=Bytes(latestMonthConsumed)',
    'networkDock.RowStyles[0].Height=Math.Max(260,Math.Min(380,available-205));',
    'graphLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,40));',
    'chartViewDropdown.Items.AddRange',
    'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");',
    'downloadSpeed.Text=Rate(rateRx)',
    'uploadSpeed.Text=Rate(rateTx)',
    'new VScrollBar{',
    'TrackUsageCheckpoint('
]:
    if expected not in s:raise RuntimeError("Required feature missing: "+expected)
p.write_text(s,encoding="utf-8")
print("PASS: Nordic v6.30 footer, Network card and real-data usage overview; monitoring engine unchanged")
