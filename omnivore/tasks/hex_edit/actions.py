""" Action definitions for HexEdit task

"""
import sys

import wx

# Enthought library imports.
from traits.api import on_trait_change, Any, Int
from pyface.action.api import Action, ActionItem
from pyface.tasks.action.api import TaskAction, EditorAction

from omnivore.framework.actions import *
from commands import *
from omnivore.utils.wx.antic_colors import AnticColorDialog
from omnivore.utils.wx.dialogs import prompt_for_hex, prompt_for_string
from omnivore.framework.minibuffer import *

class FontChoiceGroup(TaskDynamicSubmenuGroup):
    """Dynamic menu group to display the available fonts
    """
    #### 'DynamicSubmenuGroup' interface ######################################

    event_name = 'fonts_changed'

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self, event_data=None):
        items = []
        if event_data is not None:
            for font in event_data:
                action = UseFontAction(font=font)
                items.append(ActionItem(action=action))
            
        return items

class UseFontAction(EditorAction):
    font = Any
    
    def _name_default(self):
        return "%s" % (self.font['name'])
    
    def perform(self, event):
        self.active_editor.set_font(self.font)

class LoadFontAction(EditorAction):
    name = 'Load Font...'
    
    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control)
        if dialog.open() == OK:
            self.active_editor.load_font(dialog.path)

class GetFontFromSelectionAction(EditorAction):
    name = 'Get Font From Selection'
    enabled_name = 'grid_range_selected'
    
    def perform(self, event):
        self.active_editor.get_font_from_selection()


class FontStyleBaseAction(EditorAction):
    """Radio buttons for changing font style
    """
    # Traits
    style = 'radio'
    
    font_mode = Int

    def perform(self, event):
        self.active_editor.set_font(font_mode=self.font_mode)

    @on_trait_change('active_editor.font_mode')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.font_mode == self.font_mode


class FontMappingBaseAction(EditorAction):
    """Radio buttons for changing font style
    """
    # Traits
    style = 'radio'
    
    font_mapping = Int

    def perform(self, event):
        self.active_editor.set_font_mapping(self.font_mapping)

    @on_trait_change('active_editor.antic_font_mapping')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.antic_font_mapping == self.font_mapping


class BitmapWidthAction(EditorAction):
    name = "Bitmap Width"

    def perform(self, event):
        e = self.active_editor
        width = prompt_for_hex(e.window.control, 'Enter new bitmap width in bytes', 'Set Bitmap Width', e.bitmap_width)
        if width is not None and width > 0:
            wx.CallAfter(e.set_bitmap_width, width)


class BitmapZoomAction(EditorAction):
    name = "Bitmap Zoom"

    def perform(self, event):
        e = self.active_editor
        width = prompt_for_hex(e.window.control, 'Enter new pixel zoom factor', 'Set Bitmap Zoom', e.bitmap_zoom)
        if width is not None and width > 0:
            wx.CallAfter(e.set_bitmap_zoom, width)


class FontMappingWidthAction(EditorAction):
    name = "Map Width"

    def perform(self, event):
        e = self.active_editor
        width = prompt_for_hex(e.window.control, 'Enter new map width in bytes', 'Set Map Width', str(e.map_width))
        if width is not None and width > 0:
            wx.CallAfter(e.set_map_width, width)


class FontMappingZoomAction(EditorAction):
    name = "Map Zoom"

    def perform(self, event):
        e = self.active_editor
        width = prompt_for_hex(e.window.control, 'Enter new pixel zoom factor', 'Set Map Zoom', e.map_zoom)
        if width is not None and width > 0:
            wx.CallAfter(e.set_map_zoom, width)


class AnticColorAction(EditorAction):
    name = 'Choose Colors...'
    
    def perform(self, event):
        e = self.active_editor
        dlg = AnticColorDialog(event.task.window.control, e)
        if dlg.ShowModal() == wx.ID_OK:
            e.update_colors(dlg.colors)


class UseColorsAction(EditorAction):
    name = 'Use Colors'
    colors = Any
    
    def perform(self, event):
        self.active_editor.update_colors(self.colors)


class ColorStandardAction(EditorAction):
    style = 'radio'
    
    color_standard = Int

    def perform(self, event):
        self.active_editor.set_color_standard(self.color_standard)

    @on_trait_change('active_editor.color_standard')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.color_standard == self.color_standard


class TextFontAction(EditorAction):
    name = 'Text Font...'
    
    def perform(self, event):
        e = self.active_editor
        data = wx.FontData()
        data.EnableEffects(True)
        data.SetColour(e.text_color)
        data.SetInitialFont(e.text_font)
        dlg = wx.FontDialog(self.active_editor.control, data)
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetFontData()
            e.set_text_font(data.GetChosenFont(), data.GetColour())
            e.reconfigure_panes()


class DisassemblerBaseAction(EditorAction):
    """Radio buttons for changing font style
    """
    # Traits
    style = 'radio'
    
    disassembler = Any
    
    def _name_default(self):
        return self.disassembler.menu_name

    def perform(self, event):
        self.active_editor.set_disassembler(self.disassembler)

    @on_trait_change('active_editor.disassembler')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.disassembler == self.disassembler


class SegmentParserAction(EditorAction):
    """Radio buttons for changing font style
    """
    # Traits
    style = 'radio'
    
    segment_parser = Any
    
    def _name_default(self):
        return self.segment_parser.menu_name

    def perform(self, event):
        self.active_editor.set_segment_parser(self.segment_parser)

    @on_trait_change('task.segments_changed')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.document.segment_parser.__class__ == self.segment_parser

class SegmentChoiceGroup(TaskDynamicSubmenuGroup):
    """Dynamic menu group to display the available fonts
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
                if sys.platform == "darwin":
                    action = UseSegmentAction(segment=segment, segment_number=i, task=self.task)
                else:
                    action = UseSegmentRadioAction(segment=segment, segment_number=i, task=self.task, checked=False)
                log.debug("SegmentChoiceGroup: created %s for %s, num=%d" % (action, str(segment), i))
                items.append(ActionItem(action=action, parent=self))
            
        return items

class UseSegmentAction(EditorAction):
    segment = Any
    
    segment_number = Int
    
    def _name_default(self):
        return str(self.segment)
    
    def perform(self, event):
        self.active_editor.view_segment_number(self.segment_number)

class UseSegmentRadioAction(UseSegmentAction):
    style = 'radio'

    @on_trait_change('task.segment_selected')
    def _update_checked(self):
        if self.active_editor:
            state = self.active_editor.segment_number == self.segment_number
            log.debug("UseSegmentAction: checked=%s %s %s %s" % (state, str(self.segment), self.active_editor.segment_number, self.segment_number))
            self.checked = state

class GetSegmentFromSelectionAction(EditorAction):
    name = 'New Segment From Selection'
    enabled_name = 'can_copy'
    
    def perform(self, event):
        e = self.active_editor
        text = prompt_for_string(e.window.control, "Enter segment name", "New Segment")
        if text is not None:
            segment = e.get_segment_from_selection()
            if not text:
                text = "%04x-%04x" % (segment.start_addr, segment.start_addr + len(segment) - 1)
            segment.name = text
            e.add_user_segment(segment)


class SaveSegmentAsFormatAction(EditorAction):
    saver = Any
    
    segment_number = Int
    
    def _name_default(self):
        return "%s (%s)" % (self.saver.name, self.saver.extensions[0])
    
    def perform(self, event):
        segment = self.task.active_editor.document.segments[self.segment_number]
        dialog = FileDialog(default_filename=segment.name, parent=event.task.window.control, action='save as', wildcard=self.saver.get_file_dialog_wildcard())
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
            for saver in segment.savers:
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
        addr = prompt_for_hex(e.window.control, "Enter address value: (prefix with 0x or $ for hex)", "Goto Address in a Segment")
        if addr is not None:
            segment_num, segment, index = e.document.find_segment_in_range(addr)
            if segment_num >= 0:
                e.view_segment_number(segment_num)
                e.index_clicked(index, 0, None)
            else:
                e.task.status_bar.message = "Address $%04x not valid in any segment" % addr


class IndexRangeAction(EditorAction):
    enabled_name = 'can_copy'
    cmd = None
    
    def _name_default(self):
        return self.cmd.pretty_name
    
    def perform(self, event):
        e = self.active_editor
        ranges = e.get_optimized_selected_ranges()
        cmd = self.cmd(e.segment, ranges)
        self.active_editor.process_command(cmd)

class ZeroAction(IndexRangeAction):
    cmd = ZeroCommand
    accelerator = 'Ctrl+0'

class FFAction(IndexRangeAction):
    cmd = FFCommand
    accelerator = 'Ctrl+9'

class SetHighBitAction(IndexRangeAction):
    cmd = SetHighBitCommand

class ClearHighBitAction(IndexRangeAction):
    cmd = ClearHighBitCommand

class BitwiseNotAction(IndexRangeAction):
    cmd = BitwiseNotCommand
    accelerator = 'Ctrl+1'

class LeftShiftAction(IndexRangeAction):
    cmd = LeftShiftCommand

class RightShiftAction(IndexRangeAction):
    cmd = RightShiftCommand

class LeftRotateAction(IndexRangeAction):
    cmd = LeftRotateCommand
    accelerator = 'Ctrl+<'

class RightRotateAction(IndexRangeAction):
    cmd = RightRotateCommand
    accelerator = 'Ctrl+>'


class IndexRangeValueAction(IndexRangeAction):
    def _name_default(self):
        return self.cmd.pretty_name + "..."
    
    def show_dialog(self, e):
        value = prompt_for_hex(e.window.control, "Enter byte value: (prefix with 0x or $ for hex)", "Byte Value")
        if value is not None:
            cmd = self.cmd(e.segment, e.selected_ranges, value)
            self.active_editor.process_command(cmd)
            
    def perform(self, event):
        wx.CallAfter(self.show_dialog, self.active_editor)

class SetValueAction(IndexRangeValueAction):
    cmd = SetRangeValueCommand

class OrWithAction(IndexRangeValueAction):
    cmd = OrWithCommand
    accelerator = 'Ctrl+\\'

class AndWithAction(IndexRangeValueAction):
    cmd = AndWithCommand
    accelerator = 'Ctrl+7'

class XorWithAction(IndexRangeValueAction):
    cmd = XorWithCommand
    accelerator = 'Ctrl+6'

class RampUpAction(IndexRangeValueAction):
    cmd = RampUpCommand

class RampDownAction(IndexRangeValueAction):
    cmd = RampDownCommand

class AddValueAction(IndexRangeValueAction):
    cmd = AddValueCommand
    accelerator = 'Ctrl+='

class SubtractValueAction(IndexRangeValueAction):
    cmd = SubtractValueCommand
    accelerator = 'Ctrl+-'

class SubtractFromAction(IndexRangeValueAction):
    cmd = SubtractFromCommand
    accelerator = 'Shift+Ctrl+-'

class MultiplyAction(IndexRangeValueAction):
    cmd = MultiplyCommand
    accelerator = 'Ctrl+8'

class DivideByAction(IndexRangeValueAction):
    cmd = DivideByCommand
    accelerator = 'Ctrl+/'

class DivideFromAction(IndexRangeValueAction):
    cmd = DivideFromCommand
    accelerator = 'Shift+Ctrl+/'


class PasteAndRepeatAction(EditorAction):
    name = 'Paste and Repeat'
    accelerator = 'Shift+Ctrl+V'
    tooltip = 'Paste and repeat clipboard data until current selection is filled'
    enabled_name = 'can_copy'
    
    def perform(self, event):
        e = self.active_editor
        data_obj = e.get_paste_data_object()
        if data_obj is not None:
            bytes, extra = e.get_numpy_from_data_object(data_obj)
            cmd = PasteAndRepeatCommand(e.segment, e.anchor_start_index, e.anchor_end_index, bytes)
            self.active_editor.process_command(cmd)


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


class CancelMinibufferAction(EditorAction):
    name = 'Cancel Minibuffer or current edit'
    accelerator = 'ESC'
    tooltip = 'Remove minibuffer or cancel current edit'

    def perform(self, event):
        event.task.on_hide_minibuffer_or_cancel(None)
