import re
import bisect

import numpy as np

from omnivore.framework.errors import ProgressCancelError
from omnivore.utils.command import Command, UndoInfo

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
            ]
    
    def __init__(self, segment, start_index, end_index, bytes, cursor_at_end=False):
        SetDataCommand.__init__(self, segment, start_index, end_index)
        self.data = bytes
        self.cursor_at_end = cursor_at_end
    
    def get_data(self, orig):
        return self.data


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


class PasteCommand(ChangeByteCommand):
    short_name = "paste"
    pretty_name = "Paste"
    
    def get_data(self, orig):
        data_len = np.alen(self.data)
        orig_len = np.alen(orig)
        if data_len > orig_len > 1:
            data_len = orig_len
        return self.data[0:data_len]
    
    def perform(self, editor):
        i1 = self.start_index
        i2 = self.end_index
        data = self.get_data(self.segment.data[i1:i2])
        i2 = i1 + np.alen(data)  # Force end index to be length of pasted data
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_values_changed = True
        undo.flags.index_range = i1, i2
        undo.flags.select_range = True
        old_data = self.segment[i1:i2].copy()
        self.segment[i1:i2] = data
        undo.data = (old_data, )
        return undo

    def undo(self, editor):
        old_data, = self.undo_info.data
        i1 = self.start_index
        i2 = i1 + np.alen(old_data)
        self.segment[i1:i2] = old_data
        return self.undo_info


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


class ZeroCommand(ChangeByteCommand):
    short_name = "zero"
    pretty_name = "Zero Bytes"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        ChangeByteCommand.__init__(self, segment, start_index, end_index, 0)


class FFCommand(ChangeByteCommand):
    short_name = "ff"
    pretty_name = "FF Bytes"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        ChangeByteCommand.__init__(self, segment, start_index, end_index, 0xff)


class SetValueCommand(ChangeByteCommand):
    short_name = "set_value"
    pretty_name = "Set Value"


class SetHighBitCommand(SetDataCommand):
    short_name = "set_high_bit"
    pretty_name = "Set High Bit"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        SetDataCommand.__init__(self, segment, start_index, end_index)
    
    def get_data(self, orig):
        return np.bitwise_or(orig, 0x80)


class ClearHighBitCommand(SetDataCommand):
    short_name = "clear_high_bit"
    pretty_name = "Clear High Bit"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        SetDataCommand.__init__(self, segment, start_index, end_index)
    
    def get_data(self, orig):
        return np.bitwise_and(orig, 0x7f)


class BitwiseNotCommand(SetDataCommand):
    short_name = "bitwise_not"
    pretty_name = "Bitwise NOT"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        SetDataCommand.__init__(self, segment, start_index, end_index)
    
    def get_data(self, orig):
        return np.invert(orig)


class OrWithCommand(ChangeByteCommand):
    short_name = "or_value"
    pretty_name = "OR With"
    
    def get_data(self, orig):
        return np.bitwise_or(orig, self.data)


class AndWithCommand(ChangeByteCommand):
    short_name = "and_value"
    pretty_name = "AND With"
    
    def get_data(self, orig):
        return np.bitwise_and(orig, self.data)


class XorWithCommand(ChangeByteCommand):
    short_name = "xor_value"
    pretty_name = "XOR With"
    
    def get_data(self, orig):
        return np.bitwise_xor(orig, self.data)


class LeftShiftCommand(SetDataCommand):
    short_name = "left_shift"
    pretty_name = "Left Shift"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        SetDataCommand.__init__(self, segment, start_index, end_index)
    
    def get_data(self, orig):
        return np.left_shift(orig, 1)


class RightShiftCommand(SetDataCommand):
    short_name = "right_shift"
    pretty_name = "Right Shift"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        SetDataCommand.__init__(self, segment, start_index, end_index)
    
    def get_data(self, orig):
        return np.right_shift(orig, 1)


class LeftRotateCommand(SetDataCommand):
    short_name = "left_rotate"
    pretty_name = "Left Rotate"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        SetDataCommand.__init__(self, segment, start_index, end_index)
    
    def get_data(self, orig):
        rotated = np.right_shift(np.bitwise_and(orig, 0x80), 7)
        return np.bitwise_or(np.left_shift(orig, 1), rotated)


class RightRotateCommand(SetDataCommand):
    short_name = "right_rotate"
    pretty_name = "Right Rotate"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        SetDataCommand.__init__(self, segment, start_index, end_index)
    
    def get_data(self, orig):
        rotated = np.left_shift(np.bitwise_and(orig, 0x01), 7)
        return np.bitwise_or(np.right_shift(orig, 1), rotated)


class RampUpCommand(ChangeByteCommand):
    short_name = "ramp_up"
    pretty_name = "Ramp Up"
    
    def get_data(self, orig):
        num = np.alen(orig)
        return np.arange(self.data, self.data + num)


class RampDownCommand(ChangeByteCommand):
    short_name = "ramp_down"
    pretty_name = "Ramp Down"
    
    def get_data(self, orig):
        num = np.alen(orig)
        return np.arange(self.data, self.data - num, -1)


class AddValueCommand(ChangeByteCommand):
    short_name = "add_value"
    pretty_name = "Add"
    
    def get_data(self, orig):
        return orig + self.data


class SubtractValueCommand(ChangeByteCommand):
    short_name = "subtract_value"
    pretty_name = "Subtract"
    
    def get_data(self, orig):
        return orig - self.data


class SubtractFromCommand(ChangeByteCommand):
    short_name = "subtract_from"
    pretty_name = "Subtract From"
    
    def get_data(self, orig):
        return self.data - orig


class MultiplyCommand(ChangeByteCommand):
    short_name = "multiply"
    pretty_name = "Multiply"
    
    def get_data(self, orig):
        return orig * self.data


class DivideByCommand(ChangeByteCommand):
    short_name = "divide"
    pretty_name = "Divide By"
    
    def get_data(self, orig):
        return orig / self.data


class DivideFromCommand(ChangeByteCommand):
    short_name = "divide_from"
    pretty_name = "Divide From"
    
    def get_data(self, orig):
        return self.data / orig


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
    
    def __str__(self):
        return "%s %s" % (self.pretty_name, repr(self.search_text))
    
    def get_search_string(self):
        return bytearray.fromhex(self.search_text)
    
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
            for searcher_cls in editor.searchers:
                try:
                    searcher = searcher_cls(editor, self.search_text)
                    found.append(searcher)
                except ValueError, e:
                    errors.append(str(e))
            
            if found:
                for searcher in found:
                    self.all_matches.extend(searcher.matches)
                self.all_matches.sort()
                print "Find:", self.all_matches
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
            undo.flags.refresh_needed = True
        return undo

class FindNextCommand(Command):
    short_name = "findnext"
    pretty_name = "Find Next"
    
    def __init__(self, search_command):
        Command.__init__(self)
        self.search_command = search_command
    
    def get_index(self):
        cmd = self.search_command
        cmd.current_match_index += 1
        index = cmd.current_match_index
        if index >= len(cmd.all_matches):
            index = cmd.current_match_index = 0
        return index
    
    def perform(self, editor):
        self.undo_info = undo = UndoInfo()
        undo.flags.changed_document = False
        index = self.get_index()
        all_matches = self.search_command.all_matches
        print "FindNext:", all_matches
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
    
    def get_index(self):
        cmd = self.search_command
        cmd.current_match_index -= 1
        index = cmd.current_match_index
        if index < 0:
            index = cmd.current_match_index = len(cmd.all_matches) - 1
        return index
