"""Sample panes for Skeleton

"""
# Enthought library imports.
from pyface.tasks.api import DockPane, TraitsDockPane
from traits.api import on_trait_change

# Local imports.
from mos6502 import MOS6502Disassembly
from peppy2.utils.wx.bitmapscroller import BitmapScroller

import logging
log = logging.getLogger(__name__)



class MOS6502DisassemblyPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.mos6502_disasmbly_pane'
    name = '6502 Disassembly'
    
    def create_contents(self, parent):
        control = MOS6502Disassembly(parent, self.task)
        return control
    
    #### trait change handlers
    
    def _task_changed(self):
        log.debug("TASK CHANGED IN MERGEPOINTSPANE!!!! %s" % self.task)
        if self.control:
            self.control.set_task(self.task)


class ByteGraphicsPane(DockPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.byte_graphics'
    name = 'Byte Graphics'
    
    def create_contents(self, parent):
        control = BitmapScroller(parent)
        return control
