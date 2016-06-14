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
from omnivore.utils.jumpman import *
from omnivore.tasks.hex_edit.commands import ChangeByteCommand, PasteCommand
from omnivore.framework.mouse_handler import MouseHandler

from commands import *

import logging
log = logging.getLogger(__name__)


class JumpmanSelectMode(SelectMode):
    def draw_extra_objects(self, lever_builder, screen, current_segment):
        return

    def draw_overlay(self, bitimage):
        return
    
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

    def process_left_down(self, evt):
        self.display_coords(evt)

    def process_left_up(self, evt):
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        self.display_coords(evt)

    def process_mouse_motion_up(self, evt):
        self.display_coords(evt)


class AnticDSelectMode(JumpmanSelectMode):
    icon = "select.png"
    menu_item_name = "Select"
    menu_item_tooltip = "Select regions"

    def highlight_pick(self, evt):
        index, x, y, pick = self.get_xy(evt)
        if pick >= 0:
            e = self.canvas.editor
            e.index_clicked(pick, 0, None)
            e.select_range(pick, pick + 4)
            wx.CallAfter(e.index_clicked, pick, 0, None)

    def process_left_down(self, evt):
        self.highlight_pick(evt)
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        self.highlight_pick(evt)
        self.display_coords(evt)


class PeanutCheckMode(JumpmanSelectMode):
    icon = "jumpman_peanut_check.png"
    menu_item_name = "Peanut Check"
    menu_item_tooltip = "Check for valid peanut positions"

    def __init__(self, *args, **kwargs):
        JumpmanSelectMode.__init__(self, *args, **kwargs)
        self.mouse_down = (0, 0)
        self.batch = None

    def get_harvest_offset(self):
        source = self.canvas.editor.segment
        if len(source) < 0x47:
            hx = hy = 0, 0
        else:
            hx = source[0x46]
            hy = source[0x47]
        return hx, hy

    def draw_overlay(self, bitimage):
        hx, hy = self.get_harvest_offset()
        w = 160
        h = 88
        bad = (203, 144, 161)
        orig = bitimage.copy()
        
        # Original (slow) algorithm to determine bad locations:
        #
        # def is_allergic(x, y, hx, hy):
        #     return (x + 0x30 + hx) & 0x1f < 7 or (2 * y + 0x20 + hy) & 0x1f < 5
        #
        # Note that in the originial 6502 code, the y coord is in player
        # coords, which is has twice the resolution of graphics 7. That's the
        # factor of two in the y part. Simplifying, the bad locations can be
        # defined in sets of 32 columns and 16 rows:
        #
        # x: 16 - hx, 16 - hx + 6 inclusive
        # y: 0 - hy/2, 0 - hy/2 + 2 inclusive
        hx = hx & 0x1f
        hy = (hy & 0x1f) / 2
        startx = (16 - hx) & 0x1f
        starty = (0 - hy) & 0xf

        # Don't know how to set multiple ranges simultaneously in numpy, so use
        # a slow python loop
        for x in range(startx, startx + 7):
            x = x & 0x1f
            bitimage[0:h:, x::32] = orig[0:h:, x::32] / 8 + bad
        for y in range(starty, starty + 3):
            y = y & 0xf
            bitimage[y:h:16,:] = orig[y:h:16,:] / 8 + bad

    def display_coords(self, evt, extra=None):
        c = self.canvas
        e = c.editor
        if e is not None:
            hx, hy = self.get_harvest_offset()
            msg = "harvest offset: x=%d (0x%x) y=%d (0x%x)" % (hx, hx, hy, hy)
            e.task.status_bar.message = msg

    def change_harvest_offset(self, evt, start=False):
        c = self.canvas
        e = c.editor
        if e is None:
            return
        index, x, y, pick = self.get_xy(evt)
        if start:
            self.batch = Overlay()
            hx, hy = self.get_harvest_offset()
            self.mouse_down = hx + x, hy + y
        else:
            dx = (self.mouse_down[0] - x) & 0x1f
            dy = (self.mouse_down[1] - y) & 0x1f
            self.display_coords(evt)
            values = [dx, dy]
            source = self.canvas.editor.segment
            cmd = ChangeByteCommand(source, 0x46, 0x48, values)
            e.process_command(cmd, self.batch)
        self.display_coords(evt)

    def process_left_down(self, evt):
        self.change_harvest_offset(evt, True)

    def process_left_up(self, evt):
        c = self.canvas
        e = c.editor
        if e is None:
            return
        e.end_batch()
        self.batch = None

        # Force updating of the hex view
        e.document.change_count += 1
        e.refresh_panes()

    def process_mouse_motion_down(self, evt):
        self.change_harvest_offset(evt)


class DrawMode(JumpmanSelectMode):
    icon = "select.png"
    menu_item_name = "Draw"
    menu_item_tooltip = "Draw stuff"
    drawing_object = Girder

    def __init__(self, *args, **kwargs):
        JumpmanSelectMode.__init__(self, *args, **kwargs)
        self.mouse_down = (0, 0)
        self.objects = []

    def draw_extra_objects(self, level_builder, screen, current_segment):
        level_builder.draw_objects(screen, self.objects, current_segment)

    def create_objects(self, evt, start=False):
        c = self.canvas
        e = c.editor
        if e is None:
            return
        index, x, y, pick = self.get_xy(evt)
        if start:
            self.mouse_down = x, y
        dx = x - self.mouse_down[0]
        dy = y - self.mouse_down[1]
        obj = self.drawing_object
        if obj.vertical_only:
            sx = 0
            sy = obj.default_dy if dy > 0 else -obj.default_dy
            num = max((dy + sy - 1) / sy, 1)
        elif obj.single:
            sx = obj.default_dx
            sy = 0
            num = 1
        else:
            if abs(dx) >= abs(dy):
                sx = obj.default_dx if dx > 0 else -obj.default_dx
                num = max((abs(dx) + abs(sx) - 1) / abs(sx), 1)
                sy = dy / num
            else:
                sy = obj.default_dy if dy > 0 else -obj.default_dy
                num = max((abs(dy) + abs(sy) - 1) / abs(sy), 1)
                sx = dx / num
        self.objects = [
            obj(-1, self.mouse_down[0], self.mouse_down[1], num, sx, sy),
        ]
        self.display_coords(evt)

    def process_left_down(self, evt):
        self.create_objects(evt, True)
        self.canvas.Refresh()
        self.display_coords(evt)

    def process_left_up(self, evt):
        # Record the command!
        self.objects = []
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        self.create_objects(evt)
        self.canvas.Refresh()
        self.display_coords(evt)

    def process_mouse_motion_up(self, evt):
        self.create_objects(evt, True)
        self.canvas.Refresh()
        self.display_coords(evt)

class DrawGirderMode(DrawMode):
    icon = "jumpman_girder.png"
    menu_item_name = "Draw Girder"
    menu_item_tooltip = "Draw girders"
    drawing_object = Girder

class DrawLadderMode(DrawMode):
    icon = "jumpman_ladder.png"
    menu_item_name = "Draw Ladder"
    menu_item_tooltip = "Draw ladders (vertical only)"
    drawing_object = Ladder

class DrawUpRopeMode(DrawMode):
    icon = "jumpman_uprope.png"
    menu_item_name = "Draw Up Rope"
    menu_item_tooltip = "Draw up ropes (vertical only)"
    drawing_object = UpRope

class DrawDownRopeMode(DrawMode):
    icon = "jumpman_downrope.png"
    menu_item_name = "Draw Down Rope"
    menu_item_tooltip = "Draw down ropes (vertical only)"
    drawing_object = DownRope

class DrawPeanutMode(DrawMode):
    icon = "jumpman_peanut.png"
    menu_item_name = "Draw Peanuts"
    menu_item_tooltip = "Draw peanuts (single only)"
    drawing_object = Peanut


class JumpmanLevelView(MainBitmapScroller):
    default_mouse_handler = JumpmanSelectMode

    def __init__(self, *args, **kwargs):
        MainBitmapScroller.__init__(self, *args, **kwargs)
        self.level_builder = None
        self.cached_screen = None
        self.last_commands = None

    def get_segment(self, editor):
        self.level_builder = JumpmanLevelBuilder(editor.document.user_segments)
        self.pick_buffer = editor.pick_buffer
        return editor.screen

    def clear_screen(self):
        self.segment[:] = 0
        self.pick_buffer[:] = -1

    def get_level_definition(self):
        source = self.editor.segment
        start = source.start_addr
        if len(source) < 0x38:
            return np.zeros([0], dtype=np.uint8), 0
        index = source[0x38]*256 + source[0x37]
        log.debug("level def table: %x" % index)
        if index > start:
            index -= start
        if index < len(source):
            commands = source[index:index + 500]  # arbitrary max number of bytes
        else:
            commands = source[index:index]
        return commands, index

    def compute_image(self):
        if self.level_builder is None:
            return
        commands, index = self.get_level_definition()
        if np.array_equal(commands, self.last_commands):
            self.segment[:] = self.cached_screen
        else:
            self.clear_screen()
            self.level_builder.parse_and_draw(self.segment, commands, current_segment=self.editor.segment, pick_buffer=self.pick_buffer)
            self.pick_buffer[self.pick_buffer >= 0] += index
            self.cached_screen = self.segment[:].copy()
            self.last_commands = commands[:]

    def get_image(self):
        self.compute_image()
        self.mouse_mode.draw_extra_objects(self.level_builder, self.segment, self.editor.segment)
        bitimage = MainBitmapScroller.get_image(self)
        self.mouse_mode.draw_overlay(bitimage)
        return bitimage


class JumpmanEditor(BitmapEditor):
    """ The toolkit specific implementation of a HexEditor.  See the
    IHexEditor interface for the API documentation.
    """
    ##### class attributes
    
    valid_mouse_modes = [AnticDSelectMode, PeanutCheckMode, DrawGirderMode, DrawLadderMode, DrawUpRopeMode, DrawDownRopeMode, DrawPeanutMode]
    
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
        self.level_data.recalc_view()
    
    def refresh_panes(self):
        self.hex_edit.refresh_view()
        p = self.get_level_colors()
        if p != self.machine.antic_color_registers:
            self.machine.update_colors(p)
        self.bitmap.refresh_view()
        self.level_data.refresh_view()
    
    def rebuild_document_properties(self):
        self.bitmap.set_mouse_mode(AnticDSelectMode)
    
    def copy_view_properties(self, old_editor):
        self.find_segment(segment=old_editor.segment)
    
    def view_segment_set_width(self, segment):
        self.bitmap_width = 40
        self.machine.update_colors(self.get_level_colors(segment))

    def get_level_colors(self, segment=None):
        if segment is None:
            segment = self.segment
        colors = segment[0x2a:0x33].copy()
        # on some levels, the bombs are set to color 0 because they are cycled
        # to produce a glowing effect, but that's not visible here so we force
        # it to be bright white
        fg = colors[4:8]
        fg[fg == 0] = 15
        return list(colors)
    
    def update_mouse_mode(self):
        self.bitmap.set_mouse_mode(self.mouse_mode)
        self.bitmap.refresh_view()
    
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
        # Don't use bitmap editor's paste, we want it to paste in hex
        return HexEditor.process_paste_data_object(self, data_obj, cmd_cls)
    
    def create_clipboard_data_object(self):
        # Don't use bitmap editor's clipboard, we want hex bytes
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

        self.antic_lines = 88
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
        self.level_data = self.window.get_dock_pane('jumpman.level_data').control

        # Load the editor's contents.
        self.load()

        return self.bitmap

    #### wx event handlers ####################################################
    
    def index_clicked(self, index, bit, control):
        self.cursor_index = index
        if control != self.hex_edit:
            self.hex_edit.select_index(index)
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
