from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8")

def exactly_one(old,new):
    global s
    count=s.count(old)
    if count!=1:raise RuntimeError("Expected one match (%d): %r"%(count,old[:110]))
    s=s.replace(old,new)

exactly_one('const string AppVersion = "6.5.0";','const string AppVersion = "6.6.0";')

start=s.index('    // Display ONLY. The raw SSID is left untouched')
end=s.index('    void ApplyUsage(Dictionary<string,object> d){',start)
assert s.count('wifi.Text=HotspotLabel(currentSsid);')==1
assert s.count('static string HotspotLabel(string raw)')==1
s=s[:start]+r'''    // DISPLAY ONLY: never modify currentSsid, targetSsid, matching, saved
    // settings, network adapter selection, sampling or user usage history.
    // The user's visible "GLOBALðŸ¤-" is a broken text-decoding suffix.
    // Show the known readable GLOBAL prefix if it is followed by a broken,
    // non-surrogate Unicode tail. Intact UTF-16 emoji remain visible.
    static string HotspotLabel(string raw){
      if(String.IsNullOrWhiteSpace(raw))return "Not connected";
      string name=raw.Trim();

      // Work around variations in Windows code-page decoding of the
      // connected Android hotspot. The plain GLOBAL Wi-Fi label is the
      // requested fallback; this only affects this displayed label.
      if(name.StartsWith("GLOBAL",StringComparison.OrdinalIgnoreCase) &&
         name.Length>6 && name[6]>127 && !Char.IsHighSurrogate(name[6])){
        return name.Substring(0,6);
      }

      // Generic mojibake detection for other SSIDs: when Windows has decoded
      // UTF-8 bytes as ANSI, preserve the readable prefix only.
      int damaged=-1;
      for(int i=0;i<name.Length;i++){
        char c=name[i];
        if(Char.IsHighSurrogate(c)){
          if(i+1<name.Length && Char.IsLowSurrogate(name[i+1])){i++;continue;}
          damaged=i;break;
        }
        if(c=='\uFFFD' || (c>='\u0080' && c<='\u009F')){
          damaged=i;break;
        }
        if((c=='\u00F0' || c=='\u00C3' || c=='\u00E2' || c=='\u00EF') &&
           i+1<name.Length &&
           (name[i+1]>127 || name[i+1]=='?')){
          damaged=i;break;
        }
      }
      if(damaged>0){
        string prefix=name.Substring(0,damaged).TrimEnd();
        if(prefix.Length>0)return prefix;
      }
      return name;
    }
'''+s[end:]

assert 'const string AppVersion = "6.6.0";' in s
assert 'downloadSpeed.Text=Rate(Num(d,"rateRxBps"));' in s
assert 'uploadSpeed.Text=Rate(Num(d,"rateTxBps"));' in s
assert 'wifi.Text=HotspotLabel(currentSsid);' in s
p.write_text(s,encoding="utf-8")
print("T-Net v6.6: stronger connected Wi-Fi name display fallback; no other source changed")
