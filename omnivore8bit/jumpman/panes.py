from omnivore.framework.panes import FrameworkPane

# Local imports.
from omnivore8bit.hex_edit.panes import SidebarPane
from omnivore8bit.hex_edit.segments import SegmentList
from omnivore8bit.hex_edit.grid_control import HexEditControl
from omnivore8bit.hex_edit.panes import CommentsPanel
from omnivore8bit.ui.info_panels import InfoPanel
from omnivore8bit.utils.jumpman import is_valid_level_segment

from peanuts import TriggerList

import logging
log = logging.getLogger(__name__)


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
            ("label", "# Peanuts", "num_peanuts", 42),
            ("peanuts_needed", "Peanuts Needed", 0x3e, 1, ["All", "All except 1", "All except 2", "All except 3", "All except 4"]),
            ("uint", "Bonus Value", 0x35, 2, 2500),
            ("dropdown", "Number of Bullets", 0x3d, 1, ["None", "1", "2", "3", "4"]),
            ("antic_colors", "Game Colors", 0x2a, 9),
            ("label", "# Columns with Ladders", "num_ladders", 12),
            ("label", "# Columns with Downropes", "num_downropes", 6),
        ]
        control = JumpmanInfoPanel(parent, self.task, fields, size=(350, 150))
        return control


class LevelList(SegmentList):
    def show_segment_in_list(self, segment):
        # Only show jumpman levels in the list
        return is_valid_level_segment(segment)


class JumpmanSidebarPane(SidebarPane):
    #### TaskPane interface ###################################################

    id = 'jumpman.sidebar'
    name = 'Sidebar'

    movable = False
    caption_visible = False
    dock_layer = 9

    def levels_cb(self, parent, task, **kwargs):
        control = LevelList(parent, task)

    def add_tabs(self, control):
        control.add_tab("Levels", self.levels_cb)
        control.add_tab("Undo History", self.undo_cb)
