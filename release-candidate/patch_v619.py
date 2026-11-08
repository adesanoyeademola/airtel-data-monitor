from pathlib import Path
p=Path("work/AirtelMonitorNative.cs")
s=p.read_text(encoding="utf-8-sig")
def one(a,b):
    global s
    n=s.count(a)
    if n!=1: raise RuntimeError("Expected exactly one anchor; found %d: %r"%(n,a[:150]))
    s=s.replace(a,b)

one('const string AppVersion = "6.18.0";','const string AppVersion = "6.19.0";')
one('using Microsoft.Win32;','using Microsoft.Win32;\nusing System.Drawing.Drawing2D;')
one('    static readonly Color lightBg=Color.FromArgb(244,247,251);',
    '    static readonly Color lightBg=Color.FromArgb(239,244,249);')
one('    static readonly Color lightInk=Color.FromArgb(28,40,56);',
    '    static readonly Color lightInk=Color.FromArgb(25,39,56);')
one('    static readonly Color lightMuted=Color.FromArgb(91,107,128);',
    '    static readonly Color lightMuted=Color.FromArgb(79,100,124);')

# Only header column distribution changes; dashboard metrics / network / charts
# retain their existing sizes, placements, and layout.
one('head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,64));head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,36));',
    'head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,40));head.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,60));')
one('updateButton = new Button {Text="Check for updates",Width=136,Height=29,Anchor=AnchorStyles.Right,BackColor=Color.FromArgb(32,46,68),ForeColor=Color.White,FlatStyle=FlatStyle.Flat};',
'''updateButton = new Button {Text="Check for updates",Width=136,Height=34,Anchor=AnchorStyles.None,Margin=new Padding(3,3,3,3),BackColor=Color.FromArgb(32,46,68),ForeColor=Color.White,FlatStyle=FlatStyle.Flat};''')
one('''      appearanceButton=new Button{
        Text="◐",Width=32,Height=29,
        BackColor=Color.FromArgb(32,46,68),ForeColor=ink,
        FlatStyle=FlatStyle.Flat,Margin=new Padding(3,0,3,0)
      };
      appearanceButton.FlatAppearance.BorderColor=Color.FromArgb(49,65,86);
      var appearanceTip=new ToolTip();
      appearanceTip.SetToolTip(appearanceButton,"Appearance: Light, Dark or System");
      appearanceButton.Click+=(sender,e)=>ShowAppearanceMenu();
      headerActions.Controls.Add(appearanceButton);''',
'''      // Full-size, labeled rounded selector, aligned to Check for updates.
      // Do not reduce other app controls or use an ambiguous standalone icon.
      appearanceButton=new Button{
        Text="Appearance  ▾",Width=125,Height=34,
        BackColor=Color.FromArgb(32,46,68),ForeColor=ink,
        FlatStyle=FlatStyle.Flat,Margin=new Padding(3,3,3,3),
        TextAlign=ContentAlignment.MiddleCenter,
        Font=new Font("Segoe UI",9,FontStyle.Regular)
      };
      appearanceButton.FlatAppearance.BorderSize=1;
      appearanceButton.FlatAppearance.BorderColor=Color.FromArgb(49,65,86);
      appearanceButton.Resize+=(sender,e)=>ShapeAppearanceButton();
      var appearanceTip=new ToolTip();
      appearanceTip.SetToolTip(appearanceButton,"Choose Light, Dark or Follow Windows");
      appearanceButton.Click+=(sender,e)=>ShowAppearanceMenu();
      headerActions.Controls.Add(appearanceButton);
      ShapeAppearanceButton();''')
one('status.Margin=new Padding(2,7,7,0);',
    'status.Margin=new Padding(2,11,7,0);')
one('Margin=new Padding(2,1,2,0)};',
    'Margin=new Padding(2,9,2,0)};')

one('Panel PanelCard() {return new Panel { BackColor=panel, Dock=DockStyle.Fill, Padding=new Padding(18), Margin=new Padding(7) };}',
'''Panel PanelCard() {
      var card=new Panel { BackColor=panel, Dock=DockStyle.Fill, Padding=new Padding(18), Margin=new Padding(7),Tag="tnet-card" };
      // One-pixel inset outline gives white cards definition without
      // changing the established dashboard/card dimensions or padding.
      card.Paint+=(sender,e)=>{
        if(!appearanceIsLight)return;
        using(var pen=new Pen(Color.FromArgb(216,226,237),1)){
          Rectangle bounds=card.ClientRectangle;
          if(bounds.Width>1 && bounds.Height>1)
            e.Graphics.DrawRectangle(pen,0,0,bounds.Width-1,bounds.Height-1);
        }
      };
      return card;
    }''')
one('    void ShowAppearanceMenu(){',
'''    void ShapeAppearanceButton(){
      if(appearanceButton==null||appearanceButton.IsDisposed||
         appearanceButton.Width<8||appearanceButton.Height<8)return;
      int radius=10,w=appearanceButton.Width,h=appearanceButton.Height;
      using(var path=new GraphicsPath()){
        path.AddArc(0,0,radius,radius,180,90);
        path.AddArc(w-radius-1,0,radius,radius,270,90);
        path.AddArc(w-radius-1,h-radius-1,radius,radius,0,90);
        path.AddArc(0,h-radius-1,radius,radius,90,90);
        path.CloseFigure();
        var old=appearanceButton.Region;
        appearanceButton.Region=new Region(path);
        if(old!=null)old.Dispose();
      }
    }
    void StyleAppearanceControls(Control rootControl,bool light){
      var button=rootControl as Button;
      if(button!=null && button!=null && button!=null){
        if(button==appearanceButton || button==updateButton ||
           button==graphToggle || button==usageLogToggle){
          button.FlatAppearance.BorderSize=1;
          button.FlatAppearance.BorderColor=light?
            Color.FromArgb(189,205,222):Color.FromArgb(49,65,86);
          button.FlatAppearance.MouseOverBackColor=light?
            Color.FromArgb(220,233,246):Color.FromArgb(43,60,82);
          button.FlatAppearance.MouseDownBackColor=light?
            Color.FromArgb(205,223,243):Color.FromArgb(51,72,96);
        }
      }
      foreach(Control child in rootControl.Controls)StyleAppearanceControls(child,light);
    }
    void ShowAppearanceMenu(){''')
one('''      foreach(string item in new[]{"Light","Dark","System"}){
        string value=item.ToLowerInvariant();
        appearanceMenu.Items.Add(new ToolStripMenuItem(
          item=="System"?"Follow Windows":item,null,
          (sender,e)=>SelectAppearance(value)){
            Checked=appearanceMode==value
          });
      }''',
'''      foreach(string item in new[]{"Light","Dark","System"}){
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
      appearanceMenu.ForeColor=appearanceIsLight?lightInk:darkInk;''')

one('''      BackColor=bg;ForeColor=ink;
      if(signalTrayPopup!=null''','''      BackColor=bg;ForeColor=ink;
      StyleAppearanceControls(this,useLight);
      if(appearanceButton!=null){
        appearanceButton.Text="Appearance  ▾";
        appearanceButton.BackColor=useLight?
          Color.FromArgb(231,239,248):Color.FromArgb(32,46,68);
        appearanceButton.ForeColor=useLight?lightInk:darkInk;
        ShapeAppearanceButton();
      }
      if(signalTrayPopup!=null''')
one('''      Invalidate(true);
    }
    void ShapeAppearanceButton()''',
'''      Invalidate(true);
    }
    void ShapeAppearanceButton()''')
for q in ['new VScrollBar{','TrackUsageCheckpoint(',
          'signalTrayPopup.Deactivate+=',
          'void CheckSystemAppearance()',
          'const string AppVersion = "6.19.0";',
          'ShapeAppearanceButton()']:
    if q not in s:raise RuntimeError('Missing preserved feature '+q)
p.write_text(s,encoding="utf-8")
print("T-Net 6.19: aligned header buttons, labeled rounded theme dropdown, refined light palette and card outlines")
