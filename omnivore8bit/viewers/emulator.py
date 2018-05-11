import os
import sys
from collections import namedtuple

import wx

from traits.api import on_trait_change, Bool, Undefined

import pyatari800 as a8

from omnivore.utils.wx import compactgrid as cg
from ..byte_edit.segments import SegmentList
from ..ui.segment_grid import SegmentGridControl, SegmentTable, SegmentGridTextCtrl
from . import SegmentViewer
from .info import BaseInfoViewer

import logging
log = logging.getLogger(__name__)


class EmulatorViewer(SegmentViewer):
    viewer_category = "Emulator"

    has_caret = False

    def use_default_view_params(self):
        pass

    def restore_view_params(self, params):
        pass

    def update_toolbar(self):
        pass

    def recalc_data_model(self):
        # self.control.recalc_view()
        self.control.Refresh()

    def recalc_view(self):
        # self.control.recalc_view()
        self.control.Refresh()


class Atari800Viewer(EmulatorViewer):
    name = "atari800"

    pretty_name = "Atari 800"

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        return a8.BitmapScreen(parent, linked_base.emulator)

    def show_caret(self, control, index, bit):
        pass

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0


class CPU6502Table(cg.HexTable):
    column_labels = ["A", "X", "Y", "SP", "N", "V", "-", "B", "D", "I", "Z", "C", "PC"]
    column_sizes = [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 4]
    p_bit = [0, 0, 0, 0, 0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01]

    def __init__(self, linked_base):
        self.linked_base = linked_base
        dummy_data = [0] * 13
        cg.HexTable.__init__(self, dummy_data, dummy_data, 13)

    def calc_display_text(self, col, dummy):
        emu = self.linked_base.emulator
        vals = emu.get_cpu()
        if col < 4:
            text = "%02x" % vals[col]
        elif col < 12:
            text = self.column_labels[col] if vals[4] & self.p_bit[col] else "-"
        else:
            text = "%04x" % vals[5]
        return text

    def get_label_at_index(self, index):
        return "cpu"


class CPU6502GridControl(SegmentGridControl):
    col_labels = ["^A", "^X", "^Y", "^SP", "^N", "^V", "^-", "^B", "^D", "^I", "^Z", "^C", "^PC"]
    col_widths = [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 4]

    def calc_default_table(self):
        linked_base = self.caret_handler
        return CPU6502Table(linked_base)

    def calc_line_renderer(self):
        return cg.TableLineRenderer(self, 1, None, widths=self.col_widths, col_labels=self.col_labels)

    ##### editing

    def set_viewer_defaults(self):
        self.items_per_row = 13
        self.want_row_header = False

    def verify_keycode_can_start_edit(self, c):
        return get_valid_hex_digit(c)


class CPU6502Viewer(BaseInfoViewer):
    name = "cpu6502"
    viewer_category = "Emulator"

    pretty_name = "6502 CPU Registers"

    control_cls = CPU6502GridControl
