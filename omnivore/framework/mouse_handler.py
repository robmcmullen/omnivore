# Standard library imports.
import sys

# Major package imports.
import wx

# Local imports.
from omnivore import get_image_path

import logging
log = logging.getLogger(__name__)


class MouseHandler(object):
    """
    Processing of mouse events, separate from the rendering window
    
    This is an object-based control system of mouse modes
    """
    icon = "help.png"
    menu_item_name = "Generic Mouse Handler"
    menu_item_tooltip = "Tooltip for generic mouse handler"
    editor_trait_for_enabled = ""

    mouse_too_close_pixel_tolerance = 5

    def __init__(self, window):
        self.control = window
        self.snapped_point = None, 0
        self.first_mouse_down_position = 0, 0
        self.after_first_mouse_up = False
        self.mouse_up_too_close = False
        self.can_snap = False

        # left_up events can be called after double click on some platforms, so
        # this parameter can be set by the parent of the handler if the handler
        # wants to differentiate response to left_up
        self.num_clicks = 0

        # Optional (only OS X at this point) mouse wheel event filter
        self.wheel_scroll_count = 0
        self.use_every_nth_wheel_scroll = 5

        self.init_post_hook()

    def init_post_hook(self):
        pass

    def cleanup(self):
        pass

    def get_cursor(self):
        return wx.Cursor(wx.CURSOR_ARROW)

    def process_left_down(self, evt):
        evt.Skip()

    def get_position(self, evt):
        return evt.GetPosition()

    def process_mouse_motion_up(self, evt):
        self.control.release_mouse()
        evt.Skip()

    def process_mouse_motion_down(self, evt):
        evt.Skip()

    def reset_early_mouse_params(self):
        self.mouse_up_too_close = False
        self.after_first_mouse_up = False

    def check_early_mouse_release(self, evt):
        c = self.control
        p = evt.GetPosition()
        dx = p[0] - self.first_mouse_down_position[0]
        dy = p[1] - self.first_mouse_down_position[1]
        tol = self.mouse_too_close_pixel_tolerance
        if abs(dx) < tol and abs(dy) < tol:
            return True
        return False

    def process_left_up(self, evt):
        c = self.control
        c.release_mouse()  # it's hard to know for sure when the mouse may be captured
        c.selection_box_is_being_defined = False

    def process_left_dclick(self, evt):
        evt.Skip()

    def process_popup(self, evt):
        actions = self.get_popup_actions(evt)
        if actions:
            self.control.editor.popup_context_menu_from_actions(self.control, actions)

    def get_popup_actions(self, evt):
        return None

    def process_mouse_wheel(self, evt):
        c = self.control
        e = c.editor
        rotation = evt.GetWheelRotation()
        delta = evt.GetWheelDelta()
        window = evt.GetEventObject()
        log.debug("on_mouse_wheel_scroll. rot=%s delta=%d win=%s" % (rotation, delta, window))
        if rotation == 0 or delta == 0:
            return

        if sys.platform == "darwin":
            # OS X mouse wheel handling is not the same as other platform.
            # The delta value is 10 while the other platforms are 120,
            # and the rotation amount varies, seemingly due to the speed at
            # which the wheel is rotated (or how fast the trackpad is swiped)
            # while other platforms are either 120 or -120.  When mouse wheel
            # handling is performed in the usual manner on OS X it produces a
            # strange back-and-forth zooming in/zooming out.  So, this extra
            # hack is needed to operate like the other platforms.

            # add extra to the rotation so the minimum amount is 1 or -1
            extra = delta if rotation > 0 else -delta
            amount = (rotation + extra) / delta
            self.wheel_scroll_count -= abs(amount)
            if self.wheel_scroll_count > 0:
                return
            self.wheel_scroll_count = self.use_every_nth_wheel_scroll
        else:
            amount = rotation / delta

        if evt.ControlDown():
            self.zoom_mouse_wheel(evt, amount)
        else:
            self.pan_mouse_wheel(evt, amount)

    def zoom_mouse_wheel(self, evt, amount):
        pass

    def pan_mouse_wheel(self, evt, amount):
        evt.Skip()

    def process_mouse_enter(self, evt):
        evt.Skip()

    def process_mouse_leave(self, evt):
        evt.Skip()

    def process_focus(self, evt):
        pass

    def process_focus_lost(self, evt):
        pass

    def process_key_char(self, evt):
        c = self.control
        if (evt.GetKeyCode() == wx.WXK_ESCAPE):
            self.esc_key_pressed()
        elif evt.GetKeyCode() == wx.WXK_DELETE:
            self.delete_key_pressed()
        elif evt.GetKeyCode() == wx.WXK_BACK:
            self.backspace_key_pressed()
        else:
            evt.Skip()

    def esc_key_pressed(self):
        self.control.project.clear_all_selections()

    def delete_key_pressed(self):
        pass

    def backspace_key_pressed(self):
        pass



class MouseControllerMixin(object):
    """Mixin for a control to adapt to the MouseHandler class
    
    Must specify the default pan mode
    """

    def __init__(self, pan_mode_class):
        p = get_image_path("icons/hand.ico")
        self.hand_cursor = wx.Cursor(p, wx.BITMAP_TYPE_ICO, 16, 16)
        p = get_image_path("icons/hand_closed.ico")
        self.hand_closed_cursor = wx.Cursor(p, wx.BITMAP_TYPE_ICO, 16, 16)
        self.forced_cursor = None
        self.set_mouse_mode(MouseHandler)  # dummy initial mouse handler
        self.default_pan_mode = pan_mode_class(self)
        self.batch = None

    def set_mouse_mode(self, handler):
        self.release_mouse()
        self.mouse_mode = handler(self)

    def set_cursor(self, mode=None):
        if (self.forced_cursor is not None):
            self.SetCursor(self.forced_cursor)
            #
            return

        if mode is None:
            mode = self.mouse_mode
        c = mode.get_cursor()
        self.SetCursor(c)

    def get_effective_tool_mode(self, event):
        middle_down = False
        alt_down = False
        if (event is not None):
            try:
                alt_down = event.AltDown()
                # print self.is_alt_key_down
            except:
                pass
            try:
                middle_down = event.MiddleIsDown()
            except:
                pass
        if alt_down or middle_down:
            mode = self.default_pan_mode
        else:
            mode = self.mouse_mode
        return mode

    def release_mouse(self):
        self.mouse_is_down = False
        self.selection_box_is_being_defined = False
        while self.HasCapture():
            self.ReleaseMouse()

    def on_left_down(self, evt):
        # self.SetFocus() # why would it not be focused?
        mode = self.get_effective_tool_mode(evt)
        self.forced_cursor = None
        self.selection_box_is_being_defined = False
        self.mouse_down_position = evt.GetPosition()
        self.mouse_move_position = self.mouse_down_position

        mode.process_left_down(evt)
        self.set_cursor(mode)
        evt.Skip()

    def on_motion(self, evt):
        mode = self.get_effective_tool_mode(evt)
        log.debug("on_motion: effective mode=%s" % mode)
        if evt.LeftIsDown():
            mode.process_mouse_motion_down(evt)
        else:
            mode.process_mouse_motion_up(evt)
        self.set_cursor(mode)
        evt.Skip()

    def on_left_up(self, evt):
        mode = self.get_effective_tool_mode(evt)
        self.forced_cursor = None
        mode.process_left_up(evt)
        self.set_cursor(mode)
        evt.Skip()

    def on_left_dclick(self, evt):
        # self.SetFocus() # why would it not be focused?
        mode = self.get_effective_tool_mode(evt)
        mode.process_left_dclick(evt)
        self.set_cursor(mode)
        evt.Skip()

    def on_popup(self, evt):
        mode = self.get_effective_tool_mode(evt)
        self.forced_cursor = None
        mode.process_popup(evt)
        self.set_cursor(mode)

    def on_mouse_wheel(self, evt):
        mode = self.get_effective_tool_mode(evt)
        mode.process_mouse_wheel(evt)
        self.set_cursor(mode)

    def on_mouse_enter(self, evt):
        self.set_cursor()
        evt.Skip()

    def on_mouse_leave(self, evt):
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.mouse_mode.process_mouse_leave(evt)
        evt.Skip()

    def on_key_char(self, evt):
        mode = self.get_effective_tool_mode(evt)
        self.set_cursor(mode)

        mode.process_key_char(evt)
        evt.Skip()

    def on_focus(self, evt):
        mode = self.get_effective_tool_mode(evt)
        mode.process_focus(evt)

    def on_focus_lost(self, evt):
        mode = self.get_effective_tool_mode(evt)
        mode.process_focus_lost(evt)

