from omnivore.framework.panes import FrameworkPane

# Local imports.
from omnivore.tasks.hex_edit.segments import SegmentList
from omnivore.tasks.hex_edit.grid_control import HexEditControl
from omnivore.tasks.hex_edit.panes import CommentsPanel
from omnivore.framework.undo_panel import UndoHistoryPanel
from omnivore.utils.wx.springtabs import SpringTabs
from omnivore.utils.wx.info_panels import InfoPanel

from peanuts import TriggerList

import logging
log = logging.getLogger(__name__)


class SegmentsPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'jumpman.segments'
    name = 'Segments'
    
    def create_contents(self, parent):
        control = SegmentList(parent, self.task, size=(64,150))
        return control


class UndoPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'jumpman.undo'
    name = 'Undo History'
    
    def create_contents(self, parent):
        control = UndoHistoryPanel(parent, self.task, size=(64,150))
        return control


class HexPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'jumpman.hex'
    name = 'Raw Level Data'
    
    def create_contents(self, parent):
        control = HexEditControl(parent, self.task, size=(350, 150))
        return control


class TriggerPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'jumpman.triggers'
    name = 'Trigger Painting'
    
    def create_contents(self, parent):
        control = TriggerList(parent, self.task, size=(350,150))
        return control


class JumpmanInfoPanel(InfoPanel):
    def is_valid_data(self):
        return self.editor.valid_jumpman_segment and bool(self.editor.bitmap.level_builder.objects)


class LevelDataPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'jumpman.level_data'
    name = 'Level Data'
    
    def create_contents(self, parent):
        fields = [
            ("text", "Level Number", 0x00, 2),
            ("atascii_gr2_0xc0", "Level Name", 0x3ec, 20),
            ("uint", "Points per Peanut", 0x33, 2, 250),
            ("label", "# Peanuts", "num_peanuts", 1000),
            ("peanuts_needed", "Peanuts Needed", 0x3e, 1, ["All", "All except 1", "All except 2", "All except 3", "All except 4"]),
            ("uint", "Bonus Value", 0x35, 2, 2500),
            ("dropdown", "Number of Bullets", 0x3d, 1, ["None", "1", "2", "3", "4"]),
            ("antic_colors", "Game Colors", 0x2a, 9),
            ("label", "# Columns with Ladders", "num_ladders", 12),
            ("label", "# Columns with Downropes", "num_downropes", 6),
        ]
        control = JumpmanInfoPanel(parent, self.task, fields, size=(350, 150))
        return control


class SidebarPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'jumpman.sidebar'
    name = 'Sidebar'
    
    movable = False
    caption_visible = False
    dock_layer = 9
    
    def comments_cb(self, parent, task, **kwargs):
        control = CommentsPanel(parent, task)
        
    def create_contents(self, parent):
        control = SpringTabs(parent, self.task, popup_direction="left")
        control.addTab("Comments", self.comments_cb)
        return control
    
    def refresh_active(self):
        active = self.control._radio
        if active is not None and active.is_shown:
            active.managed_window.refresh_view()
