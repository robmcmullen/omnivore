""" Action definitions for Jumpman Task

"""
import os
import sys

import wx

# Enthought library imports.
from pyface.tasks.action.api import EditorAction

from omnivore.utils.wx.dialogs import prompt_for_hex, prompt_for_string
from omnivore.framework.actions import SelectAllAction, SelectNoneAction, SelectInvertAction
from omnivore.utils.jumpman import DrawObjectBounds

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
        possible_labels = e.get_triggers()
        print possible_labels
        addr, error = prompt_for_hex(e.window.control, "Enter trigger subroutine address: (default hex; prefix with # for decimal)", "Function to be Activated", self.picked.trigger_function, return_error=True, default_base="hex")
        if addr is not None:
            self.picked.trigger_function = addr
            e.bitmap.save_changes()

class ClearTriggerSelectionAction(EditorAction):
    name = "Clear Trigger Function"
    enabled_name = 'can_copy'
    command = ClearTriggerCommand

    def get_addr(self, objects):
        return None

    def permute_object(self, obj, addr):
        obj.trigger_function = addr

    def perform(self, event):
        e = self.active_editor
        objects = e.bitmap.mouse_mode.objects
        try:
            addr = self.get_addr(objects)
            for o in objects:
                self.permute_object(o, addr)
            e.bitmap.save_changes(self.command)
            e.bitmap.mouse_mode.resync_objects()
        except ValueError:
            pass

class SetTriggerSelectionAction(ClearTriggerSelectionAction):
    name = "Set Trigger Function"
    command = SetTriggerCommand

    def get_addr(self, objects):
        e = self.active_editor
        addr, error = prompt_for_hex(e.window.control, "Enter trigger subroutine address: (default hex; prefix with # for decimal)", "Function to be Activated", return_error=True, default_base="hex")
        if addr is not None:
            return addr
        raise ValueError("Cancelled!")


class SelectAllJumpmanAction(EditorAction):
    name = 'Select All'
    accelerator = 'Ctrl+A'
    tooltip = 'Select the entire document'
    enabled_name = 'can_select_objects'

    def perform(self, event):
        event.task.active_editor.select_all()

class SelectNoneJumpmanAction(EditorAction):
    name = 'Select None'
    accelerator = 'Shift+Ctrl+A'
    tooltip = 'Clear selection'
    enabled_name = 'can_select_objects'

    def perform(self, event):
        event.task.active_editor.select_none()

class SelectInvertJumpmanAction(EditorAction):
    name = 'Invert Selection'
    tooltip = 'Invert selection'
    enabled_name = 'can_select_objects'

    def perform(self, event):
        event.task.active_editor.select_invert()

class FlipVerticalAction(EditorAction):
    name = "Flip Selection Vertically"
    enabled_name = 'can_copy'
    picked = None
    command = FlipVerticalCommand

    def permute_object(self, obj, bounds):
        obj.flip_vertical(bounds)

    def perform(self, event):
        e = self.active_editor
        objects = e.bitmap.mouse_mode.objects
        bounds = DrawObjectBounds.get_bounds(objects)
        print "mirroring objects: %s" % objects, "bounds", bounds
        for o in e.bitmap.mouse_mode.objects:
            self.permute_object(o, bounds)
        e.bitmap.save_changes(self.command)
        e.bitmap.mouse_mode.resync_objects()


class FlipHorizontalAction(FlipVerticalAction):
    name = "Flip Selection Horizontally"
    command = FlipHorizontalCommand

    def permute_object(self, obj, bounds):
        obj.flip_horizontal(bounds)


class AssemblySourceAction(EditorAction):
    name = 'Custom Code...'

    def perform(self, event):
        e = self.active_editor
        filename = prompt_for_string(e.window.control, "Enter MAC/65 assembly source filename for custom code", "Source File For Custom Code", e.assembly_source)
        if filename is not None:
            e.set_assembly_source(filename)


class RecompileAction(EditorAction):
    name = 'Recompile Code'

    def perform(self, event):
        e = self.active_editor
        e.compile_assembly_source()
