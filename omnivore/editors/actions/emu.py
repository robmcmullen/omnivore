"""Emulator
"""
import os
import sys

import wx

from sawx.action import SawxAction, SawxRadioListAction

from ... import commands
from ... import errors
from ...emulator import known_emulators

import logging
log = logging.getLogger(__name__)


class emu_list(SawxRadioListAction):
    def calc_name(self, action_key):
        emu = self.get_item(action_key)
        if emu is None:
            return "Default Based On Disk Image"
        return emu.ui_name

    def calc_list_items(self):
        items = [None]
        items.extend(known_emulators)
        return items

    def calc_checked_list_item(self, action_key, index, item):
        return self.editor.document.emulator_class_override == item

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.editor.document.emulator_class_override = item

class emu_boot_disk_image(SawxAction):
    def calc_name(self, action_key):
        return "Boot Disk Image"

    def perform(self, action_key):
        print(f"Booting disk image using {self.editor.document.emulator_class_override}")

class emu_boot_segment(SawxAction):
    def calc_name(self, action_key):
        return "Boot Segment"

    def perform(self, action_key):
        print(f"Booting segment using {self.editor.document.emulator_class_override}")
