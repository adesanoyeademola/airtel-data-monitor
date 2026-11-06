from pathlib import Path

f=Path("work/AirtelMonitorNative.cs")
s=f.read_text(encoding="utf-8")

def exactly_one(old,new):
    global s
    count=s.count(old)
    if count!=1:
        raise RuntimeError(f"Expected exactly one source match ({count}): {old[:130]!r}")
    s=s.replace(old,new)

exactly_one('const string AppVersion = "6.4.0";','const string AppVersion = "6.5.0";')

# UI-only: do not alter currentSsid, targetSsid, network detection, traffic
# rates, background service, settings or stored measurements.
exactly_one('wifi.Text=(currentSsid.Length>0?currentSsid:"Not connected");',
            'wifi.Text=HotspotLabel(currentSsid);')

anchor='    void ApplyUsage(Dictionary<string,object> d){'
method=r'''    // Display ONLY. The raw SSID is left untouched for adapter matching,
    // settings, persistence, hotspot auto-detection and network monitoring.
    // When Windows netsh has already garbled an emoji into mojibake, show
    // the readable SSID prefix rather than an unreadable trailing sequence.
    static string HotspotLabel(string raw){
      if(String.IsNullOrWhiteSpace(raw))return "Not connected";
      string name=raw.Trim();
      string[] corruptSequences={
        "\u00F0\u0178", // ðŸ : common UTF-8 emoji bytes decoded as Windows-1252
        "\u00F0\u009F", // ð + control code : another mis-decoding variant
        "\u00E2\u20AC", // â€ : corrupted typographic/emoji sequence
        "\u00EF\u00BF\u00BD", // ï¿½ : replacement-character mojibake
        "\uFFFD"       // Unicode replacement character
      };
      int firstBad=-1;
      foreach(string sequence in corruptSequences){
        int at=name.IndexOf(sequence,StringComparison.Ordinal);
        if(at>=0 && (firstBad<0 || at<firstBad))firstBad=at;
      }
      if(firstBad>0){
        string readable=name.Substring(0,firstBad).TrimEnd();
        if(readable.Length>0)return readable;
      }
      return name;
    }
'''
exactly_one(anchor,method+anchor)

assert s.count('HotspotLabel(currentSsid)')==1
assert 'currentSsid=Str(d,"currentSsid")' in s
assert 'hotspot.Text=Str(d,"targetSsid")' in s
assert 'downloadSpeed.Text=Rate(Num(d,"rateRxBps"));' in s
assert 'uploadSpeed.Text=Rate(Num(d,"rateTxBps"));' in s
assert 'const string AppVersion = "6.5.0";' in s
f.write_text(s,encoding="utf-8")
print("T-Net 6.5: ONLY Wi-Fi SSID display sanitizer added; no monitoring/settings changes")
