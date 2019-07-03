"""Byte modification actions
"""
import os
import sys

import wx

from sawx.ui import dialogs
from atrip.char_mapping import font_mapping_list
from atrip.machines import atari8bit

from . import ViewerAction, ViewerListAction, ViewerRadioListAction
from .. import commands
from ...arch.bitmap_renderers import bitmap_renderer_list
from ...arch.fonts import font_list, font_groups, prompt_for_font_from_group
from ...arch.font_renderers import font_renderer_list
from ...arch.ui.antic_colors import AnticColorDialog
from ...viewer import find_viewer_class_by_name, get_viewers

import logging
log = logging.getLogger(__name__)


class view_width(ViewerAction):
    """Set the number of items per row of the bitmap display. The width can
    mean different things for different viewers (i.e. bitmap widths are in
    byte_values, not pixels), so prompt is based on the viewer.
    """
    name = "Width..."

    def calc_enabled(self, action_key):
        state = self.viewer.has_width
        return state

    def perform(self, action_key):
        v = self.viewer
        val = dialogs.prompt_for_dec(v.control, 'Enter new %s' % v.width_text, 'Set Width', v.width)
        if val is not None and val > 0:
            v.set_width(val)


class view_zoom(ViewerAction):
    """Set the zoom factor of the viewer, if applicable. This is an integer
    value greater than zero that scales the display size of each item.
    """
    name = "Zoom..."

    def calc_enabled(self, action_key):
        state = self.viewer.has_zoom
        return state

    def perform(self, event):
        v = self.viewer
        val = dialogs.prompt_for_dec(v.control, 'Enter new %s' % v.zoom_text, 'Set Zoom', v.zoom)
        if val is not None and val > 0:
            v.set_zoom(val)


class ColorAction(ViewerAction):
    def calc_enabled(self, action_key):
        state = self.viewer.has_colors
        return state


class view_ask_colors(ColorAction):
    """Open a window to choose the color palette from the available colors
    of the ANTIC processor.
    """
    name = 'Use ANTIC Colors...'

    def perform(self, action_key):
        v = self.viewer
        dlg = AnticColorDialog(v.control, v.antic_color_registers, v.linked_base.cached_preferences)
        if dlg.ShowModal() == wx.ID_OK:
            v.antic_color_registers = dlg.colors


class view_antic_powerup_colors(ColorAction):
    """Changes the color palette to {name}
    """
    name = 'ANTIC Powerup Colors'

    def perform(self, action_key):
        self.viewer.antic_color_registers = atari8bit.powerup_colors()


class view_color_standards(ViewerRadioListAction):
    def calc_enabled(self, action_key):
        return self.viewer.has_colors

    def calc_name(self, action_key):
        item = self.get_item(action_key)
        return str(item)

    def calc_list_items(self):
        return atari8bit.color_standard_list

    def calc_checked_list_item(self, action_key, index, item):
        return self.viewer.color_standard_name == item.name

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.viewer.color_standard_name = item.name


class view_bitmap_renderers(ViewerRadioListAction):
    def calc_enabled(self, action_key):
        return self.viewer.has_bitmap

    def calc_name(self, action_key):
        item = self.get_item(action_key)
        return str(item)

    def calc_list_items(self):
        return bitmap_renderer_list

    def calc_checked_list_item(self, action_key, index, item):
        return self.viewer.bitmap_renderer_name == item.name

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.viewer.bitmap_renderer_name = item.name


class view_font_renderers(ViewerRadioListAction):
    def calc_enabled(self, action_key):
        return self.viewer.has_font

    def calc_name(self, action_key):
        item = self.get_item(action_key)
        return str(item)

    def calc_list_items(self):
        return font_renderer_list

    def calc_checked_list_item(self, action_key, index, item):
        return self.viewer.font_renderer_name == item.name

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.viewer.font_renderer_name = item.name


class view_font_mappings(ViewerRadioListAction):
    def calc_enabled(self, action_key):
        return self.viewer.has_font

    def calc_name(self, action_key):
        item = self.get_item(action_key)
        return str(item)

    def calc_list_items(self):
        return font_mapping_list

    def calc_checked_list_item(self, action_key, index, item):
        return self.viewer.font_mapping_name == item.name

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.viewer.font_mapping_name = item.name


class view_fonts(ViewerRadioListAction):
    def calc_enabled(self, action_key):
        return self.viewer.has_font

    def calc_name(self, action_key):
        item = self.get_item(action_key)
        return str(item)

    def calc_list_items(self):
        return font_list

    def calc_checked_list_item(self, action_key, index, item):
        return self.viewer.antic_font_uuid == item["uuid"]

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.viewer.antic_font_data = item


class view_font_groups(ViewerListAction):
    def calc_enabled(self, action_key):
        return self.viewer.has_font

    def calc_name(self, action_key):
        item = self.get_item(action_key)
        return str(item) + "..."

    def calc_list_items(self):
        return sorted(font_groups.keys())

    def callback(self, font):
        self.viewer.antic_font_data = font

    def perform(self, action_key):
        item = self.get_item(action_key)
        current_font = self.viewer.antic_font_data
        font = prompt_for_font_from_group(self.editor.frame, item, self.callback)
        if font is None:
            # cancel should restore the old font
            font = current_font
        self.viewer.antic_font_data = font


class view_add_viewer(ViewerListAction):
    def prune_viewers(self, viewer_cls):
        return viewer_cls.viewer_category != "Emulator"

    def calc_list_items(self):
        subset = [v for v in get_viewers().values() if self.prune_viewers(v)]
        subset.sort(key=lambda v: v.ui_name)
        return subset

    def calc_name(self, action_key):
        viewer = self.get_item(action_key)
        return viewer.ui_name

    def perform(self, action_key):
        viewer = self.get_item(action_key)
        self.editor.add_viewer(viewer)


class view_add_emulation_viewer(view_add_viewer):
    def prune_viewers(self, viewer_cls):
        return viewer_cls.viewer_category == "Emulator"
