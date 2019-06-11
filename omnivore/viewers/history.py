import os
import sys

import numpy as np

import wx

from atrip import Container, Segment

from ..disassembler import flags
from ..disassembler import dtypes as dd

from sawx.ui import compactgrid as cg
from ..editors.linked_base import VirtualTableLinkedBase

from ..ui.segment_grid import SegmentGridControl

from ..viewer import SegmentViewer
from .emulator import EmulatorViewerMixin

import logging
log = logging.getLogger(__name__)



class InstructionHistoryTable(cg.VirtualTable):
    column_labels = ["^Instruction", "^Result"]
    column_sizes = [21, 12]

    def __init__(self, linked_base):
        self.virtual_linked_base = linked_base
        s = linked_base.segment
        self.current_num_rows = 0
        self.history_entries = None
        self.visible_history_start_row = 0
        self.visible_history_lookup_table = None
        cg.VirtualTable.__init__(self, len(self.column_labels), s.origin)

    def calc_num_rows(self):
        return self.current_num_rows

    def calc_last_valid_index(self):
        return self.current_num_rows * self.items_per_row

    def get_label_at_index(self, index):
        row = (index // self.items_per_row) - self.visible_history_start_row
        if row < 0:
            return "----"
        try:
            emu = self.virtual_linked_base.emulator
            return "%04x" % (emu.cpu_history[row][0])
        except IndexError:
            return "----"

    def get_row_label_text(self, start_line, num_lines, step=1):
        last_line = min(start_line + num_lines, self.num_rows)
        emu = self.virtual_linked_base.emulator
        for line in range(start_line, last_line, step):
            h = emu.cpu_history[line]
            t = h['disassembler_type']
            if t == flags.DISASM_NEXT_INSTRUCTION:
                h = h.view(dtype=dd.HISTORY_BREAKPOINT_DTYPE)
                t = h['disassembler_type_cpu']
            if t == flags.DISASM_ATARI800_HISTORY:
                h = h.view(dtype=dd.HISTORY_ATARI800_DTYPE)
                x = h['antic_xpos']
                y = h['antic_ypos']
                if x & 0x80:
                    x = x & 0x7f
                    y = y | 0x100
                yield "%3d %3d" % (y, x)
            elif t == flags.DISASM_FRAME_START or t == flags.DISASM_FRAME_END:
                h = h.view(dtype=dd.HISTORY_FRAME_DTYPE)
                f = h['frame_number']
                yield "f%d" % (f)
            else:
                yield "%d" % (emu.cpu_history[line][0])

    def calc_row_label_width(self, view_params):
        return view_params.calc_text_width("256 256")

    def get_value_style(self, row, col):
        t = self.parsed
        if t is None:
            return "", 0
        try:
            text = t[row - self.visible_history_start_row][col]
        except IndexError:
            print(f"tried row {row} out of {self.visible_history_lookup_table}")
            text = f"row {row} out of bounds"
        # style = s.style[index]
        style = 0
        return text, style

    def clear_selected_style(self):
        # self.style[:] &= (0xff ^ selected_bit_mask)
        pass

    def set_selected_index_range(self, index1, index2):
        # self.style[index1:index2] |= selected_bit_mask
        pass

    def prepare_for_drawing(self, start_row, visible_rows, start_cell, visible_cells):
        emu = self.virtual_linked_base.emulator
        self.visible_history_start_row = start_row
        self.parsed = emu.calc_stringified_history(start_row, visible_rows)

    @property
    def needs_rebuild(self):
        v = self.virtual_linked_base
        emu = v.emulator
        return not self.current_num_rows == emu.num_cpu_history_entries

    def rebuild(self):
        v = self.virtual_linked_base
        emu = v.emulator
        self.current_num_rows = len(emu.cpu_history)
        c = Container(emu.cpu_history.entries.view(np.uint8), force_numpy_data=True)
        v.segment = Segment(c, 0)
        print("CPU HISTORY ENTRIES", self.current_num_rows)
        self.init_boundaries()


class InstructionHistoryGridControl(SegmentGridControl):
    default_table_cls = InstructionHistoryTable

    def calc_default_table(self, linked_base):
        table = self.default_table_cls(linked_base)
        table.rebuild()  # find number of rows so scrollbars can be set properly
        return table

    def calc_line_renderer(self):
        return cg.VirtualTableLineRenderer(self, 2, widths=self.default_table_cls.column_sizes, col_labels=self.default_table_cls.column_labels)

    def move_viewport_to_bottom(self):
        self.move_viewport_origin((self.table.current_num_rows, 0))

    def recalc_view(self):
        log.debug(f"recalc_view: {self}")
        self.table.rebuild()
        cg.CompactGrid.recalc_view(self)
        self.move_viewport_to_bottom()

    def refresh_view(self):
        if self.IsShown():
            log.debug("refreshing %s" % self)
            if self.table.needs_rebuild:
                self.recalc_view()
            else:
                SegmentGridControl.refresh_view(self)
        else:
            log.debug("skipping refresh of hidden %s" % self)


class InstructionHistoryViewer(EmulatorViewerMixin, SegmentViewer):
    name = "cpuhistory"

    ui_name = "Instruction History"

    viewer_category = "Emulator"

    control_cls = InstructionHistoryGridControl

    priority_refresh_frame_count = 1

    # initialization

    @classmethod
    def replace_linked_base(cls, linked_base):
        # the new linked base decouples the cursor here from the other segments
        c = Container(np.arange(40, dtype=np.uint8))
        segment = Segment(c, 0)
        return VirtualTableLinkedBase(editor=linked_base.editor, segment=segment)

    def create_post(self):
        self.linked_base.table = self.control.table

    # properties

    @property
    def table(self):
        return self.control.table

    # @on_trait_change('linked_base.editor.document.byte_values_changed')
    def byte_values_changed(self, index_range):
        log.debug("byte_values_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.table.rebuild()

    # @on_trait_change('linked_base.editor.document.byte_style_changed')
    def byte_style_changed(self, index_range):
        log.debug("byte_style_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.table.rebuild()

    def recalc_data_model(self):
        self.table.rebuild()

    def do_priority_level_refresh(self):
        self.control.recalc_view()
        self.refresh_view(True)
