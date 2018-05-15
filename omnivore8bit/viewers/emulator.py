import os
import sys
from collections import namedtuple

import wx

from traits.api import on_trait_change, Bool, Undefined

import pyatari800 as a8

from omnivore.utils.wx import compactgrid as cg
from ..byte_edit.segments import SegmentList
from ..ui.segment_grid import SegmentVirtualGridControl, SegmentVirtualTable, SegmentGridTextCtrl
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


class CPU6502Table(SegmentVirtualTable):
    col_labels = ["A", "X", "Y", "SP", "N", "V", "-", "B", "D", "I", "Z", "C", "PC"]
    col_from_cpu_state = [0, 3, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1, 6]  # a, p, sp, x, y, _, pc
    col_sizes = [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 4]
    p_bit = [0, 0, 0, 0, 0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01]

    def get_data_style_view(self, linked_base):
        data = linked_base.emulator.cpu_state
        return data, data

    def get_value_style(self, row, col):
        val = self.data[self.col_from_cpu_state[col]]
        if col < 4:
            text = "%02x" % val
        elif col < 12:
            text = self.col_labels[col] if val & self.p_bit[col] else "-"
        else:
            text = "%04x" % val
        return text, 0

    def get_label_at_index(self, index):
        return "cpu"


class CPUParamTableViewer(BaseInfoViewer):
    name = "<base class>"

    viewer_category = "Emulator"

    pretty_name = "<pretty name>"

    control_cls = SegmentVirtualGridControl

    @on_trait_change('linked_base.editor.document.emulator_update_event')
    def process_emulator_update(self, evt):
        log.debug("process_data_model_change for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.refresh_view()

    def show_caret(self, control, index, bit):
        pass


class CPU6502Viewer(CPUParamTableViewer):
    name = "cpu6502"

    pretty_name = "6502 CPU Registers"

    override_table_cls = CPU6502Table
