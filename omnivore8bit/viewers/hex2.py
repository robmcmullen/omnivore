import os
import sys

import wx

from traits.api import on_trait_change, Bool

from atrcopy import match_bit_mask, comment_bit_mask, user_bit_mask, selected_bit_mask, diff_bit_mask

from ..ui.segment_grid import SegmentGridControl, SegmentTable
from omnivore.utils.wx import compactgrid as cg
from omnivore8bit.arch.disasm import get_style_name

from ..byte_edit.actions import GotoIndexAction
from ..byte_edit.commands import ChangeByteCommand

from . import SegmentViewer

import logging
log = logging.getLogger(__name__)


class HexEditControl(SegmentGridControl):
    """
    View for editing in hexidecimal notation.
    """
    short_name = "hex"

    def set_viewer_defaults(self):
        old = self.items_per_row
        self.items_per_row = self.view_params.hex_grid_width
        if old is not None and self.items_per_row != old:
            self.recalc_view()

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


class HexEditViewer(SegmentViewer):
    name = "hex"

    pretty_name = "Hex"

    has_hex = True

    @classmethod
    def create_control(cls, parent, linked_base):
        return HexEditControl(parent, linked_base.segment, linked_base, linked_base.cached_preferences)

    def recalc_data_model(self):
        """Rebuild the data model after a document formatting (or other
        structural change) or loading a new document.
        """
        self.control.recalc_view()

    def update_carets(self, flags):
        pass
