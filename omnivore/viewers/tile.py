import os
import sys

import wx

from ..ui.tilewrap import TileWrapControl

from ..viewer import SegmentViewer

import logging
log = logging.getLogger(__name__)


class TileWindow(wx.SplitterWindow):
    def __init__(self, parent, linked_base, *args, **kwargs):
        wx.SplitterWindow.__init__(self, parent, -1, style = wx.SP_LIVE_UPDATE)
        self._segment_viewer = None
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnSashChanged)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.OnSashChanging)

        self.groups = TileWrapControl(self, linked_base, size=(256,100), command=ChangeByteCommand)

        # self.tiles = CharacterSetViewer(self, linked_base, size=(256,100))

        self.SetMinimumPaneSize(100)
        self.SetSashGravity(0.5)
        self.SplitHorizontally(self.groups, self.tiles, 0)

    @property
    def segment_viewer(self):
        return self._segment_viewer

    @segment_viewer.setter
    def segment_viewer(self, segment_viewer):
        # Need to update the child controls
        self._segment_viewer = segment_viewer
        self.groups.segment_viewer = segment_viewer
        self.tiles.segment_viewer = segment_viewer

    def OnSashChanged(self, evt):
        log.debug("sash changed to %s\n" % str(evt.GetSashPosition()))

    def OnSashChanging(self, evt):
        log.debug("sash changing to %s\n" % str(evt.GetSashPosition()))
        # uncomment this to not allow the change
        #evt.SetSashPosition(-1)

    def set_font(self):
        self.groups.set_font()
        self.tiles.set_font()

    def refresh_view(self):
        self.groups.Refresh()
        self.tiles.Refresh()

    def recalc_view(self):
        self.groups.recalc_view()
        self.tiles.recalc_view()


class TileViewer(SegmentViewer):
    name = "tile"

    ui_name = "Tile"

    has_font = True

    linked_viewer = Any(None)

    tile_groups = Any([])

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        return TileWindow(parent, linked_base, size=(160,500))

    ##### Initialization and serialization

    def from_metadata_dict(self, e):
        log.debug("metadata: %s" % str(e))
        if 'tile groups' in e:
            self.tile_groups = e['tile groups']

    def to_metadata_dict(self, mdict, document):
        mdict['tile groups'] = self.tile_groups

    ##### SegmentViewer interface

    def update_bitmap(self, evt):
        log.debug("TileViewer: machine font changed for %s" % self.control)
        if evt is not Undefined:
            self.control.set_font()
            self.control.recalc_view()

    def update_bitmap(self, evt):
        log.debug("focused viewer changed to %s" % evt)
        v = evt
        if hasattr(v, 'draw_pattern'):
            log.debug("changing to %s, checking %s" % (v, self.linked_viewer))
            if v != self.linked_viewer:
                self.linked_viewer = v
                self.control.recalc_view()
                log.debug("new linked_viewer=%s" % (self.linked_viewer))

    def show_caret(self, control, index, bit):
        # Cursor view is meaningless for this view
        pass

    def set_draw_pattern(self, value):
        # inform linked viewer that there should be a new draw pattern!
        log.debug("set draw pattern: %s in %s" % (value, self.linked_viewer))
        if self.linked_viewer is not None:
            self.linked_viewer.set_draw_pattern(value)
            self.control.groups.show_pattern(self.linked_viewer.draw_pattern)
            self.control.tiles.show_pattern(self.linked_viewer.draw_pattern)
