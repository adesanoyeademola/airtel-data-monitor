from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(a,b):
    global s
    n=s.count(a)
    if n!=1:raise RuntimeError("Expected one v6.26 anchor, found %d: %r"%(n,a[:150]))
    s=s.replace(a,b)

one('const string AppVersion = "6.26.0";','const string AppVersion = "6.27.0";')
# New installs use Nordic Light while saved preferences are respected.
one('''    string appearanceMode="dark";''','''    string appearanceMode="light";''')


# Nordic Canvas keeps light / dark / Windows-auto functionality but uses
# the segmented sun, moon, and Auto selector chosen in Application Desk.
one('''    int? dashboardSignalPercent=null;''',
'''    int? dashboardSignalPercent=null;
    Label nordicSignalMetric;
    Panel nordicSidebar,nordicNetworkPanel;
    FlowLayoutPanel nordicAppearanceStrip;
    Button nordicLightButton,nordicDarkButton,nordicAutoButton;
    Button nordicSelectedNav;
    readonly List<Button> nordicNavButtons=new List<Button>();''')

one('''    static readonly Color lightBg=Color.FromArgb(239,244,249);''',
    '''    static readonly Color lightBg=Color.FromArgb(242,246,252);''')
one('''    static readonly Color lightMuted=Color.FromArgb(79,100,124);''',
    '''    static readonly Color lightMuted=Color.FromArgb(94,110,133);''')
one('''        Color.FromArgb(228,234,243),Color.FromArgb(190,202,218),
        Color.FromArgb(215,223,233),Color.FromArgb(224,230,239),
        Color.FromArgb(207,226,244),Color.FromArgb(230,236,245)''',
'''        Color.FromArgb(236,243,253),Color.FromArgb(197,214,234),
        Color.FromArgb(229,238,249),Color.FromArgb(227,237,249),
        Color.FromArgb(214,233,254),Color.FromArgb(236,243,252)''')

# Replace dark-only dashboard composition with the Nordic app shell.
one('''      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,86));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,138));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));outer.RowStyles.Add(new RowStyle(SizeType.Percent,100));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));outer.RowStyles.Add(new RowStyle(SizeType.Absolute,28)); Controls.Add(outer);''',
'''      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,72));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,126));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      outer.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,26));
      var shell=new TableLayoutPanel{
        Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,
        Margin=new Padding(0),Padding=new Padding(0),BackColor=bg
      };
      shell.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,176));
      shell.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      nordicSidebar=CreateNordicSidebar();
      shell.Controls.Add(nordicSidebar,0,0);
      shell.Controls.Add(outer,1,0);
      Controls.Add(shell);''')
one('''      head.Controls.Add(new Label {Text="T-Net",Dock=DockStyle.Fill,AutoEllipsis=false,TextAlign=ContentAlignment.MiddleLeft,ForeColor=Color.White,Font=new Font("Segoe UI",24,FontStyle.Bold),Padding=new Padding(8,0,0,0)},0,0);''',
'''      head.Controls.Add(new Label {Text="Overview",Dock=DockStyle.Fill,AutoEllipsis=false,
        TextAlign=ContentAlignment.MiddleLeft,ForeColor=ink,
        Font=new Font("Segoe UI",20,FontStyle.Bold),
        Padding=new Padding(8,0,0,0)},0,0);''')
one('''      head.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,120));''',
    '''      head.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,154));''')

# Embed selected three-position appearance selector directly in command bar.
# Preserve old field / persistence functions as compatibility paths.
one('''      headerActions.Controls.Add(appearanceButton);
      // Keep the update action visually readable even while checking.''',
'''      nordicAppearanceStrip=new FlowLayoutPanel{
        Width=246,Height=36,Margin=new Padding(4,2,4,2),
        WrapContents=false,FlowDirection=FlowDirection.LeftToRight,
        Padding=new Padding(3),BackColor=Color.FromArgb(229,238,251)
      };
      nordicLightButton=NordicModeButton("☀  Light","light");
      nordicDarkButton=NordicModeButton("☾  Dark","dark");
      nordicAutoButton=NordicModeButton("◐  Auto","system");
      nordicAppearanceStrip.Controls.Add(nordicLightButton);
      nordicAppearanceStrip.Controls.Add(nordicDarkButton);
      nordicAppearanceStrip.Controls.Add(nordicAutoButton);
      headerActions.Controls.Add(nordicAppearanceStrip);
      // Keep the update action visually readable even while checking.''')
one('''      headerActions.Controls.SetChildIndex(appearanceButton,2);''',
    '''      headerActions.Controls.SetChildIndex(nordicAppearanceStrip,2);''')

one('''        name=="Download speed"?Color.FromArgb(66,149,220):
        name=="Upload speed"?Color.FromArgb(45,168,127):''',
'''        name=="Download speed"?Color.FromArgb(66,149,220):
        name=="Upload speed"?Color.FromArgb(45,168,127):
        name=="Wi-Fi signal"?Color.FromArgb(33,167,135):''')

# Use four balanced top statistics cards including the real signal percentage.
one('''      var metrics=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=3};
      for(int i=0;i<3;i++)metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100f/3));''',
'''      var metrics=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=4};
      for(int i=0;i<4;i++)metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,25));''')
one('''      downloadSpeed=down;uploadSpeed=up;
      outer.Controls.Add(metrics,0,1);''',
'''      downloadSpeed=down;uploadSpeed=up;
      nordicSignalMetric=Metric(metrics,"Wi-Fi signal",3);
      outer.Controls.Add(metrics,0,1);''')
one('''      var middle=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2};middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,48));middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,52));''',
'''      var middle=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,
        Margin=new Padding(0),Padding=new Padding(0)};
      middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,64));
      middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,36));''')
one('''      var net=PanelCard();''',
'''      var net=PanelCard();
      nordicNetworkPanel=net;''')
one('''      middle.Controls.Add(net,0,0);''',
    '''      middle.Controls.Add(net,1,0);''')
one('''      chPanel.Controls.Add(graphLayout);middle.Controls.Add(chPanel,1,0);''',
    '''      chPanel.Controls.Add(graphLayout);middle.Controls.Add(chPanel,0,0);''')

# Updating the real Windows-reported Wi-Fi signal also updates the hero metric.
one('''        signalStrength.Text="—";
        signalStrengthFill.Width=0;''',
'''        signalStrength.Text="—";
        if(nordicSignalMetric!=null)nordicSignalMetric.Text="—";
        signalStrengthFill.Width=0;''')
one('''      signalStrength.Text=value.ToString(CultureInfo.InvariantCulture)+"%";''',
'''      signalStrength.Text=value.ToString(CultureInfo.InvariantCulture)+"%";
      if(nordicSignalMetric!=null)nordicSignalMetric.Text=signalStrength.Text;''')

# Keep chart readability in light mode while retaining all original data.
one('''      StyleSelectedUsagePeriod();
      if(chartViewDropdown!=null){''',
'''      StyleSelectedUsagePeriod();
      StyleNordicShell(useLight);
      if(chart!=null && chart.Series.Count>0)
        chart.Series[0].Color=useLight?Color.FromArgb(61,127,235):accent;
      if(chartViewDropdown!=null){''')

# The appearance setting still uses SelectAppearance and follows Windows.
one('''    void ShapeAppearanceButton(){''',
'''    Button NordicModeButton(string title,string mode){
      var button=new Button{Text=title,Width=78,Height=28,
        Margin=new Padding(1,1,1,1),Padding=new Padding(0),
        FlatStyle=FlatStyle.Flat,Font=new Font("Segoe UI",8),
        TextAlign=ContentAlignment.MiddleCenter};
      button.FlatAppearance.BorderSize=0;
      button.Click+=(sender,e)=>SelectAppearance(mode);
      return button;
    }
    Button NordicNavButton(string label,int destination){
      var button=new Button{
        Text=label,Dock=DockStyle.Top,Height=43,
        TextAlign=ContentAlignment.MiddleLeft,FlatStyle=FlatStyle.Flat,
        Font=new Font("Segoe UI",10),Margin=new Padding(0,0,0,5),
        Padding=new Padding(13,0,0,0),TabStop=true
      };
      button.FlatAppearance.BorderSize=0;
      button.Click+=(sender,e)=>{
        nordicSelectedNav=button;
        StyleNordicShell(appearanceIsLight);
        if(destination==0)SetGraphView(0);
        else if(destination==1)SetGraphView(3);
        else if(destination==2){
          if(nordicNetworkPanel!=null)nordicNetworkPanel.Focus();
        }
        else if(destination==3)SetGraphView(2);
        else if(destination==4){
          if(nordicLightButton!=null)nordicLightButton.Focus();
        }
      };
      nordicNavButtons.Add(button);
      if(destination==0)nordicSelectedNav=button;
      return button;
    }
    Panel CreateNordicSidebar(){
      var aside=new Panel{Dock=DockStyle.Fill,Padding=new Padding(12,26,12,16),
        BackColor=Color.White,Tag="nordic-sidebar"};
      var brand=new Label{Text="◉ T-Net",Dock=DockStyle.Top,Height=70,
        Font=new Font("Segoe UI",19,FontStyle.Bold),
        ForeColor=Color.FromArgb(37,107,220),
        TextAlign=ContentAlignment.MiddleLeft};
      aside.Controls.Add(brand);
      var navigation=new Panel{Dock=DockStyle.Top,Height=260,
        Margin=new Padding(0),Padding=new Padding(0,8,0,0)};
      // Add in reverse for top dock stacking order.
      navigation.Controls.Add(NordicNavButton("⚙   Settings",4));
      navigation.Controls.Add(NordicNavButton("◷   History",3));
      navigation.Controls.Add(NordicNavButton("⌁   Network",2));
      navigation.Controls.Add(NordicNavButton("▥   Usage",1));
      navigation.Controls.Add(NordicNavButton("⌂   Dashboard",0));
      aside.Controls.Add(navigation);
      navigation.BringToFront();
      brand.BringToFront();
      return aside;
    }
    void StyleNordicShell(bool light){
      Color blue=Color.FromArgb(44,114,227);
      if(nordicSidebar!=null){
        nordicSidebar.BackColor=light?Color.White:Color.FromArgb(18,27,44);
      }
      foreach(var nav in nordicNavButtons){
        if(nav==null)continue;
        bool selected=nav==nordicSelectedNav;
        nav.ForeColor=selected?blue:(light?lightInk:darkMuted);
        nav.BackColor=selected?
          (light?Color.FromArgb(224,236,254):Color.FromArgb(37,57,82)):
          (light?Color.White:Color.FromArgb(18,27,44));
        nav.FlatAppearance.MouseOverBackColor=light?
          Color.FromArgb(235,243,255):Color.FromArgb(44,61,86);
      }
      if(nordicAppearanceStrip!=null){
        nordicAppearanceStrip.BackColor=light?
          Color.FromArgb(229,238,251):Color.FromArgb(35,48,69);
        foreach(var button in new[]{nordicLightButton,nordicDarkButton,nordicAutoButton}){
          if(button==null)continue;
          string mode=button==nordicLightButton?"light":
            button==nordicDarkButton?"dark":"system";
          bool selected=appearanceMode==mode;
          button.ForeColor=selected?(light?blue:Color.FromArgb(152,188,255)):
            (light?lightMuted:darkMuted);
          button.BackColor=selected?
            (light?Color.White:Color.FromArgb(53,71,104)):
            (light?Color.FromArgb(229,238,251):Color.FromArgb(35,48,69));
        }
      }
    }
    void ShapeAppearanceButton(){''')

# Keep in theme selection and normal refresh automatic light/dark changes.
one('''      appearanceMode=choice;
      try{''',
'''      appearanceMode=choice;
      try{''')

for term in (
'const string AppVersion = "6.27.0";',
'CreateNordicSidebar()',
'nordicAppearanceStrip.Controls.Add(nordicLightButton);',
'nordicAppearanceStrip.Controls.Add(nordicDarkButton);',
'nordicAppearanceStrip.Controls.Add(nordicAutoButton);',
'nordicSignalMetric=Metric(metrics,"Wi-Fi signal",3);',
'middle.Controls.Add(net,1,0);',
'middle.Controls.Add(chPanel,0,0);',
'StyleNordicShell(useLight);',
'new VScrollBar{',
'void DrawSignalPulse(Graphics g,Rectangle bounds,int? signalPercent)',
'TrackUsageCheckpoint(',
'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");',
'chartViewDropdown.Items.AddRange'
):
    if term not in s:raise RuntimeError('Missing Nordic or preserved feature '+term)
p.write_text(s,encoding="utf-8")
print('Nordic Canvas v6.27: left navigation, light blue/white cards, signal metric, main chart, segmented appearance; monitoring untouched')
