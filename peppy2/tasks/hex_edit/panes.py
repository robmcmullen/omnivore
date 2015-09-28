"""Sample panes for Skeleton

"""
# Enthought library imports.
from pyface.tasks.api import DockPane, TraitsDockPane
from traits.api import on_trait_change

# Local imports.
from disassembly import DisassemblyPanel
from segments import SegmentList
from peppy2.utils.wx.bitviewscroller import BitviewScroller, FontMapScroller, MemoryMapScroller

import logging
log = logging.getLogger(__name__)



class DisassemblyPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.disasmbly_pane'
    name = 'Disassembly'
    
    def create_contents(self, parent):
        control = DisassemblyPanel(parent, self.task)
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)


class ByteGraphicsPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.byte_graphics'
    name = 'Byte Graphics'
    
    def create_contents(self, parent):
        control = BitviewScroller(parent, self.task)
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)


class FontMapPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.font_map'
    name = 'Font Map'
    
    def create_contents(self, parent):
        control = FontMapScroller(parent, self.task)
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)


class MemoryMapPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.memory_map'
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

    id = 'hex_edit.segments'
    name = 'Segments'
    
    def create_contents(self, parent):
        control = SegmentList(parent, self.task)
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)
