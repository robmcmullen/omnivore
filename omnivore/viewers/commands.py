import numpy as np

from ..commands import SetSelectionCommand, SetRangeCommand, ChangeStyleCommand, SetRangeValueModifyIndexesCommand
from sawx.utils.permute import bit_reverse_table

from ..disassembler import miniasm

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


class MiniAssemblerCommand(SetSelectionCommand):
    short_name = "miniasm"
    ui_name = "Assemble"

    def __init__(self, segment, cpu, selection, data, advance=False):
        SetSelectionCommand.__init__(self, segment, selection, data, advance)
        self.cpu = cpu

    def change_data_at_indexes(self, indexes):
        new_data = np.empty(len(indexes) + 100, dtype=np.uint8)
        new_indexes = np.empty(len(indexes) + 100, dtype=np.uint8)
        total = 0
        indexes.sort()  # carets may be out of order, so force increasing
        next_valid_start = 0
        for index in indexes:
            if index < next_valid_start:
                # don't overwrite an instruction in the middle
                continue
            pc = self.segment.origin + index
            d = miniasm.process(self.cpu, self.data, pc)
            count = len(d)
            new_data[total:total + count] = d
            next_valid_start = index + count
            new_indexes[total:total + count] = np.arange(index, next_valid_start)
            total += count
        indexes = new_indexes[0:total]
        old_data = self.segment[indexes]
        self.segment[indexes] = new_data[0:total]
        return old_data, indexes


class SetCommentCommand(ChangeStyleCommand):
    short_name = "set_comment"
    ui_name = "Comment"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('text', 'string'),
            ]

    def __init__(self, segment, ranges, text):
        ChangeStyleCommand.__init__(self, segment)
        # Only use the first byte of each range
        self.ranges = self.convert_ranges(ranges)
        log.debug("%s operating on ranges: %s" % (self.ui_name, str(ranges)))
        self.text = text
        # indexes = ranges_to_indexes(self.ranges)
        # self.index_range = indexes[0], indexes[-1]
        # if len(ranges) == 1:
        #     self.ui_name = "%s @ %04x" % (self.ui_name, self.segment.origin + indexes[0])

    def __str__(self):
        if len(self.text) > 20:
            text = self.text[:20] + "..."
        else:
            text = self.text
        return "%s: %s" % (self.ui_name, text)

    def convert_ranges(self, ranges):
        return tuple([(start, start + 1) for start, end in ranges])

    def set_undo_flags(self, flags):
        flags.byte_style_changed = True
        # flags.index_range = self.index_range

    def clamp_ranges_and_indexes(self, editor):
        return self.ranges, None

    def change_comments(self, ranges, indexes):
        self.segment.set_comment_ranges(ranges, self.text)

    def do_change(self, editor, undo):
        ranges, indexes = self.clamp_ranges_and_indexes(editor)
        old_data = self.segment.get_comment_restore_data(ranges)
        self.change_comments(ranges, indexes)
        return old_data

    def undo_change(self, editor, old_data):
        self.segment.restore_comments(old_data)


class ClearCommentCommand(SetCommentCommand):
    short_name = "clear_comment"
    ui_name = "Remove Comment"

    def __init__(self, segment, ranges):
        SetCommentCommand.__init__(self, segment, ranges, "")

    def convert_ranges(self, ranges):
        # When clearing comments, we want to look at every space, not just the
        # first byte of each range like setting comments
        return ranges

    def change_comments(self, ranges, indexes):
        self.segment.clear_comment_ranges(ranges)


class PasteCommentsCommand(ClearCommentCommand):
    short_name = "paste_comments"
    ui_name = "Paste Comments"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('cursor', 'int'),
            ('bytes', 'string'),
            ]

    def __init__(self, segment, ranges, cursor, bytes, *args, **kwargs):
        # remove zero-length ranges
        r = [(start, end) for start, end in ranges if start != end]
        ranges = r
        if not ranges:
            # use the range from cursor to end
            ranges = [(cursor, len(segment))]
        ClearCommentCommand.__init__(self, segment, ranges, bytes)
        self.cursor = cursor
        self.comments = bytes.tostring().splitlines()
        self.num_lines = len(self.comments)

    def __str__(self):
        return "%s: %d line%s" % (self.ui_name, self.num_lines, "" if self.num_lines == 1 else "s")

    def clamp_ranges_and_indexes(self, editor):
        disasm = editor.disassembly.table.disassembler
        count = self.num_lines
        comment_indexes = []
        clamped = []
        for start, end in self.ranges:
            index = start
            log.debug("starting range %d:%d" % (start, end))
            while index < end and count > 0:
                comment_indexes.append(index)
                pc = index + self.segment.origin
                log.debug("comment at %d, %04x" % (index, pc))
                try:
                    index = disasm.get_next_instruction_pc(pc)
                    count -= 1
                except IndexError:
                    count = 0
            clamped.append((start, index))
            if count <= 0:
                break
        return clamped, comment_indexes

    def change_comments(self, ranges, indexes):
        """Add comment lines as long as we don't go out of range (if specified)
        or until the end of the segment or the comment list is exhausted.

        Depends on a valid disassembly to find the lines; we are adding a
        comment for the first byte in each statement.
        """
        log.debug("ranges: %s" % str(ranges))
        log.debug("indexes: %s" % str(indexes))
        self.segment.set_comments_at_indexes(ranges, indexes, self.comments)
        self.segment.set_style_at_indexes(indexes, comment=True)


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
