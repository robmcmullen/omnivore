"""Emulator
"""
import os
import sys

import wx

from sawx.action import SawxAction, SawxRadioListAction
from sawx.frame import SawxSingleEditorFrame

from ... import commands
from ... import errors
from ...emulator import known_emulators
from ...emulator.document import EmulationDocument
from ...emulator.editor import EmulatorEditor

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
        source_document = self.editor.document
        doc = EmulationDocument.create_document(source_document, source_document.emulator_class_override)
        doc.boot(source_document.collection.containers[0])
        print(f"emulator document: {doc}")
        editor = EmulatorEditor(doc)
        frame = SawxSingleEditorFrame(editor)
        frame.Show()

class emu_boot_segment(SawxAction):
    def calc_name(self, action_key):
        return "Boot Segment"

    def perform(self, action_key):
        print(f"Booting segment using {self.editor.document.emulator_class_override}")

class emu_restore(SawxAction):
    def calc_name(self, action_key):
        return "Restore Saved State..."

    def perform(self, action_key):
        print(f"Restoring saved state from file")


class emu_pause_resume(SawxAction):
    """Stop or restart the emulation
    """
    def calc_name(self, action_key):
        if not self.editor.document.emulator_running:
            name = "Resume"
        else:
            name = "Pause"
        return name

    def perform(self, action_key):
        if self.editor.document.emulator_running:
            self.editor.document.pause_emulator()
        else:
            self.editor.document.restart_emulator()


class emu_step(SawxAction):
    """Step to next instruction, into subroutine
    """
    def calc_name(self, action_key):
        return "Step"

    def calc_enabled(self, action_key):
        return self.editor.document.emulator.emulator_paused

    def perform(self, action_key):
        self.editor.document.debugger_step()


class emu_step_over(emu_step):
    """Step to next line, through subroutines
    """
    def calc_name(self, action_key):
        return "Step Into"

    def perform(self, action_key):
        print("resume!")


class emu_step_out(emu_step):
    """Step to subroutine return statement, through any subroutines
    called by the current block of code.
    """
    def calc_name(self, action_key):
        return "Step Over"

    def perform(self, action_key):
        print("resume!")


class emu_break_vbi_start(SawxAction):
    """Continue and break at the start of the next VBI
    """
    def calc_name(self, action_key):
        return "Break at Next VBI Start"

    def perform(self, action_key):
        self.editor.document.debugger_break_vbi_start()

    def _update_enabled(self, ui_state):
        self.enabled = self.editor.document.emulator_paused


class emu_break_frame(emu_step):
    """Continue and break when reaching the end of the current frame
    """
    def calc_name(self, action_key):
        return "Break at End of Frame"

    def perform(self, action_key):
        self.editor.document.debugger_count_frames()


class emu_a8_start_key(SawxAction):
    """Press the Start button
    """
    def calc_name(self, action_key):
        return "Start"

    def perform(self, action_key):
        print("START!")
        self.editor.document.emulator.forced_modifier = "start"


class emu_a8_select_key(SawxAction):
    """Press the Select button
    """
    def calc_name(self, action_key):
        return "Select"

    def perform(self, action_key):
        self.editor.document.emulator.forced_modifier = "select"


class emu_a8_option_key(SawxAction):
    """Press the Option button
    """
    def calc_name(self, action_key):
        return "Option"

    def perform(self, action_key):
        self.editor.document.emulator.forced_modifier = "option"


class emu_coldstart(SawxAction):
    """Simulate turning off the power and turning it back on again
    """
    def calc_name(self, action_key):
        return "Reboot"

    def perform(self, action_key):
        self.editor.document.emulator.coldstart()


class emu_warmstart(SawxAction):
    """Simulate pressing the system reset key
    """
    def calc_name(self, action_key):
        return "System Reset"

    def perform(self, action_key):
        self.editor.document.emulator.warmstart()


class emu_prev_history(SawxAction):
    """Load the previous saved frame into the current state of the emulator
    """
    def calc_name(self, action_key):
        return "Previous Save Point"

    def perform(self, action_key):
        d = self.editor.document
        if d.emulator_running:
            d.pause_emulator()
        else:
            d.history_previous()


class emu_next_history(SawxAction):
    """Load the next saved frame into the current state of the emulator
    """
    def calc_name(self, action_key):
        return "Next Save Point"

    def perform(self, action_key):
        d = self.editor.document 
        print("OEUOEU", d.emulator_running)
        if d.emulator_running:
            d.pause_emulator()
        else:
            print("BBVJKBVJKBQJBKQB")
            d.history_next()
