"""Popup window created as a child of a window and controlled by showing and
hiding the subwindow.

"""

import os, sys, struct, queue, threading, time, socket
from io import StringIO

import wx
import wx.stc

import logging
log = logging.getLogger(__name__)


class PopupSubWindow(wx.Window):
    """Transient status bar that displays status text in a popup
    
    Unlike a wx.StatusBar window that uses a constant amount of screen real-
    estate, the PopupStatusBar displays status info in a temporary popup
    that is displayed on the bottom of the frame.
    
    Status text is always overwritten with updates to the status text.  Status
    text is designed to be used for repetitive updates in response to an event;
    for example, to update coordinates when the mouse is moved.
    """
    def __init__(self, parent, target, side=wx.LEFT|wx.BOTTOM):
        """Creates (but doesn't show) the PopupStatusBar
        
        target is a sibling window; that is: target and this window share the
        same parent
        """
        wx.Window.__init__(self, parent, -1, name="PopupStatusWindow of %s" % parent.GetName(), pos=(0,0), size=(200, 15))
        self.target_window = target
        self.SetBackgroundColour("#B6C1FF")

        self.status = wx.StaticText(self, -1, "", style = wx.BORDER_NONE)
        self.Hide()

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
            self.Hide()
            pass

    def position_and_show(self):
        target = self.target_window
        tx, ty = target.GetPosition()
        tw, th = target.GetSize()
        w, h = self.GetSize()
        x = tx
        y = ty + th - h
        self.SetPosition((x, y))
        if w > tw:
            self.SetSize(tw, h)
        log.debug("target pos:%s, size=%s  popup pos:%s size=%s  text=%s" % (str((tx, ty)), str((tw, th)), str((x, y)), str((w, h)), self.status.GetLabelText()))
        self.Show(True)


    def clear(self):
        """Remove all messages and hide the popup"""
        self.show_status_text("")


if __name__ == "__main__":
    import wx.stc

    logging.basicConfig(level=logging.DEBUG)

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

    text = TestSTC(panel, -1)
    text.SetText("Just a placeholder here.\nThe real action is on the borders\nand in the popup status bar.\n\nWhen the text cursor is in any column\nother than zero, the popup status\nbar will show the location.")
    sizer.Add(text, 1, wx.EXPAND)

    panel.status = PopupSubWindow(panel, text)

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
