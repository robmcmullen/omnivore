""" Action definitions for HexEdit task

"""
import os
import sys

import wx
import wx.lib.dialogs

# Enthought library imports.
from traits.api import on_trait_change, Any, Int, Bool
from pyface.api import YES, NO
from pyface.action.api import Action, ActionItem
from pyface.tasks.action.api import TaskAction, EditorAction

from atrcopy import user_bit_mask, data_style, add_xexboot_header, add_atr_header, BootDiskImage, SegmentData, interleave_segments, get_xex

from omnivore.framework.actions import *
from commands import *
from omnivore8bit.arch.disasm import ANTIC_DISASM, JUMPMAN_LEVEL, JUMPMAN_HARVEST, UNINITIALIZED_DATA
from omnivore8bit.arch.ui.antic_colors import AnticColorDialog
from omnivore.utils.wx.dialogs import prompt_for_hex, prompt_for_dec, prompt_for_string, get_file_dialog_wildcard, ListReorderDialog
from omnivore8bit.ui.dialogs import prompt_for_emulator, prompt_for_assembler, SegmentOrderDialog, SegmentInterleaveDialog
from omnivore8bit.arch.machine import Machine
from omnivore8bit.document import SegmentedDocument
from omnivore.framework.minibuffer import *
from omnivore.utils.textutil import parse_int_label_dict
from omnivore.utils.nputil import count_in_range
from omnivore.utils.jsonutil import dict_to_list

if sys.platform == "darwin":
    RADIO_STYLE = "toggle"
else:
    RADIO_STYLE = "radio"


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


class UseFontAction(EditorAction):
    font = Any

    def _name_default(self):
        return "%s" % (self.font['name'])

    def perform(self, event):
        self.active_editor.machine.set_font(self.font)


class LoadFontAction(EditorAction):
    name = 'Load Font...'

    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control)
        if dialog.open() == OK:
            self.active_editor.machine.load_font(event.task, dialog.path)


class GetFontFromSelectionAction(EditorAction):
    name = 'Get Font From Selection'
    enabled_name = 'grid_range_selected'

    def perform(self, event):
        self.active_editor.get_font_from_selection()


class EmulatorChoiceGroup(TaskDynamicSubmenuGroup):
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
            for emu in event_data.emulator_list:
                action = UseEmulatorAction(emulator=emu)
                items.append(ActionItem(action=action))

        return items


class UseEmulatorAction(EditorAction):
    """This submenu contains a list of the known emulators and a checkbox
    to indicate the current emulator.

    """
    doc_hint = "parent"
    style = RADIO_STYLE
    emulator = Any

    def _name_default(self):
        return "%s" % (self.emulator['name'])

    def perform(self, event):
        self.active_editor.document.set_emulator(self.emulator)

    @on_trait_change('active_editor.document')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.document.emulator == self.emulator


class AddNewEmulatorAction(EditorAction):
    """Open up a window to define a reference to an external emulator

    Omnivore can run the disk image in any emulator that is capable of being
    started from a command line. It spawns a separate process and feeds the
    emulator a path to the disk image along with any necessary command line
    arguments that you have to specify when setting up the emulator in this
    window.
    """
    name = 'Add New Emulator...'

    def perform(self, event):
        emu = prompt_for_emulator(event.task.window.control, "New Emulator")
        if emu:
            self.active_editor.machine.add_emulator(event.task, emu)


class EditEmulatorsAction(EditorAction):
    """Make changes to the current list of emulators.

    This opens a window with a list of the currently defined emulators
    to make changes to existing emulators or add/delete any already defined.
    """
    name = 'Edit Emulators...'

    def perform(self, event):
        dlg = ListReorderDialog(event.task.window.control, Machine.get_user_defined_emulator_list(), lambda a:a['name'], prompt_for_emulator, "Manage Emulators")
        if dlg.ShowModal() == wx.ID_OK:
            emus = dlg.get_items()
            Machine.set_user_defined_emulator_list(event.task, emus)
        dlg.Destroy()


class SetSystemDefaultEmulatorAction(EditorAction):
    """The currently specified emulator in the `Emulators`_ list will be set as
    the system default and remembered for subsequent editing sessions.
    """
    name = 'Set Current as System Default'

    def perform(self, event):
        Machine.set_system_default_emulator(event.task, self.active_editor.document.emulator)


class RunEmulatorAction(NameChangeAction):
    """Run the current emulator using the current emulator.

    The current emulator is shown in the `Emulators`_ sub-menu.
    """
    default_name = 'Run Emulator'
    name = default_name
    accelerator = 'F5'
    menu_item_name = 'emulator_label'

    def perform(self, event):
        self.active_editor.run_emulator()


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


class UseAssemblerAction(EditorAction):
    style = RADIO_STYLE
    assembler = Any

    def _name_default(self):
        return "%s" % (self.assembler['name'])

    def perform(self, event):
        self.active_editor.machine.set_assembler(self.assembler)

    @on_trait_change('active_editor.machine.assembler')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.machine.assembler == self.assembler


class AddNewAssemblerAction(EditorAction):
    """Add the syntax characteristics for a new assembler.

    """
    name = 'Add New Assembler...'

    def perform(self, event):
        d = prompt_for_assembler(event.task.window.control, "New Assembler")
        if d:
            self.active_editor.machine.add_assembler(event.task, d)


class EditAssemblersAction(EditorAction):
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
            self.active_editor.machine.verify_current_assembler()
        dlg.Destroy()


class SetSystemDefaultAssemblerAction(EditorAction):
    """Mark an assembler that will become the default for future
    editing sessions.

    """
    name = 'Set Current as System Default'

    def perform(self, event):
        Machine.set_system_default_assembler(event.task, self.active_editor.machine.assembler)


class FontRendererAction(EditorAction):
    """This submenu contains a list of all available font renderers. Selecting
    an item in this list will change how the text is displayed in the character
    map window.
    """
    doc_hint = "parent,list"
    submenu_of = "Character Display Modes"
    # Traits
    style = RADIO_STYLE

    font_renderer = Any

    def _name_default(self):
        return self.font_renderer.name

    def perform(self, event):
        self.active_editor.machine.set_font(font_renderer=self.font_renderer)

    @on_trait_change('active_editor.machine.font_renderer')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.machine.font_renderer == self.font_renderer


class FontMappingAction(EditorAction):
    """This submenu contains a list of all available character mappings. Most
    platforms use a regular ASCII mapping, but some like the Atari 8-bits have
    different character mappings depending on the usage: the ANTIC mapping if
    looking at screen memory and the ATASCII mapping for normal usage.
    """
    doc_hint = "parent,list"
    submenu_of = "Character Mappings"
    # Traits
    style = RADIO_STYLE

    font_mapping = Any

    def _name_default(self):
        return self.font_mapping.name

    def perform(self, event):
        self.active_editor.machine.set_font_mapping(self.font_mapping)

    @on_trait_change('active_editor.machine.font_mapping')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.machine.font_mapping == self.font_mapping


class BitmapRendererAction(EditorAction):
    """This submenu contains a list of all available bitmap renderers.
    Selecting an item in this list will change the rendering of the graphics
    display.
    """
    doc_hint = "parent,list"
    # Traits
    style = RADIO_STYLE

    bitmap_renderer = Any

    def _name_default(self):
        return self.bitmap_renderer.name

    def perform(self, event):
        self.active_editor.machine.set_bitmap_renderer(self.bitmap_renderer)

    @on_trait_change('active_editor.machine.bitmap_renderer')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.machine.bitmap_renderer == self.bitmap_renderer


class BitmapWidthAction(EditorAction):
    """Set the number of bytes per row of the bitmap display, which in turn
    sets the width in pixels.
    """
    name = "Bitmap Width"

    def perform(self, event):
        e = self.active_editor
        width = prompt_for_dec(e.window.control, 'Enter new bitmap width in bytes', 'Set Bitmap Width', e.bitmap_width)
        if width is not None and width > 0:
            wx.CallAfter(e.set_bitmap_width, width)


class BitmapZoomAction(EditorAction):
    """Set the zoom factor of bitmap display. This is an integer value greater
    than zero that scales the display size of each pixel in the bitmap.
    """
    name = "Bitmap Zoom"

    def perform(self, event):
        e = self.active_editor
        width = prompt_for_dec(e.window.control, 'Enter new pixel zoom factor', 'Set Bitmap Zoom', e.bitmap_zoom)
        if width is not None and width > 0:
            wx.CallAfter(e.set_bitmap_zoom, width)


class FontMappingWidthAction(EditorAction):
    """Set the number of bytes per row of the character display.
    """
    name = "Map Width"

    def perform(self, event):
        e = self.active_editor
        width = prompt_for_dec(e.window.control, 'Enter new map width in bytes', 'Set Map Width', str(e.map_width))
        if width is not None and width > 0:
            wx.CallAfter(e.set_map_width, width)


class FontMappingZoomAction(EditorAction):
    """Set the zoom factor of font display. This is an integer value greater
    than zero that scales the display size of each character.
    """
    name = "Map Zoom"

    def perform(self, event):
        e = self.active_editor
        width = prompt_for_dec(e.window.control, 'Enter new pixel zoom factor', 'Set Map Zoom', e.map_zoom)
        if width is not None and width > 0:
            wx.CallAfter(e.set_map_zoom, width)


class AnticColorAction(EditorAction):
    """Open a window to choose the color palette from the available colors
    of the ANTIC processor.
    """
    name = 'Use ANTIC Colors...'

    def perform(self, event):
        e = self.active_editor
        dlg = AnticColorDialog(event.task.window.control, e.machine.antic_color_registers)
        if dlg.ShowModal() == wx.ID_OK:
            e.machine.update_colors(dlg.colors)


class UseColorsAction(EditorAction):
    """Changes the color palette to {name}
    """
    name = 'Use Colors'
    colors = Any

    def perform(self, event):
        self.active_editor.machine.update_colors(self.colors)


class ColorStandardAction(EditorAction):
    """This list sets the color encoding standard for all bitmapped graphics of
    the disk image. Currently supported are:
    """
    doc_hint = "parent,list"
    style = RADIO_STYLE

    color_standard = Int

    def perform(self, event):
        self.active_editor.machine.set_color_standard(self.color_standard)

    @on_trait_change('active_editor.machine.color_standard')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.machine.color_standard == self.color_standard


class TextFontAction(EditorAction):
    """Open a font selection window to choose the font and size used to display
    the values in the hex grid and the disassembly text.
    """
    name = 'Text Font...'

    def perform(self, event):
        e = self.active_editor
        data = wx.FontData()
        data.EnableEffects(True)
        data.SetColour(e.machine.text_color)
        data.SetInitialFont(e.machine.text_font)
        dlg = wx.FontDialog(self.active_editor.control, data)
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetFontData()
            font = data.GetChosenFont()
            e.machine.set_text_font(font, data.GetColour())
            prefs = e.task.preferences
            prefs.text_font = font
            e.reconfigure_panes()


class PredefinedMachineAction(EditorAction):
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
        self.active_editor.set_machine(self.machine)

    @on_trait_change('active_editor.machine')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.machine == self.machine


class ProcessorTypeAction(EditorAction):
    """The processor type defines the opcodes displayed in the disassembly
    window and those understood by the mini-assembler.

    Currently supported processors are:
    """
    doc_hint = "parent,list"
    # Traits
    style = RADIO_STYLE

    disassembler = Any

    def _name_default(self):
        return self.disassembler.name

    def perform(self, event):
        self.active_editor.machine.set_disassembler(self.disassembler)

    @on_trait_change('active_editor.machine.disassembler')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.machine.disassembler == self.disassembler


class MemoryMapAction(EditorAction):
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

    memory_map = Any

    def _name_default(self):
        return self.memory_map.name

    def perform(self, event):
        self.active_editor.machine.set_memory_map(self.memory_map)

    @on_trait_change('active_editor.machine.memory_map')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.machine.memory_map == self.memory_map


class CurrentSegmentParserAction(NameChangeAction):
    default_name = 'Current Disk Image'
    name = default_name
    enabled = False
    enabled_name = None
    menu_item_name = 'segment_parser_label'

    def perform(self, event):
        pass

    def _enabled_update(self):
        # override the lookup of the enabled_name trait and simply force it to
        # be disabled
        self.enabled = False


class SegmentParserAction(EditorAction):
    """Change the parser that generates segments from the disk image.
    """
    # Traits
    style = 'toggle'

    segment_parser = Any

    def _name_default(self):
        return self.segment_parser.menu_name

    def perform(self, event):
        self.active_editor.set_segment_parser(self.segment_parser)

    @on_trait_change('task.segments_changed')
    def _update_checked(self):
        if self.active_editor:
            new_state = self.active_editor.document.segment_parser.__class__ == self.segment_parser
            # workaround to force reset of state because sometimes the toggle
            # is not turned off otherwise
            self.checked = not new_state
            self.checked = new_state


class SegmentChoiceGroup(TaskDynamicSubmenuGroup):
    """Menu containing list of segments
    """
    #### 'DynamicSubmenuGroup' interface ######################################

    event_name = 'segments_changed'

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self, event_data=None):
        items = []
        if event_data is not None:
            for i, segment in enumerate(event_data):
                action = UseSegmentAction(segment=segment, segment_number=i, task=self.task, checked=False)
                log.debug("SegmentChoiceGroup: created %s for %s, num=%d" % (action, str(segment), i))
                items.append(ActionItem(action=action, parent=self))

        return items


class UseSegmentAction(EditorAction):
    """This submenu contains a list of all segments in the disk image.
    Selecting one of these items will change the view to the selected segment.
    """
    doc_hint = "parent"
    style = RADIO_STYLE

    segment = Any

    segment_number = Int

    def _name_default(self):
        return str(self.segment)

    def perform(self, event):
        self.active_editor.view_segment_number(self.segment_number)

    @on_trait_change('task.segment_selected')
    def _update_checked(self):
        if self.active_editor:
            state = self.active_editor.segment_number == self.segment_number
            log.debug("UseSegmentAction: checked=%s %s %s %s" % (state, str(self.segment), self.active_editor.segment_number, self.segment_number))
            self.checked = state


class ParseSubSegmentsAction(EditorAction):
    """Expand the segment into sub-segments using a parser.  The disk image
    parser only parses the first level of segments automatically, so if there
    are segments that can be further parsed, for instance an Atari DOS file
    containing executable files, the executable files will only show the main
    segment. To see the segments of the executable, you would use this command.
    """
    name = 'Show Sub-Segments'

    segment_number = Int

    def perform(self, event):
        e = self.active_editor
        s = e.document.segments[self.segment_number]
        parser = e.document.parse_sub_segments(s)
        if parser is not None:
            e.added_segment(s)


class SelectSegmentInAllAction(EditorAction):
    name = 'Select This Segment in All'

    segment_number = Int

    def perform(self, event):
        e = self.active_editor
        s = e.document.segments[self.segment_number]
        e.view_segment_number(0)
        e.select_none(False)
        s.set_style_ranges([(0, len(s))], selected=True)
        e.adjust_selection(s)
        e.index_clicked(e.anchor_start_index, 0, None)


class GetSegmentFromSelectionAction(EditorAction):
    """Create a new segment in the segment list using the current selection.

    All the bytes in the current selection will be shown in the new segment. If
    there are multiple selections, the new segment will show the bytes as
    contiguous but they will represent the original locations in the disk
    image.
    """
    name = 'New Segment From Selection'
    enabled_name = 'can_copy'

    def perform(self, event):
        e = self.active_editor
        text = prompt_for_string(e.window.control, "Enter segment name", "New Segment")
        if text is not None:
            segment, = e.get_segments_from_selection()
            if not text:
                text = "%04x-%04x" % (segment.start_addr, segment.start_addr + len(segment) - 1)
            segment.name = text
            e.add_user_segment(segment)


class MultipleSegmentsFromSelectionAction(EditorAction):
    """Create a set of segments from the current selection, given the desired
    length of the resulting segments. If the number of bytes in the selection
    is not an exact multiple of the specified length, the last segment created
    will contain the remaining bytes. It will not be padded with zeros.
    """
    name = 'Multiple Segments From Selection'
    enabled_name = 'can_copy'

    def perform(self, event):
        e = self.active_editor
        size = prompt_for_hex(e.window.control, "Enter number of bytes in each segment\n(default hex, prefix with # for decimal, %% for binary)", "Multiple Segments")
        if size is not None and size > 0:
            segments = e.get_segments_from_selection(size)
            for segment in segments:
                text = "%04x-%04x" % (segment.start_addr, segment.start_addr + len(segment) - 1)
                segment.name = text
                e.add_user_segment(segment, False)
            e.update_segments_ui()


class InterleaveSegmentsAction(EditorAction):
    name = 'Interleave Segments'
    tooltip = 'Create new segment by interleaving segments'

    def get_bytes(self, dlg):
        return dlg.get_bytes()

    def perform(self, event):
        e = self.active_editor
        dlg = SegmentInterleaveDialog(e.window.control, "Interleave Segments", e.document.segments[1:])
        if dlg.ShowModal() == wx.ID_OK:
            s = dlg.get_segments()
            factor = dlg.get_interleave()
            segment = interleave_segments(s, factor)
            e.add_user_segment(segment, False)
            e.update_segments_ui()
        dlg.Destroy()


class ExpandDocumentAction(EditorAction):
    name = 'Expand Disk Image'
    tooltip = 'Resize the document to add extra data at the end'
    enabled_name = 'can_resize_document'

    def perform(self, event):
        e = self.active_editor
        d = e.document
        s = d.expand_container(len(d) + 0x400)
        s.name = "Expanded %x bytes" % len(s)
        e.add_user_segment(s, False)
        e.find_segment(segment=s)
        e.update_segments_ui()


class MarkSelectionAsCodeAction(EditorAction):
    """Marks the selected bytes as valid code to be disassembled using the
    current processor definition.

    """
    name = 'Code'
    enabled_name = 'can_copy'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = s.get_style_ranges(selected=True)
        s.clear_style_ranges(ranges, data=True, user=1)
        e.document.change_count += 1
        e.metadata_dirty = True
        e.mark_index_range_changed(ranges[0])
        e.refresh_panes()


class MarkSelectionAsDataAction(EditorAction):
    """Marks the selected bytes as data, not to be disassembled but shown
    as byte values in the disassembly listing.

    """
    name = 'Data'
    enabled_name = 'can_copy'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = s.get_style_ranges(selected=True)
        s.clear_style_ranges(ranges, user=user_bit_mask)
        s.set_style_ranges(ranges, data=True)
        e.document.change_count += 1
        e.metadata_dirty = True
        # check if the segment can be merged with a previous data segment
        index = ranges[0][0]
        while index > 0 and (s.style[index-1] & user_bit_mask) == data_style:
            index -= 1
        e.mark_index_range_changed((index, ranges[0][1]))
        e.refresh_panes()


class CustomDisassemblerAction(EditorAction):
    name = '<custom>'
    enabled_name = 'can_copy'
    disassembly_type = 0

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = s.get_style_ranges(selected=True)
        s.clear_style_ranges(ranges, user=user_bit_mask)
        s.set_style_ranges(ranges, user=self.disassembly_type)
        e.document.change_count += 1
        e.metadata_dirty = True
        e.mark_index_range_changed(ranges[0])
        e.refresh_panes()


class MarkSelectionAsDisplayListAction(CustomDisassemblerAction):
    """Marks the selected bytes as an ANTIC display list, which will be shown
    as data in the disassembly listing. The data will be grouped by ANTIC
    command, where all bytes that belong to a command will be on a single line.
    This can result in a large number of data bytes appearing on one line when
    displaying a graphics 8 display list, for example. Exporting the
    disassembly will produce listings that break up these long lines into
    normal amounts, defaulting to 4 bytes on a line.
    """
    name = 'Display List'
    disassembly_type = ANTIC_DISASM


class MarkSelectionAsJumpmanLevelAction(CustomDisassemblerAction):
    """Marks the selected bytes as Jumpman drawing element descriptors. This is
    not used much for editing now that the `Jumpman Level Editor
    <omnivore.jumpman>`_ is available.
    """
    name = 'Jumpman Level Data'
    enabled_name = 'can_copy'
    disassembly_type = JUMPMAN_LEVEL


class MarkSelectionAsJumpmanHarvestAction(CustomDisassemblerAction):
    """Marks the selected bytes as a Jumpman harvest table. This is
    not used much for editing now that the `Jumpman Level Editor
    <omnivore.jumpman>`_ is available.
    """
    name = 'Jumpman Harvest Table'
    enabled_name = 'can_copy'
    disassembly_type = JUMPMAN_HARVEST


class MarkSelectionAsUninitializedDataAction(CustomDisassemblerAction):
    """Marks the selected bytes as unitialized data, skipping over those bytes
    and placing an ``origin`` directive in the disassembly that points to the
    next address that contains any other type of data.
    """
    name = 'Uninitialized Data'
    enabled_name = 'can_copy'
    disassembly_type = UNINITIALIZED_DATA


class ImportSegmentLabelsAction(EditorAction):
    """Imports a text file that defines labels and addresses.

    The text file should contain the address and the label on a single line.
    It's pretty generous about parsing the input; there are two major types recognized.

    The first is typical assembler format::

        <label> = <address>

    where the address can be in decimal without a prefix or in hex with the
    ``$`` or ``0x`` prefix.

    and the second is a line with a hex value first and the label following.
    Any line without an ``=`` character is parsed this way, such that the first
    thing that lookslike a hex or decimal number is used as the address, and
    the first thing after that that looks like a valid text string is used as
    the label. It can be comma separated, space separated, tab separated, etc;
    anything but ``=``.
    """
    name = 'Import Segment Labels'
    enabled_name = 'has_origin'

    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control, title="Import Segment Labels")
        if dialog.open() == OK:
            e = self.active_editor
            with open(dialog.path, "r") as fh:
                text = fh.read()
            d = parse_int_label_dict(text, allow_equals=True)
            s = e.segment
            start, end = s.start_addr, s.start_addr + len(s)
            below, above = count_in_range(d.keys(), start, end)
            if below + above > 0:
                msg = ""
                if below > 0:
                    msg += "\n%d below $%04x\n" % (below, start)
                if above > 0:
                    msg += "\n%d above $%04x\n" % (above, end)
                if not self.task.confirm("Some labels out of range.\n%s\nUse this set of labels anyway?" % msg, "Labels Out of Range"):
                    return
            cmd = SegmentMemoryMapCommand(s, d)
            e.process_command(cmd)


class ExportSegmentLabelsAction(EditorAction):
    """Exports a text file containing label/address pairs.

    The text file will have a format that can be included in most assemblers::

        <label> = $<hex address>

    for example::

        SIOV = $E459
        SETVBV = $E45C
    """
    name = 'Export Segment Labels'
    enabled_name = 'has_origin'

    include_disassembly_labels = Bool(False)

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        if s.memory_map or self.include_disassembly_labels:
            d = {}
            if self.include_disassembly_labels:
                d.update(e.disassembly.table.disassembler.label_dict)
            d.update(s.memory_map)
            tmp = dict_to_list(d)
            if tmp:
                dialog = FileDialog(parent=event.task.window.control, action="save as", title="Export Segment Labels")
                if dialog.open() == OK:
                    with open(dialog.path, "w") as fh:
                        fh.write("\n".join(["%s = $%04x" % (v, k) for k, v in tmp]) + "\n")
                    return
        e.task.status_bar.error = "No labels in segment"


class CopyDisassemblyAction(EditorAction):
    name = 'Copy Disassembly Text'
    enabled_name = 'can_copy'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = s.get_style_ranges(selected=True)
        lines = []
        try:
            for start, end in ranges:
                lines.extend(e.disassembly.get_disassembled_text(start, end))
        except IndexError:
            e.window.error("Disassembly tried to jump to an address outside this segment.")
            return
        text = os.linesep.join(lines) + os.linesep
        data_obj = wx.TextDataObject()
        data_obj.SetText(text)
        e.set_clipboard_object(data_obj)


class CopyAsReprAction(EditorAction):
    name = 'Copy as Escaped String'
    enabled_name = 'can_copy'

    def perform(self, event):
        e = self.active_editor
        ranges, indexes = e.get_selected_ranges_and_indexes()
        data = e.segment[indexes]
        s1 = repr(data.tostring())
        q = s1[0]
        text = s1[1:-1]  # remove leading/trailing quotes
        if q == "'":
            # double quotes are literal, single quotes are escaped
            text = text.replace('"', "\\x22").replace("\\'", "\\x27")
        else:
            # single quotes are literal, double are escaped
            text = text.replace("'", "\\x27").replace('\\"', "\\x22")
        data_obj = wx.TextDataObject()
        data_obj.SetText(text)
        e.set_clipboard_object(data_obj)


class CopyCommentsAction(EditorAction):
    name = 'Copy Disassembly Comments'
    enabled_name = 'can_copy'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = s.get_style_ranges(selected=True)
        lines = []
        for start, end in ranges:
            for _, _, _, comment, _ in e.disassembly.table.disassembler.iter_row_text(start, end):
                lines.append(comment)
        text = os.linesep.join(lines) + os.linesep
        data_obj = wx.TextDataObject()
        data_obj.SetText(text)
        e.set_clipboard_object(data_obj)


def prompt_for_comment(e, s, ranges, desc):
    existing = s.get_first_comment(ranges)
    text = prompt_for_string(e.window.control, desc, "Add Comment", existing)
    if text is not None:
        cmd = SetCommentCommand(s, ranges, text)
        e.process_command(cmd)


class AddCommentAction(EditorAction):
    name = 'Add Comment'
    accelerator = 'Alt+C'

    def is_range(self, event):
        return self.active_editor.can_copy

    def get_index(self, event):
        return self.active_editor.cursor_index

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        if self.is_range(event):
            ranges = s.get_style_ranges(selected=True)
            if len(ranges) == 1:
                desc = "Enter comment for first byte of range:\n%s" % e.get_label_of_first_byte(ranges)
            else:
                desc = "Enter comment for first byte of each range:\n%s" % e.get_label_of_first_byte(ranges)
        else:
            ranges = []
        if not ranges:
            index = self.get_index(event)
            ranges = [(index, index+1)]
            desc = "Enter comment for location %s" % index
        prompt_for_comment(e, s, ranges, desc)


class AddCommentPopupAction(AddCommentAction):
    name = 'Add Comment'

    def is_range(self, event):
        return event.popup_data["in_selection"]

    def get_index(self, event):
        return event.popup_data["index"]


class RemoveCommentAction(EditorAction):
    name = 'Remove Comment'
    accelerator = 'Shift+Alt+C'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        if e.can_copy:
            ranges = s.get_style_ranges(selected=True)
        else:
            index = e.cursor_index
            ranges = [(index, index+1)]
        if ranges:
            cmd = ClearCommentCommand(s, ranges)
            e.process_command(cmd)


class RemoveCommentPopupAction(EditorAction):
    name = 'Remove Comment'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        if event.popup_data["in_selection"]:
            ranges = s.get_style_ranges(selected=True)
        else:
            index = event.popup_data["index"]
            ranges = [(index, index+1)]
        if ranges:
            cmd = ClearCommentCommand(s, ranges)
            e.process_command(cmd)


def prompt_for_label(e, s, addr, desc):
    existing = s.memory_map.get(addr, "")
    text = prompt_for_string(e.window.control, desc, "Add Label", existing)
    if text is not None:
        cmd = SetLabelCommand(s, addr, text)
        e.process_command(cmd)


class AddLabelAction(EditorAction):
    name = 'Add Label'
    accelerator = 'Alt+L'
    enabled_name = 'has_origin'

    def get_ranges(self, editor, segment, event):
        if editor.can_copy:  # has selected ranges
            ranges = segment.get_style_ranges(selected=True)
        else:
            ranges = []
        return ranges

    def process(self, editor, segment, addr):
        desc = "Enter label for address $%04x" % addr
        prompt_for_label(editor, segment, addr, desc)

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = self.get_ranges(e, s, event)
        if ranges:
            index = ranges[0][0]
        else:
            index = e.cursor_index
        addr = index + s.start_addr
        self.process(e, s, addr)


class AddLabelPopupAction(AddLabelAction):
    def get_ranges(self, editor, segment, event):
        if event.popup_data["in_selection"]:
            ranges = segment.get_style_ranges(selected=True)
        else:
            index = event.popup_data["index"]
            ranges = [(index, index+1)]
        return ranges


class RemoveLabelAction(AddLabelAction):
    name = 'Remove Label'
    accelerator = 'Shift+Alt+L'

    def process(self, editor, segment, addr):
        existing = segment.memory_map.get(addr, "")
        if existing:
            cmd = ClearLabelCommand(segment, addr)
            editor.process_command(cmd)


class RemoveLabelPopupAction(RemoveLabelAction):
    def get_ranges(self, editor, segment, event):
        if event.popup_data["in_selection"]:
            ranges = segment.get_style_ranges(selected=True)
        else:
            index = event.popup_data["index"]
            ranges = [(index, index+1)]
        return ranges


class DeleteUserSegmentAction(EditorAction):
    name = 'Delete User Segment'
    segment_number = Int

    def perform(self, event):
        e = self.task.active_editor
        segment = e.document.segments[self.segment_number]
        if self.task.confirm("Delete user segment %s?" % segment.name, "Delete User Segment"):
            e.delete_user_segment(segment)


class SetSegmentOriginAction(EditorAction):
    name = 'Set Segment Origin'
    segment_number = Int

    def perform(self, event):
        e = self.active_editor
        segment = e.document.segments[self.segment_number]
        org = prompt_for_hex(e.window.control, "Enter origin address for %s\n(default hex, prefix with # for decimal, %% for binary)" % segment.name, "Set Segment Origin")
        if org is not None:
            cmd = SetSegmentOriginCommand(segment, org)
            e.process_command(cmd)


class SaveAsXEXAction(EditorAction):
    name = 'Export as XEX...'
    tooltip = 'Create executable from segments'
    title = 'Create Executable'
    file_ext = "xex"

    def get_document(self, dlg):
        segments = dlg.get_segments()
        root, segs = get_xex(segments)
        doc = SegmentedDocument.create_from_segments(root, segs)
        return doc

    def get_dialog(self, e):
        return SegmentOrderDialog(e.window.control, self.title, e.document.segments[1:])

    def perform(self, event):
        e = self.active_editor
        dlg = self.get_dialog(e)
        if dlg.ShowModal() == wx.ID_OK:
            doc = self.get_document(dlg)
            dialog = FileDialog(default_filename="test.%s" % self.file_ext, parent=e.window.control, action='save as')
            if dialog.open() == OK:
                self.active_editor.save(dialog.path, document=doc)
        dlg.Destroy()


class SaveAsXEXBootAction(SaveAsXEXAction):
    name = 'Export as Boot Disk...'
    tooltip = 'Create a bootable disk from segments'
    title = 'Create Boot Disk'
    file_ext = "atr"

    def get_bytes(self, dlg):
        xex = dlg.get_bytes()
        title, author = dlg.get_extra_text()[0:2]
        bytes = add_xexboot_header(xex, title=title, author=author)
        bytes = add_atr_header(bytes)
        rawdata = SegmentData(bytes)
        atr = BootDiskImage(rawdata)
        return atr.bytes.tostring()

    def get_dialog(self, e):
        return SegmentOrderDialog(e.window.control, self.title, e.document.segments[1:], "Segment Order for Boot Disk", True)


class SaveSegmentAsFormatAction(EditorAction):
    saver = Any

    segment_number = Int

    def _name_default(self):
        return "%s (%s)" % (self.saver.export_data_name, self.saver.export_extensions[0])

    def perform(self, event):
        segment = self.task.active_editor.document.segments[self.segment_number]
        dialog = FileDialog(default_filename=segment.name, parent=event.task.window.control, action='save as', wildcard=get_file_dialog_wildcard(self.saver.export_data_name, self.saver.export_extensions))
        if dialog.open() == OK:
            self.active_editor.save_segment(self.saver, dialog.path)


class SaveSegmentGroup(TaskDynamicSubmenuGroup):
    """ A menu for changing the active task in a task window.
    """
    id = 'SaveSegmentGroup'

    event_name = 'segment_selected'

    def _get_items(self, event_data=None):
        items = []
        if event_data is not None:
            segment_number = event_data
            segment = self.task.active_editor.document.segments[segment_number]
            savers = self.task.active_editor.get_extra_segment_savers(segment)
            savers.extend(segment.savers)
            for saver in savers:
                action = SaveSegmentAsFormatAction(saver=saver, segment_number=segment_number)
                items.append(ActionItem(action=action))
        return items


class GotoIndexAction(Action):
    addr_index = Int()

    segment_num = Int()

    def perform(self, event):
        e = self.active_editor
        if self.segment_num >= 0:
            e.view_segment_number(self.segment_num)
        e.index_clicked(self.addr_index, 0, None)


class SegmentGotoAction(EditorAction):
    name = "Goto Address..."
    accelerator = 'Alt+G'

    def perform(self, event):
        e = self.active_editor
        addr, error = prompt_for_hex(e.window.control, "Enter address value:\n(default hex; prefix with # for decimal)", "Goto Address in a Segment", return_error=True, default_base="hex")
        if addr is not None:
            s = e.segment
            index = addr - s.start_addr
            if e.segment.is_valid_index(index):
                e.index_clicked(index, 0, None)
                e.task.status_bar.message = e.get_label_at_index(index)
            else:
                segments = e.document.find_segments_in_range(addr)
                if len(segments) > 1:
                    segments = segments[1:] # Skip ALL segment if other segments exist
                if len(segments) == 0:
                    e.task.status_bar.message = "Address $%04x not valid in any segment" % addr
                else:
                    if len(segments) > 1:
                        segments = segments[1:] # Skip ALL segment if others are available
                    segment_num, segment, index = segments[0]
                    e.view_segment_number(segment_num)
                    e.index_clicked(index, 0, None)
                    e.task.status_bar.message = "%s in segment %s" % (e.get_label_at_index(index), e.segment.name)
        else:
            e.task.status_bar.message = error


class InsertFileAction(EditorAction):
    """Insert binary data at the cursor

    The data from the loaded file will overwrite data starting at the cursor,
    so it's not inserted in the text editor sense where space is created in the
    existing data.
    """
    name = 'Insert File...'

    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control)
        if dialog.open() == OK:
            e = self.active_editor
            cmd = InsertFileCommand(e.segment, e.cursor_index, dialog.path)
            e.process_command(cmd)


class IndexRangeAction(EditorAction):
    """base class for byte modification operations
    """
    doc_hint = "parent,list,level 3"
    parent_doc = """The commands in this menu operate on the current selection to change the byte values to:
    """
    enabled_name = 'can_copy'
    cmd = None

    def _name_default(self):
        return self.cmd.pretty_name

    def get_cmd(self, editor, segment, ranges):
        return self.cmd(segment, ranges)

    def perform(self, event):
        e = self.active_editor
        ranges = e.get_optimized_selected_ranges()
        cmd = self.get_cmd(e, e.segment, ranges)
        self.active_editor.process_command(cmd)


class ZeroAction(IndexRangeAction):
    """Set to zero"""
    cmd = ZeroCommand
    accelerator = 'Ctrl+0'


class FFAction(IndexRangeAction):
    """Set to $ff"""
    cmd = FFCommand
    accelerator = 'Ctrl+9'


class NOPAction(IndexRangeAction):
    """Set to the NOP command of the current processor"""
    cmd = NOPCommand
    accelerator = 'Ctrl+3'

    def get_cmd(self, editor, segment, ranges):
        nop = editor.machine.get_nop()
        return self.cmd(segment, ranges, nop)


class SetHighBitAction(IndexRangeAction):
    """Or with $80"""
    cmd = SetHighBitCommand


class ClearHighBitAction(IndexRangeAction):
    """And with $7f"""
    cmd = ClearHighBitCommand


class BitwiseNotAction(IndexRangeAction):
    """Invert every bit in each byte"""
    cmd = BitwiseNotCommand
    accelerator = 'Ctrl+1'


class LeftShiftAction(IndexRangeAction):
    """Shift bits left (multiply by 2), inserting zeros in the low bit"""
    cmd = LeftShiftCommand


class RightShiftAction(IndexRangeAction):
    """Shift bits right (divide by 2), inserting zeros in the high bit"""
    cmd = RightShiftCommand


class LeftRotateAction(IndexRangeAction):
    """Shift bits left where the high bit wraps around to become the new low bit"""
    cmd = LeftRotateCommand
    accelerator = 'Ctrl+<'


class RightRotateAction(IndexRangeAction):
    """Shift bits right where the low bit wraps around to become the new high bit"""
    cmd = RightRotateCommand
    accelerator = 'Ctrl+>'


class ReverseBitsAction(IndexRangeAction):
    """Reverse the bit pattern of each byte; e.g. $c0 or 11000000 in binary becomes 00000011 in binary, $03 in hex"""
    cmd = ReverseBitsCommand


class IndexRangeValueAction(IndexRangeAction):
    def _name_default(self):
        return self.cmd.pretty_name + "..."

    def show_dialog(self, e):
        value = prompt_for_hex(e.window.control, "Enter byte value: (default hex, prefix with # for decimal, %% for binary)", self.cmd.pretty_name)
        if value is not None:
            cmd = self.cmd(e.segment, e.selected_ranges, value)
            self.active_editor.process_command(cmd)

    def perform(self, event):
        wx.CallAfter(self.show_dialog, self.active_editor)


class SetValueAction(IndexRangeValueAction):
    """Prompts the user and sets the data to the specified value"""
    cmd = SetValueCommand


class OrWithAction(IndexRangeValueAction):
    """Logical OR the selected data with the user specified value"""
    cmd = OrWithCommand
    accelerator = 'Ctrl+\\'


class AndWithAction(IndexRangeValueAction):
    """Logical AND the selected data with the user specified value"""
    cmd = AndWithCommand
    accelerator = 'Ctrl+7'


class XorWithAction(IndexRangeValueAction):
    """Logical XOR the selected data with the user specified value"""
    cmd = XorWithCommand
    accelerator = 'Ctrl+6'


class RampUpAction(IndexRangeValueAction):
    """Starting with the user specified value at the first selected byte, loops
    over each byte in the selection and adds one to the value of the previous
    byte. At $ff, it wraps around to $00.
    """
    cmd = RampUpCommand


class RampDownAction(IndexRangeValueAction):
    """Starting with the user specified value at the first selected byte, loops
    over each byte in the selection and subtracts one from the value of the
    previous byte. At $00, it wraps around to $ff.
    """
    cmd = RampDownCommand


class AddValueAction(IndexRangeValueAction):
    """Adds the user specified value to the data, performing a logical AND with
    $ff if necessary to keep all values in the 8-bit range."""
    cmd = AddValueCommand
    accelerator = 'Ctrl+='


class SubtractValueAction(IndexRangeValueAction):
    """Subtracts the user specified value from the data (AND with $ff if
    necessary). Note the difference between this and `Subtract From`_"""
    cmd = SubtractValueCommand
    accelerator = 'Ctrl+-'


class SubtractFromAction(IndexRangeValueAction):
    """Subtracts the data from the user specified value (AND with $ff if
    necessary). Note the difference between this and `Subtract`_"""
    cmd = SubtractFromCommand
    accelerator = 'Shift+Ctrl+-'


class MultiplyAction(IndexRangeValueAction):
    """Multiply the data from the user specified value (AND with $ff if
    necessary)."""
    cmd = MultiplyCommand
    accelerator = 'Ctrl+8'


class DivideByAction(IndexRangeValueAction):
    """Divides the data by the user specified value by the data, ignoring the
    remainder. Note the difference between this and `Divide From`_"""
    cmd = DivideByCommand
    accelerator = 'Ctrl+/'


class DivideFromAction(IndexRangeValueAction):
    """Divides the data from the user specified value (that is to say: dividing
    the user specified value by the data), ignoring the remainder. Note the
    difference between this and `Divide By`_"""
    cmd = DivideFromCommand
    accelerator = 'Shift+Ctrl+/'


class PasteAndRepeatAction(EditorAction):
    name = 'Paste and Repeat'
    accelerator = 'Shift+Ctrl+V'
    tooltip = 'Paste and repeat clipboard data until current selection is filled'
    enabled_name = 'can_paste'

    def perform(self, event):
        self.active_editor.paste(PasteAndRepeatCommand)


class PasteCommentsAction(EditorAction):
    name = 'Paste Comments'
    tooltip = 'Paste text as comment lines'
    enabled_name = 'can_paste'
    accelerator = 'F6'

    def perform(self, event):
        self.active_editor.paste(PasteCommentsCommand)


class FindAction(EditorAction):
    name = 'Find'
    accelerator = 'Ctrl+F'
    tooltip = 'Find bytes or characters in the raw data or in disassembly comments'

    def perform(self, event):
        e = self.active_editor
        event.task.show_minibuffer(NextPrevTextMinibuffer(e, FindAllCommand, FindNextCommand, FindPrevCommand, initial=e.last_search_settings["find"]))


class FindNextAction(EditorAction):
    name = 'Find Next'
    accelerator = 'Ctrl+G'
    tooltip = 'Find next match'

    def perform(self, event):
        e = self.active_editor
        event.task.show_minibuffer(NextPrevTextMinibuffer(e, FindAllCommand, FindNextCommand, FindPrevCommand, next_match=True, initial=e.last_search_settings["find"]))


class FindPrevAction(EditorAction):
    name = 'Find Previous'
    accelerator = 'Shift+Ctrl+G'
    tooltip = 'Find previous match'

    def perform(self, event):
        e = self.active_editor
        event.task.show_minibuffer(NextPrevTextMinibuffer(e, FindAllCommand, FindNextCommand, FindPrevCommand, prev_match=True, initial=e.last_search_settings["find"]))


class FindAlgorithmAction(EditorAction):
    name = 'Find Using Expression'
    accelerator = 'Alt+Ctrl+F'
    tooltip = 'Find bytes using logical and arithmetic comparisons'

    def perform(self, event):
        e = self.active_editor
        event.task.show_minibuffer(NextPrevTextMinibuffer(e, FindAlgorithmCommand, FindNextCommand, FindPrevCommand, initial=e.last_search_settings["algorithm"], help_text=" Use variable 'a' for address, 'b' for byte values. (Mouse over for examples)", help_tip="Examples:\n\nAll bytes after the 10th byte: a > 10\n\nBytes with values > 128 but only after the 10th byte: (b > 128) & (a > 10)\n\n"))


class FindToSelectionAction(EditorAction):
    name = 'Find to Selection'
    accelerator = 'Alt+Ctrl+A'
    tooltip = 'Convert all matched locations to multi-selection'

    def perform(self, event):
        e = self.active_editor
        e.convert_ranges({'match':True}, {'selected':True})
        e.refresh_panes()
        event.task.on_hide_minibuffer_or_cancel(None)


class CancelMinibufferAction(EditorAction):
    name = 'Cancel Minibuffer or current edit'
    accelerator = 'ESC'
    tooltip = 'Remove minibuffer or cancel current edit'

    def perform(self, event):
        event.task.on_hide_minibuffer_or_cancel(None)


class ViewDiffHighlightAction(EditorAction):
    """Toggle whether differences to the `Baseline Data`_ are highlighted
    or not.

    """
    name = 'Show Baseline Differences'
    tooltip = 'Show bytes that are different than the baseline version'
    style = 'toggle'
    enabled_name = 'baseline_present'

    def perform(self, event):
        e = self.active_editor
        value = not e.diff_highlight
        e.diff_highlight = value
        if value:
            e.compare_to_baseline()
        else:
            e.document.clear_baseline()
        e.refresh_panes()

    @on_trait_change('active_editor.diff_highlight')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.diff_highlight


class LoadBaselineVersionAction(EditorAction):
    """Open a window to select a `Baseline Data`_ file.

    The absolute path to the baseline file is stored, so if the baseline file
    is moved to a new location you will have to use this command again to point
    to the new location.
    """
    name = 'Add Baseline Difference File...'
    tooltip = 'Add baseline file to be used to show differences in current version'

    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control)
        if dialog.open() == OK:
            e = self.active_editor
            e.load_baseline(dialog.path)
            e.compare_to_baseline()
            e.refresh_panes()


class RevertToBaselineAction(IndexRangeAction):
    """Restore the selection to the data contained in the `Baseline
    Data`_ file.
    """
    cmd = RevertToBaselineCommand
    enabled_name = 'can_copy_baseline'


class FindNextBaselineDiffAction(EditorAction):
    """Move the cursor to the next block of data that is different than
    the `Baseline Data`_ file.

    This will wrap around to the beginning of the segment if it doesn't find a
    difference before the end.
    """
    name = 'Find Next Difference'
    accelerator = 'Ctrl+D'
    tooltip = 'Find next difference to the baseline'
    enabled_name = 'diff_highlight'

    def perform(self, event):
        e = self.active_editor
        index = e.cursor_index
        new_index = e.segment.find_next(index, diff=True)
        if new_index is not None:
            e.index_clicked(new_index, 0, None)


class FindPrevBaselineDiffAction(EditorAction):
    """Move the cursor to the previous block of data that is different than
    the `Baseline Data`_ file.Data

    This will wrap around to the end of the segment if it doesn't find a
    difference before the beginning.
    """
    name = 'Find Previous Difference'
    accelerator = 'Ctrl+Shift+D'
    tooltip = 'Find previous difference to the baseline'
    enabled_name = 'diff_highlight'

    def perform(self, event):
        e = self.active_editor
        index = e.cursor_index
        new_index = e.segment.find_previous(index, diff=True)
        if new_index is not None:
            e.index_clicked(new_index, 0, None)


class ListDiffAction(EditorAction):
    name = 'List Differences'
    tooltip = 'Show a text representation of the differences'
    enabled_name = 'diff_highlight'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = s.get_style_ranges(diff=True)
        d = e.machine.get_disassembler(e.task.hex_grid_lower_case, e.task.assembly_lower_case)
        d.set_pc(s, s.start_addr)
        lines = []
        blank_label = ""
        for start, end in ranges:
            bytes = list(s[start:end])
            origin = s.label(start, e.task.hex_grid_lower_case)
            comment = s.get_comment(start)
            if comment:
                lines.append("%-8s; %s" % (blank_label, comment))
            lines.append("%-8s%s $%s" % (blank_label, d.asm_origin, origin))
            lines.append("%-8s%s" % (blank_label, d.get_data_byte_string(bytes)))
            lines.append("")
        text = "\n".join(lines) + "\n"
        dlg = wx.lib.dialogs.ScrolledMessageDialog(e.task.window.control, text, "Summary of Differences")
        dlg.ShowModal()


class UndoCursorPositionAction(EditorAction):
    name = 'Previous Cursor Position'
    accelerator = 'Ctrl+-'
    tooltip = 'Go to previous cursor position in cursor history'

    def perform(self, event):
        e = self.active_editor
        e.undo_cursor_history()


class RedoCursorPositionAction(EditorAction):
    name = 'Next Cursor Position'
    accelerator = 'Shift+Ctrl+-'
    tooltip = 'Go to next cursor position in cursor history'

    def perform(self, event):
        e = self.active_editor
        e.redo_cursor_history()


class StartTraceAction(EditorAction):
    name = "Start New Disassembly Trace"
    accelerator = 'F12'
    enabled_name = 'has_origin'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        e.disassembly.start_trace()
        e.document.change_count += 1
        e.refresh_panes()
        e.can_trace = True


class AddTraceStartPointAction(EditorAction):
    name = "Add Trace Start Point"
    accelerator = 'F11'
    enabled_name = 'can_trace'
    tooltip = 'Start a trace at the cursor or at all instructions in the selected ranges'

    def perform(self, event):
        e = self.active_editor
        # check if selected a range:
        ranges, indexes = e.get_selected_ranges_and_indexes()
        if len(indexes) == 0:
            indexes = [e.cursor_index]
        s = e.segment
        checked = set()
        for i in indexes:
            pc = e.disassembly.table.lines.get_instruction_start_pc(i + s.start_addr)
            if pc not in checked:
                e.disassembly.trace_disassembly(pc)
                checked.add(pc)
        e.document.change_count += 1
        e.refresh_panes()


class ApplyTraceSegmentAction(EditorAction):
    name = "Apply Trace to Segment"
    accelerator = 'F10'
    tooltip = 'Copy the results of the trace to the current segment'
    enabled_name = 'can_trace'

    def perform(self, event):
        cmd = ApplyTraceSegmentCommand(self.active_editor.segment)
        self.active_editor.process_command(cmd)


class ClearTraceAction(EditorAction):
    name = "Clear Trace"
    accelerator = 'F9'
    tooltip = 'Clear the current trace'
    enabled_name = 'can_trace'

    def perform(self, event):
        cmd = ClearTraceCommand(self.active_editor.document.container_segment)
        self.active_editor.process_command(cmd)
