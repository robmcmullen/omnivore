import wx

from ..action import ViewerAction

from sawx.action import SawxAction, SawxListAction, SawxPersistentDictAction
from sawx import errors
from sawx.persistence import get_json_data, save_json_data

import logging
log = logging.getLogger(__name__)


class layout_save(SawxAction):
    name = "Save Layout"

    def save_layout(self, label, layout):
        layout_restore.add(label, layout)

    def perform(self, action_key):
        label = self.editor.frame.prompt("Enter name for layout", "Save Layout")
        if label:
            layout = {}
            self.editor.serialize_session(layout, False)
            self.save_layout(label, layout)


class layout_restore(SawxPersistentDictAction):
    prefix = "layout_restore_"

    json_name = "tilemanager_layouts"

    def get_layout(self, action_key):
        label = self.current_list[self.get_index(action_key)]
        d = self.get_dict()
        return d[label]

    def perform(self, action_key):
        layout = self.get_layout(action_key)
        self.editor.replace_layout(layout)


class layout_save_emu(layout_save):
    name = "Save Emulator Layout"

    def save_layout(self, label, layout):
        layout_restore_emu.add(label, layout)


class layout_restore_emu(layout_restore):
    prefix = "layout_restore_emu_"

    json_name = "tilemanager_emulator_layouts"

    def perform(self, action_key):
        doc = self.editor.document
        doc.pause_emulator()
        try:
            layout_restore.perform(self, action_key)
        finally:
            doc.resume_emulator()


class TileManagerAction(ViewerAction):
    name = "Add Viewer Above"

    @property
    def tilemanger(self):
        return self.editor.control

    @property
    def tile_client(self):
        v = self.viewer
        client = self.tilemanger.find_control(v.control)
        log.debug(f"viewer={v}, client={client}")
        return client


class TileAddAction(TileManagerAction):
    side = None

    def perform(self, action_key):
        client = self.tile_client
        client.split_side(self.side)


class layout_add_viewer_above(TileAddAction):
    name = "Add Viewer Above"
    side = wx.TOP


class layout_add_viewer_below(TileAddAction):
    name = "Add Viewer Below"
    side = wx.BOTTOM


class layout_add_viewer_left(TileAddAction):
    name = "Add Viewer Left"
    side = wx.LEFT


class layout_add_viewer_right(TileAddAction):
    name = "Add Viewer Right"
    side = wx.RIGHT


class TileSidebarAction(TileManagerAction):
    side = None

    def perform(self, action_key):
        client = self.tile_client
        client.minimize(self.side)


class layout_move_to_top_sidebar(TileSidebarAction):
    name = "Move Viewer to Top Sidebar"
    side = wx.TOP


class layout_move_to_bottom_sidebar(TileSidebarAction):
    name = "Move Viewer to Bottom Sidebar"
    side = wx.BOTTOM


class layout_move_to_left_sidebar(TileSidebarAction):
    name = "Move Viewer to Left Sidebar"
    side = wx.LEFT


class layout_move_to_right_sidebar(TileSidebarAction):
    name = "Move Viewer to Right Sidebar"
    side = wx.RIGHT


class layout_remove_viewer_and_close_tile(TileManagerAction):
    name = "Remove Viewer and Tile"

    def perform(self, action_key):
        client = self.tile_client
        client.destroy_thyself()


class layout_remove_viewer_and_keep_tile(TileManagerAction):
    name = "Remove Viewer, Keep Tile"

    def perform(self, action_key):
        client = self.tile_client
        client.clear_child()
