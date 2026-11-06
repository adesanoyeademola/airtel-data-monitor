from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8")
def one(old,new):
    global s
    n=s.count(old)
    if n!=1: raise RuntimeError(f"Expected one match, got {n}: {old[:120]!r}")
    s=s.replace(old,new)

one('const string AppVersion = "6.0.0";','const string AppVersion = "6.1.0";')

# Remove the daily-usage difference fallback, which can display earlier
# traffic after the direct adapter-rate sample has dropped to zero.
start=s.index('        // Use native byte-counter rates first')
end=s.index('        if(stat!="tracking"){',start)
assert 'fallbackValid' in s[start:end]
s=s[:start]+'''        // Speeds originate only from the engine's latest adapter-counter
        // sampling interval, never from delayed daily-usage totals.
        DateTime nowUtc=DateTime.UtcNow;
'''+s[end:]

start=s.index('          } else if(valid && fresh){')
end=s.index('          previousUsageRx=rx;',start)
part=s[start:end]
assert 'fallbackValid' in part and 'directRx' in part
s=s[:start]+'''          } else if(valid && fresh){
            // Fresh interval: a measured zero is a real zero.
            downloadSpeed.Text=Rate(Num(d,"rateRxBps"));
            uploadSpeed.Text=Rate(Num(d,"rateTxBps"));
            previousRateSampleId=sampleId;
            previousRateReceivedUtc=nowUtc;
          } else {
            downloadSpeed.Text="Measuring...";
            uploadSpeed.Text="Measuring...";
          }
'''+s[end:]

# Keep the existing 1-second monitoring engine, status dots, usage history,
# startup recovery, update system and chart unchanged.
assert 'refreshTimer.Interval = 1000' in s
assert 'fallbackValid' not in s
assert 'fallbackRx' not in s
assert 'const string AppVersion = "6.1.0";' in s
p.write_text(s,encoding="utf-8")
print("T-Net 6.1 direct interval rates only; cumulative history unchanged")
