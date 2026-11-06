from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8")

def one(old,new):
    global s
    n=s.count(old)
    if n!=1:raise RuntimeError(f"Expected one match: {n}: {old[:120]!r}")
    s=s.replace(old,new)

one('const string AppVersion = "6.7.0";','const string AppVersion = "6.8.0";')
one(
 '    Label status, statusDot, sampleAgeLabel, wifi, adapter, last, today, down, up, week, downloadSpeed, uploadSpeed;',
 '    Label status, statusDot, sampleAgeLabel, speedSourceLabel, wifi, adapter, last, today, down, up, week, downloadSpeed, uploadSpeed;'
)
one('''      detailScroll.Controls.Add(LabelText("Adapter"));adapter=LabelText("—",12,true);detailScroll.Controls.Add(adapter);''',
'''      speedSourceLabel=new Label{
        Text="Live speed source: checking...",AutoSize=true,ForeColor=muted,
        Font=new Font("Segoe UI",9),Margin=new Padding(0,1,0,9)
      };
      detailScroll.Controls.Add(speedSourceLabel);
      detailScroll.Controls.Add(LabelText("Adapter"));adapter=LabelText("—",12,true);detailScroll.Controls.Add(adapter);''')
one('''        bool liveFresh=useNative || fresh;''',
'''        if(speedSourceLabel!=null){
          speedSourceLabel.Text=stat!="tracking"?"Live speed source: not connected":
            useNative?"Live speed source: Windows counters":
            "Live speed source: adapter fallback";
          speedSourceLabel.ForeColor=useNative?Color.FromArgb(79,212,161):
            Color.FromArgb(171,187,207);
        }
        bool liveFresh=useNative || fresh;''')
assert 'downloadSpeed.Text=Rate(rateRx)' in s
assert 'uploadSpeed.Text=Rate(rateTx)' in s
assert 'CaptureLiveSpeedSample(stat,liveSampleId' in s
assert 'wifi.Text=HotspotLabel(currentSsid);' in s
p.write_text(s,encoding="utf-8")
print("T-Net v6.8 speed-source diagnostic; speed formulas and counters unchanged")
