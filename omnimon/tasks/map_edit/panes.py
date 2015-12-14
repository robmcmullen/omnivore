from omnimon.framework.panes import FrameworkPane

# Local imports.
from omnimon.tasks.hex_edit.segments import SegmentList
from omnimon.tasks.hex_edit.commands import ChangeByteCommand
from omnimon.utils.wx.bitviewscroller import BitviewScroller, FontMapScroller, MemoryMapScroller
from omnimon.utils.wx.tilelist import TileListControl
from omnimon.framework.undo_panel import UndoHistoryPanel

import logging
log = logging.getLogger(__name__)


class MemoryMapPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.memory_map'
    name = 'Page Map'
    
    def create_contents(self, parent):
        control = MemoryMapScroller(parent, self.task, size=(600,30))
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
        control = TileListControl(parent, self.task, size=(200,500), command=ChangeByteCommand)
        return control
