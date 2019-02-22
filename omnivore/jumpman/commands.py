""" Action definitions for Jumpman Task

"""
import os
import sys

import wx
import numpy as np

from omnivore_framework.utils.wx.dialogs import prompt_for_hex, prompt_for_string, ChooseOnePlusCustomDialog
from omnivore_framework.utils.textutil import text_to_int
from ..byte_edit.actions import UseSegmentAction

from .. import errors
from ..viewers.commands import SetValueCommand
from ..viewers.actions import ViewerAction

from .parser import DrawObjectBounds, is_valid_level_segment

import logging
progress_log = logging.getLogger("progress")

import logging
log = logging.getLogger(__name__)


def trigger_dialog(event, segment_viewer, obj):
    model = segment_viewer.linked_base.jumpman_playfield_model
    possible_labels = model.get_triggers()
    label = model.get_trigger_label(obj.trigger_function)
    if label is None and obj.trigger_function:
        custom_value = "%04x" % obj.trigger_function
    else:
        custom_value = ""
    dlg = ChooseOnePlusCustomDialog(event.task.window.control, list(possible_labels.keys()), label, custom_value, "Choose Trigger Function", "Select one trigger function or enter custom address", "Trigger Addr (hex)")
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

class JumpmanBaseCommand(SetValueCommand):
    def set_undo_flags(self, flags):
        # FIXME: need to add new flags to control rebuilding of objects, etc?
        flags.byte_values_changed = True


class CreateObjectCommand(JumpmanBaseCommand):
    short_name = "create_jumpman_obj"
    pretty_name = "Create Object"


class MoveObjectCommand(JumpmanBaseCommand):
    short_name = "move_jumpman_obj"
    pretty_name = "Move Object"


class FlipVerticalCommand(JumpmanBaseCommand):
    short_name = "vflip_jumpman_obj"
    pretty_name = "Flip Vertically"


class FlipHorizontalCommand(JumpmanBaseCommand):
    short_name = "hflip_jumpman_obj"
    pretty_name = "Flip Horizontally"


class ClearTriggerCommand(JumpmanBaseCommand):
    short_name = "cleartrigger_jumpman_obj"
    pretty_name = "Clear Trigger Function"


class SetTriggerCommand(JumpmanBaseCommand):
    short_name = "settrigger_jumpman_obj"
    pretty_name = "Set Trigger Function"


class AssemblyChangedCommand(JumpmanBaseCommand):
    short_name = "jumpman_custom_code"
    pretty_name = "Reassemble Custom Code"


class ClearTriggerAction(ViewerAction):
    """Remove any trigger function from the selected peanut(s).
    
    """
    name = "Clear Trigger Function"
    enabled_name = 'can_copy'
    command = ClearTriggerCommand

    picked = None

    def get_objects(self):
        if self.picked is not None:
            return self.picked
        return self.viewer.control.mouse_mode.objects

    def get_addr(self, event, objects):
        return None

    def permute_object(self, obj, addr):
        obj.trigger_function = addr

    def perform(self, event):
        objects = self.get_objects()
        try:
            addr = self.get_addr(event, objects)
            for o in objects:
                self.permute_object(o, addr)
            self.viewer.linked_base.jumpman_playfield_model.save_changes(self.command)
            self.viewer.control.mouse_mode.resync_objects()
        except ValueError:
            pass


class SetTriggerAction(ClearTriggerAction):
    """Set a trigger function for the selected peanut(s).

    If you have used the custom code option, have compiled your code using the
    built-in assembler, *and* your code has labels that start with ``trigger``,
    these will show up in the list that appears when you invoke this action.

    Otherwise, you can specify the hex address of a subroutine.
    """
    name = "Set Trigger Function..."
    command = SetTriggerCommand

    def get_addr(self, event, objects):
        addr = trigger_dialog(event, self.viewer, objects[0])
        if addr is not None:
            return addr
        raise ValueError("Cancelled!")


class SelectAllJumpmanAction(ViewerAction):
    """Select all drawing elements in the main level

    """
    name = 'Select All'
    accelerator = 'Ctrl+A'
    tooltip = 'Select the entire document'
    enabled_name = 'can_select_objects'

    def perform(self, event):
        self.viewer.select_all()


class SelectNoneJumpmanAction(ViewerAction):
    """Clear all selections

    """
    name = 'Select None'
    accelerator = 'Shift+Ctrl+A'
    tooltip = 'Clear selection'
    enabled_name = 'can_select_objects'

    def perform(self, event):
        self.viewer.select_none()


class SelectInvertJumpmanAction(ViewerAction):
    """Invert the selection; that is: select everything that is currently
    unselected and unselect those that were selected.

    """
    name = 'Invert Selection'
    tooltip = 'Invert selection'
    enabled_name = 'can_select_objects'

    def perform(self, event):
        self.viewer.select_invert()


class FlipVerticalAction(ViewerAction):
    """Flips the selected items top to bottom.

    This calculates the bounding box of just the selected items and uses that
    to find the centerline about which to flip.
    """
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
    """Flips the selected items left to right.

    This calculates the bounding box of just the selected items and uses that
    to find the centerline about which to flip.
    """
    name = "Flip Selection Horizontally"
    command = FlipHorizontalCommand

    def permute_object(self, obj, bounds):
        obj.flip_horizontal(bounds)


class AssemblySourceAction(ViewerAction):
    """Add an assembly source file to this level (and compile it)

    This is used to provide custom actions or even game loops, beyond what is
    already built-in with trigger painting. There are special labels that are
    recognized by the assembler and used in the appropriate places:

        * vbi1
        * vbi2
        * vbi3
        * vbi4
        * dead_begin
        * dead_at_bottom
        * dead_falling
        * gameloop
        * out_of_lives
        * level_complete
        * collect_callback

    See our `reverse engineering notes
    <http://playermissile.com/jumpman/notes.html#h.s0ullubzr0vv>`_ for more
    details.
    """
    name = 'Custom Code...'

    def perform(self, event):
        filename = prompt_for_string(self.viewer.control, "Enter MAC/65 assembly source filename for custom code", "Source File For Custom Code", self.viewer.current_level.assembly_source)
        if filename is not None:
            self.linked_base.jumpman_playfield_model.set_assembly_source(filename)


class RecompileAction(ViewerAction):
    """Recompile the assembly source code.

    This is a manual action, currently the program doesn't know when the file
    has changed. Making this process more automatic is a planned future
    enhancement.
    """
    name = 'Recompile Code'

    def perform(self, event):
        self.linked_base.jumpman_playfield_model.compile_assembly_source(True)


class jumpman_level_list(ViewerAction):
    prefix = "jumpman_level_"

    prefix_count = len(prefix)

    def init_from_editor(self):
        valid_segments = []
        for i, segment in enumerate(self.editor.document.segments):
            if is_valid_level_segment(segment):
                valid_segments.append((i, segment))
        self.current_list = valid_segments

    def get_index(self, action_key):
        return int(action_key[self.prefix_count:])

    def get_segment(self, action_key):
        return self.current_list[self.get_index(action_key)][1]

    def get_segment_number(self, action_key):
        return self.current_list[self.get_index(action_key)][0]

    def calc_name(self, action_key):
        if len(self.current_list) == 0:
            return "No recent files"
        return str(self.get_segment(action_key))

    def calc_menu_sub_keys(self, action_key):
        if len(self.current_list) == 0:
            return [self.prefix + "empty"]
        return [f"{self.prefix}{i}" for i in range(len(self.current_list))]

    def sync_menu_item_from_editor(self, action_key, menu_item):
        doc = self.editor.document
        segment_number, segment = self.current_list[self.get_index(action_key)]
        if segment_number >= len(doc.segments) or segment != doc.segments[segment_number]:
            raise errors.RecreateDynamicMenuBar
        state = self.editor.segment_number == self.get_segment_number(action_key)
        log.debug(f"jumpman_level_list: checked={state}, {self.editor.segment}")
        menu_item.Check(state)

    def perform(self, action_key):
        self.active_editor.view_segment_number(self.get_segment_number(action_key))
