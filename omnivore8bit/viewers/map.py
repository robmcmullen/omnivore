# Standard library imports.
import sys
import os
import functools

# Major package imports.
import wx
import numpy as np

# Enthought library imports.
from traits.api import on_trait_change, Any, Bool, Int, Str, List, Event, Enum, Instance, File, Unicode, Property, provides, Undefined, CArray

# Local imports.
from omnivore8bit.ui.bitviewscroller import BitviewScroller, FontMapScroller
from omnivore.utils.command import Overlay
from omnivore8bit.utils.drawutil import get_bounds
from omnivore.utils.sortutil import invert_rects, rect_ranges_to_indexes
from ..byte_edit.commands import ChangeByteCommand, PasteCommand, PasteRectCommand
from omnivore.framework.mouse_handler import MouseHandler, MouseControllerMixin

from . import SegmentViewer
from .map_commands import *

import logging
log = logging.getLogger(__name__)


class MainFontMapScroller(MouseControllerMixin, FontMapScroller):
#class MainFontMapScroller(FontMapScroller):
    """Subclass adapts the mouse interface to the MouseHandler class
    
    """

    def __init__(self, parent, linked_base, width, *args, **kwargs):
        FontMapScroller.__init__(self, parent, linked_base, width, rect_select=True, *args, **kwargs)
        MouseControllerMixin.__init__(self, SelectMode)

    def update_bytes_per_row(self):
        BitviewScroller.update_bytes_per_row(self)
        # remove FontMapScroller call to find font width from machine


class SelectMode(MouseHandler):
    icon = "select.png"
    menu_item_name = "Select"
    menu_item_tooltip = "Select regions"

    def display_coords(self, evt, extra=None):
        log.debug("display_coords")
        c = self.control
        e = c.editor
        if e is not None:
            index, bit, inside = c.event_coords_to_byte(evt)
            r0, c0 = c.index_to_row_col(index)
            msg = "x=$%x y=$%x index=$%x" % (c0, r0, index)
            if extra:
                msg += " " + extra
            e.show_status_message(msg)

    def process_left_down(self, evt):
        FontMapScroller.on_left_down(self.control, evt)  # can't use self.control directly because it overrides on_left_down
        self.display_coords(evt)

    def process_left_up(self, evt):
        FontMapScroller.on_left_up(self.control, evt)  # can't use self.control directly because it overrides on_left_down

    def process_mouse_motion_down(self, evt):
        self.control.handle_select_motion(self.control.linked_base, evt)
        self.display_coords(evt)

    def process_mouse_motion_up(self, evt):
        self.display_coords(evt)

    def zoom_mouse_wheel(self, evt, amount):
        if amount < 0:
            self.control.zoom_out()
        elif amount > 0:
            self.control.zoom_in()

    def get_popup_actions(self, evt):
        return self.control.get_popup_actions()


class PickTileMode(SelectMode):
    icon = "eyedropper.png"
    menu_item_name = "Pick Tile"
    menu_item_tooltip = "Pick a tile from the map and use as the current draw tile"

    def init_post_hook(self):
        self.last_index = None

    def process_left_down(self, evt):
        c = self.control
        index, bit, inside = c.event_coords_to_byte(evt)
        if not inside:
            return
        v = c.segment_viewer
        e = v.linked_base
        value = e.segment[index]
        if self.last_index != index:
            e.set_cursor(index, False)
            v.set_draw_pattern(value)
            e.index_clicked(index, bit, None)
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
        c = self.control
        v = c.segment_viewer
        pattern = c.segment_viewer.draw_pattern
        if start:
            self.batch = DrawBatchCommand()
        byte, bit, inside = c.event_coords_to_byte(evt)
        if inside:
            v.linked_base.set_cursor(byte, False)
            index = v.linked_base.cursor_index
            cmd = ChangeByteCommand(e.segment, index, index+len(pattern), pattern, False, True)
            v.editor.process_command(cmd, self.batch)

    def process_left_down(self, evt):
        self.draw(evt, True)
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        self.draw(evt)
        self.display_coords(evt)

    def process_left_up(self, evt):
        c = self.control
        v = c.segment_viewer
        v.editor.end_batch()
        self.batch = None


class OverlayMode(SelectMode):
    command = None

    def get_display_rect(self, index):
        c = self.control
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
        c = self.control
        v = c.segment_viewer
        pattern = v.draw_pattern
        byte, bit, inside = c.event_coords_to_byte(evt)
        if inside:
            if start:
                self.batch = Overlay()
                self.start_index = byte
            v.linked_base.set_cursor(byte, False)
            index = byte
            cmd = self.command(v.segment, self.start_index, index, pattern, c.bytes_per_row)
            v.editor.process_command(cmd, self.batch)
            self.display_coords(evt, self.get_display_rect(index))

    def process_left_down(self, evt):
        self.draw(evt, True)

    def process_mouse_motion_down(self, evt):
        self.draw(evt)

    def process_left_up(self, evt):
        c = self.control
        v = c.segment_viewer
        v.editor.end_batch()
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


class MapViewer(SegmentViewer):
    name = "map"

    pretty_name = "Map"

    has_font = True

    valid_mouse_modes = [SelectMode, PickTileMode, DrawMode, LineMode, SquareMode, FilledSquareMode]

    mouse_mode_factory = SelectMode

    default_map_width = 16

    draw_pattern = CArray(dtype=np.uint8, value=(0,))

    @classmethod
    def create_control(cls, parent, linked_base):
        return MainFontMapScroller(parent, linked_base, cls.default_map_width, size=(500,500), command=ChangeByteCommand)

    ##### Range operations

    def _get_range_processor(self):  # Trait property getter
        return functools.partial(rect_ranges_to_indexes, self.control.bytes_per_row, 0)

    def get_optimized_selected_ranges(self, ranges):
        return ranges

    ##### SegmentViewer interface

    @property
    def window_title(self):
        return self.pretty_name + " " + self.machine.font_renderer.name + ", " + self.machine.font_mapping.name

    @on_trait_change('machine.font_change_event')
    def update_bitmap(self, evt):
        log.debug("MapViewer: machine font changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()

    def update_mouse_mode(self, mouse_handler=None):
        if mouse_handler is not None:
            self.mouse_mode_factory = mouse_handler
        log.debug("mouse mode: %s" % self.mouse_mode_factory)
        self.control.set_mouse_mode(self.mouse_mode_factory)

    @on_trait_change('linked_base.editor.task.segment_selected')
    def process_segment_selected(self, evt):
        log.debug("process_segment_selected for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.control.bytes_per_row = self.linked_base.segment.map_width
            self.update_mouse_mode(SelectMode)

    def set_width(self, width):
        # also update the segment map width when changed
        SegmentViewer.set_width(self, width)
        self.linked_base.segment.map_width = self.width

    ##### Selections

    def highlight_selected_ranges(self):
        s = self.linked_base.segment
        s.clear_style_bits(selected=True)
        s.set_style_ranges_rect(self.linked_base.selected_ranges, self.control.bytes_per_row, selected=True)

    ##### Clipboard & Copy/Paste

    @property
    def clipboard_data_format(self):
        return "numpy,columns"

    def get_paste_command(self, serialized_data):
        print(serialized_data)
        print(serialized_data.source_data_format_name)
        if serialized_data.source_data_format_name == "numpy,columns":
            return PasteRectCommand
        return PasteCommand

    ##### toolbar

    def update_toolbar(self):
        self.update_mouse_mode()

    ##### Drawing pattern

    def set_draw_pattern(self, value):
        log.debug("new draw pattern: %s" % str(value))
        self.draw_pattern = np.asarray(value, dtype=np.uint8)
