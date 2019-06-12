"""Byte modification actions
"""
import os
import sys

import wx

from sawx.ui.dialogs import prompt_for_hex, prompt_for_slice

from . import ViewerAction
from .. import commands

import logging
log = logging.getLogger(__name__)


class IndexRangeAction(ViewerAction):
    """base class for byte modification operations
    """
    doc_hint = "parent,list,level 3"
    parent_doc = """The commands in this menu operate on the current selection to change the byte values to:
    """
    cmd = None

    def calc_name(self, action_key):
        return self.cmd.ui_name

    def calc_enabled(self, action_key):
        return self.editor.can_copy

    def get_cmd(self, editor, segment, ranges):
        return self.cmd(segment, ranges)

    def perform(self, action_key):
        e = self.editor
        cmd = self.get_cmd(e, e.segment, e.current_selection)
        e.process_command(cmd)


class byte_set_to_zero(IndexRangeAction):
    """Set to zero"""
    cmd = commands.ZeroCommand


class byte_set_to_ff(IndexRangeAction):
    """Set to $ff"""
    cmd = commands.FFCommand


class byte_nop(IndexRangeAction):
    """Set to the NOP command of the current processor"""
    cmd = commands.NOPCommand

    def calc_enabled(self, action_key):
        return self.viewer.has_cpu

    def get_cmd(self, editor, segment, ranges):
        nop = self.viewer.machine.get_nop()
        return self.cmd(segment, ranges, nop)


class byte_set_high_bit(IndexRangeAction):
    """Or with $80"""
    cmd = commands.SetHighBitCommand


class byte_clear_high_bit(IndexRangeAction):
    """And with $7f"""
    cmd = commands.ClearHighBitCommand


class byte_bitwise_not(IndexRangeAction):
    """Invert every bit in each byte"""
    cmd = commands.BitwiseNotCommand


class byte_shift_left(IndexRangeAction):
    """Shift bits left (multiply by 2), inserting zeros in the low bit"""
    cmd = commands.LeftShiftCommand


class byte_shift_right(IndexRangeAction):
    """Shift bits right (divide by 2), inserting zeros in the high bit"""
    cmd = commands.RightShiftCommand


class byte_rotate_left(IndexRangeAction):
    """Shift bits left where the high bit wraps around to become the new low bit"""
    cmd = commands.LeftRotateCommand


class byte_rotate_right(IndexRangeAction):
    """Shift bits right where the low bit wraps around to become the new high bit"""
    cmd = commands.RightRotateCommand


class byte_reverse_bits(IndexRangeAction):
    """Reverse the bit pattern of each byte; e.g. $c0 or 11000000 in binary becomes 00000011 in binary, $03 in hex"""
    cmd = commands.ReverseBitsCommand


class byte_random(IndexRangeAction):
    """Generate random bytes to replace the selected data"""
    cmd = commands.RandomBytesCommand


class IndexRangeValueAction(IndexRangeAction):
    prompt = "Enter byte value: (default hex, prefix with # for decimal, %% for binary)"

    def calc_name(self, action_key):
        return self.cmd.ui_name + "..."

    def show_dialog(self):
        value = prompt_for_hex(self.viewer.control, self.prompt, self.cmd.ui_name)
        if value is not None:
            ranges = self.viewer.control.get_selected_ranges()
            cmd = self.cmd(self.editor.segment, ranges, value)
            self.editor.process_command(cmd)

    def perform(self, action_key):
        wx.CallAfter(self.show_dialog)

    def _update_enabled(self, ui_state):
        # Setting a range of values don't make sense for a single byte
        # location, so require it to have an actual range
        return self.viewer.has_editable_bytes and self.linked_base.has_selection


class byte_set_value(IndexRangeValueAction):
    """Prompts the user and sets the data to the specified value"""
    cmd = commands.SetValueCommand


class byte_or_with_value(IndexRangeValueAction):
    """Logical OR the selected data with the user specified value"""
    cmd = commands.OrWithCommand


class byte_and_with_value(IndexRangeValueAction):
    """Logical AND the selected data with the user specified value"""
    cmd = commands.AndWithCommand


class byte_xor_with_value(IndexRangeValueAction):
    """Logical XOR the selected data with the user specified value"""
    cmd = commands.XorWithCommand


class SliceValueAction(IndexRangeValueAction):
    prompt = "Enter byte value: (default hex, prefix with # for decimal, %% for binary)"

    def show_dialog(self):
        slice_obj = prompt_for_slice(self.viewer.control, self.prompt, self.cmd.ui_name)
        if slice_obj is not None:
            cmd = self.cmd(self.linked_base.segment, self.linked_base.carets.selected_ranges, slice_obj)
            self.editor.process_command(cmd)


class byte_ramp_up(SliceValueAction):
    """Starting with the user specified value at the first selected byte, loops
    over each byte in the selection and adds one to the value of the previous
    byte. At $ff, it wraps around to $00.
    """
    cmd = commands.RampUpCommand


class byte_ramp_down(SliceValueAction):
    """Starting with the user specified value at the first selected byte, loops
    over each byte in the selection and subtracts one from the value of the
    previous byte. At $00, it wraps around to $ff.
    """
    cmd = commands.RampDownCommand


class byte_add_value(IndexRangeValueAction):
    """Adds the user specified value to the data, performing a logical AND with
    $ff if necessary to keep all values in the 8-bit range."""
    cmd = commands.AddValueCommand


class byte_subtract_value(IndexRangeValueAction):
    """Subtracts the user specified value from the data (AND with $ff if
    necessary). Note the difference between this and `Subtract From`_"""
    cmd = commands.SubtractValueCommand


class byte_subtract_from(IndexRangeValueAction):
    """Subtracts the data from the user specified value (AND with $ff if
    necessary). Note the difference between this and `Subtract`_"""
    cmd = commands.SubtractFromCommand


class byte_multiply_by(IndexRangeValueAction):
    """Multiply the data from the user specified value (AND with $ff if
    necessary)."""
    cmd = commands.MultiplyCommand


class byte_divide_by(IndexRangeValueAction):
    """Divides the data by the user specified value by the data, ignoring the
    remainder. Note the difference between this and `Divide From`_"""
    cmd = commands.DivideByCommand


class byte_divide_from(IndexRangeValueAction):
    """Divides the data from the user specified value (that is to say: dividing
    the user specified value by the data), ignoring the remainder. Note the
    difference between this and `Divide By`_"""
    cmd = commands.DivideFromCommand


class byte_reverse_selection(IndexRangeAction):
    """Reverses the order of bytes in the selection"""
    cmd = commands.ReverseSelectionCommand


class byte_reverse_group(IndexRangeValueAction):
    prompt = "Enter number of bytes in each group: (default hex, prefix with # for decimal, %% for binary)"
    cmd = commands.ReverseGroupCommand
