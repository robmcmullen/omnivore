import wx

from omnivore.framework.panes import FrameworkPane

# Local imports.
from disassembly import DisassemblyPanel
from segments import SegmentList
from omnivore.utils.wx.bitviewscroller import BitmapScroller, FontMapScroller, MemoryMapScroller
from omnivore.framework.undo_panel import UndoHistoryPanel
from commands import ChangeByteCommand

import logging
log = logging.getLogger(__name__)


class DisassemblyPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.disassembly'
    name = 'Disassembly'
    
    def create_contents(self, parent):
        control = DisassemblyPanel(parent, self.task, size=(300,500))
        return control


class BitmapPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.bitmap'
    name = 'Bitmap'
    
    def create_contents(self, parent):
        control = BitmapScroller(parent, self.task, size=(64,500))
        return control


class FontMapPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.font_map'
    name = 'Char Map'
    
    def create_contents(self, parent):
        control = FontMapScroller(parent, self.task, size=(160,500), command=ChangeByteCommand)
        return control


class MemoryMapPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.memory_map'
    name = 'Page Map'
    
    def create_contents(self, parent):
        control = MemoryMapScroller(parent, self.task, size=(600,30))
        return control


class SegmentsPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.segments'
    name = 'Segments'
    
    def create_contents(self, parent):
        control = SegmentList(parent, self.task, size=(64,150))
        return control


class UndoPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.undo'
    name = 'Undo History'
    
    def create_contents(self, parent):
        control = UndoHistoryPanel(parent, self.task, size=(64,150))
        return control
