"""Segment actions
"""
import os
import sys

import wx

from sawx.ui.dialogs import prompt_for_string

from . import ViewerAction

from .. import commands
from ... import errors

import logging
log = logging.getLogger(__name__)


def prompt_for_comment(e, s, ranges, desc):
    existing = s.get_first_comment(ranges)
    text = prompt_for_string(e.control, desc, "Add Comment", existing)
    if text is not None:
        cmd = commands.SetCommentCommand(s, ranges, text)
        e.process_command(cmd)


class comment_add(ViewerAction):
    """Add a text comment to a byte location.

    A comment is associated with a single byte, so although a range can be
    selected, the comment is applied to only the first byte in the range.

    Bytes with comments will be highlighted in all displays.
    """
    name = 'Add Comment'

    def calc_enabled(self, action_key):
        return True

    def is_range(self):
        ch = self.viewer.control.caret_handler
        return ch.has_selection or len(ch) > 1

    def perform(self, action_key):
        e = self.editor
        s = e.segment
        if self.is_range():
            ranges = self.viewer.control.get_selected_ranges_including_carets()
            if len(ranges) == 1:
                desc = "Enter comment for first byte of range:\n%s" % self.viewer.get_label_of_first_byte(ranges)
            else:
                desc = "Enter comment for first byte of each range:\n%s" % self.viewer.get_label_of_first_byte(ranges)
        else:
            ranges = []
        if not ranges:
            index = self.viewer.control.get_current_caret_index()
            ranges = [(index, index+1)]
            desc = "Enter comment for location %s" % index
        prompt_for_comment(e, s, ranges, desc)


class comment_remove(ViewerAction):
    """Remove any comments that are in the selected range, or if no selection
    from the current caret position.

    """
    name = 'Remove Comment'
    accelerator = 'Shift+Alt+C'

    def perform(self, event):
        e = self.editor
        s = e.segment
        ranges = self.viewer.control.get_selected_ranges_including_carets()
        if ranges:
            cmd = commands.ClearCommentCommand(s, ranges)
            e.process_command(cmd)
