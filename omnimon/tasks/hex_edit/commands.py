import numpy as np

from omnimon.framework.errors import ProgressCancelError
from omnimon.utils.command import Command, UndoInfo

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
        self.end_index = end_index
    
    def __str__(self):
        return self.pretty_name
    
    def get_data(self, source):
        raise NotImplementedError
    
    def perform(self, editor):
        i1 = self.start_index
        i2 = self.end_index
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_values_changed = True
        undo.flags.index_range = i1, i2
        old_data = self.segment.data[i1:i2].copy()
        self.segment.data[i1:i2] = self.get_data(self.segment.data[i1:i2])
        undo.data = (old_data, )
        return undo

    def undo(self, editor):
        old_data, = self.undo_info.data
        print "undo: old_data =", old_data
        self.segment.data[self.start_index:self.end_index] = old_data
        return self.undo_info


class ChangeByteCommand(SetDataCommand):
    short_name = "cb"
    pretty_name = "Change Bytes"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ('bytes', 'string'),
            ]
    
    def __init__(self, segment, start_index, end_index, bytes):
        SetDataCommand.__init__(self, segment, start_index, end_index)
        self.data = bytes
    
    def get_data(self, source):
        return self.data


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
    
    def get_data(self, source):
        return np.bitwise_or(source, 0x80)


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
    
    def get_data(self, source):
        return np.bitwise_and(source, 0x7f)


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
    
    def get_data(self, source):
        return np.invert(source)


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
    
    def get_data(self, source):
        return np.left_shift(source, 1)


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
    
    def get_data(self, source):
        return np.right_shift(source, 1)


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
    
    def get_data(self, source):
        rotated = np.right_shift(np.bitwise_and(source, 0x80), 7)
        return np.bitwise_or(np.left_shift(source, 1), rotated)


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
    
    def get_data(self, source):
        rotated = np.left_shift(np.bitwise_and(source, 0x01), 7)
        return np.bitwise_or(np.right_shift(source, 1), rotated)

