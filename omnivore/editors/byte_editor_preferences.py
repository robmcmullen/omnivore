import sys

import wx

from sawx.preferences import SawxFrameworkPreferences, str_to_font, def_font, cached_property


def byte2hex(val):
    return "$02x" % val

def word2hex(val):
    return "$04x" % val

def int2hex(val):
    return "%x" % val

byte2str = byte2hex
word2str = word2hex
int2str = int2hex

class ByteEditorPreferences(SawxFrameworkPreferences):
    def __init__(self):
        SawxFrameworkPreferences.__init__(self)

        # int_display_format = Enum(
        #     "Hexadecimal",
        #     "Decimal",
        #     "Both",
        # )

        # hex_display_format = Enum(
        #     "$XX",
        #     "0xXX",
        #     "XXh",
        # )

        self.image_caches = {}
        self.header_font = str_to_font(def_font + "bold")
        self.hex_grid_lower_case = True
        self.assembly_lower_case = False
        self.disassembly_column_widths = (0, 0, 0)
        self.map_width_low = 1
        self.map_width_high = 256
        self.map_width = 40
        self.bitmap_width_low = 1
        self.bitmap_width_high = 16
        self.bitmap_width = 1
        self.hex_grid_width_low = 1
        self.hex_grid_width_high = 256
        self.hex_grid_width = 16
        self.highlight_background_color = wx.Colour(100, 200, 230)
        self.data_background_color = wx.Colour(224, 224, 224)
        self.match_background_color = wx.Colour(255, 255, 180)
        self.comment_background_color = wx.Colour(255, 180, 200)
        self.error_background_color = wx.Colour(255, 128, 128)
        self.diff_text_color = wx.Colour(255, 0, 0)
        self.unfocused_caret_color = wx.Colour(128, 128, 128)
        self.row_header_bg_color = wx.Colour(224, 224, 224)
        self.col_header_bg_color = wx.Colour(224, 224, 224)
        self.col_label_border_width = 3
        self.row_label_border_width = 3
        self.row_height_extra_padding = -3
        self.base_cell_width_in_chars = 2
        self.pixel_width_padding = 2
        self.caret_pen = wx.Pen(self.unfocused_caret_color, 1, wx.SOLID)
        self.selected_brush = wx.Brush(self.highlight_background_color, wx.SOLID)
        self.normal_brush = wx.Brush(self.background_color, wx.SOLID)
        self.data_brush = wx.Brush(self.data_background_color, wx.SOLID)
        self.match_brush = wx.Brush(self.match_background_color, wx.SOLID)
        self.comment_brush = wx.Brush(self.comment_background_color, wx.SOLID)
        self.empty_brush = wx.Brush(self.empty_background_color, wx.SOLID)

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
