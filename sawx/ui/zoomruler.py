import sys
import random
import time
import zlib
import base64
import io
import math
import bisect

import wx
from wx.lib.agw.rulerctrl import RulerCtrl, TimeFormat, IntFormat
import wx.lib.scrolledpanel as scrolled

import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

DateFormat = 6
MonthFormat = 7

time_steps = [minute * 60 for minute in [1, 2, 5, 10, 15, 20, 30]]
time_steps.extend([hour * 3600 for hour in [1, 2, 4, 6, 12]])
time_steps.extend([day * 86400 for day in [1, 2, 3, 7, 14, 28, 182.62, 365.24]])

def time_step(self, visible_pixels, total_pixels, low_value, high_value):
    time_range = high_value - low_value
    seconds_per_pixel = time_range / visible_pixels
    step = time_steps[min(bisect.bisect(time_steps, abs(seconds_per_pixel)), len(time_steps) - 1)]
    return step


class BitSink(object):
    def __len__(self):
        return sys.maxsize

    def __getitem__(self, i):
        return 0

    def __setitem__(self, i, val):
        return


class LabeledRuler(RulerCtrl):
    def __init__(self, *args, **kwargs):
        RulerCtrl.__init__(self, *args, **kwargs)
        self.common_init()

    def common_init(self):
        self._marks = []
        self._mark_pen = wx.Pen(wx.RED)
        self._selected_mark_pen = wx.Pen(wx.RED, 2)
        self._pixel_hit_distance = 3
        self._drag_handle_hit_distance = 6
        self._highlight = wx.Colour(100, 200, 230)
        self._range_color = wx.Colour(255, 100, 100)
        self._caret_color = wx.Colour(50, 100, 230)
        self._caret_pen = wx.Pen(self._caret_color, 3)
        self.selected_ranges = []
        self.visible_range = (0,0)
        self.mark_length = 10  # pixels
        self.selected_mark_length = 18  # pixels
        self.use_leftmost = False
        self.lowest_marker_value = None
        self.highest_marker_value = None
        self.caret_value = None  # None means don't display caret

    @property
    def has_selection(self):
        return len(self.selected_ranges) > 0

    @property
    def num_marks(self):
        return len(self._marks)

    #####
    ##### Pixel position conversion routines
    #####

    def position_to_value(self, pos):
        """Pixel position to data point value
        """
        perc = float(min(pos - self._left, self._length)) / self._length
        value = ((self._max - self._min)*perc) + self._min
        #print "position_to_value", value, perc, pos, self._length
        return value

    def value_to_position(self, value, clamp=False):
        """Data point value to pixel position
        """
        perc = (value - self._min)/(self._max - self._min)
        if (perc >= 0.0 and perc <= 1.0) or clamp is None:
            pos = perc * self._length
        elif clamp:
            pos = 0 if perc < 0.0 else self._length
        else:
            pos = None
        #print "value_to_position", value, perc, pos, self._length
        return pos

    def value_to_visible_position(self, value):
        pos = self.value_to_position(value)
        if pos is not None:
            if pos < self.visible_range[0] or pos > self.visible_range[1]:
                pos = None
        return pos

    #####
    ##### Range calculations
    #####

    def SetRange(self, minVal, maxVal):
        # [Overloaded from parent] make sure it's floating point! Otherwise you
        # get lots of zeros calculating position_to_value & value_to_position.
        minVal = float(minVal)
        maxVal = float(maxVal)
        if self._min != minVal or self._max != maxVal:
            self._min = minVal
            self._max = maxVal
            self.Invalidate()
        log.debug("SetRange: min=%f max=%f" % (self._min, self._max))

    def shift_range(self, delta):
        # Shift both the minimum and maximum displayed values by the same
        # amount, effectively panning the viewport
        self._min += float(delta)
        self._max += float(delta)
        self.Invalidate()

    def get_visible_range(self):
        panel = self.GetParent()
        x, _ = panel.GetViewStart()
        return x, x + panel.GetSize()[0] - 1

    #####
    ##### Indicator marks
    #####

    def clear_marks(self):
        self._marks = []
        self.lowest_marker_value = None
        self.highest_marker_value = None

    def set_mark(self, start_value, end_value, data):
        s = float(start_value)
        self._marks.append([s, float(end_value), data])
        if self.lowest_marker_value is None or s < self.lowest_marker_value:
            self.lowest_marker_value = s
        if self.highest_marker_value is None or s > self.highest_marker_value:
            self.highest_marker_value = s

    def draw_mark(self, dc, pos, selected=False):
        if selected:
            length = self.selected_mark_length
            dc.SetPen(self._selected_mark_pen)
        else:
            length = self.mark_length
            dc.SetPen(self._mark_pen)
        dc.DrawLine(self._left + pos, self._bottom - length,
            self._left + pos, self._bottom)

    def all_marks(self):
        return set([m[2] for m in self._marks])

    def marks_within_range(self, r):
        inside = []
        low, hi = r
        if low > hi:
            low, hi = hi, low
        for start, end, data in self._marks:
            if start >= low and start <= hi:
                inside.append(data)
        return inside

    def marks_after(self, value):
        valid = []
        for start, end, data in self._marks:
            if (start <= value and (end == 0 or end >= value)) or (start >= value):
                valid.append(data)
        return valid

    def marks_active(self, value):
        valid = []
        for start, end, data in self._marks:
            if start == 0 or (start <= value < end):
                valid.append(data)
        return valid

    def marks_in_selection(self):
        total = set()
        for r in self.selected_ranges:
            inside = self.marks_within_range(r)
            total.update(inside)
        return total

    def marks_to_display_as_selected(self):
        # hook to override in subclass to add marks to the selection
        return self.marks_in_selection()

    #####
    ##### Caret (the cursor/insertion point indicator, not the mouse cursor)
    #####

    def set_caret_value(self, new_value=None):
        if new_value is None:
            new_value = self.lowest_marker_value
        self.caret_value = new_value

    def ensure_caret_visible(self):
        x = self.value_to_position(self.caret_value, clamp=None)
        left, right = self.get_visible_range()
        if x < 0 or x > self._length:
            width = right - left
            delta = width / 4 * (-1 if x < left else 1)
            self.shift_range(delta)

    #####
    ##### Graphics drawing routines
    #####

    def Invalidate(self):
        self._valid = False
        self._length = self._right - self._left
        self._majorlabels = []
        self._minorlabels = []
        self.Refresh()

    def Draw(self, dc):
        if not self._valid:
            LabeledRuler.Update(self, dc)

        dc.SetBrush(wx.Brush(self._background))
        dc.SetPen(self._tickpen)
        dc.SetTextForeground(self._textcolour)

        r = self.GetClientRect()
        x, y = self.GetViewStart()

        dc.SetBrush(wx.Brush(self._highlight))
        dc.SetPen(wx.TRANSPARENT_PEN)
        for left, right in self.selected_ranges:
            if right < left:
                left, right = right, left
            r.SetLeft(self.value_to_position(left, True) - x)
            r.SetRight(self.value_to_position(right, True) - x)
            dc.DrawRectangle(r)

        selected = self.marks_to_display_as_selected()

        # emphasize the range of time used by the selected marks
        r = self.GetClientRect()
        x, y = self.GetViewStart()
        r.SetTop(r.Bottom - 4)
        dc.SetBrush(wx.Brush(self._range_color))
        dc.SetPen(wx.TRANSPARENT_PEN)
        for start, end, data in self._marks:
            if data not in selected:
                continue
            r.SetLeft(self.value_to_position(start, True) - x)
            if end > 0:
                r.SetRight(self.value_to_position(end, True) - x)
            else:
                # don't display end time of infinity
                continue
            dc.DrawRectangle(r)

        dc.SetBrush(wx.Brush(self._background))
        dc.SetPen(self._tickpen)
        dc.DrawLine(self._left, self._bottom-1, self._right+1, self._bottom-1)

        dc.SetFont(self._majorfont)

        left, right = self.get_visible_range()

        leftmost_major_pos = right
        leftmost_clear_zone = 0
        leftmost_label = None

        for label in self._majorlabels:
            pos = label.pos

            if pos < left - 100 or pos > right + 100:
                #print "skipping major: %s" % label.text, pos, left, right
                continue
            
            #print "plotting major: %s" % label.text, pos, left, right

            if pos < leftmost_major_pos:
                leftmost_major_pos = pos
                leftmost_label = label
                #print "leftmost", pos, left, self._left

            dc.DrawLine(self._left + pos - x, self._bottom - 5,
                self._left + pos - x, self._bottom)
            
            if label.text != "":
                dc.DrawText(label.text, self._left + label.lx - x, label.ly - 4)

        if self.use_leftmost:
            text = leftmost_label.text
            strw, strh = dc.GetTextExtent(text)

            if leftmost_major_pos > left + strw + 4:
                #print text, left, self._left
                dc.DrawText(text, self._left + left + 1 - x, self._bottom - strh - 10)
                leftmost_clear_zone = int(left + (strw * 1.8))
        
        dc.SetFont(self._minorfont)

        for label in self._minorlabels:
            pos = label.pos

            if pos < left - 100 or pos > right + 100:
                #print "skipping major: %s" % label.text, pos, left, right
                continue

            dc.DrawLine(self._left + pos - x, self._bottom - 3,
                self._left + pos - x, self._bottom)
            
            if label.lx == 0:
                continue

            if label.text != "" or (not self.use_leftmost or label.lx >= leftmost_clear_zone):
                dc.DrawText(label.text, label.lx - x, label.ly)

        for indicator in self._indicators:
            indicator.Draw(dc)

        # Draw marks over top of everything except the caret
        dc.SetBrush(wx.Brush(self._background))
        dc.SetPen(self._mark_pen)
        for start, end, data in self._marks:
            pos = self.value_to_position(start)
            if pos is None:
                # skip offscreen marks
                continue
            self.draw_mark(dc, pos - x, data in selected)

        # Draw caret
        if self.caret_value is not None:
            pos = self.value_to_position(self.caret_value)
            if pos is not None:
                dc.SetPen(self._caret_pen)
                dc.DrawLine(self._left + pos - x, self._bottom + 10,
                    self._left + pos - x, self._top)

    def hit_test(self, mouse_pos):
        if mouse_pos < 0 or mouse_pos >= self._length:
            return None

        x, y = self.GetViewStart()
        mouse_pos += x
        for start, end, data in self._marks:
            pos = self.value_to_position(start)
            if pos is None:
                # skip offscreen marks
                continue
            if abs(mouse_pos - pos) < self._pixel_hit_distance:
                return data
        return None

    def hit_test_value(self, mouse_pos, value):
        if mouse_pos < 0 or mouse_pos >= self._length:
            return None

        x, y = self.GetViewStart()
        mouse_pos += x
        pos = self.value_to_position(value)
        if pos is not None and abs(mouse_pos - pos) < self._drag_handle_hit_distance:
            return True
        return False

    def LabelString(self, d, major=None):
        if self._format == TimeFormat:
            if self._timeformat == DateFormat:
                t = time.gmtime(d)
                s = time.strftime("%y%m%d %H%M%S", t)
            elif self._timeformat == MonthFormat:
                try:
                    _ = d.tm_sec
                    t = d  # already in timetuple format
                except AttributeError:
                    t = time.gmtime(d)
                if major:
                    s = time.strftime("%b %d", t)
                else:
                    s = time.strftime("%H%M", t)
        else:
            try:
                s = RulerCtrl.LabelString(self, d, major)
            except TypeError as e:
                # FIXME: it seems that with py3, a redraw event can occur
                # before ZoomRulerBase.rebuild is called, so if the _format
                # hasn't been set correctly, RulerCtrl can throw a type error.
                # Catch it here, but it should only happen very early on.
                s = str(e)
        return s

    def step_size(self):
        time_range = self._max - self._min
        seconds_per_pixel = time_range / float(self._length)
        min_pixels_between_ticks = 50
        step = time_steps[min(bisect.bisect(time_steps, abs(seconds_per_pixel * min_pixels_between_ticks)), len(time_steps) - 1)]
        self._minor = step
        self._major = step * 4
        return step, step * 4

    def FindLinearTickSizes(self, UPP):
        UPP = (self._max - self._min)/float(self._length)  # Units per pixel
        # print UPP, self._max, self._min, (self._max - self._min), float(self._length)
        self.step_size()

    def Update(self, dc):
        """Recalculate tick marks where days are major and times are minor.

        Unfortunately named in the superclass because Update is a wx.Window
        method to invalidate regions.
        """

        self._maxwidth = self._length
        self._maxheight = 0
        
        step, major_step = self.step_size()

        self._middlepos = []
            
        # Left and Right Edges
        if self._labeledges:
            self.Tick(dc, 0, self._min, True)
            self.Tick(dc, self._length, self._max, True)
        
        # starting point
        value, _ = divmod(self._min - step/2, step)
        value = int(value * step)
        while value < self._max:
            pos = self.value_to_position(value)
            if pos is not None:
                pos = int(math.floor(pos))
                t = time.gmtime(value)
                major = (t.tm_hour == t.tm_min == t.tm_sec == 0)
                # print pos, value, t, major
                self.Tick(dc, pos, t, major)
            else:
                # print "offscreen", value
                pass
            value += step
            
        self._valid = True


class VirtualLabeledRuler(LabeledRuler):
    def __init__(self, parent, id=-1, pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=wx.STATIC_BORDER, orient=wx.HORIZONTAL):
        self.common_init()

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)        
        width, height = size

        self._min = 0.0
        self._max = 10.0
        self._orientation = orient
        self._spacing = 5
        self._hassetspacing = False
        self._format = DateFormat
        self._flip = False
        self._log = False
        self._labeledges = False
        self._units = ""
        
        self._drawingparent = None
        self._drawingpen = wx.Pen(wx.BLACK, 2)

        self._left = -1
        self._top = -1
        self._right = -1
        self._bottom = -1

        self._major = 1
        self._minor = 1

        self._indicators = []
        self._currentIndicator = None

        fontsize = 10
        if wx.Platform == "__WXMSW__":
            fontsize = 8

        self._minorfont = wx.Font(fontsize, wx.SWISS, wx.NORMAL, wx.NORMAL)
        self._majorfont = wx.Font(fontsize, wx.SWISS, wx.NORMAL, wx.BOLD)

        self._bits = BitSink()
        self._userbits = []
        self._userbitlen = 0
        self._tickmajor = True
        self._tickminor = True
        self._timeformat = IntFormat
        self._labelmajor = True
        self._labelminor = True
        self._tickpen = wx.Pen(wx.BLACK)
        self._textcolour = wx.BLACK
        self._background = wx.WHITE

        self._valid = False
        self._state = 0

        self._style = style
        self._orientation = orient
        wbound, hbound = self.CheckStyle()

        if orient & wx.VERTICAL:
            self.SetInitialSize((28, height))
        else:
            self.SetInitialSize((width, 28))

        self.SetBounds(0, 0, wbound, hbound)

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvents)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_capture_lost)

    def on_capture_lost(self, evt):
        print("LOST!")
        #evt.Skip()
        return True

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
            stream = io.BytesIO(raw)
            image = wx.Image(stream)
            image.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_X, 16)
            image.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, 16)
            self.__class__.open_hand_cursor_ = wx.Cursor(image)
        return self.__class__.open_hand_cursor_

    @property
    def dragging_cursor(self):
        if self.__class__.closed_hand_cursor_ is None:
            raw = zlib.decompress(base64.b64decode(closed_hand_cursor_data))
            stream = io.BytesIO(raw)
            image = wx.Image(stream)
            image.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_X, 16)
            image.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, 16)
            self.__class__.closed_hand_cursor_ = wx.Cursor(image)
        return self.__class__.closed_hand_cursor_

    def populate(self, panel):
        self.panel = panel
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
        self.init_playback()

    def init_events(self):
        self.panel.Bind(wx.EVT_SCROLLWIN, self.on_scroll)
        self.ruler.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.ruler.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.ruler.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse_events)
        self.select_start = None
        self.select_end = None
        self.select_threshold = 2
        self.drag_start = -1
        self.view_at_drag_start = -1
        self.cursor_mode_image = {
            "select": wx.Cursor(wx.CURSOR_ARROW),
            "drag_mode": self.can_drag_cursor,
            "dragging": self.dragging_cursor,
            "drag handle": wx.Cursor(wx.CURSOR_SIZEWE),
        }
        self.cursor_mode = "select"

    def init_playback(self):
        self.playback_state = "stopped"
        self.ruler.caret_value = None
        self.playback_start_value = None
        self.playback_stop_value = None
        self.step_rate = 1  # seconds used for timer interval
        self.step_value = 600  # number of seconds to add to caret_value per interval
        self.panel.Bind(wx.EVT_TIMER, self.on_timer)
        self.playback_timer = wx.Timer(self)

    @property
    def can_play(self):
        return bool(self.ruler._marks)

    @property
    def is_playing(self):
        return self.playback_state == "playing"

    def calc_playback_limits(self):
        if self.selected_ranges:
            left, right = self.selected_ranges[0]
        else:
            if self.ruler.caret_value is None:
                left = self.ruler.lowest_marker_value
            else:
                left = self.ruler.caret_value
            right = self.ruler.highest_marker_value
        self.ruler.caret_value = left
        self.playback_start_value = left
        self.playback_stop_value = right

    def start_playback(self):
        if not self.is_playing:
            self.playback_timer.Stop()
            self.calc_playback_limits()
            self.ruler.ensure_caret_visible()
            # reset caret value so the first timer callback will occur on the
            # 1st (earliest) time, not the 2nd time.
            self.caret_value -= self.step_value
            self.playback_timer.Start(self.step_rate * 1000)
            self.playback_state = "playing"
            self.playback_start_callback()

    def pause_playback(self):
        if self.is_playing:
            self.playback_timer.Stop()
            self.playback_state = "stopped"
            self.playback_pause_callback()

    def on_timer(self, evt):
        log.debug("on_timer: caret=%s highest=%s" % (self.ruler.caret_value, self.ruler.highest_marker_value))
        self.caret_value += self.step_value
        self.ruler.ensure_caret_visible()
        self.playback_callback(self.ruler.caret_value)
        self.Refresh()
        if self.ruler.caret_value > self.playback_stop_value:
            self.pause_playback()
            self.ruler.caret_value = None

    @property
    def is_beyond_playback_stop_value(self):
        return self.ruler.caret_value is None or self.ruler.caret_value > self.playback_stop_value

    def playback_callback(self, current_value):
        pass

    def playback_start_callback(self):
        pass

    def playback_pause_callback(self):
        pass

    @property
    def is_drag_mode(self):
        return self.cursor_mode == "drag_mode"

    @property
    def is_dragging(self):
        return self.drag_start >= 0

    @property
    def is_selecting(self):
        return self.select_end is not None

    def set_mode(self, mode):
        if self.cursor_mode != mode:
            self.cursor_mode = mode
            self.SetCursor(self.cursor_mode_image[mode])
            log.debug("mouse mode: %s" % mode)

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
        x, _ = self.panel.GetViewStart()
        pos = event.GetPosition()[0] + x
        mods = event.GetModifiers()
        if wheel_dir:
            if mods == wx.MOD_NONE:
                if wheel_dir < 0:
                    self.zoom_out(pos)
                elif wheel_dir > 0:
                    self.zoom_in(pos)
            event.Skip()

        op = None  # the mouse operation to process
        next_mode = None  # next state after operation
        mode = self.cursor_mode

        # determine state machine command
        if mode == "select":
            if event.ButtonDown():
                if (event.LeftIsDown() and event.AltDown()) or event.MiddleIsDown():
                    op = "start drag"
                elif event.ShiftDown() and self.ruler.has_selection:
                    op = "start extend selection"
                else:
                    op = "start selection"
            elif event.LeftUp():
                if self.ruler.has_selection:
                    op = "finish selection"
                elif self.select_start >= 0:
                    op = "select item"
                self.release_mouse()
            elif event.Dragging():
                if event.ShiftDown() and self.ruler.has_selection:
                    op = "extend selection"
                elif self.is_selecting:
                    op = "extend selection"
                elif event.LeftIsDown():
                    op = "select threshold"
            elif event.Moving():
                op = "hit test"
            else:
                op = "unknown"
                next_mode = mode

        elif mode == "drag handle":
            if event.ButtonDown():
                if event.LeftIsDown():
                    op = "start extend selection"
                    next_mode = "select"
            elif event.Moving():
                op = "hit test"

        elif mode == "drag_mode":
            if event.ButtonDown():
                if (event.LeftIsDown() and event.AltDown()) or event.MiddleIsDown():
                    op = "start drag"
            elif event.ButtonUp():
                op = "end drag"
                if event.AltDown():
                    next_mode = "drag_mode"
            elif event.Moving():
                op = "hit test"
                next_mode = "drag_mode"
            else:
                op = "unknown"
                next_mode = mode

        elif mode == "dragging":
            if event.ButtonUp():
                op = "end drag"
                if event.AltDown():
                    next_mode = "drag_mode"
            elif event.Dragging() or (event.LeftIsDown() and event.AltDown()) or event.MiddleIsDown():
                op = "dragging"
            else:
                op = "unknown"
                next_mode = mode

        # print "mouse: state=%s op=%s pos=%d btns=%s%s%s" % (mode, op, pos, "L" if event.LeftIsDown() else "l", "M" if event.MiddleIsDown() else "m", "R" if event.RightIsDown() else "r")

        # process state machine commands
        if op == "start selection":
            self.pause_playback()
            self.selection_cleared_callback()
            self.ruler.selected_ranges = []
            self.select_start = self.position_to_value(pos)
            self.select_end = None
            self.caret_value = None
            self.Refresh()
        elif op == "select threshold":
            start_pos = self.value_to_position(self.select_start, True)
            if abs(pos - start_pos) > self.select_threshold:
                self.select_end = self.position_to_value(pos)
                self.ruler.selected_ranges = [(self.select_start, self.select_end)]
                self.selection_started_callback(self.ruler.selected_ranges)
                self.Refresh()
        elif op == "start extend selection":
            last_start, last_end = self.ruler.selected_ranges[-1]
            value = self.position_to_value(pos)
            start, end = self.select_start, self.select_end
            if mode == "drag handle":
                # nearest end to handle determines which edge is moving
                if abs(value - start) < abs(value - end):
                    self.select_start = end
            else:
                if value < self.select_start:
                    self.select_start = end
            self.select_end = value
            self.ruler.selected_ranges[-1] = (self.select_start, self.select_end)
            self.selection_extended_callback(self.ruler.selected_ranges, self.ruler.marks_in_selection())
            self.Refresh()
        elif op == "extend selection":
            last_start, last_end = self.ruler.selected_ranges[-1]
            value = self.position_to_value(pos)
            self.ruler.selected_ranges[-1] = (last_start, value)
            self.selection_extended_callback(self.ruler.selected_ranges, self.ruler.marks_in_selection())
            self.Refresh()
        elif op == "finish selection":
            start, end = self.ruler.selected_ranges[-1]
            if end < start:
                start, end = end, start
            self.select_start, self.select_end = start, end
            self.selection_finished_callback(self.ruler.selected_ranges)
            if self.HasCapture():
                self.ReleaseMouse()
        elif op == "start drag":
            self.drag_start = wx.GetMousePosition()[0]  # absolute mouse pos (see below)
            self.view_at_drag_start, _ = self.panel.GetViewStart()
            next_mode = "dragging"
            if not self.HasCapture():
                self.CaptureMouse()
        elif op == "dragging":
            pos =  wx.GetMousePosition()[0]  # absolute mouse pos
            delta = pos - self.drag_start
            x = self.view_at_drag_start - delta
            self.panel.Scroll(x, 0)
            next_mode = "dragging"
        elif op == "end drag":
            self.drag_start = -1
            if self.HasCapture():
                self.ReleaseMouse()
        elif op == "hit test":
            if self.has_selection:
                start, end = self.ruler.selected_ranges[-1]
                if self.ruler.hit_test_value(pos, start) or self.ruler.hit_test_value(pos, end):
                    next_mode = "drag handle"
            label = self.ruler.hit_test(pos)
            if label is not None:
                self.over_item_callback(pos, label)
            else:
                self.not_over_item_callback(pos)
        elif op == "drag handle":
            start, end = self.ruler.selected_ranges[-1]
            if self.ruler.hit_test_value(pos, start) or self.ruler.hit_test_value(pos, end):
                pass
            else:
                next_mode = "select"
        elif op == "select item":
            self.caret_value = None
            if self.ruler.has_selection:
                self.ruler.selected_ranges = []
                self.Refresh()
            p = self.value_to_position(self.select_start)
            item = self.ruler.hit_test(p)
            if item is not None:
                self.selected_item_callback(item)
        else:
            log.debug("unknown state for mouse")
            if self.HasCapture():
                self.ReleaseMouse()

        if next_mode is None:
            next_mode = "select"
        self.set_mode(next_mode)
        event.Skip()

    def release_mouse(self):
        pass

    def selection_started_callback(self, selected_ranges):
        log.debug("selected_started_callback")

    def selection_extended_callback(self, selected_ranges, marks_in_selection):
        log.debug("selected_extended_callback")

    def selection_finished_callback(self, selected_ranges):
        items = self.ruler.marks_in_selection()
        log.debug("selected_finished_callback: items=%s" % str(items))

    def over_item_callback(self, pos, item):
        log.debug("hit at %d: %s" % (pos, item))

    def not_over_item_callback(self, pos):
        pass

    def selected_item_callback(self, item):
        log.debug("selected_item_callback: %s" % item)

    def selection_cleared_callback(self):
        log.debug("selected_cleared_callback")

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

        if size[0] < self.actual_screen_width:
            size[0] = self.actual_screen_width

        self.ruler.SetSize(size)
        # print "SIZE", size, type(size)
        self.panel.SetVirtualSize(size)

        new_pos = self.ruler.value_to_position(value)
        new_left = new_pos - pixels_from_left
        self.panel.Scroll(new_left, 0)

        self.update_limits()

    def update_limits(self):
        x, y = self.panel.GetViewStart()
        x1, y1 = self.panel.CalcUnscrolledPosition(x, y)
        left = self.ruler.position_to_value(x1)
        right = self.ruler.position_to_value(x1 + self.GetSize()[0] - 1)
        log.debug("update_limits: view=%d,%d unscrolled=%d,%d parent=%s left=%f right=%f" % (x, y, x1, y1, self.GetSize(), left, right))
        if self.label_min is not None:
            self.label_min.SetLabel(self.ruler.LabelString(left, True))
            self.label_max.SetLabel(self.ruler.LabelString(right, True))

    def on_scroll(self, evt):
        self.Refresh()
        self.update_limits()
        evt.Skip()

    def add_mark(self, start_time, end_time, item):
        self.ruler.set_mark(start_time, end_time, item)

    def rebuild(self, editor):
        log.debug("rebuild")
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
            log.debug("adding %s at %s - %s" % (item, start, end))
            self.add_mark(start, end, item)
        start = timeline_info["earliest_time"]
        end = timeline_info["latest_time"]
        self.ruler.SetRange(start, end)
        self.update_limits()


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
        self.populate(self)


class VirtualZoomRuler(wx.ScrolledWindow, ZoomRulerBase, VirtualLabeledRuler):
    """Zoomable ruler that uses a scrollbar and owner-drawing to implement the
    zoom.

    When the zoom is too far in, using a regular window will fail when it gets
    too big. "Too big" is platform dependent, but still it's an unacceptable
    limitation.

    This works around that by handling the scroll offsets ourselves and drawing
    on a virtual canvas.

    This class has multiple parents, and note that we are subclassing from
    RulerCtrl but *not* calling its constructor. We need to override some
    methods, but can't use the constructor because it expects itself to be in a
    real (non-virtual) window.

    The VirtualLabeledRuler constructor takes care of initializing all the
    attributes in RulerCtrl that it needs.
    """
    def __init__(self, parent, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, -1, style=wx.HSCROLL, **kwargs)
        VirtualLabeledRuler.__init__(self, parent)
        self.panel = self
        self.ruler = self

        self.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        self.SetScrollbars(1, 0, self._right, 0, 0, 0)
        self.SetScrollRate(1, 0)
        self.SetDoubleBuffered(False)

        self.label_max = self.label_min = None
        self.init_events()
        self.init_playback()

    def get_visible_range(self):
        x, _ = self.GetViewStart()
        return x, x + self.GetSize()[0] - 1

    def SetSize(self, size):
        self.SetBounds(0, 0, size[0], size[1])

    def GetSize(self):
        if self._right == -1:
            size = wx.ScrolledWindow.GetSize(self)
            self._right = 500
            self._bottom = size[1]
        return wx.Size(self._right, self._bottom)

    @property
    def actual_screen_width(self):
        size = wx.ScrolledWindow.GetSize(self)
        return size[0]

    def get_viewport(self):
        size = self.ruler.GetSize()
        width = size[0]
        left, _ = self.ruler.get_visible_range()
        return width, left

    def set_viewport(self, width, left):
        size = self.ruler.GetSize()
        size[0] = width
        self.ruler.SetSize(size)
        self.panel.SetVirtualSize(size)
        self.panel.Scroll(left, 0)

    def OnSize(self, event):
        # Need to handle the initial case to get the ruler size up to the
        # window size
        size = event.GetSize()
        if self._right == -1 or self._right < size[0]:
            self._right = size[0]
            self._bottom = size[1]

        width, height = self.CheckStyle()
        self.SetBounds(0, 0, width, height)
        log.debug("new virtual size: %d,%d; as reported %s" % (width, height, self.GetSize()))

        self.Invalidate()
        event.Skip()

    def OnPaint(self, event):
        """
        Handles the ``wx.EVT_PAINT`` event for :class:`RulerCtrl`.

        :param `event`: a :class:`PaintEvent` event to be processed.        
        """
        self.clear_and_paint()

    def clear_and_paint(self):
        dc = wx.ClientDC(self)
        dc.SetBackground(wx.Brush(self._background))
        dc.Clear()
        self.Draw(dc)

    def Update(self):
        wx.ScrolledWindow.Update(self)

ZoomRuler = VirtualZoomRuler


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)

    time_steps = [minute * 60.0 for minute in [1, 2, 5, 10, 15, 20, 30]]
    time_steps.extend([hour * 3600.0 for hour in [1, 2, 4, 6, 12]])
    time_steps.extend([day * 86400.0 for day in [1, 2, 3, 7, 14, 28]])
    visible_pixels = 800
    time_range = 100000  # seconds
    seconds_per_pixel = 100000 / 800
    step = time_steps[min(bisect.bisect(time_steps, abs(seconds_per_pixel)), len(time_steps) - 1)]
    print(time_steps)
    print(step)

    b = BitSink()
    print((b[1000000]))

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


    class DebugZoomRuler(VirtualZoomRuler):
        def selected_item_callback(self, item):
            print(f"item:{item}")


    app = wx.App()
    frm = wx.Frame(None,-1,"Test",style=wx.TAB_TRAVERSAL|wx.DEFAULT_FRAME_STYLE,
                   size=(800,400))
    panel = wx.Panel(frm)
    sizer = wx.BoxSizer(wx.VERTICAL)

    text = wx.StaticText(panel, -1, "Just a placeholder here.")
    sizer.Add(text, 1, wx.EXPAND)

    scroll = DebugZoomRuler(panel)
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
