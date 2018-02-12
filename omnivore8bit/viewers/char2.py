import os
import sys

import wx

from traits.api import on_trait_change, Bool, Undefined

from omnivore.utils.nputil import intscale
from omnivore.utils.wx import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentTable

from . import SegmentViewer

import logging
log = logging.getLogger(__name__)


class AnticCharImageCache(cg.DrawTextImageCache):
    def draw_item(self, parent, dc, rect, data, style):
        start = 0
        end = len(data)
        nr = 1
        data = data.reshape((nr, -1))
        style = style.reshape((nr, -1))
        v = parent.segment_viewer
        array = parent.font_renderer.get_image(v, v.current_antic_font, data, style, start, end, end, nr, start, end)
        width = array.shape[1]
        height = array.shape[0]
        if width > 0 and height > 0:
            array = intscale(array, parent.zoom_h, parent.zoom_w)
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tostring())
            bmp = wx.Bitmap(image)
            dc.DrawBitmap(bmp, rect.x, rect.y)


class AnticCharRenderer(cg.TableLineRenderer):
    default_image_cache = AnticCharImageCache

    def __init__(self, parent, image_cache=None):
        image_cache = AnticCharImageCache()
        w = parent.font_renderer.char_bit_width * parent.zoom_w
        h = parent.font_renderer.char_bit_height * parent.zoom_h
        cg.LineRenderer.__init__(self, parent, w, h, parent.table.items_per_row, image_cache)

    # BaseLineRenderer interface

    def draw_line(self, parent, dc, line_num, col, index, last_index):
        t = parent.table
        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(parent, dc, rect, data, style)


class CharGridControl(SegmentGridControl):
    initial_zoom = 2

    def set_viewer_defaults(self):
        old = self.items_per_row
        self.items_per_row = self.view_params.map_width
        if old is not None and self.items_per_row != old:
            self.recalc_view()

    def calc_default_table(self, segment, view_params):
        return SegmentTable(segment, view_params.map_width)

    def calc_line_renderer(self):
        if hasattr(self, 'segment_viewer'):
            return AnticCharRenderer(self)
        return SegmentGridControl.calc_line_renderer(self)

    @property
    def font_renderer(self):
        return self.segment_viewer.machine.font_renderer

    @property
    def zoom_w(self):
        return self.zoom * self.font_renderer.scale_width

    @property
    def zoom_h(self):
        return self.zoom * self.font_renderer.scale_height

    def recalc_view(self):
        table = SegmentTable(self.segment_viewer.linked_base.segment, self.items_per_row)
        line_renderer = self.calc_line_renderer()
        log.debug("recalculating %s; items_per_row=%d" % (self, self.items_per_row))
        print("before table:", table)
        print("before main:", self.table)
        cg.HexGridWindow.recalc_view(self, table, self.segment_viewer.linked_base.cached_preferences, line_renderer)
        print("after table:", table)
        print("after main:", self.table)


class CharViewer(SegmentViewer):
    name = "char"

    pretty_name = "Character"

    has_font = True

    @classmethod
    def create_control(cls, parent, linked_base):
        return CharGridControl(parent, linked_base.segment, linked_base, linked_base.cached_preferences)

    @property
    def window_title(self):
        return self.machine.font_renderer.name + ", " + self.machine.font_mapping.name

    @on_trait_change('machine.font_change_event')
    def update_bitmap(self, evt):
        log.debug("CharViewer: machine font changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()
