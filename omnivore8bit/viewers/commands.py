import numpy as np

from ..commands import SetRangeCommand, SetRangeValueCommand, ChangeStyleCommand
from omnivore.utils.permute import bit_reverse_table

import logging
log = logging.getLogger(__name__)


class SetValueCommand(SetRangeValueCommand):
    short_name = "set_value"
    pretty_name = "Set Value"


class ZeroCommand(SetRangeValueCommand):
    short_name = "zero"
    pretty_name = "Zero Bytes"

    def __init__(self, segment, ranges):
        SetRangeValueCommand.__init__(self, segment, ranges, 0)


class FFCommand(SetRangeValueCommand):
    short_name = "ff"
    pretty_name = "FF Bytes"

    def __init__(self, segment, ranges):
        SetRangeValueCommand.__init__(self, segment, ranges, 0xff)


class NOPCommand(SetRangeValueCommand):
    short_name = "nop"
    pretty_name = "NOP Bytes"


class SetHighBitCommand(SetRangeCommand):
    short_name = "set_high_bit"
    pretty_name = "Set High Bit"

    def get_data(self, orig):
        return np.bitwise_or(orig, 0x80)


class ClearHighBitCommand(SetRangeCommand):
    short_name = "clear_high_bit"
    pretty_name = "Clear High Bit"

    def get_data(self, orig):
        return np.bitwise_and(orig, 0x7f)


class BitwiseNotCommand(SetRangeCommand):
    short_name = "bitwise_not"
    pretty_name = "Bitwise NOT"

    def get_data(self, orig):
        return np.invert(orig)


class OrWithCommand(SetRangeValueCommand):
    short_name = "or_value"
    pretty_name = "OR With"

    def get_data(self, orig):
        return np.bitwise_or(orig, self.data)


class AndWithCommand(SetRangeValueCommand):
    short_name = "and_value"
    pretty_name = "AND With"

    def get_data(self, orig):
        return np.bitwise_and(orig, self.data)


class XorWithCommand(SetRangeValueCommand):
    short_name = "xor_value"
    pretty_name = "XOR With"

    def get_data(self, orig):
        return np.bitwise_xor(orig, self.data)


class LeftShiftCommand(SetRangeCommand):
    short_name = "left_shift"
    pretty_name = "Left Shift"

    def get_data(self, orig):
        return np.left_shift(orig, 1)


class RightShiftCommand(SetRangeCommand):
    short_name = "right_shift"
    pretty_name = "Right Shift"

    def get_data(self, orig):
        return np.right_shift(orig, 1)


class LeftRotateCommand(SetRangeCommand):
    short_name = "left_rotate"
    pretty_name = "Left Rotate"

    def get_data(self, orig):
        rotated = np.right_shift(np.bitwise_and(orig, 0x80), 7)
        return np.bitwise_or(np.left_shift(orig, 1), rotated)


class RightRotateCommand(SetRangeCommand):
    short_name = "right_rotate"
    pretty_name = "Right Rotate"

    def get_data(self, orig):
        rotated = np.left_shift(np.bitwise_and(orig, 0x01), 7)
        return np.bitwise_or(np.right_shift(orig, 1), rotated)


class ReverseBitsCommand(SetRangeCommand):
    short_name = "reverse_bits"
    pretty_name = "Reverse Bits"

    def get_data(self, orig):
        return bit_reverse_table[orig]


class RandomBytesCommand(SetRangeCommand):
    short_name = "random_bytes"
    pretty_name = "Random Bytes"

    def get_data(self, orig):
        return np.random.randint(0, 256, len(orig), dtype=np.uint8)


class RampUpCommand(SetRangeValueCommand):
    short_name = "ramp_up"
    pretty_name = "Ramp Up"

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


class RampDownCommand(SetRangeValueCommand):
    short_name = "ramp_down"
    pretty_name = "Ramp Down"

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


class AddValueCommand(SetRangeValueCommand):
    short_name = "add_value"
    pretty_name = "Add"

    def get_data(self, orig):
        return orig + self.data


class SubtractValueCommand(SetRangeValueCommand):
    short_name = "subtract_value"
    pretty_name = "Subtract"

    def get_data(self, orig):
        return orig - self.data


class SubtractFromCommand(SetRangeValueCommand):
    short_name = "subtract_from"
    pretty_name = "Subtract From"

    def get_data(self, orig):
        return self.data - orig


class MultiplyCommand(SetRangeValueCommand):
    short_name = "multiply"
    pretty_name = "Multiply"

    def get_data(self, orig):
        return orig * self.data


class DivideByCommand(SetRangeValueCommand):
    short_name = "divide"
    pretty_name = "Divide By"

    def get_data(self, orig):
        return orig // self.data


class DivideFromCommand(SetRangeValueCommand):
    short_name = "divide_from"
    pretty_name = "Divide From"

    def get_data(self, orig):
        return self.data // orig


class ReverseSelectionCommand(SetRangeCommand):
    short_name = "reverse_selection"
    pretty_name = "Reverse Selection"

    def get_data(self, orig):
        return orig[::-1,...]


class ReverseGroupCommand(SetRangeValueCommand):
    short_name = "reverse_group"
    pretty_name = "Reverse In Groups"

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
    pretty_name = "Apply Trace to Segment"

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
    pretty_name = "Clear Current Trace Results"

    def get_style(self, editor):
        mask = self.segment.get_style_mask(match=True)
        style_data = (self.segment.style[:].copy() & mask)
        return style_data

    def update_can_trace(self, editor):
        editor.can_trace = False
