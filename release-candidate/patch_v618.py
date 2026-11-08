from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")

def one(old,new):
    global s
    n=s.count(old)
    if n!=1: raise RuntimeError("Expected exactly one patch anchor, found %d: %r"%(n,old[:110]))
    s=s.replace(old,new)

one('const string AppVersion = "6.17.0";','const string AppVersion = "6.18.0";')
one('using System.Windows.Forms;','using System.Windows.Forms;\nusing Microsoft.Win32;')
one('    public MainForm(bool shareMode) {', '''    string appearanceMode="dark";
    bool appearanceIsLight=false;
    Button appearanceButton;
    ContextMenuStrip appearanceMenu;
    DateTime nextSystemThemeCheck=DateTime.MinValue;
    readonly string appearanceFile=Path.Combine(
      Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
      "AirtelDataMonitor","appearance.txt");
    static readonly Color darkBg=Color.FromArgb(13,19,30);
    static readonly Color darkPanel=Color.FromArgb(25,35,53);
    static readonly Color darkInk=Color.FromArgb(239,245,252);
    static readonly Color darkMuted=Color.FromArgb(171,187,207);
    static readonly Color lightBg=Color.FromArgb(244,247,251);
    static readonly Color lightPanel=Color.White;
    static readonly Color lightInk=Color.FromArgb(28,40,56);
    static readonly Color lightMuted=Color.FromArgb(91,107,128);
    public MainForm(bool shareMode) {''')
one('      BuildUi();\n      LoadUsageLog();','''      LoadAppearanceChoice();
      BuildUi();
      ApplyAppearance(true);
      LoadUsageLog();''')
one('tray.ContextMenuStrip=menu;','''var appearanceItem=new ToolStripMenuItem("Appearance");
      appearanceItem.DropDownItems.Add("Light",null,(sender,e)=>SelectAppearance("light"));
      appearanceItem.DropDownItems.Add("Dark",null,(sender,e)=>SelectAppearance("dark"));
      appearanceItem.DropDownItems.Add("Follow Windows",null,(sender,e)=>SelectAppearance("system"));
      menu.Items.Insert(2,appearanceItem);
      tray.ContextMenuStrip=menu;''')
one('headerActions.Controls.Add(updateButton);','''headerActions.Controls.Add(updateButton);
      appearanceButton=new Button{
        Text="◐",Width=32,Height=29,
        BackColor=Color.FromArgb(32,46,68),ForeColor=ink,
        FlatStyle=FlatStyle.Flat,Margin=new Padding(3,0,3,0)
      };
      appearanceButton.FlatAppearance.BorderColor=Color.FromArgb(49,65,86);
      var appearanceTip=new ToolTip();
      appearanceTip.SetToolTip(appearanceButton,"Appearance: Light, Dark or System");
      appearanceButton.Click+=(sender,e)=>ShowAppearanceMenu();
      headerActions.Controls.Add(appearanceButton);''')
one('    void ShowWindow(){','''    void LoadAppearanceChoice(){
      try{
        if(File.Exists(appearanceFile)){
          string choice=File.ReadAllText(appearanceFile).Trim().ToLowerInvariant();
          if(choice=="light"||choice=="dark"||choice=="system")
            appearanceMode=choice;
        }
      }catch{/* Appearance is optional; monitoring must still start. */}
    }
    bool WindowsPrefersLight(){
      try{
        using(var key=Registry.CurrentUser.OpenSubKey(
          @"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")){
          object value=key==null?null:key.GetValue("AppsUseLightTheme");
          return value!=null && Convert.ToInt32(value,CultureInfo.InvariantCulture)!=0;
        }
      }catch{return false;}
    }
    void SelectAppearance(string choice){
      if(choice!="light"&&choice!="dark"&&choice!="system")return;
      appearanceMode=choice;
      try{
        Directory.CreateDirectory(Path.GetDirectoryName(appearanceFile));
        File.WriteAllText(appearanceFile,choice,Encoding.UTF8);
      }catch{/* Failure to save preference cannot interrupt monitoring. */}
      ApplyAppearance(true);
    }
    void CheckSystemAppearance(){
      if(appearanceMode!="system" || DateTime.UtcNow<nextSystemThemeCheck)return;
      nextSystemThemeCheck=DateTime.UtcNow.AddSeconds(2);
      if(appearanceIsLight!=WindowsPrefersLight())ApplyAppearance(true);
    }
    Color AppearanceColor(Color color,bool light){
      if(color==Color.Empty||color==Color.Transparent||color.A==0)return color;
      Color[] darkColors={
        darkBg,darkPanel,darkInk,darkMuted,
        Color.FromArgb(32,46,68),Color.FromArgb(49,65,86),
        Color.FromArgb(42,54,71),Color.FromArgb(48,60,76),
        Color.FromArgb(38,62,86),Color.FromArgb(34,47,66)
      };
      Color[] lightColors={
        lightBg,lightPanel,lightInk,lightMuted,
        Color.FromArgb(228,234,243),Color.FromArgb(190,202,218),
        Color.FromArgb(215,223,233),Color.FromArgb(224,230,239),
        Color.FromArgb(207,226,244),Color.FromArgb(230,236,245)
      };
      for(int i=0;i<darkColors.Length;i++)
        if(color.ToArgb()==darkColors[i].ToArgb()||
           color.ToArgb()==lightColors[i].ToArgb())
          return light?lightColors[i]:darkColors[i];
      return color; // Preserve signal status, coloured bars and chart series.
    }
    void AppearanceControl(Control control,bool light){
      control.BackColor=AppearanceColor(control.BackColor,light);
      control.ForeColor=AppearanceColor(control.ForeColor,light);
      // Keep neutral header buttons readable on light surfaces; retain
      // white text on the coloured Save hotspot button.
      if(control is Button && control.BackColor!=accent &&
         (control.ForeColor==Color.White || control.ForeColor==lightInk))
        control.ForeColor=light?lightInk:Color.White;
      if(control is Label && control.Text=="T-Net")
        control.ForeColor=light?lightInk:Color.White;
      var grid=control as DataGridView;
      if(grid!=null){
        grid.BackgroundColor=AppearanceColor(grid.BackgroundColor,light);
        grid.GridColor=AppearanceColor(grid.GridColor,light);
        foreach(DataGridViewCellStyle st in new[]{
          grid.DefaultCellStyle,grid.ColumnHeadersDefaultCellStyle,
          grid.RowHeadersDefaultCellStyle,grid.AlternatingRowsDefaultCellStyle}){
          st.BackColor=AppearanceColor(st.BackColor,light);
          st.ForeColor=AppearanceColor(st.ForeColor,light);
          st.SelectionBackColor=AppearanceColor(st.SelectionBackColor,light);
          st.SelectionForeColor=AppearanceColor(st.SelectionForeColor,light);
        }
      }
      var graph=control as Chart;
      if(graph!=null){
        foreach(ChartArea a in graph.ChartAreas){
          a.BackColor=AppearanceColor(a.BackColor,light);
          a.AxisX.LineColor=AppearanceColor(a.AxisX.LineColor,light);
          a.AxisY.LineColor=AppearanceColor(a.AxisY.LineColor,light);
          a.AxisX.LabelStyle.ForeColor=AppearanceColor(a.AxisX.LabelStyle.ForeColor,light);
          a.AxisY.LabelStyle.ForeColor=AppearanceColor(a.AxisY.LabelStyle.ForeColor,light);
          a.AxisY.TitleForeColor=AppearanceColor(a.AxisY.TitleForeColor,light);
          a.AxisX.MajorGrid.LineColor=AppearanceColor(a.AxisX.MajorGrid.LineColor,light);
          a.AxisY.MajorGrid.LineColor=AppearanceColor(a.AxisY.MajorGrid.LineColor,light);
        }
        foreach(Legend legend in graph.Legends){
          legend.BackColor=AppearanceColor(legend.BackColor,light);
          legend.ForeColor=AppearanceColor(legend.ForeColor,light);
        }
      }
      foreach(Control child in control.Controls)AppearanceControl(child,light);
    }
    void ApplyAppearance(bool force){
      bool useLight=appearanceMode=="light" ||
        (appearanceMode=="system"&&WindowsPrefersLight());
      if(!force&&appearanceIsLight==useLight)return;
      appearanceIsLight=useLight;
      AppearanceControl(this,useLight);
      bg=useLight?lightBg:darkBg;
      panel=useLight?lightPanel:darkPanel;
      ink=useLight?lightInk:darkInk;
      muted=useLight?lightMuted:darkMuted;
      BackColor=bg;ForeColor=ink;
      if(signalTrayPopup!=null&&!signalTrayPopup.IsDisposed){
        AppearanceControl(signalTrayPopup,useLight);
        signalTrayPopup.BackColor=panel;
        RenderSignalTrayPopup();
      }
      Invalidate(true);
    }
    void ShowAppearanceMenu(){
      if(appearanceMenu!=null){appearanceMenu.Dispose();appearanceMenu=null;}
      appearanceMenu=new ContextMenuStrip();
      foreach(string item in new[]{"Light","Dark","System"}){
        string value=item.ToLowerInvariant();
        appearanceMenu.Items.Add(new ToolStripMenuItem(
          item=="System"?"Follow Windows":item,null,
          (sender,e)=>SelectAppearance(value)){
            Checked=appearanceMode==value
          });
      }
      appearanceMenu.Show(appearanceButton,new Point(0,appearanceButton.Height));
    }
    void ShowWindow(){''')
one('refreshTimer.Tick+=(s,e)=>RefreshUsageAsync();','refreshTimer.Tick+=(s,e)=>{RefreshUsageAsync();CheckSystemAppearance();};')
one('      CreateSignalTrayPopup();\n      if(signalTrayPopup.Visible)', '''      CreateSignalTrayPopup();
      AppearanceControl(signalTrayPopup,appearanceIsLight);
      if(signalTrayPopup.Visible)''')
for key in ['ToggleSignalTrayPopup','TrackUsageCheckpoint(','downloadSpeed.Text=Rate(rateRx)',
            'uploadSpeed.Text=Rate(rateTx)','new VScrollBar{',
            'signalTrayLastAutoHideUtc','const string AppVersion = "6.18.0";']:
    if key not in s:raise RuntimeError("Feature missing after patch: "+key)
p.write_text(s,encoding="utf-8")
print("Patched T-Net 6.18 appearance mode selectors; monitoring engine untouched")
