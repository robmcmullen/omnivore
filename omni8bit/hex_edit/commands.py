import re
import bisect

import fs
import numpy as np

from omnivore.framework.errors import ProgressCancelError
from omnivore.utils.command import Command, UndoInfo
from omnivore.utils.sortutil import ranges_to_indexes
from omni8bit.utils.searchalgorithm import AlgorithmSearcher
from omnivore.utils.file_guess import FileGuess
from omnivore.utils.permute import bit_reverse_table

import logging
progress_log = logging.getLogger("progress")


class SetDataCommand(Command):
    short_name = "get_data_base"
    pretty_name = "Set Data Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        Command.__init__(self)
        self.segment = segment
        self.start_index = start_index
        if start_index == end_index:
            end_index += 1
        self.end_index = end_index
        self.cursor_at_end = False
        self.ignore_if_same_bytes = False
    
    def __str__(self):
        if self.end_index - self.start_index > 1:
            return "%s @ %04x-%04x" % (self.pretty_name, self.start_index + self.segment.start_addr, self.end_index + self.segment.start_addr)
        else:
            return "%s @ %04x" % (self.pretty_name, self.start_index)
    
    def get_data(self, orig):
        raise NotImplementedError
    
    def perform(self, editor):
        i1 = self.start_index
        i2 = self.end_index
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_values_changed = True
        undo.flags.index_range = i1, i2
        if self.cursor_at_end:
            undo.flags.cursor_index = i2
        old_data = self.segment[i1:i2].copy()
        self.segment[i1:i2] = self.get_data(old_data)
        if self.ignore_if_same_bytes and self.segment[i1:i2] == old_data:
            undo.flags.success = False
        undo.data = (old_data, )
        return undo

    def undo(self, editor):
        old_data, = self.undo_info.data
        self.segment[self.start_index:self.end_index] = old_data
        return self.undo_info


class ChangeByteCommand(SetDataCommand):
    short_name = "cb"
    pretty_name = "Change Bytes"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ('bytes', 'string'),
            ('cursor_at_end', 'bool'),
            ('ignore_if_same_bytes', 'bool'),
            ]
    
    def __init__(self, segment, start_index, end_index, bytes, cursor_at_end=False, ignore_if_same_bytes=False):
        SetDataCommand.__init__(self, segment, start_index, end_index)
        self.data = bytes
        self.cursor_at_end = cursor_at_end
        self.ignore_if_same_bytes = ignore_if_same_bytes
    
    def get_data(self, orig):
        return self.data


class CoalescingChangeByteCommand(ChangeByteCommand):
    short_name = "ccb"
    
    def coalesce(self, next_command):
        n = next_command
        if n.__class__ == self.__class__ and n.segment == self.segment and n.start_index == self.start_index and n.end_index == self.end_index:
            self.data = n.data
            return True


class InsertFileCommand(SetDataCommand):
    short_name = "in"
    pretty_name = "Insert File"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('uri', 'string'),
            ]
    
    def __init__(self, segment, start_index, uri):
        SetDataCommand.__init__(self, segment, start_index, -1)
        self.uri = uri
        self.error = None
    
    def get_data(self, orig):
        try:
            guess = FileGuess(self.uri)
        except fs.errors.FSError, e:
            self.error = "File load error: %s" % str(e)
            return
        data = guess.numpy
        if len(orig) < len(data):
            data = data[0:len(orig)]
        return data
    
    def perform(self, editor):
        i1 = self.start_index
        orig = self.segment.data[self.start_index:]
        data = self.get_data(orig)
        if self.error:
            undo.flags.message = self.error
        else:
            i2 = i1 + len(data)
            self.end_index = i2
            self.undo_info = undo = UndoInfo()
            undo.flags.byte_values_changed = True
            undo.flags.index_range = i1, i2
            undo.flags.select_range = True
            old_data = self.segment[i1:i2].copy()
            self.segment[i1:i2] = data
            undo.data = (old_data,)
        return undo


class MiniAssemblerCommand(ChangeByteCommand):
    short_name = "asm"
    pretty_name = "Asm"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ('bytes', 'string'),
            ('asm', 'string'),
            ]
    
    def __init__(self, segment, start_index, end_index, bytes, asm):
        ChangeByteCommand.__init__(self, segment, start_index, end_index, bytes)
        self.asm = asm
    
    def __str__(self):
        return "%s @ %04x" % (self.asm, self.start_index)


class SetCommentCommand(Command):
    short_name = "set_comment"
    pretty_name = "Comment"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('comment', 'string'),
            ]
    
    def __init__(self, segment, ranges, comment):
        Command.__init__(self)
        self.segment = segment
        self.ranges = tuple(ranges)
        self.comment = comment
        indexes = ranges_to_indexes(self.ranges)
        self.index_range = indexes[0], indexes[-1]
        if len(ranges) == 1:
            self.pretty_name = "%s @ %04x" % (self.pretty_name, self.segment.start_addr + indexes[0])
    
    def __str__(self):
        if len(self.comment) > 20:
            text = self.comment[:20] + "..."
        else:
            text = self.comment
        return "%s: %s" % (self.pretty_name, text)
    
    def change_comments(self):
        self.segment.set_comment(self.ranges, self.comment)

    def perform(self, editor):
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_style_changed = True
        undo.flags.index_range = self.index_range
        old_data = self.segment.get_comment_restore_data(self.ranges)
        self.change_comments()
        undo.data = (old_data, )
        return undo

    def undo(self, editor):
        old_data, = self.undo_info.data
        self.segment.restore_comments(old_data)
        return self.undo_info


class ClearCommentCommand(SetCommentCommand):
    short_name = "clear_comment"
    pretty_name = "Remove Comment"
    
    def __init__(self, segment, ranges):
        SetCommentCommand.__init__(self, segment, ranges, "")
    
    def __str__(self):
        return self.pretty_name

    def change_comments(self):
        self.segment.clear_comment(self.ranges)


class SetValuesAtIndexesCommand(Command):
    short_name = "set_values_at_indexes"
    pretty_name = "Set Indexes Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('cursor', 'int'),
            ('bytes', 'string'),
            ('indexes', 'nparray'),
            ]
    
    def __init__(self, segment, ranges, cursor, bytes, indexes, style=None, comment_indexes=None, comments=None):
        Command.__init__(self)
        self.segment = segment
        self.ranges = tuple(ranges)
        self.cursor = cursor
        self.data = bytes
        self.indexes = indexes
        self.style = style
        self.relative_comment_indexes = comment_indexes
        self.comments = comments
    
    def __str__(self):
        return "%s" % self.pretty_name
    
    def get_data(self, orig):
        raise NotImplementedError
    
    def perform(self, editor):
        raise NotImplementedError

    def undo(self, editor):
        old_data, old_indexes, old_style, old_comment_info = self.undo_info.data
        self.segment[old_indexes] = old_data
        self.segment.style[old_indexes] = old_style
        old_comment_indexes, old_comments = old_comment_info
        self.segment.remove_comments_at_indexes(old_indexes)
        self.segment.set_comments_at_indexes(old_comment_indexes, old_comments)
        return self.undo_info


class PasteCommand(SetValuesAtIndexesCommand):
    short_name = "paste"
    pretty_name = "Paste"
    
    def get_data(self, orig):
        data_len = np.alen(self.data)
        orig_len = np.alen(orig)
        if data_len > orig_len > 1:
            data_len = orig_len
        return self.data[0:data_len]

    def perform(self, editor):
        indexes = ranges_to_indexes(self.ranges)
        if np.alen(indexes) == 0:
            if self.indexes is not None:
                indexes = self.indexes.copy() - self.indexes[0] + self.cursor
            else:
                indexes = np.arange(self.cursor, self.cursor + np.alen(self.data))
        max_index = len(self.segment)
        indexes = indexes[indexes < max_index]
        data = self.get_data(self.segment.data[indexes])
        style = self.style[0:np.alen(data)]
        indexes = indexes[0:np.alen(data)]
        comment_indexes = indexes[self.relative_comment_indexes[self.relative_comment_indexes < np.alen(indexes)]]
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_values_changed = True
        undo.flags.index_range = indexes[0], indexes[-1]
        undo.flags.select_range = True
        old_data = self.segment[indexes].copy()
        old_style = self.segment.style[indexes].copy()
        old_comment_info = self.segment.get_comments_at_indexes(indexes)
        self.segment[indexes] = data
        self.segment.style[indexes] = style
        self.segment.set_comments_at_indexes(comment_indexes, self.comments)
        undo.data = (old_data, indexes, old_style, old_comment_info)
        return undo


class PasteAndRepeatCommand(PasteCommand):
    short_name = "paste_rep"
    pretty_name = "Paste And Repeat"
    
    def get_data(self, orig):
        bytes = self.data
        data_len = np.alen(bytes)
        orig_len = np.alen(orig)
        if orig_len > data_len:
            reps = (orig_len / data_len) + 1
            bytes = np.tile(bytes, reps)
        return bytes[0:orig_len]


class SetRangeCommand(Command):
    short_name = "set_range_base"
    pretty_name = "Set Ranges Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ]
    
    def __init__(self, segment, ranges):
        Command.__init__(self)
        self.segment = segment
        self.ranges = tuple(ranges)
    
    def __str__(self):
        return "%s" % self.pretty_name
    
    def get_data(self, orig):
        raise NotImplementedError
    
    def perform(self, editor):
        indexes = ranges_to_indexes(self.ranges)
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_values_changed = True
        undo.flags.index_range = indexes[0], indexes[-1]
        old_data = self.segment[indexes].copy()
        self.segment[indexes] = self.get_data(old_data)
        undo.data = (old_data, )
        return undo

    def undo(self, editor):
        old_data, = self.undo_info.data
        indexes = ranges_to_indexes(self.ranges)
        self.segment[indexes] = old_data
        return self.undo_info


class SetRangeValueCommand(SetRangeCommand):
    short_name = "set_range_base"
    pretty_name = "Set Ranges Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('bytes', 'string'),
            ]
    
    def __init__(self, segment, ranges, bytes):
        SetRangeCommand.__init__(self, segment, ranges)
        self.data = bytes
    
    def get_data(self, orig):
        return self.data


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


class RampUpCommand(SetRangeValueCommand):
    short_name = "ramp_up"
    pretty_name = "Ramp Up"
    
    def get_data(self, orig):
        num = np.alen(orig)
        return np.arange(self.data, self.data + num)


class RampDownCommand(SetRangeValueCommand):
    short_name = "ramp_down"
    pretty_name = "Ramp Down"
    
    def get_data(self, orig):
        num = np.alen(orig)
        return np.arange(self.data, self.data - num, -1)


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
        return orig / self.data


class DivideFromCommand(SetRangeValueCommand):
    short_name = "divide_from"
    pretty_name = "Divide From"
    
    def get_data(self, orig):
        return self.data / orig


class RevertToBaselineCommand(SetRangeCommand):
    short_name = "revert_baseline"
    pretty_name = "Revert to Baseline Data"
    
    def get_baseline_data(self, orig, editor, indexes):
        r = editor.document.baseline_document.global_segment.get_parallel_raw_data(self.segment)
        return r[indexes].data
    
    def perform(self, editor):
        indexes = ranges_to_indexes(self.ranges)
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_values_changed = True
        undo.flags.index_range = indexes[0], indexes[-1]
        old_data = self.segment[indexes].copy()
        self.segment[indexes] = self.get_baseline_data(old_data, editor, indexes)
        undo.data = (old_data, )
        return undo


class FindAllCommand(Command):
    short_name = "find"
    pretty_name = "Find"
    
    def __init__(self, start_cursor_index, search_text, error, repeat=False, reverse=False):
        Command.__init__(self)
        self.start_cursor_index = start_cursor_index
        self.search_text = search_text
        self.error = error
        self.repeat = repeat
        self.reverse = reverse
        self.current_match_index = -1
    
    def __str__(self):
        return "%s %s" % (self.pretty_name, repr(self.search_text))
    
    def get_search_string(self):
        return bytearray.fromhex(self.search_text)
    
    def get_searchers(self, editor):
        return editor.searchers
    
    def perform(self, editor):
        self.all_matches = []
        self.undo_info = undo = UndoInfo()
        undo.flags.changed_document = False
        if self.error:
            undo.flags.message = self.error
        else:
            errors = []
            found = []
            editor.segment.clear_style_bits(match=True)
            for searcher_cls in self.get_searchers(editor):
                try:
                    searcher = searcher_cls(editor, self.search_text)
                    found.append(searcher)
                except ValueError, e:
                    errors.append(str(e))
            
            if found:
                for searcher in found:
                    self.all_matches.extend(searcher.matches)
                self.all_matches.sort()

                # remove entries that duplicate the start point, finding the
                # match of largest size if two are coincident
                dups = {}
                dups_removed = []
                for match in self.all_matches:
                    start = match[0]
                    if start not in dups:
                        dups_removed.append(match)
                        dups[start] = match[1]
                    elif dups[start] < match[1]:
                        dups[start] = match[1]
                self.all_matches = [m if m[0] in dups and dups[m[0]] < m[1] else (m[0], dups[m[0]]) for m in dups_removed]

                #print "Find:", self.all_matches
                if len(self.all_matches) == 0:
                    undo.flags.message = "Not found"
                else:
                # Need to use a tuple in order for bisect to search the list
                # of tuples
                    cursor_tuple = (editor.cursor_index, 0)
                    self.current_match_index = bisect.bisect_left(self.all_matches, cursor_tuple)
                    if self.current_match_index >= len(self.all_matches):
                        self.current_match_index = 0
                    match = self.all_matches[self.current_match_index]
                    print self.current_match_index, match, cursor_tuple
                    undo.flags.index_range = match
                    undo.flags.cursor_index = match[0]
                    undo.flags.select_range = True
                    undo.flags.message = ("Match %d of %d, found at $%04x" % (self.current_match_index + 1, len(self.all_matches), match[0]))
            elif errors:
                undo.flags.message = " ".join(errors)
            undo.flags.refresh_needed = True
        return undo

class FindNextCommand(Command):
    short_name = "findnext"
    pretty_name = "Find Next"
    
    def __init__(self, search_command):
        Command.__init__(self)
        self.search_command = search_command
    
    def get_index(self, editor):
        cmd = self.search_command
        cursor_tuple = (editor.cursor_index, 0)
        match_index = bisect.bisect_right(cmd.all_matches, cursor_tuple)
        if match_index == cmd.current_match_index:
            match_index += 1
        if match_index >= len(cmd.all_matches):
            match_index = 0
        cmd.current_match_index = match_index
        return match_index
    
    def perform(self, editor):
        self.undo_info = undo = UndoInfo()
        undo.flags.changed_document = False
        index = self.get_index(editor)
        all_matches = self.search_command.all_matches
        #print "FindNext:", all_matches
        try:
            match = all_matches[index]
            undo.flags.index_range = match
            undo.flags.cursor_index = match[0]
            undo.flags.select_range = True
            undo.flags.message = ("Match %d of %d, found at $%04x" % (index + 1, len(all_matches), match[0]))
        except IndexError:
            pass
        undo.flags.refresh_needed = True
        return undo

class FindPrevCommand(FindNextCommand):
    short_name = "findprev"
    pretty_name = "Find Previous"
    
    def get_index(self, editor):
        cmd = self.search_command
        cursor_tuple = (editor.cursor_index, 0)
        match_index = bisect.bisect_left(cmd.all_matches, cursor_tuple)
        match_index -= 1
        if match_index < 0:
            match_index = len(cmd.all_matches) - 1
        cmd.current_match_index = match_index
        return match_index

class FindAlgorithmCommand(FindAllCommand):
    short_name = "findalgorithm"
    pretty_name = "Find using expression"
    
    def get_searchers(self, editor):
        return [AlgorithmSearcher]


class ChangeStyleCommand(SetDataCommand):
    short_name = "cs"
    pretty_name = "Change Style"
    serialize_order =  [
            ('segment', 'int'),
            ]
    
    def __init__(self, segment):
        start_index = 0
        end_index = len(segment)
        SetDataCommand.__init__(self, segment, start_index, end_index)

    def get_style(self, editor):
        style = self.segment.style[self.start_index:self.end_index].copy()
        return style

    def clip(self, style):
        if len(style) < self.end_index - self.start_index:
            self.end_index = self.start_index + len(style)

    def update_can_trace(self, editor):
        pass

    def set_undo_flags(self):
        self.undo_info.flags.byte_style_changed = True

    def perform(self, editor):
        self.undo_info = undo = UndoInfo()
        self.set_undo_flags()
        old_can_trace = editor.can_trace
        new_style = self.get_style(editor)
        self.clip(new_style)
        old_style = self.segment.style[self.start_index:self.end_index].copy()
        self.segment.style[self.start_index:self.end_index] = new_style
        self.update_can_trace(editor)
        editor.document.change_count += 1
        undo.data = (old_style, old_can_trace)
        return undo

    def undo(self, editor):
        old_style, old_can_trace = self.undo_info.data
        self.segment.style[self.start_index:self.end_index] = old_style
        editor.can_trace = old_can_trace
        return self.undo_info


class ApplyTraceSegmentCommand(ChangeStyleCommand):
    short_name = "applytrace"
    pretty_name = "Apply Trace to Segment"
    
    def get_style(self, editor):
        trace, mask = editor.disassembly.get_trace(save=True)
        self.clip(trace)
        style_data = (self.segment.style[self.start_index:self.end_index].copy() & mask) | trace
        return style_data

    def set_undo_flags(self):
        self.undo_info.flags.byte_values_changed = True
        self.undo_info.flags.index_range = self.start_index, self.end_index


class ClearTraceCommand(ChangeStyleCommand):
    short_name = "cleartrace"
    pretty_name = "Clear Current Trace Results"
    
    def get_style(self, editor):
        mask = self.segment.get_style_mask(match=True)
        style_data = (self.segment.style[:].copy() & mask)
        return style_data

    def update_can_trace(self, editor):
        editor.can_trace = False
