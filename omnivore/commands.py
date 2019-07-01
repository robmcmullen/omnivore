import numpy as np

from sawx.utils.command import Command, UndoInfo
from sawx.utils.sortutil import ranges_to_indexes, indexes_to_ranges
from sawx.utils.permute import bit_reverse_table

import logging
log = logging.getLogger(__name__)
progress_log = logging.getLogger("progress")


class SegmentCommand(Command):
    short_name = "segment_data_base"
    ui_name = "Segment Modification Abstract Command"
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
    ui_name = "Change Values Abstract Command"

    def __init__(self, segment, advance=False):
        SegmentCommand.__init__(self, segment)
        self.advance = advance

    def set_undo_flags(self, flags):
        flags.byte_values_changed = True


class ChangeMetadataCommand(SegmentCommand):
    short_name = "metadata_base"
    ui_name = "Change Metadata Abstract Command"

    def set_undo_flags(self, flags):
        flags.byte_style_changed = True


class SetSelectionCommand(ChangeByteValuesCommand):
    short_name = "set_indexes_value"
    ui_name = "Set Values at Indexes"
    serialize_order =  [
            ('segment', 'int'),
            ('selection', 'selection'),
            ('data', 'string'),
            ]

    def __init__(self, segment, selection, data=0, advance=False):
        ChangeByteValuesCommand.__init__(self, segment, advance)
        self.selection = selection.copy()  # use FrozenSelection so it won't change after undo/redo
        self.data = data

    def __str__(self):
        return f"{self.ui_name}"

    def get_indexes(self):
        return self.selection.calc_indexes(self.segment, True)

    def get_data(self, orig):
        return self.data

    def change_data_at_indexes(self, indexes):
        old_data = self.segment[indexes].copy()
        self.segment[indexes] = self.get_data(old_data)
        return (old_data, indexes)

    def do_change(self, editor, undo):
        indexes = self.get_indexes()
        i1 = min(indexes)
        i2 = max(indexes)
        undo.flags.index_range = i1, i2
        if self.advance:
            undo.flags.advance_caret_position_in_control = editor.focused_viewer.control
        return self.change_data_at_indexes(indexes)

    def undo_change(self, editor, old_data):
        old_data, indexes = old_data
        self.segment[indexes] = old_data
















class SetContiguousDataCommand(ChangeByteValuesCommand):
    short_name = "set_data_base"
    ui_name = "Set Data Abstract Command"
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
            return "%s @ %04x-%04x" % (self.ui_name, self.start_index + self.segment.origin, self.end_index + self.segment.origin)
        else:
            return "%s @ %04x" % (self.ui_name, self.start_index)

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


class ChangeByteCommand(SetContiguousDataCommand):
    short_name = "cb"
    ui_name = "Change Bytes"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ('byte_values', 'string'),
            ('caret_at_end', 'bool'),
            ('ignore_if_same_bytes', 'bool'),
            ]

    def __init__(self, segment, start_index, end_index, byte_values, caret_at_end=False, ignore_if_same_bytes=False, advance=False):
        SetContiguousDataCommand.__init__(self, segment, start_index, end_index, advance=advance)
        self.data = byte_values
        self.caret_at_end = caret_at_end
        self.ignore_if_same_bytes = ignore_if_same_bytes

    def get_data(self, orig):
        return self.data


class CoalescingChangeByteCommand(ChangeByteCommand):
    short_name = "ccb"

    def can_coalesce(self, next_command):
        return next_command.start_index == self.start_index and next_command.end_index == self.end_index

    def coalesce_merge(self, next_command):
        self.data = next_command.data


class SetRangeCommand(ChangeByteValuesCommand):
    short_name = "set_range_base"
    ui_name = "Set Ranges Abstract Command"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('range_to_index_function', 'func_pointer'),
            ]

    def __init__(self, segment, ranges, advance=False, range_to_index_function=None):
        ChangeByteValuesCommand.__init__(self, segment, advance)
        self.ranges = tuple(ranges)

        # function to convert ranges to indexes will be set the first time this
        # command is performed so it can use the function appropriate to the
        # currently focused viewer.
        self.range_to_index_function = range_to_index_function

    def get_data(self, orig):
        raise NotImplementedError

    def perform(self, editor, undo_info):
        if self.range_to_index_function is None:
            self.range_to_index_function = editor.focused_viewer.range_processor
        ChangeByteValuesCommand.perform(self, editor, undo_info)

    def do_change(self, editor, undo):
        indexes = self.range_to_index_function(self.ranges)
        # print(f"{self.short_name}: ranges={self.ranges}, indexes={indexes}")
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
    short_name = "set_range_value"
    ui_name = "Set Ranges To Value"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('data', 'string'),
            ]

    def __init__(self, segment, ranges, data, advance=False, range_to_index_function=None):
        SetRangeCommand.__init__(self, segment, ranges, advance, range_to_index_function)
        self.data = data

    def get_data(self, orig):
        return self.data


class SetRangeValueModifyIndexesCommand(SetRangeCommand):
    short_name = "set_range_value_modify_index"
    ui_name = "Set Ranges To Value + Modify"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('data', 'string'),
            ]

    def __init__(self, segment, ranges, data, advance=False, range_to_index_function=None):
        SetRangeCommand.__init__(self, segment, ranges, advance, range_to_index_function)
        self.data = data

    def get_data_and_indexes(self, indexes):
        return self.data, indexes

    def do_change(self, editor, undo):
        indexes = self.range_to_index_function(self.ranges)
        print(f"{self.short_name}: ranges={self.ranges}, indexes={indexes}")
        undo.flags.index_range = indexes[0], indexes[-1]
        data, new_indexes = self.get_data_and_indexes(indexes)
        old_data = self.segment[new_indexes].copy()
        self.segment[new_indexes] = data
        if self.advance:
            undo.flags.advance_caret_position_in_control = editor.focused_viewer.control
        return old_data


class SetDisasmCommand(SetRangeCommand):
    short_name = "set_disasm_type"
    ui_name = "Set Disassembler Type"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('disasm_type', 'int'),
            ]

    def __init__(self, segment, ranges, disasm_type):
        SetRangeCommand.__init__(self, segment, ranges)
        self.disasm_type = disasm_type

    def get_data(self, orig):
        return self.disasm_type

    def do_change(self, editor, undo):
        indexes = self.range_to_index_function(self.ranges)
        # print(f"{self.short_name}: ranges={self.ranges}, indexes={indexes}")
        undo.flags.index_range = indexes[0], indexes[-1]
        old_data = self.segment.disasm_type[indexes].copy()
        self.segment.disasm_type[indexes] = self.get_data(old_data)
        self.segment.update_data_style_from_disasm_type()
        if self.advance:
            undo.flags.advance_caret_position_in_control = editor.focused_viewer.control
        return old_data

    def undo_change(self, editor, old_data):
        indexes = self.range_to_index_function(self.ranges)
        self.segment.disasm_type[indexes] = old_data
        self.segment.update_data_style_from_disasm_type()


class ChangeStyleCommand(SetContiguousDataCommand):
    short_name = "cs"
    ui_name = "Change Style"

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
