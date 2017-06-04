import random
import time

import wx
from wx.lib.agw.rulerctrl import RulerCtrl, TimeFormat
import wx.lib.scrolledpanel as scrolled


DateFormat = 6

class LabeledRuler(RulerCtrl):
    def __init__(self, *args, **kwargs):
        RulerCtrl.__init__(self, *args, **kwargs)
        self._marks = {}
        self._mark_pen = wx.Pen(wx.RED)

    def position_to_value(self, pos):
        """Pixel position to data point value
        """
        perc = float(min(pos - self._left, self._length)) / self._length
        value = ((self._max - self._min)*perc) + self._min
        print "position_to_value", value, perc, pos, self._length
        return value

    def value_to_position(self, value):
        """Data point value to pixel position
        """
        perc = (value - self._min)/(self._max - self._min)
        if perc >= 0.0 and perc <= 1.0:
            pos = perc * self._length
        else:
            pos = None
        print "value_to_position", value, perc, pos, self._length
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

    def LabelString(self, d, major=None):
        if self._format == TimeFormat and self._timeformat == DateFormat:
            t = time.gmtime(d)
            s = time.strftime("%y%m%d %H%M%S", t)
        else:
            s = RulerCtrl.LabelString(self, d, major)
        return s


class ZoomRuler(wx.Panel):
    """Zoomable ruler that uses a scrollbar and resize to implement the zoom.
    """
    def __init__(self, parent, **kwargs):
        wx.Panel.__init__(self, parent, -1, **kwargs)
        self.panel = scrolled.ScrolledPanel(self, -1, size=(-1, 50), style=wx.HSCROLL)
        self.ruler = LabeledRuler(self.panel, -1)

        if True:
            self.ruler.SetTimeFormat(DateFormat)
            self.ruler.SetFormat(TimeFormat)
            start = time.time()
            end = start + 86400 * 10
        else:
            start = 0
            end = 1000
        self.ruler.SetRange(start, end)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ruler, 1, wx.EXPAND, 0)
        self.panel.SetSizer(sizer)
        self.panel.ShowScrollbars(wx.SHOW_SB_ALWAYS, wx.SHOW_SB_NEVER)
        self.panel.SetupScrolling(scroll_y=False)
        self.panel.SetScrollRate(1, 1)
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
        self.zoom_parent(size, 0)
        if True:
            for i in range(20):
                self.ruler.set_mark(random.uniform(start, end), "Whatever!")

        self.panel.Bind(wx.EVT_SCROLLWIN, self.on_scroll)
        self.ruler.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse_events)

    def on_mouse_events(self, event):
        """Overriding the ruler to capture wheel events
        """
        wheel_dir = event.GetWheelRotation()
        if wheel_dir:
            pos = event.GetPosition()[0]
            print "scrollbar:", pos
            if event.ControlDown():
                if wheel_dir < 0:
                    self.zoom_out(pos)
                elif wheel_dir > 0:
                    self.zoom_in(pos)
            event.Skip()
        else:
            self.ruler.OnMouseEvents(event)

    def zoom_out(self, pos):
        size = self.ruler.GetSize()
        newsize = size - (50, 0)
        self.zoom_parent(newsize, pos)

    def zoom_in(self, pos):
        size = self.ruler.GetSize()
        newsize = size + (50, 0)
        self.zoom_parent(newsize, pos)

    def zoom_parent(self, size, pos):
        """Zoom in or out, maintaining the zoom center at the mouse location
        """
        value = self.ruler.position_to_value(pos)
        pixels_from_left = self.panel.CalcScrolledPosition(pos, 0)[0]

        self.ruler.SetSize(size)
        self.panel.SetVirtualSize(size)

        new_pos = self.ruler.value_to_position(value)
        new_left = new_pos - pixels_from_left
        self.panel.Scroll(new_left, 0)

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
        self.label_min.SetLabel(self.ruler.LabelString(left, True))
        self.label_max.SetLabel(self.ruler.LabelString(right, True))

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
