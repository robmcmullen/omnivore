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

def opposite(dir):
    if dir == wx.HORIZONTAL:
        return wx.VERTICAL
    return wx.HORIZONTAL

SIZER_THICKNESS = 5

#----------------------------------------------------------------------

class MultiSash(wx.Window):

    wxEVT_CLIENT_CLOSE = wx.NewEventType()
    EVT_CLIENT_CLOSE = wx.PyEventBinder(wxEVT_CLIENT_CLOSE, 1)

    wxEVT_CLIENT_ACTIVATED = wx.NewEventType()
    EVT_CLIENT_ACTIVATED = wx.PyEventBinder(wxEVT_CLIENT_ACTIVATED, 1)

    def __init__(self, parent, layout_direction=wx.VERTICAL, *_args,**_kwargs):
        wx.Window.__init__(self, parent, *_args, **_kwargs)
        self.live_update_control = None
        self._defChild = EmptyChild
        self.child = MultiSplit(self, self, layout_direction)
        self.Bind(wx.EVT_SIZE,self.OnMultiSize)
        self.last_direction = wx.VERTICAL

    def OnMultiSize(self,evt):
        self.child.sizer_after = False
        self.child.sizer.Hide()
        self.child.SetSize(self.GetSize())
        self.child.do_layout()

    def UnSelect(self):
        self.child.UnSelect()

    def Clear(self):
        old = self.child
        self.child = MultiSplit(self, self, old.layout_direction)
        old.remove_all()
        self.OnMultiSize(None)

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
        self.OnMultiSize(None)
        self.child.do_layout()

    def update_captions(self):
        self.Refresh()

    def find_uuid(self, uuid):
        return self.child.find_uuid(uuid)

    def find_empty(self):
        return self.child.find_empty()

    def focus_uuid(self, uuid):
        found = self.find_uuid(uuid)
        if found:
            found.Select()

    def replace_by_uuid(self, control, u):
        found = self.find_uuid(u)
        if found is not None:
            found.replace(control, u)
            return True
        return False

    def add(self, control, u=None, layout_direction=None, use_empty=True):
        if use_empty:
            found = self.find_empty()
            if found:
                found.replace(control, u)
                return
        if layout_direction is None:
            self.last_direction = opposite(self.last_direction)
            direction = self.last_direction
        leaf = self.child.views[-1]
        self.child.split(leaf, control, u, layout_direction)


#----------------------------------------------------------------------


class HorizontalLayout(object):
    @classmethod
    def calc_size(cls, multi_split):
        w, h = multi_split.GetClientSize()

        # size used for ratio includes all the sizer widths (including the
        # extra sizer at the end that won't be displayed)
        full_size = w + SIZER_THICKNESS

        return w, h, full_size

    @classmethod
    def do_view_size(cls, view, pos, size, w, h):
        view_width = size - SIZER_THICKNESS
        view.SetSize(pos, 0, view_width, h)
        view.sizer.SetSize(pos + view_width, 0, SIZER_THICKNESS, h)

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
        w = w1 + w2 + 2 * (SIZER_THICKNESS)
        h = h1 + h2 + 2 * (SIZER_THICKNESS)
        return w, h

    def calc_splitter_pos(self, sizer_evt_x, sizer_evt_y):
        # Calculate the right/bottom location of the moving sash (for either
        # horz or vert; they don't use the other value so both can be
        # calculated in a single method). This location is used because it's
        # the point at which the ratio is calculated in the layout_calculator's
        # do_view_size method
        xs, ys = self.sizer.ClientToScreen((sizer_evt_x, sizer_evt_y))
        x, y = self.splitter.ScreenToClient((xs, ys))
        print("calc_splitter_pos: evt: %d,%d screen: %d,%d first: %d,%d" % (sizer_evt_x, sizer_evt_y, xs, ys, x, y))
        x, y = x - self.mouse_offset[0] + SIZER_THICKNESS, y - self.mouse_offset[1] + SIZER_THICKNESS
        return x, y

    def calc_extrema(self):
        self.x_min, _ = self.first.GetPosition()
        self.x_min += 2 * SIZER_THICKNESS
        x, _ = self.second.GetPosition()
        w, _ = self.second.GetSize()
        self.x_max = x + w
        self.x_max -= SIZER_THICKNESS
        print("calc_extrema: min %d, x %d, w %d, max %d" % (self.x_min, x, w, self.x_max))

    def set_ratios(self, x, y):
        r = float(x - self.zero_pos[0]) / float(self.total_width) * self.total_ratio
        print("x,r,x_min,xmax", x, r, self.x_min, self.x_max)
        if x > self.x_min and x < self.x_max:
            self.first.ratio_in_parent = r
            self.second.ratio_in_parent = self.total_ratio - r
            return True

    def do_mouse_move(self, sizer_evt_x, sizer_evt_y):
        x, y = self.calc_splitter_pos(sizer_evt_x, sizer_evt_y)
        print("do_mouse_move: sizer: %d,%d first: %d,%d" % (sizer_evt_x, sizer_evt_y, x, y))
        print(self, x, y)
        if self.set_ratios(x, y):
            self.splitter.do_layout()
        else:
            print("out of range")

class VerticalLayout(object):
    @classmethod
    def calc_size(cls, multi_split):
        w, h = multi_split.GetClientSize()

        # size used for ratio includes all the sizer widths (including the
        # extra sizer at the end that won't be displayed)
        full_size = h + SIZER_THICKNESS

        return w, h, full_size

    @classmethod
    def do_view_size(cls, view, pos, size, w, h):
        view_height = size - SIZER_THICKNESS
        view.SetSize(0, pos, w, view_height)
        view.sizer.SetSize(0, pos + view_height, w, SIZER_THICKNESS)

    @classmethod
    def calc_resizer(cls, splitter, top, sizer, bot, x, y):
        return VerticalResizer(splitter, top, sizer, bot, x, y)


class VerticalResizer(HorizontalResizer):
    def __repr__(self):
        return "%s: %s %s, ratio=%f, height=%d" % (self.__class__.__name__, self.first.debug_id, self.second.debug_id, self.total_ratio, self.total_height)

    def calc_extrema(self):
        _, self.y_min = self.first.GetPosition()
        self.y_min += 2 * SIZER_THICKNESS
        _, y = self.second.GetPosition()
        _, h = self.second.GetSize()
        self.y_max = y + h
        self.y_max -= SIZER_THICKNESS
        print("calc_extrema: min %d, y %d, h %d, max %d" % (self.y_min, y, h, self.y_max))

    def set_ratios(self, x, y):
        r = float(y - self.zero_pos[1]) / float(self.total_height) * self.total_ratio
        print("y,r,y_min,xmax", y, r, self.y_min, self.y_max)
        if y > self.y_min and y < self.y_max:
            self.first.ratio_in_parent = r
            self.second.ratio_in_parent = self.total_ratio - r
            return True


class MultiWindowBase(wx.Window):
    debug_letter = "A"

    @classmethod
    def next_debug_letter(cls):
        cls.debug_letter = chr(ord(cls.debug_letter) + 1)
        return cls.debug_letter

    def __init__(self, multiView, parent, ratio=1.0):
        wx.Window.__init__(self, parent, -1, style = wx.CLIP_CHILDREN)
        self.multiView = multiView

        self.resizer = None
        self.sizer_after = True
        self.sizer = MultiSizer(parent)
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


class MultiSplit(MultiWindowBase):
    debug_count = 1

    def __init__(self, multiView, parent, layout_direction=wx.HORIZONTAL, ratio=1.0, leaf=None, layout=None):
        MultiWindowBase.__init__(self, multiView, parent, ratio)
        self.views = []
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

    def remove(self):
        self.sizer.Destroy()
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
        subsplit = MultiSplit(self.multiView, self, opposite(self.layout_direction), leaf.ratio_in_parent, leaf)
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

    def UnSelect(self):
        for view in self.views:
            view.UnSelect()

    def destroy_leaf(self, view):
        print("destroy_leaf: view=%s views=%s self=%s parent=%s" % (view, self.views, self, self.GetParent()))
        index = self.find_leaf_index(view)  # raise IndexError
        if len(self.views) > 2:
            print("deleting > 2: %d %s" %(index, self.views))
            del self.views[index]
            r = view.ratio_in_parent / len(self.views)
            for v in self.views:
                v.ratio_in_parent += r
            view.remove()
            self.do_layout()
        elif len(self.views) == 2:
            print("deleting == 2: %d %s, parent=%s self=%s" % (index, self.views, self.GetParent(), self))
            # remove leaf, resulting in a single leaf inside a multisplit.
            # Instead of leaving it like this, move it up into the parent
            # multisplit
            del self.views[index]
            view.remove()
            if self.GetParent() == self.multiView:
                # Only one item left.
                print("  last item in %s!" % (self))
                self.views[0].ratio_in_parent = 1.0
                self.do_layout()
            else:
                print("  deleting %s from parent %s parent views=%s" % (self, self.GetParent(), self.GetParent().views))
                self.GetParent().reparent_from_splitter(self)
        else:
            # must be at the top; the final splitter.
            print("Removing the last item!", view)
            self.GetParent().Clear()

    def reparent_from_splitter(self, splitter):
        index = self.find_leaf_index(splitter)  # raise IndexError
        view = splitter.views[0]
        view.ratio_in_parent = splitter.ratio_in_parent
        view.Reparent(self)
        view.sizer.Reparent(self)
        self.views[index] = view
        splitter.remove()
        self.do_layout()


#----------------------------------------------------------------------


class MultiViewLeaf(MultiWindowBase):
    def __init__(self, multiView, parent, ratio=1.0, child=None, u=None, layout=None):
        MultiWindowBase.__init__(self, multiView, parent, ratio)
        if layout is not None:
            self.client = None
            self.restore_layout(layout)
        else:
            self.client = MultiClient(self, child, u)
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE))

    def __repr__(self):
        return "<MultiLeaf %s %f>" % (self.debug_id, self.ratio_in_parent)

    def remove(self):
        log.debug("sending close event for %s" % self.client)
        evt = MultiSashEvent(MultiSash.wxEVT_CLIENT_CLOSE, self.client)
        evt.SetChild(self.client.child)
        self.client.do_send_event(evt)
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

    def UnSelect(self):
        self.client.UnSelect()

    def get_multi_split(self):
        return self.GetParent()

    def split(self, *args, **kwargs):
        self.GetParent().split(self, *args, **kwargs)

    def destroy_leaf(self):
        self.GetParent().destroy_leaf(self)

    def do_layout(self):
        self.client.do_size_from_parent()


#----------------------------------------------------------------------


class MultiClient(wx.Window):
    use_title_bar = True
    use_close_button = True

    child_window_x = 2
    child_window_y = 2

    title_bar_height = 20
    title_bar_margin = 3
    title_bar_font = wx.NORMAL_FONT
    title_bar_font_height = None
    title_bar_x = None
    title_bar_y = None

    focused_color = wx.Colour(0x2e, 0xb5, 0xf4) # Blue
    focused_brush = None
    focused_text_color = wx.WHITE
    focused_pen = None

    unfocused_color = None
    unfocused_brush = None
    unfocused_text_color = wx.BLACK
    unfocused_pen = None

    title_font = wx.NORMAL_FONT

    close_button_size = (11, 11)

    def __init__(self, parent, child=None, uuid=None):
        w,h = parent.GetSize()
        wx.Window.__init__(self, parent, -1, pos=(0,0), size=(w,h), style = wx.CLIP_CHILDREN | wx.SUNKEN_BORDER)
        if uuid is None:
            uuid = str(uuid4())
        self.child_uuid = uuid
        self.selected = False
        self.setup_paint()

        if self.use_title_bar:
            self.title_bar = TitleBar(self)

        if child is None:
            child = parent.multiView._defChild(self)
        self.child = child
        self.child.Reparent(self)
        self.move_child()
        log.debug("Created client for %s" % self.child_uuid)

        self.Bind(wx.EVT_SET_FOCUS,self.OnSetFocus)
        self.Bind(wx.EVT_CHILD_FOCUS,self.OnChildFocus)

    def do_send_event(self, evt):
        return not self.GetEventHandler().ProcessEvent(evt) or evt.IsAllowed()

    @classmethod
    def setup_paint(cls):
        if cls.title_bar_font_height is not None:
            return

        cls.unfocused_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        cls.focused_brush = wx.Brush(cls.focused_color, wx.SOLID)
        cls.unfocused_brush = wx.Brush(cls.unfocused_color, wx.SOLID)
        cls.focused_pen = wx.Pen(cls.focused_text_color)
        cls.unfocused_pen = wx.Pen(cls.unfocused_text_color)
        cls.focused_fill = wx.Brush(cls.focused_text_color, wx.SOLID)
        cls.unfocused_fill = wx.Brush(cls.unfocused_text_color, wx.SOLID)

        dc = wx.MemoryDC()
        dc.SetFont(cls.title_bar_font)
        cls.title_bar_font_height = max(dc.GetCharHeight(), 2)
        cls.title_bar_x = cls.title_bar_margin
        cls.title_bar_y = (cls.title_bar_height - cls.title_bar_font_height) // 2

    def get_paint_tools(self):
        if self.selected:
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

    @property
    def title(self):
        leaf = self.GetParent()  # parent is always Leaf
        v = "%s " % leaf.debug_id
        depth = 0
        top = leaf.multiView
        while leaf != top:
            depth += 1
            leaf = leaf.GetParent()
        return "%s-%d: %s" % (v, depth, self.child.GetName())

    def UnSelect(self):
        if self.selected:
            self.selected = False
            self.Refresh()

    def Select(self):
        self.GetParent().multiView.UnSelect()
        self.selected = True
        evt = MultiSashEvent(MultiSash.wxEVT_CLIENT_ACTIVATED, self)
        evt.SetChild(self.child)
        self.do_send_event(evt)
        self.child.SetFocus()
        self.Refresh()

    def do_size_from_parent(self):
        w,h = self.GetParent().GetClientSize()
        self.SetSize((w, h))
        # print("in client %s:" % self.GetParent().debug_id, w, h)
        if self.use_title_bar:
            self.title_bar.SetSize((w, self.title_bar_height))
            self.child.SetSize((w, h - self.title_bar_height))
        else:
            self.child.SetSize((w - 2 * self.child_window_x, h - 2 * self.child_window_y))

    def replace(self, child, u=None):
        if self.child:
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
        if self.use_title_bar:
            self.title_bar.Move(0, 0)
            self.child.Move(0, self.title_bar_height)
        else:
            self.child.Move(self.child_window_x, self.child_window_y)

    def OnSetFocus(self,evt):
        self.Select()

    def OnChildFocus(self,evt):
        self.OnSetFocus(evt)
##        from Funcs import FindFocusedChild
##        child = FindFocusedChild(self)
##        child.Bind(wx.EVT_KILL_FOCUS,self.OnChildKillFocus)


class TitleBar(wx.Window):
    def __init__(self, parent):
        wx.Window.__init__(self, parent, -1)
        self.client = parent

        button_index = 0
        self.buttons = []
        button_index += 1
        self.buttons.append(TitleBarCloser(self, button_index))
        top = self.client.GetParent().multiView
        button_index += 1
        self.buttons.append(TitleBarHSplitNewBot(self, button_index))
        button_index += 1
        self.buttons.append(TitleBarVSplitNewRight(self, button_index))

        self.SetBackgroundColour(wx.RED)
        self.hide_buttons()

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LEAVE_WINDOW,self.OnLeave)
        self.Bind(wx.EVT_ENTER_WINDOW,self.OnEnter)

    def draw_title_bar(self, dc):
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetPen(wx.TRANSPARENT_PEN)
        brush, _, _, text, textbg = self.client.get_paint_tools()
        dc.SetBrush(brush)

        w, h = self.GetSize()
        dc.SetFont(wx.NORMAL_FONT)
        dc.SetTextBackground(textbg)
        dc.SetTextForeground(text)
        dc.DrawRectangle(0, 0, w, h)
        dc.DrawText(self.client.title, self.client.title_bar_x, self.client.title_bar_y)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.draw_title_bar(dc)

    def OnSize(self, evt):
        for button in self.buttons:
            x, y, w, h = button.CalcSizePos(self)
            button.SetSize(x, y, w, h)

    def hide_buttons(self):
        for b in self.buttons[1:]:
            if b: b.Hide()

    def show_buttons(self):
        for b in self.buttons[1:]:
            if b: b.Show()

    def OnEnter(self, evt):
        self.show_buttons()

    def OnLeave(self, evt):
        # check if left the window but still in the title bar, otherwise will
        # enter an endless cycle of leave/enter events as the buttons due to
        # the show/hide of the buttons being right under the cursor
        x, y = evt.GetPosition()
        w, h = self.GetSize()
        if x <= 0 or x >= w or y <= 0 or y >= h:
            self.hide_buttons()


#----------------------------------------------------------------------


class MultiSizer(wx.Window):
    def __init__(self, parent, layout_direction=wx.HORIZONTAL):
        wx.Window.__init__(self, parent, -1, style = wx.CLIP_CHILDREN)

        self.Bind(wx.EVT_LEAVE_WINDOW,self.OnLeave)
        self.Bind(wx.EVT_ENTER_WINDOW,self.OnEnter)

        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE))
        self.SetBackgroundColour(wx.WHITE)

    def OnLeave(self,evt):
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def OnEnter(self,evt):
        if self.GetParent().layout_direction == wx.HORIZONTAL:
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))


#----------------------------------------------------------------------


class TitleBarButton(wx.Window):
    def __init__(self, parent, order):
        self.order = order
        self.title_bar = parent
        self.client = parent.GetParent()
        self.leaf = self.client.GetParent()
        x,y,w,h = self.CalcSizePos(parent)
        wx.Window.__init__(self,id = -1,parent = parent,
                          pos = (x,y),
                          size = (w,h),
                          style = wx.CLIP_CHILDREN)

        self.down = False
        self.entered = False

        self.Bind(wx.EVT_LEFT_DOWN,self.OnPress)
        self.Bind(wx.EVT_LEFT_UP,self.OnRelease)
        self.Bind(wx.EVT_PAINT,self.OnPaint)
        self.Bind(wx.EVT_LEAVE_WINDOW,self.OnLeave)
        self.Bind(wx.EVT_ENTER_WINDOW,self.OnEnter)

    def OnPress(self,evt):
        self.down = True
        evt.Skip()

    def OnRelease(self,evt):
        if self.down and self.entered:
            wx.CallAfter(self.title_bar.hide_buttons)
            self.do_action(evt)
        else:
            evt.Skip()
        self.down = False

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        size = self.GetClientSize()

        bg_brush, pen, fg_brush, _, _ = self.client.get_paint_tools()
        self.draw_button(dc, size, bg_brush, pen, fg_brush)

    def draw_button(self, dc, size, bg_brush, pen, fg_brush):
        print("draw")

    def OnLeave(self,evt):
        self.entered = False

    def OnEnter(self,evt):
        self.entered = True

    def do_action(self, evt):
        pass

    def CalcSizePos(self, parent):
        pw, ph = parent.GetClientSize()
        w, h = self.client.close_button_size
        x = pw - (w - self.client.title_bar_margin) * self.order * 2
        y = (self.client.title_bar_height - h) // 2
        return (x, y, w, h)

    def OnSize(self,evt):
        x,y,w,h = self.CalcSizePos(self.title_bar)
        self.SetSize(x,y,w,h)


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
            self.leaf.destroy_leaf()

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
        print(self.client)
        print(self.leaf)
        print("HORZ")
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
        print(self.client)
        print(self.leaf)
        print("VERT")
        self.leaf.split(layout_direction=wx.VERTICAL)

#----------------------------------------------------------------------


class EmptyChild(wx.Window):
    multisash2_empty_control = True

    def __init__(self,parent):
        wx.Window.__init__(self,parent,-1, style = wx.CLIP_CHILDREN)




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
        self.isAllowed = True

    def SetChild(self, child):
        """
        The MultiClient that is reporting the event

        :param `client`: MultiClient instance

        """
        self.child = child

    def GetChild(self):
        """
        The MultiClient that is reporting the event

        :param `client`: MultiClient instance

        """
        return self.child

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
            self.Bind(wx.EVT_PAINT, self.OnPaint)
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
            self.Bind(wx.EVT_SIZE, self.OnSize)

        def OnPaint(self, event):
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

        def OnSize(self, event):
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

        multi.Clear()

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
