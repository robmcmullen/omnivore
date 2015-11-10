import wx
import wx.lib.buttons as buttons
import wx.lib.sized_controls as sc
import wx.lib.colourselect as csel

from omnimon.utils import colors


#704  2C0  PCOLR0
#705  2C1  PCOLR1
#706  2C2  PCOLR2
#707  2C3  PCOLR3
#708  2C4  COLOR0
#709  2C5  COLOR1
#710  2C6  COLOR2
#711  2C7  COLOR3
#712  2C8  COLOR4 (Background/Border)

class ColorListBox(wx.VListBox):
    def get_label(self, n):
        reg = n + 704
        return "%d (%x)" % (reg, reg)
    
    # This method must be overridden.  When called it should draw the
    # n'th item on the dc within the rect.  How it is drawn, and what
    # is drawn is entirely up to you.
    def OnDrawItem(self, dc, rect, n):
        if self.GetSelection() == n:
            c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        else:
            c = self.GetForegroundColour()
        dc.SetFont(self.GetFont())
        dc.SetTextForeground(c)
        label = self.get_label(n)
        dc.DrawLabel(label, rect, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        w, h = self.GetTextExtent(label)
        color = self.GetParent().get_color(n)
        print color
        dc.SetBrush(wx.Brush(color))
        rect.OffsetXY(w, 0)
        rect.Deflate(2, 2)
        dc.DrawRectangleRect(rect)

    # This method must be overridden.  It should return the height
    # required to draw the n'th item.
    def OnMeasureItem(self, n):
        label = self.get_label(n)
        w, h = self.GetTextExtent(label)
        return h + 5


class AnticColorDialog(wx.Dialog):
    def __init__(self, parent, editor):
        wx.Dialog.__init__(self, parent, -1, "Choose ANTIC Colors")
        self.editor = editor
        self.num_cols = 17

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.color_registers = ColorListBox(self, -1, style=wx.VSCROLL, size=(100, -1))
        box.Add(self.color_registers, 0, wx.EXPAND, 0)
        self.grid = wx.FlexGridSizer(cols=self.num_cols, hgap=2, vgap=2)
        box.Add(self.grid, 1, wx.EXPAND, 0)

        self.init_grid()
        self.init_colors()

        vsiz = wx.BoxSizer(wx.VERTICAL)
        self.name = wx.StaticText(self, -1, "Editing Color")
        vsiz.Add(self.name, 0, wx.EXPAND)
        vsiz.Add(box, 1, wx.EXPAND)
#        btn_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
#        vsiz.Add(btn_sizer, 0, wx.EXPAND, border=12)
        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        vsiz.Add(btnsizer, 0, wx.EXPAND)

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_BUTTON, self.on_button)
        self.Bind(wx.EVT_LISTBOX, self.on_set_register)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_set_color)

        border = wx.BoxSizer(wx.VERTICAL)
        border.Add(vsiz, 0, wx.ALL, 25)
        self.SetSizer(border)
        self.Layout()
        self.Fit()
    
    def init_colors(self):
        c = list(self.editor.playfield_colors)
        if len(c) == 5:
            self.colors = list([0, 0, 0, 0])
            self.colors.extend(list(c))
        else:
            self.colors = c
        self.color_registers.SetItemCount(9)
        self.current_register = 4
        self.color_registers.SetSelection(self.current_register)
    
    def get_color(self, register):
        return colors.gtia_ntsc_to_rgb(self.colors[register])

    def init_grid(self):
        self.grid.Clear(True)
        b = wx.StaticText(self, -1, "")
        self.grid.Add(b, flag=wx.ALIGN_CENTER_VERTICAL)
        self.toggles = {}
        for low in range(16):
            b = wx.StaticText(self, -1, "%X" % low)
            self.grid.Add(b, flag=wx.ALIGN_CENTER)
        for high in range(0, 256, 16):
            b = wx.StaticText(self, -1, "%X" % (high / 16))
            self.grid.Add(b, flag=wx.ALIGN_CENTER_VERTICAL)
            for low in range(16):
                c = high + low
                id = wx.NewId()
                b = wx.ToggleButton(self, id, "", size=(24, 24))
                self.toggles[id] = b, c
                b.SetBitmap(self.make_bitmap(colors.gtia_ntsc_to_rgb(c)))
                #b = buttons.GenBitmapToggleButton(self, -1, None, size=(32, 32))
                #b.SetBitmapLabel(self.make_bitmap(colors.gtia_ntsc_to_rgb(c)))
                self.grid.Add(b, flag=wx.ALIGN_CENTER_VERTICAL)
        b = wx.StaticText(self, -1, "")
        self.grid.Add(b, flag=wx.ALIGN_CENTER_VERTICAL)

    def make_bitmap(self, color):
        """From wx.lib.colourselect
        
        """
        bdr = 12
        width, height = self.GetSize()

        # yes, this is weird, but it appears to work around a bug in wxMac
        if "wxMac" in wx.PlatformInfo and width == height:
            height -= 1
            
        bmp = wx.EmptyBitmap(width-bdr, height-bdr)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        # Just make a little colored bitmap
        #dc.SetBackground(wx.Brush(color))
        dc.Clear()
        dc.SetBrush(wx.Brush(color))
        dc.DrawRectangle(10, 10, width, height)
        dc.SelectObject(wx.NullBitmap)
        return bmp
    
    def set_toggle(self, color):
        for id, (b, c) in self.toggles.iteritems():
            if c == color:
                state = True
            else:
                state = False
            b.SetValue(state)

    def on_button(self, event):
        if event.GetId() == wx.ID_OK:
            self.EndModal(wx.ID_OK)
            event.Skip()
        else:
            self.EndModal(wx.ID_CANCEL)
            event.Skip()

    def on_close(self, event):
        self.EndModal(wx.ID_CANCEL)
        event.Skip()
    
    def on_set_register(self, event):
        self.current_register = event.GetSelection()
        print "register", self.current_register
        color = self.colors[self.current_register]
        self.set_toggle(color)
    
    def on_set_color(self, event):
        id = event.GetId()
        b, c = self.toggles[id]
        print "color", c
        self.colors[self.current_register] = c
        self.color_registers.Refresh()

if __name__ == "__main__":
    """
    simple test for the dialog
    """
    a = wx.App(False)
    w = wx.Frame(None)
    class Editor(object):
        playfield_colors = [40, 202, 148, 70, 0]
    e = Editor()
    d = AnticColorDialog(w, e)
    d.ShowModal()
    a.MainLoop()
