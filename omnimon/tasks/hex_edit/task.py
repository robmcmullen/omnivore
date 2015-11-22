""" Text editor sample task

"""
# Enthought library imports.
from pyface.action.api import Separator, Group
from pyface.tasks.api import Task, TaskWindow, TaskLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import SMenuBar, SMenu, SToolBar, SchemaAddition
from traits.api import on_trait_change, Property, Instance, Any, Event, Int

from omnimon.framework.task import FrameworkTask
from omnimon.framework.actions import *
from hex_editor import HexEditor
from preferences import HexEditPreferences
from actions import *
import pane_layout
import omnimon.utils.wx.fonts as fonts
import omnimon.utils.dis6502 as dis6502
from omnimon.utils.binutil import known_segment_parsers
import omnimon.utils.colors as colors


class HexEditTask(FrameworkTask):
    """ Binary file editor
    """

    new_file_text = "Binary File"

    #### Task interface #######################################################

    id = pane_layout.task_id_with_pane_layout
    name = 'Hex Editor'
    
    preferences_helper = HexEditPreferences
    
    #### Menu events ##########################################################
    
    fonts_changed = Event
    
    segments_changed = Event

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _default_layout_default(self):
        return pane_layout.pane_layout()

    def create_dock_panes(self):
        return pane_layout.pane_create()

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
        # Make sure it's a valid document before refreshing
        if editor is not None and editor.document.segments:
            editor.update_panes()

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = HexEditor()
        return editor

    def get_font_mapping_actions(self):
        return [
            FontMappingBaseAction(font_mapping=0, name="Antic Internal Codes", task=self),
            FontMappingBaseAction(font_mapping=1, name="ATASCII Codes", task=self),
            ]
    
    def get_actions(self, location, menu_name, group_name):
        if location == "Menu":
            if menu_name == "Edit":
                if group_name == "CopyPasteGroup":
                    return [
                        CutAction(),
                        CopyAction(),
                        PasteAction(),
                        PasteAndRepeatAction(),
                        ]
                elif group_name == "FindGroup":
                    return [
                        FindAction(),
                        FindBytesAction(),
                        ]
            elif menu_name == "View":
                if group_name == "ViewConfigGroup":
                    font_mapping_actions = self.get_font_mapping_actions()
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
                            id='FontChoiceSubmenu1', separator=True, name="Antic Font"),
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
                                *font_mapping_actions,
                                id="a2", separator=True),
                            id='FontChoiceSubmenu2', separator=True, name="Antic Font Mapping"),
                        SMenu(
                            Group(
                                FontMappingWidthAction(),
                                id="a3", separator=True),
                            id='FontChoiceSubmenu2', separator=True, name="Antic Font Width"),
                        SMenu(
                            Group(
                                UseColorsAction(name="Powerup Colors", colors=colors.powerup_colors()),
                                id="a1", separator=True),
                            Group(
                                AnticColorAction(),
                                id="a2", separator=True),
                            id='FontChoiceSubmenu2a', separator=True, name="Antic Colors"),
                        SMenu(
                            Group(
                                DisassemblerBaseAction(disassembler=dis6502.Basic6502Disassembler),
                                DisassemblerBaseAction(disassembler=dis6502.Atari800Disassembler),
                                DisassemblerBaseAction(disassembler=dis6502.Atari5200Disassembler),
                                id="a1", separator=True),
                            id='FontChoiceSubmenu3', separator=True, name="Disassembler"),
                        TextFontAction(),
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
                        GetSegmentFromSelectionAction(),
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
                        Separator(),
                        AddValueAction(),
                        SubtractValueAction(),
                        SubtractFromAction(),
                        MultiplyAction(),
                        DivideByAction(),
                        DivideFromAction(),
                        Separator(),
                        RampUpAction(),
                        RampDownAction(),
                        ]

    def get_keyboard_actions(self):
        return [
            FindBytesReverseAction(),
            CancelMinibufferAction(),
            ]

    ###
    @classmethod
    def can_edit(cls, mime):
        return mime == "application/octet-stream"
    
    @classmethod
    def get_match_score(cls, guess):
        """Return a number based on how good of a match this task is to the
        incoming FileGuess.
        
        0 = generic match
        ...
        10 = absolute match
        """
        return 1
