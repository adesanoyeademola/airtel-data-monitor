from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8")

def one(old,new):
    global s
    n=s.count(old)
    if n!=1:
        raise RuntimeError("Expected exactly one match (%d): %r"%(n,old[:120]))
    s=s.replace(old,new)

one('const string AppVersion = "6.9.0";','const string AppVersion = "6.10.0";')

# No ambiguity between UTC, the Windows system timezone, and West Africa Time.
# DateTimeOffset's explicit offset is preserved in CSV. No raw usage is altered.
one('''    DateTime logWindowStart=DateTime.MinValue;''',
'''    static readonly TimeSpan UsageZoneOffset=TimeSpan.FromHours(1); // Nigeria WAT; no DST
    DateTime logLastMeasurementUtc=DateTime.MinValue;
    DateTime logWindowStart=DateTime.MinValue;''')

one('''      usageGrid.Columns.Add("recorded","Recorded at");''',
'''      usageGrid.Columns.Add("recorded","Interval end (WAT)");''')
one('''        end.LocalDateTime.ToString("yyyy-MM-dd HH:mm:ss",CultureInfo.InvariantCulture),''',
'''        FormatUsageTime(end),''')

one('''      usageGrid.Rows[index].Cells[0].ToolTipText=
        (baseline?"Starting checkpoint; no interval usage":
          "Measured interval: "+start.LocalDateTime.ToString("yyyy-MM-dd HH:mm:ss")+
          " to "+end.LocalDateTime.ToString("yyyy-MM-dd HH:mm:ss"))+
        " (PC local time)";''',
'''      usageGrid.Rows[index].Cells[0].ToolTipText=
        baseline?"Starting baseline at "+FormatUsageTime(end)+
          "; no interval usage attributed":
          "Usage measured from "+FormatUsageTime(start)+" to "+
          FormatUsageTime(end)+" (West Africa Time, UTC+01:00)";''')

one('''      string entry=String.Join(",",new []{
        start.ToString("yyyy-MM-ddTHH:mm:sszzz",CultureInfo.InvariantCulture),
        end.ToString("yyyy-MM-ddTHH:mm:sszzz",CultureInfo.InvariantCulture),''',
'''      string entry=String.Join(",",new []{
        new DateTimeOffset(DateTime.SpecifyKind(start,DateTimeKind.Unspecified),
          UsageZoneOffset).ToString("yyyy-MM-ddTHH:mm:sszzz",CultureInfo.InvariantCulture),
        new DateTimeOffset(DateTime.SpecifyKind(end,DateTimeKind.Unspecified),
          UsageZoneOffset).ToString("yyyy-MM-ddTHH:mm:sszzz",CultureInfo.InvariantCulture),''')

one('''        if(showUsageLog)
          chartCaption.Text="Saved "+end.ToString("HH:mm:ss")+
            "  •  checkpoints about every minute  •  click to open CSV";''',
'''        if(showUsageLog)
          chartCaption.Text="Last interval ended "+end.ToString("hh:mm:ss tt",CultureInfo.InvariantCulture)+
            " WAT  •  about 1 minute per row  •  click to open CSV";''')

one('''          "Timestamped checkpoints (about 1 min)  •  click to open CSV";''',
'''          "Interval end shown in WAT (UTC+01:00)  •  hover time for range  •  click to open CSV";''')

one('''      DateTime observed=sampleUtc.ToLocalTime();
      if(logLastObserved!=DateTime.MinValue && observed<=logLastObserved)return;''',
'''      // Deduplicate by the engine's actual sample timestamp, while labeling
      // a checkpoint using the same sample instant in WAT (not repeatedly
      // converting the service timestamp between different timezone kinds).
      DateTime measurementUtc=sampleUtc.ToUniversalTime();
      if(logLastMeasurementUtc!=DateTime.MinValue &&
         measurementUtc<=logLastMeasurementUtc)return;
      logLastMeasurementUtc=measurementUtc;
      DateTime observed=new DateTimeOffset(measurementUtc).ToOffset(UsageZoneOffset).DateTime;
      if(logLastObserved!=DateTime.MinValue && observed<=logLastObserved)return;''')

# The UI formatter must NOT depend on the system's timezone. CSV records from
# v6.9 are retained and parsed from their original offset without rewriting.
anchor='    void ShowUsageLogRow(string row){'
formatter='''    static string FormatUsageTime(DateTimeOffset time){
      // Always present the same WAT clock that the user uses in Nigeria.
      return time.ToOffset(UsageZoneOffset).ToString(
        "yyyy-MM-dd hh:mm:ss tt",CultureInfo.InvariantCulture)+" WAT";
    }
'''
one(anchor,formatter+anchor)

assert 'const string AppVersion = "6.10.0";' in s
assert 'downloadSpeed.Text=Rate(rateRx);' in s
assert 'uploadSpeed.Text=Rate(rateTx);' in s
assert 'CaptureLiveSpeedSample(stat,liveSampleId' in s
assert 'wifi.Text=HotspotLabel(currentSsid);' in s
assert 'GetDataFast()' in s
assert 'usage-timeline.csv' in s
p.write_text(s,encoding="utf-8")
print("T-Net 6.10: WAT timestamp clarity; same usage engine, speed calculations and existing CSV retained.")
