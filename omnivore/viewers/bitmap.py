import os
import sys

import wx

from sawx.utils.nputil import intscale
from sawx.ui import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentTable
from ..arch.bitmap_renderers import valid_bitmap_renderers

from .antic import AnticColorViewer

import logging
log = logging.getLogger(__name__)


class BitmapImageCache(cg.DrawTextImageCache):
    def draw_item(self, grid_control, dc, rect, data, style):
        start = 0
        end = len(data)
        nr = 1
        array = grid_control.bitmap_renderer.get_image(grid_control.segment_viewer, end, nr, end, data, style)
        width = array.shape[1]
        height = array.shape[0]
        if width > 0 and height > 0:
            array = intscale(array, grid_control.zoom_h * grid_control.scale_height, grid_control.zoom_w * grid_control.scale_width)
            #print("bitmap: %d,%d,3 after scaling: %s" % (height, width, str(array.shape)))
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tobytes())
            bmp = wx.Bitmap(image)
            dc.DrawBitmap(bmp, rect.x, rect.y)


class BitmapLineRenderer(cg.TableLineRenderer):
    default_image_cache = BitmapImageCache

    def __init__(self, grid_control, image_cache=None):
        image_cache = BitmapImageCache()
        w, h = self.calc_cell_size_in_pixels(grid_control)
        cg.LineRenderer.__init__(self, grid_control, w, h, grid_control.items_per_row, image_cache)

    def calc_cell_size_in_pixels(self, grid_control):
        w = grid_control.zoom_w * grid_control.scale_width * grid_control.pixels_per_byte
        h = grid_control.zoom_h * grid_control.scale_height
        return w, h

    # BaseLineRenderer interface

    def draw_line(self, grid_control, dc, line_num, col, index, last_index):
        t = grid_control.table
        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(grid_control, dc, rect, data, style)

    # fast BaseLineRenderer interface drawing entire grid at once

    def calc_bytes_per_row(self, table):
        return table.items_per_row

    def draw_grid(self, grid_control, dc, first_row, visible_rows, first_cell, visible_cells):
        t = grid_control.table
        log.debug(f"draw_grid: first_row={first_row} visible_rows={visible_rows}; first_cell={first_cell} visible_cells={visible_cells}")
        first_col = self.cell_to_col(first_row, first_cell)
        last_cell = min(first_cell + visible_cells, self.num_cells)
        last_row = min(first_row + visible_rows, t.num_rows)
        last_col = self.cell_to_col(last_row, last_cell - 1) + 1
        log.debug("draw_grid: rows:%d,%d (vis %d, num %d) cols:%d,%d" % (first_row, last_row, visible_rows, t.num_rows, first_col, last_col))

        ul_rect = self.col_to_rect(first_row, first_col)
        lr_rect = self.col_to_rect(last_row - 1, last_col - 1)
        frame_rect = wx.Rect(ul_rect.x, ul_rect.y, lr_rect.x - ul_rect.x + lr_rect.width, lr_rect.y - ul_rect.y + lr_rect.height)
        dc.SetClippingRegion(frame_rect)

        # First and last rows may not span entire width. Process those
        # separately
        #
        # First row may not have bytes at the beginning of the row if the start
        # offset is not zero
        if first_row == 0:
            try:
                col, index, last_index = self.calc_column_range(grid_control, first_row, first_col, last_col)
            except IndexError:
                pass  # skip lines with no visible cells
            else:
                self.draw_line(grid_control, dc, first_row, col, index, last_index)
            first_row += 1
            if first_row == last_row:
                return
            frame_rect.y += ul_rect.height

        # Last row may not have bytes at the end of the row
        if last_row == t.num_rows:
            try:
                col, index, last_index = self.calc_column_range(grid_control, last_row - 1, first_col, last_col)
            except IndexError:
                pass  # skip lines with no visible cells
            else:
                self.draw_line(grid_control, dc, last_row - 1, col, index, last_index)
            last_row -= 1

        # If there are any more rows to display, they will be full-width rows;
        # i.e. the data is in a rectangular grid
        nr = last_row - first_row
        if nr > 0:
            bytes_per_row = self.calc_bytes_per_row(t)
            nc = last_col - first_col
            offset = t.start_offset % bytes_per_row
            first_index = (first_row * bytes_per_row) - offset
            last_index = (last_row * bytes_per_row) - offset
            log.debug(f"drawing rectangular grid: bpr={bytes_per_row}, first,last={first_index},{last_index}, nr={nr}, start_offset={offset}")
            data = t.data[first_index:last_index].reshape((nr, bytes_per_row))[0:nr,first_col:last_col].flatten()
            style = t.style[first_index:last_index].reshape((nr, bytes_per_row))[0:nr,first_col:last_col].flatten()

            # get_image(cls, machine, antic_font, byte_values, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols):

            array = grid_control.bitmap_renderer.get_image(grid_control.segment_viewer, nc, nr, nc * nr, data, style)
            width = array.shape[1]
            height = array.shape[0]
            if width > 0 and height > 0:
                array = intscale(array, grid_control.zoom_h, grid_control.zoom_w)
                #print("bitmap: %d,%d,3 after scaling: %s" % (height, width, str(array.shape)))
                image = wx.Image(array.shape[1], array.shape[0])
                image.SetData(array.tobytes())
                bmp = wx.Bitmap(image)
                dc.DrawBitmap(bmp, frame_rect.x, frame_rect.y)


class BitmapGridControl(SegmentGridControl):
    def set_viewer_defaults(self):
        self.items_per_row = self.view_params.bitmap_width
        self.zoom = 2

    @property
    def bitmap_renderer(self):
        return self.segment_viewer.bitmap_renderer

    @property
    def zoom_w(self):
        return self.zoom  # * self.bitmap_renderer.scale_width

    @property
    def zoom_h(self):
        return self.zoom  # * self.bitmap_renderer.scale_height

    @property
    def pixels_per_byte(self):
        return self.bitmap_renderer.pixels_per_byte

    @property
    def scale_width(self):
        return self.bitmap_renderer.scale_width

    @property
    def scale_height(self):
        return self.bitmap_renderer.scale_height

    def calc_line_renderer(self):
        if hasattr(self, 'segment_viewer'):
            return BitmapLineRenderer(self)
        return SegmentGridControl.calc_line_renderer(self)

    def verify_line_renderer(self):
        self.recalc_line_renderer()


class BitmapViewer(AnticColorViewer):
    name = "bitmap"

    ui_name = "Bitmap"

    control_cls = BitmapGridControl

    has_bitmap = True

    has_width = True

    width_text = "bitmap width in bytes"

    has_zoom = True

    zoom_text = "bitmap zoom factor"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bitmap_renderer_name = "B/W, 1bpp, on=black"
        self._bitmap_renderer = None

    @property
    def bitmap_renderer_name(self):
        return self._bitmap_renderer_name

    @bitmap_renderer_name.setter
    def bitmap_renderer_name(self, value):
        self._bitmap_renderer_name = value
        self._bitmap_renderer = None
        self.graphics_properties_changed()

    @property
    def bitmap_renderer(self):
        if self._bitmap_renderer is None:
            self._bitmap_renderer = valid_bitmap_renderers[self._bitmap_renderer_name]
        return self._bitmap_renderer

    @property
    def window_title(self):
        return self.bitmap_renderer.name

    def validate_width(self, width):
        return self.bitmap_renderer.validate_bytes_per_row(width)

    def recalc_data_model(self):
        self.control.recalc_view()


class MemoryMapViewer(BitmapViewer):
    name = "memmap"

    ui_name = "Memory Page Map"
