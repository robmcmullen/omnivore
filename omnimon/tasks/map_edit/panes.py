"""Sample panes for Skeleton

"""
# Enthought library imports.
from pyface.tasks.api import DockPane, TraitsDockPane
from traits.api import on_trait_change

# Local imports.
from omnimon.tasks.hex_edit.segments import SegmentList
from omnimon.utils.wx.bitviewscroller import BitviewScroller, FontMapScroller, MemoryMapScroller
from omnimon.framework.undo_panel import UndoHistoryPanel

import logging
log = logging.getLogger(__name__)



class MemoryMapPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.memory_map'
    name = 'Memory Map'
    
    def create_contents(self, parent):
        control = MemoryMapScroller(parent, self.task)
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)


class SegmentsPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.segments'
    name = 'Segments'
    
    def create_contents(self, parent):
        control = SegmentList(parent, self.task, size=(64,-1))
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)


class UndoPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'map_edit.undo'
    name = 'Undo History'
    
    def create_contents(self, parent):
        control = UndoHistoryPanel(parent, self.task)
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)
