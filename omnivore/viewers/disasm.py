import os
import sys

import numpy as np

import wx

from sawx.ui import compactgrid as cg
from ..editors.linked_base import VirtualTableLinkedBase

from ..ui.segment_grid import SegmentGridControl, SegmentTable

from ..viewer import SegmentViewer

from .commands import MiniAssemblerCommand
from ..disassembler.miniasm import get_miniasm
from ..utils import searchutil

import logging
log = logging.getLogger(__name__)


class DisassemblyTable(SegmentTable):
    column_labels = ["Label", "Disassembly", "Comment"]
    column_sizes = [5, 12, 30]

    def __init__(self, linked_base):
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
                    comments.append(s.get_comment_at(i))
                if comments:
                    text = " ".join([str(c) for c in comments])
                else:
                    text = ""
            elif col == 3:
                text = str(e[row]['disassembler_type'])
            else:
                text = f"r{row}c{col}"
            for i in range(index, index + e[row]['num_bytes']):
                style |= s.style[i]
        else:
            text = ""
        # print(f"get_value_style: {row},{col} = {index} {self.last_valid_index} {self.is_index_valid(index)} ; {text}, {style}, {self.linked_base.segment}")
        return text, style

    def prepare_for_drawing(self, start_row, visible_rows, start_cell, visible_cells):
        self.parsed = self.current.stringify(start_row, visible_rows, self.linked_base.document.labels)

    def search(self, search_bytes, match_case=False):
        return self.current.search(search_bytes, match_case, self.linked_base.document.labels)

    def rebuild(self):
        segment = self.linked_base.segment
        self.current = self.linked_base.document.disassembler.parse(segment, self.max_num_entries)
        self.parsed = None
        self.init_boundaries()
        print(f"new num_rows: {self.num_rows}, {segment}")


class DisassemblyControl(SegmentGridControl):
    default_table_cls = DisassemblyTable

    def calc_default_table(self, linked_base):
        return self.default_table_cls(linked_base)

    def calc_line_renderer(self):
        return cg.VirtualTableLineRenderer(self, 2, widths=self.default_table_cls.column_sizes, col_labels=self.default_table_cls.column_labels)

    def recalc_view(self):
        self.table.rebuild()
        super().recalc_view()

    def calc_ranges_for_edit(self):
        table = self.table
        ranges = []
        for c in self.caret_handler.carets:
            r = c.range_including_caret
            start, _ = table.get_index_range(*r[0])
            _, end = table.get_index_range(*r[1])
            row1, _ = table.index_to_row_col(start)
            row2, _ = table.index_to_row_col(end - 1)
            if row1 == row2:
                # single line selected, so pass a singly byte so moving from a
                # multi-byte op (e.g. JSR) to fewer bytes doesn't result in
                # more than one op
                ranges.append((start, start + 1))
            else:
                # multiple lines passes entire range, MiniAssemblerCommand
                # handdles possible overlaps
                ranges.append((start, end))
        return ranges

    def calc_edit_command(self, val):
        cmd = MiniAssemblerCommand(self.segment_viewer.segment, self.segment_viewer.document.cpu, self.caret_handler, val, advance=True)
        return cmd

    def advance_caret_position(self, evt, flags):
        self.caret_handler.move_carets_vertically(self.table, 1)

    def verify_keycode_can_start_edit(self, c):
        miniasm = get_miniasm(self.segment_viewer.document.cpu)
        return miniasm.can_start_edit(c)


# Disassembly searcher uses the __call__ method to return the object because it
# needs access to the particular viewer's CPU type and disassembly table.
# Normal searchers just use the segment's raw data and returns itself in the
# constructor.
class DisassemblySearcher(searchutil.BaseSearcher):
    def __init__(self, viewer):
        self.search_text = None
        self.matches = []
        self.table = viewer.table
        self.ui_name = viewer.document.cpu

    def __call__(self, editor, search_text, search_copy):
        self.search_text = self.get_search_text(search_text)
        if len(self.search_text) > 0:
            self.matches = self.get_matches(editor)
        else:
            self.matches = []
        return self

    def __str__(self):
        return f"{self.ui_name} matches: {self.matches}"

    def get_matches(self, editor):
        match_case = editor.last_search_settings.get('match_case', False)
        search_bytes = self.search_text
        if not match_case:
            search_bytes = search_bytes.lower()
        matches = self.table.search(search_bytes, match_case)
        log.debug("instruction matches: %s" % str(matches))
        return matches


class DisassemblyViewer(SegmentViewer):
    name = "disasm"

    ui_name = "Static Disassembly"

    control_cls = DisassemblyControl

    # initialization

    # properties

    @property
    def table(self):
        return self.control.table

    @property
    def searchers(self):
        # Replace the normal viewer searcher class attribute with a searcher
        # that is custom to the cpu shown in this viewer
        return [DisassemblySearcher(self)]

    def set_event_handlers(self):
        self.document.cpu_changed_event += self.on_cpu_changed
        super().set_event_handlers()

    def on_cpu_changed(self, evt):
        self.recalc_view()
        self.refresh_view(True)

    def refresh_view_for_value_change(self, flags):
        self.table.rebuild()

    def refresh_view_for_style_change(self, flags):
        self.table.rebuild()

    def recalc_data_model(self):
        self.control.recalc_view()
