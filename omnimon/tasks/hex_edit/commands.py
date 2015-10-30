import numpy as np

from omnimon.framework.errors import ProgressCancelError
from omnimon.utils.command import Command, UndoInfo

import logging
progress_log = logging.getLogger("progress")


class ChangeByteCommand(Command):
    short_name = "cb"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ('bytes', 'string'),
            ]
    
    def __init__(self, segment, start_index, end_index, bytes):
        Command.__init__(self)
        self.segment = segment
        self.start_index = start_index
        self.end_index = end_index
        self.data = bytes
    
    def __str__(self):
        return "Change Bytes"
    
    def perform(self, editor):
        i1 = self.start_index
        i2 = self.end_index
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_values_changed = True
        undo.flags.index_range = i1, i2
        old_data = self.segment.data[i1:i2].copy()
        self.segment.data[i1:i2] = self.data
        undo.data = (old_data, )
        return undo

    def undo(self, editor):
        old_data, = self.undo_info.data
        print "undo: old_data =", old_data
        self.segment.data[self.start_index:self.end_index] = old_data
        return self.undo_info


class ZeroCommand(ChangeByteCommand):
    short_name = "zero"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index):
        ChangeByteCommand.__init__(self, segment, start_index, end_index, 0)
    
    def __str__(self):
        return "Zero Bytes"
