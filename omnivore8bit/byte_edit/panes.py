from collections import namedtuple

import wx

from omnivore.framework.panes import FrameworkPane, FrameworkFixedPane

# Enthought library imports.
from pyface.api import YES, NO

# Local imports.
from omnivore.utils.wx.popuputil import SpringTabs

import logging
log = logging.getLogger(__name__)


class SidebarPane(FrameworkFixedPane):
    #### TaskPane interface ###################################################

    id = 'byte_edit.sidebar'
    name = 'Sidebar'

    movable = False
    caption_visible = False
    dock_layer = 9

    def segments_cb(self, parent, task, **kwargs):
        control = SegmentList(parent, task)

    def create_contents(self, parent):
        control = SpringTabs(parent, self.task, popup_direction="right")
        self.add_tabs(control)
        return control

    def add_tabs(self, control):
        from omnivore8bit.viewers.info import CommentsViewer, UndoViewer, SegmentListViewer
        # from omnivore8bit.viewers.bitmap import MemoryMapViewer
        control.add_tab("Segments", SegmentListViewer())
        control.add_tab("Comments", CommentsViewer())
        # control.add_tab("Page Map", MemoryMapViewer())
        control.add_tab("Undo History", UndoViewer())

    def refresh_active(self):
        active = self.control._radio
        if active is not None and active.is_shown:
            active.managed_window.refresh_view()

    def recalc_active(self):
        active = self.control._radio
        if active is not None and active.is_shown:
            active.managed_window.recalc_view()
