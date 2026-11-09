from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(old,new):
    global s
    n=s.count(old)
    if n!=1:raise RuntimeError("Expected unique v6.25 anchor (%d): %r"%(n,old[:170]))
    s=s.replace(old,new)

one('const string AppVersion = "6.25.0";','const string AppVersion = "6.26.0";')

# Root cause: the old v6.25 column consumes 34px header + 90px hotspot +
# 215px pinnedDetails BEFORE its 34px expanded detail. At ordinary window
# heights, the pinnedDetails row is clipped at the Wi-Fi signal. Compact the
# fixed vertical allocations and give the disclosure a predictable row.
one('''      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,34));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,90));''',
'''      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,32));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,76));''')

one('''      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,35)); // Adapter label
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,42)); // Adapter value
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,37)); // Signal label
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,56)); // Pulse and percentage
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,45)); // Last update arrow
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,0));  // Timestamp on click''',
'''      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,23)); // Adapter label
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,28)); // Adapter value
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,24)); // Signal label
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,40)); // Pulse and percentage
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,32)); // Last update dropdown
      pinnedDetails.RowStyles.Add(new RowStyle(SizeType.Absolute,0));  // Expanded timestamp''')

one('''      adapterCaption.Margin=new Padding(0,10,0,4);''',
    '''      adapterCaption.Margin=new Padding(0,1,0,1);''')
one('''      adapter=LabelText("—",13,true);adapter.Margin=new Padding(0,0,0,12);''',
    '''      adapter=LabelText("—",13,true);adapter.Margin=new Padding(0);''')
one('''      signalCaption.Margin=new Padding(0,2,0,6);''',
    '''      signalCaption.Margin=new Padding(0,0,0,2);''')
one('''      signalRow.Height=44;
      signalRow.Margin=new Padding(0,2,0,12);''',
    '''      signalRow.Height=38;
      signalRow.Margin=new Padding(0);''')
one('''      signalStrengthTrack.Height=35;
      signalStrengthTrack.Margin=new Padding(5,3,7,0);
      signalStrength.Height=35;''',
    '''      signalStrengthTrack.Height=32;
      signalStrengthTrack.Margin=new Padding(5,1,7,0);
      signalStrength.Height=32;''')

one('''      lastUpdateDisclosure.Dock=DockStyle.Fill;
      lastUpdateDisclosure.Margin=new Padding(0,5,0,5);''',
'''      lastUpdateDisclosure.Dock=DockStyle.Fill;
      lastUpdateDisclosure.Margin=new Padding(0,1,0,1);
      lastUpdateDisclosure.Padding=new Padding(0);
      lastUpdateDisclosure.TabStop=true;''')
one('''        pinnedDetails.RowStyles[5].Height=last.Visible?34:0;''',
    '''        pinnedDetails.RowStyles[5].Height=last.Visible?27:0;''')
one('''      last.Width=224;last.Height=28;last.Visible=false;''',
    '''      last.Width=224;last.Height=27;last.Visible=false;''')

# Root cause of horizontal mismatch: nested labels do not share a guaranteed
# x coordinate if one sublayout has nonzero padding/margins. Explicitly zero
# both sublayout paddings and the labels; share a single left inset.
one('''      networkHeader.Controls.Add(networkTitle,0,0);''',
'''      networkHeader.Padding=new Padding(0);
      networkTitle.Padding=new Padding(0);
      networkHeader.Controls.Add(networkTitle,0,0);''')
one('''      hotspotHeader.Controls.Add(hotspotCaption,0,0);''',
'''      hotspotHeader.Padding=new Padding(0);
      hotspotCaption.Padding=new Padding(0);
      hotspotHeader.Controls.Add(hotspotCaption,0,0);''')
one('''      hotspotHeader.Controls.Add(wifi,0,1);layoutNetwork.Controls.Add(hotspotHeader,0,1);''',
'''      wifi.Margin=new Padding(0);
      wifi.Padding=new Padding(0);
      hotspotHeader.Controls.Add(wifi,0,1);layoutNetwork.Controls.Add(hotspotHeader,0,1);''')

# Keep Last update under Wi-Fi, not an offscreen scroll view. Decorative
# scrollbar is preserved unchanged and takes no space from the text column.
for q in (
'const string AppVersion = "6.26.0";',
'pinnedDetails.Controls.Add(lastUpdateDisclosure,0,4);',
'pinnedDetails.Controls.Add(last,0,5);',
'last.Visible=!last.Visible;',
'pinnedDetails.RowStyles[5].Height=last.Visible?27:0;',
'networkTitle.Margin=new Padding(0);',
'hotspotCaption.Margin=new Padding(0);',
'networkHeader.Padding=new Padding(0);',
'hotspotHeader.Padding=new Padding(0);',
'new VScrollBar{',
'detailBar.Enabled=false;',
'void DrawSignalPulse(Graphics g,Rectangle bounds,int? signalPercent)',
'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");',
'TrackUsageCheckpoint('
):
    if q not in s:raise RuntimeError('Missing preserved behaviour: '+q)
p.write_text(s,encoding="utf-8")
print("PASS: compact row allocations reveal Last update, shared left inset for Network/Hotspot")
