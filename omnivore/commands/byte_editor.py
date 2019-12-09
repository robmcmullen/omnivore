import numpy as np

from . import SetSelectionCommand, SetRangeCommand, ChangeStyleCommand, SetRangeValueModifyIndexesCommand
from sawx.utils.permute import bit_reverse_table

from atrip.disassembler import mini_assemble

import logging
log = logging.getLogger(__name__)


class SetValueCommand(SetSelectionCommand):
    short_name = "set_value"
    ui_name = "Set Value"


class ZeroCommand(SetSelectionCommand):
    short_name = "zero"
    ui_name = "Zero Bytes"

    def __init__(self, segment, current_selection):
        super().__init__(segment, current_selection, 0)


class FFCommand(SetSelectionCommand):
    short_name = "ff"
    ui_name = "FF Bytes"

    def __init__(self, segment, current_selection):
        super().__init__(segment, current_selection, 0xff)


class NOPCommand(SetSelectionCommand):
    short_name = "nop"
    ui_name = "NOP Bytes"


class SetHighBitCommand(SetSelectionCommand):
    short_name = "set_high_bit"
    ui_name = "Set High Bit"

    def get_data(self, orig):
        return np.bitwise_or(orig, 0x80)


class ClearHighBitCommand(SetSelectionCommand):
    short_name = "clear_high_bit"
    ui_name = "Clear High Bit"

    def get_data(self, orig):
        return np.bitwise_and(orig, 0x7f)


class BitwiseNotCommand(SetSelectionCommand):
    short_name = "bitwise_not"
    ui_name = "Bitwise NOT"

    def get_data(self, orig):
        return np.invert(orig)


class OrWithCommand(SetSelectionCommand):
    short_name = "or_value"
    ui_name = "OR With"

    def get_data(self, orig):
        return np.bitwise_or(orig, self.data)


class AndWithCommand(SetSelectionCommand):
    short_name = "and_value"
    ui_name = "AND With"

    def get_data(self, orig):
        return np.bitwise_and(orig, self.data)


class XorWithCommand(SetSelectionCommand):
    short_name = "xor_value"
    ui_name = "XOR With"

    def get_data(self, orig):
        return np.bitwise_xor(orig, self.data)


class LeftShiftCommand(SetSelectionCommand):
    short_name = "left_shift"
    ui_name = "Left Shift"

    def get_data(self, orig):
        return np.left_shift(orig, 1)


class RightShiftCommand(SetSelectionCommand):
    short_name = "right_shift"
    ui_name = "Right Shift"

    def get_data(self, orig):
        return np.right_shift(orig, 1)


class LeftRotateCommand(SetSelectionCommand):
    short_name = "left_rotate"
    ui_name = "Left Rotate"

    def get_data(self, orig):
        rotated = np.right_shift(np.bitwise_and(orig, 0x80), 7)
        return np.bitwise_or(np.left_shift(orig, 1), rotated)


class RightRotateCommand(SetSelectionCommand):
    short_name = "right_rotate"
    ui_name = "Right Rotate"

    def get_data(self, orig):
        rotated = np.left_shift(np.bitwise_and(orig, 0x01), 7)
        return np.bitwise_or(np.right_shift(orig, 1), rotated)


class ReverseBitsCommand(SetSelectionCommand):
    short_name = "reverse_bits"
    ui_name = "Reverse Bits"

    def get_data(self, orig):
        return bit_reverse_table[orig]


class RandomBytesCommand(SetSelectionCommand):
    short_name = "random_bytes"
    ui_name = "Random Bytes"

    def get_data(self, orig):
        return np.random.randint(0, 256, len(orig), dtype=np.uint8)


class RampUpCommand(SetSelectionCommand):
    short_name = "ramp_up"
    ui_name = "Ramp Up"

    def get_data(self, orig):
        num = np.alen(orig)
        if type(self.data) == slice:
            first = self.data.start
            last = self.data.stop
            if last == -1:
                last = self.data.start + num
        else:
            first = self.data
            last = self.data + num
        step = (last - first) / num
        print(f"range: {first}, {last}, {step}")
        return np.arange(first, last, step)


class RampDownCommand(SetSelectionCommand):
    short_name = "ramp_down"
    ui_name = "Ramp Down"

    def get_data(self, orig):
        num = np.alen(orig)
        if type(self.data) == slice:
            first = self.data.start
            last = self.data.stop
            if last == -1:
                last = self.data.start - num
        else:
            first = self.data
            last = self.data - num
        step = (last - first) / num
        return np.arange(first, last, step)


class AddValueCommand(SetSelectionCommand):
    short_name = "add_value"
    ui_name = "Add"

    def get_data(self, orig):
        return orig + self.data


class SubtractValueCommand(SetSelectionCommand):
    short_name = "subtract_value"
    ui_name = "Subtract"

    def get_data(self, orig):
        return orig - self.data


class SubtractFromCommand(SetSelectionCommand):
    short_name = "subtract_from"
    ui_name = "Subtract From"

    def get_data(self, orig):
        return self.data - orig


class MultiplyCommand(SetSelectionCommand):
    short_name = "multiply"
    ui_name = "Multiply"

    def get_data(self, orig):
        return orig * self.data


class DivideByCommand(SetSelectionCommand):
    short_name = "divide"
    ui_name = "Divide By"

    def get_data(self, orig):
        return orig // self.data


class DivideFromCommand(SetSelectionCommand):
    short_name = "divide_from"
    ui_name = "Divide From"

    def get_data(self, orig):
        return self.data // orig


class ReverseSelectionCommand(SetSelectionCommand):
    short_name = "reverse_selection"
    ui_name = "Reverse Selection"

    def get_data(self, orig):
        return orig[::-1,...]


class ReverseGroupCommand(SetSelectionCommand):
    short_name = "reverse_group"
    ui_name = "Reverse In Groups"

    def get_data(self, orig):
        num = len(orig)
        chunk = self.data
        num_groups = num // chunk
        indexes = np.arange(num)
        if num_groups > 0:
            # have to handle special case: can't do indexes[9:-1:-1] !!!
            indexes[0:chunk] = indexes[self.data-1::-1]
            for i in range(1,num_groups):
                start = i * chunk
                indexes[start:start+chunk] = indexes[start+chunk-1:start-1:-1]
        print(num, chunk, num_groups, indexes)
        return orig[indexes]


class ApplyTraceSegmentCommand(ChangeStyleCommand):
    short_name = "applytrace"
    ui_name = "Apply Trace to Segment"

    def get_style(self, editor):
        v = editor.focused_viewer
        trace, mask = v.get_trace(save=True)
        self.clip(trace)
        style_data = (self.segment.style[self.start_index:self.end_index].copy() & mask) | trace
        return style_data

    def set_undo_flags(self, flags):
        flags.byte_values_changed = True
        flags.index_range = self.start_index, self.end_index


class ClearTraceCommand(ChangeStyleCommand):
    short_name = "cleartrace"
    ui_name = "Clear Current Trace Results"

    def get_style(self, editor):
        mask = self.segment.get_style_mask(match=True)
        style_data = (self.segment.style[:].copy() & mask)
        return style_data

    def update_can_trace(self, editor):
        editor.can_trace = False


class SetLabelCommand(ChangeStyleCommand):
    short_name = "set_comment"
    ui_name = "Label"
    serialize_order =  [
            ('segment', 'int'),
            ('addr', 'addr'),
            ('label', 'string'),
            ]

    def __init__(self, segment, addr, label):
        ChangeStyleCommand.__init__(self, segment)
        self.addr = addr
        self.label = label

    def __str__(self):
        if len(self.label) > 20:
            text = self.label[:20] + "..."
        else:
            text = self.label
        return "%s: %s" % (self.ui_name, text)

    def do_change(self, editor, undo):
        old = self.segment.memory_map.get(self.addr, None)
        self.segment.memory_map[self.addr] = self.label
        return old

    def undo_change(self, editor, old_data):
        if old_data is None:
            self.segment.memory_map.pop(self.addr, "")
        else:
            self.segment.memory_map[self.addr] = old_data


class ClearLabelCommand(ChangeStyleCommand):
    short_name = "clear_comment"
    ui_name = "Remove Label"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ]

    def __init__(self, segment, ranges):
        ChangeStyleCommand.__init__(self, segment)
        print(ranges)
        self.ranges = ranges

    def do_change(self, editor, undo):
        print(self.ranges)
        indexes = ranges_to_indexes(self.ranges)
        origin = self.segment.origin
        old = {}
        for i in indexes:
            addr = i + origin
            old[addr] = self.segment.memory_map.get(addr, None)
            self.segment.memory_map.pop(addr, "")
        return old

    def undo_change(self, editor, old_data):
        if old_data is not None:
            indexes = ranges_to_indexes(self.ranges)
            for addr, label in old_data.iteritems():
                if label is None:
                    self.segment.memory_map.pop(addr, "")
                else:
                    self.segment.memory_map[addr] = label
