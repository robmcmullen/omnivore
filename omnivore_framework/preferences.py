import sys

import wx

from traits.api import HasTraits, Bool, Dict, Enum, List, Str, Unicode, Int, Range, Tuple, Any, Property, cached_property

from .third_party.traitsui.font_trait import WxFont
Font = WxFont

from .third_party.traitsui.color_trait import WxColor
Color = WxColor

if sys.platform == "darwin":
    def_font = "10 point Monaco"
elif sys.platform == "win32":
    def_font = "10 point Lucida Console"
else:
    def_font = "10 point monospace"


class OmnivoreFrameworkPreferences(HasTraits):
    # Font used for hex/disassembly
    text_font = Font(def_font)

    text_font_char_width = Property(Int, depends_on='text_font')
  
    text_font_char_height = Property(Int, depends_on='text_font')

    background_color = Color(wx.WHITE)

    text_color = Color(wx.BLACK)

    empty_background_color = Color(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get(False))

    @cached_property
    def _get_text_font_char_width(self):
        dc = wx.MemoryDC()
        dc.SetFont(self.text_font)
        return dc.GetCharWidth()

    @cached_property
    def _get_text_font_char_height(self):
        dc = wx.MemoryDC()
        dc.SetFont(self.text_font)
        return dc.GetCharHeight()
