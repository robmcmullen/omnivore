""" Action definitions for emulators

"""
import os
import sys

import wx
import wx.lib.dialogs

# Enthought library imports.
from traits.api import on_trait_change, Any, Int, Bool
from pyface.api import YES, NO

from atrcopy import user_bit_mask, data_style, add_xexboot_header, add_atr_header, BootDiskImage, SegmentData, interleave_segments, get_xex

from omnivore.framework.enthought_api import Action, ActionItem, EditorAction, NameChangeAction, TaskDynamicSubmenuGroup
from omnivore.utils.command import StatusFlags

from commands import *
from omnivore.utils.wx.dialogs import prompt_for_hex, prompt_for_dec, prompt_for_string, get_file_dialog_wildcard, ListReorderDialog
from omnivore8bit.ui.dialogs import SegmentOrderDialog
from .. import emulators as emu
from .document import EmulationDocument

if sys.platform == "darwin":
    RADIO_STYLE = "toggle"
else:
    RADIO_STYLE = "radio"

import logging
log = logging.getLogger(__name__)


class UseEmulatorAction(EditorAction):
    """Change the default emulator
    """
    # Traits
    name = "<emu>"
    emulator = Any
    style = RADIO_STYLE

    def perform(self, event):
        emu.default_emulator = self.emulator


class BootDiskImageAction(EditorAction):
    """Run the current disk image in an emulator
    """
    name = "Boot Current Disk Image"
    tooltip = "Start emulator using the current file as the boot disk"

    def perform(self, event=None):
        doc = EmulationDocument(source=self.active_editor.document, emulator_type=emu.default_emulator)
        self.task.new(doc)

    def _update_enabled(self, ui_state):
        self.enabled = not self.active_editor.has_emulator


class BootSegmentsAction(EditorAction):
    """Start an emulator by pre-populating memory using the contents of some
    selected segments.
    """
    name = "Boot Segments in Memory"
    tooltip = "Start emulator using segments to pre-fill the memory of the emulator"

    def perform(self, event=None):
        #self.task.new(self.active_editor.document, emu.default_emulator)
        self.task.error("Not implemented yet!")

    def _update_enabled(self, ui_state):
        self.enabled = not self.active_editor.has_emulator


class EmulatorAction(EditorAction):
    """Base class for emulator actions
    """
    name = "<emulator action>"
    tooltip = "control the emulator"

    def perform(self, event=None):
        print("emulate!")

    def _update_enabled(self, ui_state):
        self.enabled = self.active_editor.has_emulator


class ResumeAction(EmulatorAction):
    """Restart the emulation
    """
    name = "Resume"
    tooltip = "Restart the emulation"

    def perform(self, event=None):
        print("resume!")

    def _update_enabled(self, ui_state):
        self.enabled = self.active_editor.has_emulator and self.active_editor.emulator_running


class PauseAction(EmulatorAction):
    """Restart the emulation
    """
    name = "Pause"
    tooltip = "Restart the emulation"

    def perform(self, event=None):
        print("resume!")

    def _update_enabled(self, ui_state):
        self.enabled = self.active_editor.has_emulator and not self.active_editor.emulator_running


class StepAction(PauseAction):
    """Restart the emulation
    """
    name = "Step"
    tooltip = "Restart the emulation"

    def perform(self, event=None):
        print("resume!")

    def _update_enabled(self, ui_state):
        self.enabled = self.active_editor.has_emulator and self.active_editor.emulator_running


class StepIntoAction(PauseAction):
    """Restart the emulation
    """
    name = "Step Into"
    tooltip = "Restart the emulation"

    def perform(self, event=None):
        print("resume!")

    def _update_enabled(self, ui_state):
        self.enabled = self.active_editor.has_emulator and not self.active_editor.emulator_running


class StepOverAction(PauseAction):
    """Restart the emulation
    """
    name = "Step Over"
    tooltip = "Restart the emulation"

    def perform(self, event=None):
        print("resume!")

    def _update_enabled(self, ui_state):
        self.enabled = self.active_editor.has_emulator and not self.active_editor.emulator_running
