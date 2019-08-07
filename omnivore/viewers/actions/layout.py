"""Tile manager layout actions for viewers
"""
import os
import sys

import wx

from . import ViewerAction

import logging
log = logging.getLogger(__name__)


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
