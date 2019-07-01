import os
import sys

import wx

from ..ui.segment_grid import SegmentGridControl, SegmentTable
from sawx.ui import compactgrid as cg
from ..arch.disasm import get_style_name

from ..viewer import SegmentViewer

import logging
log = logging.getLogger(__name__)


hex_digits_on_keypad=[
    wx.WXK_NUMPAD0, wx.WXK_NUMPAD1, wx.WXK_NUMPAD2, wx.WXK_NUMPAD3,
    wx.WXK_NUMPAD4, wx.WXK_NUMPAD5, wx.WXK_NUMPAD6, wx.WXK_NUMPAD7,
    wx.WXK_NUMPAD8, wx.WXK_NUMPAD9
    ]

def is_valid_hex_digit(key):
    return key in hex_digits_on_keypad or (key>=ord('0') and key<=ord('9')) or (key>=ord('A') and key<=ord('F')) or (key>=ord('a') and key<=ord('f'))

def get_valid_hex_digit(key):
    if key in hex_digits_on_keypad:
        return chr(ord('0') + key - wx.WXK_NUMPAD0)
    elif (key>=ord('0') and key<=ord('9')) or (key>=ord('A') and key<=ord('F')) or (key>=ord('a') and key<=ord('f')):
        return chr(key)
    else:
        return None


class HexTextCtrl(cg.GridCellTextCtrl):
    def __init__(self, parent, id, *args, **kwargs):
        # Don't use the validator here, because apparently we can't
        # reset the validator based on the columns.  We have to do the
        # validation ourselves using EVT_KEY_DOWN.
        super().__init__(parent, id, 2, *args, **kwargs)

    def is_valid_keycode(self, keycode):
        return is_valid_hex_digit(keycode)

    def get_processed_value(self):
        text = self.GetValue()
        print(("text value: %s" % text))
        return int(text, 16)


class HexEditControl(SegmentGridControl):
    """
    View for editing in hexidecimal notation.
    """
    short_name = "hex"

    def set_viewer_defaults(self):
        self.items_per_row = self.view_params.hex_grid_width

    def verify_keycode_can_start_edit(self, c):
        return get_valid_hex_digit(c)

    def create_hidden_text_ctrl(self):
        c = HexTextCtrl(self, -1, pos=(600,100), size=(400,24))
        return c


class HexEditViewer(SegmentViewer):
    name = "hex"

    ui_name = "Hex"

    control_cls = HexEditControl

    has_hex = True

    has_width = True

    def recalc_data_model(self):
        """Rebuild the data model after a document formatting (or other
        structural change) or loading a new document.
        """
        self.control.recalc_view()

    def update_carets(self, flags):
        pass
