import numpy as np

from omnivore.utils.command import Command, UndoInfo
from omnivore.utils.sortutil import ranges_to_indexes
from omnivore8bit.utils.searchalgorithm import AlgorithmSearcher
from omnivore.utils.file_guess import FileGuess
from omnivore.utils.permute import bit_reverse_table

import logging
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


class ChangeMetadataCommand(SegmentCommand):
    short_name = "metadata_base"
    pretty_name = "Change Metadata Abstract Command"

    def change_metadata(self, editor):
        raise NotImplementedError

    def restore_metadata(self, editor, old_data):
        raise NotImplementedError

    def set_undo_flags(self):
        self.undo_info.flags.byte_style_changed = True

    def perform(self, editor):
        self.undo_info = undo = UndoInfo()
        old_data = self.change_metadata(editor)
        undo.data = (old_data, )
        self.set_undo_flags()
        return undo

    def undo(self, editor):
        old_data, = self.undo_info.data
        self.restore_metadata(editor, old_data)
        return self.undo_info


class SetDataCommand(SegmentCommand):
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
        if self.ignore_if_same_bytes and self.segment[i1:i2] == old_data:
            undo.flags.success = False
        undo.data = (old_data, )
        return undo

    def undo(self, editor):
        old_data, = self.undo_info.data
        self.segment[self.start_index:self.end_index] = old_data
        return self.undo_info


class SetValuesAtIndexesCommand(SegmentCommand):
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
        self.relative_comment_indexes = comment_indexes
        self.comments = comments

    def get_data(self, orig):
        raise NotImplementedError

    def perform(self, editor):
        raise NotImplementedError

    def undo(self, editor):
        old_data, old_indexes, old_style, old_comment_info = self.undo_info.data
        self.segment[old_indexes] = old_data
        self.segment.style[old_indexes] = old_style
        old_comment_indexes, old_comments = old_comment_info
        self.segment.remove_comments_at_indexes(old_indexes)
        self.segment.set_comments_at_indexes(old_comment_indexes, old_comments)
        return self.undo_info


class SetRangeCommand(SegmentCommand):
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

    def perform(self, editor):
        indexes = ranges_to_indexes(self.ranges)
        self.undo_info = undo = UndoInfo()
        undo.flags.byte_values_changed = True
        undo.flags.index_range = indexes[0], indexes[-1]
        old_data = self.segment[indexes].copy()
        self.segment[indexes] = self.get_data(old_data)
        undo.data = (old_data, )
        return undo

    def undo(self, editor):
        old_data, = self.undo_info.data
        indexes = ranges_to_indexes(self.ranges)
        self.segment[indexes] = old_data
        return self.undo_info


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

    def get_style(self, editor):
        style = self.segment.style[self.start_index:self.end_index].copy()
        return style

    def clip(self, style):
        if len(style) < self.end_index - self.start_index:
            self.end_index = self.start_index + len(style)

    def update_can_trace(self, editor):
        pass

    def set_undo_flags(self):
        self.undo_info.flags.byte_style_changed = True

    def perform(self, editor):
        self.undo_info = undo = UndoInfo()
        self.set_undo_flags()
        old_can_trace = editor.can_trace
        new_style = self.get_style(editor)
        self.clip(new_style)
        old_style = self.segment.style[self.start_index:self.end_index].copy()
        self.segment.style[self.start_index:self.end_index] = new_style
        self.update_can_trace(editor)
        editor.document.change_count += 1
        undo.data = (old_style, old_can_trace)
        return undo

    def undo(self, editor):
        old_style, old_can_trace = self.undo_info.data
        self.segment.style[self.start_index:self.end_index] = old_style
        editor.can_trace = old_can_trace
        return self.undo_info
