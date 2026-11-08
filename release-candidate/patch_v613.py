from pathlib import Path

p=Path('work/AirtelMonitorNative.cs')
source=p.read_text(encoding='utf-8-sig')
s=source

def one(old,new):
    global s
    count=s.count(old)
    if count!=1:
        raise RuntimeError('Expected one exact UI match (%d): %s'%(count,old[:150]))
    s=s.replace(old,new)

one('const string AppVersion = "6.12.0";','const string AppVersion = "6.13.0";')

one('''      var layoutNetwork=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=3,Margin=new Padding(0)};
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,34));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,66));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Percent,100));''',
'''      var layoutNetwork=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=4,Margin=new Padding(0)};
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,34));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,66));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,118));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Percent,100));''')

one('''      var detailScroll=new FlowLayoutPanel{Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,AutoScroll=true,Margin=new Padding(0),Padding=new Padding(0,0,0,0)};
      detailScroll.AutoScrollMinSize=new Size(0,300);
      speedSourceLabel=new Label{''',
'''      // Keep the three essential live network readings permanently visible.
      // Only the lower, optional details remain in the original scroll area.
      var pinnedDetails=new FlowLayoutPanel{
        Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,
        WrapContents=false,AutoScroll=false,Margin=new Padding(0),
        Padding=new Padding(0)
      };
      speedSourceLabel=new Label{''')

one('''Font=new Font("Segoe UI",9),Margin=new Padding(0,0,0,16)
      };
      detailScroll.Controls.Add(speedSourceLabel);
      detailScroll.Controls.Add(LabelText("Adapter"));adapter=LabelText("—",12,true);detailScroll.Controls.Add(adapter);
      detailScroll.Controls.Add(LabelText("Wi-Fi signal strength"));''',
'''Font=new Font("Segoe UI",9),Margin=new Padding(0,0,0,2)
      };
      pinnedDetails.Controls.Add(speedSourceLabel);
      var adapterCaption=LabelText("Adapter",10);
      adapterCaption.Margin=new Padding(0);
      pinnedDetails.Controls.Add(adapterCaption);
      adapter=LabelText("—",11,true);adapter.Margin=new Padding(0,0,0,2);
      pinnedDetails.Controls.Add(adapter);
      var signalCaption=LabelText("Wi-Fi signal strength",10);
      signalCaption.Margin=new Padding(0);
      pinnedDetails.Controls.Add(signalCaption);''')

one('''      detailScroll.Controls.Add(signalRow);
      detailScroll.Controls.Add(LabelText("Last update"));''',
'''      pinnedDetails.Controls.Add(signalRow);
      layoutNetwork.Controls.Add(pinnedDetails,0,2);
      // Keep the scroll area intact for timestamp and further details.
      var detailScroll=new FlowLayoutPanel{
        Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,
        WrapContents=false,AutoScroll=true,Margin=new Padding(0),
        Padding=new Padding(0)
      };
      detailScroll.AutoScrollMinSize=new Size(0,160);
      detailScroll.Controls.Add(LabelText("Last update"));''')

one('''      detailScroll.Controls.Add(new Label{Text="Measured Windows Wi-Fi traffic, not Airtel SIM balance.",AutoSize=false,Width=245,Height=75,ForeColor=muted,Padding=new Padding(0,8,0,0)});
      layoutNetwork.Controls.Add(detailScroll,0,2);net.Controls.Add(layoutNetwork);middle.Controls.Add(net,0,0);''',
'''      layoutNetwork.Controls.Add(detailScroll,0,3);net.Controls.Add(layoutNetwork);middle.Controls.Add(net,0,0);''')

assert 'var pinnedDetails=new FlowLayoutPanel' in s
assert 'detailScroll.Controls.Add(LabelText("Last update"))' in s
assert 'detailScroll.Controls.Add(signalRow)' not in s
assert 'pinnedDetails.Controls.Add(signalRow)' in s
assert 'Live speed source: checking...' in s
assert 'Measured Windows Wi-Fi traffic, not Airtel SIM balance.' not in s
assert 'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking")' in s
assert 'downloadSpeed.Text=Rate(rateRx)' in s
assert 'uploadSpeed.Text=Rate(rateTx)' in s
assert 'CaptureLiveSpeedSample(stat,liveSampleId' in s
assert 'requestedCounterAdapter=stat=="tracking"' in s
p.write_text(s,encoding='utf-8')
print('T-Net v6.13: pinned source, adapter, Wi-Fi signal; existing detail scroll retained; disclaimer removed')
