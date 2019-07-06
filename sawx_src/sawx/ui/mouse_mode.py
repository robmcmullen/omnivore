# Standard library imports.
import sys
import weakref

# Major package imports.
import wx

import logging
log = logging.getLogger(__name__)


class MouseMode(object):
    """
    Processing of mouse events, separate from the rendering window
    
    This is an object-based control system of mouse modes
    """
    icon = "help.png"
    menu_item_name = "Generic Mouse Mode"
    menu_item_tooltip = "Tooltip for generic mouse mode"
    editor_trait_for_enabled = ""

    mouse_too_close_pixel_tolerance = 5

    def __init__(self, window):
        self.control = weakref.proxy(window)
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

    def get_position(self, evt):
        return evt.GetPosition()

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

    ##### Sublasses need to override these for customized actions

    def process_mouse_motion_down(self, evt):
        evt.Skip()

    def process_left_down(self, evt):
        evt.Skip()

    def process_mouse_motion_up(self, evt):
        evt.Skip()

    def process_left_up(self, evt):
        evt.Skip()

    def process_left_dclick(self, evt):
        evt.Skip()

    def process_popup(self, evt):
        data = self.calc_popup_data(evt)
        actions = self.calc_popup_actions(evt, data)
        log.debug(f"process_popup: found actions {actions}")
        if actions:
            self.show_popup(actions, data)

    def calc_popup_data(self, evt):
        return None

    def calc_popup_actions(self, evt, data):
        return None

    def show_popup(self, actions):
        raise NotImplementedError("No popup method defined")

    def process_mouse_wheel(self, evt):
        c = self.control
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
            amount = (rotation + extra) // delta
            self.wheel_scroll_count -= abs(amount)
            if self.wheel_scroll_count > 0:
                return
            self.wheel_scroll_count = self.use_every_nth_wheel_scroll
        else:
            amount = rotation // delta

        if evt.ControlDown():
            if amount < 0:
                self.zoom_out(evt, amount)
            elif amount > 0:
                self.zoom_in(evt, amount)
        else:
            self.pan_mouse_wheel(evt, amount)

    def zoom_out(self, evt, amount):
        evt.Skip()

    def zoom_in(self, evt, amount):
        evt.Skip()

    def pan_mouse_wheel(self, evt, amount):
        self.control.pan_mouse_wheel(evt)

    def process_mouse_enter(self, evt):
        evt.Skip()

    def process_mouse_leave(self, evt):
        evt.Skip()

    def process_focus(self, evt):
        pass

    def process_focus_lost(self, evt):
        pass
