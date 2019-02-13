import sys

import wx

from omnivore_framework.preferences import OmnivoreFrameworkPreferences, Bool, Dict, Enum, List, Str, Unicode, Int, Font, Range, Tuple, Color, Any, Property, cached_property

if sys.platform == "darwin":
    def_font = "10 point Monaco"
elif sys.platform == "win32":
    def_font = "10 point Lucida Console"
else:
    def_font = "10 point monospace"


def byte2hex(val):
    return "$02x" % val

def word2hex(val):
    return "$04x" % val

def int2hex(val):
    return "%x" % val

byte2str = byte2hex
word2str = word2hex
int2str = int2hex

class ByteEditorPreferences(OmnivoreFrameworkPreferences):
    image_caches = Property(Dict, depends_on='text_font')

    header_font = Font(def_font + " bold")

    hex_grid_lower_case = Bool(True)

    assembly_lower_case = Bool(False)

    int_display_format = Enum(
        "Hexadecimal",
        "Decimal",
        "Both",
    )

    hex_display_format = Enum(
        "$XX",
        "0xXX",
        "XXh",
    )

    disassembly_column_widths = Tuple(0, 0, 0)

    map_width_low = 1
    map_width_high = 256
    map_width = Range(low=map_width_low, high=map_width_high, value=40)

    bitmap_width_low = 1
    bitmap_width_high = 16
    bitmap_width = Range(low=bitmap_width_low, high=bitmap_width_high, value=1)

    hex_grid_width_low = 1
    hex_grid_width_high = 256
    hex_grid_width = Range(low=hex_grid_width_low, high=hex_grid_width_high, value=16)

    highlight_background_color = Color(wx.Colour(100, 200, 230))

    data_background_color = Color(wx.Colour(224, 224, 224))

    match_background_color = Color(wx.Colour(255, 255, 180))

    comment_background_color = Color(wx.Colour(255, 180, 200))

    error_background_color = Color(wx.Colour(255, 128, 128))

    diff_text_color = Color(wx.Colour(255, 0, 0))

    unfocused_caret_color = Color(wx.Colour(128, 128, 128))
    
    row_header_bg_color = Color(wx.Colour(224, 224, 224))
    
    col_header_bg_color = Color(wx.Colour(224, 224, 224))

    col_label_border_width = Int(3)

    row_label_border_width = Int(3)

    row_height_extra_padding = Int(-3)

    base_cell_width_in_chars = Int(2)

    pixel_width_padding = Int(2)
    
    caret_pen = Any

    selected_brush = Any
    
    normal_brush = Any
    
    data_brush = Any
    
    match_brush = Any
    
    comment_brush = Any
    
    empty_brush = Any

    def _caret_pen_default(self):
        return wx.Pen(self.unfocused_caret_color, 1, wx.SOLID)

    def _selected_brush_default(self):
        return wx.Brush(self.highlight_background_color, wx.SOLID)

    def _normal_brush_default(self):
        return wx.Brush(self.background_color, wx.SOLID)

    def _data_brush_default(self):
        return wx.Brush(self.data_background_color, wx.SOLID)

    def _match_brush_default(self):
        return wx.Brush(self.match_background_color, wx.SOLID)

    def _comment_brush_default(self):
        return wx.Brush(self.comment_background_color, wx.SOLID)

    def _empty_brush_default(self):
        return wx.Brush(self.empty_background_color, wx.SOLID)

    @cached_property
    def _get_image_caches(self):
        return dict()

    def calc_cell_size_in_pixels(self, chars_per_cell):
        width = self.pixel_width_padding * 2 + self.text_font_char_width * chars_per_cell
        height = self.row_height_extra_padding + self.text_font_char_height
        return width, height

    def calc_text_width(self, text):
        return self.text_font_char_width * len(text)

    def calc_image_cache(self, cache_cls):
        try:
            c = self.image_caches[cache_cls]
        except KeyError:
            c = cache_cls(self)
            self.image_caches[cache_cls] = c
        return c

    @property
    def hex_format_character(self):
        return "x" if self.hex_grid_lower_case else "X"
