import os
import sys
from collections import namedtuple

import numpy as np
import wx

from ..ui.screen import BitmapScreen

from sawx.ui import compactgrid as cg
from sawx.ui import checkpointtree as ct
from sawx.utils.command import DisplayFlags
from ..ui import segment_grid as sg
from ..viewer import SegmentViewer
from .info import VirtualTableInfoViewer
from ..editors.linked_base import VirtualTableLinkedBase

import logging
log = logging.getLogger(__name__)


class EmulatorViewerMixin:
    viewer_category = "Emulator"

    has_caret = False

    @property
    def emulator(self):
        return self.linked_base.editor.document.emulator

    @property
    def can_copy(self):
        return False

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
        self.update_caption()
        # FIXME: probably shouldn't know this much about the internals to call
        # blah.blah.title_bar
        self.control.GetParent().title_bar.Refresh()


class VideoViewer(EmulatorViewerMixin, SegmentViewer):
    name = "video"

    ui_name = "Emulator Video Output"

    has_caret = False

    # # effectively don't allow emulator screen viewers to use the priority
    # # refresh; they will always be explicitly refreshed with the
    # # emulator_update_screen_event
    # priority_refresh_frame_count = 10000000

    def set_event_handlers(self):
        # override SegmentViewer handlers, which skips the priority level
        # refresh
        self.document.emulator_breakpoint_event += self.on_emulator_breakpoint
        self.document.emulator_update_screen_event += self.on_emulator_update_screen

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        return BitmapScreen(parent, linked_base.emulator)

    def show_caret(self, control, index, bit):
        pass

    @property
    def window_title(self):
        emu = self.emulator
        return f"{emu.ui_name} (frame {emu.current_frame_number})"

    #### event handlers

    def on_emulator_update_screen(self, evt):
        log.debug("process_emulator_update_screen for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        self.do_emulator_update_screen()

    def do_emulator_update_screen(self):
        self.control.show_frame(force=True)
        self.update_window_title()

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0


class CheckpointViewer(EmulatorViewerMixin, SegmentViewer):
    name = "checkpoint"

    ui_name = "Checkpoint Viewer"

    has_caret = False

    priority_refresh_frame_count = 59 # about once per second

    def set_event_handlers(self):
        SegmentViewer.set_event_handlers(self)  # skip viewer mixin handlers, which skips the priority level refresh
        self.document.emulator_breakpoint_event += self.on_emulator_breakpoint
        self.document.emulator_update_screen_event += self.on_emulator_update_screen
        self.control.Bind(ct.EVT_CHECKPOINT_SELECTED, self.on_selected)
        self.control.Bind(ct.EVT_CHECKPOINT_RANGE_SELECTED, self.on_range_selected)

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        return ct.CheckpointTree(parent, linked_base.emulator)

    def show_caret(self, control, index, bit):
        pass

    @property
    def window_title(self):
        return "Emulator Checkpoints"

    def recalc_view(self):
        self.control.recalc_view()

    #### event handlers

    def on_selected(self, evt):
        print("RESTART SELECTED!", evt.GetRestartNumber(), evt.GetFrameNumber(), evt.GetLine())
        doc = self.document
        doc.pause_emulator()
        doc.checkpoint_restore(evt.GetRestartNumber(), evt.GetFrameNumber())
        self.editor.selected_checkpoint_range = None

    def on_range_selected(self, evt):
        print(f"RANGE SELECTED! {evt.start.frame_number}@{evt.start.restart_number} -> {evt.end.frame_number}@{evt.end.restart_number}")
        doc = self.document
        doc.pause_emulator()
        doc.checkpoint_restore(evt.end.restart_number, evt.end.frame_number)
        self.editor.selected_checkpoint_range = (evt.start, evt.end)

    def on_emulator_update_screen(self, evt):
        log.debug("process_emulator_update_screen for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        self.do_emulator_update_screen()

    def do_emulator_update_screen(self):
        self.control.recalc_view()
        self.control.refresh_view()


class CPU6502Table(sg.SegmentVirtualTable):
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

    def calc_last_valid_index(self):
        return self.items_per_row

    def get_data_style_view(self, linked_base):
        data = linked_base.emulator.cpu_state
        self.compute_col_lookup(data.dtype)
        return data, None

    def compute_col_lookup(self, dtype):
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
        return text, self.style[col]

    def get_label_at_index(self, index):
        return "cpu"


class CPUParamTableViewer(EmulatorViewerMixin, VirtualTableInfoViewer):
    name = ""

    viewer_category = "Emulator"

    ui_name = "<pretty name>"

    control_cls = sg.SegmentVirtualGridControl

    @property
    def linked_base_segment_identifier(self):
        return ""

    def recalc_view(self):
        self.control.recalc_view()


class CPU6502Viewer(CPUParamTableViewer):
    name = "cpu6502"

    ui_name = "6502 CPU Registers"

    override_table_cls = CPU6502Table


class DtypeTable(sg.SegmentVirtualTable):
    emulator_dtype_name = "<from subclass>"
    col_labels = ["hex", "dec", "bin"]
    col_sizes = [4, 4, 8]
    want_col_header = False
    want_row_header = True
    verbose = False

    def calc_num_rows(self):
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
        return len(self.row_labels)

    def calc_last_valid_index(self):
        return (self.items_per_row * self.num_rows) - 1

    def get_data_style_view(self, linked_base):
        data = linked_base.emulator.calc_dtype_data(self.emulator_dtype_name)
        return data, None

    def create_row_labels(self):
        # already generated above
        pass

    def get_row_label_text(self, start_line, num_lines, step=1):
        last_line = min(start_line + num_lines, self.num_rows)
        for line in range(start_line, last_line, step):
            yield self.row_labels[line]

    def calc_row_label_width(self, view_params):
        return max([view_params.calc_text_width(r) for r in self.row_labels])

    def get_value_style(self, row, col):
        val = self.data[self.row_offsets_into_data[row]]
        try:
            if col == 0:
                text = f"{val:02x}"
            elif col == 1:
                text = f"{val}"
            elif col == 2:
                text = f"{val:08b}"
            index, _ = self.get_index_range(row, col)
            style = self.style[index]
        except TypeError:
            text = "..."
            style = 0
        return text, style

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
#     ui_name = "ANTIC Registers"
#     override_table_cls = type('ANTICTable', (DtypeTable,), {'emulator_dtype_name': 'ANTIC'})

for dtype_name in ['ANTIC', 'GTIA', 'POKEY', 'PIA']:
    clsname = '%sViewer' % dtype_name
    cls = type(clsname, (CPUParamTableViewer,), {
        'name': dtype_name.lower(),
        'ui_name': '%s Registers' % dtype_name,
        'override_table_cls': type('%sTable' % dtype_name, (DtypeTable,), {'emulator_dtype_name': dtype_name}),
        })
    globals()[clsname] = cls
