from omnivore.framework.panes import FrameworkPane

# Local imports.
from omnivore8bit.hex_edit.panes import SidebarPane
from omnivore8bit.hex_edit.commands import ChangeByteCommand
from omnivore8bit.ui.bitviewscroller import BitviewScroller, FontMapScroller, CharacterSetViewer, MemoryMapScroller
from omnivore.utils.wx.tilelist import TileWrapControl

import logging
log = logging.getLogger(__name__)


class MemoryMapPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.memory_map'
    name = 'Page Map'

    def create_contents(self, parent):
        control = MemoryMapScroller(parent, self.task, size=(64,50))
        return control


class MapSidebarPane(SidebarPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.sidebar'
    name = 'Sidebar'

    movable = False
    caption_visible = False
    dock_layer = 9

    def add_tabs(self, control):
        control.add_tab("Segments", self.segments_cb)
        control.add_tab("Undo History", self.undo_cb)


class TileMapPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.tile_map'
    name = 'Tile Map'

    def create_contents(self, parent):
        control = TileWrapControl(parent, self.task, size=(200,500), command=ChangeByteCommand)
        return control


class CharacterSetPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.character_set'
    name = 'Character Set'

    def create_contents(self, parent):
        control = CharacterSetViewer(parent, self.task, size=(256,500))
        return control
