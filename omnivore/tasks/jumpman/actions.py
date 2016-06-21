""" Action definitions for Jumpman Task

"""
import os
import sys

import wx

# Enthought library imports.
from pyface.tasks.action.api import EditorAction

from omnivore.utils.wx.dialogs import prompt_for_hex

from commands import *


class ClearTriggerAction(EditorAction):
    name = "Clear Trigger Function"

    picked = None

    def perform(self, event):
        self.picked.trigger_function = None

class TriggerAction(EditorAction):
    name = "Set Trigger Function..."

    picked = None

    def perform(self, event):
        e = self.active_editor
        addr, error = prompt_for_hex(e.window.control, "Enter trigger subroutine address: (default hex; prefix with # for decimal)", "Function to be Activated", self.picked.trigger_function, return_error=True, default_base="hex")
        if addr is not None:
            self.picked.trigger_function = addr
            e.bitmap.save_changes()
