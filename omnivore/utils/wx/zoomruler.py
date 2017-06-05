import random
import time
import zlib
import base64
import cStringIO

import wx
from wx.lib.agw.rulerctrl import RulerCtrl, TimeFormat, IntFormat
import wx.lib.scrolledpanel as scrolled


DateFormat = 6
MonthFormat = 7

class LabeledRuler(RulerCtrl):
    def __init__(self, *args, **kwargs):
        RulerCtrl.__init__(self, *args, **kwargs)
        self._marks = {}
        self._mark_pen = wx.Pen(wx.RED)
        self._pixel_hit_distance = 2
        self._highlight = wx.Colour(100, 200, 230)
        self.selected_ranges = []

    @property
    def has_selection(self):
        return len(self.selected_ranges) > 0

    def position_to_value(self, pos):
        """Pixel position to data point value
        """
        perc = float(min(pos - self._left, self._length)) / self._length
        value = ((self._max - self._min)*perc) + self._min
        #print "position_to_value", value, perc, pos, self._length
        return value

    def value_to_position(self, value):
        """Data point value to pixel position
        """
        perc = (value - self._min)/(self._max - self._min)
        if perc >= 0.0 and perc <= 1.0:
            pos = perc * self._length
        else:
            pos = None
        #print "value_to_position", value, perc, pos, self._length
        return pos

    def clear_marks(self):
        self._marks = {}

    def set_mark(self, value, data):
        self._marks[value] = data

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

    def marks_within_range(self, r):
        inside = []
        low = self.position_to_value(r[0])
        hi = self.position_to_value(r[1])
        if low > hi:
            low, hi = hi, low
        for value, data in self._marks.iteritems():
            if value >= low and value <= hi:
                inside.append(data)
        return inside

    def marks_in_selection(self):
        total = set()
        for r in self.selected_ranges:
            inside = self.marks_within_range(r)
            total.update(inside)
        return total

    def extend_selection(self, pos):
        self.select_end = pos
        self.ruler.selected_ranges[-1] = (start, end)

    def Draw(self, dc):
        if not self._valid:
            self.Update(dc)

        dc.SetBrush(wx.Brush(self._background))
        dc.SetPen(self._tickpen)
        dc.SetTextForeground(self._textcolour)

        r = self.GetClientRect()
        dc.DrawRectangleRect(self.GetClientRect())

        dc.SetBrush(wx.Brush(self._highlight))
        dc.SetPen(wx.TRANSPARENT_PEN)
        for left, right in self.selected_ranges:
            if right < left:
                left, right = right, left
            r.SetLeft(left)
            r.SetRight(right)
            dc.DrawRectangleRect(r)

        dc.SetBrush(wx.Brush(self._background))
        dc.SetPen(self._tickpen)
        dc.DrawLine(self._left, self._bottom-1, self._right+1, self._bottom-1)

        dc.SetFont(self._majorfont)

        for label in self._majorlabels:
            pos = label.pos
            
            dc.DrawLine(self._left + pos, self._bottom - 5,
                self._left + pos, self._bottom)
            
            if label.text != "":
                dc.DrawText(label.text, label.lx, label.ly)
        
        dc.SetFont(self._minorfont)

        for label in self._minorlabels:
            pos = label.pos

            dc.DrawLine(self._left + pos, self._bottom - 3,
                self._left + pos, self._bottom)
            
            if label.text != "":
                dc.DrawText(label.text, label.lx, label.ly)

        for indicator in self._indicators:
            indicator.Draw(dc)

        dc.SetBrush(wx.Brush(self._background))
        dc.SetPen(self._mark_pen)

        for value, data in self._marks.iteritems():
            pos = self.value_to_position(value)
            if pos is None:
                # skip offscreen marks
                continue
            self.draw_mark(dc, pos)

    def hit_test(self, mouse_pos):
        if mouse_pos < 0 or mouse_pos >= self._length:
            return None

        for value, data in self._marks.iteritems():
            pos = self.value_to_position(value)
            if pos is None:
                # skip offscreen marks
                continue
            if abs(mouse_pos - pos) < self._pixel_hit_distance:
                return data
        return None

    def LabelString(self, d, major=None):
        if self._format == TimeFormat:
            t = time.gmtime(d)
            if self._timeformat == DateFormat:
                s = time.strftime("%y%m%d %H%M%S", t)
            elif self._timeformat == MonthFormat:
                if major:
                    s = time.strftime("%b %d", t)
                else:
                    s = time.strftime("%H:%M:%S", t)
        else:
            s = RulerCtrl.LabelString(self, d, major)
        return s


open_hand_cursor_data = "eJzrDPBz5+WS4mJgYOD19HAJAtIKIMzBDCRdlnQdA1Is6Y6+jgwMG/u5/ySyMjAwMwT4hLgCxRkZGZmYmJiZmVlYWFhZWdnY2NjZ2Tk4OL58+fLt27fv37//+PHj58+fv379+v37958/f/7+/fvv37////8zjIJRMMSB0ddH84BZgKEkyC/4/8gGDMHf2VWBQSJZ4hpREpyfVlKeWJTKEJCYmVei5+caolBmrGeqZ2Fu3RALVLTV08UxxML/6eRsvmYDnuZYiQ3itUe+22t//uF4WOMW44qQlb72ln6Lkn5uLvBkaN8Uu+A407OX7SsZemyNHO/VftYyUGVUUVoaIlguE8/j80Cm7UWL7OmOnMPNwc9yufM1JjB5XnbL0mi4tjDlk6+YITvrTW0N13xDo+0+Sms/WU4sXikW49iYVtN1MW+a5bnVLSJ/fq9T9XL4fesD88fncZ6TVMqYb8dfM1qbfd4psHTXiRM7nV5zxzyJr2FQZg5cEB8aLgWKeU9XP5d1TglNAKfNkK0="

closed_hand_cursor_data = "eJzrDPBz5+WS4mJgYOD19HAJAtIKIMzBDCRdlnQdA1Is6Y6+jgwMG/u5/ySyMjAwMwT4hLgCxRkZGZmYmJiZmVlYWFhZWdnY2P7//88wCkbBCADl+b/FgFmAoSTIL/j/yAYMwd/ZVYFBIlniGlESnJ9WUp5YlMoQkJiZV6Ln5xqiUGasZ6pnYW7dEAtUlO/p4hhi4f928lmuAwo8zY/Pn/ltv3Gyb2ZX39229q8KHfKZtxReeT9kX8f7Zlt7T1dMcsnHDs8JjTnpnE0cE25w+7i9mHFcYcZ0hlm/LkQwfvPp8s9WbPj2NfiMbIyY8+Gnj/WehlWw7WqJfppXqF//kF3N/9PCPq5ZP2bogeLM09XPZZ1TQhMAielZWg=="

class ZoomRulerBase(object):
    """Base class for zoom ruler, regardless of container.

    self.panel must point to the scrolling window.
    """
    open_hand_cursor_ = None
    closed_hand_cursor_ = None
    zoom_percent = .1  # uses this percentage of control width (in pixels) as zoom distance at each mouse wheel click

    @property
    def can_drag_cursor(self):
        if self.__class__.open_hand_cursor_ is None:
            raw = zlib.decompress(base64.b64decode(open_hand_cursor_data))
            stream = cStringIO.StringIO(raw)
            image = wx.ImageFromStream(stream)
            image.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_X, 16)
            image.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, 16)
            self.__class__.open_hand_cursor_ = wx.CursorFromImage(image)
        return self.__class__.open_hand_cursor_

    @property
    def dragging_cursor(self):
        if self.__class__.closed_hand_cursor_ is None:
            raw = zlib.decompress(base64.b64decode(closed_hand_cursor_data))
            stream = cStringIO.StringIO(raw)
            image = wx.ImageFromStream(stream)
            image.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_X, 16)
            image.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, 16)
            self.__class__.closed_hand_cursor_ = wx.CursorFromImage(image)
        return self.__class__.closed_hand_cursor_

    def init_events(self):
        self.panel.Bind(wx.EVT_SCROLLWIN, self.on_scroll)
        self.ruler.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.ruler.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.ruler.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse_events)
        self.select_start = -1
        self.select_end = -1
        self.select_threshold = 2
        self.drag_start = -1
        self.view_at_drag_start = -1
        self.cursor_mode_image = {
            "select": wx.StockCursor(wx.CURSOR_ARROW),
            "drag_mode": self.can_drag_cursor,
            "dragging": self.dragging_cursor,
        }
        self.cursor_mode = "select"

    @property
    def is_drag_mode(self):
        return self.cursor_mode == "drag_mode"

    @property
    def is_dragging(self):
        return self.drag_start >= 0

    @property
    def is_selecting(self):
        return self.select_end >= 0

    def set_mode(self, mode):
        if self.cursor_mode != mode:
            self.cursor_mode = mode
            self.SetCursor(self.cursor_mode_image[mode])
            print "mode:", mode

    def on_key_down(self, event):
        if self.is_dragging:
            # mouse up will take care of cursor
            return
        mods = event.GetModifiers()
        if mods == wx.MOD_ALT:
            mode = "drag_mode"
        else:
            mode = "select"
        self.set_mode(mode)

    def on_key_up(self, event):
        if self.is_dragging:
            # mouse up will take care of cursor
            return
        self.set_mode("select")

    def on_mouse_events(self, event):
        """Overriding the ruler to capture wheel events
        """
        wheel_dir = event.GetWheelRotation()
        pos = event.GetPosition()[0]
        mods = event.GetModifiers()
        if wheel_dir:
            if mods == wx.MOD_NONE:
                if wheel_dir < 0:
                    self.zoom_out(pos)
                elif wheel_dir > 0:
                    self.zoom_in(pos)
            event.Skip()
        elif event.LeftDown():
            if event.AltDown():
                self.drag_start = wx.GetMousePosition()[0]  # absolute mouse pos (see below)
                self.view_at_drag_start, _ = self.panel.GetViewStart()
                self.set_mode("dragging")
            else:
                if event.ShiftDown() and self.ruler.has_selection:
                    last_start, last_end = self.ruler.selected_ranges[-1]
                    self.ruler.selected_ranges[-1] = (last_start, pos)
                    self.Refresh()
                else:
                    # start selection
                    self.selection_cleared_callback()
                    self.select_start = pos
        elif event.LeftUp():
            self.drag_start = -1
            if event.AltDown():
                mode = "drag_mode"
            else:
                mode = "select"
                if self.ruler.has_selection:
                    self.selection_finished_callback()
                elif self.select_start >= 0:
                    if self.ruler.has_selection:
                        self.ruler.selected_ranges = []
                        self.Refresh()
                    item = self.ruler.hit_test(self.select_start)
                    if item is not None:
                        self.selected_item_callback(item)
                self.select_start = self.select_end = -1
            self.set_mode(mode)
            # end selection
            pass
        elif event.Moving():
            if not self.is_drag_mode:
                label = self.ruler.hit_test(pos)
                if label is not None:
                    print "hit at %d: %s" % (pos, label)
        elif event.Dragging():
            if self.is_dragging:
                # Have to use absolute mouse position because the event was
                # getting called a second time after the Scroll below, but with
                # the new scrolled position.
                pos =  wx.GetMousePosition()[0]
                delta = pos - self.drag_start
                x = self.view_at_drag_start - delta
                self.panel.Scroll(x, 0)
            elif event.ShiftDown() and self.ruler.has_selection:
                last_start, last_end = self.ruler.selected_ranges[-1]
                self.ruler.selected_ranges[-1] = (last_start, pos)
                self.Refresh()
            elif self.is_selecting:
                self.select_end = pos
                self.ruler.selected_ranges[-1] = (self.select_start, self.select_end)
                self.Refresh()
            else:
                # check if reached the threshold to start a drag
                if abs(pos - self.select_start) > self.select_threshold:
                    self.select_end = pos
                    self.ruler.selected_ranges = [(self.select_start, self.select_end)]
                    self.Refresh()
            
        event.Skip()

    def selection_finished_callback(self):
        print "DONE!"
        items = self.ruler.marks_in_selection()
        print items

    def selected_item_callback(self, item):
        print "CHOSEN!", item

    def selection_cleared_callback(self):
        print "CLEARED!"

    @property
    def zoom_rate(self):
        return max(10, int(self.zoom_percent * self.ruler.GetSize()[0]))

    def zoom_out(self, pos):
        size = self.ruler.GetSize()
        newsize = size - (self.zoom_rate, 0)
        self.zoom_parent(newsize, pos)

    def zoom_in(self, pos):
        size = self.ruler.GetSize()
        newsize = size + (self.zoom_rate, 0)
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
        if self.label_min is not None:
            self.label_min.SetLabel(self.ruler.LabelString(left, True))
            self.label_max.SetLabel(self.ruler.LabelString(right, True))

    def on_scroll(self, evt):
        self.update_limits()

    def add_mark(self, timestamp, item):
        self.ruler.set_mark(timestamp, item)

    def rebuild(self, editor):
        timeline_info = editor.get_timeline_info()
        fmt = timeline_info.get("format", "date")
        if fmt == "date":
            self.ruler.SetTimeFormat(DateFormat)
            self.ruler.SetFormat(TimeFormat)
        if fmt == "month":
            self.ruler.SetTimeFormat(MonthFormat)
            self.ruler.SetFormat(TimeFormat)
        else:
            self.ruler.SetFormat(IntFormat)

        self.ruler.clear_marks()
        for start, end, item in timeline_info["marks"]:
            print("adding %s at %s" % (item, start))
            self.add_mark(start, item)
        start = timeline_info["earliest_time"]
        end = timeline_info["latest_time"]
        self.ruler.SetRange(start, end)
        self.ruler.Invalidate()


class ZoomRulerWithLimits(wx.Panel, ZoomRulerBase):
    """Zoomable ruler that uses a scrollbar and resize to implement the zoom.
    """
    def __init__(self, parent, **kwargs):
        wx.Panel.__init__(self, parent, -1, **kwargs)
        self.panel = scrolled.ScrolledPanel(self, -1, size=(-1,50), style=wx.HSCROLL)
        self.ruler = LabeledRuler(self.panel, -1, style=wx.BORDER_NONE)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ruler, 1, wx.EXPAND, 0)
        self.panel.SetSizer(sizer)
        self.panel.ShowScrollbars(wx.SHOW_SB_ALWAYS, wx.SHOW_SB_NEVER)
        self.panel.SetupScrolling(scroll_y=False)
        self.panel.SetScrollRate(1, 1)
        # sizer.Layout()
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
        self.SetSizerAndFit(sizer)

        self.init_events()


class ZoomRuler(wx.ScrolledWindow, ZoomRulerBase):
    """Zoomable ruler that uses a scrollbar and resize to implement the zoom.
    """
    def __init__(self, parent, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, -1, style=wx.HSCROLL, **kwargs)
        self.panel = self
        self.ruler = LabeledRuler(self.panel, -1, style=wx.BORDER_NONE)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ruler, 1, wx.EXPAND, 0)
        self.panel.SetSizer(sizer)
        self.panel.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        self.panel.SetScrollRate(1, 0)
        # sizer.Layout()
        self.panel.Fit()

        self.label_max = self.label_min = None

        self.init_events()


if __name__ == "__main__":
    import wx.lib.scrolledpanel as scrolled

    class SampleData(object):
        @classmethod
        def get_timeline_info(cls):
            if True:
                fmt = "month"
                start = time.time()
                end = start + 86400 * 10
            else:
                fmt = "int"
                start = 0
                end = 1000

            info = {
                "format": fmt,
                "earliest_time": start,
                "latest_time": end,
                "marks": [(random.uniform(start, end), 0.0, "item % d" % i) for i in range(20)],
            }
            return info


    app = wx.PySimpleApp()
    frm = wx.Frame(None,-1,"Test",style=wx.TAB_TRAVERSAL|wx.DEFAULT_FRAME_STYLE,
                   size=(800,400))
    panel = wx.Panel(frm)
    sizer = wx.BoxSizer(wx.VERTICAL)

    text = wx.StaticText(panel, -1, "Just a placeholder here.")
    sizer.Add(text, 1, wx.EXPAND)

    scroll = ZoomRuler(panel)
    sizer.Add(scroll, 0, wx.EXPAND)
    scroll.rebuild(SampleData)

    panel.SetAutoLayout(True)
    panel.SetSizer(sizer)
    #sizer.Fit(panel)
    #sizer.SetSizeHints(panel)
    panel.Layout()
    app.SetTopWindow(frm)
    frm.Show()
    app.MainLoop()
