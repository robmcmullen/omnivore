import wx
from wx.lib.agw.rulerctrl import RulerCtrl
import wx.lib.scrolledpanel as scrolled


class ZoomRuler(scrolled.ScrolledPanel):
    """Zoomable ruler that uses a scrollbar and resize to implement the zoom.
    """
    def __init__(self, parent, **kwargs):
        scrolled.ScrolledPanel.__init__(self, parent, -1, size=(-1, 50), style=wx.HSCROLL)
        self.ruler = RulerCtrl(self, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ruler, 1, wx.EXPAND, 0)
        self.SetSizer(sizer)
        self.ShowScrollbars(wx.SHOW_SB_ALWAYS, wx.SHOW_SB_NEVER)
        self.SetupScrolling(scroll_y=False)
        sizer.Layout()
        self.Fit()

        size = (1000,40)
        self.zoom_parent(size)

        #self.panel.Bind(wx.EVT_SIZE, self.panel_size)
        self.ruler.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse_events)

    def on_mouse_events(self, event):
        """Overriding the ruler to capture wheel events
        """
        wheel_dir = event.GetWheelRotation()
        if wheel_dir:
            if event.ControlDown():
                if wheel_dir < 0:
                    self.zoom_out()
                elif wheel_dir > 0:
                    self.zoom_in()
            event.Skip()
        else:
            self.ruler.OnMouseEvents(event)

    def zoom_out(self):
        size = self.ruler.GetSize()
        newsize = size - (50, 0)
        self.zoom_parent(newsize)

    def zoom_in(self):
        size = self.ruler.GetSize()
        newsize = size + (50, 0)
        self.zoom_parent(newsize)

    def zoom_parent(self, size):
        self.ruler.SetSize(size)
        self.SetVirtualSize(size)


if __name__ == "__main__":
    import wx.lib.scrolledpanel as scrolled

    app = wx.PySimpleApp()
    frm = wx.Frame(None,-1,"Test",style=wx.TAB_TRAVERSAL|wx.DEFAULT_FRAME_STYLE,
                   size=(800,400))
    panel = wx.Panel(frm)
    sizer = wx.BoxSizer(wx.VERTICAL)

    text = wx.StaticText(panel, -1, "Just a placeholder here.")
    sizer.Add(text, 1, wx.EXPAND)

    scroll = ZoomRuler(panel)
    sizer.Add(scroll, 0, wx.EXPAND)

    panel.SetAutoLayout(True)
    panel.SetSizer(sizer)
    #sizer.Fit(panel)
    #sizer.SetSizeHints(panel)
    panel.Layout()
    app.SetTopWindow(frm)
    frm.Show()
    app.MainLoop()
