import os
import sys

import wx

import logging
log = logging.getLogger(__name__)
mouselog = logging.getLogger("mouse")

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
        self.canvas = window
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
    
    def get_cursor(self):
        return wx.StockCursor(wx.CURSOR_ARROW)

    def process_left_down(self, evt):
        evt.Skip()

    def get_position(self, evt):
        return evt.GetPosition()
    
    def process_mouse_motion_up(self, evt):
        self.canvas.release_mouse()
        evt.Skip()

    def process_mouse_motion_down(self, evt):
        evt.Skip()
    
    def reset_early_mouse_params(self):
        self.mouse_up_too_close = False
        self.after_first_mouse_up = False
    
    def check_early_mouse_release(self, evt):
        c = self.canvas
        p = evt.GetPosition()
        dx = p[0] - self.first_mouse_down_position[0]
        dy = p[1] - self.first_mouse_down_position[1]
        tol = self.mouse_too_close_pixel_tolerance
        if abs(dx) < tol and abs(dy) < tol:
            return True
        return False

    def process_left_up(self, evt):
        c = self.canvas
        c.release_mouse()  # it's hard to know for sure when the mouse may be captured
        c.selection_box_is_being_defined = False

    def process_left_dclick(self, evt):
        evt.Skip()

    def process_popup(self, evt):
        actions = self.get_popup_actions(evt)
        if actions:
            self.canvas.editor.popup_context_menu_from_actions(self.canvas, actions)
    
    def get_popup_actions(self, evt):
        return None
        
    def process_mouse_wheel(self, evt):
        c = self.canvas
        e = c.editor
        rotation = evt.GetWheelRotation()
        delta = evt.GetWheelDelta()
        window = evt.GetEventObject()
        mouselog.debug("on_mouse_wheel_scroll. rot=%s delta=%d win=%s" % (rotation, delta, window))
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
        c = self.canvas
        if (evt.GetKeyCode() == wx.WXK_ESCAPE):
            self.esc_key_pressed()
        elif evt.GetKeyCode() == wx.WXK_DELETE:
            self.delete_key_pressed()
        elif evt.GetKeyCode() == wx.WXK_BACK:
            self.backspace_key_pressed()
        else:
            evt.Skip()
    
    def esc_key_pressed(self):
        self.canvas.project.clear_all_selections()
    
    def delete_key_pressed(self):
        pass
    
    def backspace_key_pressed(self):
        pass
