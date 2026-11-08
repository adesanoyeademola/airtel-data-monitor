from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def once(old,new):
    global s
    n=s.count(old)
    if n!=1:raise RuntimeError("Expected exactly one UI match %d: %r"%(n,old[:130]))
    s=s.replace(old,new)

once('const string AppVersion = "6.13.0";','const string AppVersion = "6.14.0";')

# Give the hotspot section its own fixed source label, directly after GLOBAL.
# Keep the same total network-card pinned height, and preserve adapter and
# signal strength font, size, bar width/height, and existing color boundaries.
once(
'''      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,66));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,118));''',
'''      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,90));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,94));'''
)
once(
'''      var hotspotHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,Margin=new Padding(0)};
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,25));
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,34));''',
'''      var hotspotHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=3,Margin=new Padding(0)};
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,25));
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,34));
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,27));'''
)
once(
'''      hotspotHeader.Controls.Add(wifi,0,1);layoutNetwork.Controls.Add(hotspotHeader,0,1);
      // Keep the three essential live network readings permanently visible.''',
'''      hotspotHeader.Controls.Add(wifi,0,1);layoutNetwork.Controls.Add(hotspotHeader,0,1);
      // Pinned directly after the GLOBAL hotspot, immediately before Adapter.
      speedSourceLabel=new Label{
        Text="Live speed source: checking...",AutoSize=true,ForeColor=muted,
        Font=new Font("Segoe UI",9),Margin=new Padding(0,0,0,2)
      };
      hotspotHeader.Controls.Add(speedSourceLabel,0,2);
      // Keep the three essential live network readings permanently visible.'''
)
once(
'''      speedSourceLabel=new Label{
        Text="Live speed source: checking...",AutoSize=true,ForeColor=muted,
        Font=new Font("Segoe UI",9),Margin=new Padding(0,0,0,2)
      };
      pinnedDetails.Controls.Add(speedSourceLabel);
      var adapterCaption=''',
'''      var adapterCaption='''
)
# The scrollbar is an actual scroll control, not a decorative drawing.
# Return the original large virtual content area so the track remains visible
# even though adapter and Wi-Fi signal are now fixed above it.
once('      detailScroll.AutoScrollMinSize=new Size(0,160);','      detailScroll.AutoScrollMinSize=new Size(0,320);')

assert s.count('hotspotHeader.Controls.Add(speedSourceLabel,0,2)')==1
assert 'pinnedDetails.Controls.Add(speedSourceLabel)' not in s
assert s.count('detailScroll.Controls.Add(LabelText("Last update"))')==1
assert 'AutoScroll=true' in s
assert 'signalRow.Controls.Add(signalStrength);' in s
assert 'pinnedDetails.Controls.Add(signalRow);' in s
assert 'adapter=LabelText("—",11,true);adapter.Margin=new Padding(0,0,0,2)' in s
assert 'signalStrengthTrack=new Panel{' in s
assert 'signalStrength.Width=68;' in s
assert 'signalStrengthTrack.AccessibleDescription=' in s
assert 'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking")' in s
assert 'downloadSpeed.Text=Rate(rateRx)' in s
assert 'uploadSpeed.Text=Rate(rateTx)' in s
assert 'requestedCounterAdapter=stat=="tracking"' in s
p.write_text(s,encoding="utf-8")
print("Only source label positioning, genuine scroller virtual height, network fixed-row proportions and version modified; adapter/signal sizes preserved.")
