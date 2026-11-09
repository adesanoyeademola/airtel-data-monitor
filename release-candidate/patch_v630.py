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
'''      var networkDock=new Panel{
        Dock=DockStyle.Fill,Margin=new Padding(0),Padding=new Padding(0),
        BackColor=bg
      };
      net.Dock=DockStyle.Top;
      net.Height=414;
      networkDock.Controls.Add(net);
      middle.Controls.Add(networkDock,1,0);
      middle.SetRowSpan(networkDock,2);
      Action fitNetworkCard=()=>{
        int maxHeight=Math.Max(260,networkDock.ClientSize.Height-12);
        net.Height=Math.Min(414,maxHeight);
      };
      networkDock.SizeChanged+=(sender,e)=>fitNetworkCard();
      fitNetworkCard();''')

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
    'net.Height=Math.Min(414,maxHeight);',
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
print("PASS: Nordic v6.30 layout safe-area and compact Network card patch; engine unmodified")
