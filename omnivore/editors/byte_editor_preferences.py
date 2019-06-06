import sys

import wx

from sawx.preferences import SawxEditorPreferences
from sawx.ui.fonts import str_to_font, default_font


def byte2hex(val):
    return "$02x" % val

def word2hex(val):
    return "$04x" % val

def int2hex(val):
    return "%x" % val

byte2str = byte2hex
word2str = word2hex
int2str = int2hex

class ByteEditorPreferences(SawxEditorPreferences):
    def set_defaults(self):
        SawxEditorPreferences.set_defaults(self)

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

        self.hex_grid_lower_case = True
        self.assembly_lower_case = False
        self.disassembly_column_widths = (0, 0, 0)
        self.default_cpu = "6502"
        self.map_width_low = 1
        self.map_width_high = 256
        self.map_width = 40
        self.bitmap_width_low = 1
        self.bitmap_width_high = 16
        self.bitmap_width = 1
        self.hex_grid_width_low = 1
        self.hex_grid_width_high = 256
        self.hex_grid_width = 16
        self.text_copy_stringifier = "basic_data"

    @property
    def hex_format_character(self):
        return "x" if self.hex_grid_lower_case else "X"
