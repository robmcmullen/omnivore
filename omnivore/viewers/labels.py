import os
import sys
from collections import namedtuple

import numpy as np
import wx

from sawx.ui import compactgrid as cg
from ..ui import segment_grid as sg
from ..viewer import SegmentViewer
from .emulator import EmulatorViewerMixin

import logging
log = logging.getLogger(__name__)


from atrip.memory_map import MemoryMap
filename = "./omnivore/templates/atari800.labels"
try:
    labels1 = MemoryMap.from_file(filename)
except:
    log.warning("Can't find local labels for emulator labels test")
else:
    pass #print(labels1.labels)

class LabelTable(cg.VariableWidthHexTable):
    want_col_header = False
    want_row_header = True

    def __init__(self, linked_base):
        self.linked_base = linked_base

        s = linked_base.segment
        super().__init__(s.data, s.style, [], s.origin)
        self.rebuild()

    def size_of_entry(self, d):
        return d[2]

    def parse_table_description(self, desc):
        row_to_label_number = []
        items_per_row = []
        index_of_row = []
        row_of_index = []
        index = 0
        row = 0
        i = 0
        print(desc)
        try:
            self.row_to_label_number = desc.keys()
        except AttributeError:
            self.row_to_label_number = []
        for i in self.row_to_label_number:
            d = desc[i]
            s = self.size_of_entry(d)
            items_per_row.append(s)
            index_of_row.append(index)
            row_of_index.extend([row] * s)
            print(f"row_of_index: {d[0]} index={index}, s={s} {d}") #: {row_of_index}")
            # print(f"index_of_row: {index_of_row}")
            index += s
            row += 1
        self.index_of_row = index_of_row
        self.row_of_index = row_of_index
        self.items_per_row = items_per_row
        self.last_valid_index = index

    def get_row_label_text(self, start_line, num_lines, step=1):
        last_line = min(start_line + num_lines, self.num_rows)
        for line in range(start_line, last_line, step):
            yield self.labels[self.row_to_label_number[line]][0]

    def calc_row_label_width(self, view_params):
        return max([view_params.calc_text_width(r) for r in self.get_row_label_text(0, self.num_rows)])

    def calc_last_valid_index(self):
        pass  # calculated in init_table_description

    type_code_fmt = {
        0x00: "02x",  # hex byte
        0x01: "04x",  # hex word
        0x03: "08x",  # hex long
        0x30: "03d",  # dec byte
        0x31: "05d",  # dec word
        0x33: "010d",  # dec long
        0x40: "08b",  # bin byte
        0x41: "016b",  # bin word
        0x43: "032b",  # bin long
    }

    dtype_fmt = [
        None,
        np.uint8,
        np.uint16,
        np.uint32,
        np.uint32,
    ]

    def calc_cell_widths(self):
        cell_widths = [1] * self.num_rows
        for row in range(self.num_rows):
            label_num = self.row_to_label_number[row]
            type_code = self.labels[label_num][3]
            cell_widths[row] = len(format(0, self.type_code_fmt[type_code])) // 2  # each cell is 2 chars wide
        # print(cell_widths)
        return cell_widths

    def get_value_style(self, row, col):
        label_num = self.row_to_label_number[row]
        type_code = self.labels[label_num][3]
        bytes_per_col = (type_code & 0x03) + 1
        index = label_num + (col * bytes_per_col)
        dtype = self.dtype_fmt[bytes_per_col]
        try:
            value = int(self.data[index:index + bytes_per_col].view(dtype))
        except IndexError:
            text = ""
            style = 0
        else:
            style = self.style[index]
            text = format(value, self.type_code_fmt[type_code])
        return text, style

    def get_label_at_index(self, index):
        row = self.row_of_index[index]
        return self.labels[self.row_to_label_number[row]][0]

    def prepare_for_drawing(self, start_row, visible_rows, start_cell, visible_cells):
        # for i, item in enumerate(self.labels):
        #     print(i, item)
        pass

    def rebuild(self):
        self.labels = labels1.labels
        self.init_table_description(self.labels)
        self.init_boundaries()
        print(f"new num_rows: {self.num_rows}")


class LabelGridControl(sg.SegmentGridControl):
    default_table_cls = LabelTable
 
    def calc_default_table(self, linked_base):
        table = self.default_table_cls(linked_base)
        self.items_per_row = table.items_per_row
        self.want_row_header = table.want_row_header
        self.want_col_header = table.want_col_header
        return table

    def calc_line_renderer(self):
        print(self.table.items_per_row)
        return cg.VariableWidthLineRenderer(self, 2, self.table.items_per_row, self.table.calc_cell_widths())

    def recalc_view(self):
        log.debug(f"recalc_view: {self}")
        self.table.rebuild()
        self.line_renderer = self.calc_line_renderer()
        super().recalc_view()



class LabelViewer(EmulatorViewerMixin, SegmentViewer):
    name = "labels"

    viewer_category = "Emulator"

    ui_name = "Labels"

    control_cls = LabelGridControl

    @property
    def linked_base_segment_identifier(self):
        return ""
