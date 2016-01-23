# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np

# Enthought library imports.
from traits.api import Any, Bool, Int, Str, List, Event, Enum, Instance, File, Unicode, Property, provides
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore import get_image_path
from omnivore.tasks.hex_edit.hex_editor import HexEditor
from omnivore.framework.document import Document
from omnivore.utils.wx.bitviewscroller import FontMapScroller
from omnivore.utils.binutil import ATRSegmentParser, XexSegmentParser
from omnivore.utils.command import Overlay
from omnivore.utils.searchutil import HexSearcher, CharSearcher
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

    def process_left_down(self, evt):
        self.canvas.set_cursor_pos_from_event(evt)

    def process_mouse_motion_down(self, evt):
        self.canvas.set_selection_from_event(evt)
    
    def zoom_mouse_wheel(self, evt, amount):
        if amount < 0:
            self.canvas.zoom_out()
        elif amount > 0:
            self.canvas.zoom_in()


class PickTileMode(SelectMode):
    icon = "eyedropper.png"
    menu_item_name = "Pick Tile"
    menu_item_tooltip = "Pick a tile from the map and use as the current draw tile"
    
    def init_post_hook(self):
        self.last_index = None

    def process_left_down(self, evt):
        c = self.canvas
        index, bit, inside = c.event_coords_to_byte(evt)
        e = c.editor
        value = e.segment[index]
        if self.last_index != index:
            e.set_cursor(index, False)
            e.character_set.set_selected_char(value)
            e.index_clicked(index, bit, None)
            e.character_set.Refresh()
        self.last_index = index

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

    def process_mouse_motion_down(self, evt):
        self.draw(evt)

    def process_left_up(self, evt):
        c = self.canvas
        e = c.editor
        if e is None:
            return
        e.end_batch()
        self.batch = None


class OverlayMode(SelectMode):
    command = None

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
    
    def _antic_font_mapping_default(self):
        return 0  # Internal
    
    def _map_width_default(self):
        return 32

    ###########################################################################
    # 'FrameworkEditor' interface.
    ###########################################################################

    def init_extra_metadata(self, doc):
        """ Set up any pre-calculated segments based on the type or content of
        the just-loaded document.
        """
        HexEditor.init_extra_metadata(self, doc)
        e = doc.extra_metadata
        if 'tile map' in e:
            self.antic_tile_map = e['tile map']

    def update_fonts(self):
        self.font_map.Refresh()
        self.tile_map.Refresh()
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
        self.control.set_mouse_mode(SelectMode)
    
    def view_segment_set_width(self, segment):
        self.map_width = segment.map_width
    
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
    
    def process_paste_data_object(self, data_obj):
        bytes, extra = self.get_numpy_from_data_object(data_obj)
        print extra
        if extra is None:
            cmd = PasteCommand(self.segment, self.anchor_start_index, self.anchor_end_index, bytes)
        else:
            r, c = extra
            cmd = PasteRectangularCommand(self.segment, self.anchor_start_index, r, c, self.control.bytes_per_row, bytes)
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
    
    ###########################################################################
    # Trait handlers.
    ###########################################################################


    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        # Base-class constructor.
        self.control = self.font_map = MainFontMapScroller(parent, self.task, self.map_width, self.antic_font_mapping, ChangeByteCommand)
        self.antic_font = self.get_antic_font()

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
        if control != self.control:
            self.control.select_index(index)
        if control != self.memory_map:
            self.memory_map.select_index(index)
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
