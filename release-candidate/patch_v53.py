from pathlib import Path
p=Path('work')
f=p/'AirtelMonitorNative.cs'
s=f.read_text(encoding='utf-8')
def swap(a,b):
 global s
 if s.count(a)!=1: raise RuntimeError('Expected one match: '+a[:80])
 s=s.replace(a,b)
def region(a,z,new):
 global s
 i=s.index(a); j=s.index(z,i)+len(z)
 s=s[:i]+new+s[j:]
swap('const string AppVersion = "5.2.0";','const string AppVersion = "5.3.0";')
swap('    DateTime previousRateReceivedUtc = DateTime.MinValue;',"""    DateTime previousRateReceivedUtc = DateTime.MinValue;
    DateTime previousUsageReceivedUtc = DateTime.MinValue;
    double previousUsageRx = -1, previousUsageTx = -1;""")
region('      var net=PanelCard();','middle.Controls.Add(net,0,0);',"""      var net=PanelCard();
      var layoutNetwork=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=3,Margin=new Padding(0)};
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,34));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Absolute,66));
      layoutNetwork.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      var networkTitle=LabelText("Network",15,true);networkTitle.Dock=DockStyle.Fill;
      layoutNetwork.Controls.Add(networkTitle,0,0);
      var hotspotHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,Margin=new Padding(0)};
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,25));
      hotspotHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,34));
      hotspotHeader.Controls.Add(LabelText("Hotspot"),0,0);
      wifi=LabelText("—",12,true);wifi.AutoEllipsis=true;wifi.AutoSize=false;wifi.Dock=DockStyle.Fill;
      hotspotHeader.Controls.Add(wifi,0,1);layoutNetwork.Controls.Add(hotspotHeader,0,1);
      var detailScroll=new FlowLayoutPanel{Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,AutoScroll=true,Margin=new Padding(0),Padding=new Padding(0,8,0,0)};
      detailScroll.AutoScrollMinSize=new Size(0,300);
      detailScroll.Controls.Add(LabelText("Adapter"));adapter=LabelText("—",12,true);detailScroll.Controls.Add(adapter);
      detailScroll.Controls.Add(LabelText("Last update"));last=LabelText("—");detailScroll.Controls.Add(last);
      detailScroll.Controls.Add(new Label{Text="Scroll for more details",AutoSize=true,ForeColor=muted,Padding=new Padding(0,12,0,5)});
      detailScroll.Controls.Add(new Label{Text="Measured Windows Wi-Fi traffic, not Airtel SIM balance.",AutoSize=false,Width=245,Height=75,ForeColor=muted,Padding=new Padding(0,8,0,0)});
      layoutNetwork.Controls.Add(detailScroll,0,2);net.Controls.Add(layoutNetwork);middle.Controls.Add(net,0,0);""")
region('        if(stat!="tracking" || !valid || !fresh){','        currentSsid=Str(d,"currentSsid");',"""        // Use native byte-counter rates first, then recorded usage deltas if the
        // sample validity/timestamp is unavailable. No invented traffic values.
        DateTime nowUtc=DateTime.UtcNow;
        bool fallbackValid=false;
        double fallbackRx=0,fallbackTx=0;
        if(stat=="tracking" && previousUsageRx>=0 && previousUsageTx>=0){
          double seconds=(nowUtc-previousUsageReceivedUtc).TotalSeconds;
          double diffRx=rx-previousUsageRx,diffTx=tx-previousUsageTx;
          if(seconds>0.5 && seconds<30 && diffRx>=0 && diffTx>=0){
            fallbackRx=diffRx/seconds;fallbackTx=diffTx/seconds;fallbackValid=true;
          }
        }
        if(stat!="tracking"){
          downloadSpeed.Text="— KB/s";uploadSpeed.Text="— KB/s";
          previousUsageRx=-1;previousUsageTx=-1;previousRateSampleId=-1;
        } else {
          if(valid && fresh){
            downloadSpeed.Text=Rate(Num(d,"rateRxBps"));
            uploadSpeed.Text=Rate(Num(d,"rateTxBps"));
            previousRateSampleId=sampleId;previousRateReceivedUtc=nowUtc;
          } else if(fallbackValid){
            downloadSpeed.Text=Rate(fallbackRx);
            uploadSpeed.Text=Rate(fallbackTx);
          } else {
            downloadSpeed.Text="Measuring...";uploadSpeed.Text="Measuring...";
          }
          previousUsageRx=rx;previousUsageTx=tx;previousUsageReceivedUtc=nowUtc;
        }
        currentSsid=Str(d,"currentSsid");""")
swap('previousRateSampleId=-1;downloadSpeed.Text="— KB/s";uploadSpeed.Text="— KB/s";','previousRateSampleId=-1;previousUsageRx=-1;previousUsageTx=-1;downloadSpeed.Text="— KB/s";uploadSpeed.Text="— KB/s";')
f.write_text(s,encoding='utf-8')
print('Prepared Airtel Data Monitor v5.3.0')
