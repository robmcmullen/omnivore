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
        self.bytes = bytes
    
    def __str__(self):
        return "Change Bytes"
    
    def perform(self, editor):
        self.undo_info = undo = UndoInfo()
        undo.flags.refresh_needed = True
        old_bytes = self.segment.data[self.start_index:self.end_index]
        self.segment.data[self.start_index:self.end_index] = self.bytes
        undo.data = (old_bytes, )
        return undo

    def undo(self, editor):
        old_bytes, = self.undo_info.data
        self.segment.data[self.start_index:self.end_index] = old_bytes
        undo = UndoInfo()
        undo.flags.refresh_needed = True
        return undo
