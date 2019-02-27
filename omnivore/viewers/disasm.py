import os
import sys

import numpy as np

import wx

from atrcopy import DefaultSegment, not_user_bit_mask
from ..disassembler import DisassemblyConfig, flags

from omnivore_framework.utils.wx import compactgrid as cg
from ..editors.linked_base import VirtualTableLinkedBase

from ..ui.segment_grid import SegmentGridControl, SegmentTable

from ..viewer import SegmentViewer

import logging
log = logging.getLogger(__name__)


class DisassemblyTable(SegmentTable):
    column_labels = ["Label", "Disassembly", "Comment"]
    column_sizes = [5, 12, 30]

    def __init__(self, linked_base):
        driver = DisassemblyConfig()
        driver.register_parser("6502", 0)
        driver.register_parser("data", 1)
        driver.register_parser("antic_dl", 2)
        driver.register_parser("jumpman_level", 3)
        driver.register_parser("jumpman_harvest", 4)
        self.driver = driver

        SegmentTable.__init__(self, linked_base, len(self.column_labels), False)

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
        index, _ = self.get_index_range(row, col)
        style = 0
        if self.is_index_valid(index):
            s = self.linked_base.segment
            p = self.current
            e = p.entries
            if col == 1:
                t = self.parsed
                if t is None:
                    text = ""
                else:
                    text = t[row - t.start_index]
            elif col == 0:
                addr = e[row]['pc']
                has_label = p.jmp_targets[addr]
                if has_label:
                    text = "L%04x" % addr
                else:
                    text = ""
            elif col == 2:
                comments = []
                for i in range(index, index + e[row]['num_bytes']):
                    comments.append(s.get_comment(i))
                if comments:
                    text = " ".join([str(c) for c in comments])
                else:
                    text = ""
            elif col == 3:
                text = str(e[row]['disassembler_type'])
            else:
                text = f"r{row}c{col}"
            for i in range(index, index + e[row]['num_bytes']):
                style |= (s.style[i] & not_user_bit_mask)
        else:
            text = ""
        # print(f"get_value_style: {row},{col} = {index} {self.last_valid_index} {self.is_index_valid(index)} ; {text}, {style}, {self.linked_base.segment}")
        return text, style

    def prepare_for_drawing(self, start_row, visible_rows, start_cell, visible_cells):
        self.parsed = self.current.stringify(start_row, visible_rows, self.linked_base.document.labels)

    def rebuild(self):
        segment = self.linked_base.segment
        self.current = self.driver.parse(segment, self.max_num_entries)
        self.parsed = None
        self.init_boundaries()
        print(f"new num_rows: {self.num_rows}")


class DisassemblyControl(SegmentGridControl):
    default_table_cls = DisassemblyTable

    def calc_default_table(self, linked_base):
        return self.default_table_cls(linked_base)

    def calc_line_renderer(self):
        return cg.VirtualTableLineRenderer(self, 2, widths=self.default_table_cls.column_sizes, col_labels=self.default_table_cls.column_labels)

    def recalc_view(self):
        self.table.rebuild()
        super().recalc_view()


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

    def refresh_view_for_value_change(self, flags):
        self.table.rebuild()

    def refresh_view_for_style_change(self, flags):
        self.table.rebuild()

    def recalc_data_model(self):
        self.control.recalc_view()
