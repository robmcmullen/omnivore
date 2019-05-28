import os
import sys
from collections import namedtuple

import numpy as np
import wx

from ..ui.screen import BitmapScreen

from sawx.ui import compactgrid as cg
from sawx.utils.command import DisplayFlags
from ..ui import segment_grid as sg
from ..viewer import SegmentViewer
from .info import VirtualTableInfoViewer
from ..editors.linked_base import VirtualTableLinkedBase

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

    # @on_trait_change('linked_base.editor.document.emulator_update_screen_event')
    def process_emulator_update_screen(self, evt):
        log.debug("process_emulator_update_screen for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.control.show_frame(force=True)
            self.update_window_title()


class VideoViewer(EmulatorViewer):
    name = "video"

    ui_name = "Emulator Video Output"

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        return BitmapScreen(parent, linked_base.emulator)

    def show_caret(self, control, index, bit):
        pass

    @property
    def window_title(self):
        emu = self.linked_base.emulator
        return f"{emu.ui_name} (frame {emu.current_frame_number})"

    def update_window_title(self):
        self.update_caption()
        # FIXME: probably shouldn't know this much about the internals to call
        # blah.blah.title_bar
        self.control.GetParent().title_bar.Refresh()

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0


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


class CPUParamTableViewer(VirtualTableInfoViewer):
    name = "<base class>"

    viewer_category = "Emulator"

    ui_name = "<pretty name>"

    control_cls = sg.SegmentVirtualGridControl

    @property
    def linked_base_segment_identifier(self):
        return ""


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
        print((data.dtype.names))
        return data, data

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


from .disasm import labels1

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



class LabelViewer(SegmentViewer):
    name = "labels"

    viewer_category = "Emulator"

    ui_name = "Labels"

    control_cls = LabelGridControl

    @property
    def linked_base_segment_identifier(self):
        return ""
