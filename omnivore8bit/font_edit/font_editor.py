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
from omnivore8bit.hex_edit.hex_editor import HexEditor
from omnivore8bit.arch.machine import predefined
from omnivore8bit.ui.bitviewscroller import CharacterSetViewer
from omnivore.utils.command import Overlay
from omnivore8bit.utils.searchutil import HexSearcher, CharSearcher
from omnivore8bit.utils.drawutil import get_bounds
from omnivore.utils.sortutil import invert_rects
from omnivore8bit.hex_edit.commands import ChangeByteCommand, PasteCommand
from omnivore.framework.mouse_handler import MouseHandler, MouseControllerMixin
import omnivore.framework.actions as fa
import omnivore8bit.hex_edit.actions as ha

from commands import *


class MainCharacterSetViewer(MouseControllerMixin, CharacterSetViewer):
    """Subclass adapts the mouse interface to the MouseHandler class
    
    """

    def __init__(self, *args, **kwargs):
        CharacterSetViewer.__init__(self, *args, **kwargs)
        MouseControllerMixin.__init__(self, SelectMode)


class SelectMode(MouseHandler):
    icon = "select.png"
    menu_item_name = "Select"
    menu_item_tooltip = "Select regions"

    def display_coords(self, evt, extra=None):
        c = self.canvas
        e = c.editor
        if e is not None:
            index, bit, inside = c.event_coords_to_byte(evt)
            r0, c0 = c.index_to_row_col(index)
            msg = "x=$%x y=$%x index=$%x" % (c0, r0, index)
            if extra:
                msg += " " + extra
            e.show_status_message(msg)

    def process_left_down(self, evt):
        FontMapScroller.on_left_down(self.canvas, evt)  # can't use self.canvas directly because it has an overridded method on_left_down
        self.display_coords(evt)

    def process_left_up(self, evt):
        FontMapScroller.on_left_up(self.canvas, evt)  # can't use self.canvas directly because it has an overridded method on_left_down

    def process_mouse_motion_down(self, evt):
        self.canvas.handle_select_motion(self.canvas.editor, evt)
        self.display_coords(evt)

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
            extra = "rectangle: $%x x $%x" % (w, h)
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


class FontEditor(HexEditor):
    """ The toolkit specific implementation of a MapEditor.  See the
    IMapEditor interface for the API documentation.
    """
    ##### class attributes

    valid_mouse_modes = [SelectMode, PickTileMode, DrawMode, LineMode, SquareMode, FilledSquareMode]

    ##### traits

    imageable = True

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

    def from_metadata_dict(self, e):
        """ Set up any pre-calculated segments based on the type or content of
        the just-loaded document.
        """
        MapEditor.from_metadata_dict(self, e)
        if 'tile map' in e:
            self.antic_tile_map = e['tile map']
        # Force ANTIC font mapping if not present
        if 'font_mapping' not in e:
            self.machine.set_font_mapping(predefined['font_mapping'][1])

    def to_metadata_dict(self, mdict, document):
        mdict["map width"] = self.map_width
        mdict["map zoom"] = self.map_zoom
        mdict["tile map"] = self.antic_tile_map
        if document == self.document:
            # If we're saving the document currently displayed, save the
            # display parameters too.
            mdict["segment view params"] = dict(self.segment_view_params)  # shallow copy, but only need to get rid of Traits dict wrapper
        self.machine.serialize_extra_to_dict(mdict)

    @on_trait_change('machine.bitmap_shape_change_event,machine.bitmap_color_change_event')
    def update_bitmap(self):
        self.control.recalc_view()

    @on_trait_change('machine.font_change_event')
    def update_fonts(self):
        self.glyph_list.recalc_view()
        self.pixel_editor.recalc_view()

    @on_trait_change('machine.disassembler_change_event')
    def update_disassembler(self):
        pass  # no disassembler!

    def reconfigure_panes(self):
        self.control.recalc_view()
        self.pixel_editor.recalc_view()

    def refresh_panes(self):
        self.control.refresh_view()

    def rebuild_document_properties(self):
        self.find_segment("Playfield map")
        self.update_mouse_mode(SelectMode)

    def process_preference_change(self, prefs):
        # override MapEditor because those preferences don't apply here
        pass

    def set_map_width(self, width=None):
        if width is None:
            width = self.map_width
        self.map_width = width
        self.control.recalc_view()

    def view_segment_set_width(self, segment):
        self.map_width = segment.map_width

    def update_mouse_mode(self, mouse_handler=None):
        if mouse_handler is not None:
            self.mouse_mode_factory = mouse_handler
        self.control.set_mouse_mode(self.mouse_mode_factory)

    def set_current_draw_pattern(self, pattern, control=None):
        try:
            iter(pattern)
        except TypeError:
            self.draw_pattern = (pattern,)
        else:
            self.draw_pattern = tuple(pattern)
        self.pixel_editor.show_pattern(self.draw_pattern)
        self.character_set.show_pattern(self.draw_pattern)

    def mark_index_range_changed(self, index_range):
        pass

    def perform_idle(self):
        pass

    def get_selected_status_message(self):
        return ""

    def process_paste_data_object(self, data_obj, cmd_cls=None):
        bytes, extra = self.get_numpy_from_data_object(data_obj)
        ranges, indexes = self.get_selected_ranges_and_indexes()
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
            bpr = self.control.bytes_per_row
            last = r2 * bpr
            d = self.segment[:last].reshape(-1, bpr)
            data = d[r1:r2, c1:c2]
            data_obj = wx.CustomDataObject("numpy,columns")
            data_obj.SetData("%d,%d,%s" % (r2 - r1, c2 - c1, data.tostring()))
            return data_obj
        return None

    def highlight_selected_ranges(self):
        s = self.segment
        s.clear_style_bits(selected=True)
        s.set_style_ranges_rect(self.selected_ranges, self.control.bytes_per_row, selected=True)
        self.document.change_count += 1

    def invert_selection_ranges(self, ranges):
        rects = [(rect[2], rect[3]) for rect in [self.segment.get_rect_indexes(r[0], r[1], self.control.bytes_per_row) for r in ranges]]
        inverted = invert_rects(rects, self.control.total_rows, self.control.bytes_per_row)
        ranges = self.segment.rects_to_ranges(inverted, self.control.bytes_per_row)
        return ranges

    def get_extra_segment_savers(self, segment):
        return []

    def get_numpy_image(self):
        return self.glyph_list.get_full_image()

    def common_popup_actions(self):
        return [fa.CutAction, fa.CopyAction, fa.PasteAction, None, fa.SelectAllAction, fa.SelectNoneAction, None, ha.GetSegmentFromSelectionAction, ha.RevertToBaselineAction]

    ###########################################################################
    # Trait handlers.
    ###########################################################################

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        # Base-class constructor.
        self.control = self.glyph_list = MainCharacterSetViewer(parent, self.task)

        ##########################################
        # Events.
        ##########################################

        # Get related controls
        self.pixel_editor = self.window.get_dock_pane('font_edit.pixel_editor').control
        self.color_chooser = self.window.get_dock_pane('font_edit.color_chooser').control

        # segment list and undo history exclusively in sidebar
        self.segment_list = None
        self.undo_history = None
        self.sidebar = self.window.get_dock_pane('font_edit.sidebar')

        # Load the editor's contents.
        self.load()

        return self.control

    #### wx event handlers ####################################################

    def index_clicked(self, index, bit, from_control, refresh_from=True):
        self.cursor_index = index
        skip_control = None if refresh_from else from_control
        if skip_control != self.control:
            self.control.select_index(from_control, index)
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
