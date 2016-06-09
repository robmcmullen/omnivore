# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np
from atrcopy import SegmentData, DefaultSegment

# Enthought library imports.
from traits.api import on_trait_change, Any, Bool, Int, Str, List, Event, Enum, Instance, File, Unicode, Property, provides
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore import get_image_path
from omnivore.tasks.hex_edit.hex_editor import HexEditor
from omnivore.tasks.bitmap_edit.bitmap_editor import MainBitmapScroller, SelectMode, BitmapEditor
from omnivore.framework.document import Document
from omnivore.arch.machine import Machine, predefined
from omnivore.utils.wx.bitviewscroller import BitmapScroller
from omnivore.utils.command import Overlay
from omnivore.utils.searchutil import HexSearcher, CharSearcher
from omnivore.utils.drawutil import get_bounds
from omnivore.utils.sortutil import invert_rects
from omnivore.utils.jumpman import JumpmanLevelBuilder
from omnivore.tasks.hex_edit.commands import ChangeByteCommand, PasteCommand
from omnivore.framework.mouse_handler import MouseHandler

from commands import *

import logging
log = logging.getLogger(__name__)


class JumpmanLevelView(MainBitmapScroller):
    def __init__(self, *args, **kwargs):
        MainBitmapScroller.__init__(self, *args, **kwargs)
        self.level_builder = None

    def get_segment(self, editor):
        self.level_builder = JumpmanLevelBuilder(editor.document.user_segments)
        self.pick_buffer = editor.pick_buffer
        return editor.screen

    def clear_screen(self):
        self.segment[:] = 0
        self.pick_buffer[:] = -1

    def compute_image(self):
        if self.level_builder is None:
            return
        self.clear_screen()
        source = self.editor.segment
        start = source.start_addr
        if len(source) < 0x38:
            return
        index = source[0x38]*256 + source[0x37]
        log.debug("level def table: %x" % index)
        if index > start:
            index -= start
        if index < len(source):
            commands = source[index:index + 500]  # arbitrary max number of bytes
        else:
            commands = source[index:index]
        self.level_builder.draw_commands(self.segment, commands, current_segment=source, pick_buffer=self.pick_buffer)
        self.pick_buffer[self.pick_buffer >= 0] += index

    def get_image(self):
        self.compute_image()
        return MainBitmapScroller.get_image(self)


class AnticDSelectMode(SelectMode):
    icon = "select.png"
    menu_item_name = "Select"
    menu_item_tooltip = "Select regions"
    
    def get_xy(self, evt):
        c = self.canvas
        e = c.editor
        if e is not None:
            index, bit, inside = c.event_coords_to_byte(evt)
            r0, c0 = c.byte_to_row_col(index)
            x = c0 * 4 + (3 - bit)
            y = r0
            if y < e.antic_lines:
                pick = e.pick_buffer[x, y]
            else:
                pick = -1
            return index, x, y, pick
        return None, None, None, None

    def display_coords(self, evt, extra=None):
        c = self.canvas
        e = c.editor
        if e is not None:
            index, x, y, pick = self.get_xy(evt)
            msg = "x=%d (0x%x) y=%d (0x%x) index=%d (0x%x) pick=%d" % (x, x, y, y, index, index, pick)
            if extra:
                msg += " " + extra
            e.task.status_bar.message = msg
    
    def get_display_rect(self):
        c = self.canvas
        anchor_start, anchor_end, (r1, c1), (r2, c2) = c.get_highlight_indexes()
        extra = None
        if r1 >= 0:
            w = c2 - c1
            h = r2 - r1
            if w > 0 or h > 0:
                extra = "rectangle: width=%d (0x%x), height=%d (0x%x)" % (w, w, h, h)
        return extra

    def highlight_pick(self, evt):
        index, x, y, pick = self.get_xy(evt)
        if pick >= 0:
            e = self.canvas.editor
            e.index_clicked(pick, 0, None)
            e.select_range(pick - 3, pick + 1)
            wx.CallAfter(e.index_clicked, pick, 0, None)

    def process_left_down(self, evt):
        self.highlight_pick(evt)
        self.display_coords(evt)

    def process_left_up(self, evt):
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        self.highlight_pick(evt)
        self.display_coords(evt)

    def process_mouse_motion_up(self, evt):
        self.display_coords(evt)


class JumpmanEditor(BitmapEditor):
    """ The toolkit specific implementation of a HexEditor.  See the
    IHexEditor interface for the API documentation.
    """
    ##### class attributes
    
    valid_mouse_modes = [AnticDSelectMode]
    
    ##### Default traits
    
    def _machine_default(self):
        return Machine(name="Jumpman", bitmap_renderer=predefined['bitmap_renderer'][2])

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
        self.hex_edit.recalc_view()
        self.bitmap.recalc_view()
    
    @on_trait_change('machine.font_change_event')
    def update_fonts(self):
        pass
    
    @on_trait_change('machine.disassembler_change_event')
    def update_disassembler(self):
        pass
    
    def reconfigure_panes(self):
        self.hex_edit.recalc_view()
        self.bitmap.recalc_view()
    
    def refresh_panes(self):
        self.hex_edit.refresh_view()
        self.bitmap.refresh_view()
    
    def rebuild_document_properties(self):
        self.bitmap.set_mouse_mode(AnticDSelectMode)
    
    def copy_view_properties(self, old_editor):
        self.find_segment(segment=old_editor.segment)
    
    def view_segment_set_width(self, segment):
        self.bitmap_width = 40
        colors = segment[0x2e:0x33].copy()
        # on some levels, the bombs are set to color 0 because they are cycled
        # to produce a glowing effect, but that's not visible here so we force
        # it to be bright white
        fg = colors[0:4]
        fg[fg == 0] = 15
        self.machine.update_colors(colors)
    
    def update_mouse_mode(self):
        self.bitmap.set_mouse_mode(self.mouse_mode)
    
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
    
    def highlight_selected_ranges(self):
        HexEditor.highlight_selected_ranges(self)

    def mark_index_range_changed(self, index_range):
        pass
    
    def perform_idle(self):
        pass
    
    def process_paste_data_object(self, data_obj, cmd_cls=None):
        pass
    
    def create_clipboard_data_object(self):
        return HexEditor.create_clipboard_data_object(self)
    
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
        self.bitmap = JumpmanLevelView(parent, self.task)

        self.antic_lines = 90
        data = np.zeros(40 * self.antic_lines, dtype=np.uint8)
        data[::41] = 255
        r = SegmentData(data)
        self.screen = DefaultSegment(r, 0x7000)
        self.pick_buffer = np.zeros((160, self.antic_lines), dtype=np.int32)

        ##########################################
        # Events.
        ##########################################

        # Get related controls
        self.segment_list = self.window.get_dock_pane('jumpman.segments').control
        self.undo_history = self.window.get_dock_pane('jumpman.undo').control
        self.hex_edit = self.window.get_dock_pane('jumpman.hex').control

        # Load the editor's contents.
        self.load()

        return self.bitmap

    #### wx event handlers ####################################################
    
    def index_clicked(self, index, bit, control):
        self.cursor_index = index
        if control != self.hex_edit:
            self.hex_edit.select_index(index)
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
