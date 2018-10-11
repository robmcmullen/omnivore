import wx
import wx.lib.buttons as buttons

from pyface.api import ImageResource


class GenToggleButtonEvent(wx.PyCommandEvent):
    """Event sent from the generic buttons when the button is activated. """
    def __init__(self, eventType, id, pressed, evt_obj):
        wx.PyCommandEvent.__init__(self, eventType, id)
        self.pressed = pressed
        self.evt_obj = evt_obj

    def Checked(self):
        return self.pressed

    IsChecked = Checked

    def GetEventObject(self):
        return self.evt_obj

        btn.SetToolTip("Case sensitive match")


class FlatBitmapToggleButton(buttons.GenBitmapToggleButton):
    def __init__(self, parent, id, icon_name, pressed=False, tooltip_prefix="Toggle", *args, **kwargs):
        buttons.GenBitmapToggleButton.__init__(self, parent, -1, None, style=wx.BORDER_NONE)
        self.SetValue(pressed)
        self.tooltip_prefix = tooltip_prefix
        img = ImageResource(icon_name)
        bmp = img.create_bitmap()
        self.SetBitmapLabel(bmp)
        self.SetInitialSize()
        self.set_tooltip()

    def InitColours(self):
        buttons.GenBitmapToggleButton.InitColours(self)
        faceClr = self.GetBackgroundColour()
        r, g, b, a = faceClr.Get()
        fr, fg, fb = max(0,r-32), max(0,g-32), max(0,b-32)
        self.faceDnClr = wx.Colour(fr, fg, fb, a)

    def Notify(self):
        evt = GenToggleButtonEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.GetId(), not self.up, self)
        self.GetEventHandler().ProcessEvent(evt)
        self.set_tooltip()

    def set_tooltip(self):
        state = "off" if self.up else "on"
        if self.tooltip_prefix:
            state = "%s: %s" % (self.tooltip_prefix, state)
        self.SetToolTip(state)
