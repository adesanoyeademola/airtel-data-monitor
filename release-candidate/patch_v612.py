from pathlib import Path

p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")

def exactly_one(old,new):
    global s
    n=s.count(old)
    if n!=1:
        raise RuntimeError("Expected exactly one match (%s): %r"%(n,old[:180]))
    s=s.replace(old,new)

exactly_one('const string AppVersion = "6.11.0";','const string AppVersion = "6.12.0";')

exactly_one(
  '    Label status, statusDot, sampleAgeLabel, speedSourceLabel, wifi, adapter, signalStrength, last, today, down, up, week, downloadSpeed, uploadSpeed;',
  '    Label status, statusDot, sampleAgeLabel, speedSourceLabel, wifi, adapter, signalStrength, last, today, down, up, week, downloadSpeed, uploadSpeed;\n    Panel signalStrengthTrack, signalStrengthFill;'
)

exactly_one(
 '      detailScroll.Controls.Add(LabelText("Wi-Fi signal strength"));signalStrength=LabelText("—",12,true);detailScroll.Controls.Add(signalStrength);',
 '''      detailScroll.Controls.Add(LabelText("Wi-Fi signal strength"));
      // A thin, color-coded Wi-Fi quality line. The percentage still comes
      // exclusively from Windows via the existing monitor.ps1 API.
      var signalRow=new FlowLayoutPanel{
        Width=306,Height=25,AutoSize=false,WrapContents=false,
        FlowDirection=FlowDirection.LeftToRight,
        Margin=new Padding(0,1,0,1),Padding=new Padding(0)
      };
      signalStrengthTrack=new Panel{
        Width=210,Height=9,BackColor=Color.FromArgb(49,65,86),
        Margin=new Padding(0,8,12,0)
      };
      signalStrengthFill=new Panel{
        Width=0,Height=9,BackColor=Color.FromArgb(79,212,161),
        Location=new Point(0,0),Margin=new Padding(0)
      };
      signalStrengthTrack.Controls.Add(signalStrengthFill);
      signalStrength=LabelText("—",11,true);
      signalStrength.AutoSize=false;
      signalStrength.Width=68;
      signalStrength.Height=25;
      signalStrength.TextAlign=ContentAlignment.MiddleLeft;
      signalStrength.Margin=new Padding(0);
      signalRow.Controls.Add(signalStrengthTrack);
      signalRow.Controls.Add(signalStrength);
      detailScroll.Controls.Add(signalRow);'''
)

exactly_one(
 '''        if(signalStrength!=null){
          string strength=Str(d,"wifiSignal");
          signalStrength.Text=stat=="tracking" && !String.IsNullOrWhiteSpace(strength)?strength+"%":"—";
        }''',
 '''        UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");'''
)

anchor='    void ApplyUsage(Dictionary<string,object> d){'
helper='''    // The exact reported 0-100% WLAN signal quality is displayed directly.
    // No internet speed estimates, interpolation, or inferred readings.
    static Color SignalBarColor(int percentage){
      if(percentage>=80)return Color.FromArgb(79,212,161);    // green 80-100
      if(percentage>=50)return Color.FromArgb(236,185,65);    // yellow 50-79
      return Color.FromArgb(240,105,105);                    // red 0-49
    }
    void UpdateSignalDisplay(string reportedSignal,bool connected){
      if(signalStrength==null || signalStrengthTrack==null || signalStrengthFill==null)return;
      int value=0;
      bool valid=connected &&
        Int32.TryParse(reportedSignal,NumberStyles.Integer,CultureInfo.InvariantCulture,out value) &&
        value>=0 && value<=100;
      if(!valid){
        signalStrength.Text="—";
        signalStrengthFill.Width=0;
        signalStrengthTrack.AccessibleDescription="Wi-Fi signal unavailable";
        return;
      }
      // Reuse the same exact percentage shown in text. No made-up value.
      signalStrength.Text=value.ToString(CultureInfo.InvariantCulture)+"%";
      signalStrengthFill.BackColor=SignalBarColor(value);
      signalStrengthFill.Width=(signalStrengthTrack.ClientSize.Width*value+50)/100;
      signalStrengthTrack.AccessibleDescription="Wi-Fi signal strength "+signalStrength.Text;
    }
'''
exactly_one(anchor,helper+anchor)

assert s.count('UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking")')==1
assert s.count('SignalBarColor(int percentage)')==1
assert 'wifi.Text=HotspotLabel(currentSsid)' in s
assert 'downloadSpeed.Text=Rate(rateRx)' in s
assert 'uploadSpeed.Text=Rate(rateTx)' in s
assert 'TrackUsageCheckpoint(' in s
assert 'requestedCounterAdapter=stat=="tracking"' in s
assert 'const string AppVersion = "6.12.0";' in s
p.write_text(s,encoding="utf-8")
print("T-Net v6.12: ONLY signal bar UI and displayed signal % thresholds changed")
