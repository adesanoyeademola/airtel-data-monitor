from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8")

def replace_one(old,new):
    global s
    n=s.count(old)
    if n!=1:
        raise RuntimeError("Expected one match (%d) for: %r" % (n, old[:140]))
    s=s.replace(old,new)

replace_one('const string AppVersion = "6.3.0";','const string AppVersion = "6.4.0";')

# Record the engine's actual sample timestamp rather than the UI poll time.
replace_one('''    Label status, statusDot, wifi, adapter, last, today, down, up, week, downloadSpeed, uploadSpeed;''',
'''    Label status, statusDot, sampleAgeLabel, wifi, adapter, last, today, down, up, week, downloadSpeed, uploadSpeed;
    DateTime mostRecentAdapterSampleUtc=DateTime.MinValue;''')

# The network panel already has a title row. Fit the indicator beside it,
# rather than crowding the monitoring status or shrinking the speed cards.
replace_one('''      layoutNetwork.Controls.Add(networkTitle,0,0);''',
'''      var networkHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,Margin=new Padding(0)};
      networkHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,42));
      networkHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,58));
      sampleAgeLabel=new Label{
        Text="Last sample: waiting",Dock=DockStyle.Fill,
        TextAlign=ContentAlignment.MiddleRight,ForeColor=muted,
        Font=new Font("Segoe UI",9),AutoEllipsis=true
      };
      networkHeader.Controls.Add(networkTitle,0,0);
      networkHeader.Controls.Add(sampleAgeLabel,1,0);
      layoutNetwork.Controls.Add(networkHeader,0,0);''')

# Latency only reflects the age of the timestamp delivered by the engine.
# Update locally even between the 500ms HTTP polls. No fake points or traffic.
replace_one('''    void PulseIndicator(){
      if(statusDot==null||statusDot.IsDisposed)return;''',
'''    void RefreshSampleAgeIndicator(){
      if(sampleAgeLabel==null || sampleAgeLabel.IsDisposed)return;
      if(mostRecentAdapterSampleUtc==DateTime.MinValue){
        sampleAgeLabel.Text="Last sample: waiting";
        sampleAgeLabel.ForeColor=muted;
        return;
      }
      double age=(DateTime.UtcNow-mostRecentAdapterSampleUtc).TotalSeconds;
      if(Double.IsNaN(age) || age < -2.0){
        sampleAgeLabel.Text="Sample clock mismatch";
        sampleAgeLabel.ForeColor=Color.FromArgb(236,185,65);
        return;
      }
      age=Math.Max(0.0,age);
      if(age>3.0 && indicatorState==0){
        SetIndicator("Monitoring paused",1);
      }
      if(age>3.0){
        sampleAgeLabel.Text="Stale sample: "+age.ToString("0.0",CultureInfo.InvariantCulture)+"s ago";
        sampleAgeLabel.ForeColor=indicatorState==2?
          Color.FromArgb(240,105,105):Color.FromArgb(236,185,65);
      }else{
        sampleAgeLabel.Text="Last sample: "+age.ToString("0.0",CultureInfo.InvariantCulture)+"s ago";
        sampleAgeLabel.ForeColor=Color.FromArgb(162,191,216);
      }
    }
    void PulseIndicator(){
      RefreshSampleAgeIndicator();
      if(statusDot==null||statusDot.IsDisposed)return;''')

replace_one('''        bool timestampValid = DateTime.TryParse(Str(d,"rateSampleTime"), CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out sampleUtc);
        bool fresh = timestampValid''',
'''        bool timestampValid = DateTime.TryParse(Str(d,"rateSampleTime"), CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out sampleUtc);
        if(timestampValid){
          mostRecentAdapterSampleUtc=sampleUtc.ToUniversalTime();
        }
        RefreshSampleAgeIndicator();
        bool fresh = timestampValid''')

assert 'GetDataFast()' in s and 'RefreshUsageAsync()' in s
assert 'CaptureLiveSpeedSample(' in s and 'AutoRecoverEngine()' in s
assert 'Get-NetAdapterStatistics' not in s # engine unchanged
assert 'Last sample:' in s and 'Stale sample:' in s
p.write_text(s,encoding="utf-8")
print("T-Net v6.4: real age of latest adapter sample, stale warning; meter unchanged.")
