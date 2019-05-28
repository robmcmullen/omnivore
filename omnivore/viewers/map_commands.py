import numpy as np

from sawx.errors import ProgressCancelError
from sawx.utils.command import Batch, Command, UndoInfo
from ..commands import SegmentCommand
from ..utils import drawutil

import logging
progress_log = logging.getLogger("progress")


class DrawBatchCommand(Batch):
    short_name = "draw"
    ui_name = "Draw"

    def __str__(self):
        if self.commands:
            return "%s %dx%s" % (self.ui_name, len(self.commands), str(self.commands[0]))
        return self.ui_name

    def get_next_batch_command(self, segment, index, data):
        cmd = ChangeByteCommand(segment, index, index+len(data), data, False, True)
        return cmd


class LineCommand(SegmentCommand):
    short_name = "line"
    ui_name = "Line"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]

    def __init__(self, segment, start_index, end_index, data, bytes_per_row):
        SegmentCommand.__init__(self, segment)
        self.start_index = start_index
        self.end_index = end_index
        self.data = data
        self.bytes_per_row = bytes_per_row

    def __str__(self):
        return "%s @ %04x-%04x" % (self.ui_name, self.start_index + self.segment.origin, self.end_index + self.segment.origin)

    def get_data(self, orig):
        return self.data

    def get_points(self, i1, i2):
        return drawutil.get_line(i1, i2, self.bytes_per_row)

    def perform(self, editor, undo):
        i1 = self.start_index
        i2 = self.end_index
        if i2 < i1:
            i1, i2 = i2, i1
        undo.flags.byte_values_changed = True
        undo.flags.index_range = i1, i2
        undo.flags.force_single_caret = True
        undo.flags.caret_index = self.end_index
        line = np.asarray(self.get_points(i1, i2), dtype=np.uint32)
        old_data = self.segment[line].copy()
        self.segment[line] = self.get_data(old_data)
        if (self.segment[line] == old_data).all():
            undo.flags.success = False
        undo.data = (line, old_data)
        self.undo_info = undo

    def undo(self, editor):
        line, old_data = self.undo_info.data
        self.segment[line] = old_data
        return self.undo_info


class SquareCommand(LineCommand):
    short_name = "square"
    ui_name = "Square"

    def get_points(self, i1, i2):
        return drawutil.get_rectangle(i1, i2, self.bytes_per_row)


class FilledSquareCommand(LineCommand):
    short_name = "filled_square"
    ui_name = "Filled Square"

    def get_points(self, i1, i2):
        return drawutil.get_filled_rectangle(i1, i2, self.bytes_per_row)


class PasteRectangularCommand(SegmentCommand):
    short_name = "paste_rect"
    ui_name = "Paste Rectangular"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('rows', 'int'),
            ('cols', 'int'),
            ('bytes_per_row', 'int'),
            ('data', 'string'),
            ]

    def __init__(self, segment, start_index, rows, cols, bytes_per_row, data):
        SegmentCommand.__init__(self, segment)
        self.start_index = start_index
        self.rows = rows
        self.cols = cols
        self.bytes_per_row = bytes_per_row
        self.data = data

    def __str__(self):
        return "%s @ %04x (%dx%d)" % (self.ui_name, self.start_index + self.segment.origin, self.cols, self.rows)

    def perform(self, editor, undo):
        i1 = self.start_index
        bpr = self.bytes_per_row
        r1, c1 = divmod(i1, bpr)
        r2 = r1 + self.rows
        c2 = c1 + self.cols
        last = r2 * bpr
        d = self.segment[:last].reshape(-1, bpr)
        r2 = min(r2, d.shape[0])
        c2 = min(c2, d.shape[1])
        undo.flags.byte_values_changed = True
        #undo.flags.index_range = i1, i2
        old_data = d[r1:r2,c1:c2].copy()
        new_data = np.fromstring(self.data, dtype=np.uint8).reshape(self.rows, self.cols)
        d[r1:r2, c1:c2] = new_data[0:r2 - r1, 0:c2 - c1]
        undo.data = (r1, c1, r2, c2, last, old_data, )
        self.undo_info = undo

    def undo(self, editor):
        r1, c1, r2, c2, last, old_data, = self.undo_info.data
        d = self.segment[:last].reshape(-1, self.bytes_per_row)
        d[r1:r2, c1:c2] = old_data
        return self.undo_info
