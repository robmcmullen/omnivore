"""Segment actions
"""
import os
import sys

import wx

from sawx.action import SawxAction, SawxRadioListAction

from ... import commands
from ... import errors

import logging
log = logging.getLogger(__name__)


class SegmentEntry:
    spaces_per_level = 4

    def __init__(self, segment, level):
        self.segment = segment
        self.indent_level = level * self.spaces_per_level

    def __str__(self):
        return (" " * self.indent_level) + str(self.segment)


class segment_select(SawxRadioListAction):
    empty_list_name = "No Valid Segments"

    def is_valid_segment(self, segment):
        return True

    def calc_list_items(self):
        valid_segments = []
        doc = self.editor.document
        if doc is not None and doc.collection is not None:
            log.debug(f"segment_select: prefix={self.prefix}, list={self.action_list_id}")
            if self.action_list_id:
                container_index = int(self.action_list_id)
                container = doc.collection.containers[container_index]
                it = container.iter_menu(0)
            else:
                it = doc.collection.iter_menu()
            for segment, level in it:
                if self.is_valid_segment(segment):
                    valid_segments.append(SegmentEntry(segment, level))
        return valid_segments

    def calc_checked_list_item(self, action_key, index, item):
        collection = self.editor.document.collection
        try:
            segment = collection[item.segment.uuid]
        except KeyError:
            raise errors.RecreateDynamicMenuBar
        return self.editor.segment_uuid == item.segment.uuid

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.editor.view_segment_uuid(item.segment.uuid)


def prompt_for_comment(e, s, ranges, desc):
    existing = s.get_first_comment(ranges)
    text = prompt_for_string(e.window.control, desc, "Add Comment", existing)
    if text is not None:
        cmd = SetCommentCommand(s, ranges, text)
        e.process_command(cmd)


class AddCommentAction(SawxAction):
    """Add a text comment to a byte location.

    A comment is associated with a single byte, so although a range can be
    selected, the comment is applied to only the first byte in the range.

    Bytes with comments will be highlighted in all displays.
    """
    name = 'Add Comment'
    accelerator = 'Alt+C'

    def is_range(self, event):
        return self.active_editor.can_copy

    def get_index(self, event):
        return self.viewer.linked_base.carets.current.index

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        if self.is_range(event):
            ranges = s.get_style_ranges(selected=True)
            if len(ranges) == 1:
                desc = "Enter comment for first byte of range:\n%s" % e.get_label_of_first_byte(ranges)
            else:
                desc = "Enter comment for first byte of each range:\n%s" % e.get_label_of_first_byte(ranges)
        else:
            ranges = []
        if not ranges:
            index = self.get_index(event)
            ranges = [(index, index+1)]
            desc = "Enter comment for location %s" % index
        prompt_for_comment(e, s, ranges, desc)


class AddCommentPopupAction(AddCommentAction):
    name = 'Add Comment'

    def is_range(self, event):
        return event.popup_data["in_selection"]

    def get_index(self, event):
        return event.popup_data["index"]


class RemoveCommentAction(SawxAction):
    """Remove any comments that are in the selected range, or if no selection
    from the current caret position.

    """
    name = 'Remove Comment'
    accelerator = 'Shift+Alt+C'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        if e.can_copy:
            ranges = s.get_style_ranges(selected=True)
        else:
            index = e.caret_index
            ranges = [(index, index+1)]
        if ranges:
            cmd = ClearCommentCommand(s, ranges)
            e.process_command(cmd)


class RemoveCommentPopupAction(SawxAction):
    name = 'Remove Comment'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        if event.popup_data["in_selection"]:
            ranges = s.get_style_ranges(selected=True)
        else:
            index = event.popup_data["index"]
            ranges = [(index, index+1)]
        if ranges:
            cmd = ClearCommentCommand(s, ranges)
            e.process_command(cmd)


def prompt_for_label(e, s, addr, desc):
    existing = s.memory_map.get(addr, "")
    text = prompt_for_string(e.window.control, desc, "Add Label", existing)
    if text is not None:
        cmd = SetLabelCommand(s, addr, text)
        e.process_command(cmd)


class AddLabelAction(SawxAction):
    """Add a label to a byte location.

    Like `Add Comment`_, a label is associated with a single byte, so although
    a range can be selected, the comment is applied to only the first byte in
    the range.

    Unlike comments, labels are *not* highlighted and are only shown in the
    disassembly window.
    """
    name = 'Add Label'
    accelerator = 'Alt+L'
    enabled_name = 'has_origin'

    def get_ranges(self, editor, segment, event):
        if editor.can_copy:  # has selected ranges
            ranges = segment.get_style_ranges(selected=True)
        else:
            ranges = [(editor.caret_index, editor.caret_index + 1)]
        return ranges

    def process_ranges(self, editor, segment, ranges):
        index = ranges[0][0]
        addr = index + segment.origin
        return addr

    def process(self, editor, segment, addr):
        desc = "Enter label for address $%04x" % addr
        prompt_for_label(editor, segment, addr, desc)

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = self.get_ranges(e, s, event)
        addr = self.process_ranges(e, s, ranges)
        self.process(e, s, addr)


class AddLabelPopupAction(AddLabelAction):
    def get_ranges(self, editor, segment, event):
        if event.popup_data["in_selection"]:
            ranges = segment.get_style_ranges(selected=True)
        else:
            index = event.popup_data["index"]
            ranges = [(index, index+1)]
        return ranges


class RemoveLabelAction(AddLabelAction):
    """Remove the label at the current caret position, or if there is a
    selection, all labels in the selected range.

    """
    name = 'Remove Label'
    accelerator = 'Shift+Alt+L'

    def process_ranges(self, editor, segment, ranges):
        return ranges

    def process(self, editor, segment, ranges):
        cmd = ClearLabelCommand(segment, ranges)
        editor.process_command(cmd)


class RemoveLabelPopupAction(RemoveLabelAction):
    def get_ranges(self, editor, segment, event):
        if event.popup_data["in_selection"]:
            ranges = segment.get_style_ranges(selected=True)
        else:
            index = event.popup_data["index"]
            ranges = [(index, index+1)]
        return ranges
