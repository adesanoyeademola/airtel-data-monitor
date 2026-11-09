from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(a,b):
    global s
    n=s.count(a)
    if n!=1:raise RuntimeError("Expected one v6.24 UI anchor, got %d: %r"%(n,a[:180]))
    s=s.replace(a,b)

one('const string AppVersion = "6.24.0";','const string AppVersion = "6.25.0";')

# A top-down FlowLayoutPanel clips the disclosure below the Wi-Fi row when
# the card is resized. Reserve six explicit rows for content instead.
one('''      var pinnedDetails=new FlowLayoutPanel{
        Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,
        WrapContents=false,AutoScroll=false,Margin=new Padding(0),
        Padding=new Padding(0)
      };''',
'''      var pinnedDetails=new TableLayoutPanel{
        Dock=DockStyle.Fill,ColumnCount=1,RowCount=6,
        AutoScroll=false,Margin=new Padding(0),Padding=new Padding(0),
        GrowStyle=TableLayoutPanelGrowStyle.FixedSize
      };
      pinnedDetails.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,35)); // Adapter label
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,42)); // Adapter value
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,37)); // Signal label
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,56)); // Pulse and percentage
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,45)); // Last update arrow
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,0));  // Timestamp on click''')

# Map all six controls to their exact row; no invisible overflow clipping.
one('''      pinnedDetails.Controls.Add(adapterCaption);''',
'''      adapterCaption.Dock=DockStyle.Fill;
      pinnedDetails.Controls.Add(adapterCaption,0,0);''')
one('''      pinnedDetails.Controls.Add(adapter);''',
'''      adapter.Dock=DockStyle.Fill;
      pinnedDetails.Controls.Add(adapter,0,1);''')
one('''      pinnedDetails.Controls.Add(signalCaption);''',
'''      signalCaption.Dock=DockStyle.Fill;
      pinnedDetails.Controls.Add(signalCaption,0,2);''')
one('''      pinnedDetails.Controls.Add(signalRow);''',
'''      signalRow.Dock=DockStyle.Fill;
      signalRow.AutoScroll=false;
      pinnedDetails.Controls.Add(signalRow,0,3);''')
one('''      pinnedDetails.Controls.Add(lastUpdateDisclosure);
      pinnedDetails.Controls.Add(last);''',
'''      lastUpdateDisclosure.Dock=DockStyle.Fill;
      lastUpdateDisclosure.Margin=new Padding(0,5,0,5);
      last.Dock=DockStyle.Fill;
      last.Margin=new Padding(0);
      pinnedDetails.Controls.Add(lastUpdateDisclosure,0,4);
      pinnedDetails.Controls.Add(last,0,5);''')
one('''        last.Visible=!last.Visible;
        lastUpdateDisclosure.Text=last.Visible?"▾ Last update":"▸ Last update";
        pinnedDetails.PerformLayout();''',
'''        last.Visible=!last.Visible;
        pinnedDetails.RowStyles[5].Height=last.Visible?34:0;
        lastUpdateDisclosure.Text=last.Visible?"▾ Last update":"▸ Last update";
        pinnedDetails.PerformLayout();
        pinnedDetails.Invalidate(true);''')

# Don't pin the disclosure in a clipped region: use all of the available
# Network card row, while preserving existing status/adapter/signal geometry.
one('''      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,0));''',
'''      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,0));''')

# Ensure Network / Hotspot are exact left-aligned peers. GLOBAL stays below
# Hotspot with the current design; neither label receives a horizontal offset.
one('''      var networkTitle=LabelText("Network",17,true);networkTitle.Dock=DockStyle.Fill;''',
'''      var networkTitle=LabelText("Network",17,true);
      networkTitle.Dock=DockStyle.Fill;
      networkTitle.Margin=new Padding(0);
      networkTitle.TextAlign=ContentAlignment.MiddleLeft;''')
one('''      hotspotHeader.Controls.Add(LabelText("Hotspot"),0,0);''',
'''      var hotspotCaption=LabelText("Hotspot");
      hotspotCaption.Dock=DockStyle.Fill;
      hotspotCaption.Margin=new Padding(0);
      hotspotCaption.TextAlign=ContentAlignment.MiddleLeft;
      hotspotHeader.Controls.Add(hotspotCaption,0,0);''')

# Pin the last-update row above any other leftover zero-height legacy area.
# The scrollbar remains the existing decorative element; we do not remove it.
one('''      layoutNetwork.Controls.Add(pinnedDetails,0,2);''',
'''      layoutNetwork.Controls.Add(pinnedDetails,0,2);
      pinnedDetails.BringToFront();''')

for token in (
    'const string AppVersion = "6.25.0";',
    'var pinnedDetails=new TableLayoutPanel{',
    'pinnedDetails.Controls.Add(lastUpdateDisclosure,0,4);',
    'pinnedDetails.Controls.Add(last,0,5);',
    'pinnedDetails.RowStyles[5].Height=last.Visible?34:0;',
    'networkTitle.Margin=new Padding(0);',
    'hotspotCaption.Margin=new Padding(0);',
    'new VScrollBar{',
    'detailBar.Enabled=false;',
    'signalStrengthTrack.Height=35;',
    'void DrawSignalPulse(Graphics g,Rectangle bounds,int? signalPercent)',
    'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");',
    'TrackUsageCheckpoint(',
    'chartViewDropdown.Items.AddRange'
):
    if token not in s:raise RuntimeError('Missing required layout/monitor feature '+token)

p.write_text(s,encoding="utf-8")
print("v6.25: fixed-row Network details, clickable arrow with visible timestamp, matching left alignment; engine unaffected")
