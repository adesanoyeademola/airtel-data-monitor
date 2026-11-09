from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(a,b):
    global s
    n=s.count(a)
    if n!=1: raise RuntimeError("Expected one anchor, found %d: %r"%(n,a[:160]))
    s=s.replace(a,b)

one('const string AppVersion = "6.23.0";','const string AppVersion = "6.24.0";')

# The empty lower half was an unused scrolling viewport with an artificial
# fold spacer. Give this space to the real adapter/signal/disclosure content.
# Keep the original scrollbar at the bottom-right as a visual, inert element.
one('''      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,94));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Percent,100));''',
'''      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,0));''')
one('''      detailBar.ValueChanged+=(sender,e)=>detailScroll.Top=-detailBar.Value;''',
'''      // Decorative scrollbar only. Network details no longer scroll.
      detailBar.Enabled=false;
      detailBar.ValueChanged+=(sender,e)=>{ /* intentionally non-interactive */ };''')
one('''        detailBar.Enabled=scrollMax>0;''',
'''        // Keep scrollbar permanently decorative even after resizing.
        detailBar.Enabled=false;''')

# Remove the huge reveal spacer and allow the Last update disclosure to
# live directly below signal strength, inside the expanded network body.
one('''      detailScroll.Controls.Add(detailsRevealSpacer);''',
'''      // No artificial blank scroll fold in the expanded Network card.''')
one('''      detailScroll.Controls.Add(lastUpdateDisclosure);
      detailScroll.Controls.Add(last);''',
'''      pinnedDetails.Controls.Add(lastUpdateDisclosure);
      pinnedDetails.Controls.Add(last);''')
one('''      detailsRevealSpacer=new Panel{Width=1,Height=320,Margin=new Padding(0),
        BackColor=Color.Transparent,Tag="tnet-detail-fold"};''',
'''      // Previously used to keep Last update off-screen; no longer necessary.''')
one('''        if(detailsRevealSpacer!=null)detailsRevealSpacer.Height=viewportHeight+12;''',
'''        // The hidden legacy viewport is empty; no reveal spacer required.''')
one('''      Panel detailsRevealSpacer=null;
      Action syncDetails=()=>{''',
'''      Action syncDetails=()=>{''')

# Use more of the available Network card area for the actual content, not a
# new fake metric. In particular, emphasise the ECG waveform + percentage.
one('''      adapterCaption.Margin=new Padding(0);''',
'''      adapterCaption.Margin=new Padding(0,10,0,4);''')
one('''      adapter=LabelText("—",12,true);adapter.Margin=new Padding(0,0,0,2);''',
'''      adapter=LabelText("—",13,true);adapter.Margin=new Padding(0,0,0,12);''')
one('''      signalCaption.Margin=new Padding(0);''',
'''      signalCaption.Margin=new Padding(0,2,0,6);''')
one('''      pinnedDetails.Controls.Add(signalRow);''',
'''      signalRow.Height=44;
      signalRow.Margin=new Padding(0,2,0,12);
      signalStrengthTrack.Height=35;
      signalStrengthTrack.Margin=new Padding(5,3,7,0);
      signalStrength.Height=35;
      pinnedDetails.Controls.Add(signalRow);''')
one('''        Width=224,Height=30,Margin=new Padding(0,4,0,0),''',
'''        Width=224,Height=34,Margin=new Padding(0,12,0,0),''')

# When the user clicks the arrow, show the existing live last-update label
# directly below it. The timestamp continues updating via the original API.
one('''        last.Visible=!last.Visible;
        lastUpdateDisclosure.Text=last.Visible?"▾ Last update":"▸ Last update";''',
'''        last.Visible=!last.Visible;
        lastUpdateDisclosure.Text=last.Visible?"▾ Last update":"▸ Last update";
        pinnedDetails.PerformLayout();''')

# A decorative scroll control should also not receive keyboard focus.
one('''      detailBar.BringToFront();''',
'''      detailBar.BringToFront();
        detailBar.TabStop=false;''')

for needle in [
  'const string AppVersion = "6.24.0";',
  'layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,0));',
  'pinnedDetails.Controls.Add(lastUpdateDisclosure);',
  'pinnedDetails.Controls.Add(last);',
  'detailBar.Enabled=false;',
  'lastUpdateDisclosure.Text=last.Visible?',
  'signalStrengthTrack.Height=35;',
  'new VScrollBar{',
  'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");',
  'TrackUsageCheckpoint(',
  'void DrawSignalPulse(Graphics g,Rectangle bounds,int? signalPercent)',
  'chartViewDropdown.Items.AddRange',
]:
    if needle not in s:raise RuntimeError('Missing required UI or monitoring behaviour '+needle)
p.write_text(s,encoding='utf-8')
print('PASS: network card enlarged, no dead space, inert decorative scroll, Last update expands in place')
