from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(old,new):
    global s
    n=s.count(old)
    if n!=1: raise RuntimeError("Expected exactly one v6.27 anchor, got %d: %r"%(n,old[:180]))
    s=s.replace(old,new)

one('const string AppVersion = "6.27.0";','const string AppVersion = "6.28.0";')

# Reference option 02: one top header with T-Net branded sidebar,
# live status, a compact Appearance dropdown, and Check for updates.
# No large "Overview" heading or 3-segment control in the header.
one('''      head.Controls.Add(new Label {Text="Overview",Dock=DockStyle.Fill,AutoEllipsis=false,
        TextAlign=ContentAlignment.MiddleLeft,ForeColor=ink,
        Font=new Font("Segoe UI",20,FontStyle.Bold),
        Padding=new Padding(8,0,0,0)},0,0);''',
'''      head.Controls.Add(new Label {Text="",Dock=DockStyle.Fill,Margin=new Padding(0)},0,0);''')
one('''      head.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,154));''',
    '''      head.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,0));''')

one('''      nordicAppearanceStrip.Controls.Add(nordicAutoButton);
      headerActions.Controls.Add(nordicAppearanceStrip);''',
'''      nordicAppearanceStrip.Controls.Add(nordicAutoButton);
      // Match the reference: one polished Appearance dropdown in the header.
      // Preserve the three existing mode choices inside that dropdown.
      appearanceButton.Text="◐ Appearance  ▾";
      appearanceButton.Width=147;
      headerActions.Controls.Add(appearanceButton);''')
one('''      headerActions.Controls.SetChildIndex(nordicAppearanceStrip,2);''',
'''      // RTL FlowLayoutPanel child ordering is reverse visual ordering.
      // Left-to-right result: Monitoring live | Appearance | Check for updates.
      headerActions.Controls.SetChildIndex(updateButton,0);
      headerActions.Controls.SetChildIndex(appearanceButton,1);
      headerActions.Controls.SetChildIndex(statusLine,2);''')
one('''        appearanceButton.Text="Appearance  ▾";''',
    '''        appearanceButton.Text="◐ Appearance  ▾";''')

# The chosen reference has a single row of THREE top tiles (download,
# upload, Wi-Fi) over a large usage chart. The tall NETWORK panel is on
# the right of both rows. Previous v6.27 kept four cards over two equal
# lower columns; explicitly replace that old composition.
one('''      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,72));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,126));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      outer.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,26));''',
'''      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,55));
      outer.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,0));
      outer.RowStyles.Add(new RowStyle(SizeType.Absolute,22));''')
one('''      var outer=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=1, RowCount=6, Padding=new Padding(18), BackColor=bg };''',
'''      var outer=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=1,
        RowCount=6, Padding=new Padding(11), BackColor=bg };''')
one('''      shell.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,176));''',
    '''      shell.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,157));''')
one('''      var metrics=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=4};
      for(int i=0;i<4;i++)metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,25));
      today=Metric(metrics,"Today",0);
      down=ArrowSpeedCard(metrics,"Download speed",1,"↓",Color.FromArgb(65,156,235));
      up=ArrowSpeedCard(metrics,"Upload speed",2,"↑",Color.FromArgb(52,180,137));''',
'''      var metrics=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=3,
        Margin=new Padding(0),Padding=new Padding(0)};
      for(int i=0;i<3;i++)metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100f/3));
      // Keep the Today label as a hidden data target for the existing engine.
      // The reference uses a consumption caption beneath the chart instead.
      today=new Label{Visible=false};
      down=ArrowSpeedCard(metrics,"Download speed",0,"↓",Color.FromArgb(65,156,235));
      up=ArrowSpeedCard(metrics,"Upload speed",1,"↑",Color.FromArgb(52,180,137));''')
one('''      nordicSignalMetric=Metric(metrics,"Wi-Fi signal",3);
      outer.Controls.Add(metrics,0,1);''',
'''      nordicSignalMetric=Metric(metrics,"Wi-Fi signal",2);
      // Metrics now belong to the upper-left body cell, not a full-width row.''')
one('''      var middle=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,
        Margin=new Padding(0),Padding=new Padding(0)};
      middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,64));
      middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,36));''',
'''      var middle=new TableLayoutPanel{Dock=DockStyle.Fill,
        ColumnCount=2,RowCount=2,Margin=new Padding(0),Padding=new Padding(0)};
      middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,65));
      middle.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,35));
      middle.RowStyles.Add(new RowStyle(SizeType.Absolute,112));
      middle.RowStyles.Add(new RowStyle(SizeType.Percent,100));
      middle.Controls.Add(metrics,0,0);''')
one('''      middle.Controls.Add(net,1,0);''',
'''      middle.Controls.Add(net,1,0);
      middle.SetRowSpan(net,2);''')
# Narrow windows must not clip the signal readout inside the right card.
one('''      signalRow.Controls.Add(signalStrengthTrack);
      signalRow.Controls.Add(signalStrength);''',
'''      signalRow.Controls.Add(signalStrengthTrack);
      signalRow.Controls.Add(signalStrength);
      Action fitNordicSignal=()=>{
        if(net==null || signalStrengthTrack==null)return;
        int usable=Math.Max(90,net.ClientSize.Width-net.Padding.Horizontal-90);
        signalStrengthTrack.Width=Math.Min(210,usable);
        signalRow.Width=Math.Max(175,signalStrengthTrack.Width+84);
      };
      net.SizeChanged+=(sender,e)=>fitNordicSignal();
      fitNordicSignal();''')

one('''      chPanel.Controls.Add(graphLayout);middle.Controls.Add(chPanel,0,0);''',
    '''      chPanel.Controls.Add(graphLayout);middle.Controls.Add(chPanel,0,1);''')
one('''      outer.Controls.Add(middle,0,3);''',
    '''      outer.Controls.Add(middle,0,1);''')

# Refine the compact top tiles so they resemble option 02, not giant
# inherited cards. Restrained blue/purple accents, small rounded icons.
one('''      var arrowLabel=new Label{Text=arrow,Size=new Size(36,40),
        Margin=new Padding(0,5,5,0),Font=new Font("Segoe UI",21,FontStyle.Bold),''',
'''      var arrowLabel=new Label{Text=arrow,Size=new Size(30,34),
        Margin=new Padding(0,3,7,0),Font=new Font("Segoe UI",16,FontStyle.Bold),''')
one('''      var speedValue=new Label{Text="— Kbps",AutoSize=true,
        MaximumSize=new Size(220,50),Margin=new Padding(0,9,0,0),
        Font=new Font("Segoe UI",20,FontStyle.Bold),''',
'''      var speedValue=new Label{Text="— Kbps",AutoSize=true,
        MaximumSize=new Size(180,39),Margin=new Padding(0,6,0,0),
        Font=new Font("Segoe UI",15,FontStyle.Bold),''')
one('''      stack.RowStyles.Add(new RowStyle(SizeType.Percent,37));
      stack.RowStyles.Add(new RowStyle(SizeType.Percent,63));''',
'''      stack.RowStyles.Add(new RowStyle(SizeType.Percent,41));
      stack.RowStyles.Add(new RowStyle(SizeType.Percent,59));''')

# The original metric used oversized 20-point numerals, unlike option 02.
one('''      nordicSignalMetric=Metric(metrics,"Wi-Fi signal",2);''',
'''      nordicSignalMetric=Metric(metrics,"Wi-Fi signal",2);
      nordicSignalMetric.Font=new Font("Segoe UI",16,FontStyle.Bold);''')
one('''      nordicSignalMetric.Font=new Font("Segoe UI",16,FontStyle.Bold);''',
'''      nordicSignalMetric.Font=new Font("Segoe UI",16,FontStyle.Bold);
      nordicSignalMetric.Text="—";''')


# Opt 02 uses a softly blue sidebar and inset selected nav, not a white slab.
one('''      var aside=new Panel{Dock=DockStyle.Fill,Padding=new Padding(12,26,12,16),
        BackColor=Color.White,Tag="nordic-sidebar"};''',
'''      var aside=new Panel{Dock=DockStyle.Fill,Padding=new Padding(10,15,10,12),
        BackColor=Color.FromArgb(238,245,255),Tag="nordic-sidebar"};''')
one('''      var brand=new Label{Text="◉ T-Net",Dock=DockStyle.Top,Height=70,
        Font=new Font("Segoe UI",19,FontStyle.Bold),''',
'''      var brand=new Label{Text="◉ T-Net",Dock=DockStyle.Top,Height=64,
        Font=new Font("Segoe UI",17,FontStyle.Bold),''')
one('''        nordicSidebar.BackColor=light?Color.White:Color.FromArgb(18,27,44);''',
'''        nordicSidebar.BackColor=light?Color.FromArgb(238,245,255):Color.FromArgb(18,27,44);''')
one('''          (light?Color.White:Color.FromArgb(18,27,44));''',
'''          (light?Color.FromArgb(238,245,255):Color.FromArgb(18,27,44));''')


# Header branding stays at the TOP of the sidebar, and navigation beneath.
# Avoid top-docking order which placed the brand under the navigation.
one('''      var brand=new Label{Text="◉ T-Net",Dock=DockStyle.Top,Height=64,
        Font=new Font("Segoe UI",17,FontStyle.Bold),''',
'''      var brand=new Label{Text="◉ T-Net",Dock=DockStyle.None,
        Location=new Point(12,17),Size=new Size(138,47),
        Font=new Font("Segoe UI",17,FontStyle.Bold),''')
one('''      var navigation=new Panel{Dock=DockStyle.Top,Height=260,
        Margin=new Padding(0),Padding=new Padding(0,8,0,0)};''',
'''      var navigation=new Panel{Dock=DockStyle.None,
        Location=new Point(10,84),Size=new Size(137,260),
        Margin=new Padding(0),Padding=new Padding(0,8,0,0)};''')

# The old native menu was visually plain. Use a compact rounded, segmented
# Light / Dark / Auto popover, preserving actual saved theme logic.
one('''    void ShowAppearanceMenu(){
      if(appearanceMenu!=null){appearanceMenu.Dispose();appearanceMenu=null;}
      appearanceMenu=new ContextMenuStrip();
      foreach(string item in new[]{"Light","Dark","System"}){
        string value=item.ToLowerInvariant();
        string display=item=="Light"?"☀  Light mode":
          item=="Dark"?"☾  Dark mode":"▣  Follow Windows";
        appearanceMenu.Items.Add(new ToolStripMenuItem(
          display,null,(sender,e)=>SelectAppearance(value)){
            Checked=appearanceMode==value
          });
      }
      appearanceMenu.Font=new Font("Segoe UI",10);
      appearanceMenu.Padding=new Padding(5);
      appearanceMenu.ShowImageMargin=false;
      appearanceMenu.BackColor=appearanceIsLight?lightPanel:darkPanel;
      appearanceMenu.ForeColor=appearanceIsLight?lightInk:darkInk;
      appearanceMenu.Show(appearanceButton,new Point(0,appearanceButton.Height));
    }''',
'''    void ShowAppearanceMenu(){
      if(appearanceMenu!=null){appearanceMenu.Dispose();appearanceMenu=null;}
      appearanceMenu=new ContextMenuStrip{
        ShowImageMargin=false,ShowCheckMargin=false,
        Padding=new Padding(6),BackColor=appearanceIsLight?
          Color.White:darkPanel
      };
      var options=new FlowLayoutPanel{
        Size=new Size(266,42),Margin=new Padding(0),
        Padding=new Padding(4),WrapContents=false,
        FlowDirection=FlowDirection.LeftToRight,
        BackColor=appearanceIsLight?
          Color.FromArgb(230,240,252):Color.FromArgb(35,48,69)
      };
      foreach(string choice in new[]{"light","dark","system"}){
        string label=choice=="light"?"☀ Light":
          choice=="dark"?"☾ Dark":"◐ Auto";
        bool selected=appearanceMode==choice;
        var button=new Button{Text=label,
          Size=new Size(82,32),Margin=new Padding(1),
          FlatStyle=FlatStyle.Flat,
          Font=new Font("Segoe UI",9,selected?FontStyle.Bold:FontStyle.Regular),
          ForeColor=selected?Color.FromArgb(44,114,227):
            (appearanceIsLight?lightInk:darkInk),
          BackColor=selected?
            (appearanceIsLight?Color.White:Color.FromArgb(55,74,103)):
            (appearanceIsLight?Color.FromArgb(230,240,252):
              Color.FromArgb(35,48,69))
        };
        button.FlatAppearance.BorderSize=0;
        string mode=choice;
        button.Click+=(sender,e)=>{
          SelectAppearance(mode);
          if(appearanceMenu!=null)appearanceMenu.Close();
        };
        options.Controls.Add(button);
      }
      var host=new ToolStripControlHost(options){
        AutoSize=false,Size=new Size(266,42),
        Margin=new Padding(0),Padding=new Padding(0)
      };
      appearanceMenu.Items.Add(host);
      appearanceMenu.Show(appearanceButton,new Point(0,appearanceButton.Height+3));
    }''')


# The reference's actions and period selectors are rounded pills, not the
# original square WinForms buttons. Retain all existing click handlers.
one('''      graphHeader.Controls.Add(monthUsageButton,2,0);''',
'''      graphHeader.Controls.Add(monthUsageButton,2,0);
      foreach(var tab in new[]{dayUsageButton,weekUsageButton,monthUsageButton}){
        tab.FlatAppearance.BorderSize=0;
        tab.Resize+=(sender,e)=>RoundSurface(tab,12);
        RoundSurface(tab,12);
      }''')
one('''      updateButton.Font=new Font("Segoe UI",9,FontStyle.Regular);
      ShapeAppearanceButton();''',
'''      updateButton.Font=new Font("Segoe UI",9,FontStyle.Regular);
      updateButton.Resize+=(sender,e)=>RoundSurface(updateButton,12);
      RoundSurface(updateButton,12);
      ShapeAppearanceButton();''')



# Reference design is composed for a wide Windows desktop screen; previous
# v6.27 inherited an overly small 1000px window that crushed both columns.
one('''MinimumSize = new Size(785, 660); Size = new Size(1000, 780);''',
    '''MinimumSize = new Size(1030, 670); Size = new Size(1320, 790);''')
# FINAL VISUAL-PARITY PASS: Option 02's top speed tiles are softly elevated,
# the network panel reads as a compact inspection card, and no-data charts
# must not look like a broken white rectangle.
one('''      var card=PanelCard();
      var stack=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=2,ColumnCount=1,''',
'''      var card=PanelCard();
      card.Padding=new Padding(13,11,12,10);
      var stack=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=2,ColumnCount=1,''')
one('''      var caption=new Label{Text=name,ForeColor=color,Dock=DockStyle.Fill,
        Font=new Font("Segoe UI",10,FontStyle.Regular),''',
'''      var caption=new Label{Text=name,ForeColor=muted,Dock=DockStyle.Fill,
        Font=new Font("Segoe UI",9,FontStyle.Regular),''')
# The brand in the reference uses a blue wireless symbol with blue T-Net text.
# Ensure selected navigation has a blue outline/shading, like reference.
# Contrast and spacing on the right network information panel.
one('''      var net=PanelCard();
      nordicNetworkPanel=net;''',
'''      var net=PanelCard();
      net.Padding=new Padding(15,16,14,16);
      nordicNetworkPanel=net;''')
# Give the chart area its own true white surface with distinctive airy padding.
one('''      var chPanel=PanelCard();''',
'''      var chPanel=PanelCard();
      chPanel.Padding=new Padding(14,15,14,13);''')
# The daily/weekly/monthly selectors are compact, soft-blue rounded chips.
one('''      foreach(var tab in new[]{dayUsageButton,weekUsageButton,monthUsageButton}){
        tab.FlatAppearance.BorderSize=0;''',
'''      foreach(var tab in new[]{dayUsageButton,weekUsageButton,monthUsageButton}){
        tab.Font=new Font("Segoe UI",9,FontStyle.Regular);
        tab.Margin=new Padding(3,3,3,3);
        tab.FlatAppearance.BorderSize=0;''')
# More legible blue daily-usage histogram on Nordic white background.
one('''      if(chart!=null && chart.Series.Count>0)
        chart.Series[0].Color=useLight?Color.FromArgb(61,127,235):accent;''',
'''      if(chart!=null && chart.Series.Count>0){
        chart.Series[0].Color=useLight?Color.FromArgb(57,132,241):accent;
        var axis=chart.ChartAreas[0];
        axis.AxisX.MajorGrid.Enabled=false;
        axis.AxisY.MajorGrid.LineColor=useLight?
          Color.FromArgb(221,232,247):Color.FromArgb(48,60,76);
        axis.AxisX.LineColor=useLight?Color.FromArgb(213,226,245):muted;
        axis.AxisY.LineColor=useLight?Color.FromArgb(213,226,245):muted;
        axis.AxisX.LabelStyle.ForeColor=useLight?lightMuted:darkMuted;
        axis.AxisY.LabelStyle.ForeColor=useLight?lightMuted:darkMuted;
      }''')

# Option 02 uses white cards with a clean, lightly outlined border.
one('''using(var pen=new Pen(Color.FromArgb(211,224,237),1))''',
'''using(var pen=new Pen(Color.FromArgb(223,233,248),1))''')

for q in (
'const string AppVersion = "6.28.0";',
'middle.Controls.Add(metrics,0,0);',
'middle.Controls.Add(chPanel,0,1);',
'middle.SetRowSpan(net,2);',
'middle.Controls.Add(net,1,0);',
'outer.Controls.Add(middle,0,1);',
'appearanceButton.Text="◐ Appearance  ▾";',
'headerActions.Controls.SetChildIndex(updateButton,0);',
'nordicSignalMetric=Metric(metrics,"Wi-Fi signal",2);',
'new VScrollBar{','void DrawSignalPulse(Graphics g,Rectangle bounds,int? signalPercent)',
'UpdateSignalDisplay(Str(d,"wifiSignal"),stat=="tracking");',
'TrackUsageCheckpoint(', 'chartViewDropdown.Items.AddRange'
):
    if q not in s:raise RuntimeError('Missing reference-layout or preserved feature '+q)
p.write_text(s,encoding='utf-8')
print('T-Net v6.28: three top tiles and chart on left, full-height network card on right, sidebar/header match option 02')
