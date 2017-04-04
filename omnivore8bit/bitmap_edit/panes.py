from omnivore.framework.panes import FrameworkPane

# Local imports.
from omnivore8bit.hex_edit.panes import SidebarPane

import logging
log = logging.getLogger(__name__)


class BitmapSidebarPane(SidebarPane):
    #### TaskPane interface ###################################################

    id = 'bitmap_edit.sidebar'
    name = 'Sidebar'

    movable = False
    caption_visible = False
    dock_layer = 9

    def add_tabs(self, control):
        control.addTab("Segments", self.segments_cb)
        control.addTab("Undo History", self.undo_cb)
