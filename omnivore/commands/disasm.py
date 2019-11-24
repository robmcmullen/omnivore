import numpy as np

from . import SetSelectionCommand, SetRangeCommand

from atrip.disassembler import mini_assemble

import logging
log = logging.getLogger(__name__)


class SetDisasmCommand(SetRangeCommand):
    short_name = "set_disasm_type"
    ui_name = "Set Disassembler Type"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('disasm_type', 'int'),
            ]

    def __init__(self, segment, ranges, disasm_type):
        SetRangeCommand.__init__(self, segment, ranges)
        self.disasm_type = disasm_type

    def get_data(self, orig):
        return self.disasm_type

    def do_change(self, editor, undo):
        indexes = self.range_to_index_function(self.ranges)
        # print(f"{self.short_name}: ranges={self.ranges}, indexes={indexes}")
        undo.flags.index_range = indexes[0], indexes[-1]
        old_data = self.segment.disasm_type[indexes].copy()
        self.segment.disasm_type[indexes] = self.get_data(old_data)
        self.segment.update_data_style_from_disasm_type()
        if self.advance:
            undo.flags.advance_caret_position_in_control = editor.focused_viewer.control
        return old_data

    def undo_change(self, editor, old_data):
        indexes = self.range_to_index_function(self.ranges)
        self.segment.disasm_type[indexes] = old_data
        self.segment.update_data_style_from_disasm_type()


class MiniAssemblerCommand(SetSelectionCommand):
    short_name = "miniasm"
    ui_name = "Assemble"

    def __init__(self, segment, cpu, selection, data, advance=False):
        SetSelectionCommand.__init__(self, segment, selection, data, advance)
        self.cpu = cpu

    def change_data_at_indexes(self, indexes):
        new_data = np.empty(len(indexes) + 100, dtype=np.uint8)
        new_indexes = np.empty(len(indexes) + 100, dtype=np.uint32)
        total = 0
        indexes.sort()  # carets may be out of order, so force increasing
        next_valid_start = 0
        for index in indexes:
            if index < next_valid_start:
                # don't overwrite an instruction in the middle
                continue
            pc = self.segment.origin + index
            d = mini_assemble(self.cpu, self.data, pc)
            count = len(d)
            new_data[total:total + count] = d
            next_valid_start = index + count
            new_indexes[total:total + count] = np.arange(index, next_valid_start)
            total += count
        indexes = new_indexes[0:total]
        old_data = self.segment[indexes]
        self.segment[indexes] = new_data[0:total]
        return old_data, indexes
