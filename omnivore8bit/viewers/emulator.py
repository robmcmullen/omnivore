import os
import sys
from collections import namedtuple

import numpy as np
import wx

from traits.api import on_trait_change, Bool, Undefined

import omni8bit.atari800 as a8

from omnivore.utils.wx import compactgrid as cg
from omnivore.utils.command import DisplayFlags
from ..byte_edit.segments import SegmentList
from ..ui.segment_grid import SegmentVirtualGridControl, SegmentVirtualTable, SegmentGridTextCtrl
from . import SegmentViewer
from .info import BaseInfoViewer

import logging
log = logging.getLogger(__name__)


class EmulatorViewer(SegmentViewer):
    viewer_category = "Emulator"

    has_caret = False

    # effectively don't allow emulator screen viewers to use the priority
    # refresh; they will always be explicitly refreshed with the
    # emulator_update_screen_event
    priority_refresh_frame_count = 10000000

    @property
    def emulator(self):
        return self.linked_base.editor.document.emulator

    @property
    def linked_base_segment_identifier(self):
        return ""

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

    def update_window_title(self):
        pass

    @on_trait_change('linked_base.editor.document.emulator_update_screen_event')
    def process_emulator_update_screen(self, evt):
        log.debug("process_emulator_update_screen for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.control.show_frame(force=True)
            self.update_window_title()


class Atari800Viewer(EmulatorViewer):
    name = "atari800"

    pretty_name = "Atari 800"

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        return a8.BitmapScreen(parent, linked_base.emulator)

    def show_caret(self, control, index, bit):
        pass

    @property
    def window_title(self):
        return f"{self.pretty_name} (frame {self.linked_base.emulator.current_frame_number})"

    def update_window_title(self):
        self.update_caption()
        # FIXME: probably shouldn't know this much about the internals to call
        # blah.blah.title_bar
        self.control.GetParent().title_bar.Refresh()

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0


class CPU6502Table(SegmentVirtualTable):
    want_col_header = True
    want_row_header = False

    col_labels = ["A", "X", "Y", "N", "V", "-", "B", "D", "I", "Z", "C", "SP", "PC"]
    col_sizes = [2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 4]
    p_bit = [0, 0, 0, 0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01, 0]

    # cpu state is not necessarily in "A,X,Y,SP..." order, so use the dtype
    # names of the cpu state array to look up which positions they should be
    # mapped to. The array below is the default from atari800 which is
    # a, p, sp, x, y, _, pc. It's overridden below in compute_col_lookup
    col_from_cpu_state = [0, 3, 4, 1, 1, 1, 1, 1, 1, 1, 1, 2, 6]

    def get_data_style_view(self, linked_base):
        data = linked_base.emulator.cpu_state
        self.compute_col_lookup(data.dtype)
        return data, data

    def compute_col_lookup(self, dtype):
        print(dtype)
        label_lookup = {label:i for i,label in enumerate(dtype.names)}
        col_from_cpu_state = [0] * len(self.col_labels)
        for i, d in enumerate(self.col_labels):
            if d in "NV-BDIZC":
                d = "P"
            if d in label_lookup:
                col_from_cpu_state[i] = label_lookup[d]
        self.col_from_cpu_state = col_from_cpu_state

    def get_value_style(self, row, col):
        val = self.data[self.col_from_cpu_state[col]]
        if col < 3 or col == 11:
            text = "%02x" % val
        elif col < 11:
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

    @property
    def linked_base_segment_identifier(self):
        return ""

    def show_caret(self, control, index, bit):
        pass


class CPU6502Viewer(CPUParamTableViewer):
    name = "cpu6502"

    pretty_name = "6502 CPU Registers"

    override_table_cls = CPU6502Table


class DtypeTable(SegmentVirtualTable):
    emulator_dtype_name = "<from subclass>"
    col_labels = ["value"]
    col_sizes = [4]
    want_col_header = False
    want_row_header = True
    verbose = False

    def get_data_style_view(self, linked_base):
        data = linked_base.emulator.calc_dtype_data(self.emulator_dtype_name)
        print((data.dtype.names))
        return data, data

    def calc_labels(self):
        self.row_labels = []
        offsets = []
        self.label_char_width = 1
        for i, label in enumerate(self.data.dtype.names):
            if label.startswith("_") and not self.verbose:
                continue
            self.row_labels.append(label)
            offsets.append(i)
            size = len(label)
            if size > self.label_char_width:
                self.label_char_width = size
        self.row_offsets_into_data = np.asarray(offsets, dtype=np.int32)
        self.num_rows = len(self.row_labels)

    def get_row_label_text(self, start_line, num_lines, step=1):
        last_line = min(start_line + num_lines, self.num_rows)
        for line in range(start_line, last_line, step):
            yield self.row_labels[line]

    def calc_row_label_width(self, view_params):
        return max([view_params.calc_text_width(r) for r in self.row_labels])

    def get_value_style(self, row, col):
        val = self.data[self.row_offsets_into_data[row]]
        try:
            text = "%02x" % val
        except TypeError:
            text = "..."
        return text, 0

    def get_label_at_index(self, index):
        return self.emulator_dtype_name


# This dynamically creates clases based on the emulator-defined dtypes.
#
# Each resulting class looks like this ANTIC example, except for everywhere
# that ANTIC appears, the other class name is substituted. Much repetition! So,
# instead, we create the classes in a loop.
#
# class ANTICTableViewer(CPUParamTableViewer):
#     name = "antic"
#     pretty_name = "ANTIC Registers"
#     override_table_cls = type('ANTICTable', (DtypeTable,), {'emulator_dtype_name': 'ANTIC'})

for dtype_name in ['ANTIC', 'GTIA', 'POKEY', 'PIA']:
    clsname = '%sViewer' % dtype_name
    cls = type(clsname, (CPUParamTableViewer,), {
        'name': dtype_name.lower(),
        'pretty_name': '%s Registers' % dtype_name,
        'override_table_cls': type('%sTable' % dtype_name, (DtypeTable,), {'emulator_dtype_name': dtype_name}),
        })
    globals()[clsname] = cls
