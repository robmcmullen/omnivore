"""Emulator
"""
import os
import sys

import wx

from sawx.action import SawxAction, SawxNameChangeAction, SawxRadioListAction, SawxRadioAction
from sawx.frame import SawxTablessFrame
from sawx.ui.dialogs import prompt_for_dec

from .. import commands
from .. import errors
from ..emulator import find_emulators
from ..documents.emulation_document import EmulationDocument
from ..editors.emulation_editor import EmulationEditor

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
        items.extend(find_emulators())
        return items

    def calc_checked_list_item(self, action_key, index, item):
        return self.editor.document.emulator_class_override == item

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.editor.document.emulator_class_override = item


class emu_boot_skip_frames(SawxAction):
    def calc_name(self, action_key):
        return "Skip Boot Frames..."

    def show_dialog(self):
        value = prompt_for_dec(self.editor.control, "Skip Boot Frames (decimal, use $ for hex)", "Skip Boot Frames")
        if value is not None:
            print(f"emu_boot_skip_frames: {value}")
            self.editor.document.skip_frames_on_boot = value

    def perform(self, action_key):
        wx.CallAfter(self.show_dialog)


class emu_boot_start_paused(SawxRadioAction):
    name = "Start Paused"
    def calc_checked(self, action_key):
        return self.editor.document.pause_emulator_on_boot

    def perform(self, action_key):
        self.editor.document.pause_emulator_on_boot = not self.editor.document.pause_emulator_on_boot
        print("NOW Paused?", self.editor.document.pause_emulator_on_boot)


class emu_boot_disk_image(SawxAction):
    def calc_name(self, action_key):
        return "Boot Disk Image"

    def do_boot(self, doc, source_document):
        doc.boot(source_document.collection.containers[0])

    def perform(self, action_key):
        print(f"Booting disk image using {self.editor.document.emulator_class_override}")
        source_document = self.editor.document
        try:
            doc = EmulationDocument.create_document(source_document, source_document.emulator_class_override)
        except errors.EmulatorInUseError as e:
            print(f"Currently running emulator: {e.current_emulator_document}")
            doc = e.current_emulator_document
            doc.pause_emulator()
            if self.editor.frame.confirm(f"Only one {doc.emulator.ui_name} emulator can be running at any one time.\n\nReplace with the new boot image? Current emulation\nwill be lost.", "Replace Emulator"):
                self.do_boot(doc, source_document)
                editor = wx.GetApp().find_editor_of_document(doc)
                editor.frame.Raise()
                doc.recalc_event(True)
            else:
                doc.resume_emulator()
        else:
            self.do_boot(doc, source_document)
            print(f"emulator document: {doc}")
            editor = EmulationEditor(doc)
            frame = SawxTablessFrame(editor)
            frame.Show()

class emu_boot_segment(emu_boot_disk_image):
    def calc_name(self, action_key):
        return "Boot Segment"

    def do_boot(self, doc, source_document):
        doc.boot(self.editor.focused_viewer.segment)


class emu_restore(SawxAction):
    def calc_name(self, action_key):
        return "Restore Saved State..."

    def perform(self, action_key):
        print(f"Restoring saved state from file")


class emu_pause_resume(SawxNameChangeAction):
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
            self.editor.document.resume_emulator()


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


class emu_break_next_scan_line(SawxAction):
    """Continue to next scan line
    """
    def calc_name(self, action_key):
        return "Break at Next Scan Line"

    def calc_enabled(self, action_key):
        return self.editor.document.emulator.emulator_paused

    def perform(self, action_key):
        self.editor.document.debugger_break_next_scan_line()


class emu_break_vbi_start(SawxAction):
    """Continue and break at the start of the next VBI
    """
    def calc_name(self, action_key):
        return "Break at Next VBI Start"

    def calc_enabled(self, action_key):
        return self.editor.document.emulator.emulator_paused

    def perform(self, action_key):
        self.editor.document.debugger_break_vbi_start()


class emu_break_vbi_end(SawxAction):
    """Continue and break at the end of the next VBI
    """
    def calc_name(self, action_key):
        return "Break at Next VBI End"

    def calc_enabled(self, action_key):
        return self.editor.document.emulator.emulator_paused

    def perform(self, action_key):
        self.editor.document.debugger_break_vbi_end()


class emu_break_dli_start(SawxAction):
    """Continue and break at the start of the next DLI
    """
    def calc_name(self, action_key):
        return "Break at Next DLI Start"

    def calc_enabled(self, action_key):
        return self.editor.document.emulator.emulator_paused

    def perform(self, action_key):
        self.editor.document.debugger_break_dli_start()


class emu_break_dli_end(SawxAction):
    """Continue and break at the end of the next DLI
    """
    def calc_name(self, action_key):
        return "Break at Next DLI End"

    def calc_enabled(self, action_key):
        return self.editor.document.emulator.emulator_paused

    def perform(self, action_key):
        self.editor.document.debugger_break_dli_end()


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
        self.editor.document.resume_emulator()


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
