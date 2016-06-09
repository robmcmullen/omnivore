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
        return editor.screen

    def compute_image(self):
        if self.level_builder is None:
            return
        self.segment[:] = 0  # clear screen
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
        self.level_builder.draw_commands(self.segment, commands, current_segment=source)

    def get_image(self):
        self.compute_image()
        return MainBitmapScroller.get_image(self)


class JumpmanEditor(BitmapEditor):
    """ The toolkit specific implementation of a HexEditor.  See the
    IHexEditor interface for the API documentation.
    """
    ##### class attributes
    
    valid_mouse_modes = [SelectMode]
    
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
        self.bitmap.set_mouse_mode(SelectMode)
    
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

        data = np.zeros(40 * 90, dtype=np.uint8)
        data[::41] = 255
        r = SegmentData(data)
        self.screen = DefaultSegment(r, 0x7000)

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
