""" Text editor sample task

"""
# Enthought library imports.
from pyface.action.api import Separator, Group
from pyface.tasks.api import Task, TaskWindow, TaskLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import SMenuBar, SMenu, SToolBar, SchemaAddition
from traits.api import on_trait_change, Property, Instance, Any, Event, Int

from omnivore.framework.task import FrameworkTask
from omnivore.framework.actions import *
from hex_editor import HexEditor
from preferences import HexEditPreferences
from actions import *
import pane_layout
import omnivore.utils.wx.fonts as fonts
import omnivore.utils.dis6502 as dis6502
from omnivore.utils.segmentutil import known_segment_parsers
import omnivore.utils.colors as colors
from grid_control import ByteTable
from disassembly import DisassemblyTable


class HexEditTask(FrameworkTask):
    """ Binary file editor
    """

    new_file_text = "Binary File"
    
    hex_grid_lower_case = Bool(True)
    
    assembly_lower_case = Bool(False)

    #### Task interface #######################################################

    id = pane_layout.task_id_with_pane_layout
    name = 'Hex Editor'
    
    preferences_helper = HexEditPreferences
    
    #### Menu events ##########################################################
    
    fonts_changed = Event
    
    segments_changed = Event
    
    # Must use different trait event in order for actions populated in the
    # dynamic menu (set by segments_changed event above) to have their radio
    # buttons updated properly
    segment_selected = Event

    ###########################################################################
    # 'Task' interface.
    ###########################################################################
    
    def _hex_grid_lower_case_default(self):
        prefs = self.get_preferences()
        return prefs.hex_grid_lower_case
    
    def _assembly_lower_case_default(self):
        prefs = self.get_preferences()
        return prefs.assembly_lower_case

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
        # Make sure it's a valid document before refreshing
        if editor is not None and editor.document.segments:
            editor.update_panes()

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################
    
    def initialize_class_preferences(self):
        prefs = self.get_preferences()
        ByteTable.update_preferences(prefs)
        DisassemblyTable.update_preferences(prefs)

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = HexEditor()
        return editor

    @on_trait_change('window.application.preferences_changed_event')
    def refresh_from_new_preferences(self):
        e = self.active_editor
        if e is not None:
            prefs = self.get_preferences()
            e.text_font = prefs.text_font
            self.hex_grid_lower_case = prefs.hex_grid_lower_case
            self.assembly_lower_case = prefs.assembly_lower_case
            ByteTable.update_preferences(prefs)
            DisassemblyTable.update_preferences(prefs)
            e.reconfigure_panes()

    def get_font_mapping_actions(self):
        return [
            FontMappingBaseAction(font_mapping=0, name="Antic Internal Codes", task=self),
            FontMappingBaseAction(font_mapping=1, name="ATASCII Codes", task=self),
            ]
    
    def get_actions_Menu_File_SaveGroup(self):
        return [
            SaveAction(),
            SaveAsAction(),
            SMenu(SaveSegmentGroup(),
                  id='SaveSegmentAsSubmenu', name="Save Segment As"),
            ]
    
    def get_actions_Menu_Edit_CopyPasteGroup(self):
        return [
            CutAction(),
            CopyAction(),
            PasteAction(),
            PasteAndRepeatAction(),
            ]
    
    def get_actions_Menu_Edit_FindGroup(self):
        return [
            FindAction(),
            FindNextAction(),
            ]
    
    def get_common_ViewConfigGroup(self):
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
                Group(
                    FontMappingWidthAction(),
                    id="a3", separator=True),
                id='FontChoiceSubmenu2a1', separator=True, name="Char Map"),
            SMenu(
                Group(
                    BitmapWidthAction(),
                    BitmapZoomAction(),
                    id="a1", separator=True),
                id='FontChoiceSubmenu2a2', separator=True, name="Bitmap"),
            SMenu(
                Group(
                    ColorStandardAction(name="NTSC", color_standard=0),
                    ColorStandardAction(name="PAL", color_standard=1),
                    id="a0", separator=True),
                Group(
                    UseColorsAction(name="Powerup Colors", colors=colors.powerup_colors()),
                    id="a1", separator=True),
                Group(
                    AnticColorAction(),
                    id="a2", separator=True),
                id='FontChoiceSubmenu2a', separator=True, name="Antic Colors"),
            ]
    
    def get_actions_Menu_View_ViewConfigGroup(self):
        actions = self.get_common_ViewConfigGroup()
        actions.extend([
            SMenu(
                Group(
                    DisassemblerBaseAction(disassembler=dis6502.Basic6502Disassembler),
                    DisassemblerBaseAction(disassembler=dis6502.Atari800Disassembler),
                    DisassemblerBaseAction(disassembler=dis6502.Atari5200Disassembler),
                    id="a1", separator=True),
                id='FontChoiceSubmenu3', separator=True, name="Disassembler"),
            TextFontAction(),
            ])
        return actions
    
    def get_actions_Menu_Segments_SegmentParserGroup(self):
        segment_parser_actions = [SegmentParserAction(segment_parser=s) for s in known_segment_parsers]
        return [
            SMenu(
                Group(
                    *segment_parser_actions,
                    id="a1", separator=True),
                id='submenu1', separator=True, name="File Type"),
            GetSegmentFromSelectionAction(),
            ]
    
    def get_actions_Menu_Segments_SegmentGroup(self):
        return [
            SegmentChoiceGroup(id="a2", separator=True),
            Separator(),
            SegmentGotoAction(),
            ]
    
    def get_actions_Menu_Bytes_HexModifyGroup(self):
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
            FindPrevAction(),
            CancelMinibufferAction(),
            ]

    ###
    @classmethod
    def can_edit(cls, document):
        return document.metadata.mime == "application/octet-stream" or document.segments
    
    @classmethod
    def get_match_score(cls, document):
        """Return a number based on how good of a match this task is to the
        incoming Document.
        
        0 = generic match
        ...
        10 = absolute match
        """
        return 1
