import numpy as np

from omnivore.utils.command import Command, UndoInfo
from omnivore8bit.commands import SetValuesAtIndexesCommand, SegmentCommand
from omnivore.utils.sortutil import ranges_to_indexes, collapse_overlapping_ranges


class ClipboardCommand(SegmentCommand):
    pass


class PasteCommand(ClipboardCommand):
    """Paste clipboard data at each caret or selection.

    If pasting over multiple selections will overlap, later selections will
    overwrite earlier selections.
    """
    short_name = "paste"
    pretty_name = "Paste"

    def __init__(self, segment, serializer):
        self.serializer = serializer
        SegmentCommand.__init__(self, segment)


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


class PasteRectCommand(SegmentCommand):
    short_name = "paste_rect"
    pretty_name = "Paste Rectangular"
    serialize_order =  [
            ('segment', 'int'),
            ('serializer', 'clipboard_serializer'),
            ]

    def __init__(self, segment, serializer):
        #start_index, rows, cols, bytes_per_row, bytes):
        SegmentCommand.__init__(self, segment)
        s = serializer
        self.start_index = s.caret_index
        self.rows = s.num_rows
        self.cols = s.num_columns
        self.bytes_per_row = s.bytes_per_row
        self.bytes = s.data

    def __str__(self):
        return "%s @ %04x (%dx%d)" % (self.pretty_name, self.start_index + self.segment.start_addr, self.cols, self.rows)

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
        new_data = np.fromstring(self.bytes, dtype=np.uint8).reshape(self.rows, self.cols)
        d[r1:r2, c1:c2] = new_data[0:r2 - r1, 0:c2 - c1]
        undo.data = (r1, c1, r2, c2, last, old_data, )
        self.undo_info = undo

    def undo(self, editor):
        r1, c1, r2, c2, last, old_data, = self.undo_info.data
        d = self.segment[:last].reshape(-1, self.bytes_per_row)
        d[r1:r2, c1:c2] = old_data
        return self.undo_info
