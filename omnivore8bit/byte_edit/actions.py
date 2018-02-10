""" Action definitions for ByteEdit task

"""
import os
import sys

import wx
import wx.lib.dialogs

# Enthought library imports.
from traits.api import on_trait_change, Any, Int, Bool
from pyface.api import YES, NO

from atrcopy import user_bit_mask, data_style, add_xexboot_header, add_atr_header, BootDiskImage, SegmentData, interleave_segments, get_xex

from omnivore.framework.enthought_api import Action, ActionItem, EditorAction, NameChangeAction, TaskDynamicSubmenuGroup
from omnivore.utils.command import StatusFlags

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

import logging
log = logging.getLogger(__name__)


class GetFontFromSelectionAction(EditorAction):
    name = 'Get Font From Selection'
    enabled_name = 'grid_range_selected'

    def perform(self, event):
        self.active_editor.get_font_from_selection()


class EmulatorChoiceGroup(TaskDynamicSubmenuGroup):
    """Dynamic menu group to display the available fonts
    """
    #### 'DynamicSubmenuGroup' interface ######################################

    event_name = 'emulator_changed'

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

    def _update_checked(self, ui_state):
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
            self.active_editor.focused_viewer.machine.add_emulator(event.task, emu)


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




class AddViewerAction(EditorAction):
    """Add a new viewer to the user interface
    """
    # Traits
    viewer = Any

    def _name_default(self):
        return self.viewer.pretty_name

    def perform(self, event):
        self.active_editor.add_viewer(self.viewer)


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

    def _update_checked(self, ui_state):
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
        wx.CallAfter(self.active_editor.view_segment_number, self.segment_number)

    def _update_checked(self, ui_state):
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
            e.find_segment(segment=segment, refresh=True)


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
            e.find_segment(segment=segments[0], refresh=True)


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
            e.find_segment(segment=segment, refresh=True)
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
        e.find_segment(segment=s, refresh=True)


class FindStyleBaseAction(EditorAction):
    name = 'Select Style'
    tooltip = 'Select a particular style'

    def get_ranges(self, segment):
        return segment.get_style_ranges(selected=True)

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = self.get_ranges(s)
        e.segment.clear_style_bits(match=True)
        try:
            start, end = ranges[0]
            e.segment.set_style_ranges(ranges, match=True)
            e.index_clicked(start, 0, None)
        except IndexError:
            pass


class FindCodeAction(FindStyleBaseAction):
    name = 'Code'

    def get_ranges(self, segment):
        return segment.get_style_ranges(selected=True)


class FindDataAction(FindStyleBaseAction):
    name = 'Data'
    user_type = 0

    def get_ranges(self, segment):
        return segment.get_style_ranges(data=True, user=self.user_type)


class FindDisplayListAction(FindDataAction):
    name = 'Display List'
    user_type = ANTIC_DISASM


class FindJumpmanLevelAction(FindDataAction):
    name = 'Jumpman Level Data'
    user_type = JUMPMAN_LEVEL


class FindJumpmanHarvestAction(FindDataAction):
    name = 'Jumpman Harvest Table'
    user_type = JUMPMAN_HARVEST


class FindUninitializedAction(FindDataAction):
    name = 'Uninitialized Data'
    user_type = UNINITIALIZED_DATA


class CustomDisassemblerAction(EditorAction):
    name = '<custom>'
    enabled_name = 'can_copy'
    disassembly_type = 0

    def set_style(self, segment, ranges):
        segment.clear_style_ranges(ranges, user=user_bit_mask)
        segment.set_style_ranges(ranges, user=self.disassembly_type)

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = s.get_style_ranges(selected=True)
        self.set_style(s, ranges)
        f = StatusFlags()
        f.byte_style_changed = True
        e.process_flags(f)

class MarkSelectionAsCodeAction(CustomDisassemblerAction):
    """Marks the selected bytes as valid code to be disassembled using the
    current processor definition.

    """
    name = 'Code'

    def set_style(self, segment, ranges):
        segment.clear_style_ranges(ranges, data=True, user=1)


class MarkSelectionAsDataAction(CustomDisassemblerAction):
    """Marks the selected bytes as data, not to be disassembled but shown
    as byte values in the disassembly listing.

    """
    name = 'Data'

    def set_style(self, segment, ranges):
        segment.clear_style_ranges(ranges, user=user_bit_mask)
        segment.set_style_ranges(ranges, data=True)
        # check if the segment can be merged with a previous data segment
        index = ranges[0][0]
        while index > 0 and (segment.style[index-1] & user_bit_mask) == data_style:
            index -= 1
        ranges[0] = (index, ranges[0][1])


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
    not used much for direct editing now that the `Jumpman Level Editor <omnivore.jumpman.html>`_ is
    available.
    """
    name = 'Jumpman Level Data'
    disassembly_type = JUMPMAN_LEVEL


class MarkSelectionAsJumpmanHarvestAction(CustomDisassemblerAction):
    """Marks the selected bytes as a Jumpman harvest table. This is not used
    much for direct editing now that the `Jumpman Level Editor`_ is available.
    """
    name = 'Jumpman Harvest Table'
    disassembly_type = JUMPMAN_HARVEST


class MarkSelectionAsUninitializedDataAction(CustomDisassemblerAction):
    """Marks the selected bytes as unitialized data, skipping over those bytes
    and placing an ``origin`` directive in the disassembly that points to the
    next address that contains any other type of data.
    """
    name = 'Uninitialized Data'
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
        path = event.task.prompt_local_file_dialog("Import Segment Labels")
        if path is not None:
            e = self.active_editor
            with open(path, "r") as fh:
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
                path = event.task.prompt_local_file_dialog(save=True, title="Export Segment Labels")
                if path:
                    with open(path, "w") as fh:
                        fh.write("\n".join(["%s = $%04x" % (v, k) for k, v in tmp]) + "\n")
                    return
        e.task.status_bar.error = "No labels in segment"


class CopyAsCBytesAction(EditorAction):
    """Copy the current selection as text where each byte is converted to the
    C source code representation.
    """
    name = 'Copy as C Data'
    enabled_name = 'can_copy'

    def perform(self, event):
        e = self.active_editor
        ranges, indexes = e.get_selected_ranges_and_indexes()
        data = e.segment[indexes]
        text = ",\n".join([",".join(["0x%02x" % d for d in list(c)]) for c in [data[i:i+8] for i in range(0, len(data), 8)]])
        data_obj = wx.TextDataObject()
        data_obj.SetText(text)
        e.set_clipboard_object(data_obj)


class CopyAsReprAction(EditorAction):
    """Copy the current selection as a text string containing a string (with
    escaped characters where necessary) that reproduces the bytes in the
    selection.

    Python note: both double quotes and single quotes are escaped as hex values
    so the resulting string is safe to use inside either of those characters as
    the string delimiter.
    """
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


def prompt_for_comment(e, s, ranges, desc):
    existing = s.get_first_comment(ranges)
    text = prompt_for_string(e.window.control, desc, "Add Comment", existing)
    if text is not None:
        cmd = SetCommentCommand(s, ranges, text)
        e.process_command(cmd)


class AddCommentAction(EditorAction):
    """Add a text comment to a byte location.

    A comment is associated with a single byte, so although a range can be
    selected, the comment is applied to only the first byte in the range.

    Bytes with comments will be highlighted in all displays.
    """
    name = 'Add Comment'
    accelerator = 'Alt+C'

    def is_range(self, event):
        return self.active_editor.can_copy

    def get_index(self, event):
        return self.active_editor.caret_index

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
    """Remove any comments that are in the selected range, or if no selection
    from the current caret position.

    """
    name = 'Remove Comment'
    accelerator = 'Shift+Alt+C'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        if e.can_copy:
            ranges = s.get_style_ranges(selected=True)
        else:
            index = e.caret_index
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
    """Add a label to a byte location.

    Like `Add Comment`_, a label is associated with a single byte, so although
    a range can be selected, the comment is applied to only the first byte in
    the range.

    Unlike comments, labels are *not* highlighted and are only shown in the
    disassembly window.
    """
    name = 'Add Label'
    accelerator = 'Alt+L'
    enabled_name = 'has_origin'

    def get_ranges(self, editor, segment, event):
        if editor.can_copy:  # has selected ranges
            ranges = segment.get_style_ranges(selected=True)
        else:
            ranges = [(editor.caret_index, editor.caret_index + 1)]
        return ranges

    def process_ranges(self, editor, segment, ranges):
        index = ranges[0][0]
        addr = index + segment.start_addr
        return addr

    def process(self, editor, segment, addr):
        desc = "Enter label for address $%04x" % addr
        prompt_for_label(editor, segment, addr, desc)

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = self.get_ranges(e, s, event)
        addr = self.process_ranges(e, s, ranges)
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
    """Remove the label at the current caret position, or if there is a
    selection, all labels in the selected range.

    """
    name = 'Remove Label'
    accelerator = 'Shift+Alt+L'

    def process_ranges(self, editor, segment, ranges):
        return ranges

    def process(self, editor, segment, ranges):
        cmd = ClearLabelCommand(segment, ranges)
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
    """Remove a segment from the list of segments

    Any segment except the root segment can be deleted. Recall that this
    doesn't delete any data, just this view of the data.
    """
    name = 'Delete User Segment'
    segment_number = Int

    def perform(self, event):
        e = self.task.active_editor
        segment = e.document.segments[self.segment_number]
        if self.task.confirm("Delete user segment %s?" % segment.name, "Delete User Segment"):
            e.delete_user_segment(segment)


class SetSegmentOriginAction(EditorAction):
    """Sets the origin of the current segment to an address, changing the
    starting point for all windows displaying this segment's data.

    """
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
    """Create an Atari 8-bit executable from a set of segments.

    Opens a dialog window providing a list of segments to be added to the new
    executable and a starting address at which the Atari will begin executing
    the program on completion of the load.
    """
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
            path = event.task.prompt_local_file_dialog(default_filename="test.%s" % self.file_ext, save=True)
            if path:
                self.active_editor.save(path, document=doc)
        dlg.Destroy()


class SaveAsXEXBootAction(SaveAsXEXAction):
    """Create an Atari 8-bit boot disk from a set of segments.

    Opens a dialog window providing a list of segments to be added to the boot
    disk and a starting address at which the Atari will begin executing the
    program after reading all the sectors written to disk.

    This creates a smaller-than-normal ATR image with a custom bootloader. Any
    sectors beyond the number fo sectors required to create the image are not
    included in the image.
    """
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
        path = event.task.prompt_local_file_dialog(default_filename=segment.name, save=True, wildcard=get_file_dialog_wildcard(self.saver.export_data_name, self.saver.export_extensions))
        if path:
            self.active_editor.save_segment(self.saver, path)


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
    """Move the caret to an address. If the address is in this segment, moves
    there. If not, it searches through all the segments (in segment list order)
    to find one that does contain that address.

    If that address is not valid for any segment, it will return an error
    message.
    """
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
    """Insert binary data at the caret

    The data from the loaded file will overwrite data starting at the caret,
    so it's not inserted in the text editor sense where space is created in the
    existing data.
    """
    name = 'Insert File...'

    def perform(self, event):
        path = event.task.prompt_local_file_dialog("Insert File")
        if path is not None:
            e = self.active_editor
            cmd = InsertFileCommand(e.segment, e.caret_index, path)
            e.process_command(cmd)


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

    def _update_checked(self, ui_state):
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
        path = event.task.prompt_local_file_dialog()
        if path:
            e = self.active_editor
            e.load_baseline(path)
            e.compare_to_baseline()
            e.refresh_panes()


class RevertToBaselineAction(EditorAction):
    """Restore the selection to the data contained in the `Baseline
    Data`_ file.
    """
    enabled_name = 'can_copy_baseline'

    def perform(self, event):
        e = self.active_editor
        ranges = e.get_optimized_selected_ranges()
        cmd = RevertToBaselineCommand(e, e.segment, ranges)
        self.active_editor.process_command(cmd)


class FindNextBaselineDiffAction(EditorAction):
    """Move the caret to the next block of data that is different than
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
        index = e.caret_index
        new_index = e.segment.find_next(index, diff=True)
        if new_index is not None:
            e.index_clicked(new_index, 0, None)


class FindPrevBaselineDiffAction(EditorAction):
    """Move the caret to the previous block of data that is different than
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
        index = e.caret_index
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


class UndoCaretPositionAction(EditorAction):
    name = 'Previous Caret Position'
    accelerator = 'Ctrl+-'
    tooltip = 'Go to previous caret position in caret history'

    def perform(self, event):
        e = self.active_editor
        e.undo_caret_history()


class RedoCaretPositionAction(EditorAction):
    name = 'Next Caret Position'
    accelerator = 'Shift+Ctrl+-'
    tooltip = 'Go to next caret position in caret history'

    def perform(self, event):
        e = self.active_editor
        e.redo_caret_history()


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
    tooltip = 'Start a trace at the caret or at all instructions in the selected ranges'

    def perform(self, event):
        e = self.active_editor
        # check if selected a range:
        ranges, indexes = e.get_selected_ranges_and_indexes()
        if len(indexes) == 0:
            indexes = [e.caret_index]
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
