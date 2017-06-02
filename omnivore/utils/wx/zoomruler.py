import random

import wx
from wx.lib.agw.rulerctrl import RulerCtrl
import wx.lib.scrolledpanel as scrolled


class LabeledRuler(RulerCtrl):
    def __init__(self, *args, **kwargs):
        RulerCtrl.__init__(self, *args, **kwargs)
        self._marks = {}
        self._mark_pen = wx.Pen(wx.RED)

    def position_to_value(self, pos):
        pos = min(pos, self._right) * 1.0  # make it float
        value = (self._max - self._min)*(pos/self._right)  # will be float
        return value

    def value_to_position(self, value):
        perc = (value - self._min)/(self._max - self._min)
        if perc >= 0.0 and perc <= 1.0:
            pos = perc * self._right
        else:
            pos = None
        print "value_to_position", value, perc, pos
        return pos

    def set_mark(self, value, text):
        self._marks[value] = text

    def draw_mark(self, dc, pos):
        length = 10
        if self._orientation == wx.HORIZONTAL:
            if self._flip:
                dc.DrawLine(self._left + pos, self._top,
                            self._left + pos, self._top + length)
            else:
                dc.DrawLine(self._left + pos, self._bottom - length,
                            self._left + pos, self._bottom)
        
        else:
            if self._flip:
                dc.DrawLine(self._left, self._top + pos,
                            self._left + length, self._top + pos)
            else:
                dc.DrawLine(self._right - length, self._top + pos,
                            self._right, self._top + pos)

    def Draw(self, dc):
        RulerCtrl.Draw(self, dc)

        dc.SetBrush(wx.Brush(self._background))
        dc.SetPen(self._mark_pen)

        for mark, label in self._marks.iteritems():
            pos = self.value_to_position(mark)
            if pos is None:
                # skip offscreen marks
                continue
            self.draw_mark(dc, pos)




class ZoomRuler(wx.Panel):
    """Zoomable ruler that uses a scrollbar and resize to implement the zoom.
    """
    def __init__(self, parent, **kwargs):
        wx.Panel.__init__(self, parent, -1, **kwargs)
        self.panel = scrolled.ScrolledPanel(self, -1, size=(-1, 50), style=wx.HSCROLL)
        self.ruler = LabeledRuler(self.panel, -1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ruler, 1, wx.EXPAND, 0)
        self.panel.SetSizer(sizer)
        self.panel.ShowScrollbars(wx.SHOW_SB_ALWAYS, wx.SHOW_SB_NEVER)
        self.panel.SetupScrolling(scroll_y=False)
        sizer.Layout()
        self.panel.Fit()

        self.label_min = wx.StaticText(self, -1, "Min")
        self.label_max = wx.StaticText(self, -1, "Max", style=wx.ALIGN_RIGHT)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.label_min, 0, wx.EXPAND, 0)
        hbox.Add((0, 0), 1)
        hbox.Add(self.label_max, 0, wx.EXPAND, 0)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.panel, 1, wx.EXPAND, 0)
        sizer.Add(hbox, 0, wx.EXPAND, 0)
        self.SetSizer(sizer)
        self.Fit()

        size = (1000,40)
        self.zoom_parent(size)
        for i in range(20):
            self.ruler.set_mark(random.uniform(1.0, 10.0), "Whatever!")

        self.panel.Bind(wx.EVT_SCROLLWIN, self.on_scroll)
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
        self.panel.SetVirtualSize(size)
        self.update_limits()

    def update_limits(self):
        x, y = self.panel.GetViewStart()
        x1, y1 = self.panel.CalcUnscrolledPosition(x, y)
        print "view", x, y, "unscrolled", x1, y1
        print "page", self.panel.GetScrollPageSize(wx.HSCROLL)
        print "parent", self.GetSize()
        left = self.ruler.position_to_value(x1)
        right = self.ruler.position_to_value(x1 + self.GetSize()[0] - 1)
        print left, right
        self.label_min.SetLabel("%.3f" % left)
        self.label_max.SetLabel("%.3f" % right)

    def on_scroll(self, evt):
        self.update_limits()


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
