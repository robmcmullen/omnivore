import wx

# Enthought library imports.
from pyface.tasks.api import DockPane, TraitsDockPane
from traits.api import on_trait_change

# Local imports.
from disassembly import DisassemblyPanel
from segments import SegmentList
from omnimon.utils.wx.bitviewscroller import BitviewScroller, FontMapScroller, MemoryMapScroller
from omnimon.framework.undo_panel import UndoHistoryPanel
from commands import ChangeByteCommand

import logging
log = logging.getLogger(__name__)



class DisassemblyPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.disasmbly_pane'
    name = 'Disassembly'
    
    def create_contents(self, parent):
        control = DisassemblyPanel(parent, self.task, size=(200,-1))
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
        control = BitviewScroller(parent, self.task, size=(64,-1))
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)


class CharMap(FontMapScroller):
    def change_byte(self, value):
        e = self.editor
        if e.can_copy:
            index = e.anchor_start_index
        else:
            index = e.cursor_index
        cmd = ChangeByteCommand(e.segment, index, index+1, value, True)
        e.process_command(cmd)


class FontMapPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.font_map'
    name = 'Font Map'
    
    def create_contents(self, parent):
        control = CharMap(parent, self.task, size=(160,-1))
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)


class MemoryMapPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.memory_map'
    name = 'Page Map'
    
    def create_contents(self, parent):
        control = MemoryMapScroller(parent, self.task, size=(-1,30))
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
        control = SegmentList(parent, self.task, size=(64,-1))
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)


class UndoPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.undo'
    name = 'Undo History'
    
    def create_contents(self, parent):
        control = UndoHistoryPanel(parent, self.task, size=(64,-1))
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN DISASSEMBLY!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)
