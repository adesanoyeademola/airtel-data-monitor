from pathlib import Path
p=Path('work')
ui=p/'AirtelMonitorNative.cs'
engine=p/'monitor.ps1'
s=ui.read_text(encoding='utf-8')
e=engine.read_text(encoding='utf-8')
def change(src,old,new):
    n=src.count(old)
    if n!=1: raise RuntimeError(f'Expected one match for {old!r}, found {n}')
    return src.replace(old,new)
s=change(s,'const string AppVersion = "5.3.0";','const string AppVersion = "5.4.0";')
s=change(s,'refreshTimer.Interval = 3000;','refreshTimer.Interval = 1000;')
# Explicitly mark a sample older than 3 seconds as unavailable.
s=change(s,'Math.Abs((DateTime.UtcNow - sampleUtc.ToUniversalTime()).TotalSeconds) <= 14','Math.Abs((DateTime.UtcNow - sampleUtc.ToUniversalTime()).TotalSeconds) <= 3')
s=change(s,'''          if(valid && fresh){
            downloadSpeed.Text=Rate(Num(d,"rateRxBps"));
            uploadSpeed.Text=Rate(Num(d,"rateTxBps"));
            previousRateSampleId=sampleId;previousRateReceivedUtc=nowUtc;
          } else if(fallbackValid){
            downloadSpeed.Text=Rate(fallbackRx);
            uploadSpeed.Text=Rate(fallbackTx);
          } else {
            downloadSpeed.Text="Measuring...";uploadSpeed.Text="Measuring...";
          }''','''          if(valid && fresh){
            // Direct rates and daily totals originate from the same adapter samples.
            // The more recent of two valid measured deltas avoids displaying stale zero
            // when a fresh daily-usage increment arrived between UI refreshes.
            double directRx=Num(d,"rateRxBps"),directTx=Num(d,"rateTxBps");
            downloadSpeed.Text=Rate(fallbackValid && fallbackRx>0 && directRx==0?fallbackRx:directRx);
            uploadSpeed.Text=Rate(fallbackValid && fallbackTx>0 && directTx==0?fallbackTx:directTx);
            previousRateSampleId=sampleId;previousRateReceivedUtc=nowUtc;
          } else if(fallbackValid){
            downloadSpeed.Text=Rate(fallbackRx);
            uploadSpeed.Text=Rate(fallbackTx);
          } else {
            downloadSpeed.Text="Measuring...";uploadSpeed.Text="Measuring...";
          }''')
# Add actual sample timestamp and current state in the network information for debugging.
s=change(s,'last.Text=Str(d,"lastUpdated").Length>0?Str(d,"lastUpdated"):"No activity";','last.Text=Str(d,"rateSampleTime").Length>0?Str(d,"rateSampleTime"):"No sample yet";')
e=change(e,'$nextPoll = (Get-Date).AddSeconds(5)','$nextPoll = (Get-Date).AddSeconds(1)')
# After longer sampling gaps, display unmeasured rather than incorrectly adding
# a large transfer to the current second.
e=change(e,'$elapsed -le 15','$elapsed -le 5')
# Remove the "always zero at top of Take-Sample" issue during polling? Keep reset
# because it correctly marks intervals without valid speed samples.
ui.write_text(s,encoding='utf-8')
engine.write_text(e,encoding='utf-8')
assert 'refreshTimer.Interval = 1000' in s
assert 'AddSeconds(1)' in e
print('v5.4 source patched')
