from omnivore.framework.panes import FrameworkPane

# Local imports.
from omnivore8bit.hex_edit.panes import SidebarPane
from omnivore8bit.hex_edit.commands import ChangeByteCommand
from omnivore8bit.ui.bitviewscroller import BitviewScroller, FontMapScroller, CharacterSetViewer
from omnivore.framework.undo_panel import UndoHistoryPanel

import logging
log = logging.getLogger(__name__)


class FontSidebarPane(SidebarPane):
    #### TaskPane interface ###################################################

    id = 'font_edit.sidebar'
    name = 'Sidebar'

    movable = False
    caption_visible = False
    dock_layer = 9

    def add_tabs(self, control):
        control.add_tab("Segments", self.segments_cb)
        control.add_tab("Undo History", self.undo_cb)


class PixelEditorPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'font_edit.pixel_editor'
    name = 'Pixel Editor'

    def create_contents(self, parent):
        control = CharacterSetViewer(parent, self.task, size=(200,500))
        return control


class ColorChooserPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'font_edit.color_chooser'
    name = 'Colors'

    def create_contents(self, parent):
        control = UndoHistoryPanel(parent, self.task, size=(256,500))
        return control
