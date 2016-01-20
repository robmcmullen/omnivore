from omnivore.framework.panes import FrameworkPane

# Local imports.
from omnivore.tasks.hex_edit.segments import SegmentList
from omnivore.tasks.hex_edit.commands import ChangeByteCommand
from omnivore.utils.wx.bitviewscroller import BitviewScroller, FontMapScroller, CharacterSetViewer, MemoryMapScroller
from omnivore.utils.wx.tilelist import TileWrapControl
from omnivore.framework.undo_panel import UndoHistoryPanel

import logging
log = logging.getLogger(__name__)


class MemoryMapPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.memory_map'
    name = 'Page Map'
    
    def create_contents(self, parent):
        control = MemoryMapScroller(parent, self.task, size=(64,50))
        return control


class SegmentsPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.segments'
    name = 'Segments'
    
    def create_contents(self, parent):
        control = SegmentList(parent, self.task, size=(64,150))
        return control


class UndoPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.undo'
    name = 'Undo History'
    
    def create_contents(self, parent):
        control = UndoHistoryPanel(parent, self.task, size=(64,150))
        return control


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
