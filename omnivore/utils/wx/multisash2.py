#----------------------------------------------------------------------
# Name:         multisash
# Purpose:      Multi Sash control
#
# Author:       Gerrit van Dyk
#
# Created:      2002/11/20
# Version:      0.1
# License:      wxWindows license
#----------------------------------------------------------------------
# 12/09/2003 - Jeff Grimmett (grimmtooth@softhome.net)
#
# o 2.5 compatibility update.
#
# 12/20/2003 - Jeff Grimmett (grimmtooth@softhome.net)
#
# o wxMultiSash -> MultiSash
# o wxMultiSplit -> MultiSplit
# o wxMultiViewLeaf -> MultiViewLeaf
#
import weakref
import json
from uuid import uuid4

import wx


import logging
#logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)
resize_log = logging.getLogger("resize")
#resize_log.setLevel(logging.DEBUG)


# Horizontal layout (side-by-side) or vertical layout (over-under) specified by
# either wx.HORIZONTAL or wx.VERTICAL. Split direction (left-to-
# right, bottom- to-top) specified with wx.LEFT, wx.RIGHT, wx.TOP, wx.BOTTOM

opposite = {
    wx.HORIZONTAL: wx.VERTICAL,
    wx.VERTICAL: wx.HORIZONTAL,
    wx.LEFT: wx.RIGHT,
    wx.RIGHT: wx.LEFT,
    wx.TOP: wx.BOTTOM,
    wx.BOTTOM: wx.TOP,
}


class MultiSash(wx.Window):
    _debug_count = 1

    sizer_thickness = 5

    wxEVT_CLIENT_CLOSE = wx.NewEventType()
    EVT_CLIENT_CLOSE = wx.PyEventBinder(wxEVT_CLIENT_CLOSE, 1)

    wxEVT_CLIENT_REPLACE = wx.NewEventType()
    EVT_CLIENT_REPLACE = wx.PyEventBinder(wxEVT_CLIENT_REPLACE, 1)

    wxEVT_CLIENT_ACTIVATED = wx.NewEventType()
    EVT_CLIENT_ACTIVATED = wx.PyEventBinder(wxEVT_CLIENT_ACTIVATED, 1)

    def __init__(self, parent, layout_direction=wx.HORIZONTAL, name="top", *_args, **_kwargs):
        wx.Window.__init__(self, parent, name=name, *_args, **_kwargs)
        self.live_update_control = None
        self.debug_id = "root"
        self.set_defaults()
        self._defChild = EmptyChild
        self.child = MultiSplit(self, self, layout_direction)
        self.hiding_space = wx.Window(self, -1, name="reparenting hiding space")
        self.hiding_space.Hide()
        self.sidebars = []
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.last_direction = wx.VERTICAL
        self.pending_sidebar_focus = None
        self.current_sidebar_focus = None
        self.current_leaf_focus = None
        self.previous_leaf_focus_list = []

    def set_defaults(self):
        self.use_close_button = True

        self.child_window_x = 2
        self.child_window_y = 2

        self.title_bar_height = 20
        self.title_bar_margin = 3
        self.title_bar_font = wx.NORMAL_FONT

        dc = wx.MemoryDC()
        dc.SetFont(self.title_bar_font)
        self.memory_dc = dc

        self.title_bar_font_height = max(dc.GetCharHeight(), 2)
        self.title_bar_x = self.title_bar_margin
        self.title_bar_y = (self.title_bar_height - self.title_bar_font_height) // 2

        self.sidebar_margin = 4

        self.focused_color = wx.Colour(0x2e, 0xb5, 0xf4) # Blue
        if wx.Platform == "__WXMAC__":
            self.border_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW)
            self.empty_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
            self.unfocused_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNHILIGHT)
        else:
            self.border_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW)
            self.empty_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INACTIVECAPTION)
            self.unfocused_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)

        self.empty_brush = wx.Brush(self.empty_color, wx.SOLID)

        self.focused_brush = wx.Brush(self.focused_color, wx.SOLID)
        self.focused_text_color = wx.WHITE
        self.focused_pen = wx.Pen(self.focused_text_color)
        self.focused_fill = wx.Brush(self.focused_text_color, wx.SOLID)

        self.unfocused_brush = wx.Brush(self.unfocused_color, wx.SOLID)
        self.unfocused_text_color = wx.BLACK
        self.unfocused_pen = wx.Pen(self.unfocused_text_color)
        self.unfocused_fill = wx.Brush(self.unfocused_text_color, wx.SOLID)

        self.close_button_size = (11, 11)

    def get_text_size(self, text):
        return self.memory_dc.GetTextExtent(text)

    def get_paint_tools(self, selected=False):
        if selected:
            brush = self.focused_brush
            pen = self.focused_pen
            fill = self.focused_fill
            text = self.focused_text_color
            textbg = self.focused_color
        else:
            brush = self.unfocused_brush
            pen = self.unfocused_pen
            fill = self.unfocused_fill
            text = self.unfocused_text_color
            textbg = self.unfocused_color
        return brush, pen, fill, text, textbg

    def configure_dc(self, dc, selected):
        brush, pen, fill, text, textbg = self.get_paint_tools(selected)
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetPen(pen)
        dc.SetBrush(brush)
        dc.SetTextForeground(text)
        dc.SetTextBackground(textbg)
        dc.SetFont(self.title_bar_font)
        return brush, pen, fill, text, textbg

    def configure_sidebar_dc(self, dc, selected):
        brush, _, fill, text, textbg = self.get_paint_tools(selected)
        if not selected:
            brush = self.empty_brush
            textbg = self.empty_color
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(brush)
        dc.SetTextForeground(text)
        dc.SetTextBackground(textbg)
        dc.SetFont(self.title_bar_font)

    def on_size(self, evt):
        self.do_layout()

    def do_layout(self):
        self.child.sizer_after = False
        self.child.sizer.Hide()
        x, y = 0, 0
        w, h = self.GetSize()
        for sidebar in self.sidebars:
            x, y, w, h = sidebar.set_size_inside(x, y, w, h)
        self.child.SetSize(x, y, w, h)
        self.child.do_layout()

    def calc_usable_rect(self):
        x, y = self.child.GetPosition()
        w, h = self.child.GetSize()
        return x, y, w, h

    def set_leaf_focus(self, leaf):
        self.clear_leaf_focus()
        self.current_leaf_focus = weakref.proxy(leaf)
        print("current_leaf_focus", leaf, "current_sidebar_focus", self.current_sidebar_focus)
        if self.current_sidebar_focus is not None:
            self.current_sidebar_focus.popdown()
            self.current_sidebar_focus = None
        self.current_leaf_focus.client.set_focus()

    def clear_leaf_focus(self):
        current = self.current_leaf_focus
        print("clear_leaf_focus", current)
        if current:  # fails if None or non-existent proxy
            current.client.clear_focus()
            if current.main_window_leaf:
                self.previous_leaf_focus_list.append(current)
        print("previous_leaf_focus_list", str(self.previous_leaf_focus_list))
        self.current_leaf_focus = None
        if self.pending_sidebar_focus is not None:
            if self.current_sidebar_focus != self.pending_sidebar_focus:
                self.pending_sidebar_focus.popdown()
            self.pending_sidebar_focus = None

    def force_clear_sidebar(self):
        if self.pending_sidebar_focus is not None:
            self.pending_sidebar_focus.popdown()
            self.pending_sidebar_focus = None
        if self.current_sidebar_focus is not None:
            self.current_sidebar_focus.popdown()
            self.current_sidebar_focus = None
            self.current_leaf_focus = None

    def set_sidebar_focus(self):
        self.current_sidebar_focus = self.pending_sidebar_focus
        #self.pending_sidebar_focus = None
        self.clear_leaf_focus()
        #self.set_leaf_focus(self.current_sidebar_focus)
        self.current_leaf_focus = self.current_sidebar_focus
        self.current_leaf_focus.client.set_focus()

    def restore_last_main_window_focus(self):
        try:
            print("restoring from", str(self.previous_leaf_focus_list))
            while True:
                prev = self.previous_leaf_focus_list.pop()
                if prev:
                    self.current_leaf_focus = prev
                    prev.client.set_focus()
                    return
        except IndexError:
            # nothing in list that still exists
            self.current_leaf_focus = None

    def is_leaf_focused(self, window):
        c = self.current_leaf_focus
        return c is not None and (c == window or c.client == window)

    def remove_all(self):
        old = self.child
        self.child = MultiSplit(self, self, old.layout_direction)
        old.remove_all()
        for sidebar in self.sidebars:
            sidebar.force_popup_to_top_of_stacking_order()
        self.do_layout()

    def get_layout(self, to_json=False, pretty=False):
        d = {'multisash': self.child.get_layout()}
        if to_json:
            if pretty:
                d = json.dumps(d, sort_keys=True, indent=4)
            else:
                d = json.dumps(d)
        return d

    def restore_layout(self, d):
        try:
            layout = d['multisash']
        except TypeError:
            try:
                d = json.loads(d)
            except ValueError, e:
                log.error("Error loading layout: %s" % e.message)
                return
            layout = d['multisash']
        old = self.child
        try:
            self.child = MultiSplit(self, self, layout=layout)
        except KeyError, e:
            log.error("Error loading layout: missing key %s. Restoring previous layout." % e.message)
            self.child.Destroy()
            self.child = old
        else:
            old.Destroy()
        self.do_layout()

    def update_captions(self):
        for sidebar in self.sidebars:
            sidebar.do_layout()
        self.Refresh()

    def find_uuid(self, uuid):
        return self.child.find_uuid(uuid)

    def find_empty(self):
        return self.child.find_empty()

    def focus_uuid(self, uuid):
        found = self.find_uuid(uuid)
        if found:
            print("FOCUS UUID:", found)
            self.set_leaf_focus(found.leaf)

    def replace_by_uuid(self, control, u):
        found = self.find_uuid(u)
        if found is not None:
            found.replace(control, u)
            return True
        return False

    def add(self, control, u=None, layout_direction=None, use_empty=True, side=None):
        if side is not None:
            self.add_sidebar(control, u, side)
        else:
            self.add_split(control, u, layout_direction, use_empty)

    def add_split(self, control, u=None, layout_direction=None, use_empty=True):
        if use_empty:
            found = self.find_empty()
            if found:
                found.replace(control, u)
                return
        if layout_direction is None:
            self.last_direction = opposite[self.last_direction]
            direction = self.last_direction
        leaf = self.child.views[-1]
        self.child.split(leaf, control, u, layout_direction)

    def use_sidebar(self, side=wx.LEFT):
        try:
            sidebar = self.find_sidebar(side)
        except ValueError:
            sidebar = Sidebar(self, side)
            self.sidebars.append(sidebar)
            self.do_layout()
        return sidebar

    def find_sidebar(self, side=wx.LEFT):
        for sidebar in self.sidebars:
            if side == sidebar.side:
                return sidebar
        raise ValueError("No sidebar on side")

    def add_sidebar(self, control, u=None, side=wx.LEFT):
        sidebar = self.use_sidebar(side)
        sidebar.add_client(control, u)

    def calc_graphviz(self):
        from graphviz import Digraph
        g = Digraph('multisash2', filename='multisash2.dot')
        self.calc_graphviz_children(self, g)
        return g

    def calc_graphviz_children(self, window, g):
        parent = window.GetName()
        for child in window.GetChildren():
            g.edge(parent, child.GetName())
            self.calc_graphviz_children(child, g)

    @classmethod
    def debug_window_name(cls, name):
        cls._debug_count += 1
        return "%s-%d" % (name, cls._debug_count)



class EmptyChild(wx.Window):
    multisash2_empty_control = True

    def __init__(self,parent):
        wx.Window.__init__(self,parent,-1, name=MultiSash.debug_window_name("blank"), style=wx.CLIP_CHILDREN)
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INACTIVECAPTION))
        self.SetLabel("Popup blank")

    def DoGetBestClientSize(self):
        return wx.Size(250, 300)


########## Splitter Layout ##########

class HorizontalLayout(object):
    @classmethod
    def calc_size(cls, multi_split):
        w, h = multi_split.GetClientSize()

        # size used for ratio includes all the sizer widths (including the
        # extra sizer at the end that won't be displayed)
        full_size = w + MultiSash.sizer_thickness

        return w, h, full_size

    @classmethod
    def do_view_size(cls, view, pos, size, w, h):
        view_width = size - MultiSash.sizer_thickness
        view.SetSize(pos, 0, view_width, h)
        view.sizer.SetSize(pos + view_width, 0, MultiSash.sizer_thickness, h)

    @classmethod
    def calc_resizer(cls, splitter, left, sizer, right, x, y):
        return HorizontalResizer(splitter, left, sizer, right, x, y)


class HorizontalResizer(object):
    def __init__(self, splitter, first, sizer, second, sizer_evt_x, sizer_evt_y):
        self.splitter = splitter
        self.first = first
        self.sizer = sizer
        self.second = second
        self.zero_pos = first.GetPosition()
        self.total_ratio = first.ratio_in_parent + second.ratio_in_parent
        self.total_width, self.total_height = self.calc_pixel_size()
        self.mouse_offset = sizer_evt_x, sizer_evt_y
        self.x_sash, self.y_sash = self.calc_splitter_pos(sizer_evt_x, sizer_evt_y)
        self.calc_extrema()

    def __repr__(self):
        return "%s: %s %s, ratio=%f, width=%d" % (self.__class__.__name__, self.first.debug_id, self.second.debug_id, self.total_ratio, self.total_width)

    def calc_pixel_size(self):
        w1, h1 = self.first.GetSize()
        w2, h2 = self.second.GetSize()
        w = w1 + w2 + 2 * (MultiSash.sizer_thickness)
        h = h1 + h2 + 2 * (MultiSash.sizer_thickness)
        return w, h

    def calc_splitter_pos(self, sizer_evt_x, sizer_evt_y):
        # Calculate the right/bottom location of the moving sash (for either
        # horz or vert; they don't use the other value so both can be
        # calculated in a single method). This location is used because it's
        # the point at which the ratio is calculated in the layout_calculator's
        # do_view_size method
        xs, ys = self.sizer.ClientToScreen((sizer_evt_x, sizer_evt_y))
        x, y = self.splitter.ScreenToClient((xs, ys))
        log.debug("calc_splitter_pos: evt: %d,%d screen: %d,%d first: %d,%d" % (sizer_evt_x, sizer_evt_y, xs, ys, x, y))
        x, y = x - self.mouse_offset[0] + MultiSash.sizer_thickness, y - self.mouse_offset[1] + MultiSash.sizer_thickness
        return x, y

    def calc_extrema(self):
        self.x_min, _ = self.first.GetPosition()
        self.x_min += 2 * MultiSash.sizer_thickness
        x, _ = self.second.GetPosition()
        w, _ = self.second.GetSize()
        self.x_max = x + w
        self.x_max -= MultiSash.sizer_thickness
        log.debug("calc_extrema: min %d, x %d, w %d, max %d" % (self.x_min, x, w, self.x_max))

    def set_ratios(self, x, y):
        r = float(x - self.zero_pos[0]) / float(self.total_width) * self.total_ratio
        log.debug("x,r,x_min,xmax", x, r, self.x_min, self.x_max)
        if x > self.x_min and x < self.x_max:
            self.first.ratio_in_parent = r
            self.second.ratio_in_parent = self.total_ratio - r
            return True

    def do_mouse_move(self, sizer_evt_x, sizer_evt_y):
        x, y = self.calc_splitter_pos(sizer_evt_x, sizer_evt_y)
        log.debug("do_mouse_move: sizer: %d,%d first: %d,%d" % (sizer_evt_x, sizer_evt_y, x, y))
        if self.set_ratios(x, y):
            self.splitter.do_layout()
        else:
            log.debug("do_mouse_move: out of range")

class VerticalLayout(object):
    @classmethod
    def calc_size(cls, multi_split):
        w, h = multi_split.GetClientSize()

        # size used for ratio includes all the sizer widths (including the
        # extra sizer at the end that won't be displayed)
        full_size = h + MultiSash.sizer_thickness

        return w, h, full_size

    @classmethod
    def do_view_size(cls, view, pos, size, w, h):
        view_height = size - MultiSash.sizer_thickness
        view.SetSize(0, pos, w, view_height)
        view.sizer.SetSize(0, pos + view_height, w, MultiSash.sizer_thickness)

    @classmethod
    def calc_resizer(cls, splitter, top, sizer, bot, x, y):
        return VerticalResizer(splitter, top, sizer, bot, x, y)


class VerticalResizer(HorizontalResizer):
    def __repr__(self):
        return "%s: %s %s, ratio=%f, height=%d" % (self.__class__.__name__, self.first.debug_id, self.second.debug_id, self.total_ratio, self.total_height)

    def calc_extrema(self):
        _, self.y_min = self.first.GetPosition()
        self.y_min += 2 * MultiSash.sizer_thickness
        _, y = self.second.GetPosition()
        _, h = self.second.GetSize()
        self.y_max = y + h
        self.y_max -= MultiSash.sizer_thickness
        log.debug("calc_extrema: min %d, y %d, h %d, max %d" % (self.y_min, y, h, self.y_max))

    def set_ratios(self, x, y):
        r = float(y - self.zero_pos[1]) / float(self.total_height) * self.total_ratio
        log.debug("y,r,y_min,xmax", y, r, self.y_min, self.y_max)
        if y > self.y_min and y < self.y_max:
            self.first.ratio_in_parent = r
            self.second.ratio_in_parent = self.total_ratio - r
            return True


class MultiSizer(wx.Window):
    def __init__(self, parent, color):
        wx.Window.__init__(self, parent, -1, style = wx.CLIP_CHILDREN, name=MultiSash.debug_window_name("MultiSizer"))

        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)

        self.SetBackgroundColour(color)

    def on_leave(self,evt):
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def on_enter(self,evt):
        if self.GetParent().layout_direction == wx.HORIZONTAL:
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))


########## Splitter ##########

class MultiWindowBase(wx.Window):
    debug_letter = "A"

    @classmethod
    def next_debug_letter(cls):
        cls.debug_letter = chr(ord(cls.debug_letter) + 1)
        return cls.debug_letter

    def __init__(self, multiView, parent, ratio=1.0, name="MultiWindowBase"):
        wx.Window.__init__(self, parent, -1, style = wx.CLIP_CHILDREN, name=MultiSash.debug_window_name(name))
        self.multiView = multiView

        self.resizer = None
        self.sizer_after = True
        self.sizer = MultiSizer(parent, multiView.empty_color)
        self.sizer.Bind(wx.EVT_MOTION, self.on_motion)
        self.sizer.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.sizer.Bind(wx.EVT_LEFT_UP, self.on_left_up)

        self.ratio_in_parent = ratio
        self.debug_id = self.next_debug_letter()
        if self.debug_id == "S":
            # Skip S; used for hidden panes
            self.debug_id = self.next_debug_letter()
        self.SetBackgroundColour(wx.RED)

    def do_layout(self):
        raise NotImplementedError

    def remove(self):
        self.sizer.Destroy()
        self.Destroy()

    def remove_all(self):
        self.remove()

    def on_motion(self,evt):
        if self.resizer is not None:
            self.resizer.do_mouse_move(evt.x, evt.y)
        else:
            evt.Skip()

    def on_left_down(self, evt):
        splitter = self.GetParent()
        try:
            resize_partner = splitter.find_resize_partner(self)
        except IndexError:
            evt.Skip()
            resize_partner = None
        if resize_partner:
            self.resizer = splitter.layout_calculator.calc_resizer(splitter, self, self.sizer, resize_partner, evt.x, evt.y)
            self.sizer.CaptureMouse()

    def on_left_up(self,evt):
        if self.resizer is not None:
            self.sizer.ReleaseMouse()
            self.resizer = None
        else:
            evt.Skip()


class ViewContainer(object):
    def __init__(self):
        self.views = []

    def remove(self):
        self.Destroy()

    def remove_all(self):
        for view in self.views:
            view.remove_all()
        self.remove()

    def find_uuid(self, uuid):
        for view in self.views:
            found = view.find_uuid(uuid)
            if found is not None:
                return found
        return None

    def find_empty(self):
        for view in self.views:
            found = view.find_empty()
            if found is not None:
                return found
        return None


class MultiSplit(MultiWindowBase, ViewContainer):
    def __init__(self, multiView, parent, layout_direction=wx.HORIZONTAL, ratio=1.0, leaf=None, layout=None):
        MultiWindowBase.__init__(self, multiView, parent, ratio, name="MultiSplit")
        ViewContainer.__init__(self)
        if layout is not None:
            self.restore_layout(layout)
        else:
            self.layout_direction = layout_direction
            if leaf:
                leaf.Reparent(self)
                leaf.sizer.Reparent(self)
                leaf.Move(0,0)
                leaf.ratio_in_parent = 1.0
            else:
                leaf = MultiViewLeaf(self.multiView, self, 1.0)
            self.views.append(leaf)
        if self.layout_direction == wx.HORIZONTAL:
            self.layout_calculator = HorizontalLayout
        else:
            self.layout_calculator = VerticalLayout
        self.do_layout()

    def __repr__(self):
        return "<MultiSplit %s %f>" % (self.debug_id, self.ratio_in_parent)

    def find_leaf_index(self, leaf):
        return self.views.index(leaf)  # raises IndexError on failure

    def find_resize_partner(self, leaf):
        current = self.find_leaf_index(leaf)
        return self.views[current + 1]

    def split(self, leaf, control=None, uuid=None, layout_direction=None, start=wx.LEFT|wx.TOP):
        if layout_direction is not None and layout_direction != self.layout_direction:
            self.split_opposite(leaf, control, uuid, start)
        else:
            self.split_same(leaf, control, uuid, start)

    def split_same(self, leaf, control=None, uuid=None, start=wx.LEFT|wx.TOP):
        view_index_to_split = self.find_leaf_index(leaf)
        if start & (wx.LEFT|wx.TOP):
            # insert at beginning of list
            insert_pos = view_index_to_split
        else:
            insert_pos = view_index_to_split + 1
        ratio = leaf.ratio_in_parent / 2.0
        leaf.ratio_in_parent = ratio

        if control is None:
            control = self.multiView._defChild(self)
        view = MultiViewLeaf(self.multiView, self, ratio, control, uuid)
        self.views[insert_pos:insert_pos] = [view]
        self.do_layout()

    def split_opposite(self, leaf, control=None, uuid=None, start=wx.LEFT|wx.TOP):
        view_index_to_split = self.find_leaf_index(leaf)
        subsplit = MultiSplit(self.multiView, self, opposite[self.layout_direction], leaf.ratio_in_parent, leaf)
        self.views[view_index_to_split] = subsplit
        self.do_layout()
        subsplit.split_same(leaf, control, uuid, start)

    def do_layout(self):
        w, h, full_size = self.layout_calculator.calc_size(self)

        for view in self.views:
            view.sizer_after = True
        view.sizer_after = False

        remaining_size = full_size
        pos = 0
        for view in self.views:
            if view.sizer_after:
                size = int(view.ratio_in_parent * full_size)
            else:
                size = remaining_size
            self.layout_calculator.do_view_size(view, pos, size, w, h)
            view.sizer.Show(view.sizer_after)
            view.do_layout()
            remaining_size -= size
            pos += size

    def get_layout(self):
        d = {
            'direction': self.layout_direction,
            'ratio_in_parent': self.ratio_in_parent,
            'views': [v.get_layout() for v in self.views],
            'debug_id': self.debug_id,
            }
        return d

    def restore_layout(self, d):
        self.layout_direction = d['direction']
        self.ratio_in_parent = d['ratio_in_parent']
        self.debug_id = d['debug_id']
        for layout in d['views']:
            if 'direction' in layout:
                view = MultiSplit(self.multiView, self, layout=layout)
            else:
                view = MultiViewLeaf(self.multiView, self, layout=layout)
            self.views.append(view)

    def destroy_leaf(self, view):
        log.debug("destroy_leaf: view=%s views=%s self=%s parent=%s" % (view, self.views, self, self.GetParent()))
        index = self.find_leaf_index(view)  # raise IndexError
        if len(self.views) > 2:
            log.debug("deleting > 2: %d %s" %(index, self.views))
            del self.views[index]
            r = view.ratio_in_parent / len(self.views)
            for v in self.views:
                v.ratio_in_parent += r
            view.remove()
            self.do_layout()
        elif len(self.views) == 2:
            log.debug("deleting == 2: %d %s, parent=%s self=%s" % (index, self.views, self.GetParent(), self))
            # remove leaf, resulting in a single leaf inside a multisplit.
            # Instead of leaving it like this, move it up into the parent
            # multisplit
            del self.views[index]
            view.remove()
            if self.GetParent() == self.multiView:
                # Only one item left.
                log.debug("  last item in %s!" % (self))
                self.views[0].ratio_in_parent = 1.0
                self.do_layout()
            else:
                log.debug("  deleting %s from parent %s parent views=%s" % (self, self.GetParent(), self.GetParent().views))
                self.GetParent().reparent_from_splitter(self)
        else:
            # must be at the top; the final splitter.
            log.debug("Removing the last item!", view)
            self.GetParent().remove_all()

    def reparent_from_splitter(self, splitter):
        index = self.find_leaf_index(splitter)  # raise IndexError
        view = splitter.views[0]
        view.ratio_in_parent = splitter.ratio_in_parent
        view.Reparent(self)
        view.sizer.Reparent(self)
        self.views[index] = view
        splitter.remove()
        self.do_layout()


########## Leaf (Client Container) ##########


class MultiViewLeaf(MultiWindowBase):
    main_window_leaf = True

    def __init__(self, multiView, parent, ratio=1.0, child=None, u=None, layout=None):
        MultiWindowBase.__init__(self, multiView, parent, ratio, name="MultiViewLeaf")
        if layout is not None:
            self.client = None
            self.restore_layout(layout)
        else:
            self.client = MultiClient(self, child, u)
        self.SetBackgroundColour(multiView.unfocused_color)

    def __repr__(self):
        return "<MultiLeaf %s %f>" % (self.debug_id, self.ratio_in_parent)

    def remove(self):
        self.client.do_send_close_event()
        self.sizer.Destroy()
        self.Destroy()

    def remove_all(self):
        self.remove()

    def find_uuid(self, uuid):
        if uuid == self.client.child_uuid:
            log.debug("find_uuid: found %s in %s" % (uuid, self.client.child.GetName()))
            return self.client
        log.debug("find_uuid: skipping %s in %s" % (self.client.child_uuid, self.client.child.GetName()))
        return None

    def find_empty(self):
        if hasattr(self.client.child, "multisash2_empty_control") and self.client.child.multisash2_empty_control:
            log.debug("find_empty: found %s" % (self.client.child.GetName()))
            return self.client
        log.debug("find_empty: skipping %s in %s" % (self.client.child_uuid, self.client.child.GetName()))
        return None

    def get_layout(self):
        d = {
            'ratio_in_parent': self.ratio_in_parent,
            'debug_id': self.debug_id,
            'child_uuid': self.client.child_uuid,
            }
        if hasattr(self.client.child,'get_layout'):
            attr = getattr(self.client.child, 'get_layout')
            if callable(attr):
                layout = attr()
                if layout:
                    d['detail'] = layout
        return d

    def restore_layout(self, d):
        self.debug_id = d['debug_id']
        self.ratio_in_parent = d['ratio_in_parent']
        old = self.client
        self.client = MultiClient(self, None, d['child_uuid'])
        dData = d.get('detail',None)
        if dData:
            if hasattr(self.client.child,'restore_layout'):
                attr = getattr(self.client.child,'restore_layout')
                if callable(attr):
                    attr(dData)
        if old is not None:
            old.Destroy()
        self.client.do_size_from_parent()

    def get_multi_split(self):
        return self.GetParent()

    def split(self, *args, **kwargs):
        self.GetParent().split(self, *args, **kwargs)

    def destroy_leaf(self):
        self.GetParent().destroy_leaf(self)

    def do_layout(self):
        self.client.do_size_from_parent()


class MultiClient(wx.Window):
    def __init__(self, parent, child=None, uuid=None, pos=None, size=None, multiView=None, extra_border=1, in_sidebar=False, leaf=None):
        if pos is None:
            pos = (0, 0)
        if size is None:
            size = parent.GetSize()

        wx.Window.__init__(self, parent, -1, pos=pos, size=size, style=wx.CLIP_CHILDREN | wx.BORDER_NONE, name=MultiSash.debug_window_name("MultiClient"))
        if multiView is None:
            multiView = parent.multiView
        self.multiView = multiView

        if leaf is None:
            leaf = parent
        self.leaf = leaf

        if in_sidebar:
            self.SetBackgroundColour(multiView.focused_color)
        else:
            self.SetBackgroundColour(multiView.border_color)
        self.SetBackgroundColour(wx.RED)
        self.in_sidebar = in_sidebar

        if uuid is None:
            uuid = str(uuid4())
        self.child_uuid = uuid

        self.extra_border = extra_border
        self.title_bar = TitleBar(self, close=not in_sidebar, split=not in_sidebar)

        if child is None:
            child = self.multiView._defChild(self)
        self.child = child
        self.child.Reparent(self)
        self.move_child()
        log.debug("Created client for %s" % self.child_uuid)

        self.Bind(wx.EVT_SET_FOCUS, self.on_set_focus)
        self.Bind(wx.EVT_CHILD_FOCUS, self.on_child_focus)

    def do_send_event(self, evt):
        return not self.GetEventHandler().ProcessEvent(evt) or evt.IsAllowed()

    def do_send_close_event(self):
        log.debug("sending close event for %s" % self)
        evt = MultiSashEvent(MultiSash.wxEVT_CLIENT_CLOSE, self)
        evt.SetChild(self.child)
        self.do_send_event(evt)

    def do_send_replace_event(self, new_child):
        log.debug("sending replace event for %s" % self)
        evt = MultiSashEvent(MultiSash.wxEVT_CLIENT_REPLACE, self)
        evt.SetChild(self.child)
        evt.SetReplacementChild(new_child)
        self.do_send_event(evt)

    @property
    def title(self):
        return self.child.GetName()

    @property
    def popup_name(self):
        return self.child.GetLabel()

    def clear_focus(self):
        self.Refresh()

    def set_focus(self):
        evt = MultiSashEvent(MultiSash.wxEVT_CLIENT_ACTIVATED, self)
        evt.SetChild(self.child)
        self.do_send_event(evt)
        self.child.SetFocus()
        self.Refresh()

    def do_size_from_parent(self):
        w, h = self.GetParent().GetClientSize()
        self.do_size_from_bounds(w, h)

    def do_size_from_bounds(self, w, h):
        self.SetSize(w, h)
        b = self.extra_border
        m = self.multiView
        w -= b * 2
        h -= b * 2
        # print("in client %s:" % self.GetParent().debug_id, w, h)
        self.title_bar.SetSize(b, b, w, m.title_bar_height)
        self.child.SetSize(b, b + m.title_bar_height, w, h - m.title_bar_height)

    def DoGetBestClientSize(self):
        b = self.extra_border
        m = self.multiView
        w, h = self.child.GetBestSize()
        return wx.Size(w + b * 2, h + b * 2 + m.title_bar_height)

    def do_size_from_child(self):
        b = self.extra_border
        m = self.multiView
        w, h = self.child.GetBestSize()
        self.SetSize((w + b * 2, h + b * 2 + m.title_bar_height))
        self.title_bar.SetSize(b, b, w, m.title_bar_height)
        self.child.SetSize(b, b + m.title_bar_height, w, h)

    def replace(self, child, u=None):
        if self.child:
            self.do_send_replace_event(child)
            self.child.Destroy()
            self.child = None
        self.child = child
        self.child.Reparent(self)
        if u is None:
            u = str(uuid4())
        self.child_uuid = u
        self.move_child()
        self.do_size_from_parent()

    def move_child(self):
        self.title_bar.Move(0, 0)
        self.child.Move(0, self.multiView.title_bar_height)

    def on_set_focus(self,evt):
        m = self.multiView
        if self.leaf == m.current_leaf_focus:
            print("already focused", self.leaf)
        else:
            print("on_set_focus", self.leaf, "current_leaf_focus", m.current_leaf_focus, "current_sidebar_focus", m.current_sidebar_focus)
            m.set_leaf_focus(self.leaf)

    def on_child_focus(self,evt):
        self.on_set_focus(evt)

    def show_as_popup(self, x, y, w, h):
        self.SetPosition((x, y))
        self.do_size_from_bounds(w, h)
        self.Show()


########## Title Bar ##########

class TitleBar(wx.Window):
    def __init__(self, parent, close=True, split=True):
        wx.Window.__init__(self, parent, -1, name=MultiSash.debug_window_name("TitleBar"))
        self.client = parent
        m = self.client.multiView

        self.buttons = []
        self.buttons.append(TitleBarCloser(self, m.close_button_size, enabled=close))
        self.buttons.append(TitleBarHSplitNewBot(self, m.close_button_size, enabled=split))
        self.buttons.append(TitleBarVSplitNewRight(self, m.close_button_size, enabled=split))

        self.SetBackgroundColour(wx.RED)
        self.hide_buttons()

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEAVE_WINDOW,self.on_leave)
        self.Bind(wx.EVT_ENTER_WINDOW,self.on_enter)

    def draw_title_bar(self, dc):
        m = self.client.multiView
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetPen(wx.TRANSPARENT_PEN)
        brush, _, _, text, textbg = m.get_paint_tools(m.is_leaf_focused(self.client))
        dc.SetBrush(brush)

        w, h = self.GetSize()
        dc.SetFont(m.title_bar_font)
        dc.SetTextBackground(textbg)
        dc.SetTextForeground(text)
        dc.DrawRectangle(0, 0, w, h)
        dc.DrawText(self.client.title, m.title_bar_x, m.title_bar_y)

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        self.draw_title_bar(dc)

    def on_size(self, evt):
        m = self.client.multiView
        w, h = self.GetClientSize()
        x = w - m.title_bar_margin
        for button in self.buttons:
            if button.is_enabled:
                x = button.do_button_pos(x, h)
                x -= m.title_bar_margin
                button.Show()
            else:
                button.Hide()

    def hide_buttons(self):
        for b in self.buttons[1:]:
            if b: b.Hide()

    def show_buttons(self):
        for b in self.buttons[1:]:
            if b: b.Show()

    def on_enter(self, evt):
        self.show_buttons()

    def on_leave(self, evt):
        # check if left the window but still in the title bar, otherwise will
        # enter an endless cycle of leave/enter events as the buttons due to
        # the show/hide of the buttons being right under the cursor
        x, y = evt.GetPosition()
        w, h = self.GetSize()
        if x <= 0 or x >= w or y <= 0 or y >= h:
            self.hide_buttons()


class TitleBarButton(wx.Window):
    def __init__(self, parent, size, enabled=True):
        self.title_bar = parent
        self.client = parent.GetParent()
        self.leaf = self.client.GetParent()
        wx.Window.__init__(self, parent, -1, pos=(0, 0), size=size, style=wx.BORDER_NONE, name=MultiSash.debug_window_name("TitleBarButton"))

        self.down = False
        self.entered = False
        self.is_enabled = enabled

        self.Bind(wx.EVT_LEFT_DOWN, self.on_press)
        self.Bind(wx.EVT_LEFT_UP, self.on_release)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)

    def on_press(self,evt):
        self.down = True
        evt.Skip()

    def on_release(self,evt):
        if self.down and self.entered:
            wx.CallAfter(self.title_bar.hide_buttons)
            self.do_action(evt)
        else:
            evt.Skip()
        self.down = False

    def on_paint(self, event):
        m = self.client.multiView
        dc = wx.PaintDC(self)
        size = self.GetClientSize()

        bg_brush, pen, fg_brush, _, _ = m.get_paint_tools(m.is_leaf_focused(self.client))
        self.draw_button(dc, size, bg_brush, pen, fg_brush)

    def draw_button(self, dc, size, bg_brush, pen, fg_brush):
        pass

    def on_leave(self,evt):
        self.entered = False

    def on_enter(self,evt):
        self.entered = True

    def do_action(self, evt):
        pass

    def do_button_pos(self, x, h):
        bw, bh = self.GetSize()
        x -= bw
        y = (h - bh) // 2
        self.SetPosition((x, y))
        return x


class TitleBarCloser(TitleBarButton):
    def draw_button(self, dc, size, bg_brush, pen, fg_brush):
        dc.SetBrush(bg_brush)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, size.x, size.y)
        dc.SetPen(pen)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(0, 0, size.x, size.y)
        dc.DrawLine(0, 0, size.x, size.y)
        dc.DrawLine(0, size.y, size.x, 0)

    def do_action(self, evt):
        requested_close = self.ask_close()
        if requested_close:
            wx.CallAfter(self.leaf.destroy_leaf)

    def ask_close(self):
        return True


class TitleBarVSplitNewRight(TitleBarCloser):
    def draw_button(self, dc, size, bg_brush, pen, fg_brush):
        split = size.x // 2
        dc.SetBrush(bg_brush)
        dc.SetPen(pen)
        dc.DrawRectangle(0, 0, split + 1, size.y)
        dc.SetBrush(fg_brush)
        dc.DrawRectangle(split, 0, size.x - split, size.y)

    def do_action(self, evt):
        self.leaf.split(layout_direction=wx.HORIZONTAL)


class TitleBarHSplitNewBot(TitleBarCloser):
    def draw_button(self, dc, size, bg_brush, pen, fg_brush):
        split = size.y // 2
        dc.SetBrush(bg_brush)
        dc.SetPen(pen)
        dc.DrawRectangle(0, 0, size.x, split + 1)
        dc.SetBrush(fg_brush)
        dc.DrawRectangle(0, split, size.x, size.y - split)

    def do_action(self, evt):
        self.leaf.split(layout_direction=wx.VERTICAL)


########## Sidebar ##########

class SidebarBaseRenderer(object):
    @classmethod
    def calc_view_start(self, w, h):
        return 0

    @classmethod
    def calc_thickness(cls, sidebar):
        m = sidebar.multiView
        pixels = m.sidebar_margin * 2 + m.title_bar_font_height
        return pixels


class SidebarVerticalRenderer(SidebarBaseRenderer):
    @classmethod
    def do_view_size(self, view, pos, w, h):
        m = view.multiView
        text_width, text_height = m.get_text_size(view.client.popup_name)
        size = text_width + 2 * m.sidebar_margin
        view.SetSize(0, pos, w, size)
        view.label_x = m.sidebar_margin
        view.label_y = m.sidebar_margin + text_width
        return pos + size

    @classmethod
    def draw_label(self, dc, view):
        w, h = view.GetSize()
        dc.DrawRectangle(0, 0, w, h)
        dc.DrawRotatedText(view.client.popup_name, view.label_x, view.label_y, 90.0)

    @classmethod
    def show_client_prevent_clipping(self, sidebar, view, x, y):
        cw, ch = view.client.GetBestSize()
        x_min, y_min, sw, sh = sidebar.multiView.calc_usable_rect()
        if y + ch > y_min + sh:
            y -= (y + ch - sh)
        if y < y_min:
            y = y_min
            ch = sh
        if cw > sw:
            cw = sw
        sidebar.do_popup_view(view, x, y, cw, ch)


class SidebarLeftRenderer(SidebarVerticalRenderer):
    @classmethod
    def set_size_inside(cls, sidebar, x, y, w, h):
        thickness = cls.calc_thickness(sidebar)
        sidebar.SetSize(x, y, thickness, h)
        return x + thickness, y, w - thickness, h

    @classmethod
    def show_client(cls, sidebar, view):
        # sidebar position within multiView, so these are global values
        x_min, y_min = sidebar.GetPosition()
        w, h = sidebar.GetSize()
        x_min += w

        # view position is position within sidebar
        x, y = view.GetPosition()
        w, h = view.GetSize()
        y += y_min  # global y for top of window
        cls.show_client_prevent_clipping(sidebar, view, x_min, y)


class SidebarRightRenderer(SidebarVerticalRenderer):
    @classmethod
    def set_size_inside(cls, sidebar, x, y, w, h):
        thickness = cls.calc_thickness(sidebar)
        sidebar.SetSize(x + w - thickness, y, thickness, h)
        return x, y, w - thickness, h


class SidebarHorizontalRenderer(SidebarBaseRenderer):
    @classmethod
    def do_view_size(self, view, pos, w, h):
        m = view.multiView
        text_width, text_height = m.get_text_size(view.client.popup_name)
        size = text_width + 2 * m.sidebar_margin
        view.SetSize(pos, 0, size, h)
        view.label_x = m.sidebar_margin
        view.label_y = m.sidebar_margin
        return pos + size

    @classmethod
    def draw_label(self, dc, view):
        w, h = view.GetSize()
        dc.DrawRectangle(0, 0, w, h)
        dc.DrawText(view.client.popup_name, view.label_x, view.label_y)

    @classmethod
    def show_client_prevent_clipping(self, sidebar, view, x, y):
        cw, ch = view.client.GetBestSize()
        x_min, y_min, sw, sh = sidebar.multiView.calc_usable_rect()
        x = max(x, x_min)
        if x + cw > x_min + sw:
            # first try to shift left to attempt to contain larger popup
            x -= (x + cw - sw)
        if x < x_min:
            # if popup is too wide, force it to be exact size of usable area
            x = x_min
            cw = sw
        if ch > sh:
            ch = sh
        sidebar.do_popup_view(view, x, y, cw, ch)


class SidebarTopRenderer(SidebarHorizontalRenderer):
    @classmethod
    def set_size_inside(cls, sidebar, x, y, w, h):
        thickness = cls.calc_thickness(sidebar)
        sidebar.SetSize(x, y, w, thickness)
        return x, y + thickness, w, h - thickness

    @classmethod
    def show_client(cls, sidebar, view):
        # sidebar position within multiView, so these are global values
        x_min, y_min = sidebar.GetPosition()
        w, h = sidebar.GetSize()
        y_min += h

        # view position is position within sidebar
        x, y = view.GetPosition()
        w, h = view.GetSize()
        x += x_min  # global y for top of window
        cls.show_client_prevent_clipping(sidebar, view, x, y_min)


class SidebarBottomRenderer(SidebarHorizontalRenderer):
    @classmethod
    def set_size_inside(cls, sidebar, x, y, w, h):
        thickness = cls.calc_thickness(sidebar)
        sidebar.SetSize(x, y + h - thickness, w, thickness)
        return x, y, w, h - thickness


class SidebarMenuItem(wx.Window):
    main_window_leaf = False

    def __init__(self, sidebar, child, uuid=None):
        wx.Window.__init__(self, sidebar, -1, name=MultiSash.debug_window_name("SidebarMenuItem"))
        self.sidebar = sidebar
        self.multiView = sidebar.multiView

        # Client windows are children of the main window so they can be
        # positioned over (and therefore obscure) any window within the
        # MultiSash
        self.client = MultiClient(self.multiView, child, uuid, size=(200,200), multiView=self.multiView, extra_border=4, in_sidebar=True, leaf=self)
        self.SetBackgroundColour(self.multiView.empty_color)

        # the label drawing offsets will be calculated during sizing
        self.label_x = 0
        self.label_y = 0
        self.entered = False
        self.client.Hide()

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        s = self.sidebar
        s.multiView.configure_sidebar_dc(dc, self.entered)
        s.title_renderer.draw_label(dc, self)

    def on_leave(self,evt):
        m = self.multiView
        if m.current_sidebar_focus == self:
            pass
        elif m.pending_sidebar_focus != self:
            self.popdown()

    def on_enter(self,evt):
        m = self.multiView
        print("on_enter: current sidebar focus", m.current_sidebar_focus, "current_leaf_focus", m.current_leaf_focus)
        if not m.current_sidebar_focus:
            if m.pending_sidebar_focus:
                m.pending_sidebar_focus.popdown()
            self.popup()

    def on_motion(self,evt):
        print("pending sidebar focus=%s" % self.multiView.pending_sidebar_focus)
        evt.Skip()

    def on_left_down(self, evt):
        m = self.multiView
        if m.current_sidebar_focus == self:
            m.restore_last_main_window_focus()
        else:
            if m.current_sidebar_focus:
                print("clicked on another sidebar label %s" % self)
                m.force_clear_sidebar()
                self.popup()
            else:
                m.pending_sidebar_focus = self
                print("setting pending focus to sidebar %s" % self)

    def on_left_up(self,evt):
        m = self.multiView
        if m.pending_sidebar_focus == self:
            print("Setting focus to sidebar!")
            m.set_sidebar_focus()

    def popup(self):
        self.entered = True
        self.sidebar.title_renderer.show_client(self.sidebar, self)
        self.Refresh()

    def popdown(self):
        self.entered = False
        self.client.Hide()
        self.Refresh()

    def remove(self):
        self.client.do_send_close_event()
        self.Destroy()

    def remove_all(self):
        self.remove()

    def find_uuid(self, uuid):
        if uuid == self.client.child_uuid:
            log.debug("find_uuid: found %s in %s" % (uuid, self.client.child.GetName()))
            return self.client
        log.debug("find_uuid: skipping %s in %s" % (self.client.child_uuid, self.client.child.GetName()))
        return None


class Sidebar(wx.Window, ViewContainer):
    def __init__(self, multiView, side=wx.LEFT, layout=None):
        wx.Window.__init__(self, multiView, -1, name=MultiSash.debug_window_name("Sidebar"))
        ViewContainer.__init__(self)
        self.multiView = multiView

        self.SetBackgroundColour(multiView.empty_color)
        if layout is not None:
            self.restore_layout(layout)
        else:
            if side == wx.RIGHT:
                self.title_renderer = SidebarRightRenderer
            elif side == wx.TOP:
                self.title_renderer = SidebarTopRenderer
            elif side == wx.BOTTOM:
                self.title_renderer = SidebarBottomRenderer
            else:
                side = wx.LEFT
                self.title_renderer = SidebarLeftRenderer
            self.side = side

    def set_size_inside(self, x, y, w, h):
        return self.title_renderer.set_size_inside(self, x, y, w, h)

    def add_client(self, control, u=None):
        if control is None:
            control = self.multiView._defChild(self)
        view = SidebarMenuItem(self, control, u)
        self.views.append(view)
        self.do_layout()

    def force_popup_to_top_of_stacking_order(self):
        # Unless popup is at the top of the stacking order, it will be obscured
        # by the main MultiSplit window (and all of its children, of course).
        # This method is needed only when the main MultiSplit window is changed
        # with a call to MultiSash.remove_all
        for view in self.views:
            # There doesn't appear to be an explicit way to force a particular
            # child window to the top of the stacking order, but this is a
            # workaround.
            view.client.Reparent(self.multiView.hiding_space)
            view.client.Reparent(self.multiView)
            pass

    def do_layout(self):
        w, h = self.GetSize()

        pos = self.title_renderer.calc_view_start(w, h)
        for view in self.views:
            pos = self.title_renderer.do_view_size(view, pos, w, h)

    def do_popup_view(self, view, x, y, w, h):
        print("operating on view", view)
        print("children before:", str(self.multiView.GetChildren()))
        print("client parent before:", view.client.GetParent())
        view.client.Reparent(self.multiView.hiding_space)
        print("client parent mid:", view.client.GetParent())
        view.client.Reparent(self.multiView)
        print("client parent after:", view.client.GetParent())
        print("children after:", str(self.multiView.GetChildren()))
        view.client.show_as_popup(x, y, w, h)

    def do_popup_view_msw(self, view, x, y, w, h):
        top = self.multiView
        client = view.client
        print("reparenting %s" % self.GetName())
        #top.Freeze()
        client.Reparent(top.hiding_space)
        order = [c for c in top.GetChildren() if c != client and c != top.hiding_space]
        for c in order:
            c.Reparent(top.hiding_space)
        client.Reparent(top)
        for c in order:
            c.Reparent(top)
        #top.Thaw()
        client.show_as_popup(x, y, w, h)

    if wx.Platform == "__WXMSW__":
        do_popup_view = do_popup_view_msw




########## Events ##########

class MultiSashEvent(wx.PyCommandEvent):
    """
    This event class is almost the same as `wx.SplitterEvent` except
    it adds an accessor for the sash index that is being changed.  The
    same event type IDs and event binders are used as with
    `wx.SplitterEvent`.
    """
    def __init__(self, type=wx.wxEVT_NULL, splitter=None):
        """
        Constructor.

        Used internally by wxWidgets only.

        :param `eventType`:
        :type `eventType`: EventType
        :param `splitter`:
        :type `splitter`: SplitterWindow

        """
        wx.PyCommandEvent.__init__(self, type)
        if splitter:
            self.SetEventObject(splitter)
            self.SetId(splitter.GetId())
        self.child = None
        self.replacement_child = None
        self.isAllowed = True

    def SetChild(self, child):
        """
        The MultiClient child window that is reporting the event

        :param `client`: MultiClient instance

        """
        self.child = child

    def GetChild(self):
        """
        The MultiClient child window that is reporting the event

        :param `client`: MultiClient instance

        """
        return self.child

    def SetReplacementChild(self, child):
        """
        The child window that will become the new child of the MultiClient

        :param `client`: MultiClient instance

        """
        self.replacement_child = child

    def GetReplacementChild(self):
        """
        The child window that will become the new child of the MultiClient

        :param `client`: MultiClient instance

        """
        return self.replacement_child

    def SetSashPosition(self, pos):
        """
        In the case of ``wxEVT_SPLITTER_SASH_POS_CHANGED`` events, sets the
        new sash position.

        In the case of ``wxEVT_SPLITTER_SASH_POS_CHANGING`` events, sets the
        new tracking bar position so visual feedback during dragging will
        represent that change that will actually take place. Set to -1 from
        the event handler code to prevent repositioning.

        May only be called while processing ``wxEVT_SPLITTER_SASH_POS_CHANGING``
        and ``wxEVT_SPLITTER_SASH_POS_CHANGED`` events.

        :param int `pos`: New sash position.

        """
        self.sashPos = pos

    def GetSashIdx(self):
        """
        Returns the new sash index.

        May only be called while processing ``wxEVT_SPLITTER_SASH_POS_CHANGING``
        and  ``wxEVT_SPLITTER_SASH_POS_CHANGED`` events.

        :rtype: `int`

        """
        return self.sashIdx

    def GetSashPosition(self):
        """
        Returns the new sash position.

        May only be called while processing ``wxEVT_SPLITTER_SASH_POS_CHANGING``
        and  ``wxEVT_SPLITTER_SASH_POS_CHANGED`` events.

        :rtype: `int`

        """
        return self.sashPos

    # methods from wx.NotifyEvent
    def Veto(self):
        """
        Prevents the change announced by this event from happening.

        It is in general a good idea to notify the user about the reasons
        for vetoing the change because otherwise the applications behaviour
        (which just refuses to do what the user wants) might be quite
        surprising.

        """
        self.isAllowed = False

    def Allow(self):
        """
        This is the opposite of :meth:`Veto` : it explicitly allows the
        event to be processed.

        For most events it is not necessary to call this method as the events
        are allowed anyhow but some are forbidden by default (this will be
        mentioned in the corresponding event description).

        """
        self.isAllowed = True

    def IsAllowed(self):
        """
        Returns ``True`` if the change is allowed (:meth:`Veto` hasn't been
        called) or ``False`` otherwise (if it was).

        :rtype: `bool`

        """
        return self.isAllowed


#For testing
if __name__ == '__main__':
    import sys

    class SizeReportCtrl(wx.Control):

        def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                    size=wx.DefaultSize):

            wx.Control.__init__(self, parent, id, pos, size, style=wx.NO_BORDER)
            self.Bind(wx.EVT_PAINT, self.on_paint)
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
            self.Bind(wx.EVT_SIZE, self.on_size)

        def on_paint(self, event):
            dc = wx.PaintDC(self)
            size = self.GetClientSize()

            s = "Size: %d x %d"%(size.x, size.y)

            dc.SetFont(wx.NORMAL_FONT)
            w, height = dc.GetTextExtent(s)
            height += 3
            dc.SetBrush(wx.WHITE_BRUSH)
            dc.SetPen(wx.WHITE_PEN)
            dc.DrawRectangle(0, 0, size.x, size.y)
            dc.SetPen(wx.LIGHT_GREY_PEN)
            dc.DrawLine(0, 0, size.x, size.y)
            dc.DrawLine(0, size.y, size.x, 0)
            dc.DrawText(s, (size.x-w)/2, (size.y-height*5)/2)
            pos = self.GetPosition()
            s = "Position: %d, %d" % (pos.x, pos.y)
            w, h = dc.GetTextExtent(s)
            dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*3))

        def OnEraseBackground(self, event):
            pass

        def on_size(self, event):
            size = self.GetClientSize()
            s = "Size: %d x %d"%(size.x, size.y)
            self.SetName(s)
            self.Refresh()

    def save_state(evt):
        global multi, json_text

        json_text.SetValue(multi.get_layout(True, True))

    def load_state(evt):
        global multi, json_text

        state = json_text.GetValue()
        multi.restore_layout(state)

    def find_uuid(evt):
        global multi, uuid_text

        u = uuid_text.GetValue()
        multi.focus_uuid(u)

    def replace_uuid(u):
        found = multi.find_uuid(u)
        if found is not None:
            test = EmptyChild(multi)
            found.replace(test)

    def add_control(evt):
        test = EmptyChild(multi)
        multi.add(test)

    def show_tree(evt):
        global multi

        g = multi.calc_graphviz()
        print(g)
        g.view()

    def clear_all(evt):
        global multi

        multi.remove_all()

    app = wx.App()
    frame = wx.Frame(None, -1, "Test", size=(800,400))
    multi = MultiSash(frame, pos = (0,0), size = (640,480), layout_direction=wx.HORIZONTAL)
    sizer = wx.BoxSizer(wx.VERTICAL)
    horz = wx.BoxSizer(wx.HORIZONTAL)
    horz.Add(multi, 1, wx.EXPAND)
    json_text = wx.TextCtrl(frame, -1, size=(400,400), style=wx.TE_MULTILINE)
    horz.Add(json_text, 0, wx.EXPAND)
    bsizer = wx.BoxSizer(wx.HORIZONTAL)
    btn = wx.Button(frame, -1, "Show State")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, save_state)
    btn = wx.Button(frame, -1, "Load State")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, load_state)
    uuid_text = wx.TextCtrl(frame, -1)
    bsizer.Add(uuid_text, 0, wx.EXPAND)
    btn = wx.Button(frame, -1, "Find UUID")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, find_uuid)
    btn = wx.Button(frame, -1, "Add Control")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, add_control)
    btn = wx.Button(frame, -1, "Show Tree")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, show_tree)
    btn = wx.Button(frame, -1, "Clear")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, clear_all)

    multi.use_sidebar(wx.LEFT)
    multi.use_sidebar(wx.TOP)
    multi.add_sidebar(None)
    multi.add_sidebar(None)
    multi.add_sidebar(None, side=wx.TOP)
    multi.add_sidebar(None, side=wx.TOP)

    sizer.Add(horz, 1, wx.EXPAND)
    sizer.Add(bsizer, 0, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show(True)

    try:
        state = sys.argv[1]
    except IndexError:
        pass
    else:
        text = open(state, 'r').read()
        print text
        multi.restore_layout(text)

        try:
            u = sys.argv[2]
        except IndexError:
            pass
        else:
            print("searching for %s" % u)
            wx.CallAfter(replace_uuid, u)

    # import wx.lib.inspection
    # inspect = wx.lib.inspection.InspectionTool()
    # wx.CallAfter(inspect.Show)

    app.MainLoop()
