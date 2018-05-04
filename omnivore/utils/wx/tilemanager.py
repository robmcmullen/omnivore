# TileManager
# 
# MDI manager using tile layout for the main area and sidebars for pop-out
# windows. The user can split tiles either horizontally or vertically, and drag
# tiles to and from sidebars. Up to 4 sidebars are supported, at most one at
# each of the 4 cardinal directions.
#
# This is a very very large modification of the MultiSash control included in
# the wxPython distribution. It was written by Gerrit van Dyk and Jeff
# Grimmett. It has almost entirely diverged from the original, but the code
# structure remains largely the same.
#
# My coding conventions:
#
# constants:                  ALL_UPPERCASE
# classes:                    CamelCase
# normal methods:             underscore_separated
# wxPython override methods:  CamelCase
#
# method names:
#    get_*:       fast access to internal state that may include some minimal
#                   computation, but no side effects
#    set_*:       updates state of object (i.e.: side effects), no return value
#    do_*:        updates UI or state of other objects, no return value
#    calc_*:      returns a value, possibly heavyweight calculations involved,
#                   no side effects
#    on_*:        wxPython event handlers
#
# License:      wxWindows license
# Author:       Rob McMullen <feedback@playermissile.com>
# Copyright:    2018

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

side_to_direction = {
    wx.LEFT: wx.HORIZONTAL,
    wx.RIGHT: wx.HORIZONTAL,
    wx.TOP: wx.VERTICAL,
    wx.BOTTOM: wx.VERTICAL,
    }

pretty_direction = {
    wx.LEFT: "left",
    wx.RIGHT: "right",
    wx.TOP: "top",
    wx.BOTTOM: "bottom",
    }


class DockTarget(object):
    @classmethod
    def calc_bitmap_of_window(cls, win):
        # modified from a snipped that creates a screenshot of the entire desktop
        # see http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3575899
        # created by Andrea Gavana
        rect = win.GetRect()

        sx, sy = win.ClientToScreen((0, 0))
        rect.x = sx
        rect.y = sy

        dcScreen = wx.ScreenDC()

        try:
            # print("trying screenDC subbitmap: %s" % str(rect))
            drag_bitmap = dcScreen.GetAsBitmap().GetSubBitmap(rect)
        except wx.wxAssertionError:
            # print("creating bitmap manually")
            drag_bitmap = wx.Bitmap(rect.width, rect.height)
            memDC = wx.MemoryDC()
            memDC.SelectObject(drag_bitmap)
            memDC.Blit(0, 0, rect.width, rect.height, dcScreen, sx, sy)
            memDC.SelectObject(wx.NullBitmap)  # sync data to bitmap
        return rect, drag_bitmap


    class BitmapPopup(wx.PopupWindow):
        """Adds a bit of text and mouse movement to the wx.PopupWindow"""
        def __init__(self, parent, pos, style=wx.SIMPLE_BORDER):
            wx.PopupWindow.__init__(self, parent, style)
            self.SetBackgroundColour("CADET BLUE")
            
            rect, self.bitmap = DockTarget.calc_bitmap_of_window(parent)
            x, y = parent.ClientToScreen(pos)
            rect.x = x
            rect.y = y
            self.SetSize(rect)
            self.Show()

            self.Bind(wx.EVT_PAINT, self.on_paint)

        def on_paint(self, evt):
            dc = wx.PaintDC(self)
            dc.DrawBitmap(self.bitmap, 0, 0)


    class HitTestManager(object):
        def __init__(self, event_window, leafs):
            self.start_hit_test(event_window, leafs)

        def start_hit_test(self, event_window, leafs):
            self.create_rectangles(event_window, leafs)

        def create_rectangles(self, event_window, leafs):
            rects = []
            for leaf in leafs:
                rects.append((leaf, leaf.calc_rectangle_relative_to(event_window)))
            self.rectangles = rects

        def in_rect(self, pos):
            for dock_info in self.rectangles:
                leaf, rect = dock_info
                # print("checking %s in rect %s" % (pos, rect))
                if rect.Contains(pos):
                    break
            else:
                # print("NOT IN RECT")
                leaf = None
            return leaf


    class MenuHitTestManager(HitTestManager):
        def __init__(self, tile_mgr):
            leafs = []
            for s in tile_mgr.sidebars:
                leafs.extend(s.views)
            DockTarget.HitTestManager.__init__(self, tile_mgr, leafs)


    class DockingRectangleHandler(object):
        def __init__(self):
            self.use_transparency = True
            self.overlay = None
            self.docking_rectangles = []
            self.event_window = None
            self.source_leaf = None
            self.popup_window = None
            self.background_bitmap = None
            self.current_dock = None
            self.pen = wx.Pen(wx.BLUE)
            brush_color = wx.Colour(0xb0, 0xb0, 0xff, 0x80)
            self.brush = wx.Brush(brush_color)

        @property
        def is_active(self):
            return self.popup_window is not None

        def start_docking(self, event_window, source_leaf, evt):
            # Capture the mouse and save the starting posiiton for the rubber-band
            event_window.CaptureMouse()
            event_window.SetFocus()
            self.current_dock = None
            self.event_window = event_window
            self.source_leaf = source_leaf
            self.popup_window = DockTarget.BitmapPopup(source_leaf, evt.GetPosition())
            _, self.background_bitmap = DockTarget.calc_bitmap_of_window(event_window)
            self.overlay = wx.Overlay()
            self.overlay.Reset()
            self.create_docking_rectangles()

        def create_docking_rectangles(self):
            rects = []
            for leaf in self.event_window.calc_dock_targets():
                rects.extend(leaf.calc_docking_rectangles(self.event_window, self.source_leaf))
            self.docking_rectangles = rects

        def in_rect(self, pos):
            for dock_info in self.docking_rectangles:
                _, _, rect = dock_info
                print("checking %s in rect %s" % (pos, rect))
                if rect.Contains(pos):
                    break
            else:
                print("NOT IN RECT")
                dock_info = None
            return dock_info

        def process_dragging(self, evt):
            pos = evt.GetPosition()

            self.current_dock = self.in_rect(pos)

            dc = wx.ClientDC(self.event_window)
            odc = wx.DCOverlay(self.overlay, dc)
            odc.Clear()

            if wx.Platform != "__WXMAC__":
                if self.use_transparency:
                    dc = wx.GCDC(dc)        # Mac already using GCDC

                # Win & linux need this hack: copy background to overlay; otherwise
                # the overlay seems to be black? I don't know what's up with this
                # platform difference
                dc.DrawBitmap(self.background_bitmap, 0, 0)

            if self.current_dock is not None:
                dc.SetPen(self.pen)
                dc.SetBrush(self.brush)
                dc.DrawRectangle(self.current_dock[2])

            pos = self.event_window.ClientToScreen(pos)
            self.popup_window.SetPosition(pos)

            del odc  # Make sure the odc is destroyed before the dc is.


        def cleanup_docking(self, evt):
            if self.event_window.HasCapture():
                self.event_window.ReleaseMouse()
            pos = evt.GetPosition()

            # When the mouse is released we reset the overlay and it
            # restores the former content to the window.
            dc = wx.ClientDC(self.event_window)
            odc = wx.DCOverlay(self.overlay, dc)
            odc.Clear()
            del odc
            self.overlay.Reset()
            self.overlay = None

            self.popup_window.Destroy()
            self.popup_window = None
            self.event_window.Refresh()  # Force redraw
            self.event_window = None
            leaf = self.source_leaf
            self.source_leaf = None

            if self.current_dock is not None:
                leaf_to_split, side, _ = self.current_dock
            else:
                leaf_to_split = None
                side = None
            self.current_dock = None
            self.docking_rectangles = None
            return leaf, leaf_to_split, side


    def remove_client(self):
        if self.client is not None:
            self.client.remove()
            self.client = None

    def detach_client(self):
        client = self.client
        if client is not None:
            client.Reparent(self.tile_mgr.hiding_space)
        self.client = None
        return client

    def attach_client(self, client):
        self.client = client
        self.client.set_leaf(self)

    def reparent_client(self, client):
        client.Reparent(self)

    def detach(self):
        self.GetParent().detach_leaf(self)

    def find_uuid(self, uuid):
        if uuid == self.client.child_uuid:
            log.debug("find_uuid: found %s in %s" % (uuid, self.client.child.GetName()))
            return self.client
        log.debug("find_uuid: skipping %s in %s" % (self.client.child_uuid, self.client.child.GetName()))
        return None

    def find_control(self, control):
        if control == self.client.child:
            log.debug("find_control: found %s in %s" % (control, self.client.child.GetName()))
            return self.client
        log.debug("find_control: skipping %s in %s" % (self.client.child, self.client.child.GetName()))
        return None

    def find_empty(self):
        if hasattr(self.client.child, "tile_manager_empty_control") and self.client.child.tile_manager_empty_control:
            log.debug("find_empty: found %s" % (self.client.child.GetName()))
            return self.client
        log.debug("find_empty: skipping %s in %s" % (self.client.child_uuid, self.client.child.GetName()))
        return None

    def iter_leafs(self):
        log.debug("iter_leafs: found %s" % (self.client.child.GetName()))
        yield self

    def calc_rectangle_relative_to(self, event_window):
        r = self.GetClientRect()
        sx, sy = self.ClientToScreen((r.x, r.y))
        px, py = event_window.ScreenToClient((sx, sy))
        return wx.Rect(px, py, r.width, r.height)

    def calc_docking_rectangles(self, event_window, source_leaf):
        rects = []
        r = self.calc_rectangle_relative_to(event_window)
        if source_leaf == self:
            # dummy rectangle for feedback, but can't drop on itself
            rects.append((None, None, r))
        else:
            w = r.width // 4
            h = r.height // 4
            ty = r.y + r.height - h
            rx = r.x + r.width - w
            rects.append((self, wx.LEFT, wx.Rect(r.x, r.y, w, r.height)))
            rects.append((self, wx.TOP, wx.Rect(r.x, r.y, r.width, h)))
            rects.append((self, wx.RIGHT, wx.Rect(rx, r.y, w, r.height)))
            rects.append((self, wx.BOTTOM, wx.Rect(r.x, ty, r.width, h)))
        return rects

    def process_dock_target(self, leaf, side):
        print("inserting leaf=%s, splitting leaf=%s on side=%s" % (leaf, self, side))
        leaf.detach()
        self.tile_mgr.do_layout()
        self.split_side(new_side=side, view=leaf)


class TileManager(wx.Window):
    _debug_count = 1

    sizer_thickness = 5

    wxEVT_CLIENT_CLOSE = wx.NewEventType()
    EVT_CLIENT_CLOSE = wx.PyEventBinder(wxEVT_CLIENT_CLOSE, 1)

    wxEVT_CLIENT_REPLACE = wx.NewEventType()
    EVT_CLIENT_REPLACE = wx.PyEventBinder(wxEVT_CLIENT_REPLACE, 1)

    wxEVT_CLIENT_ACTIVATED = wx.NewEventType()
    EVT_CLIENT_ACTIVATED = wx.PyEventBinder(wxEVT_CLIENT_ACTIVATED, 1)

    wxEVT_LAYOUT_CHANGED = wx.NewEventType()
    EVT_LAYOUT_CHANGED = wx.PyEventBinder(wxEVT_LAYOUT_CHANGED, 1)

    class HidingSpace(wx.Window):
        can_take_leaf_focus = False
        is_sidebar = False

        def set_chrome(self, client):
            pass

        def reparent_client(self, client):
            client.Reparent(self)

    def __init__(self, parent, layout_direction=wx.HORIZONTAL, name="top", *_args, **_kwargs):
        wx.Window.__init__(self, parent, name=name, *_args, **_kwargs)
        self.debug_id = "root"
        self.set_defaults()
        self._defChild = EmptyChild
        self.child = TileSplit(self, self, layout_direction)
        self.hiding_space = TileManager.HidingSpace(self, -1, name="reparenting hiding space")
        self.hiding_space.Hide()
        self.sidebars = []
        self.header = None
        self.footer = None
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_KILL_FOCUS, self.on_kill_focus)
        self.current_leaf_focus = None
        self.previous_leaf_focus = None
        self.dock_handler = DockTarget.DockingRectangleHandler()
        self.menu_popdown_mode = False
        self.menu_hit_test = None
        self.menu_currently_displayed = None

    def set_defaults(self):
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

        self.mouse_delta_for_window_move = 4

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

    def send_layout_changed_event(self):
        evt = TileManagerEvent(TileManager.wxEVT_LAYOUT_CHANGED, self)
        self.GetEventHandler().ProcessEvent(evt)

    def do_layout(self, layout_changed=False):
        self.child.sizer_after = False
        self.child.sizer.Hide()
        x, y = 0, 0
        w, h = self.GetSize()
        x, y, w, h = self.set_header_size_inside(x, y, w, h)
        x, y, w, h = self.set_footer_size_inside(x, y, w, h)
        for sidebar in self.sidebars:
            x, y, w, h = sidebar.set_size_inside(x, y, w, h)
            sidebar.do_layout()
        self.child.SetSize(x, y, w, h)
        self.child.do_layout()
        if layout_changed:
            self.send_layout_changed_event()

    def set_header_size_inside(self, x, y, w, h):
        if self.header is not None and self.header.IsShown():
            _, hh = self.header.GetBestSize()
            self.header.SetSize(x, y, w, hh)
            y += hh
            h -= hh
        return x, y, w, h

    def set_footer_size_inside(self, x, y, w, h):
        if self.footer is not None and self.footer.IsShown():
            _, hh = self.footer.GetBestSize()
            self.footer.SetSize(x, y + h - hh, w, hh)
            h -= hh
        return x, y, w, h

    def calc_usable_rect(self):
        x, y = self.child.GetPosition()
        w, h = self.child.GetSize()
        return x, y, w, h

    def set_leaf_focus(self, leaf):
        if self.menu_popdown_mode:
            # MacOS sends a focus event when the menu is visible, before the
            # user explicitly focuses it. So, just ignore when the menu is
            # active.
            return
        last_focus = self.current_leaf_focus
        if not leaf:
            # no previous leaf or the leaf has been deleted; need to find a new
            # one
            print("can't focus on leaf %s; finding first suitable leaf" % leaf)
            for leaf in self.iter_leafs():
                if leaf.can_take_leaf_focus:
                    break
            else:
                leaf = None
        self.current_leaf_focus = leaf
        print("set_leaf_focus: current=%s last=%s menu=%s is_menu=%s" % (repr(leaf), repr(last_focus), repr(self.menu_currently_displayed), self.current_leaf_focus == self.menu_currently_displayed))
        if self.menu_currently_displayed is not None and self.menu_currently_displayed != leaf:
            self.menu_currently_displayed.close_menu()
            self.menu_currently_displayed = None
        if last_focus:
            print("CLEARING LAST LEAF", last_focus)
            last_focus.Refresh()
        if leaf:
            if leaf == last_focus:
                print("SAME FOCUS!!!!!!")
            else:
                leaf.client.set_focus()
                print("REFRESHING CURRENT LEAF", leaf)
                leaf.Refresh()
            if leaf.can_take_leaf_focus:
                self.previous_leaf_focus = leaf

    def force_clear_sidebar(self):
        if self.menu_currently_displayed is not None:
            self.menu_currently_displayed.close_menu()
            self.menu_currently_displayed = None
            self.set_leaf_focus(self.previous_leaf_focus)

    def restore_last_main_window_focus(self):
        print("restoring from", str(self.previous_leaf_focus))
        if self.previous_leaf_focus:
            self.previous_leaf_focus.client.set_focus()
            return
        else:
            for leaf in self.iter_leafs():
                if not leaf.is_sidebar:
                    leaf.client.set_focus()
                    return
        # nothing left?
        self.current_leaf_focus = None

    def is_leaf_focused(self, window):
        c = self.current_leaf_focus
        return c is not None and (c == window or c.client == window)

    def clear_main_splitter(self):
        old = self.child
        self.child = TileSplit(self, self, old.layout_direction)
        old.remove_all()
        for sidebar in self.sidebars:
            sidebar.force_popup_to_top_of_stacking_order()
        self.do_layout(layout_changed=True)

    def remove_all(self):
        self.replace_all()

    def replace_all(self, layout=None, sidebar_layout=[]):
        old = self.child
        self.child = TileSplit(self, self, old.layout_direction, layout=layout)
        old.remove_all()
        for sidebar in self.sidebars:
            sidebar.remove_all()
        self.sidebars = []
        for d in sidebar_layout:
            self.use_sidebar(layout=d)
        self.do_layout(layout_changed=True)

    def calc_layout(self, to_json=False, pretty=False):
        d = {'tile_manager': self.child.calc_layout()}
        s = []
        for sidebar in self.sidebars:
            s.append(sidebar.calc_layout())
        d['sidebars'] = s
        if to_json:
            if pretty:
                d = json.dumps(d, sort_keys=True, indent=4)
            else:
                d = json.dumps(d)
        return d

    def restore_layout(self, d):
        try:
            layout = d['tile_manager']
        except KeyError:
            log.error("No tile manager layout found")
            return
        except TypeError:
            try:
                d = json.loads(d)
            except ValueError, e:
                log.error("Error loading layout: %s" % e.message)
                return
            layout = d['tile_manager']
        try:
            self.replace_all(layout, d.get('sidebars', []))
        except KeyError, e:
            log.error("Error loading layout: missing key %s. Restoring previous layout." % e.message)
        print("SIDEBARS!", self.sidebars)

    def update_captions(self):
        for sidebar in self.sidebars:
            sidebar.do_layout()
        self.Refresh()

    def find_uuid(self, uuid):
        found = self.child.find_uuid(uuid)
        if not found:
            for sidebar in self.sidebars:
                found = sidebar.find_uuid(uuid)
                if found:
                    break
        return found

    def find_empty(self):
        found = self.child.find_empty()
        if not found:
            for sidebar in self.sidebars:
                found = sidebar.find_empty()
                if found:
                    break
        return found

    def find_control(self, control):
        found = self.child.find_control(control)
        if not found:
            for sidebar in self.sidebars:
                found = sidebar.find_control(control)
                if found:
                    break
        return found

    def iter_leafs(self):
        for leaf in self.child.iter_leafs():
            yield leaf

    def find(self, item):
        if hasattr(item, 'SetPosition'):
            found = self.find_control(item)
        else:
            found = self.find_uuid(item)
        return found

    def in_sidebar(self, control):
        found = self.find(control).leaf
        return found.is_sidebar if found is not None else False

    def force_focus(self, item):
        found = self.find(item)
        if found:
            print("FOCUS TO:", found)
            self.set_leaf_focus(found.leaf)

    def replace_by_uuid(self, control, u, **kwargs):
        found = self.find_uuid(u)
        if found is not None:
            found.replace(control, u, **kwargs)
            return True
        return False

    def add(self, control, u=None, new_side=wx.LEFT, use_empty=True, sidebar=False, **kwargs):
        if not self.replace_by_uuid(control, u, **kwargs):
            if use_empty:
                found = self.find_empty()
                if found:
                    found.replace(control, u, **kwargs)
                    return
            if sidebar:
                self.add_sidebar(control, u, new_side, **kwargs)
            else:
                self.add_split(control, u, new_side, use_empty, **kwargs)

    def add_split(self, control, u=None, new_side=wx.LEFT, use_empty=True, **kwargs):
        leaf = self.child.views[-1]
        self.child.split(leaf, control, u, new_side, **kwargs)

    def use_sidebar(self, side=wx.LEFT, layout=None):
        if layout is not None:
            sidebar = Sidebar(self, None, layout=layout)
            self.sidebars.append(sidebar)
            # do_layout will be called after all sidebars loaded
        else:
            try:
                sidebar = self.find_sidebar(side)
            except ValueError:
                sidebar = Sidebar(self, side)
                self.sidebars.append(sidebar)
                self.do_layout(layout_changed=True)
        return sidebar

    def find_sidebar(self, side=wx.LEFT):
        if side == wx.DEFAULT and len(self.sidebars) > 0:
            return self.sidebars[0]
        for sidebar in self.sidebars:
            if side == sidebar.side:
                return sidebar
        raise ValueError("No sidebar on side")

    def remove_sidebar(self, side_or_sidebar):
        try:
            sidebar = self.find_sidebar(side_or_sidebar)
        except ValueError:
            pass
        try:
            sidebar = side_or_sidebar
            sidebar.remove_all()
        except AttributeError:
            log.error("No sidebar on %s so can't remove it!" % pretty_direction(side_or_sidebar))
        else:
            self.sidebars.remove(sidebar)
            self.do_layout(layout_changed=True)

    def add_sidebar(self, control, u=None, side=wx.LEFT, **kwargs):
        sidebar = self.use_sidebar(side)
        client = TileClient(None, control, u, tile_mgr=self, **kwargs)
        sidebar.add_client(client)

    def add_header(self, control):
        if self.header is not None:
            self.header.Destroy()
        self.header = control
        self.do_layout(layout_changed=True)

    def add_footer(self, control):
        if self.footer is not None:
            self.footer.Destroy()
        self.footer = control
        self.do_layout(layout_changed=True)

    def show_footer(self, state=True):
        self.footer.Show(state)
        self.do_layout()

    def show_header(self, state=True):
        self.header.Show(state)
        self.do_layout()

    def calc_graphviz(self):
        from graphviz import Digraph
        g = Digraph('tile_manager', filename='tile_manager.dot')
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

    #### Dynamic positioning of child windows

    def on_kill_focus(self, evt):
        # FIXME: MacOS doesn't get this event
        if not self.menu_popdown_mode:
            log.debug("kill focus")
            self.force_clear_sidebar()
        else:
            log.debug("Skipping kill focus because we're in a menu event")
        evt.Skip()

    def on_start_menu(self, menu_item, evt):
        self.menu_popdown_mode = True
        self.menu_hit_test = DockTarget.MenuHitTestManager(self)
        if self.menu_currently_displayed == menu_item:
            print("START! already showing menu %s" % menu_item)
        else:
            if self.menu_currently_displayed is not None:
                print("START! closing currently shown menu %s" % self.menu_currently_displayed)
                self.menu_currently_displayed.close_menu()
            else:
                print("START! showing menu %s" % menu_item)
            self.menu_currently_displayed = menu_item
            menu_item.open_menu()
        self.CaptureMouse()

    def on_motion(self, evt):
        if self.dock_handler.is_active:
            pos = evt.GetPosition()
            print("docking in main window!", pos)
            self.dock_handler.process_dragging(evt)
        elif self.menu_popdown_mode:
            pos = evt.GetPosition()
            menu_item = self.menu_hit_test.in_rect(pos)
            if menu_item is None:
                log.debug("not over any menu; leaving menu displayed %s" % self.menu_currently_displayed)
            elif self.menu_currently_displayed != menu_item:
                if self.menu_currently_displayed is not None:
                    self.menu_currently_displayed.close_menu()
                self.menu_currently_displayed = menu_item
                menu_item.open_menu()
                log.debug("changing menu to %s" % menu_item)
            else:
                log.debug("still displaying same menu %s" % menu_item)

    def on_left_up(self, evt):
        if self.dock_handler.is_active:
            leaf, leaf_to_split, side = self.dock_handler.cleanup_docking(evt)
            if leaf_to_split is not None:
                if leaf == leaf_to_split:
                    print("nop: splitting and inserting same leaf")
                else:
                    leaf_to_split.process_dock_target(leaf, side)
        elif self.menu_popdown_mode:
            leave_open = False
            menu_item = self.menu_currently_displayed
            if menu_item is not None:
                pos = evt.GetPosition()
                if self.menu_hit_test.in_rect(pos) is not None:
                    print("FINISH IN MENU ITEM! change to popdown mode that doesn't need the mouse button down!")
                    return
                elif menu_item.actual_popup.GetScreenRect().Contains(self.ClientToScreen(pos)):
                    print("FINISH IN MENU! leave open!")
                    leave_open = True

            if self.HasCapture():
                self.ReleaseMouse()
            self.menu_popdown_mode = False
            self.menu_hit_test = None
            if leave_open:
                print("FINISH! setting focus to menu %s" % menu_item)
                #menu_item.client.on_set_focus(None)
                self.set_leaf_focus(menu_item)
            else:
                print("FINISH! menu closed")
                self.force_clear_sidebar()

    def start_child_window_move(self, source_leaf, evt):
        self.dock_handler.start_docking(self, source_leaf, evt)

    def calc_dock_targets(self):
        targets = []
        missing_sidebars = set([wx.LEFT, wx.RIGHT, wx.TOP, wx.BOTTOM])
        for sidebar in self.sidebars:
            print("checking sidebar %s" % sidebar)
            sidebar.calc_dock_targets(targets)
            missing_sidebars.remove(sidebar.side)
        print("dock targets from sidebars: %s" % str(targets))
        for side in missing_sidebars:
            targets.append(MissingSidebarDock(self, side))
            print("dock targets for missing sidebar: %s" % str(MissingSidebarDock))
        self.child.calc_dock_targets(targets)
        print("dock targets: %s" % str(targets))
        return targets

    def on_char_hook(self, evt):
        """
        Keyboard handler to process global keys before they are handled by any
        children. Unless evt.Skip is called, the character event propagation
        stops here.
        """
        key = evt.GetKeyCode()
        log.debug("on_char_hook evt=%s" % key)

        skip = True
        if key == wx.WXK_ESCAPE:
            if self.menu_currently_displayed is not None:
                log.debug("on_char_hook: popping down active sidebar %s" % self.menu_currently_displayed)
                self.force_clear_sidebar()
                skip = False
        if skip:
            evt.Skip()


class EmptyChild(wx.Window):
    tile_manager_empty_control = True

    def __init__(self,parent):
        wx.Window.__init__(self,parent,-1, name=TileManager.debug_window_name("blank"), style=wx.CLIP_CHILDREN)
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INACTIVECAPTION))
        self.SetLabel("")

    def DoGetBestClientSize(self):
        return wx.Size(250, 300)


########## Splitter ##########

class TileWindowBase(wx.Window):
    can_take_leaf_focus = False

    class TileSizer(wx.Window):
        def __init__(self, parent, tile_mgr):
            wx.Window.__init__(self, parent, -1, style = wx.CLIP_CHILDREN, name=TileManager.debug_window_name("TileSizer"))
            self.tile_mgr = tile_mgr
            self.num_grips = 5
            self.grip_delta_pixels = 4

            self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
            self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
            self.Bind(wx.EVT_PAINT, self.on_paint)

            color = self.tile_mgr.empty_color
            self.SetBackgroundColour(color)

        def on_leave(self,evt):
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

        def on_enter(self,evt):
            if self.GetParent().layout_direction == wx.HORIZONTAL:
                self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
            else:
                self.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))

        def on_paint(self, evt):
            m = self.tile_mgr
            if m == self.GetParent():
                # top level can't be resized! It fills the space
                return
            dc = wx.PaintDC(self)
            size = self.GetClientSize()
            p = wx.Pen(m.border_color)
            dc.SetPen(p)
            if self.GetParent().layout_direction == wx.HORIZONTAL:
                x = 0
                y = size.y // 2
                w = size.x
                dy = self.grip_delta_pixels
                dc.DrawLine(x, y, x + w, y)
                dc.DrawLine(x, y + dy, x + w, y + dy)
                dc.DrawLine(x, y - dy, x + w, y - dy)
                dc.DrawLine(x, y + dy + dy, x + w, y + dy + dy)
                dc.DrawLine(x, y - dy - dy, x + w, y - dy - dy)
            else:
                x = size.x // 2
                y = 0
                h = size.y
                dx = self.grip_delta_pixels
                dc.DrawLine(x, y, x, y + h)
                dc.DrawLine(x + dx, y, x + dx, y + h)
                dc.DrawLine(x - dx, y, x - dx, y + h)
                dc.DrawLine(x + dx + dx, y, x + dx + dx, y + h)
                dc.DrawLine(x - dx - dx, y, x - dx - dx, y + h)

    @classmethod
    def next_debug_letter(cls):
        cls.debug_letter = chr(ord(cls.debug_letter) + 1)
        return cls.debug_letter

    def __init__(self, tile_mgr, parent, ratio=1.0, name="TileWindowBase"):
        wx.Window.__init__(self, parent, -1, style = wx.CLIP_CHILDREN, name=TileManager.debug_window_name(name))
        self.tile_mgr = tile_mgr

        self.resizer = None
        self.sizer_after = True
        self.sizer = TileWindowBase.TileSizer(parent, tile_mgr)
        self.sizer.Bind(wx.EVT_MOTION, self.on_motion)
        self.sizer.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.sizer.Bind(wx.EVT_LEFT_UP, self.on_left_up)

        self.ratio_in_parent = ratio
        # self.SetBackgroundColour(wx.RED)

    @property
    def debug_id(self):
        return self.GetName()

    def reparent_to(self, viewer, ratio=None):
        self.Reparent(viewer)
        self.sizer.Reparent(viewer)
        if ratio is not None:
            self.ratio_in_parent = ratio

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
            self.tile_mgr.send_layout_changed_event()
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

    def find_control(self, control):
        for view in self.views:
            found = view.find_control(control)
            if found is not None:
                return found
        return None

    def find_empty(self):
        for view in self.views:
            found = view.find_empty()
            if found is not None:
                return found
        return None

    def iter_leafs(self):
        for view in self.views:
            yield view

    def find_leaf_index(self, leaf):
        return self.views.index(leaf)  # raises IndexError on failure

    def find_resize_partner(self, leaf):
        current = self.find_leaf_index(leaf)
        return self.views[current + 1]

    def calc_dock_targets(self, targets):
        for view in self.views:
            try:
                view.calc_dock_targets(targets)
            except AttributeError:
                if hasattr(view, 'calc_docking_rectangles'):
                    targets.append(view)

    def delete_leaf_from_list(self, view, index):
        raise NotImplementedError("implement in subclass!")

    def detach_leaf(self, view):
        log.debug("detach_leaf: view=%s views=%s self=%s parent=%s" % (view, self.views, self, self.GetParent()))
        index = self.find_leaf_index(view)  # raise IndexError
        view.reparent_to(self.tile_mgr.hiding_space)
        self.delete_leaf_from_list(view, index)

    def destroy_leaf(self, view):
        self.detach_leaf(view)
        view.remove()

    def minimize_leaf(self, view):
        self.detach_leaf(view)
        sidebar = self.tile_mgr.use_sidebar(wx.DEFAULT)
        client = view.detach_client()
        sidebar.add_client(client)

    def maximize_leaf(self, view):
        log.warning("maximize not implemented yet")


class TileSplit(TileWindowBase, ViewContainer):
    class HorizontalLayout(object):
        @classmethod
        def calc_size(cls, tile_split):
            w, h = tile_split.GetClientSize()

            # size used for ratio includes all the sizer widths (including the
            # extra sizer at the end that won't be displayed)
            full_size = w + TileManager.sizer_thickness

            return w, h, full_size

        @classmethod
        def do_view_size(cls, view, pos, size, w, h):
            view_width = size - TileManager.sizer_thickness
            view.SetSize(pos, 0, view_width, h)
            view.sizer.SetSize(pos + view_width, 0, TileManager.sizer_thickness, h)

        @classmethod
        def calc_resizer(cls, splitter, left, sizer, right, x, y):
            return cls(splitter, left, sizer, right, x, y)

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
            w = w1 + w2 + 2 * (TileManager.sizer_thickness)
            h = h1 + h2 + 2 * (TileManager.sizer_thickness)
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
            x, y = x - self.mouse_offset[0] + TileManager.sizer_thickness, y - self.mouse_offset[1] + TileManager.sizer_thickness
            return x, y

        def calc_extrema(self):
            self.x_min, _ = self.first.GetPosition()
            self.x_min += 2 * TileManager.sizer_thickness
            x, _ = self.second.GetPosition()
            w, _ = self.second.GetSize()
            self.x_max = x + w
            self.x_max -= TileManager.sizer_thickness
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

    class VerticalLayout(HorizontalLayout):
        @classmethod
        def calc_size(cls, tile_split):
            w, h = tile_split.GetClientSize()

            # size used for ratio includes all the sizer widths (including the
            # extra sizer at the end that won't be displayed)
            full_size = h + TileManager.sizer_thickness

            return w, h, full_size

        @classmethod
        def do_view_size(cls, view, pos, size, w, h):
            view_height = size - TileManager.sizer_thickness
            view.SetSize(0, pos, w, view_height)
            view.sizer.SetSize(0, pos + view_height, w, TileManager.sizer_thickness)

        @classmethod
        def calc_resizer(cls, splitter, top, sizer, bot, x, y):
            return cls(splitter, top, sizer, bot, x, y)

        def __repr__(self):
            return "%s: %s %s, ratio=%f, height=%d" % (self.__class__.__name__, self.first.debug_id, self.second.debug_id, self.total_ratio, self.total_height)

        def calc_extrema(self):
            _, self.y_min = self.first.GetPosition()
            self.y_min += 2 * TileManager.sizer_thickness
            _, y = self.second.GetPosition()
            _, h = self.second.GetSize()
            self.y_max = y + h
            self.y_max -= TileManager.sizer_thickness
            log.debug("calc_extrema: min %d, y %d, h %d, max %d" % (self.y_min, y, h, self.y_max))

        def set_ratios(self, x, y):
            r = float(y - self.zero_pos[1]) / float(self.total_height) * self.total_ratio
            log.debug("y,r,y_min,xmax", y, r, self.y_min, self.y_max)
            if y > self.y_min and y < self.y_max:
                self.first.ratio_in_parent = r
                self.second.ratio_in_parent = self.total_ratio - r
                return True

    def __init__(self, tile_mgr, parent, layout_direction=wx.HORIZONTAL, ratio=1.0, leaf=None, layout=None):
        TileWindowBase.__init__(self, tile_mgr, parent, ratio, name="TileSplit")
        ViewContainer.__init__(self)
        if layout is not None:
            self.restore_layout(layout)
        else:
            self.layout_direction = layout_direction
            if leaf:
                leaf.reparent_to(self, 1.0)
                leaf.Move(0,0)
            else:
                leaf = TileViewLeaf(self.tile_mgr, self, 1.0)
            self.views.append(leaf)
        if self.layout_direction == wx.HORIZONTAL:
            self.layout_calculator = TileSplit.HorizontalLayout
        else:
            self.layout_calculator = TileSplit.VerticalLayout
        self.do_layout()

    def __repr__(self):
        return "<TileSplit %s %f>" % (self.debug_id, self.ratio_in_parent)

    def split(self, leaf, control=None, uuid=None, new_side=wx.RIGHT, view=None, **kwargs):
        log.debug("split: using view %s" % view)
        layout_direction = side_to_direction[new_side]
        if layout_direction != self.layout_direction:
            new_view = self.split_opposite(leaf, control, uuid, new_side, view, **kwargs)
        else:
            new_view = self.split_same(leaf, control, uuid, new_side, view, **kwargs)
        return new_view

    def split_same(self, leaf, control=None, uuid=None, new_side=wx.LEFT, view=None, **kwargs):
        view_index_to_split = self.find_leaf_index(leaf)
        if new_side & (wx.LEFT|wx.TOP):
            # insert at beginning of list
            insert_pos = view_index_to_split
        else:
            insert_pos = view_index_to_split + 1
        ratio = leaf.ratio_in_parent / 2.0
        leaf.ratio_in_parent = ratio

        if view is None:
            client = TileClient(None, control, uuid, self.tile_mgr, **kwargs)
            view = TileViewLeaf(self.tile_mgr, self, ratio, client)
        elif view.is_sidebar:
            client = view.detach_client()
            view = TileViewLeaf(self.tile_mgr, self, ratio, client, from_sidebar=True)
        else:
            view.reparent_to(self, ratio)
        self.views[insert_pos:insert_pos] = [view]
        self.do_layout()
        self.tile_mgr.send_layout_changed_event()
        return view

    def split_opposite(self, leaf, control=None, uuid=None, new_side=wx.LEFT, view=None, **kwargs):
        view_index_to_split = self.find_leaf_index(leaf)
        subsplit = TileSplit(self.tile_mgr, self, opposite[self.layout_direction], leaf.ratio_in_parent, leaf)
        self.views[view_index_to_split] = subsplit
        self.do_layout()
        return subsplit.split_same(leaf, control, uuid, new_side, view, **kwargs)

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

    def calc_layout(self):
        d = {
            'direction': int(self.layout_direction),
            'ratio_in_parent': self.ratio_in_parent,
            'views': [v.calc_layout() for v in self.views],
            }
        return d

    def restore_layout(self, d):
        self.layout_direction = d['direction']
        self.ratio_in_parent = d['ratio_in_parent']
        for layout in d['views']:
            if 'direction' in layout:
                view = TileSplit(self.tile_mgr, self, layout=layout)
            else:
                view = TileViewLeaf(self.tile_mgr, self, layout=layout)
            self.views.append(view)

    def delete_leaf_from_list(self, view, index):
        if len(self.views) > 2:
            log.debug("deleting > 2: %d %s" %(index, self.views))
            del self.views[index]
            # add ratio to whichever leaf is bigger
            possible_views = self.views[index - 1: index + 1]
            if len(possible_views) == 2 and possible_views[0].ratio_in_parent > possible_views[1].ratio_in_parent:
                i = index - 1
            else:
                i = min(index, len(self.views) - 1)  # handle last view
            self.views[i].ratio_in_parent += view.ratio_in_parent
            self.do_layout()
            self.tile_mgr.send_layout_changed_event()
        elif len(self.views) == 2:
            log.debug("deleting == 2: %d %s, parent=%s self=%s" % (index, self.views, self.GetParent(), self))
            # remove leaf, resulting in a single leaf inside a multisplit.
            # Instead of leaving it like this, move it up into the parent
            # multisplit
            del self.views[index]
            if self.GetParent() == self.tile_mgr:
                # Only one item left.
                log.debug("  last item in %s!" % (self))
                self.views[0].ratio_in_parent = 1.0
                self.do_layout()
            else:
                log.debug("  deleting %s from parent %s parent views=%s" % (self, self.GetParent(), self.GetParent().views))
                self.GetParent().reparent_from_splitter(self)
                self.tile_mgr.send_layout_changed_event()
        else:
            # must be at the top; the final splitter.
            log.debug("Removing the last item!", view)
            self.GetParent().clear_main_splitter()

    def reparent_from_splitter(self, splitter):
        index = self.find_leaf_index(splitter)  # raise IndexError
        view = splitter.views[0]
        view.reparent_to(self, splitter.ratio_in_parent)
        self.views[index] = view
        splitter.remove()
        self.do_layout()


########## Leaf (Client Container) ##########

class TileViewLeaf(TileWindowBase, DockTarget):
    can_take_leaf_focus = True
    is_sidebar = False

    def __init__(self, tile_mgr, parent, ratio=1.0, client=None, layout=None, from_sidebar=False):
        TileWindowBase.__init__(self, tile_mgr, parent, ratio, name="TileViewLeaf")
        if layout is not None:
            self.client = None
            self.restore_layout(layout)
        else:
            if client is None:
                client = TileClient(self)
            if from_sidebar:
                client.SetPosition((0, 0))
                client.Show()
            self.attach_client(client)
        self.SetBackgroundColour(tile_mgr.unfocused_color)

    @property
    def debug_id(self):
        return self.client.child.GetName() if self.client is not None else None

    def __repr__(self):
        return "<TileLeaf %s %f>" % (self.debug_id, self.ratio_in_parent)

    def remove(self):
        self.remove_client()
        self.sizer.Destroy()
        self.Destroy()

    def remove_all(self):
        self.remove()

    def set_chrome(self, client):
        client.extra_border = 1

    def calc_layout(self):
        d = self.client.calc_layout()
        d['ratio_in_parent'] = self.ratio_in_parent
        return d

    def restore_layout(self, d):
        self.ratio_in_parent = d['ratio_in_parent']
        old = self.client
        self.client = TileClient(self, layout=d)
        if old is not None:
            old.Destroy()
        self.client.do_size_from_parent()

    def get_tile_split(self):
        return self.GetParent()

    def split_side(self, new_side, view=None):
        return self.GetParent().split(self, new_side=new_side, view=view)

    def destroy_leaf(self):
        return self.GetParent().destroy_leaf(self)

    def minimize_leaf(self):
        return self.GetParent().minimize_leaf(self)

    def do_layout(self):
        self.client.do_size_from_parent()


class TileClient(wx.Window):
    def __init__(self, parent, child=None, uuid=None, tile_mgr=None, leaf=None, layout=None, **kwargs):
        if parent is None:
            parent = tile_mgr.hiding_space
        wx.Window.__init__(self, parent, -1, style=wx.CLIP_CHILDREN | wx.BORDER_NONE, size=(200, 200), name=TileManager.debug_window_name("TileClient"))
        if tile_mgr is None:
            tile_mgr = parent.tile_mgr
        self.tile_mgr = tile_mgr
        self.init_kwargs(**kwargs)

        self.extra_border = 0
        self.title_bar = TitleBar(self)

        if child is None:
            child = self.tile_mgr._defChild(self)
        self.child = child
        self.child.Reparent(self)
        self.move_child()

        if layout is not None:
            self.restore_layout(layout)
        else:
            if uuid is None:
                uuid = str(uuid4())
            self.child_uuid = uuid

        log.debug("Created client for %s" % self.child.GetName())
        if leaf is None:
            leaf = parent
        self.set_leaf(leaf)

        self.Bind(wx.EVT_SET_FOCUS, self.on_set_focus)
        self.Bind(wx.EVT_CHILD_FOCUS, self.on_child_focus)

    def init_kwargs(self, **kwargs):
        self.show_title = kwargs.get('show_title', True)
        self.use_close_button = kwargs.get('use_close_button', True)

    def calc_layout(self):
        d = {
            'child_uuid': self.child_uuid,
            'show_title': self.show_title,
            'use_close_button': self.use_close_button,
        }
        return d

    def restore_layout(self, d):
        self.child_uuid = d['child_uuid']
        self.show_title = d.get('show_title', True)
        self.use_close_button = d.get('use_close_button', True)

    def set_leaf(self, leaf):
        self.leaf = leaf
        self.title_bar.set_buttons_for_sidebar_state(leaf.is_sidebar)
        self.leaf.set_chrome(self)
        self.leaf.reparent_client(self)
        self.do_size_from_child()
        if leaf.is_sidebar:
            self.SetBackgroundColour(self.tile_mgr.focused_color)
        else:
            self.SetBackgroundColour(self.tile_mgr.border_color)
        # self.SetBackgroundColour(wx.RED)

    def remove(self):
        self.do_send_close_event()
        self.Destroy()

    def do_send_event(self, evt):
        return not self.GetEventHandler().ProcessEvent(evt) or evt.IsAllowed()

    def do_send_close_event(self):
        log.debug("sending close event for %s" % self)
        evt = TileManagerEvent(TileManager.wxEVT_CLIENT_CLOSE, self)
        evt.SetChild(self.child)
        self.do_send_event(evt)

    def do_send_replace_event(self, new_child):
        log.debug("sending replace event for %s" % self)
        evt = TileManagerEvent(TileManager.wxEVT_CLIENT_REPLACE, self)
        evt.SetChild(self.child)
        evt.SetReplacementChild(new_child)
        self.do_send_event(evt)

    @property
    def title(self):
        return self.child.GetName()

    @property
    def popup_name(self):
        menu_label = self.child.GetLabel()
        if not menu_label:
            menu_label = self.child.GetName()
        return menu_label

    def clear_focus(self):
        self.Refresh()

    def set_focus(self):
        evt = TileManagerEvent(TileManager.wxEVT_CLIENT_ACTIVATED, self)
        evt.SetChild(self.child)
        self.do_send_event(evt)
        print("setting focus to %s" % self.child.GetName())
        self.child.SetFocus()
        self.Refresh()

    def do_size_from_parent(self):
        w, h = self.GetParent().GetClientSize()
        self.do_size_from_bounds(w, h)

    def do_size_from_bounds(self, w, h):
        self.SetSize(w, h)
        b = self.extra_border
        m = self.tile_mgr
        w -= b * 2
        h -= b * 2
        self.title_bar.SetSize(b, b, w, m.title_bar_height)
        if self.show_title:
            title_offset = m.title_bar_height
        else:
            title_offset = 0
        self.title_bar.Show(self.show_title)
        self.child.SetSize(b, b + title_offset, w, h - title_offset)

    def DoGetBestClientSize(self):
        b = self.extra_border
        m = self.tile_mgr
        w, h = self.child.GetBestSize()
        return wx.Size(w + b * 2, h + b * 2 + m.title_bar_height)

    def do_size_from_child(self):
        b = self.extra_border
        m = self.tile_mgr
        w, h = self.child.GetBestSize()
        self.SetSize((w + b * 2, h + b * 2 + m.title_bar_height))
        self.title_bar.SetSize(b, b, w, m.title_bar_height)
        self.child.SetSize(b, b + m.title_bar_height, w, h)

    def replace(self, child, u=None, **kwargs):
        if self.child:
            self.do_send_replace_event(child)
            self.child.Destroy()
            self.child = None
        self.child = child
        self.child.Reparent(self)
        if u is None:
            u = str(uuid4())
        self.child_uuid = u
        self.init_kwargs(**kwargs)
        self.title_bar.set_buttons_for_sidebar_state(self.leaf.is_sidebar)
        self.move_child()
        self.do_size_from_parent()

    def reparent_to_new_leaf(self, new_leaf):
        self.leaf.detach_client()
        new_leaf.attach_client(self)
        self.leaf = new_leaf

    def move_child(self):
        self.title_bar.Move(0, 0)
        self.child.Move(0, self.tile_mgr.title_bar_height)

    def on_set_focus(self,evt):
        m = self.tile_mgr
        if self.leaf == m.current_leaf_focus:
            print("already focused", self.leaf)
        else:
            print("on_set_focus", self.leaf, "current_leaf_focus", m.current_leaf_focus, "current menu", m.menu_currently_displayed)
            m.set_leaf_focus(self.leaf)

    def on_child_focus(self,evt):
        self.on_set_focus(evt)

    def fit_in_popup(self, x, y, w, h):
        self.SetPosition((x, y))
        self.do_size_from_bounds(w, h)
        self.Show()

    def destroy_thyself(self):
        wx.CallAfter(self.leaf.destroy_leaf)

    def minimize(self):
        wx.CallAfter(self.leaf.minimize_leaf)

    def maximize(self):
        wx.CallAfter(self.leaf.maximize_leaf)

    def split_side(self, new_side, view=None):
        return self.leaf.split_side(new_side, view)


########## Title Bar ##########

class TitleBar(wx.Window):
    class Button(wx.Window):
        def __init__(self, parent, size):
            self.title_bar = parent
            self.client = parent.GetParent()
            wx.Window.__init__(self, parent, -1, pos=(0, 0), size=size, style=wx.BORDER_NONE, name=TileManager.debug_window_name("TitleBarButton"))

            self.down = False
            self.entered = False
            self.is_enabled = True
            self.is_always_shown = False

            self.Bind(wx.EVT_LEFT_DOWN, self.on_press)
            self.Bind(wx.EVT_LEFT_UP, self.on_release)
            self.Bind(wx.EVT_PAINT, self.on_paint)
            self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
            self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)

        def set_sidebar_state(self, in_sidebar):
            self.is_enabled = not in_sidebar

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
            m = self.client.tile_mgr
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

        def do_hide(self):
            if not self.is_always_shown:
                self.Hide()

        def do_show(self):
            self.Show()

        def do_button_pos(self, x, h):
            bw, bh = self.GetSize()
            x -= bw
            y = (h - bh) // 2
            self.SetPosition((x, y))
            return x


    class Closer(Button):
        def set_sidebar_state(self, in_sidebar):
            self.is_always_shown = True
            self.is_enabled = self.client.use_close_button

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
                self.client.destroy_thyself()

        def ask_close(self):
            return True


    class Minimize(Button):
        def draw_button(self, dc, size, bg_brush, pen, fg_brush):
            cx = size.x // 2
            cy = size.y // 2
            dc.SetBrush(bg_brush)
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangle(cx - 2, cy - 2, cx + 1, cy + 1)
            dc.SetPen(pen)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(cx - 2, cy - 2, cx + 1, cy + 1)

        def do_action(self, evt):
            self.client.minimize()


    class Maximize(Button):
        def set_sidebar_state(self, in_sidebar):
            self.is_enabled = in_sidebar
            # self.is_always_shown = True

        def draw_button(self, dc, size, bg_brush, pen, fg_brush):
            dc.SetBrush(bg_brush)
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangle(0, 0, size.x, size.y)
            dc.SetPen(pen)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(0, 0, size.x, size.y)

        def do_action(self, evt):
            self.client.maximize()


    class VSplitNewLeft(Button):
        def draw_button(self, dc, size, bg_brush, pen, fg_brush):
            split = size.x // 2
            dc.SetBrush(bg_brush)
            dc.SetPen(pen)
            dc.DrawRectangle(0, 0, split + 1, size.y)
            dc.SetBrush(fg_brush)
            dc.DrawRectangle(split, 0, size.x - split, size.y)

        def do_action(self, evt):
            self.client.split_side(wx.LEFT)


    class VSplitNewRight(Button):
        def draw_button(self, dc, size, bg_brush, pen, fg_brush):
            split = size.x // 2
            dc.SetBrush(bg_brush)
            dc.SetPen(pen)
            dc.DrawRectangle(0, 0, split + 1, size.y)
            dc.SetBrush(fg_brush)
            dc.DrawRectangle(split, 0, size.x - split, size.y)

        def do_action(self, evt):
            self.client.split_side(wx.RIGHT)


    class HSplitNewBot(Button):
        def draw_button(self, dc, size, bg_brush, pen, fg_brush):
            split = size.y // 2
            dc.SetBrush(bg_brush)
            dc.SetPen(pen)
            dc.DrawRectangle(0, 0, size.x, split + 1)
            dc.SetBrush(fg_brush)
            dc.DrawRectangle(0, split, size.x, size.y - split)

        def do_action(self, evt):
            self.client.split_side(wx.BOTTOM)


    class HSplitNewTop(Button):
        def draw_button(self, dc, size, bg_brush, pen, fg_brush):
            split = size.y // 2
            dc.SetBrush(bg_brush)
            dc.SetPen(pen)
            dc.DrawRectangle(0, 0, size.x, split + 1)
            dc.SetBrush(fg_brush)
            dc.DrawRectangle(0, split, size.x, size.y - split)

        def do_action(self, evt):
            self.client.split_side(wx.TOP)

    def __init__(self, parent, in_sidebar=False):
        wx.Window.__init__(self, parent, -1, name=TileManager.debug_window_name("TitleBar"))
        self.client = parent
        m = self.client.tile_mgr

        self.buttons = []
        self.buttons.append(TitleBar.Closer(self, m.close_button_size))
        self.buttons.append(TitleBar.Minimize(self, m.close_button_size))
        self.buttons.append(TitleBar.Maximize(self, m.close_button_size))
        self.buttons.append(TitleBar.HSplitNewBot(self, m.close_button_size))
        self.buttons.append(TitleBar.HSplitNewTop(self, m.close_button_size))
        self.buttons.append(TitleBar.VSplitNewRight(self, m.close_button_size))
        self.buttons.append(TitleBar.VSplitNewLeft(self, m.close_button_size))

        # self.SetBackgroundColour(wx.RED)
        self.set_buttons_for_sidebar_state(in_sidebar)
        self.hide_buttons()

        self.mouse_down_pos = None

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEAVE_WINDOW,self.on_leave)
        self.Bind(wx.EVT_ENTER_WINDOW,self.on_enter)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_MOTION, self.on_motion)

    def on_left_down(self, evt):
        self.mouse_down_pos = evt.GetPosition()
        evt.Skip()

    def on_motion(self, evt):
        old = self.mouse_down_pos
        if evt.LeftIsDown() and old is not None:
            pos = evt.GetPosition()
            d = self.client.tile_mgr.mouse_delta_for_window_move
            if abs(old.x - pos.x) > d or abs(old.y - pos.y) > d:
                self.hide_buttons()
                self.mouse_down_pos = None
                self.client.tile_mgr.start_child_window_move(self.client.leaf, evt)

    def set_buttons_for_sidebar_state(self, in_sidebar):
        for button in self.buttons:
            button.set_sidebar_state(in_sidebar)
        self.position_buttons()

    def draw_title_bar(self, dc):
        m = self.client.tile_mgr
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

    def position_buttons(self):
        m = self.client.tile_mgr
        w, h = self.GetClientSize()
        x = w - m.title_bar_margin
        for button in self.buttons:
            if button.is_enabled:
                x = button.do_button_pos(x, h)
                x -= m.title_bar_margin
            else:
                button.SetPosition((-100, -100))

    def on_size(self, evt):
        self.position_buttons()

    def hide_buttons(self):
        for button in self.buttons:
            button.do_hide()

    def show_buttons(self):
        for button in self.buttons:
            button.do_show()

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


########## Sidebar ##########

class SidebarMenuItem(wx.Window, DockTarget):
    can_take_leaf_focus = False
    is_sidebar = True

    if wx.Platform == "__WXGTK__":
        class SidebarPopupWindow(wx.Frame):
            def __init__(self, parent, style=None):
                wx.Frame.__init__(self, parent, style = wx.NO_BORDER|wx.FRAME_FLOAT_ON_PARENT|wx.FRAME_NO_TASKBAR|wx.FRAME_SHAPED)
                #self.Bind(wx.EVT_KEY_DOWN , self.OnKeyDown)
                self.Bind(wx.EVT_CHAR, self.on_char)

            def Popup(self):
                self.Show(True)

            def Dismiss(self):
                self.Show(False)

            def on_char(self, evt):
                print("on_char: keycode=%s" % evt.GetKeyCode())
                self.GetParent().GetEventHandler().ProcessEvent(evt)
    else:
        class SidebarPopupWindow(wx.PopupWindow):
            def Popup(self):
                self.Show(True)

            def Dismiss(self):
                self.Show(False)

    def __init__(self, sidebar, client=None, layout=None):
        wx.Window.__init__(self, sidebar, -1, name=TileManager.debug_window_name("SidebarMenuItem"))
        self.sidebar = sidebar
        self.tile_mgr = sidebar.tile_mgr
        self.actual_popup = self.SidebarPopupWindow(self.tile_mgr)

        # Client windows are children of the main window so they can be
        # positioned over (and therefore obscure) any window within the
        # TileManager
        self.client = None
        if layout is not None:
            self.restore_layout(layout)
        else:
            self.attach_client(client)
        self.SetBackgroundColour(self.tile_mgr.empty_color)

        # the label drawing offsets will be calculated during sizing
        self.label_x = 0
        self.label_y = 0
        self.entered = False
        self.client.Hide()

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)

    def __repr__(self):
        return "<SidebarMenuItem %s>" % (self.client.child.GetName())

    def calc_layout(self):
        return self.client.calc_layout()

    def restore_layout(self, d):
        old = self.client
        self.client = TileClient(self, layout=d)
        if old is not None:
            old.Destroy()

    def reparent_to(self, viewer, ratio=None):
        self.Reparent(viewer)

    def set_chrome(self, client):
        client.extra_border = 4

    def reparent_client(self, client):
        client.Reparent(self.actual_popup)

    def calc_docking_rectangles(self, event_window, source_leaf):
        r = self.calc_rectangle_relative_to(event_window)
        if source_leaf == self:
            # dummy rectangle for feedback, but can't drop on itself
            rects = [(None, None, r)]
        else:
            first = self.sidebar.find_leaf_index(self) == 0
            rects = self.sidebar.title_renderer.calc_docking_rectangles_relative_to(self, r, first)
        return rects

    def split_side(self, new_side, view=None):
        return self.GetParent().split_menu_item(self, new_side, view)

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        s = self.sidebar
        s.tile_mgr.configure_sidebar_dc(dc, self.entered)
        s.title_renderer.draw_label(dc, self)

    def on_left_down(self, evt):
        self.tile_mgr.on_start_menu(self, evt)

    def position_popup(self, x, y, w, h):
        top = self.tile_mgr
        xs, ys = top.ClientToScreen(x, y)
        self.client.SetSize(0, 0, w, h)
        self.client.fit_in_popup(0, 0, w, h)
        self.actual_popup.SetSize(xs, ys, w, h)
        self.actual_popup.Popup()
        print("positioned popup %s to %s" % (self.client.child.GetName(), (xs, ys, w, h)))

    def open_menu(self):
        self.entered = True
        self.sidebar.title_renderer.show_client(self.sidebar, self)
        self.Refresh()

    def close_menu(self):
        self.entered = False
        self.actual_popup.Dismiss()
        self.Refresh()

    def remove(self):
        self.client.do_send_close_event()
        self.actual_popup.Destroy()
        self.Destroy()

    def remove_all(self):
        self.remove()

    def find_uuid(self, uuid):
        if uuid == self.client.child_uuid:
            log.debug("find_uuid: found %s in %s" % (uuid, self.client.child.GetName()))
            return self.client
        log.debug("find_uuid: skipping %s in %s" % (self.client.child_uuid, self.client.child.GetName()))
        return None

    def destroy_leaf(self):
        return self.GetParent().destroy_leaf(self)

    def maximize_leaf(self):
        return self.GetParent().maximize_leaf(self)


class MissingSidebarDock(DockTarget):
    def __init__(self, tile_mgr, side):
        self.side = side
        self.tile_mgr = tile_mgr
        self.title_renderer = Sidebar.renderers[side]

    def calc_docking_rectangles(self, event_window, source_leaf):
        mw, mh = self.tile_mgr.GetClientSize()
        ux, uy, uw, uh = self.tile_mgr.calc_usable_rect()
        rect = self.title_renderer.calc_missing_sidebar_docking_rectangle(self)
        return [(self, None, rect)]

    def split_side(self, new_side, view=None):
        sidebar = self.tile_mgr.use_sidebar(self.side)
        client = view.detach_client()
        sidebar.add_client(client)


class Sidebar(wx.Window, ViewContainer):
    class BaseRenderer(object):
        @classmethod
        def calc_view_start(cls, w, h):
            return 0

        @classmethod
        def calc_thickness(cls, sidebar):
            m = sidebar.tile_mgr
            pixels = m.sidebar_margin * 2 + m.title_bar_font_height
            return pixels

        @classmethod
        def show_client_prevent_clipping(cls, sidebar, view, x, y):
            cw, ch = view.client.GetBestSize()
            x_min, y_min, sw, sh = sidebar.tile_mgr.calc_usable_rect()
            if y + ch > y_min + sh:
                # some amount is offscreen on the bottom
                y -= (y + ch - sh - y_min)
            if y < y_min:
                # too tall, force popup height to max height of usable space
                y = y_min
                ch = sh
            if cw > sw:
                cw = sw
            if x + cw > x_min + sw:
                # some amount is offscreen to the right
                x -= (x + cw - sw - x_min)
            if x < x_min:
                # too wide; force popup to max width of usable space
                x = x_min
                cw = sw
            view.position_popup(x, y, cw, ch)


    class VerticalRenderer(BaseRenderer):
        @classmethod
        def do_view_size(cls, view, pos, w, h):
            m = view.tile_mgr
            text_width, text_height = m.get_text_size(view.client.popup_name)
            size = text_width + 2 * m.sidebar_margin
            view.SetSize(0, pos, w, size)
            view.label_x = m.sidebar_margin
            view.label_y = m.sidebar_margin + text_width
            return pos + size

        @classmethod
        def draw_label(cls, dc, view):
            w, h = view.GetSize()
            dc.DrawRectangle(0, 0, w, h)
            dc.DrawRotatedText(view.client.popup_name, view.label_x, view.label_y, 90.0)

        @classmethod
        def calc_docking_rectangles_relative_to(cls, target_to_split, r, first):
            rects = []
            h = r.height // 3
            ty = r.y + r.height - (h // 2)  # offset to between items
            if first:
                rects.append((target_to_split, wx.TOP, wx.Rect(r.x, r.y, r.width, h)))  # bottom
            rects.append((target_to_split, wx.BOTTOM, wx.Rect(r.x, ty, r.width, h)))  # top
            return rects


    class LeftRenderer(VerticalRenderer):
        @classmethod
        def set_size_inside(cls, sidebar, x, y, w, h):
            thickness = cls.calc_thickness(sidebar)
            sidebar.SetSize(x, y, thickness, h)
            return x + thickness, y, w - thickness, h

        @classmethod
        def show_client(cls, sidebar, view):
            # sidebar position within tile_mgr, so these are global values
            x_min, y_min = sidebar.GetPosition()
            w, h = sidebar.GetSize()
            x_min += w

            # view position is position within sidebar
            x, y = view.GetPosition()
            w, h = view.GetSize()
            y += y_min  # global y for top of window
            cls.show_client_prevent_clipping(sidebar, view, x_min, y)

        @classmethod
        def calc_missing_sidebar_docking_rectangle(cls, missing_sidebar):
            ux, uy, uw, uh = missing_sidebar.tile_mgr.calc_usable_rect()
            return wx.Rect(0, uy, cls.calc_thickness(missing_sidebar) // 2, uh)


    class RightRenderer(VerticalRenderer):
        @classmethod
        def set_size_inside(cls, sidebar, x, y, w, h):
            thickness = cls.calc_thickness(sidebar)
            sidebar.SetSize(x + w - thickness, y, thickness, h)
            return x, y, w - thickness, h

        @classmethod
        def show_client(cls, sidebar, view):
            # sidebar position within tile_mgr, so these are global values
            x_min, y_min = sidebar.GetPosition()

            # view position is position within sidebar
            x, y = view.GetPosition()
            w, h = view.GetSize()
            y += y_min  # global y for top of window
            cls.show_client_prevent_clipping(sidebar, view, x_min, y)

        @classmethod
        def calc_missing_sidebar_docking_rectangle(cls, missing_sidebar):
            mw, mh = missing_sidebar.tile_mgr.GetClientSize()
            ux, uy, uw, uh = missing_sidebar.tile_mgr.calc_usable_rect()
            t = cls.calc_thickness(missing_sidebar) // 2
            return wx.Rect(mw - t, uy, t, uh)


    class HorizontalRenderer(BaseRenderer):
        @classmethod
        def do_view_size(cls, view, pos, w, h):
            m = view.tile_mgr
            text_width, text_height = m.get_text_size(view.client.popup_name)
            size = text_width + 2 * m.sidebar_margin
            view.SetSize(pos, 0, size, h)
            view.label_x = m.sidebar_margin
            view.label_y = m.sidebar_margin
            return pos + size

        @classmethod
        def draw_label(cls, dc, view):
            w, h = view.GetSize()
            dc.DrawRectangle(0, 0, w, h)
            dc.DrawText(view.client.popup_name, view.label_x, view.label_y)

        @classmethod
        def calc_docking_rectangles_relative_to(cls, target_to_split, r, first):
            rects = []
            w = r.width // 3
            rx = r.x + r.width - (w // 2)
            if first:
                rects.append((target_to_split, wx.LEFT, wx.Rect(r.x, r.y, w, r.height)))  # left
            rects.append((target_to_split, wx.RIGHT, wx.Rect(rx, r.y, w, r.height)))  # right
            return rects


    class TopRenderer(HorizontalRenderer):
        @classmethod
        def set_size_inside(cls, sidebar, x, y, w, h):
            thickness = cls.calc_thickness(sidebar)
            sidebar.SetSize(x, y, w, thickness)
            return x, y + thickness, w, h - thickness

        @classmethod
        def show_client(cls, sidebar, view):
            # sidebar position within tile_mgr, so these are global values
            x_min, y_min = sidebar.GetPosition()
            w, h = sidebar.GetSize()
            y_min += h

            # view is menu item position within sidebar
            x, y = view.GetPosition()
            w, h = view.GetSize()
            x += x_min
            cls.show_client_prevent_clipping(sidebar, view, x, y_min)

        @classmethod
        def calc_missing_sidebar_docking_rectangle(cls, missing_sidebar):
            ux, uy, uw, uh = missing_sidebar.tile_mgr.calc_usable_rect()
            return wx.Rect(ux, 0, uw, cls.calc_thickness(missing_sidebar) // 2)


    class BottomRenderer(HorizontalRenderer):
        @classmethod
        def set_size_inside(cls, sidebar, x, y, w, h):
            thickness = cls.calc_thickness(sidebar)
            sidebar.SetSize(x, y + h - thickness, w, thickness)
            return x, y, w, h - thickness

        @classmethod
        def show_client(cls, sidebar, view):
            # sidebar position within tile_mgr, so these are global values
            x_min, y_max = sidebar.GetPosition()

            # view is menu item position within sidebar
            x, y = view.GetPosition()
            w, h = view.GetSize()
            x += x_min
            cls.show_client_prevent_clipping(sidebar, view, x, y_max)

        @classmethod
        def calc_missing_sidebar_docking_rectangle(cls, missing_sidebar):
            mw, mh = missing_sidebar.tile_mgr.GetClientSize()
            ux, uy, uw, uh = missing_sidebar.tile_mgr.calc_usable_rect()
            t = cls.calc_thickness(missing_sidebar) // 2
            return wx.Rect(ux, mh - t, uw, t)

    renderers = {
        wx.LEFT: LeftRenderer,
        wx.RIGHT: RightRenderer,
        wx.TOP: TopRenderer,
        wx.BOTTOM: BottomRenderer,
    }

    def __init__(self, tile_mgr, side=wx.LEFT, layout=None):
        wx.Window.__init__(self, tile_mgr, -1, name=TileManager.debug_window_name("Sidebar"))
        ViewContainer.__init__(self)
        self.tile_mgr = tile_mgr

        self.SetBackgroundColour(tile_mgr.empty_color)
        if layout is not None:
            self.restore_layout(layout)
        else:
            self.set_renderer(side)

    def __repr__(self):
        return "Sidebar %s" % pretty_direction[self.side]

    def calc_layout(self):
        d = {
            'side': int(self.side),
            'views': [v.calc_layout() for v in self.views],
            }
        return d

    def restore_layout(self, d):
        self.set_renderer(d['side'])
        for layout in d['views']:
            view = SidebarMenuItem(self, layout=layout)
            self.views.append(view)

    def set_renderer(self, side):
        self.title_renderer = self.renderers[side]
        self.side = side

    def set_size_inside(self, x, y, w, h):
        return self.title_renderer.set_size_inside(self, x, y, w, h)

    def split_menu_item(self, menu_item_to_split, side, new_leaf):
        menu_index_to_split = self.find_leaf_index(menu_item_to_split)
        if side & (wx.LEFT|wx.TOP):
            # insert at beginning of list
            insert_pos = menu_index_to_split
        else:
            insert_pos = menu_index_to_split + 1

        client = new_leaf.detach_client()
        view = SidebarMenuItem(self, client)
        self.views[insert_pos:insert_pos] = [view]
        self.do_layout()
        self.tile_mgr.send_layout_changed_event()
        return view

    def add_client(self, client):
        view = SidebarMenuItem(self, client)
        self.views.append(view)
        self.do_layout()
        self.tile_mgr.send_layout_changed_event()

    def force_popup_to_top_of_stacking_order(self):
        # Unless popup is at the top of the stacking order, it will be obscured
        # by the main TileSplit window (and all of its children, of course).
        # This method is needed only when the main TileSplit window is changed
        # with a call to TileManager.remove_all
        for view in self.views:
            # There doesn't appear to be an explicit way to force a particular
            # child window to the top of the stacking order, but this is a
            # workaround.
            view.client.Reparent(self.tile_mgr.hiding_space)
            view.client.Reparent(self.tile_mgr)
            pass

    def do_layout(self):
        w, h = self.GetSize()

        pos = self.title_renderer.calc_view_start(w, h)
        for view in self.views:
            pos = self.title_renderer.do_view_size(view, pos, w, h)

    def delete_leaf_from_list(self, view, index):
        self.tile_mgr.force_clear_sidebar()
        del self.views[index]
        self.do_layout()
        if len(self.views) == 0:
            log.debug("Nothing left in sidebar!", self)
            self.tile_mgr.remove_sidebar(self)
        else:
            self.tile_mgr.send_layout_changed_event()


########## Events ##########

class TileManagerEvent(wx.PyCommandEvent):
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
        The TileClient child window that is reporting the event

        :param `client`: TileClient instance

        """
        self.child = child

    def GetChild(self):
        """
        The TileClient child window that is reporting the event

        :param `client`: TileClient instance

        """
        return self.child

    def SetReplacementChild(self, child):
        """
        The child window that will become the new child of the TileClient

        :param `client`: TileClient instance

        """
        self.replacement_child = child

    def GetReplacementChild(self):
        """
        The child window that will become the new child of the TileClient

        :param `client`: TileClient instance

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

        json_text.SetValue(multi.calc_layout(True, True))

    def load_state(evt):
        global multi, json_text

        state = json_text.GetValue()
        multi.restore_layout(state)

    def find_uuid(evt):
        global multi, uuid_text

        u = uuid_text.GetValue()
        multi.force_focus(u)

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

    def toggle_footer(evt):
        multi.show_footer(not multi.footer.IsShown())

    def toggle_header(evt):
        multi.show_header(not multi.header.IsShown())

    app = wx.App()
    frame = wx.Frame(None, -1, "Test", size=(800,400))
    multi = TileManager(frame, pos = (0,0), size = (640,480), layout_direction=wx.HORIZONTAL)
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
    btn = wx.Button(frame, -1, "Footer")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, toggle_footer)
    btn = wx.Button(frame, -1, "Header")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, toggle_header)

    multi.use_sidebar(wx.LEFT)
    multi.use_sidebar(wx.TOP)
    multi.add_sidebar(None)
    multi.add_sidebar(None)
    multi.add_sidebar(None, side=wx.TOP)
    multi.add_sidebar(None, side=wx.TOP)

    minibuffer = wx.TextCtrl(multi, -1, size=(400,20))
    multi.add_footer(minibuffer)
    title = wx.StaticText(multi, -1, "Tile Manager test")
    title.SetBackgroundColour("darkseagreen4")
    multi.add_header(title)

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
