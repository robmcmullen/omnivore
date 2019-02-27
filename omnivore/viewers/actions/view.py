"""Byte modification actions
"""
import os
import sys

import wx

from omnivore_framework.utils.wx import dialogs

from . import ViewerAction, ViewerRadioAction
from .. import commands
from ...arch import colors
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
        dlg = AnticColorDialog(v.control, v.machine.antic_color_registers, v.linked_base.cached_preferences)
        if dlg.ShowModal() == wx.ID_OK:
            v.machine.update_colors(dlg.colors)


class view_antic_powerup_colors(ColorAction):
    """Changes the color palette to {name}
    """
    name = 'ANTIC Powerup Colors'

    def perform(self, action_key):
        self.viewer.machine.update_colors(colors.powerup_colors())


class ColorStandardAction(ViewerRadioAction):
    """This list sets the color encoding standard for all bitmapped graphics of
    the disk image. Currently supported are:
    """
    doc_hint = "parent,list"

    color_standard = None

    def calc_enabled(self, action_key):
        state = self.viewer.has_colors
        return state

    def calc_checked(self, action_key):
        state = self.viewer.machine.color_standard == self.color_standard
        return state

    def perform(self, action_key):
        self.viewer.machine.set_color_standard(self.color_standard)


class view_ntsc(ColorStandardAction):
    name = 'NTSC'
    color_standard = 0


class view_pal(ColorStandardAction):
    name = 'PAL'
    color_standard = 1
