import os
import sys

import numpy as np

import wx

from traits.api import on_trait_change, Bool, Undefined, Any, Instance

from atrcopy import DefaultSegment

from omnivore.utils.wx import compactgrid as cg
from omnivore8bit.byte_edit.linked_base import VirtualLinkedBase

from ..ui.segment_grid import SegmentGridControl

from . import SegmentViewer

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
            yield "%04x" % (emu.cpu_history[line][0])

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
        segment = DefaultSegment(emu.cpu_history.entries.view(np.uint8))
        v.segment = segment
        print("CPU HISTORY ENTRIES", self.current_num_rows)
        self.init_boundaries()


class InstructionHistoryGridControl(SegmentGridControl):
    default_table_cls = InstructionHistoryTable

    def calc_default_table(self):
        return self.default_table_cls(self.caret_handler)

    def calc_line_renderer(self):
        return cg.VirtualTableLineRenderer(self, 2, widths=self.default_table_cls.column_sizes, col_labels=self.default_table_cls.column_labels)

    def recalc_view(self):
        self.table.rebuild()
        cg.CompactGrid.recalc_view(self)

    def refresh_view(self):
        if self.IsShown():
            log.debug("refreshing %s" % self)
            if self.table.needs_rebuild:
                self.recalc_view()
            else:
                SegmentGridControl.refresh_view(self)
        else:
            log.debug("skipping refresh of hidden %s" % self)


class InstructionHistoryViewer(SegmentViewer):
    name = "cpuhistory"

    pretty_name = "Instruction History"

    control_cls = InstructionHistoryGridControl

    # trait defaults

    # initialization

    @classmethod
    def replace_linked_base(cls, linked_base):
        # the new linked base decouples the cursor here from the other segments
        segment = DefaultSegment(np.arange(400, dtype=np.uint8))
        return VirtualLinkedBase(editor=linked_base.editor, segment=segment)

    # properties

    @property
    def table(self):
        return self.control.table

    @on_trait_change('linked_base.editor.document.byte_values_changed')
    def byte_values_changed(self, index_range):
        log.debug("byte_values_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.table.rebuild()

    @on_trait_change('linked_base.editor.document.byte_style_changed')
    def byte_style_changed(self, index_range):
        log.debug("byte_style_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.table.rebuild()

    def recalc_data_model(self):
        self.table.rebuild()

    def do_priority_level_refresh(self):
        self.control.recalc_view()
        self.refresh_view(True)
