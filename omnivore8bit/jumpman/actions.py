""" Action definitions for Jumpman Task

"""
import os
import sys

import wx

# Enthought library imports.
from pyface.action.api import Action, ActionItem
from pyface.tasks.action.api import EditorAction

from omnivore.utils.wx.dialogs import prompt_for_hex, prompt_for_string, ChooseOnePlusCustomDialog
from omnivore.utils.textutil import text_to_int
from omnivore.framework.actions import SelectAllAction, SelectNoneAction, SelectInvertAction, TaskDynamicSubmenuGroup
from omnivore8bit.utils.jumpman import DrawObjectBounds, is_valid_level_segment
from omnivore8bit.hex_edit.actions import UseSegmentAction

from commands import *

import logging
log = logging.getLogger(__name__)


def trigger_dialog(event, e, obj):
    possible_labels = e.get_triggers()
    label = e.get_trigger_label(obj.trigger_function)
    if label is None and obj.trigger_function:
        custom_value = "%04x" % obj.trigger_function
    else:
        custom_value = ""
    dlg = ChooseOnePlusCustomDialog(event.task.window.control, possible_labels.keys(), label, custom_value, "Choose Trigger Function", "Select one trigger function or enter custom address", "Trigger Addr (hex)")
    if dlg.ShowModal() == wx.ID_OK:
        label, addr = dlg.get_selected()
        if label is not None:
            addr = possible_labels[label]
        else:
            try:
                addr = text_to_int(addr, "hex")
            except ValueError:
                event.task.window.error("Invalid address %s" % addr)
                addr = None
    else:
        addr = None
    dlg.Destroy()
    return addr


class ClearTriggerAction(EditorAction):
    name = "Clear Trigger Function"
    enabled_name = 'can_copy'
    command = ClearTriggerCommand

    picked = None

    def get_objects(self):
        if self.picked is not None:
            return self.picked
        return self.active_editor.bitmap.mouse_mode.objects

    def get_addr(self, event, objects):
        return None

    def permute_object(self, obj, addr):
        obj.trigger_function = addr

    def perform(self, event):
        e = self.active_editor
        objects = self.get_objects()
        try:
            addr = self.get_addr(event, objects)
            for o in objects:
                self.permute_object(o, addr)
            e.bitmap.save_changes(self.command)
            e.bitmap.mouse_mode.resync_objects()
        except ValueError:
            pass


class SetTriggerAction(ClearTriggerAction):
    name = "Set Trigger Function..."
    command = SetTriggerCommand

    def get_addr(self, event, objects):
        e = self.active_editor
        addr = trigger_dialog(event, e, objects[0])
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
        e.compile_assembly_source(True)


class LevelListGroup(TaskDynamicSubmenuGroup):
    """Dynamic menu group to display the available levels
    """
    #### 'DynamicSubmenuGroup' interface #####################################

    event_name = 'segments_changed'

    ##########################################################################
    # Private interface.
    ##########################################################################

    def _get_items(self, event_data=None):
        items = []
        if event_data is not None:
            for i, segment in enumerate(event_data):
                if is_valid_level_segment(segment):
                    action = UseSegmentAction(segment=segment, segment_number=i, task=self.task, checked=False)
                    log.debug("LevelListGroup: created %s for %s, num=%d" % (action, str(segment), i))
                    items.append(ActionItem(action=action, parent=self))

        return items
