#-----------------------------------------------------------------------------
# Name:        springtabs.py
# Purpose:     Tab-bar control that pops up windows when clicked
#
# Author:      Rob McMullen
#
# Created:     2008
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""SpringTabs

This module provides popup windows from a group of tabs.

Sometimes the popup won't properly close when clicking outside of the popup.
Certain controls seem to swallow the EVT_KILL_FOCUS event and without that
event propagating upwards, the sidebar handler never closes an open sidebar.
This seems to happen when the popup includes buttons or controls that are a
descendant of wx.PyControl.

In these cases, if the popup class defines the instance attribute
"lose_focus_helper_function" and binds all the offending controls to the
wx.EVT_KILL_FOCUS event with a callback function that calls the helper
function, the helper function will cause the popup to be dismissed.

class MyCoolSidebar(wx.ScrolledWindow):
    def __init__(...)
        ...
        btn = wx.Button(self, -i, "Button")
        btn.Bind(wx.EVT_KILL_FOCUS, self.on_lose_child_focus)

    def on_lose_child_focus(self, evt):
        evt.Skip()
        if self.lose_focus_helper_function is not None:
            self.lose_focus_helper_function(evt)

"""

import os, sys, struct, queue, threading, time, socket
from io import StringIO

import wx
import wx.stc
from wx.lib.buttons import GenToggleButton

import logging
log = logging.getLogger(__name__)


class FakePopupWindow(wx.MiniFrame):
    def __init__(self, parent, style=None):
        super(FakePopupWindow, self).__init__(parent, style = wx.NO_BORDER |wx.FRAME_FLOAT_ON_PARENT | wx.FRAME_NO_TASKBAR)
        #self.Bind(wx.EVT_KEY_DOWN , self.OnKeyDown)
        self.Bind(wx.EVT_CHAR, self.on_char)
        self.Bind(wx.EVT_SET_FOCUS, self.on_focus)

    # Superclass overrides

    def Position(self, position, size):
        #print("pos=%s size=%s" % (position, size))
        self.Move((position[0]+size[0], position[1]+size[1]))

    def SetPosition(self, position):
        #print("pos=%s" % (position))
        self.Move((position[0], position[1]))

    # Compatibility methods for wx.PopupTransientWindow

    def Popup(self):
        self.Show(True)

    def Dismiss(self):
        self.Show(False)

    # local methods

    def fix_sizer(self, child):
        pass

    def on_char(self, evt):
        #print("on_char: keycode=%s" % evt.GetKeyCode())
        self.GetParent().GetEventHandler().ProcessEvent(evt)

    def activate_parent(self):
        """Activate the parent window
        @postcondition: parent window is raised

        """
        parent = self.GetParent()
        parent.Raise()
        parent.SetFocus()

    def on_focus(self, evt):
        """Raise and reset the focus to the parent window whenever
        we get focus.
        @param evt: event that called this handler

        """
        #log.debug("on_focus: set focus to %s" % str(self.GetParent()))
        self.activate_parent()
        evt.Skip()


class RealPopupWindowMac(wx.PopupTransientWindow):
    # Superclass overrides

    def OnDismiss(self):
        print("DISMISSED!!!!!")
        wx.CallAfter(self.GetParent().clear_popup)

    # local methods

    def fix_sizer(self, child):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(child, 1, wx.EXPAND)
        self.SetSizer(sizer)


class RealPopupWindowWx(wx.PopupWindow):
    # Compatibility methods for wx.PopupTransientWindow

    def Popup(self):
        self.Show(True)

    def Dismiss(self):
        self.Show(False)

    # local methods

    def fix_sizer(self, child):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(child, 1, wx.EXPAND)
        self.SetSizer(sizer)


if sys.platform == "darwin":
    RealPopupWindow = RealPopupWindowMac
else:
    RealPopupWindow = FakePopupWindow


class SpringTabItemRenderer(object):
    # local methods

    def __init__(self):
        self.spacing_between_items = 8

    def on_paint(self, item, evt):
        (width, height) = item.GetClientSize().Get()
        x1 = y1 = 0
        x2 = width-1
        y2 = height-1

        dc = wx.PaintDC(item)
        log.debug("hover: %s %s" % (item.GetLabel(), item.hover))
        if item.hover:
            self.draw_hover_background(item, dc)
        else:
            brush = wx.Brush(item.face_background_color, wx.SOLID)
            dc.SetBackground(brush)
            dc.Clear()

        item.draw_label(dc, width, height)
        self.draw_hover_decorations(item, dc, width, height)

        #log.debug("button %s: pressed=%s" % (item.GetLabel(), not item.up))

    def draw_hover_background(self, item, dc):
        brush = wx.Brush(item.faceDnClr, wx.SOLID)
        dc.SetBackground(brush)
        dc.Clear()

    def draw_hover_decorations(self, item, dc, width, height):
        pass

    def draw_notification(self, dc, x, y, w, h, num, springtabs):
        if num > 99:
            s = "99+"
        else:
            s = str(num)
        tw, th = dc.GetTextExtent(s)
        dc.SetBrush(springtabs.notification_brush)
        dc.SetPen(springtabs.notification_pen)
        dc.SetTextBackground(springtabs.notification_background)
        dc.SetTextForeground(springtabs.notification_text)
        if tw > w - h/2:
            w2 = tw + h/2
            x -= (w2 - w) / 2
            w = w2
        dc.DrawRoundedRectangle(x, y, w, h, h / 2)
        dc.DrawText(s, x + w/2 - tw/2, y + h/2 - th/2)


class SpringTabItemVerticalRenderer(SpringTabItemRenderer):
    default_direction = "right"

    def __init__(self, popup_direction="default"):
        SpringTabItemRenderer.__init__(self)
        if popup_direction == "default":
            popup_direction = self.default_direction

        if popup_direction == "left":
            self.popleft = True
        elif popup_direction == "right":
            self.popleft = False
        else:
            raise TypeError("popup_direction %s not valid for vertical renderer" % popup_direction)

    # local methods

    def get_best_size(self, item):
        """
        Overridden base class virtual.  Determines the best size of the
        button based on the label and bezel size.
        """
        h, w, useMin = item._GetLabelSize()
        width = w + 2 * item.border + item.bezelWidth - 1
        height = h + 2 * item.border + item.bezelWidth - 1 + self.spacing_between_items
        #log.debug("width=%d height=%d" % (width, height))
        return (width, height)

    def draw_label(self, item, dc, width, height, dx=0, dy=0):
        dc.SetFont(item.GetFont())
        if item.IsEnabled():
            dc.SetTextForeground(item.GetForegroundColour())
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        label = item.GetLabel()
        th, tw = dc.GetTextExtent(label)
        #dc.DrawText(label, (width-tw)/2+dx, (height-th)/2+dy)
        if self.popleft:
            x = (width-tw)/2+dx + tw
            y = dy + item.border + self.spacing_between_items/2
            dc.DrawRotatedText(label, x, y, 270.0)
        else:
            x = (width-tw)/2+dx
            y = height + dy - item.border - self.spacing_between_items/2
            dc.DrawRotatedText(label, x, y, 90.0)
        num = item.notification_count
        if num > 0:
            parent = item.GetParent()
            dc.SetFont(parent.notification_font)
            tw, th = dc.GetTextExtent("0123456789")
            x = item.border
            w = width - 2*item.border
            h = th + 2*item.border
            if self.popleft:
                y = height - h - item.border
            else:
                y = item.border
            self.draw_notification(dc, x, y, w, h, num, parent)

    def set_popup_width(self, parent, popup, child):
        pw, ph = popup.GetSize().Get()
        pcw, pch = popup.GetClientSize().Get()
        try:
            cw, ch = child.DoGetBestSize()
        except AttributeError:
            cw, ch = child.GetSize().Get()
        log.debug("popup size=%s  popup client size=%s  child=%s" % (str((pw, ph)), str((pcw, pch)), str((cw, ch))))

        # The client size may be smaller than the popup window if the popup
        # has a border decoration.
        diffwidth =  pw - pcw
        diffheight =  ph - pch

        # The popup will be at least as tall as the SpringTabs panel
        width, height = parent.GetSize().Get()
        if ph < height:
            ph = height
        pw = min(cw + diffwidth, parent.max_popup_width)
        popup.SetSize(wx.Size(pw, ph))
        return width, height, pw, ph

    def show_popup(self, parent, item, show=True):
        popup, child = item.get_popup()
        if show:
            if hasattr(child, 'activate_spring_tab'):
                child.activate_spring_tab()
            elif hasattr(child, 'segment_viewer'):
                child.segment_viewer.activate_spring_tab()

            # Calculate the child's width twice because the popup itself may
            # not have a valid height the first time through if the popup has
            # never been shown before, and the popup height will be needed by
            # the child to calculate if a scrollbar is needed.
            self.set_popup_width(parent, popup, child)
            width, height, pw, ph = self.set_popup_width(parent, popup, child)

            x, y = parent.ClientToScreen(width, 0)
            if self.popleft:
                x -= width + pw
            #log.debug("popping up at %s" % str((x,y)))
            child.SetPosition(wx.Point(0, 0))
            popup.SetPosition(wx.Point(x, y))
            wx.CallAfter(item.set_popup_lose_focus)
            popup.Popup()
        else:
            popup.Dismiss()


class SpringTabItem(GenToggleButton):
    def __init__(self, parent, id=-1, label='', window_cb=None, available_cb=None, **kwargs):
        """Creates a springtab button
        
        This button on the springtab is linked to a callback function that
        creates a window on demand when the button is clicked.
        
        @param parent: parent window: a L{SpringTab} instance
        
        @param id: optional id of the new button
        
        @param label: label of the springtab button
        
        @param window_cb: callback to create the contents of the popup.  This
        functor will be passed two arguments: the first is the popup window
        determined from L{SpringTab.get_new_popup} to be used as the parent
        window for the popup contents.  The second argument is the kwargs dict.
        
        @param available_cb: callback to see if the button should be displayed
        in the L{SpringTab}.  This callback takes a single argument; the
        kwargs dict and should return a boolean indicating whether or not the
        button will be visible.
        
        @param kwargs: dict containing any keyword arguments necessary to
        create the popup contents or check for button availability.
        """
        self.border = 2
        self.hover = False

        GenToggleButton.__init__(self, parent, id, label)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)

        self.window_cb = window_cb
        self.available_cb = available_cb
        if self.available_cb:
            self.Show(self.available_cb(**kwargs))
        self.kwargs = kwargs
        self.popup = None
        self.notification_count = 0
        self.skip_next_lose_focus = False

    # Superclass overrides

    def InitColours(self):
        self.face_background_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        wx.Control.SetBackgroundColour(self, self.face_background_color)
        r, g, b, a = self.face_background_color.Get()
        log.debug("background: r,g,b,a: %s" % ((r,g,b,a),))
        fr, fg, fb = max(0,r-32), max(0,g-32), max(0,b-32)
        #log.debug(str((fr, fg, fb)))
        self.faceDnClr = wx.Colour(fr, fg, fb)
        sr, sg, sb = max(0,r-32), max(0,g-32), max(0,b-32)
        self.shadowPen = wx.Pen(wx.Colour(sr,sg,sb), 1, wx.SOLID)
        hr, hg, hb = min(255,r+64), min(255,g+64), min(255,b+64)
        self.highlightPen = wx.Pen(wx.Colour(hr,hg,hb), 1, wx.SOLID)
        self.focusClr = wx.Colour(hr, hg, hb)

    def DoGetBestSize(self):
        return self.GetParent().get_renderer().get_best_size(self)

    def OnPaint(self, evt):
        self.GetParent().get_renderer().on_paint(self, evt)

    def OnLeftDown(self, event):
        log.debug("clicked on %s" % self.GetLabel())
        if not self.IsEnabled():
            return
        self.saveUp = self.up
        self.up = not self.up
        self.GetParent().set_radio(self)
        self.SetFocus()
        self.Refresh()

    # local methods

    def draw_label(self, dc, width, height, dx=0, dy=0):
        self.GetParent().get_renderer().draw_label(self, dc, width, height, dx, dy)

    def set_toggle(self, flag, check_popup=True):
        self.up = not flag
        if self.up:
            # with PopupTransientWindow, need to force not hovering so it
            # doesn't take a second click to process
            self.hover = False
        if check_popup:
            self.GetParent().set_radio(self)
        self.Refresh()

    def on_enter(self, evt):
        self.hover = True
        self.Refresh()

    def on_leave(self, evt):
        self.hover = False
        self.Refresh()

    def get_popup(self):
        parent = self.GetParent()
        if self.popup is None:
            self.popup = parent.get_new_popup()
            self.popup.Bind(wx.EVT_ACTIVATE, self.on_activate)

            # Create the window using the popup as the parent
            self.window_cb(self.popup, parent.task, **self.kwargs)
            windowlist = self.popup.GetChildren()
            log.debug("Creating popup: %s" % windowlist)
            if len(windowlist) == 0:
                raise RuntimeError("Popup window creation failed!")
            child = windowlist[0]
            if hasattr(child, 'lose_focus_helper_function'):
                child.lose_focus_helper_function = self.on_lose_child_focus
            child.Bind(wx.EVT_KILL_FOCUS, self.on_lose_child_focus)
            if sys.platform != "darwin":
                child.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
            if sys.platform == "linux2":
                child.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
            self.popup.fix_sizer(child)
        windowlist = self.popup.GetChildren()
        if len(windowlist) == 0:
            raise RuntimeError("Popup window creation failed!")
        child = windowlist[0]
        return self.popup, child

    def on_char_hook(self, evt):
        """ESC handler that closes the popup

        """
        log.debug("on_char_hook: keycode=%s, popup=%s" % (evt.GetKeyCode(), evt.GetEventObject()))
        if evt.GetKeyCode() == wx.WXK_ESCAPE:
            wx.CallAfter(self.GetParent().cancel_popup)
        else:
            evt.Skip()

    def on_activate(self, evt):
        #log.debug("Activating %s: %s, shown=%s" % (self.GetLabel(), evt.GetActive(), self.popup.IsShown()))
        if self.popup.IsShown():
            evt.Skip()

    # Note: somehow, the name "set_popup_lose_focus_callback" was not working,
    # but removing the _callback worked. Something for another day.

    def set_popup_lose_focus(self):
        """Callback for use within wx.CallAfter to prevent focus being set
        after the control has been removed.
        """
        popup, child = self.get_popup()
        if popup.IsShown():
            #log.debug("setting focus to %s" % self.GetLabel())
            child.SetFocus()

    @property
    def is_shown(self):
        if self.popup is None:
            return False
        popup, child = self.get_popup()
        return popup.IsShown()

    @property
    def managed_window(self):
        if self.popup is None:
            return None
        popup, child = self.get_popup()
        return child

    def set_popup_lose_focus_callback(self):
        """Callback for use within wx.CallAfter to prevent focus being set
        after the control has been removed.
        """
        popup, child = self.get_popup()
        if popup.IsShown():
            log.debug("removing focus from %s" % self.GetLabel())
            self.GetParent().clear_popup()

    def on_lose_child_focus(self, evt):
        popup = evt.GetEventObject()
        focus = evt.GetWindow()
        log.debug("on_lose_child_focus: tab: %s, win=%s new=%s, top=%s" % (self.GetLabel(), popup, focus, wx.GetApp().GetTopWindow()))
        if self.skip_next_lose_focus:
            log.debug("Skipping next on_lose_child_focus; hack for popup menu!")
            self.skip_next_lose_focus = False
        elif popup is not None:
            if sys.platform == "linux2" or popup != focus:
                wx.CallAfter(self.set_popup_lose_focus_callback)

    def on_right_down(self, evt):
        self.skip_next_lose_focus = True
        evt.Skip()

    def recalc_notification(self):
        popup, child = self.get_popup()
        try:
            try:
                count = child.get_notification_count()
            except AttributeError:
                count = child.segment_viewer.get_notification_count()
            if count != self.notification_count:
                self.notification_count = count
                self.Refresh()
        except AttributeError:
            pass


class SpringTabs(wx.Panel):
    max_popup_width = 800

    def __init__(self, parent, task, *args, **kwargs):
        # Need to remove foreign keyword arguments
        vertical = True
        if 'orientation' in kwargs:
            if kwargs['orientation'] == 'horizontal':
                vertical = False
            del kwargs['orientation']
        popup_direction = 'default'
        if 'popup_direction' in kwargs:
            popup_direction = kwargs['popup_direction']
            del kwargs['popup_direction']
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.task = task

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        self._tabs = []
        if vertical:
            self._tab_renderer = SpringTabItemVerticalRenderer(popup_direction)
        else:
            raise RuntimeError("horizontal tab rendering not supported yet.")
        self._radio = None
        self._debug_paint = False
        self._popup_cls = RealPopupWindow

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self.init_colors()

    # local methods

    def on_size(self, evt):
        self.Refresh()
        evt.Skip()

    def init_colors(self):
        self.notification_background = wx.Colour(240, 120, 120)
        self.notification_brush = wx.Brush(self.notification_background, wx.SOLID)
        self.notification_pen = wx.Pen(self.notification_background, 1, wx.SOLID)
        self.notification_text = wx.Colour(255, 255, 255)
        self.notification_font = wx.Font(8, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.NORMAL)
        bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        self.SetBackgroundColour(bg)

    def get_renderer(self):
        return self._tab_renderer

    def set_radio(self, item):
        self._processing_radio = True
        if self._radio != item:
            self.clear_popup()
            self.popup_item(item)
        elif not item.GetToggle():
            self.clear_popup()

    def get_new_popup(self):
        popup = self._popup_cls(self)
        return popup

    def popup_item(self, item):
        self._radio = item
        #log.debug("Popping up %s" % item.GetLabel())
        self._tab_renderer.show_popup(self, item)

    def clear_popup(self, data=None):
        # uncomment this to show where the clear_popup is being called
        #import traceback
        #log.debug("".join(traceback.format_stack()))
        if self._radio is not None:
            #log.debug("Removing popup %s" % self._radio.GetLabel())
            self._tab_renderer.show_popup(self, self._radio, False)
            self._radio.set_toggle(False, check_popup=False)
        self._radio = None
        self.Refresh()

    def has_popup(self):
        return self._radio is not None

    def on_paint(self, evt):
        if self._debug_paint:
            dc = wx.PaintDC(self)

            size = self.GetClientSize()
            dc.SetFont(wx.NORMAL_FONT)
            dc.SetBrush(wx.WHITE_BRUSH)
            dc.SetPen(wx.WHITE_PEN)
            dc.DrawRectangle(0, 0, size.x, size.y)
            dc.SetPen(wx.LIGHT_GREY_PEN)
            dc.DrawLine(0, 0, size.x, size.y)
            dc.DrawLine(0, size.y, size.x, 0)

        evt.Skip()

    def add_tab(self, title, window_create_callback, window_available_callback=None, **kwargs):
        tab = SpringTabItem(self, label=title, window_cb=window_create_callback,available_cb=window_available_callback, **kwargs)
        self.GetSizer().Add(tab, 0, wx.EXPAND)
        self._tabs.append(tab)
        self.Layout()
        self.Refresh()

    def has_tabs(self):
        return bool(self._tabs)

    def delete_tabs(self):
        self.clear_popup()
        for tab in self._tabs:
            tab.Destroy()
        self._tabs = []

    def update_notifications(self):
        for tab in self._tabs:
            tab.recalc_notification()

    def cancel_popup(self):
        self.task.on_hide_minibuffer_or_cancel(None)



if sys.platform == "darwin":
    StatusPopupWindow = RealPopupWindowMac
else:
    StatusPopupWindow = RealPopupWindowWx

class PopupStatusBar(StatusPopupWindow):
    """Transient status bar that displays status text in a popup
    
    Unlike a wx.StatusBar window that uses a constant amount of screen real-
    estate, the PopupStatusBar displays status info in a temporary popup
    that is displayed on the bottom of the frame.
    
    Status text is always overwritten with updates to the status text.  Status
    text is designed to be used for repetitive updates in response to an event;
    for example, to update coordinates when the mouse is moved.
    
    To display menu help text like the wx.StatusBar does by default, capture
    the wx.EVT_MENU_HIGHLIGHT event and send the help text to the status bar
    using a method like:
    
    def OnMenuHighlight(self, evt):
        menu_id = evt.GetMenuId()
        if menu_id >= 0:
            help_text = self.GetMenuBar().GetHelpString(menu_id)
            if help_text:
                self.popup_status.showStatusText(help_text)

    """
    def __init__(self, frame):
        """Creates (but doesn't show) the PopupStatusBar
        
        @param frame: the parent frame
        
        @kwarg delay: (optional) delay in milliseconds before each message
        decays
        """
        StatusPopupWindow.__init__(self, frame)
        self.SetBackgroundColour("#B6C1FF")
        self.status = wx.StaticText(self, -1, "", style = wx.BORDER_NONE)
        self.do_hide()

    def show_status_text(self, text, multiline=False):
        """Display a status text string in the status popup.
        
        This method is intended to display text in response to a large number
        of updates to a similar actions, for example: updating x,y coordinates
        in response to mouse movement.  It is undesirable to keep these
        messages in the list as the list would quickly grow to display many
        lines.  Instead, status text updates replace any previous status
        updates at the bottom of the popup.
        
        This forces the popup to be displayed if it isn't currently displayed.
        If the popup is displayed and other messages are present, the existing
        messages are moved up and this status text is inserted at the bottom.
        
        @param text: message to display
        """
        if multiline:
            text = text.replace("\r\n", "\n").replace("\n", "\n").replace("\r", "\n")
        else:
            text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        self.status.SetLabelText(text)
        if text:
            self.position_and_show()
        else:
            self.do_hide()

    def position_and_show(self):
        frame = self.GetParent()
        frame_offset = frame.GetClientAreaOrigin()
        frame_pos = frame.ClientToScreen(frame_offset[0], frame_offset[1])
        frame_size = frame.GetClientSize().Get()
        w, h = self.status.GetSize()
        print(("frame pos: %s, size=%s  popup size=%s" % (str(frame_pos), str(frame_size), str((w, h)))))
        x = frame_pos[0]
        y = frame_pos[1] + frame_size[1] - h
        if w > frame_size[0]:
            w = frame_size[0]
        self.SetSize(x, y, w, h)
        self.do_show()

    def clear(self):
        """Remove all messages and hide the popup"""
        self.show_status_text("")

    def do_hide(self):
        self.SetSize(-10000,-10000,10,10)
        self.Show()

    def do_show(self):
        pass


if __name__ == "__main__":
    from wx.adv import CalendarCtrl
    import wx.stc

    logging.basicConfig(level=logging.DEBUG)

    class FontList(wx.Panel):
        def __init__(self, parent, *args, **kwargs):
            wx.Panel.__init__(self, parent, -1)

            e = wx.FontEnumerator()
            e.EnumerateFacenames()
            list = e.GetFacenames()

            list.sort()

            self.lb1 = wx.ListBox(self, -1, wx.DefaultPosition, (200, 250),
                                 list, wx.LB_SINGLE)

            self.Bind(wx.EVT_LISTBOX, self.OnSelect, id=self.lb1.GetId())

            self.txt = wx.StaticText(self, -1, "Sample text...", (285, 50))

            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(self.txt, 0, wx.EXPAND)
            sizer.Add(self.lb1, 0, wx.EXPAND|wx.TOP, 20)

            self.SetSizer(sizer)
            self.Fit()
            self.Layout()
            log.debug(self.GetSize())

            self.lb1.SetSelection(0)
            self.OnSelect(None)
            wx.CallLater(300, self.SetTextSize)

        def SetTextSize(self):
            self.txt.SetSize(self.txt.GetBestSize())

        def OnSelect(self, evt):
            face = self.lb1.GetStringSelection()
            font = wx.Font(28, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, face)
            self.txt.SetLabel(face)
            self.txt.SetFont(font)
            if wx.Platform == "__WXMAC__": self.Refresh()

    def ButtonCB(parent, task, **kwargs):
        button = GenToggleButton(parent, -1, "Whatevar!!!")

    def CalendarCB(parent, task, **kwargs):
        CalendarCtrl(parent, -1, wx.DateTime.Now())

    class TestSTC(wx.stc.StyledTextCtrl):
        def __init__(self, *args, **kwargs):
            wx.stc.StyledTextCtrl.__init__(self, *args, **kwargs)
            self.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnUpdateUI)

        def OnUpdateUI(self, evt):
            """Specific OnUpdateUI callback for those modes that use an actual
            STC for their edit window.
            
            Adds things like fold level and style display.
            """
            linenum = self.GetCurrentLine()
            pos = self.GetCurrentPos()
            col = self.GetColumn(pos)
            status = "Line: %d Column: %d Position: %d" % (linenum, col, pos)
            if col == 0:
                status = ""
            self.GetParent().status.show_status_text(status)
            evt.Skip()

    app = wx.App()
    frm = wx.Frame(None,-1,"Test",style=wx.TAB_TRAVERSAL|wx.DEFAULT_FRAME_STYLE,
                   size=(600,400))
    panel = wx.Panel(frm)
    sizer = wx.BoxSizer(wx.HORIZONTAL)

    # spring tabs for the left side
    tabs1 = SpringTabs(panel, None)
    tabs1.add_tab("Calendar", CalendarCB)
    tabs1.add_tab("Fonts", FontList)
    tabs1.add_tab("Three", ButtonCB)
    sizer.Add(tabs1, 0, wx.EXPAND)

    text = TestSTC(panel, -1)
    text.SetText("Just a placeholder here.\nThe real action is on the borders\nand in the popup status bar.\n\nWhen the text cursor is in any column\nother than zero, the popup status\nbar will show the location.")
    sizer.Add(text, 1, wx.EXPAND)

    panel.status = PopupStatusBar(text)

    # spring tabs for the rigth side
    tabs2 = SpringTabs(panel, None, popup_direction="left")
    tabs2.add_tab("Calendar", CalendarCB)
    tabs2.add_tab("Five", ButtonCB)
    tabs2.add_tab("Six", ButtonCB)
    sizer.Add(tabs2, 0, wx.EXPAND)

    def fixFocus(evt):
        evt.Skip()
    text.Bind(wx.EVT_SET_FOCUS, fixFocus)

    panel.SetAutoLayout(True)
    panel.SetSizer(sizer)
    #sizer.Fit(panel)
    #sizer.SetSizeHints(panel)
    panel.Layout()
    app.SetTopWindow(frm)
    frm.Show()
    app.MainLoop()
