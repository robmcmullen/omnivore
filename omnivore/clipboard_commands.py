import numpy as np

from sawx.utils.command import Command, UndoInfo
from .commands import SegmentCommand
from sawx.utils.sortutil import ranges_to_indexes, indexes_to_ranges, collapse_overlapping_ranges

import logging
log = logging.getLogger(__name__)


class ClipboardCommand(SegmentCommand):
    short_name = "clipboard_command"
    ui_name = "Clipboard Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('serializer', 'clipboard_serializer')
            ]

    def __init__(self, segment, serializer):
        SegmentCommand.__init__(self, segment)
        self.serializer = serializer
        s = serializer

    def prepare_data(self, editor):
        pass

    def get_clipped_indexes(self, editor):
        s = self.serializer
        if s.clipboard_indexes is not None:
            caret = s.dest_carets.current.index
            indexes = s.clipboard_indexes.copy() - s.clipboard_indexes[0] + caret
        elif s.dest_carets.has_selection:
            ranges = collapse_overlapping_ranges(s.dest_carets.selected_ranges_including_carets)
            log.debug("ranges:", ranges)
            indexes = ranges_to_indexes(ranges)
            log.debug("indexes:", indexes)
        else:
            count = len(s.clipboard_data)
            ranges = [(c.anchor_start_index, c.anchor_start_index + count) for c in s.dest_carets]
            ranges = collapse_overlapping_ranges(ranges)
            log.debug("ranges:", ranges)
            indexes = ranges_to_indexes(ranges)
            log.debug("indexes:", indexes)
        max_index = len(self.segment)
        indexes = indexes[indexes < max_index]
        log.debug("indexes after limits: %s" % str(indexes))
        return indexes

    def get_data(self, orig):
        data = self.serializer.clipboard_data
        data_len = np.alen(data)
        orig_len = np.alen(orig)
        if data_len > orig_len > 1:
            data_len = orig_len
        return data[0:data_len]

    def get_style(self, data):
        s = self.serializer
        style_data = s.clipboard_style
        if style_data is not None:
            style = s.clipboard_style[0:np.alen(data)]
        else:
            style = None
        return style

    def do_change(self, editor, undo):
        self.prepare_data(editor)
        indexes = self.get_clipped_indexes(editor)
        data = self.get_data(self.segment.data[indexes])
        log.debug("orig data: %s" % self.segment.data[indexes])
        log.debug("new data: %s" % data)
        indexes = indexes[0:np.alen(data)]
        log.debug("indexes truncated to data length: %s" % str(indexes))
        s = self.serializer
        if s.clipboard_relative_comment_indexes is not None:
            log.debug("relative comment indexes: %s" % (str(s.clipboard_relative_comment_indexes)))
            subset = s.clipboard_relative_comment_indexes[s.clipboard_relative_comment_indexes < np.alen(indexes)]
            log.debug("comment index subset: %s" % str(subset))
            comment_indexes = indexes[subset]
            log.debug("new comment indexes: %s" % str(comment_indexes))
            clamped_ranges = indexes_to_ranges(indexes)
            log.debug("clamped ranges: %s" % str(clamped_ranges))
            old_comment_info = self.segment.get_comment_restore_data(clamped_ranges)
        else:
            old_comment_info = None
        undo.flags.index_range = indexes[0], indexes[-1]
        undo.flags.select_range = True
        undo.flags.byte_values_changed = True
        old_data = self.segment[indexes].copy()
        self.segment[indexes] = data
        style = self.get_style(data)
        if style is not None:
            old_style = self.segment.style[indexes].copy()
            self.segment.style[indexes] = style
        else:
            old_style = None
        if old_comment_info is not None:
            log.debug("setting comments: %s" % s.clipboard_comments)
            self.segment.set_comments_at_indexes(clamped_ranges, comment_indexes, s.clipboard_comments)
        return (old_data, indexes, old_style, old_comment_info)

    def undo_change(self, editor, old_data):
        old_data, old_indexes, old_style, old_comment_info = old_data
        self.segment[old_indexes] = old_data
        if old_style is not None:
            self.segment.style[old_indexes] = old_style
        if old_comment_info is not None:
            self.segment.restore_comments(old_comment_info)


class PasteCommand(ClipboardCommand):
    """Paste clipboard data at each caret or selection.

    If pasting over multiple selections will overlap, later selections will
    overwrite earlier selections.
    """
    short_name = "paste"
    ui_name = "Paste"


class PasteCommentsCommand(PasteCommand):
    """Paste comments only

    This paste command places the comments at the byte offsets of the originial
    selection. For a command that will paste comments to match the lines of a
    disassembly, see :meth:`PasteDisassemblyComments`.
    """
    short_name = "paste_comments"
    ui_name = "Paste Comments"

    def get_data(self, orig):
        return orig

    def get_style(self, data):
        None


class PasteAndRepeatCommand(PasteCommand):
    short_name = "paste_rep"
    ui_name = "Paste And Repeat"

    def get_data(self, orig):
        data = self.data
        data_len = np.alen(data)
        orig_len = np.alen(orig)
        if orig_len > data_len:
            reps = (orig_len // data_len) + 1
            data = np.tile(data, reps)
        return data[0:orig_len]


class PasteRectCommand(SegmentCommand):
    short_name = "paste_rect"
    ui_name = "Paste Rectangular"
    serialize_order =  [
            ('segment', 'int'),
            ('serializer', 'clipboard_serializer'),
            ]

    def __init__(self, segment, serializer):
        #start_index, rows, cols, bytes_per_row, bytes):
        SegmentCommand.__init__(self, segment)
        self.serializer = serializer

    def __str__(self):
        s = self.serializer
        return "%s @ %04x (%dx%d)" % (self.ui_name, s.dest_carets.current.index + self.segment.origin, s.clipboard_num_cols, s.clipboard_num_rows)

    def single_source_single_dest(self, editor, undo):
        s = self.serializer
        caret = s.dest_carets.current
        i1 = caret.index
        bpr = s.dest_items_per_row
        r1, c1 = divmod(i1, bpr)
        r2 = r1 + s.clipboard_num_rows
        c2 = c1 + s.clipboard_num_cols
        last = r2 * bpr
        d = self.segment[:last].reshape(-1, bpr)
        r2 = min(r2, d.shape[0])
        c2 = min(c2, d.shape[1])
        undo.flags.byte_values_changed = True
        #undo.flags.index_range = i1, i2
        old_data = d[r1:r2,c1:c2].copy()
        new_data = np.fromstring(s.clipboard_data, dtype=np.uint8).reshape(s.clipboard_num_rows, s.clipboard_num_cols)
        d[r1:r2, c1:c2] = new_data[0:r2 - r1, 0:c2 - c1]
        undo.data = (r1, c1, r2, c2, last, old_data, )
        self.undo_info = undo

    def perform(self, editor, undo):
        self.single_source_single_dest(editor, undo)

    def undo(self, editor):
        s = self.serializer
        r1, c1, r2, c2, last, old_data, = self.undo_info.data
        d = self.segment[:last].reshape(-1, s.dest_items_per_row)
        d[r1:r2, c1:c2] = old_data
        return self.undo_info
