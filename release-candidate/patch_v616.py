from pathlib import Path

p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")

def one(old,new):
    global s
    n=s.count(old)
    if n!=1:raise RuntimeError("Expected exactly one match (got %d): %r"%(n,old[:175]))
    s=s.replace(old,new)

one('const string AppVersion = "6.15.0";','const string AppVersion = "6.16.0";')

# Keep both the green/yellow/red bar's 210px width and its 9px height.
# Adjust horizontal margins only; preserve total horizontal margin (12 px).
one('Margin=new Padding(0,8,12,0)',
    'Margin=new Padding(5,8,7,0)')

# Reuse all existing controls and scrollable content; swap the conditional
# FlowLayoutPanel scrollbar for a dedicated, always-present native VScrollBar.
old_scroll='''      var detailScroll=new FlowLayoutPanel{
        Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,
        WrapContents=false,AutoScroll=true,Margin=new Padding(0),
        Padding=new Padding(0)
      };
      detailScroll.AutoScrollMinSize=new Size(0,320);
      // AutoScroll normally hides its bar when the window is maximized and
      // all details fit. Preserve the real, interactive vertical scrollbar
      // by keeping the virtual scroll height slightly larger than the
      // visible viewport, including after resizing the main window.
      detailScroll.SizeChanged+=(sender,e)=>{
        int virtualHeight=Math.Max(320,detailScroll.ClientSize.Height+96);
        if(detailScroll.AutoScrollMinSize.Height!=virtualHeight)
          detailScroll.AutoScrollMinSize=new Size(0,virtualHeight);
      };'''
new_scroll='''      // Genuine, permanently visible WinForms scrollbar. AutoScroll alone
      // disappears when the parent layout is maximized or the viewport
      // becomes too small to expose its native scrolling area.
      var detailViewport=new Panel{
        Dock=DockStyle.Fill,AutoScroll=false,
        Margin=new Padding(0),Padding=new Padding(0)
      };
      var detailScroll=new FlowLayoutPanel{
        FlowDirection=FlowDirection.TopDown,WrapContents=false,
        AutoScroll=false,Margin=new Padding(0),Padding=new Padding(0),
        Location=new Point(0,0),AutoSize=false
      };
      detailViewport.Controls.Add(detailScroll);
      var detailBar=new VScrollBar{
        Width=SystemInformation.VerticalScrollBarWidth,
        Height=66,SmallChange=16,LargeChange=30,
        Minimum=0,Maximum=320,Visible=true,
        Anchor=AnchorStyles.Right|AnchorStyles.Bottom
      };
      // Real scrollbar movement updates the clipped detail content position.
      detailBar.ValueChanged+=(sender,e)=>detailScroll.Top=-detailBar.Value;
      Action syncDetails=()=>{
        int viewportWidth=Math.Max(1,detailViewport.ClientSize.Width);
        int viewportHeight=Math.Max(1,detailViewport.ClientSize.Height);
        detailScroll.Width=viewportWidth;
        detailScroll.Height=320;
        detailScroll.PerformLayout();
        int contentHeight=0;
        foreach(Control c in detailScroll.Controls)
          contentHeight=Math.Max(contentHeight,c.Bottom+c.Margin.Bottom);
        contentHeight=Math.Max(contentHeight,viewportHeight);
        detailScroll.Height=contentHeight;
        int scrollMax=Math.Max(0,contentHeight-viewportHeight);
        detailBar.LargeChange=Math.Max(1,Math.Min(30,viewportHeight));
        detailBar.Maximum=scrollMax+detailBar.LargeChange-1;
        if(detailBar.Value>scrollMax)detailBar.Value=scrollMax;
        detailScroll.Top=-detailBar.Value;
        // The real scrollbar stays visible, even when there is nothing
        // further to scroll. Do not fake or synthesize scrollable data.
        detailBar.Enabled=scrollMax>0;
      };
      detailViewport.SizeChanged+=(sender,e)=>syncDetails();'''
one(old_scroll,new_scroll)

one('''      layoutNetwork.Controls.Add(detailScroll,0,3);net.Controls.Add(layoutNetwork);middle.Controls.Add(net,0,0);''',
'''      layoutNetwork.Controls.Add(detailViewport,0,3);
      net.Controls.Add(layoutNetwork);
      // Dock the actual vertical scroll control at the lower right of the
      // Network card, independent of the potentially clipped details row.
      net.Controls.Add(detailBar);
      Action positionDetailBar=()=>{
        detailBar.Location=new Point(
          Math.Max(0,net.ClientSize.Width-net.Padding.Right-detailBar.Width-4),
          Math.Max(0,net.ClientSize.Height-net.Padding.Bottom-detailBar.Height+3));
        detailBar.BringToFront();
      };
      net.SizeChanged+=(sender,e)=>{positionDetailBar();syncDetails();};
      positionDetailBar();
      syncDetails();
      middle.Controls.Add(net,0,0);''')

# Align the footer with the outer edge of PanelCard (not the inner text).
one('''outer.Controls.Add(new Label{Dock=DockStyle.Fill,Text="Monitoring runs while this app is open or minimized to the tray.",ForeColor=muted,TextAlign=ContentAlignment.MiddleLeft,Font=new Font("Segoe UI",9)},0,5);''',
'''outer.Controls.Add(new Label{Dock=DockStyle.Fill,Text="Monitoring runs while this app is open or minimized to the tray.",ForeColor=muted,TextAlign=ContentAlignment.MiddleLeft,Font=new Font("Segoe UI",9),Margin=new Padding(8,0,0,0)},0,5);''')

# Guard against changes to the pinned layout and user data logic.
assert s.count('detailBar=new VScrollBar')==1
assert s.count('detailBar.ValueChanged+=(sender,e)=>detailScroll.Top=-detailBar.Value;')==1
assert s.count('detailBar.BringToFront();')==1
assert s.count('Margin=new Padding(5,8,7,0)')==1
assert 'signalStrengthTrack=new Panel{' in s
assert 'Width=210,Height=9' in s
assert 'signalStrength.Width=68;' in s
assert 'adapter=LabelText("—",11,true);adapter.Margin=new Padding(0,0,0,2);' in s
assert 'hotspotHeader.Controls.Add(speedSourceLabel,0,2)' in s
assert 'pinnedDetails.Controls.Add(signalRow)' in s
assert 'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking")' in s
assert 'downloadSpeed.Text=Rate(rateRx)' in s
assert 'uploadSpeed.Text=Rate(rateTx)' in s
assert 'TrackUsageCheckpoint(' in s
assert 'requestedCounterAdapter=stat=="tracking"' in s
assert 'const string AppVersion = "6.16.0";' in s
p.write_text(s,encoding="utf-8")
print("PASS: real scrollbar, +5px signal-bar alignment, footer card-edge alignment, no monitoring changes")
