from pathlib import Path
p=Path('work/AirtelMonitorNative.cs')
original=p.read_text(encoding='utf-8-sig')
s=original

def replace_once(old,new):
    global s
    count=s.count(old)
    if count!=1:raise RuntimeError('Expected unique source anchor (%d): %s'%(count,old[:120]))
    s=s.replace(old,new)

replace_once('const string AppVersion = "6.14.0";','const string AppVersion = "6.15.0";')
replace_once(
  '      detailScroll.AutoScrollMinSize=new Size(0,320);',
  '''      detailScroll.AutoScrollMinSize=new Size(0,320);
      // AutoScroll normally hides its bar when the window is maximized and
      // all details fit. Preserve the real, interactive vertical scrollbar
      // by keeping the virtual scroll height slightly larger than the
      // visible viewport, including after resizing the main window.
      detailScroll.SizeChanged+=(sender,e)=>{
        int virtualHeight=Math.Max(320,detailScroll.ClientSize.Height+96);
        if(detailScroll.AutoScrollMinSize.Height!=virtualHeight)
          detailScroll.AutoScrollMinSize=new Size(0,virtualHeight);
      };'''
)

assert s.count('detailScroll.SizeChanged+=(sender,e)=>')==1
assert 'WrapContents=false,AutoScroll=true' in s
assert 'detailScroll.AutoScrollMinSize=new Size(0,320);' in s
assert 'hotspotHeader.Controls.Add(speedSourceLabel,0,2);' in s
assert 'adapter=LabelText("—",11,true);adapter.Margin=new Padding(0,0,0,2);' in s
assert 'signalStrength.Width=68;' in s
assert 'signalStrengthTrack=new Panel{' in s
assert 'signalStrengthTrack.AccessibleDescription=' in s
assert 'pinnedDetails.Controls.Add(signalRow);' in s
assert 'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking")' in s
assert 'downloadSpeed.Text=Rate(rateRx)' in s
assert 'uploadSpeed.Text=Rate(rateTx)' in s
p.write_text(s,encoding='utf-8')
print('PASS: exact UI scrollbar visibility correction; no other UI or data changes')
