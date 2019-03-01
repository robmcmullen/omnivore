"""Byte modification actions
"""
import os
import sys

import wx

from omnivore_framework.utils.wx import dialogs

from . import ViewerAction, ViewerListAction
from .. import commands
from ...arch import colors
from ...arch.font_renderers import font_renderer_list
from ...arch.font_mappings import font_mapping_list
from ...arch.ui.antic_colors import AnticColorDialog

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
        self.viewer.antic_color_registers = colors.powerup_colors()


class view_color_standards(ViewerListAction):
    prefix = "view_color_standards_"

    def calc_enabled(self, action_key):
        return self.viewer.has_colors

    def calc_name(self, action_key):
        item = self.get_item(action_key)
        return str(item)

    def calc_list_items(self):
        return colors.color_standard_list

    def calc_checked_list_item(self, action_key, index, item):
        return self.viewer.color_standard_name == item.name

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.viewer.color_standard_name = item.name


class view_font_renderers(ViewerListAction):
    prefix = "view_font_renderers_"

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


class view_font_mappings(ViewerListAction):
    prefix = "view_font_mappings_"

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
