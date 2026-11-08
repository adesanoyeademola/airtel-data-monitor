from pathlib import Path

p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")

def one(old,new):
    global s
    n=s.count(old)
    if n!=1: raise RuntimeError("Expected one source anchor (found %d): %r"%(n,old[:170]))
    s=s.replace(old,new)

one('const string AppVersion = "6.16.0";','const string AppVersion = "6.17.0";')

one('''    NotifyIcon tray;
    System.Windows.Forms.Timer refreshTimer;''',
'''    NotifyIcon tray;
    // Tray mini-popup: presentation only. Reuses the main dashboard's
    // already-polled Wi-Fi signal and never starts another monitoring service.
    Form signalTrayPopup;
    Label signalTrayStatus,signalTrayAdapter,signalTrayPercent;
    Panel signalTrayTrack,signalTrayFill;
    string signalTrayLastAdapter="";
    string signalTrayLastStatus="Waiting for connection";
    int? signalTrayLastPercent=null;
    bool signalTrayConnected=false;
    DateTime signalTrayLastAutoHideUtc=DateTime.MinValue;
    System.Windows.Forms.Timer refreshTimer;''')

one('''tray.ContextMenuStrip=menu; tray.DoubleClick+=(s,e)=>ShowWindow();''',
'''tray.ContextMenuStrip=menu;
      tray.MouseClick+=(sender,e)=>{
        if(e.Button==MouseButtons.Left)ToggleSignalTrayPopup();
      };
      // Preserve the existing double-click shortcut for the main monitor.
      tray.DoubleClick+=(s,e)=>ShowWindow();''')

one('''        UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");''',
'''        UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");
        // Same Windows-provided API data as the dashboard; no extra sampling.
        UpdateSignalTrayState(stat,Str(d,"adapterName"),Str(d,"wifiSignal"));''')

one('''    void SetIndicator(string label,int state){
      indicatorState=state;status.Text=label;''',
'''    void SetIndicator(string label,int state){
      indicatorState=state;status.Text=label;
      // Do not leave an old "Connected / 100%" visible after service failure.
      if(state!=0 && signalTrayPopup!=null){
        signalTrayConnected=false;signalTrayLastPercent=null;
        signalTrayLastAdapter="";signalTrayLastStatus=label;
        RenderSignalTrayPopup();
      }''')

one('''    void ShowWindow(){Show();WindowState=FormWindowState.Normal;Activate();}''',
'''    // A small WinForms panel positioned by the clicked notification icon.
    // It displays the already-observed adapter and Wi-Fi signal values.
    void CreateSignalTrayPopup(){
      if(signalTrayPopup!=null && !signalTrayPopup.IsDisposed)return;
      signalTrayPopup=new Form{
        FormBorderStyle=FormBorderStyle.None,StartPosition=FormStartPosition.Manual,
        ShowInTaskbar=false,TopMost=true,Width=326,Height=226,
        BackColor=panel,ForeColor=ink,KeyPreview=true,
        Font=new Font("Segoe UI",10)
      };
      signalTrayPopup.Padding=new Padding(0);
      signalTrayPopup.Controls.Add(new Label{
        Text="T-Net",Location=new Point(18,12),Size=new Size(176,30),
        Font=new Font("Segoe UI",14,FontStyle.Bold),ForeColor=ink
      });
      signalTrayStatus=new Label{
        Text="Waiting for connection",Location=new Point(180,18),
        Size=new Size(128,23),TextAlign=ContentAlignment.MiddleRight,
        Font=new Font("Segoe UI",9),ForeColor=muted
      };
      signalTrayPopup.Controls.Add(signalTrayStatus);
      signalTrayPopup.Controls.Add(new Label{
        Text="Active adapter",Location=new Point(18,60),
        Size=new Size(280,19),ForeColor=muted,
        Font=new Font("Segoe UI",9)
      });
      signalTrayAdapter=new Label{
        Text="No active Wi-Fi",Location=new Point(18,80),
        Size=new Size(280,29),Font=new Font("Segoe UI",12,FontStyle.Bold),
        ForeColor=ink,AutoEllipsis=true
      };
      signalTrayPopup.Controls.Add(signalTrayAdapter);
      signalTrayPopup.Controls.Add(new Label{
        Text="Wi-Fi signal strength",Location=new Point(18,127),
        Size=new Size(215,22),ForeColor=ink,
        Font=new Font("Segoe UI",10)
      });
      signalTrayPercent=new Label{
        Text="—",Location=new Point(250,125),Size=new Size(58,26),
        TextAlign=ContentAlignment.MiddleRight,ForeColor=ink,
        Font=new Font("Segoe UI",12,FontStyle.Bold)
      };
      signalTrayPopup.Controls.Add(signalTrayPercent);
      signalTrayTrack=new Panel{
        Location=new Point(18,157),Size=new Size(290,9),
        BackColor=Color.FromArgb(49,65,86)
      };
      signalTrayFill=new Panel{
        Location=new Point(0,0),Size=new Size(0,9),
        BackColor=SignalBarColor(100)
      };
      signalTrayTrack.Controls.Add(signalTrayFill);
      signalTrayPopup.Controls.Add(signalTrayTrack);
      signalTrayPopup.Controls.Add(new Label{
        Text="Windows-reported Wi-Fi signal",Location=new Point(18,184),
        Size=new Size(288,24),ForeColor=muted,
        Font=new Font("Segoe UI",9)
      });
      // Behave like a Windows flyout: clicking away or pressing Esc closes it.
      signalTrayPopup.Deactivate+=(sender,e)=>{
        if(signalTrayPopup!=null && signalTrayPopup.Visible){
          signalTrayPopup.Hide();
          signalTrayLastAutoHideUtc=DateTime.UtcNow;
        }
      };
      signalTrayPopup.KeyDown+=(sender,e)=>{
        if(e.KeyCode==Keys.Escape){signalTrayPopup.Hide();e.Handled=true;}
      };
      RenderSignalTrayPopup();
    }
    void UpdateSignalTrayState(string statusCode,string adapterName,string signal){
      bool connected=statusCode=="tracking";
      signalTrayConnected=connected;
      signalTrayLastAdapter=connected?adapterName:"";
      signalTrayLastStatus=connected?"Connected":
        statusCode=="wrong-network"?"Disconnected":
        statusCode=="adapter-error"?"Adapter unavailable":
        statusCode=="not-configured"?"Not configured":"Waiting for connection";
      int value;
      signalTrayLastPercent=(connected &&
        Int32.TryParse(signal,NumberStyles.Integer,CultureInfo.InvariantCulture,out value) &&
        value>=0 && value<=100)?(int?)value:null;
      RenderSignalTrayPopup();
    }
    void RenderSignalTrayPopup(){
      if(signalTrayPopup==null || signalTrayPopup.IsDisposed)return;
      if(signalTrayStatus==null || signalTrayAdapter==null ||
         signalTrayPercent==null || signalTrayFill==null)return;
      signalTrayStatus.Text=signalTrayLastStatus;
      signalTrayStatus.ForeColor=signalTrayConnected?
        Color.FromArgb(79,212,161):muted;
      signalTrayAdapter.Text=signalTrayConnected &&
        !String.IsNullOrWhiteSpace(signalTrayLastAdapter)?
        signalTrayLastAdapter:"No active Wi-Fi";
      if(!signalTrayLastPercent.HasValue){
        signalTrayPercent.Text="—";
        signalTrayFill.Width=0;
      }else{
        int v=signalTrayLastPercent.Value;
        signalTrayPercent.Text=v.ToString(CultureInfo.InvariantCulture)+"%";
        signalTrayFill.BackColor=SignalBarColor(v);
        signalTrayFill.Width=(signalTrayTrack.ClientSize.Width*v+50)/100;
      }
    }
    void ToggleSignalTrayPopup(){
      if(closing)return;
      CreateSignalTrayPopup();
      if(signalTrayPopup.Visible){signalTrayPopup.Hide();return;}
      // When a tray click first deactivates the flyout, don't reopen it
      // from that same click's MouseClick event.
      if((DateTime.UtcNow-signalTrayLastAutoHideUtc).TotalMilliseconds<300)return;
      RenderSignalTrayPopup();
      Point click=System.Windows.Forms.Cursor.Position;
      Rectangle area=Screen.FromPoint(click).WorkingArea;
      int x=Math.Max(area.Left,Math.Min(area.Right-signalTrayPopup.Width,
                       click.X-signalTrayPopup.Width+42));
      int preferredY=click.Y-signalTrayPopup.Height-12;
      if(click.Y>=area.Bottom)preferredY=area.Bottom-signalTrayPopup.Height-10;
      int y=Math.Max(area.Top,Math.Min(area.Bottom-signalTrayPopup.Height,
                       preferredY));
      signalTrayPopup.Location=new Point(x,y);
      signalTrayPopup.Show();
      signalTrayPopup.Activate();
    }
    void ShowWindow(){
      if(signalTrayPopup!=null && !signalTrayPopup.IsDisposed)signalTrayPopup.Hide();
      Show();WindowState=FormWindowState.Normal;Activate();
    }''')

one('''    void Quit(){closing=true;refreshTimer.Stop();if(indicatorTimer!=null)indicatorTimer.Stop();''',
'''    void Quit(){closing=true;refreshTimer.Stop();if(indicatorTimer!=null)indicatorTimer.Stop();
      if(signalTrayPopup!=null && !signalTrayPopup.IsDisposed){
        signalTrayPopup.Close();signalTrayPopup.Dispose();signalTrayPopup=null;
      }''')

checks=[
  'tray.MouseClick+=(sender,e)=>',
  'tray.ContextMenuStrip=menu;',
  'tray.DoubleClick+=(s,e)=>ShowWindow();',
  'signalTrayPopup.Deactivate+=',
  'signalTrayPopup.KeyDown+=',
  'signalTrayFill.BackColor=SignalBarColor(v)',
  'signalTrayFill.Width=(signalTrayTrack.ClientSize.Width*v+50)/100;',
  'UpdateSignalTrayState(stat,Str(d,"adapterName"),Str(d,"wifiSignal"));',
  'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");',
  'downloadSpeed.Text=Rate(rateRx)',
  'uploadSpeed.Text=Rate(rateTx)',
  'TrackUsageCheckpoint(',
  'requestedCounterAdapter=stat=="tracking"',
  'new VScrollBar{',
  'hotspotHeader.Controls.Add(speedSourceLabel,0,2)',
  'const string AppVersion = "6.17.0";'
]
for q in checks:
    if q not in s:raise RuntimeError("Expected preserved/new source fragment missing: "+q)
p.write_text(s,encoding="utf-8")
print("T-Net v6.17 tray flyout: UI-only popup, native signal color, live existing API updates, right-click menu unchanged")
