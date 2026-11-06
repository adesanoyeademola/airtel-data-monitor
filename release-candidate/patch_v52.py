from pathlib import Path
p=Path('work')
c=p/'AirtelMonitorNative.cs'
m=p/'monitor.ps1'
s=c.read_text(encoding='utf-8')
def replace(a,b):
 global s
 if s.count(a)!=1: raise ValueError('Missing or duplicate: '+a[:60])
 s=s.replace(a,b)
replace('const string AppVersion = "5.1.0";','const string AppVersion = "5.2.0";')
replace('new Font("Segoe UI Semibold",23,FontStyle.Bold)','new Font("Segoe UI",24,FontStyle.Bold)')
replace('chPanel.Controls.Add(LabelText("Daily usage",15,true));chart=new Chart','chart=new Chart')
replace('chPanel.Controls.Add(chart);var title=LabelText("Daily usage (MB)",15,true);title.Dock=DockStyle.Top;chPanel.Controls.Add(title);title.BringToFront();','var title=LabelText("Daily usage",15,true);var layout=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=2,ColumnCount=1};layout.RowStyles.Add(new RowStyle(SizeType.Absolute,38));layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.Controls.Add(title,0,0);layout.Controls.Add(chart,0,1);chPanel.Controls.Add(layout);')
replace('currentSsid=Str(d,"currentSsid");wifi.Text=(currentSsid.Length>0?currentSsid:"Not connected")+"  ·  "+(Str(d,"targetSsid").Length>0?"Tracked: "+Str(d,"targetSsid"):"Not configured");','currentSsid=Str(d,"currentSsid");wifi.Text=(currentSsid.Length>0?currentSsid:"Not connected");')
replace('outer.RowStyles.Add(new RowStyle(SizeType.Absolute,155));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,28));','outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,28));')
replace('settings.Controls.Add(section);outer.Controls.Add(settings,0,4);','settings.Controls.Add(section);')
c.write_text(s,encoding='utf-8')
s=m.read_text(encoding='utf-8')
start=s.index('    if ([string]::IsNullOrWhiteSpace($script:State.targetSsid)) {')
end=s.index('    try {',start)
replacement="""    if ([string]::IsNullOrWhiteSpace($ssid)) {
        $script:Status = 'wrong-network'
        $script:SampleTime = [datetime]::MinValue
        $script:Sample.valid = $false
        $script:Sample.ssid = ''
        return
    }
"""
s=s[:start]+replacement+s[end:]
m.write_text(s,encoding='utf-8')
print('Prepared v5.2 patch')
