from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(a,b):
    global s
    n=s.count(a)
    if n!=1:raise RuntimeError("Expected one baseline source anchor, got %d: %r"%(n,a[:130]))
    s=s.replace(a,b)
one("public class MainForm : Form {","public partial class MainForm : Form {")
one('''      LoadUsageLog();
      // The explicit "Restart service" warning is also an action users can click.''',
'''      LoadUsageLog();
      // Exact approved UI in an embedded browser; native UI stays as fallback.
      StartApprovedWebView();
      // The explicit "Restart service" warning is also an action users can click.''')
one('''          lastDailyChartRenderUtc=DateTime.UtcNow;
        }
      }catch {''',
'''          lastDailyChartRenderUtc=DateTime.UtcNow;
        }
        // Display only: copy preexisting Windows values to the approved UI.
        PushApprovedTelemetry(d);
      }catch {''')
one('''      ApplyAppearance(true);
    }
    void CheckSystemAppearance(){''',
'''      ApplyAppearance(true);
      PostApprovedTheme();
    }
    void CheckSystemAppearance(){''')
if "const string AppVersion = \"6.31.0\";" not in s:raise RuntimeError("Version mismatch")
# Important: None of these edits alter calculations, network APIs, data
# persistence, adapter matching, history, battery, or the existing updater.
p.write_text(s,encoding="utf-8")
print("PASS WebView2 bridge insertion; monitoring calculations untouched")
