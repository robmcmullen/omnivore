""" Action definitions for ByteEdit task

"""
import os
import sys

import wx
import wx.lib.dialogs

# Enthought library imports.
from traits.api import Any, Int

from omnivore.framework.enthought_api import EditorAction, NameChangeAction, TaskDynamicSubmenuGroup

from . import commands
from omnivore8bit.arch.ui.antic_colors import AnticColorDialog
from omnivore.utils.wx.dialogs import prompt_for_hex, prompt_for_dec, prompt_for_string, get_file_dialog_wildcard, ListReorderDialog
from omnivore8bit.ui.dialogs import prompt_for_emulator, prompt_for_assembler
from omnivore8bit.arch.machine import Machine

if sys.platform == "darwin":
    RADIO_STYLE = "toggle"
else:
    RADIO_STYLE = "radio"

import logging
log = logging.getLogger(__name__)


class ViewerAction(EditorAction):
    @property
    def viewer(self):
        return self.task.active_editor.focused_viewer

    @property
    def linked_base(self):
        return self.task.active_editor.focused_viewer.linked_base

    def _update_enabled(self, ui_state):
        if self.enabled_name and ui_state:
            enabled = bool(self._get_attr(self.viewer, self.enabled_name, None))
            if enabled is None:
                log.warning("%s flag does not exist in ui_state object %s" % (self.enabled_name, ui_state))
                enabled = False
            self.enabled = enabled
        else:
            self.enabled = True



class FontChoiceGroup(TaskDynamicSubmenuGroup):
    """Dynamic menu group to display the available fonts
    """
    #### 'DynamicSubmenuGroup' interface ######################################

    event_name = 'machine_menu_changed'

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self, event_data=None):
        items = []
        if event_data is not None:
            for font in event_data.font_list:
                action = UseFontAction(font=font)
                items.append(ActionItem(action=action))

        return items


class UseFontAction(ViewerAction):
    font = Any
    enabled_name = 'has_font'

    def _name_default(self):
        return "%s" % (self.font['name'])

    def perform(self, event):
        self.viewer.machine.set_font(self.font)


class LoadFontAction(ViewerAction):
    name = 'Load Font...'

    def perform(self, event):
        path = event.task.prompt_local_file_dialog("Load Font")
        if path is not None:
            self.viewer.machine.load_font(event.task, path)

# Assembler syntax section

class AssemblerChoiceGroup(TaskDynamicSubmenuGroup):
    """Dynamic menu group to display the available assemblers used to display
    the disassembly syntax
    """
    #### 'DynamicSubmenuGroup' interface ######################################

    event_name = 'machine_menu_changed'

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self, event_data=None):
        items = []
        if event_data is not None:
            for asm in event_data.assembler_list:
                action = UseAssemblerAction(assembler=asm)
                items.append(ActionItem(action=action))

        return items


class UseAssemblerAction(ViewerAction):
    style = RADIO_STYLE
    enabled_name = 'has_cpu'

    assembler = Any

    def _name_default(self):
        return "%s" % (self.assembler['name'])

    def perform(self, event):
        self.linked_base.clear_disassembly(self.viewer.machine)
        self.viewer.machine.set_assembler(self.assembler)

    def _update_checked(self, ui_state):
        self.checked = self.viewer.machine.assembler == self.assembler


class AddNewAssemblerAction(ViewerAction):
    """Add the syntax characteristics for a new assembler.

    """
    name = 'Add New Assembler...'

    def perform(self, event):
        d = prompt_for_assembler(event.task.window.control, "New Assembler")
        if d:
            self.viewer.machine.add_assembler(event.task, d)


class EditAssemblersAction(ViewerAction):
    """Modify the list of assemblers, rearranging the order or editing
    the characteristics of existing assemlers.

    """
    name = 'Edit Assemblers...'

    def perform(self, event):
        items = Machine.assembler_list
        dlg = ListReorderDialog(event.task.window.control, Machine.assembler_list, lambda a:a['name'], prompt_for_assembler, "Manage Assemblers")
        if dlg.ShowModal() == wx.ID_OK:
            asms = dlg.get_items()
            Machine.set_assembler_list(event.task, asms)
            self.viewer.machine.verify_current_assembler()
        dlg.Destroy()


class SetSystemDefaultAssemblerAction(ViewerAction):
    """Mark an assembler that will become the default for future
    editing sessions.

    """
    name = 'Set Current as System Default'

    def perform(self, event):
        Machine.set_system_default_assembler(event.task, self.viewer.machine.assembler)


class FontRendererAction(ViewerAction):
    """This submenu contains a list of all available font renderers. Selecting
    an item in this list will change how the text is displayed in the character
    map window.
    """
    doc_hint = "parent,list"
    submenu_of = "Character Display Modes"
    # Traits
    style = RADIO_STYLE
    enabled_name = 'has_font'

    font_renderer = Any

    def _name_default(self):
        return self.font_renderer.name

    def perform(self, event):
        self.viewer.machine.set_font(font_renderer=self.font_renderer)

    def _update_checked(self, ui_state):
        self.checked = self.viewer.machine.font_renderer == self.font_renderer


class FontMappingAction(ViewerAction):
    """This submenu contains a list of all available character mappings. Most
    platforms use a regular ASCII mapping, but some like the Atari 8-bits have
    different character mappings depending on the usage: the ANTIC mapping if
    looking at screen memory and the ATASCII mapping for normal usage.
    """
    doc_hint = "parent,list"
    submenu_of = "Character Mappings"
    # Traits
    style = RADIO_STYLE
    enabled_name = 'has_font'

    font_mapping = Any

    def _name_default(self):
        return self.font_mapping.name

    def perform(self, event):
        self.viewer.machine.set_font_mapping(self.font_mapping)

    def _update_checked(self, ui_state):
        self.checked = self.viewer.machine.font_mapping == self.font_mapping


class BitmapRendererAction(ViewerAction):
    """This submenu contains a list of all available bitmap renderers.
    Selecting an item in this list will change the rendering of the graphics
    display.
    """
    doc_hint = "parent,list"
    # Traits
    style = RADIO_STYLE
    enabled_name = 'has_bitmap'

    bitmap_renderer = Any

    def _name_default(self):
        return self.bitmap_renderer.name

    def perform(self, event):
        self.viewer.machine.set_bitmap_renderer(self.bitmap_renderer)

    def _update_checked(self, ui_state):
        self.checked = self.viewer.machine.bitmap_renderer == self.bitmap_renderer


class ViewerWidthAction(ViewerAction):
    """Set the number of items per row of the bitmap display. The width can
    mean different things for different viewers (i.e. bitmap widths are in
    bytes, not pixels), so prompt is based on the viewer.
    """
    name = "Width"
    enabled_name = 'has_width'

    def perform(self, event):
        e = self.active_editor
        v = e.focused_viewer
        val = prompt_for_dec(e.window.control, 'Enter new %s' % v.width_text, 'Set Width', v.width)
        if val is not None and val > 0:
            v.set_width(val)


class ViewerZoomAction(ViewerAction):
    """Set the zoom factor of the viewer, if applicable. This is an integer
    value greater than zero that scales the display size of each item.
    """
    name = "Zoom"
    enabled_name = 'has_zoom'

    def perform(self, event):
        e = self.active_editor
        v = e.focused_viewer
        val = prompt_for_dec(e.window.control, 'Enter new %s' % v.zoom_text, 'Set Zoom', v.zoom)
        if val is not None and val > 0:
            v.set_zoom(val)


class AnticColorAction(ViewerAction):
    """Open a window to choose the color palette from the available colors
    of the ANTIC processor.
    """
    name = 'Use ANTIC Colors...'
    enabled_name = 'has_colors'

    def perform(self, event):
        e = self.active_editor
        dlg = AnticColorDialog(event.task.window.control, e.machine.antic_color_registers)
        if dlg.ShowModal() == wx.ID_OK:
            e.machine.update_colors(dlg.colors)


class UseColorsAction(ViewerAction):
    """Changes the color palette to {name}
    """
    name = 'Use Colors'
    colors = Any
    enabled_name = 'has_colors'

    def perform(self, event):
        self.viewer.machine.update_colors(self.colors)


class ColorStandardAction(ViewerAction):
    """This list sets the color encoding standard for all bitmapped graphics of
    the disk image. Currently supported are:
    """
    doc_hint = "parent,list"
    style = RADIO_STYLE
    enabled_name = 'has_colors'

    color_standard = Int

    def perform(self, event):
        self.viewer.machine.set_color_standard(self.color_standard)

    def _update_checked(self, ui_state):
        self.checked = self.viewer.machine.color_standard == self.color_standard


class TextFontAction(ViewerAction):
    """Open a font selection window to choose the font and size used to display
    the values in the hex grid and the disassembly text.
    """
    name = 'Text Font...'
    enabled_name = 'has_text_font'

    def perform(self, event):
        v = self.viewer
        data = wx.FontData()
        data.EnableEffects(True)
        data.SetColour(v.machine.text_color)
        data.SetInitialFont(v.machine.text_font)
        dlg = wx.FontDialog(self.active_editor.control, data)
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetFontData()
            font = data.GetChosenFont()
            v.machine.set_text_font(font, data.GetColour())
            prefs = self.active_editor.task.preferences
            prefs.text_font = font
            self.editor.rebuild_ui()


class PredefinedMachineAction(ViewerAction):
    """These are built-in machine definitions that store preset values for
    `Processor`_, `Memory Map`_, `Colors`_, `Font`_, `Character Display`_ and
    `Bitmap Display`_.

    Currently defined machine types are:
    """
    doc_hint = "parent,list"
    # Traits
    style = RADIO_STYLE

    machine = Any

    def _name_default(self):
        return self.machine.name

    def perform(self, event):
        self.viewer.set_machine(self.machine)

    def _update_checked(self, ui_state):
        self.checked = self.viewer.machine == self.machine


class ProcessorTypeAction(ViewerAction):
    """The processor type defines the opcodes displayed in the disassembly
    window and those understood by the mini-assembler.

    Currently supported processors are:
    """
    doc_hint = "parent,list"
    # Traits
    style = RADIO_STYLE
    enabled_name = 'has_cpu'

    disassembler = Any

    def _name_default(self):
        return self.disassembler.name

    def perform(self, event):
        log.debug("setting disassembler to: %s" % self.disassembler.name)
        self.viewer.machine.set_disassembler(self.disassembler)

    def _update_checked(self, ui_state):
        self.checked = self.viewer.machine.disassembler == self.disassembler


class MemoryMapAction(ViewerAction):
    """In the disassembly window, target addresses for jumps, branches, loads,
    stores, compares, etc. can be replaced by text labels that are defined for
    the particular platform. For example, on the Atari 8-bit platform,
    occurrences of ``$E459`` will be replaced by ``SIOV``.

    Some platforms like the Atari 8-bits have hardware locations that perform
    different functions depending on whether it is read from or written to. The
    disassembler can handle this, so reading the location ``$D000`` will show
    the label ``M0PF`` (missile 0 to playfield collisions) while writing will
    show ``HPOSP0`` (set the horizontal position of player 0).

    Currently supported platforms are:
    """
    doc_hint = "parent,list"
    # Traits
    style = RADIO_STYLE
    enabled_name = 'has_cpu'

    memory_map = Any

    def _name_default(self):
        return self.memory_map.name

    def perform(self, event):
        self.viewer.set_memory_map(self.memory_map)

    def _update_checked(self, ui_state):
        self.checked = self.viewer.machine.memory_map == self.memory_map


class IndexRangeAction(ViewerAction):
    """base class for byte modification operations
    """
    doc_hint = "parent,list,level 3"
    parent_doc = """The commands in this menu operate on the current selection to change the byte values to:
    """
    cmd = None
    enabled_name = 'has_editable_bytes'

    def _name_default(self):
        return self.cmd.pretty_name

    def get_cmd(self, editor, segment, ranges):
        return self.cmd(segment, ranges)

    def perform(self, event):
        e = self.active_editor
        ranges = self.viewer.control.get_selected_ranges(self.linked_base)
        cmd = self.get_cmd(e, e.segment, ranges)
        e.process_command(cmd)


class ZeroAction(IndexRangeAction):
    """Set to zero"""
    cmd = commands.ZeroCommand
    accelerator = 'Ctrl+0'


class FFAction(IndexRangeAction):
    """Set to $ff"""
    cmd = commands.FFCommand
    accelerator = 'Ctrl+9'


class NOPAction(IndexRangeAction):
    """Set to the NOP command of the current processor"""
    cmd = commands.NOPCommand
    accelerator = 'Ctrl+3'
    enabled_name = 'has_cpu'

    def get_cmd(self, editor, segment, ranges):
        nop = self.viewer.machine.get_nop()
        return self.cmd(segment, ranges, nop)


class SetHighBitAction(IndexRangeAction):
    """Or with $80"""
    cmd = commands.SetHighBitCommand


class ClearHighBitAction(IndexRangeAction):
    """And with $7f"""
    cmd = commands.ClearHighBitCommand


class BitwiseNotAction(IndexRangeAction):
    """Invert every bit in each byte"""
    cmd = commands.BitwiseNotCommand
    accelerator = 'Ctrl+1'


class LeftShiftAction(IndexRangeAction):
    """Shift bits left (multiply by 2), inserting zeros in the low bit"""
    cmd = commands.LeftShiftCommand


class RightShiftAction(IndexRangeAction):
    """Shift bits right (divide by 2), inserting zeros in the high bit"""
    cmd = commands.RightShiftCommand


class LeftRotateAction(IndexRangeAction):
    """Shift bits left where the high bit wraps around to become the new low bit"""
    cmd = commands.LeftRotateCommand
    accelerator = 'Ctrl+<'


class RightRotateAction(IndexRangeAction):
    """Shift bits right where the low bit wraps around to become the new high bit"""
    cmd = commands.RightRotateCommand
    accelerator = 'Ctrl+>'


class ReverseBitsAction(IndexRangeAction):
    """Reverse the bit pattern of each byte; e.g. $c0 or 11000000 in binary becomes 00000011 in binary, $03 in hex"""
    cmd = commands.ReverseBitsCommand


class RandomBytesAction(IndexRangeAction):
    """Generate random bytes to replace the selected data"""
    cmd = commands.RandomBytesCommand


class IndexRangeValueAction(IndexRangeAction):
    prompt = "Enter byte value: (default hex, prefix with # for decimal, %% for binary)"

    def _name_default(self):
        return self.cmd.pretty_name + "..."

    def show_dialog(self):
        value = prompt_for_hex(self.viewer.control, self.prompt, self.cmd.pretty_name)
        if value is not None:
            cmd = self.cmd(self.linked_base.segment, self.linked_base.selected_ranges, value)
            self.active_editor.process_command(cmd)

    def perform(self, event):
        wx.CallAfter(self.show_dialog)

    def _update_enabled(self, ui_state):
        # Setting a range of values don't make sense for a single byte
        # location, so require it to have an actual range
        return self.viewer.has_editable_bytes and self.linked_base.has_selection


class SetValueAction(IndexRangeValueAction):
    """Prompts the user and sets the data to the specified value"""
    cmd = commands.SetValueCommand


class OrWithAction(IndexRangeValueAction):
    """Logical OR the selected data with the user specified value"""
    cmd = commands.OrWithCommand
    accelerator = 'Ctrl+\\'


class AndWithAction(IndexRangeValueAction):
    """Logical AND the selected data with the user specified value"""
    cmd = commands.AndWithCommand
    accelerator = 'Ctrl+7'


class XorWithAction(IndexRangeValueAction):
    """Logical XOR the selected data with the user specified value"""
    cmd = commands.XorWithCommand
    accelerator = 'Ctrl+6'


class RampUpAction(IndexRangeValueAction):
    """Starting with the user specified value at the first selected byte, loops
    over each byte in the selection and adds one to the value of the previous
    byte. At $ff, it wraps around to $00.
    """
    cmd = commands.RampUpCommand


class RampDownAction(IndexRangeValueAction):
    """Starting with the user specified value at the first selected byte, loops
    over each byte in the selection and subtracts one from the value of the
    previous byte. At $00, it wraps around to $ff.
    """
    cmd = commands.RampDownCommand


class AddValueAction(IndexRangeValueAction):
    """Adds the user specified value to the data, performing a logical AND with
    $ff if necessary to keep all values in the 8-bit range."""
    cmd = commands.AddValueCommand
    accelerator = 'Ctrl+='


class SubtractValueAction(IndexRangeValueAction):
    """Subtracts the user specified value from the data (AND with $ff if
    necessary). Note the difference between this and `Subtract From`_"""
    cmd = commands.SubtractValueCommand
    accelerator = 'Ctrl+-'


class SubtractFromAction(IndexRangeValueAction):
    """Subtracts the data from the user specified value (AND with $ff if
    necessary). Note the difference between this and `Subtract`_"""
    cmd = commands.SubtractFromCommand
    accelerator = 'Shift+Ctrl+-'


class MultiplyAction(IndexRangeValueAction):
    """Multiply the data from the user specified value (AND with $ff if
    necessary)."""
    cmd = commands.MultiplyCommand
    accelerator = 'Ctrl+8'


class DivideByAction(IndexRangeValueAction):
    """Divides the data by the user specified value by the data, ignoring the
    remainder. Note the difference between this and `Divide From`_"""
    cmd = commands.DivideByCommand
    accelerator = 'Ctrl+/'


class DivideFromAction(IndexRangeValueAction):
    """Divides the data from the user specified value (that is to say: dividing
    the user specified value by the data), ignoring the remainder. Note the
    difference between this and `Divide By`_"""
    cmd = commands.DivideFromCommand
    accelerator = 'Shift+Ctrl+/'


class ReverseSelectionAction(IndexRangeAction):
    """Reverses the order of bytes in the selection"""
    cmd = commands.ReverseSelectionCommand


class ReverseGroupAction(IndexRangeValueAction):
    prompt = "Enter number of bytes in each group: (default hex, prefix with # for decimal, %% for binary)"
    cmd = commands.ReverseGroupCommand
