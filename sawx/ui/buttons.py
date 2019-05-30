import wx
import wx.lib.buttons as buttons
import wx.lib.colourselect as csel
import wx.lib.agw.cubecolourdialog as CCD

from .. import art

import logging
log = logging.getLogger(__name__)


EVT_COLORSELECT = csel.EVT_COLOURSELECT
ColorSelect = csel.ColourSelect
class AlwaysAlphaCCD(CCD.CubeColourDialog):
    def DoLayout(self):
        CCD.CubeColourDialog.DoLayout(self)
        self.mainSizer.Hide(self.showAlpha)


if wx.Platform == "__WXMAC__":
    color_dialog = wx.ColourDialog
else:
    color_dialog = AlwaysAlphaCCD


def prompt_for_rgba(parent, color, custom=None, use_float=False):
    data = wx.ColourData()
    data.SetChooseFull(True)
    if use_float:
        color = [a * 255 for a in color]
    data.SetColour(color)
    if custom is not None:
        for idx, clr in enumerate(custom.Colours):
            if clr is not None:
                data.SetCustomColour(idx, clr)

    dlg = color_dialog(wx.GetTopLevelParent(parent), data)
    changed = dlg.ShowModal() == wx.ID_OK

    if changed:
        data = dlg.GetColourData()
        color = data.GetColour()
        if use_float:
            color = [float(c / 255.0) for c in color]
        if custom is not None:
            custom.Colours = \
                [data.GetCustomColour(idx) for idx in range(0, 16)]
    else:
        color = None

    dlg.Destroy()
    return color


class ColorSelectButton(ColorSelect):
    SetColor = ColorSelect.SetColour

    def MakeBitmap(self):
        """ Creates a bitmap representation of the current selected colour. """

        bdr = 8
        width, height = self.GetSize()
        #print("button:", width, height)

        # yes, this is weird, but it appears to work around a bug in wxMac
        if "wxMac" in wx.PlatformInfo and width == height:
            height -= 1

        w = max(width - bdr, 1)
        h = max(height - bdr, 1)
        bmp = wx.Bitmap(w, h)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetFont(self.GetFont())
        label = self.GetLabel()
        # Just make a little colored bitmap
        fg = self.colour

        # bitmaps aren't able to use alpha, so  fake the alpha color on a white
        # background for the button color
        blend = tuple(wx.Colour.AlphaBlend(c, 255, fg.alpha / 255.0) for c in fg.Get(False))
        dc.SetBackground(wx.Brush(blend))
        dc.Clear()

        if label:
            # Add a label to it
            avg = functools.reduce(lambda a, b: a + b, self.colour.Get()) / 3
            fcolour = avg > 128 and wx.BLACK or wx.WHITE
            dc.SetTextForeground(fcolour)
            dc.DrawLabel(label, (0,0, w, h),
                         wx.ALIGN_CENTER)

        dc.SelectObject(wx.NullBitmap)
        return bmp

    def OnClick(self, event):
        color = prompt_for_rgba(self, self.colour, self.customColours)
        if color is not None:
            self.SetColour(color)
            self.OnChange()


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
        bmp = art.find_bitmap(icon_name)
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
