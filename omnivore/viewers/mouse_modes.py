# Standard library imports.
import sys
import os
import functools

# Major package imports.
import wx
import numpy as np

# Local imports.
from sawx.utils.command import Overlay
from ..utils.drawutil import get_bounds
from ..clipboard_commands import PasteCommand, PasteRectCommand
from sawx.ui.compactgrid import MouseMode, NormalSelectMode, RectangularSelectMode

from .map_commands import *

import logging
log = logging.getLogger(__name__)


class EyedropperMode(RectangularSelectMode):
    icon = "eyedropper.png"
    menu_item_name = "Pick Item"
    menu_item_tooltip = "Pick an item from the grid and use as the current draw item"

    def process_left_down(self, evt):
        log.debug("EyedropperMode: process_left_down")
        cg = self.control
        input_row, input_cell = cg.main.get_row_cell_from_event(evt)
        if (input_row, input_cell) == self.last_mouse_event:
            # only process if mouse has moved to a new cell; no sub-cell
            # events!
            return
        self.last_mouse_event = (input_row, input_cell)
        row, col, _ = cg.get_row_col_from_event(evt)
        index, _ = cg.table.get_index_range(row, col)
        value = cg.segment_viewer.segment[index]
        cg.segment_viewer.set_draw_pattern(value)
        log.debug("draw_pattern=%x at index=%d %d,%d" % (value, index, row, col))
        # self.display_coords(evt, "tile=%d" % value)

    def process_mouse_motion_down(self, evt):
        self.process_left_down(evt)

    def process_left_up(self, evt):
        self.last_mouse_event = None, None


class DrawMode(RectangularSelectMode):
    icon = "shape_freehand.png"
    menu_item_name = "Draw"
    menu_item_tooltip = "Draw with current tile"

    def draw(self, evt, start=False):
        cg = self.control
        v = cg.segment_viewer
        pattern = cg.segment_viewer.draw_pattern
        print(("drawing with!", pattern, type(pattern)))
        if start:
            self.batch = DrawBatchCommand()
        row, col, _ = cg.get_row_col_from_event(evt)
        if cg.main.is_inside(row, col):
            index, _ = cg.table.get_index_range(row, col)
            cmd = ChangeByteCommand(v.segment, index, index+len(pattern), pattern, False, True)
            v.editor.process_command(cmd, self.batch)

    def process_left_down(self, evt):
        self.draw(evt, True)
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        self.draw(evt)
        self.display_coords(evt)

    def process_left_up(self, evt):
        cg = self.control
        v = cg.segment_viewer
        v.editor.end_batch()
        self.batch = None


class OverlayMode(RectangularSelectMode):
    command = None

    def get_display_rect(self, index):
        cg = self.control
        i1 = self.start_index
        i2 = index
        if i2 < i1:
            i1, i2 = i2, i1
        (x1, y1), (x2, y2) = get_bounds(i1, i2, cg.table.items_per_row)
        extra = None
        w = x2 - x1 + 1
        h = y2 - y1 + 1
        if w > 0 or h > 0:
            extra = "rectangle: $%x x $%x" % (w, h)
        return extra

    def draw(self, evt, start=False):
        cg = self.control
        v = cg.segment_viewer
        pattern = v.draw_pattern
        row, col, _ = cg.get_row_col_from_event(evt)
        if cg.main.is_inside(row, col):
            index, _ = cg.table.get_index_range(row, col)
            if start:
                self.batch = Overlay()
                self.start_index = index
            #v.linked_base.set_caret(byte, False)
            #index = byte
            cmd = self.command(v.segment, self.start_index, index, pattern, cg.table.items_per_row)
            v.editor.process_command(cmd, self.batch)
            self.display_coords(evt, self.get_display_rect(index))

    def process_left_down(self, evt):
        self.draw(evt, True)

    def process_mouse_motion_down(self, evt):
        self.draw(evt)

    def process_left_up(self, evt):
        cg = self.control
        v = cg.segment_viewer
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
