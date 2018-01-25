import os
import sys

import wx
#import wx.grid as Grid

from traits.api import on_trait_change, Bool

from atrcopy import match_bit_mask, comment_bit_mask, user_bit_mask, selected_bit_mask, diff_bit_mask

from omnivore8bit.ui.selection_mixin import SelectionMixin
from omnivore.utils.wx import compactgrid as cg
from omnivore8bit.arch.disasm import get_style_name

from ..byte_edit.actions import GotoIndexAction
from ..byte_edit.commands import ChangeByteCommand

from . import SegmentViewer

import logging
log = logging.getLogger(__name__)


class SegmentTable(cg.HexTable):
    def __init__(self, linked_base):
        self.segment = linked_base.segment
        cg.HexTable.__init__(self, self.segment.data, self.segment.style, 16, self.segment.start_addr, col_widths=None, start_offset_mask=0x0f)

    def get_label_at_index(self, index):
        # Can't just return hex value of index because some segments (like the
        # raw sector segment) use different labels
        return self.segment.label(index, True)


class HexEditControl(cg.HexGridWindow, SelectionMixin):
    """
    View for editing in hexidecimal notation.
    """
    short_name = "hex"

    def __init__(self, parent, linked_base, **kwargs):
        """Create the HexEdit viewer
        """
        self.linked_base = linked_base
        table = SegmentTable(linked_base)
        cg.HexGridWindow.__init__(self, table, linked_base.cached_preferences, parent)
        SelectionMixin.__init__(self)

    @property
    def table(self):
        return self.main.table

    def on_left_up(self, evt):
        self.handle_select_end(self.linked_base, evt)

    def on_left_down(self, evt):
        self.handle_select_start(self.linked_base, evt)
        wx.CallAfter(self.SetFocus)

    def on_left_dclick(self, evt):
        self.on_left_down(evt)

    def on_motion(self, evt):
        self.on_motion_update_status(evt)
        if evt.LeftIsDown():
            self.handle_select_motion(self.linked_base, evt)
        evt.Skip()

    def on_motion_update_status(self, evt):
        row, cell = self.main.pixel_pos_to_row_cell(evt.GetX(), evt.GetY())
        c2 = self.table.enforce_valid_caret(row, cell)
        inside = cell == c2
        if inside:
            index, _ = self.table.get_index_range(row, cell)
            self.linked_base.show_status_message(self.get_status_at_index(index))

    def get_location_from_event(self, evt):
        row, cell = self.main.pixel_pos_to_row_cell(evt.GetX(), evt.GetY())
        c2 = self.table.enforce_valid_caret(row, cell)
        inside = cell == c2
        index1, index2 = self.table.get_index_range(row, c2)
        return row, 0, index1, index2, inside

    def get_start_end_index_of_row(self, row):
        index1, _ = self.get_index_range(row, 0)
        _, index2 = self.get_index_range(row, self.bytes_per_row - 1)
        return index1, index2

    def get_status_at_index(self, index):
        if self.table.is_index_valid(index):
            label = self.table.get_label_at_index(index)
            message = self.get_status_message_at_index(index)
            return "%s: %s %s" % (self.short_name, label, message)
        return ""

    def get_status_message_at_index(self, index):
        msg = get_style_name(self.linked_base.segment, index)
        comments = self.linked_base.segment.get_comment(index)
        return "%s  %s" % (msg, comments)

    def recalc_view(self):
        table = SegmentTable(self.linked_base)
        self.main.recalc_view(table, self.linked_base.cached_preferences)

    def change_value(self, row, col, text):
        """Called after editor has provided a new value for a cell.
        
        Can use this to override the default handler.  Return True if the grid
        should be updated, or False if the value is invalid or the grid will
        be updated some other way.
        """
        try:
            val = int(text,16)
            if val >= 0 and val < 256:
                start, end = self.table.get_index_range(row, col)
                if self.table.is_index_valid(start):
                    cmd = ChangeByteCommand(self.table.segment, start, end, val)
                    self.linked_base.editor.process_command(cmd)
        except ValueError:
            pass
        return False

    def get_goto_actions(self, r, c):
        actions = []
        addr_dest = self.table.get_addr_dest(r, c)
        actions.extend(self.linked_base.get_goto_actions_other_segments(addr_dest))
        index, _ = self.table.get_index_range(r, c)
        actions.extend(self.linked_base.get_goto_actions_same_byte(index))
        return actions

    def get_popup_actions(self, r, c, inside):
        if not inside:
            actions = []
        else:
            actions = self.get_goto_actions(r, c)
            if actions:
                actions.append(None)
        actions.extend(self.segment_viewer.common_popup_actions())
        return actions


class HexEditViewer(SegmentViewer):
    name = "hex"

    pretty_name = "Hex"

    has_hex = True

    @classmethod
    def create_control(cls, parent, linked_base):
        return HexEditControl(parent, linked_base)

    def recalc_data_model(self):
        """Rebuild the data model after a document formatting (or other
        structural change) or loading a new document.
        """
        self.control.recalc_view()
