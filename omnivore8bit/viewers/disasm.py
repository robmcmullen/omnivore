import os
import sys

import numpy as np

import wx

from traits.api import on_trait_change, Bool, Undefined, Any, Instance

from atrcopy import DefaultSegment
from omni8bit.disassembler import DisassemblyConfig, flags

from omnivore.utils.wx import compactgrid as cg
from omnivore8bit.byte_edit.linked_base import VirtualLinkedBase

from ..ui.segment_grid import SegmentGridControl

from . import SegmentViewer

import logging
log = logging.getLogger(__name__)



class DisassemblyTable(cg.HexTable):
    column_labels = ["Label", "Disassembly", "Comment"]
    column_sizes = [5, 12, 30]

    def __init__(self, linked_base):
        self.linked_base = linked_base

        driver = DisassemblyConfig()
        driver.register_parser("6502", 0)
        driver.register_parser("data", 1)
        driver.register_parser("antic_dl", 2)
        driver.register_parser("jumpman_level", 3)
        driver.register_parser("jumpman_harvest", 4)
        self.driver = driver

        s = linked_base.segment
        cg.HexTable.__init__(self, s.data, s.style, len(self.column_labels), s.origin)

        self.max_num_entries = 80000
        self.rebuild()

    def calc_num_rows(self):
        try:
            return len(self.current)
        except AttributeError:
            return 0

    def get_index_range(self, row, cell):
        """Get the byte offset from start of file given row, col
        position.
        """
        e = self.current.entries
        index = e[row]['pc'] - self.current.origin
        return index, index + e[row]['num_bytes']

    def get_index_of_row(self, row):
        index, _ = self.get_index_range(row, 0)
        return index

    def get_start_end_index_of_row(self, row):
        index1, index2 = self.get_index_range(row, 0)
        return index1, index2

    def index_to_row_col(self, index):
        return self.current.index_to_row[index], 0

    def get_label_at_index(self, index):
        row, _ = self.index_to_row_col(index)
        return str(self.current.entries[row]['pc'])

    def get_row_label_text(self, start_line, num_lines, step=1):
        last_line = min(start_line + num_lines, self.num_rows)
        entries = self.current.entries
        for line in range(start_line, last_line, step):
            yield "%04x" % (entries[line]['pc'])

    def get_value_style(self, row, col):
        if col == 1:
            t = self.parsed
            if t is None:
                return "", 0
            text = t[row - t.start_index]
        elif col == 0:
            p = self.current
            e = p.entries
            addr = e[row]['pc']
            disassembler_type = p.labels[addr]
            if disassembler_type:
                text = "L%04x" % addr
            else:
                text = ""
        elif col == 2:
            e = self.current.entries
            text = str(e[row]['disassembler_type'])
        else:
            text = f"r{row}c{col}"
        s = self.linked_base.segment
        index, _ = self.get_index_range(row, col)
        if self.is_index_valid(index):
            style = s.style[index]
            return text, style
        return "", 0

    def prepare_for_drawing(self, start_row, visible_rows, start_cell, visible_cells):
        self.parsed = self.current.stringify(start_row, visible_rows)

    def rebuild(self):
        segment = self.linked_base.segment
        self.current = self.driver.parse(segment, self.max_num_entries)
        self.parsed = None
        self.init_boundaries()
        print(f"new num_rows: {self.num_rows}")


class DisassemblyControl(SegmentGridControl):
    default_table_cls = DisassemblyTable

    def calc_default_table(self):
        return self.default_table_cls(self.caret_handler)

    def calc_line_renderer(self):
        return cg.VirtualTableLineRenderer(self, 2, widths=self.default_table_cls.column_sizes, col_labels=self.default_table_cls.column_labels)

    def recalc_view(self):
        self.table.rebuild()
        cg.CompactGrid.recalc_view(self)


class DisassemblyViewer(SegmentViewer):
    name = "disasm"

    pretty_name = "Static Disassembly"

    control_cls = DisassemblyControl

    # trait defaults

    # initialization

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
