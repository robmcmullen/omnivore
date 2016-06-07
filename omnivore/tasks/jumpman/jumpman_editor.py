# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np

# Enthought library imports.
from traits.api import on_trait_change, Any, Bool, Int, Str, List, Event, Enum, Instance, File, Unicode, Property, provides
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore import get_image_path
from omnivore.tasks.hex_edit.hex_editor import HexEditor
from omnivore.tasks.bitmap_edit.bitmap_editor import MainBitmapScroller, SelectMode, BitmapEditor
from omnivore.framework.document import Document
from omnivore.arch.machine import predefined
from omnivore.utils.wx.bitviewscroller import BitmapScroller
from omnivore.utils.command import Overlay
from omnivore.utils.searchutil import HexSearcher, CharSearcher
from omnivore.utils.drawutil import get_bounds
from omnivore.utils.sortutil import invert_rects
from omnivore.tasks.hex_edit.commands import ChangeByteCommand, PasteCommand
from omnivore.framework.mouse_handler import MouseHandler

from commands import *


class JumpmanLevelView(MainBitmapScroller):
    pass

class JumpmanEditor(BitmapEditor):
    """ The toolkit specific implementation of a HexEditor.  See the
    IHexEditor interface for the API documentation.
    """
    ##### class attributes
    
    valid_mouse_modes = [SelectMode]
    
    def _map_width_default(self):
        return 40
    
    def _draw_pattern_default(self):
        return [0]

    ###########################################################################
    # 'FrameworkEditor' interface.
    ###########################################################################

    def process_extra_metadata(self, doc, e):
        HexEditor.process_extra_metadata(self, doc, e)
        pass
    
    @on_trait_change('machine.bitmap_change_event')
    def update_bitmap(self):
        self.control.recalc_view()
    
    @on_trait_change('machine.font_change_event')
    def update_fonts(self):
        pass
    
    @on_trait_change('machine.disassembler_change_event')
    def update_disassembler(self):
        pass
    
    def reconfigure_panes(self):
        self.control.recalc_view()
    
    def refresh_panes(self):
        self.control.refresh_view()
    
    def rebuild_document_properties(self):
        self.find_segment("Playfield map")
        self.control.set_mouse_mode(SelectMode)
    
    def view_segment_set_width(self, segment):
        self.bitmap_width = segment.map_width
    
    def update_mouse_mode(self):
        self.control.set_mouse_mode(self.mouse_mode)
    
    def set_current_draw_pattern(self, pattern, control):
        try:
            iter(pattern)
        except TypeError:
            self.draw_pattern = [pattern]
        else:
            self.draw_pattern = pattern
        if control != self.tile_map:
            self.tile_map.clear_tile_selection()
        if control != self.character_set:
            self.character_set.clear_tile_selection()

    def mark_index_range_changed(self, index_range):
        pass
    
    def perform_idle(self):
        pass
    
    def process_paste_data_object(self, data_obj, cmd_cls=None):
        bytes, extra = self.get_numpy_from_data_object(data_obj)
        ranges, indexes = self.get_selected_ranges_and_indexes()
        print extra
        if extra is None:
            cmd = PasteCommand(self.segment, ranges, self.cursor_index, indexes)
        else:
            if cmd_cls is None:
                cmd_cls = PasteRectangularCommand
            format_id, r, c = extra
            cmd = cmd_cls(self.segment, self.anchor_start_index, r, c, self.control.bytes_per_row, bytes)
        self.process_command(cmd)
    
    def create_clipboard_data_object(self):
        if self.anchor_start_index != self.anchor_end_index:
            anchor_start, anchor_end, (r1, c1), (r2, c2) = self.control.get_highlight_indexes()
            print anchor_start, anchor_end, (r1, c1), (r2, c2)
            bpr = self.control.bytes_per_row
            last = r2 * bpr
            print last
            d = self.segment[:last].reshape(-1, bpr)
            print d
            data = d[r1:r2, c1:c2]
            print data
            data_obj = wx.CustomDataObject("numpy,columns")
            data_obj.SetData("%d,%d,%s" % (r2 - r1, c2 - c1, data.tostring()))
            return data_obj
        return None
    
    def highlight_selected_ranges(self):
        s = self.segment
        s.clear_style_bits(selected=True)
        s.set_style_ranges_rect(self.selected_ranges, selected=True)
        self.document.change_count += 1
    
    def invert_selection_ranges(self, ranges):
        rects = [(rect[2], rect[3]) for rect in [self.segment.get_rect_indexes(r[0], r[1]) for r in ranges]]
        inverted = invert_rects(rects, self.control.total_rows, self.control.bytes_per_row)
        ranges = self.segment.rects_to_ranges(inverted)
        return ranges
    
    def get_extra_segment_savers(self, segment):
        return []
    
    ###########################################################################
    # Trait handlers.
    ###########################################################################


    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        # Base-class constructor.
        self.control = JumpmanLevelView(parent, self.task)

        # create attribute so HexEditor parent will reference the bitmap
        self.bitmap = self.control

        ##########################################
        # Events.
        ##########################################

        # Get related controls
        self.segment_list = self.window.get_dock_pane('jumpman_edit.segments').control
        self.undo_history = self.window.get_dock_pane('jumpman_edit.undo').control

        # Load the editor's contents.
        self.load()

        return self.control

    #### wx event handlers ####################################################
    
    def index_clicked(self, index, bit, control):
        self.cursor_index = index
        if control != self.control:
            self.control.select_index(index)
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
