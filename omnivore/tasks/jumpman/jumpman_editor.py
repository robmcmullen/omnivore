# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np
from atrcopy import SegmentData, DefaultSegment, selected_bit_mask, comment_bit_mask

# Enthought library imports.
from traits.api import on_trait_change, Any, Bool, Int, Str, List, Event, Enum, Instance, File, Unicode, Property, provides
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore import get_image_path
from omnivore.tasks.hex_edit.hex_editor import HexEditor
from omnivore.tasks.bitmap_edit.bitmap_editor import MainBitmapScroller, SelectMode, BitmapEditor
from omnivore.framework.document import Document
from omnivore.arch.machine import Machine, predefined
from omnivore.arch.colors import powerup_colors
from omnivore.arch.antic_renderers import BaseRenderer
from omnivore.utils.wx.bitviewscroller import BitmapScroller
from omnivore.utils.command import Overlay
from omnivore.utils.searchutil import HexSearcher, CharSearcher
from omnivore.utils.drawutil import get_bounds
from omnivore.utils.sortutil import invert_rects
from omnivore.utils.jumpman import *
from omnivore.tasks.hex_edit.commands import ChangeByteCommand, SetValueCommand
from omnivore.framework.mouse_handler import MouseHandler

from commands import *

import logging
log = logging.getLogger(__name__)


class JumpmanSelectMode(SelectMode):
    def __init__(self, *args, **kwargs):
        SelectMode.__init__(self, *args, **kwargs)
        self.mouse_down = (0, 0)
        self.objects = []

    def cleanup(self):
        pass

    def get_image_override(self):
        """ Replace the entire bit image generation in JumpmanLevelView """
        return None

    def draw_extra_objects(self, lever_builder, screen, current_segment):
        return

    def draw_overlay(self, bitimage):
        return
    
    def get_xy(self, evt):
        c = self.canvas
        e = c.editor
        if e is not None:
            index, bit, inside = c.event_coords_to_byte(evt)
            y, x = c.byte_to_row_col(index)
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
    min_mouse_distance = 2

    def get_image_override(self):
        if not self.objects:
            return

        e = self.canvas.editor
        level_builder = self.canvas.level_builder
        playfield = e.get_playfield_segment()
        e.clear_playfield(playfield)
        level_builder.draw_objects(playfield, level_builder.objects, e.segment, highlight=self.objects)
        bitimage = self.canvas.get_rendered_image(playfield)
        return bitimage

    def highlight_pick(self, evt):
        index, x, y, pick = self.get_xy(evt)
        self.mouse_down = x, y
        if pick >= 0:
            obj = self.canvas.screen_state.get_picked(pick)
            if evt.ShiftDown():
                self.objects.append(obj)
            elif obj not in self.objects:
                self.objects = [obj]
            self.check_tolerance = True
        else:
            # don't kill multiple selection if user clicks on empty space by
            # mistake
            if not evt.ShiftDown():
                self.objects = []

    def move_pick(self, evt):
        if self.objects:
            index, x, y, pick = self.get_xy(evt)
            dx = x - self.mouse_down[0]
            dy = y - self.mouse_down[1]
            if self.check_tolerance and abs(dx) + abs(dy) <  self.min_mouse_distance:
                return
            self.check_tolerance = False
            for obj in self.objects:
                obj.x += dx
                obj.y += dy
            self.mouse_down = x, y

    def process_left_down(self, evt):
        self.highlight_pick(evt)
        self.canvas.Refresh()
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        self.move_pick(evt)
        self.canvas.Refresh()
        self.display_coords(evt)

    def process_left_up(self, evt):
        if self.objects and not self.check_tolerance:
            self.canvas.save_changes()
        self.display_coords(evt)

    def process_mouse_motion_up(self, evt):
        self.display_coords(evt)
    
    def delete_key_pressed(self):
        if self.objects:
            self.canvas.delete_objects(self.objects)
            self.objects = []
        self.canvas.Refresh()

    def backspace_key_pressed(self):
        self.delete_key_pressed()


class DrawMode(JumpmanSelectMode):
    icon = "select.png"
    menu_item_name = "Draw"
    menu_item_tooltip = "Draw stuff"
    drawing_object = Girder

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
            obj(-1, self.mouse_down[0] - obj.default_dx/2, self.mouse_down[1] - obj.default_dy/2, num, sx, sy),
        ]
        self.check_objects(x, y)

    def check_objects(self, x, y):
        pass

    def process_left_down(self, evt):
        self.create_objects(evt, True)
        self.canvas.Refresh()
        self.display_coords(evt)

    def process_left_up(self, evt):
        self.canvas.save_objects(self.objects)
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

    def __init__(self, *args, **kwargs):
        DrawMode.__init__(self, *args, **kwargs)
        self.is_bad_location = False
        self.batch = None

    def cleanup(self):
        self.canvas.editor.screen.style[:] = 0

    def get_cursor(self):
        if self.is_bad_location:
            return wx.StockCursor(wx.CURSOR_HAND)
        else:
            return wx.StockCursor(wx.CURSOR_ARROW)

    def get_harvest_offset(self):
        source = self.canvas.editor.segment
        if len(source) < 0x47:
            hx = hy = 0, 0
        else:
            hx = source[0x46]
            hy = source[0x47]
        return hx, hy

    def is_allergic(self, x, y):
        hx, hy = self.get_harvest_offset()
        hx = hx & 0x1f
        hy = (hy & 0x1f) / 2
        startx = (16 - hx) & 0x1f
        starty = (0 - hy) & 0xf
        x = x & 0x1f
        y = y & 0xf
        return (x >= startx and x < startx + 7) or (y >= starty and y < starty + 3)

    def check_objects(self, x, y):
        self.is_bad_location = self.is_allergic(x, y)

    def draw_extra_objects(self, level_builder, screen, current_segment):
        level_builder.draw_objects(screen, self.objects, current_segment)
        hx, hy = self.get_harvest_offset()
        w = 160
        h = 88
        
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
        s = screen.style.reshape((h, w))
        s[:] = 0
        for x in range(startx, startx + 7):
            x = x & 0x1f
            s[0:h:, x::32] = comment_bit_mask
        for y in range(starty, starty + 3):
            y = y & 0xf
            s[y:h:16,:] = comment_bit_mask

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

    def process_left_down(self, evt):
        self.create_objects(evt, True)
        if self.is_bad_location:
            self.change_harvest_offset(evt, True)
            self.objects = []
        else:
            self.canvas.Refresh()
        self.display_coords(evt)

    def process_left_up(self, evt):
        if self.batch is not None:
            c = self.canvas
            e = c.editor
            if e is None:
                return
            e.end_batch()
            self.batch = None

            # Force updating of the hex view
            e.document.change_count += 1
            e.refresh_panes()
        else:
            DrawMode.process_left_up(self, evt)
            return
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        if self.batch is not None:
            self.change_harvest_offset(evt)
        else:
            self.create_objects(evt)
            self.canvas.Refresh()
        self.display_coords(evt)

    def process_mouse_motion_up(self, evt):
        self.create_objects(evt, True)
        self.canvas.Refresh()
        self.display_coords(evt)


class JumpmanLevelView(MainBitmapScroller):
    default_mouse_handler = JumpmanSelectMode

    def __init__(self, *args, **kwargs):
        MainBitmapScroller.__init__(self, *args, **kwargs)
        self.level_builder = None
        self.cached_screen = None
        self.last_commands = None
        self.screen_state = None

    def set_mouse_mode(self, handler):
        if hasattr(self, 'mouse_mode'):
            self.mouse_mode.cleanup()
        self.release_mouse()
        self.mouse_mode = handler(self)

    def get_segment(self, editor):
        self.level_builder = JumpmanLevelBuilder(editor.document.user_segments)
        self.pick_buffer = editor.pick_buffer
        self.last_commands = None
        return editor.screen

    def clear_screen(self):
        self.editor.clear_playfield()
        self.pick_buffer[:] = -1

    def get_level_addrs(self):
        if not self.editor.valid_jumpman_segment:
            raise IndexError
        source = self.editor.segment
        start = source.start_addr
        level_addr = source[0x37] + source[0x38]*256
        harvest_addr = source[0x4e] + source[0x4f]*256
        log.debug("level def table: %x, harvest table: %x" % (level_addr, harvest_addr))
        last = source.start_addr + len(source)
        if level_addr > start and harvest_addr > start and level_addr < last and harvest_addr < last:
            return source, level_addr, harvest_addr
        raise IndexError

    def compute_image(self):
        if self.level_builder is None:
            return
        source, level_addr, harvest_addr = self.get_level_addrs()
        index = level_addr - source.start_addr
        command_checksum = source[index:index + 512]  # representative sample
        if np.array_equal(command_checksum, self.last_commands):
            self.segment[:] = self.cached_screen
        else:
            self.clear_screen()
            self.screen_state = self.level_builder.parse_and_draw(self.segment, source, level_addr, harvest_addr, pick_buffer=self.pick_buffer)
            self.cached_screen = self.segment[:].copy()
            self.last_commands = command_checksum.copy()

    def bad_image(self):
        self.segment[:] = 0
        self.last_commands = None
        s = self.segment.style.reshape((self.editor.antic_lines, -1))
        s[::2,::2] = comment_bit_mask
        s[1::2,1::2] = comment_bit_mask

    def get_rendered_image(self, segment=None):
        return MainBitmapScroller.get_image(self, segment)

    def get_image(self):
        if self.editor.valid_jumpman_segment:
            override = self.mouse_mode.get_image_override()
            if override is not None:
                return override
        try:
            self.compute_image()
        except IndexError:
            self.bad_image()
            bitimage = MainBitmapScroller.get_image(self)
            return bitimage
        self.mouse_mode.draw_extra_objects(self.level_builder, self.segment, self.editor.segment)
        bitimage = MainBitmapScroller.get_image(self)
        self.mouse_mode.draw_overlay(bitimage)
        return bitimage

    def delete_objects(self, objects):
        self.level_builder.delete_objects(objects)
        self.save_changes()

    def save_objects(self, objects):
        self.level_builder.add_objects(objects)
        self.save_changes()

    def save_changes(self):
        source, level_addr, old_harvest_addr = self.get_level_addrs()
        level_data, harvest_addr, ropeladder_data = self.level_builder.create_level_definition(level_addr, source[0x46], source[0x47])
        index = level_addr - source.start_addr
        ranges = [(0x18,0x2a), (0x4e,0x50), (index,index + len(level_data))]
        hdata = np.empty([2], dtype=np.uint8)
        hdata.view(dtype="<u2")[0] = harvest_addr
        data = np.hstack([ropeladder_data, hdata, level_data])
        cmd = SetValueCommand(source, ranges, data)
        self.editor.process_command(cmd)


class JumpmanPlayfieldRenderer(BaseRenderer):
    """ Custom renderer instead of Antic Mode D renderer. Need to display
    highlighting on a per-pixel level which isn't possible with the Mode D
    renderer because the styling info is applied at the byte level and there
    are 4 pixels per byte in Mode D.

    So this renderer is one byte per pixel, but only uses the first 16 colors.
    It is mapped to the ANTIC color register order, so the first 4 colors are
    player colors, then the 5 playfield colors. A blank screen corresponds to
    the index value of 8, so the last playfield color.
    """
    name = "Jumpman 1 Byte Per Pixel"
    pixels_per_byte = 1
    bitplanes = 1

    def get_image(self, m, bytes_per_row, nr, count, bytes, style):
        normal = style == 0
        highlight = (style & selected_bit_mask) == selected_bit_mask
        comment = (style & comment_bit_mask) == comment_bit_mask
        
        color_registers, h_colors, m_colors, c_colors, d_colors = self.get_colors(m, range(16))
        bitimage = np.empty((nr * bytes_per_row, 3), dtype=np.uint8)
        for i in range(16):
            color_is_set = (bytes == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:] = m.empty_color
        return bitimage.reshape((nr, bytes_per_row, 3))


class JumpmanEditor(BitmapEditor):
    """ The toolkit specific implementation of a HexEditor.  See the
    IHexEditor interface for the API documentation.
    """
    valid_jumpman_segment = Bool

    ##### class attributes
    
    valid_mouse_modes = [AnticDSelectMode, DrawGirderMode, DrawLadderMode, DrawUpRopeMode, DrawDownRopeMode, DrawPeanutMode]
    
    ##### Default traits
    
    def _machine_default(self):
        return Machine(name="Jumpman", bitmap_renderer=JumpmanPlayfieldRenderer())

    def _map_width_default(self):
        return 40 * 4
    
    def _draw_pattern_default(self):
        return [0]
    
    def _valid_jumpman_segment_default(self):
        return False

    def _mouse_mode_default(self):
        return AnticDSelectMode

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

    def check_valid_segment(self, segment):
        # 283f is always 4c (JMP) because it and the next two bytes are a jump target from the game loop
        # 2848: always 20 (i.e. JSR)
        # 284b: always 60 (i.e. RTS)
        # 284c: always FF (target for harvest table if no action to be taken)
        if len(segment) >= 0x800 and segment[0x3f] == 0x4c and segment[0x48] == 0x20 and segment[0x4b] == 0x60 and segment[0x4c] == 0xff:
            # check for sane level definition table
            index = segment[0x38]*256 + segment[0x37] - segment.start_addr
            return index >=0 and index < len(segment)
        return False

    def find_first_valid_segment_index(self):
        # Find list of matches meeting minimum criteria
        possible = []
        for i, segment in enumerate(self.document.segments):
            if self.check_valid_segment(segment):
                possible.append(i)
                if len(segment) == 0x800:
                    return i
        if possible:
            return possible[0]
        return 0
    
    def init_view_properties(self):
        self.find_segment()

    def copy_view_properties(self, old_editor):
        segment = old_editor.segment
        if self.check_valid_segment(segment):
            if len(segment) != 0x800:
                segment = None
        self.find_segment(segment=segment)
    
    def view_segment_set_width(self, segment):
        self.valid_jumpman_segment = self.check_valid_segment(segment)
        self.bitmap_width = 40 * 4
        self.machine.update_colors(self.get_level_colors(segment))
        self.bitmap.set_mouse_mode(self.mouse_mode)

    def get_level_colors(self, segment=None):
        if segment is None:
            segment = self.segment
        if self.check_valid_segment(segment):
            colors = segment[0x2a:0x33].copy()
            # on some levels, the bombs are set to color 0 because they are
            # cycled to produce a glowing effect, but that's not visible here
            # so we force it to be bright white
            fg = colors[4:8]
            fg[fg == 0] = 15
        else:
            colors = powerup_colors()
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

    def get_playfield(self):
        data = np.empty(40 * 4 * self.antic_lines, dtype=np.uint8)
        return data

    def get_playfield_segment(self, playfield=None):
        if playfield is None:
            playfield = self.get_playfield()
        r = SegmentData(playfield)
        return DefaultSegment(r, 0x7000)

    def clear_playfield(self, playfield=None):
        if playfield is None:
            playfield = self.screen
        playfield[:] = 8  # background is the 9th ANTIC color register
        playfield.style[:] = 0
    
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
        self.screen = self.get_playfield_segment()
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
