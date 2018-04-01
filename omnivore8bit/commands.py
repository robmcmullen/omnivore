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
    short_name = "change_values_base"
    pretty_name = "Change Values Abstract Command"

    def __init__(self, segment, advance=False):
        SegmentCommand.__init__(self, segment)
        self.advance = advance

    def set_undo_flags(self, flags):
        flags.byte_values_changed = True


class ChangeMetadataCommand(SegmentCommand):
    short_name = "metadata_base"
    pretty_name = "Change Metadata Abstract Command"

    def set_undo_flags(self, flags):
        flags.byte_style_changed = True


class SetContiguousDataCommand(ChangeByteValuesCommand):
    short_name = "set_data_base"
    pretty_name = "Set Data Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ]

    def __init__(self, segment, start_index, end_index, advance=False):
        ChangeByteValuesCommand.__init__(self, segment, advance)
        self.start_index = start_index
        if start_index == end_index:
            end_index += 1
        self.end_index = end_index
        self.caret_at_end = False
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
        if self.caret_at_end:
            undo.flags.caret_index = i2
        if self.advance:
            undo.flags.advance_caret_position_in_control = editor.focused_viewer.control
        old_data = self.segment[i1:i2].copy()
        self.segment[i1:i2] = self.get_data(old_data)
        if self.ignore_if_same_bytes and self.segment[i1:i2] == old_data:
            undo.flags.success = False
        return (old_data, )

    def undo_change(self, editor, old_data):
        old_data, = old_data
        self.segment[self.start_index:self.end_index] = old_data


class SetRangeCommand(ChangeByteValuesCommand):
    short_name = "set_range_base"
    pretty_name = "Set Ranges Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('range_to_index_function', 'func_pointer'),
            ]

    def __init__(self, segment, ranges, advance=False):
        ChangeByteValuesCommand.__init__(self, segment, advance)
        self.ranges = tuple(ranges)

        # function to convert ranges to indexes will be set the first time this
        # command is performed so it can use the function appropriate to the
        # currently focused viewer.
        self.range_to_index_function = None

    def get_data(self, orig):
        raise NotImplementedError

    def perform(self, editor, undo_info):
        if self.range_to_index_function is None:
            self.range_to_index_function = editor.focused_viewer.range_processor
        ChangeByteValuesCommand.perform(self, editor, undo_info)

    def do_change(self, editor, undo):
        indexes = self.range_to_index_function(self.ranges)
        undo.flags.index_range = indexes[0], indexes[-1]
        old_data = self.segment[indexes].copy()
        self.segment[indexes] = self.get_data(old_data)
        if self.advance:
            undo.flags.advance_caret_position_in_control = editor.focused_viewer.control
        return old_data

    def undo_change(self, editor, old_data):
        indexes = self.range_to_index_function(self.ranges)
        self.segment[indexes] = old_data


class SetRangeValueCommand(SetRangeCommand):
    short_name = "set_range_base"
    pretty_name = "Set Ranges Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('bytes', 'string'),
            ]

    def __init__(self, segment, ranges, bytes, advance=False):
        SetRangeCommand.__init__(self, segment, ranges, advance)
        self.data = bytes

    def get_data(self, orig):
        return self.data


class SetIndexedDataCommand(ChangeByteValuesCommand):
    short_name = "set_indexes_value"
    pretty_name = "Set Values at Indexes"
    serialize_order =  [
            ('segment', 'int'),
            ('indexes', 'int_list'),
            ('data', 'string'),
            ]

    def __init__(self, segment, indexes, data, advance=False):
        ChangeByteValuesCommand.__init__(self, segment, advance)
        self.indexes = indexes
        self.data = data

    def __str__(self):
        return "%s (%04x indexes)" % (self.pretty_name, len(self.indexes))

    def get_data(self, orig):
        return self.data

    def do_change(self, editor, undo):
        i1 = min(self.indexes)
        i2 = max(self.indexes)
        undo.flags.index_range = i1, i2
        if self.advance:
            undo.flags.advance_caret_position_in_control = editor.focused_viewer.control
        old_data = self.segment[self.indexes].copy()
        self.segment[self.indexes] = self.get_data(old_data)
        return (old_data, )

    def undo_change(self, editor, old_data):
        old_data, = old_data
        self.segment[self.indexes] = old_data


class ChangeStyleCommand(SetContiguousDataCommand):
    short_name = "cs"
    pretty_name = "Change Style"

    def __init__(self, segment):
        start_index = 0
        end_index = len(segment)
        SetContiguousDataCommand.__init__(self, segment, start_index, end_index)

    def set_undo_flags(self, flags):
        flags.byte_style_changed = True

    def get_style(self, editor):
        style = self.segment.style[self.start_index:self.end_index].copy()
        return style

    def clip(self, style):
        if len(style) < self.end_index - self.start_index:
            self.end_index = self.start_index + len(style)

    def update_is_tracing(self, viewer):
        pass

    def do_change(self, editor, undo):
        viewer = editor.focused_viewer
        old_is_tracing = viewer.is_tracing
        new_style = self.get_style(editor)
        self.clip(new_style)
        old_style = self.segment.style[self.start_index:self.end_index].copy()
        self.segment.style[self.start_index:self.end_index] = new_style
        self.update_is_tracing(viewer)
        editor.document.change_count += 1
        return (old_style, old_is_tracing)

    def undo_change(self, editor, old_data):
        old_style, old_is_tracing = old_data
        self.segment.style[self.start_index:self.end_index] = old_style
        viewer.is_tracing = old_is_tracing
