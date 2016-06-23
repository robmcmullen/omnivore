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
from omnivore.framework.document import Document
from omnivore.arch.machine import predefined
from omnivore.utils.wx.bitviewscroller import FontMapScroller
from omnivore.utils.command import Overlay
from omnivore.utils.searchutil import HexSearcher, CharSearcher
from omnivore.utils.drawutil import get_bounds
from omnivore.utils.sortutil import invert_rects
from omnivore.tasks.hex_edit.commands import ChangeByteCommand, PasteCommand
from omnivore.framework.mouse_handler import MouseHandler

from commands import *


class MainFontMapScroller(FontMapScroller):
    """Subclass adapts the mouse interface to the MouseHandler class
    
    """
    def __init__(self, *args, **kwargs):
        FontMapScroller.__init__(self, *args, **kwargs)

        p = get_image_path("icons/hand.ico")
        self.hand_cursor = wx.Cursor(p, wx.BITMAP_TYPE_ICO, 16, 16)
        p = get_image_path("icons/hand_closed.ico")
        self.hand_closed_cursor = wx.Cursor(p, wx.BITMAP_TYPE_ICO, 16, 16)
        self.forced_cursor = None
        self.set_mouse_mode(MouseHandler)  # dummy initial mouse handler
        self.default_pan_mode = SelectMode(self)
        self.batch = None

    def set_mouse_mode(self, handler):
        self.release_mouse()
        self.mouse_mode = handler(self)
    
    def set_cursor(self, mode=None):
        if (self.forced_cursor is not None):
            self.SetCursor(self.forced_cursor)
            #
            return

        if mode is None:
            mode = self.mouse_mode
        c = mode.get_cursor()
        self.SetCursor(c)

    def get_effective_tool_mode(self, event):
        middle_down = False
        alt_down = False
        if (event is not None):
            try:
                alt_down = event.AltDown()
                # print self.is_alt_key_down
            except:
                pass
            try:
                middle_down = event.MiddleIsDown()
            except:
                pass
        if alt_down or middle_down:
            mode = self.default_pan_mode
        else:
            mode = self.mouse_mode
        return mode

    def release_mouse(self):
        self.mouse_is_down = False
        self.selection_box_is_being_defined = False
        while self.HasCapture():
            self.ReleaseMouse()

    def on_left_down(self, evt):
        # self.SetFocus() # why would it not be focused?
        mode = self.get_effective_tool_mode(evt)
        self.forced_cursor = None
        self.selection_box_is_being_defined = False
        self.mouse_down_position = evt.GetPosition()
        self.mouse_move_position = self.mouse_down_position

        mode.process_left_down(evt)
        self.set_cursor(mode)

    def on_motion(self, evt):
        mode = self.get_effective_tool_mode(evt)
        if evt.LeftIsDown():
            mode.process_mouse_motion_down(evt)
        else:
            mode.process_mouse_motion_up(evt)
        self.set_cursor(mode)

    def on_left_up(self, evt):
        mode = self.get_effective_tool_mode(evt)
        self.forced_cursor = None
        mode.process_left_up(evt)
        self.set_cursor(mode)

    def on_left_dclick(self, evt):
        # self.SetFocus() # why would it not be focused?
        mode = self.get_effective_tool_mode(evt)
        mode.process_left_dclick(evt)
        self.set_cursor(mode)

    def on_popup(self, evt):
        mode = self.get_effective_tool_mode(evt)
        self.forced_cursor = None
        mode.process_popup(evt)
        self.set_cursor(mode)

    def on_mouse_wheel(self, evt):
        mode = self.get_effective_tool_mode(evt)
        mode.process_mouse_wheel(evt)
        self.set_cursor(mode)

    def on_mouse_enter(self, evt):
        self.set_cursor()

    def on_mouse_leave(self, evt):
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        self.mouse_mode.process_mouse_leave(evt)

    def on_key_char(self, evt):
        mode = self.get_effective_tool_mode(evt)
        self.set_cursor(mode)
        
        mode.process_key_char(evt)
    
    def on_focus(self, evt):
        mode = self.get_effective_tool_mode(evt)
        mode.process_focus(evt)
    
    def on_focus_lost(self, evt):
        mode = self.get_effective_tool_mode(evt)
        mode.process_focus_lost(evt)


class SelectMode(MouseHandler):
    icon = "select.png"
    menu_item_name = "Select"
    menu_item_tooltip = "Select regions"
    
    def display_coords(self, evt, extra=None):
        c = self.canvas
        e = c.editor
        if e is not None:
            index, bit, inside = c.event_coords_to_byte(evt)
            r0, c0 = c.byte_to_row_col(index)
            msg = "row=%d (0x%x) col=%d (0x%x) index=%d (0x%x)" % (r0, r0, c0, c0, index, index)
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

    def process_left_down(self, evt):
        FontMapScroller.on_left_down(self.canvas, evt)  # can't use self.canvas directly because it has an overridded method on_left_down
        self.display_coords(evt)

    def process_left_up(self, evt):
        FontMapScroller.on_left_up(self.canvas, evt)  # can't use self.canvas directly because it has an overridded method on_left_down

    def process_mouse_motion_down(self, evt):
        self.canvas.set_selection_from_event(evt)
        self.display_coords(evt, self.get_display_rect())

    def process_mouse_motion_up(self, evt):
        self.display_coords(evt)
    
    def zoom_mouse_wheel(self, evt, amount):
        if amount < 0:
            self.canvas.zoom_out()
        elif amount > 0:
            self.canvas.zoom_in()
    
    def get_popup_actions(self, evt):
        return self.canvas.get_popup_actions()


class PickTileMode(SelectMode):
    icon = "eyedropper.png"
    menu_item_name = "Pick Tile"
    menu_item_tooltip = "Pick a tile from the map and use as the current draw tile"
    
    def init_post_hook(self):
        self.last_index = None

    def process_left_down(self, evt):
        c = self.canvas
        index, bit, inside = c.event_coords_to_byte(evt)
        if not inside:
            return
        e = c.editor
        value = e.segment[index]
        if self.last_index != index:
            e.set_cursor(index, False)
            e.character_set.set_selected_char(value)
            e.index_clicked(index, bit, None)
            e.character_set.Refresh()
        self.last_index = index
        self.display_coords(evt, "tile=%d" % value)

    def process_mouse_motion_down(self, evt):
        self.process_left_down(evt)

    def process_left_up(self, evt):
        self.last_index = None


class DrawMode(SelectMode):
    icon = "shape_freehand.png"
    menu_item_name = "Draw"
    menu_item_tooltip = "Draw with current tile"

    def draw(self, evt, start=False):
        c = self.canvas
        e = c.editor
        if e is None:
            return
        bytes = e.draw_pattern
        if not bytes:
            return
        if start:
            self.batch = DrawBatchCommand()
        byte, bit, inside = c.event_coords_to_byte(evt)
        if inside:
            e.set_cursor(byte, False)
            index = e.cursor_index
            cmd = ChangeByteCommand(e.segment, index, index+len(bytes), bytes, False, True)
            e.process_command(cmd, self.batch)

    def process_left_down(self, evt):
        self.draw(evt, True)
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        self.draw(evt)
        self.display_coords(evt)

    def process_left_up(self, evt):
        c = self.canvas
        e = c.editor
        if e is None:
            return
        e.end_batch()
        self.batch = None


class OverlayMode(SelectMode):
    command = None
    
    def get_display_rect(self, index):
        c = self.canvas
        i1 = self.start_index
        i2 = index
        if i2 < i1:
            i1, i2 = i2, i1
        (x1, y1), (x2, y2) = get_bounds(i1, i2, c.bytes_per_row)
        extra = None
        w = x2 - x1 + 1
        h = y2 - y1 + 1
        if w > 0 or h > 0:
            extra = "rectangle: width=%d (0x%x), height=%d (0x%x)" % (w, w, h, h)
        return extra
    
    def draw(self, evt, start=False):
        c = self.canvas
        e = c.editor
        if e is None:
            return
        bytes = e.draw_pattern
        if not bytes:
            return
        byte, bit, inside = c.event_coords_to_byte(evt)
        if inside:
            if start:
                self.batch = Overlay()
                self.start_index = byte
            e.set_cursor(byte, False)
            index = byte
            cmd = self.command(e.segment, self.start_index, index, bytes)
            e.process_command(cmd, self.batch)
            self.display_coords(evt, self.get_display_rect(index))

    def process_left_down(self, evt):
        self.draw(evt, True)

    def process_mouse_motion_down(self, evt):
        self.draw(evt)

    def process_left_up(self, evt):
        c = self.canvas
        e = c.editor
        if e is None:
            return
        e.end_batch()
        self.batch = None

class LineMode(OverlayMode):
    icon = "shape_line.png"
    menu_item_name = "Line"
    menu_item_tooltip = "Draw line with current tile"
    command = LineCommand

class SquareMode(OverlayMode):
    icon = "shape_hollow_square.png"
    menu_item_name = "Square"
    menu_item_tooltip = "Draw square with current tile"
    command = SquareCommand

class FilledSquareMode(OverlayMode):
    icon = "shape_filled_square.png"
    menu_item_name = "Filled Square"
    menu_item_tooltip = "Draw filled square with current tile"
    command = FilledSquareCommand


class MapEditor(HexEditor):
    """ The toolkit specific implementation of a HexEditor.  See the
    IHexEditor interface for the API documentation.
    """
    ##### class attributes
    
    valid_mouse_modes = [SelectMode, PickTileMode, DrawMode, LineMode, SquareMode, FilledSquareMode]
    
    ##### traits
    
    antic_tile_map = Any
    
    draw_pattern = Any(None)
    
    # Class attributes (not traits)
    
    rect_select = True
    
    searchers = [HexSearcher, CharSearcher]
    
    ##### Default traits
    
    def _antic_tile_map_default(self):
        return []
    
    def _map_width_default(self):
        return 32
    
    def _draw_pattern_default(self):
        return [0]

    ###########################################################################
    # 'FrameworkEditor' interface.
    ###########################################################################

    def process_extra_metadata(self, doc, e):
        """ Set up any pre-calculated segments based on the type or content of
        the just-loaded document.
        """
        HexEditor.process_extra_metadata(self, doc, e)
        if 'tile map' in e:
            self.antic_tile_map = e['tile map']
        self.machine.set_font_mapping(predefined['font_mapping'][1])
    
    @on_trait_change('machine.bitmap_shape_change_event,machine.bitmap_color_change_event')
    def update_bitmap(self):
        self.control.recalc_view()
    
    @on_trait_change('machine.font_change_event')
    def update_fonts(self):
        self.font_map.set_font()
        self.font_map.Refresh()
        self.tile_map.recalc_view()
        self.character_set.set_font()
        self.character_set.Refresh()
    
    def reconfigure_panes(self):
        self.control.recalc_view()
        self.memory_map.recalc_view()
        self.tile_map.recalc_view()
        self.character_set.recalc_view()
    
    def refresh_panes(self):
        self.control.refresh_view()
        self.memory_map.refresh_view()
    
    def rebuild_document_properties(self):
        self.find_segment("Playfield map")
        self.update_mouse_mode(SelectMode)
    
    def view_segment_set_width(self, segment):
        self.map_width = segment.map_width
    
    def update_mouse_mode(self, mouse_handler=None):
        if mouse_handler is not None:
            self.mouse_mode_factory = mouse_handler
        self.control.set_mouse_mode(self.mouse_mode_factory)
    
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
        self.control = self.font_map = MainFontMapScroller(parent, self.task, self.map_width, ChangeByteCommand)

        ##########################################
        # Events.
        ##########################################

        # Get related controls
        self.memory_map = self.window.get_dock_pane('map_edit.memory_map').control
        self.tile_map = self.window.get_dock_pane('map_edit.tile_map').control
        self.character_set = self.window.get_dock_pane('map_edit.character_set').control
        self.segment_list = self.window.get_dock_pane('map_edit.segments').control
        self.undo_history = self.window.get_dock_pane('map_edit.undo').control

        # Load the editor's contents.
        self.load()

        return self.control

    #### wx event handlers ####################################################
    
    def index_clicked(self, index, bit, control):
        self.cursor_index = index
        if control != self.control:
            self.control.select_index(index)
        if control != self.memory_map:
            self.memory_map.select_index(index)
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
