from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(old,new):
    global s
    n=s.count(old)
    if n!=1:raise RuntimeError("Expected exactly one source anchor, got %d: %r"%(n,old[:160]))
    s=s.replace(old,new)

one('const string AppVersion = "6.22.0";','const string AppVersion = "6.23.0";')

# Put the live animated arrows in the TWO EXISTING speed metric cards, not
# beside Monitoring live. They use the exact existing speed label values.
one('''      downloadSpeed=CompactSpeedPill(headerActions,"↓",Color.FromArgb(65,156,235));
      uploadSpeed=CompactSpeedPill(headerActions,"↑",Color.FromArgb(52,180,137));''',
'''      // Speed displays are now in their dashboard cards below.
      // No speed pills are inserted alongside Monitoring live.''')
one('''      down=Metric(metrics,"Download speed",1);
      up=Metric(metrics,"Upload speed",2);''',
'''      down=ArrowSpeedCard(metrics,"Download speed",1,"↓",Color.FromArgb(65,156,235));
      up=ArrowSpeedCard(metrics,"Upload speed",2,"↑",Color.FromArgb(52,180,137));
      downloadSpeed=down;uploadSpeed=up;''')
one('''    Label CompactSpeedPill(FlowLayoutPanel parent,string arrow,Color color){''',
'''    Label ArrowSpeedCard(TableLayoutPanel parent,string name,int col,string arrow,Color color){
      var card=PanelCard();
      var stack=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=2,ColumnCount=1,
        Margin=new Padding(0)};
      stack.RowStyles.Add(new RowStyle(SizeType.Percent,37));
      stack.RowStyles.Add(new RowStyle(SizeType.Percent,63));
      var caption=new Label{Text=name,ForeColor=color,Dock=DockStyle.Fill,
        Font=new Font("Segoe UI",10,FontStyle.Regular),
        TextAlign=ContentAlignment.MiddleLeft};
      stack.Controls.Add(caption,0,0);
      var content=new FlowLayoutPanel{Dock=DockStyle.Fill,FlowDirection=FlowDirection.LeftToRight,
        WrapContents=false,AutoScroll=false,Margin=new Padding(0),Padding=new Padding(0)};
      var arrowLabel=new Label{Text=arrow,Size=new Size(36,40),
        Margin=new Padding(0,5,5,0),Font=new Font("Segoe UI",21,FontStyle.Bold),
        ForeColor=color,TextAlign=ContentAlignment.MiddleCenter};
      var speedValue=new Label{Text="— Kbps",AutoSize=true,
        MaximumSize=new Size(220,50),Margin=new Padding(0,9,0,0),
        Font=new Font("Segoe UI",20,FontStyle.Bold),ForeColor=ink,
        TextAlign=ContentAlignment.MiddleLeft};
      content.Controls.Add(arrowLabel);content.Controls.Add(speedValue);
      if(arrow=="↓")downloadArrow=arrowLabel;
      else uploadArrow=arrowLabel;
      stack.Controls.Add(content,0,1);
      card.Controls.Add(stack);parent.Controls.Add(card,col,0);
      return speedValue;
    }
    Label CompactSpeedPill(FlowLayoutPanel parent,string arrow,Color color){''')
# The earlier renderer used the same label twice, now speed and card are aliases.
one('''      downloadSpeed=down;uploadSpeed=up;''','''      downloadSpeed=down;uploadSpeed=up;''')
one('''      if(downloadArrow!=null && !downloadArrow.IsDisposed)
        downloadArrow.Top=downloadArrowMoving?
          (6+((telemetryAnimationFrame/2)%3)):6;
      if(uploadArrow!=null && !uploadArrow.IsDisposed)
        uploadArrow.Top=uploadArrowMoving?
          (8-((telemetryAnimationFrame/2)%3)):6;''',
'''      if(downloadArrow!=null && !downloadArrow.IsDisposed)
        downloadArrow.Margin=new Padding(0,downloadArrowMoving?
          5+((telemetryAnimationFrame/2)%3):5,5,0);
      if(uploadArrow!=null && !uploadArrow.IsDisposed)
        uploadArrow.Margin=new Padding(0,uploadArrowMoving?
          7-((telemetryAnimationFrame/2)%3):5,5,0);''')
# Do not assign a label's Text to itself after associating references.
one('''        down.Text=downloadSpeed.Text;
        up.Text=uploadSpeed.Text;''',
'''        // The metric labels are the speed labels; no duplicated top header display.''')
# In both failure handlers, speed references are also the metric values.
one('''          if(down!=null)down.Text=downloadSpeed.Text;
          if(up!=null)up.Text=uploadSpeed.Text;''','''          // The metric cards already show the unavailable speed state.''')
one('''        if(down!=null)down.Text=downloadSpeed.Text;
        if(up!=null)up.Text=uploadSpeed.Text;''','''        // The metric cards already show the unavailable speed state.''')

# Proper visual LTR sequence is Appearance -> Check for updates -> Monitoring live.
# FlowLayoutPanel is RightToLeft, so its child ordering is the reverse.
one('''      headerActions.Controls.Add(appearanceButton);
      ShapeAppearanceButton();''',
'''      headerActions.Controls.Add(appearanceButton);
      headerActions.Controls.SetChildIndex(statusLine,0);
      headerActions.Controls.SetChildIndex(updateButton,1);
      headerActions.Controls.SetChildIndex(appearanceButton,2);
      // Keep the update action visually readable even while checking.
      updateButton.BackColor=Color.FromArgb(38,57,81);
      updateButton.ForeColor=Color.White;
      updateButton.Font=new Font("Segoe UI",9,FontStyle.Regular);
      ShapeAppearanceButton();''')
one('''      checkingUpdates=true;if(updateButton!=null)updateButton.Enabled=false;''',
'''      // A guard above prevents duplicate checks; don't fade the button during a check.
      checkingUpdates=true;''')
one('''      StyleSelectedUsagePeriod();
      if(appearanceButton!=null){''',
'''      StyleSelectedUsagePeriod();
      if(updateButton!=null){
        updateButton.BackColor=useLight?Color.FromArgb(218,231,245):
          Color.FromArgb(38,57,81);
        updateButton.ForeColor=useLight?lightInk:Color.White;
      }
      if(appearanceButton!=null){''')

# Network card: slightly larger headline, adapter, and Wi-Fi signal headings.
# Retain genuine scrollbar and keep lower information below the fold.
one('''      var networkTitle=LabelText("Network",15,true);''',
'''      var networkTitle=LabelText("Network",17,true);''')
one('''      var adapterCaption=LabelText("Adapter",10);''',
'''      var adapterCaption=LabelText("Adapter",11);''')
one('''      var signalCaption=LabelText("Wi-Fi signal strength",10);''',
'''      var signalCaption=LabelText("Wi-Fi signal strength",11);''')
one('''      adapter=LabelText("—",11,true);''',
'''      adapter=LabelText("—",12,true);''')
one('''      signalStrength=LabelText("—",11,true);''',
'''      signalStrength=LabelText("—",12,true);''')
# Last update becomes a compact disclosure inside the existing scrolling section.
one('''      detailScroll.Controls.Add(LabelText("Last update"));last=LabelText("—");detailScroll.Controls.Add(last);''',
'''      var lastUpdateDisclosure=new Button{Text="▸ Last update",AutoSize=false,
        Width=224,Height=30,Margin=new Padding(0,4,0,0),
        TextAlign=ContentAlignment.MiddleLeft,FlatStyle=FlatStyle.Flat,
        BackColor=Color.FromArgb(32,46,68),ForeColor=ink,
        Font=new Font("Segoe UI",10)};
      lastUpdateDisclosure.FlatAppearance.BorderSize=0;
      last=LabelText("—",10);last.AutoSize=false;
      last.Width=224;last.Height=28;last.Visible=false;
      lastUpdateDisclosure.Click+=(sender,e)=>{
        last.Visible=!last.Visible;
        lastUpdateDisclosure.Text=last.Visible?"▾ Last update":"▸ Last update";
      };
      detailScroll.Controls.Add(lastUpdateDisclosure);
      detailScroll.Controls.Add(last);''')
one('''      detailScroll.Controls.Add(new Label{Text="Scroll for more details",AutoSize=true,ForeColor=muted,Padding=new Padding(0,12,0,5)});''',
'''      // Redundant "Scroll for more details" label removed; keep the real scrollbar.''')

# Daily, Weekly, Monthly remain in the top toolbar; replace two other
# toolbar buttons by ONE explicit view dropdown under the chart.
one('''    Button graphToggle,dayUsageButton,weekUsageButton,monthUsageButton;''',
'''    Button graphToggle,dayUsageButton,weekUsageButton,monthUsageButton;
    ComboBox chartViewDropdown;
    bool syncingChartViewDropdown=false;''')
one('''      var graphHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=5,RowCount=1};
      for(int i=0;i<5;i++)graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,20));
      graphToggle.Dock=DockStyle.Fill;
      graphToggle.Width=0;graphToggle.Font=new Font("Segoe UI",9);
      usageLogToggle.Dock=DockStyle.Fill;
      usageLogToggle.Width=0;usageLogToggle.Font=new Font("Segoe UI",9);
      graphHeader.Controls.Add(graphToggle,3,0);
      graphHeader.Controls.Add(usageLogToggle,4,0);''',
'''      var graphHeader=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=3,RowCount=1};
      for(int i=0;i<3;i++)graphHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100f/3));
      // Live speed and Usage log move to the chart footer dropdown.''')
one('''      chartCaption=new Label{Text="Today's usage: 0 B",Dock=DockStyle.Fill,ForeColor=muted,''',
'''      chartCaption=new Label{Text="Today's usage: 0 B",Dock=DockStyle.Fill,ForeColor=muted,''')
one('''      var graphLayout=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=3,ColumnCount=1};''',
'''      chartViewDropdown=new ComboBox{
        DropDownStyle=ComboBoxStyle.DropDownList,Width=132,
        Dock=DockStyle.Fill,Margin=new Padding(3,0,3,0),
        Font=new Font("Segoe UI",9),
        BackColor=panel,ForeColor=ink
      };
      chartViewDropdown.Items.AddRange(new object[]{"Usage chart","Live speed","Usage log"});
      chartViewDropdown.SelectedIndex=0;
      chartViewDropdown.SelectedIndexChanged+=(sender,e)=>{
        if(syncingChartViewDropdown)return;
        int selection=chartViewDropdown.SelectedIndex;
        SetGraphView(selection==1?1:selection==2?2:currentUsageView);
      };
      var chartFooter=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,
        Margin=new Padding(0)};
      chartFooter.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
      chartFooter.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,139));
      chartFooter.Controls.Add(chartCaption,0,0);
      chartFooter.Controls.Add(chartViewDropdown,1,0);
      var graphLayout=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=3,ColumnCount=1};''')
one('''      graphLayout.Controls.Add(chartCaption,0,2);''',
'''      graphLayout.Controls.Add(chartFooter,0,2);''')
one('''      if(view==0||view==3||view==4)currentUsageView=view;''',
'''      if(view==0||view==3||view==4)currentUsageView=view;
      if(chartViewDropdown!=null){
        int index=view==1?1:view==2?2:0;
        if(chartViewDropdown.SelectedIndex!=index){
          syncingChartViewDropdown=true;
          chartViewDropdown.SelectedIndex=index;
          syncingChartViewDropdown=false;
        }
      }''')
one('''      if(showLiveChart)RenderLiveSpeedGraph();
      else if(showUsageLog){
        chartCaption.Text=usageLogError.Length>0?
          "Log saving error: "+usageLogError:
          "Interval end shown in WAT (UTC+01:00)  •  hover time for range  •  click to open CSV";
        chartCaption.Cursor=Cursors.Hand;
      }else{
        chartCaption.Cursor=Cursors.Default;
        RenderUsagePeriod();
        UpdateUsageCaption();
      }''',
'''      if(showLiveChart)RenderLiveSpeedGraph();
      else if(!showUsageLog)RenderUsagePeriod();
      chartCaption.Cursor=showUsageLog?Cursors.Hand:Cursors.Default;
      UpdateUsageCaption();''')
one('''      if(chartCaption==null || showLiveChart || showUsageLog)return;''',
'''      if(chartCaption==null)return;''')
one('''      StyleSelectedUsagePeriod();
      if(updateButton!=null){''',
'''      StyleSelectedUsagePeriod();
      if(chartViewDropdown!=null){
        chartViewDropdown.BackColor=useLight?lightPanel:darkPanel;
        chartViewDropdown.ForeColor=useLight?lightInk:darkInk;
      }
      if(updateButton!=null){''')
# Make sure the unused graphToggle/usageLogToggle fields are still referenced
# in their creation and SetGraphView; they are no longer visible controls.
for q in ['const string AppVersion = "6.23.0";',
          'chartViewDropdown.Items.AddRange','new VScrollBar{',
          'headerActions.Controls.SetChildIndex(updateButton,1)',
          'lastUpdateDisclosure.Text=last.Visible',
          'DrawSignalPulse(Graphics g,Rectangle bounds,int? signalPercent)',
          'signalTrayPopup.Deactivate+=',
          'down=ArrowSpeedCard','up=ArrowSpeedCard',
          'downloadArrowMoving=','uploadArrowMoving=',
          'graphHeader.Controls.Add(dayUsageButton,0,0)',
          'graphHeader.Controls.Add(weekUsageButton,1,0)',
          'graphHeader.Controls.Add(monthUsageButton,2,0)',
          'MonthTotalFromExistingDays(d)']:
    if q not in s:raise RuntimeError("Missing expected feature "+q)
p.write_text(s,encoding="utf-8")
print("PASS: v6.23 layout patch, no engine modifications")
