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


class PasteRectangularCommand(Command):
    short_name = "paste_rect"
    pretty_name = "Paste Rectangular"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('rows', 'int'),
            ('cols', 'int'),
            ('bytes_per_row', 'int'),
            ('bytes', 'string'),
            ]
    
    def __init__(self, segment, start_index, rows, cols, bytes_per_row, bytes):
        Command.__init__(self)
        self.segment = segment
        self.start_index = start_index
        self.rows = rows
        self.cols = cols
        self.bytes_per_row = bytes_per_row
        self.bytes = bytes
    
    def __str__(self):
        return "%s @ %04x (%dx%d)" % (self.pretty_name, self.start_index + self.segment.start_addr, self.cols, self.rows)
    
    def perform(self, editor):
        i1 = self.start_index
        bpr = self.bytes_per_row
        r1, c1 = divmod(i1, bpr)
        r2 = r1 + self.rows
        c2 = c1 + self.cols
        last = r2 * bpr
        d = self.segment[:last].reshape(-1, bpr)
        r2 = min(r2, d.shape[0])
        c2 = min(c2, d.shape[1])
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_values_changed = True
        #undo.flags.index_range = i1, i2
        old_data = d[r1:r2,c1:c2].copy()
        new_data = np.fromstring(self.bytes, dtype=np.uint8).reshape(self.rows, self.cols)
        d[r1:r2, c1:c2] = new_data[0:r2 - r1, 0:c2 - c1]
        undo.data = (r1, c1, r2, c2, last, old_data, )
        return undo

    def undo(self, editor):
        r1, c1, r2, c2, last, old_data, = self.undo_info.data
        d = self.segment[:last].reshape(-1, self.bytes_per_row)
        d[r1:r2, c1:c2] = old_data
        return self.undo_info
