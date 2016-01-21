import numpy as np

from omnivore.framework.errors import ProgressCancelError
from omnivore.utils.command import Batch, Command, UndoInfo
from omnivore.tasks.hex_edit.commands import ChangeByteCommand
from omnivore.utils.drawutil import *

import logging
progress_log = logging.getLogger("progress")


class DrawBatchCommand(Batch):
    short_name = "draw"
    pretty_name = "Draw"
    
    def __str__(self):
        if self.commands:
            return "%s %dx%s" % (self.pretty_name, len(self.commands), str(self.commands[0]))
        return self.pretty_name

    def get_next_batch_command(self, segment, index, bytes):
        cmd = ChangeByteCommand(segment, index, index+len(bytes), bytes, False, True)
        return cmd


class LineCommand(Command):
    short_name = "line"
    pretty_name = "Line"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]
    
    def __init__(self, segment, start_index, end_index, bytes):
        Command.__init__(self)
        self.segment = segment
        self.start_index = start_index
        self.end_index = end_index
        self.data = bytes
    
    def __str__(self):
        return "%s @ %04x-%04x" % (self.pretty_name, self.start_index + self.segment.start_addr, self.end_index + self.segment.start_addr)
    
    def get_data(self, orig):
        return self.data
    
    def get_points(self, i1, i2, map_width):
        return get_line(i1, i2, map_width)
    
    def perform(self, editor):
        i1 = self.start_index
        i2 = self.end_index
        if i2 < i1:
            i1, i2 = i2, i1
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_values_changed = True
        undo.flags.index_range = i1, i2
        undo.flags.cursor_index = self.end_index
        line = np.asarray(self.get_points(i1, i2, editor.map_width), dtype=np.uint32)
        old_data = self.segment[line].copy()
        self.segment[line] = self.get_data(old_data)
        if (self.segment[line] == old_data).all():
            undo.flags.success = False
        undo.data = (line, old_data)
        return undo

    def undo(self, editor):
        line, old_data = self.undo_info.data
        self.segment[line] = old_data
        return self.undo_info


class SquareCommand(LineCommand):
    short_name = "square"
    pretty_name = "Square"
    
    def get_points(self, i1, i2, map_width):
        return get_rectangle(i1, i2, map_width)


class FilledSquareCommand(LineCommand):
    short_name = "filled_square"
    pretty_name = "Filled Square"
    
    def get_points(self, i1, i2, map_width):
        return get_filled_rectangle(i1, i2, map_width)
