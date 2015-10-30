""" Text editor sample task

"""
# Enthought library imports.
from pyface.api import GUI, ImageResource, ConfirmationDialog, FileDialog, \
    ImageResource, YES, OK, CANCEL
from pyface.action.api import Action, ActionItem, Separator, Group
from pyface.tasks.api import Task, TaskWindow, TaskLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, TaskToggleGroup, EditorAction, SchemaAddition
from traits.api import on_trait_change, Property, Instance, Any, Event, Int

from omnimon.framework.task import FrameworkTask
from omnimon.framework.actions import TaskDynamicSubmenuGroup
from hex_editor import HexEditor
from preferences import HexEditPreferences
from commands import *
import panes
import omnimon.utils.fonts as fonts
import omnimon.utils.dis6502 as dis6502
from omnimon.utils.binutil import known_segment_parsers

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
        print event_data
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
        self.active_editor.view_segment_number(0)

    @on_trait_change('active_editor.segment_parser')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.document.segment_parser == self.segment_parser

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
        print event_data
        if event_data is not None:
            for i, segment in enumerate(event_data):
                action = UseSegmentAction(segment=segment, segment_number=i)
                items.append(ActionItem(action=action))
            
        return items

class UseSegmentAction(EditorAction):
    segment = Any
    
    segment_number = Int
    
    def _name_default(self):
        return str(self.segment)
    
    def perform(self, event):
        self.active_editor.view_segment_number(self.segment_number)


class IndexRangeAction(EditorAction):
    enabled_name = 'can_copy'
    cmd = None
    
    def _name_default(self):
        return self.cmd.pretty_name
    
    def perform(self, event):
        e = self.active_editor
        cmd = self.cmd(e.segment, e.anchor_start_index, e.anchor_end_index)
        self.active_editor.process_command(cmd)

class ZeroAction(IndexRangeAction):
    cmd = ZeroCommand

class FFAction(IndexRangeAction):
    cmd = FFCommand

class SetHighBitAction(IndexRangeAction):
    cmd = SetHighBitCommand

class ClearHighBitAction(IndexRangeAction):
    cmd = ClearHighBitCommand

class BitwiseNotAction(IndexRangeAction):
    cmd = BitwiseNotCommand

class LeftShiftAction(IndexRangeAction):
    cmd = LeftShiftCommand

class RightShiftAction(IndexRangeAction):
    cmd = RightShiftCommand

class LeftRotateAction(IndexRangeAction):
    cmd = LeftRotateCommand

class RightRotateAction(IndexRangeAction):
    cmd = RightRotateCommand


class IndexRangeValueAction(IndexRangeAction):
    def _name_default(self):
        return self.cmd.pretty_name + "..."
    
    def get_value(self, editor):
        import wx
        dialog = wx.TextEntryDialog(editor.window.control, "Enter byte value: (prefix with 0x or $ for hex)", "Byte Value")

        result = dialog.ShowModal()
        if result == wx.ID_OK:
            text = dialog.GetValue()
            try:
                if text.startswith("0x"):
                    value = int(text[2:], 16)
                elif text.startswith("$"):
                    value = int(text[1:], 16)
                else:
                    value = int(text)
            except (ValueError, TypeError):
                value = None
        dialog.Destroy()
        return value
        
    def show_dialog(self, editor):
        e = editor
        value = self.get_value(editor)
        if value is not None:
            cmd = self.cmd(e.segment, e.anchor_start_index, e.anchor_end_index, value)
            self.active_editor.process_command(cmd)
            
    def perform(self, event):
        GUI.invoke_later(self.show_dialog, self.active_editor)

class SetValueAction(IndexRangeValueAction):
    cmd = SetValueCommand

class OrWithAction(IndexRangeValueAction):
    cmd = OrWithCommand

class AndWithAction(IndexRangeValueAction):
    cmd = AndWithCommand

class XorWithAction(IndexRangeValueAction):
    cmd = XorWithCommand


class HexEditTask(FrameworkTask):
    """ A simple task for opening a blank editor.
    """

    new_file_text = "Binary File"

    #### Task interface #######################################################

    id = 'omnimon.framework.hex_edit_task'
    name = 'Hex Editor'
    
    preferences_helper = HexEditPreferences
    
    #### Menu events ##########################################################
    
    fonts_changed = Event
    
    segments_changed = Event

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _default_layout_default(self):
        return TaskLayout(
            right=HSplitter(
                PaneItem('hex_edit.disasmbly_pane'),
                PaneItem('hex_edit.byte_graphics'),
                PaneItem('hex_edit.font_map'),
                PaneItem('hex_edit.memory_map'),
                PaneItem('hex_edit.segments'),
                PaneItem('hex_edit.undo'),
                ),
            )

    def create_dock_panes(self):
        """ Create the file browser and connect to its double click event.
        """
        return [
            panes.DisassemblyPane(),
            panes.ByteGraphicsPane(),
            panes.FontMapPane(),
            panes.MemoryMapPane(),
            panes.SegmentsPane(),
            panes.UndoPane(),
            ]

    def _extra_actions_default(self):
        segment_menu = self.create_menu("Menu", "Segments", "SegmentParserGroup", "SegmentGroup")
        bytes_menu = self.create_menu("Menu", "Bytes", "HexModifyGroup")
        actions = [
            # Menubar additions
            SchemaAddition(factory=lambda: segment_menu,
                           path='MenuBar',
                           after="Edit",
                           ),
            SchemaAddition(factory=lambda: bytes_menu,
                           path='MenuBar',
                           after="Edit",
                           ),
            ]
        return actions

    def _active_editor_changed(self, editor):
        print "active editor changed to ", editor
        if editor is not None:
            editor.update_panes()

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = HexEditor()
        return editor

    
    def get_actions(self, location, menu_name, group_name):
        if location == "Menu":
            if menu_name == "View":
                if group_name == "ViewConfigGroup":
                    return [
                        SMenu(
                            Group(
                                UseFontAction(font=fonts.A8DefaultFont),
                                UseFontAction(font=fonts.A8ComputerFont),
                                id="a1", separator=True),
                            FontChoiceGroup(id="a2", separator=True),
                            Group(
                                LoadFontAction(),
                                GetFontFromSelectionAction(),
                                id="a3", separator=True),
                            id='FontChoiceSubmenu1', separator=True, name="Font"),
                        SMenu(
                            Group(
                                FontStyleBaseAction(font_mode=2, name="Antic 2 (Gr 0)"),
                                FontStyleBaseAction(font_mode=4, name="Antic 4"),
                                FontStyleBaseAction(font_mode=5, name="Antic 5"),
                                FontStyleBaseAction(font_mode=6, name="Antic 6 (Gr 1) Uppercase and Numbers"),
                                FontStyleBaseAction(font_mode=8, name="Antic 6 (Gr 1) Lowercase and Symbols"),
                                FontStyleBaseAction(font_mode=7, name="Antic 7 (Gr 2) Uppercase and Numbers"),
                                FontStyleBaseAction(font_mode=9, name="Antic 7 (Gr 2) Lowercase and Symbols"),
                                id="a1", separator=True),
                            id='FontChoiceSubmenu2', separator=True, name="Antic Mode"),
                        SMenu(
                            Group(
                                DisassemblerBaseAction(disassembler=dis6502.Basic6502Disassembler),
                                DisassemblerBaseAction(disassembler=dis6502.Atari800Disassembler),
                                DisassemblerBaseAction(disassembler=dis6502.Atari5200Disassembler),
                                id="a1", separator=True),
                            id='FontChoiceSubmenu3', separator=True, name="Disassembler"),
                        ]
            elif menu_name == "Segments":
                if group_name == "SegmentParserGroup":
                    segment_parser_actions = [SegmentParserAction(segment_parser=s) for s in known_segment_parsers]
                    return [
                        SMenu(
                            Group(
                                *segment_parser_actions,
                                id="a1", separator=True),
                            id='submenu1', separator=True, name="File Type"),
                        ]
                elif group_name == "SegmentGroup":
                    return [
                        SegmentChoiceGroup(id="a2", separator=True),
                        ]
            elif menu_name == "Bytes":
                if group_name == "HexModifyGroup":
                    return [
                        ZeroAction(),
                        FFAction(),
                        SetValueAction(),
                        Separator(),
                        SetHighBitAction(),
                        ClearHighBitAction(),
                        BitwiseNotAction(),
                        OrWithAction(),
                        AndWithAction(),
                        XorWithAction(),
                        Separator(),
                        LeftShiftAction(),
                        RightShiftAction(),
                        LeftRotateAction(),
                        RightRotateAction(),
                        ]

    ###
    @classmethod
    def can_edit(cls, mime):
        return mime == "application/octet-stream"
