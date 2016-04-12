from omnivore.framework.panes import FrameworkPane

# Local imports.
from omnivore.tasks.hex_edit.segments import SegmentList
from omnivore.framework.undo_panel import UndoHistoryPanel

import logging
log = logging.getLogger(__name__)


class SegmentsPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'bitmap_edit.segments'
    name = 'Segments'
    
    def create_contents(self, parent):
        control = SegmentList(parent, self.task, size=(64,150))
        return control


class UndoPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'bitmap_edit.undo'
    name = 'Undo History'
    
    def create_contents(self, parent):
        control = UndoHistoryPanel(parent, self.task, size=(64,150))
        return control
