import numpy as np

from omnivore.utils.command import Command, UndoInfo
from omnivore.utils.sortutil import ranges_to_indexes, indexes_to_ranges
from omnivore.utils.file_guess import FileGuess
from omnivore.utils.permute import bit_reverse_table

import logging
log = logging.getLogger(__name__)
progress_log = logging.getLogger("progress")


class SegmentCommand(Command):
    short_name = "segment_data_base"
    pretty_name = "Segment Modification Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ]

    def __init__(self, segment):
        Command.__init__(self)
        self.segment = segment

    def coalesce(self, next_command):
        if next_command.__class__ == self.__class__ and next_command.segment == self.segment:
            if self.can_coalesce(next_command):
                self.coalesce_merge(next_command)


class ChangeByteValuesCommand(SegmentCommand):
    short_name = "metadata_base"
    pretty_name = "Change Metadata Abstract Command"

    def set_undo_flags(self, flags):
        flags.byte_values_changed = True


class ChangeMetadataCommand(SegmentCommand):
    short_name = "metadata_base"
    pretty_name = "Change Metadata Abstract Command"

    def set_undo_flags(self, flags):
        flags.byte_style_changed = True


class SetDataCommand(ChangeByteValuesCommand):
    short_name = "get_data_base"
    pretty_name = "Set Data Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]

    def __init__(self, segment, start_index, end_index):
        SegmentCommand.__init__(self, segment)
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

    def do_change(self, editor, undo):
        i1 = self.start_index
        i2 = self.end_index
        undo.flags.index_range = i1, i2
        if self.cursor_at_end:
            undo.flags.cursor_index = i2
        old_data = self.segment[i1:i2].copy()
        self.segment[i1:i2] = self.get_data(old_data)
        if self.ignore_if_same_bytes and self.segment[i1:i2] == old_data:
            undo.flags.success = False
        return (old_data, )

    def undo_change(self, editor, old_data):
        old_data, = old_data
        self.segment[self.start_index:self.end_index] = old_data


class SetValuesAtIndexesCommand(ChangeByteValuesCommand):
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
        SegmentCommand.__init__(self, segment)
        self.ranges = tuple(ranges)
        self.cursor = cursor
        self.data = bytes
        self.indexes = indexes
        self.style = style
        log.debug("cursor: %x, data=%s, style=%s" % (cursor, bytes, style))
        self.relative_comment_indexes = comment_indexes
        self.comments = comments

    def get_data(self, orig):
        data_len = np.alen(self.data)
        orig_len = np.alen(orig)
        if data_len > orig_len > 1:
            data_len = orig_len
        return self.data[0:data_len]

    def do_change(self, editor, undo):
        log.debug("ranges: %s" % str(self.ranges))
        indexes = ranges_to_indexes(self.ranges)
        log.debug("indexes: %s" % str(indexes))
        if np.alen(indexes) == 0:
            if self.indexes is not None:
                indexes = self.indexes.copy() - self.indexes[0] + self.cursor
            else:
                indexes = np.arange(self.cursor, self.cursor + np.alen(self.data))
        max_index = len(self.segment)
        indexes = indexes[indexes < max_index]
        log.debug("indexes after limits: %s" % str(indexes))
        data = self.get_data(self.segment.data[indexes])
        log.debug("orig data: %s" % self.segment.data[indexes])
        log.debug("new data: %s" % data)
        indexes = indexes[0:np.alen(data)]
        log.debug("indexes truncated to data length: %s" % str(indexes))
        if self.relative_comment_indexes is not None:
            log.debug("relative comment indexes: %s" % (str(self.relative_comment_indexes)))
            subset = self.relative_comment_indexes[self.relative_comment_indexes < np.alen(indexes)]
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
        old_data = self.segment[indexes].copy()
        if self.style is not None:
            style = self.style[0:np.alen(data)]
            old_style = self.segment.style[indexes].copy()
        else:
            old_style = None
        self.segment[indexes] = data
        if old_style is not None:
            self.segment.style[indexes] = style
        if old_comment_info is not None:
            log.debug("setting comments: %s" % self.comments)
            self.segment.set_comments_at_indexes(clamped_ranges, comment_indexes, self.comments)
        return (old_data, indexes, old_style, old_comment_info)

    def undo_change(self, editor, old_data):
        old_data, old_indexes, old_style, old_comment_info = old_data
        self.segment[old_indexes] = old_data
        if old_style is not None:
            self.segment.style[old_indexes] = old_style
        if old_comment_info is not None:
            self.segment.restore_comments(old_comment_info)


class SetRangeCommand(ChangeByteValuesCommand):
    short_name = "set_range_base"
    pretty_name = "Set Ranges Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ]

    def __init__(self, segment, ranges):
        SegmentCommand.__init__(self, segment)
        self.ranges = tuple(ranges)

    def get_data(self, orig):
        raise NotImplementedError

    def do_change(self, editor, undo):
        indexes = ranges_to_indexes(self.ranges)
        undo.flags.index_range = indexes[0], indexes[-1]
        old_data = self.segment[indexes].copy()
        self.segment[indexes] = self.get_data(old_data)
        return old_data

    def undo_change(self, editor, old_data):
        indexes = ranges_to_indexes(self.ranges)
        self.segment[indexes] = old_data


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


class ChangeStyleCommand(SetDataCommand):
    short_name = "cs"
    pretty_name = "Change Style"

    def __init__(self, segment):
        start_index = 0
        end_index = len(segment)
        SetDataCommand.__init__(self, segment, start_index, end_index)

    def set_undo_flags(self, flags):
        flags.byte_style_changed = True

    def get_style(self, editor):
        style = self.segment.style[self.start_index:self.end_index].copy()
        return style

    def clip(self, style):
        if len(style) < self.end_index - self.start_index:
            self.end_index = self.start_index + len(style)

    def update_can_trace(self, editor):
        pass

    def do_change(self, editor, undo):
        old_can_trace = editor.can_trace
        new_style = self.get_style(editor)
        self.clip(new_style)
        old_style = self.segment.style[self.start_index:self.end_index].copy()
        self.segment.style[self.start_index:self.end_index] = new_style
        self.update_can_trace(editor)
        editor.document.change_count += 1
        return (old_style, old_can_trace)

    def undo_change(self, editor, old_data):
        old_style, old_can_trace = old_data
        self.segment.style[self.start_index:self.end_index] = old_style
        editor.can_trace = old_can_trace
