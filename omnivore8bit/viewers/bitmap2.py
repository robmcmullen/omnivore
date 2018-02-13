import os
import sys

import wx

from traits.api import on_trait_change, Bool, Undefined

from omnivore.utils.nputil import intscale
from omnivore.utils.wx import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentTable

from . import SegmentViewer
from . import actions as va

import logging
log = logging.getLogger(__name__)


class BitmapImageCache(cg.DrawTextImageCache):
    def draw_item(self, parent, dc, rect, data, style):
        start = 0
        end = len(data)
        nr = 1
        array = parent.bitmap_renderer.get_image(parent.segment_viewer, end, nr, end, data, style)
        width = array.shape[1]
        height = array.shape[0]
        if width > 0 and height > 0:
            array = intscale(array, parent.zoom_h, parent.zoom_w)
            #print("bitmap: %d,%d,3 after scaling: %s" % (height, width, str(array.shape)))
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tostring())
            bmp = wx.Bitmap(image)
            dc.DrawBitmap(bmp, rect.x, rect.y)


class BitmapRenderer(cg.TableLineRenderer):
    default_image_cache = BitmapImageCache

    def __init__(self, parent, segment_viewer, image_cache=None):
        image_cache = BitmapImageCache()
        w = parent.zoom_w * parent.scale_width * parent.pixels_per_byte
        h = parent.zoom_h * parent.scale_height
        cg.LineRenderer.__init__(self, parent, w, h, parent.items_per_row, image_cache)

    # BaseLineRenderer interface

    def draw_line(self, parent, dc, line_num, col, index, last_index):
        t = parent.table
        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(parent, dc, rect, data, style)


class BitmapGridControl(SegmentGridControl):
    initial_zoom = 2

    def set_viewer_defaults(self):
        old = self.items_per_row
        self.items_per_row = self.view_params.bitmap_width
        if old is not None and self.items_per_row != old:
            self.recalc_view()

    def calc_default_table(self, segment, view_params):
        return SegmentTable(segment, view_params.bitmap_width)

    @property
    def bitmap_renderer(self):
        return self.segment_viewer.machine.bitmap_renderer

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
            return BitmapRenderer(self, self.segment_viewer)
        return SegmentGridControl.calc_line_renderer(self)

    def recalc_view(self):
        bytes_per_row = self.segment_viewer.validate_width(self.items_per_row)
        self.table = SegmentTable(self.segment_viewer.linked_base.segment, bytes_per_row)
        self.line_renderer = self.calc_line_renderer()
        log.debug("recalculating %s" % self)
        SegmentGridControl.recalc_view(self)

    def get_extra_actions(self):
        actions = [None, va.BitmapWidthAction, va.BitmapZoomAction]
        return actions


class BitmapViewer(SegmentViewer):
    name = "bitmap"

    pretty_name = "Bitmap"

    control_cls = BitmapGridControl

    has_bitmap = True

    @property
    def window_title(self):
        return self.machine.bitmap_renderer.name

    @on_trait_change('machine.bitmap_shape_change_event,machine.bitmap_color_change_event')
    def update_bitmap(self, evt):
        log.debug("BitmapViewer: machine bitmap changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()
            self.linked_base.editor.update_pane_names()

    def validate_width(self, width):
        return self.machine.bitmap_renderer.validate_bytes_per_row(width)


class MemoryMapViewer(BitmapViewer):
    name = "memmap"

    pretty_name = "Memory Page Map"
