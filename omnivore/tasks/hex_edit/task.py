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
import omnivore.arch.fonts as fonts
import omnivore.arch.colors as colors
import omnivore.arch.machine as machine
from omnivore.utils.segmentutil import iter_known_segment_parsers
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
    
    machine_menu_changed = Event

    emulator_changed = Event
    
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
        data_menu = self.create_menu("Menu", "Disk Image", "ParserGroup", "EmulatorGroup", "ActionGroup")
        segment_menu = self.create_menu("Menu", "Segments", "SegmentGroup")
        bytes_menu = self.create_menu("Menu", "Bytes", "HexModifyGroup")
        actions = [
            # Menubar additions
            SchemaAddition(factory=lambda: bytes_menu,
                           path='MenuBar',
                           after="Edit",
                           ),
            SchemaAddition(factory=lambda: segment_menu,
                           path='MenuBar',
                           after="Edit",
                           ),
            SchemaAddition(factory=lambda: data_menu,
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
            e.machine.text_font = prefs.text_font
            e.map_width = prefs.map_width
            e.bitmap_width = prefs.bitmap_width
            self.hex_grid_lower_case = prefs.hex_grid_lower_case
            self.assembly_lower_case = prefs.assembly_lower_case
            ByteTable.update_preferences(prefs)
            DisassemblyTable.update_preferences(prefs)
            e.reconfigure_panes()

    def get_font_mapping_actions(self, task=None):
        # When actions are needed for a popup, the task must be supplied. When
        # used from a menubar, supplying the task can mess up the EditorAction
        # automatic trait stuff, so this hack is needed. At least it is now,
        # after the addition of the Machine menu in b17fa9fe9. For some reason.
        if task is not None:
            kwargs = {'task': task}
        else:
            kwargs = {}
        actions = []
        for m in machine.predefined['font_mapping']:
            actions.append(FontMappingAction(font_mapping=m, **kwargs))
        return actions
    
    def get_actions_Menu_File_ImportGroup(self):
        return [
            InsertFileAction(),
            ]
    
    def get_actions_Menu_File_ExportGroup(self):
        return [
            SaveAsXEXAction(),
            SaveAsXEXBootAction(),
            ]
    
    def get_actions_Menu_File_SaveGroup(self):
        return [
            SaveAction(),
            SaveAsAction(),
            SMenu(SaveSegmentGroup(),
                  id='SaveSegmentAsSubmenu', name="Save Segment As"),
            ]

    def get_actions_Menu_Edit_UndoGroup(self):
        return [
            UndoAction(),
            RedoAction(),
            RevertToBaselineAction(),
            ]
    
    def get_actions_Menu_Edit_CopyPasteGroup(self):
        return [
            CutAction(),
            CopyAction(),
            CopyDisassemblyAction(),
            CopyAsReprAction(),
            PasteAction(),
            PasteAndRepeatAction(),
            ]
    
    def get_actions_Menu_Edit_SelectGroup(self):
        return [
            SelectAllAction(),
            SelectNoneAction(),
            SelectInvertAction(),
            SMenu(
                MarkSelectionAsCodeAction(name="Code"),
                MarkSelectionAsDataAction(name="Data"),
                MarkSelectionAsDisplayListAction(name="ANTIC Display List"),
                MarkSelectionAsJumpmanLevelAction(name="Jumpman Level Description"),
                MarkSelectionAsJumpmanHarvestAction(name="Jumpman Harvest Table"),
                id="mark1", name="Mark Selection As"),
            ]
    
    def get_actions_Menu_Edit_FindGroup(self):
        return [
            FindAction(),
            FindAlgorithmAction(),
            FindNextAction(),
            FindToSelectionAction(),
            ]
    
    def get_actions_Menu_View_ViewConfigGroup(self):
        return [
            ViewDiffHighlightAction(),
            TextFontAction(),
            ]
    
    def get_predefined_machines_actions(self):
        actions = []
        for m in machine.predefined['machine']:
            actions.append(PredefinedMachineAction(machine=m))
        return actions
    
    def get_actions_Menu_View_ViewPredefinedGroup(self):
        machines = self.get_predefined_machines_actions()
        return [
            SMenu(
                Group(
                    *machines,
                    id="a1", separator=True),
                id='MachineChoiceSubmenu1', separator=False, name="Predefined Machines"),
            ]
    
    def get_font_renderer_actions(self):
        actions = []
        for r in machine.predefined['font_renderer']:
            actions.append(FontRendererAction(font_renderer=r))
        return actions
    
    def get_bitmap_renderer_actions(self):
        actions = []
        for r in machine.predefined['bitmap_renderer']:
            actions.append(BitmapRendererAction(bitmap_renderer=r))
        return actions
    
    def get_processor_type_actions(self):
        actions = []
        for r in machine.predefined['disassembler']:
            actions.append(ProcessorTypeAction(disassembler=r))
        return actions
    
    def get_memory_map_actions(self):
        actions = []
        for r in machine.predefined['memory_map']:
            actions.append(MemoryMapAction(memory_map=r))
        return actions
    
    def get_actions_Menu_View_ViewChangeGroup(self):
        font_mapping_actions = self.get_font_mapping_actions()
        font_renderer_actions = self.get_font_renderer_actions()
        bitmap_renderer_actions = self.get_bitmap_renderer_actions()
        processor_type_actions = self.get_processor_type_actions()
        memory_map_actions = self.get_memory_map_actions()
        return [
            SMenu(
                Group(
                    *processor_type_actions,
                    id="a1", separator=True),
                id='mm1', separator=True, name="Processor"),
            SMenu(
                AssemblerChoiceGroup(id="a2", separator=True),
                Group(
                    AddNewAssemblerAction(),
                    EditAssemblersAction(),
                    SetSystemDefaultAssemblerAction(),
                    id="a3", separator=True),
                id='mm2', separator=False, name="Assembler Syntax"),
            SMenu(
                Group(
                    *memory_map_actions,
                    id="a1", separator=True),
                id='mm3', separator=False, name="Memory Map"),
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
                id='mm4', separator=False, name="Colors"),
            SMenu(
                Group(
                    UseFontAction(font=fonts.A8DefaultFont),
                    UseFontAction(font=fonts.A8ComputerFont),
                    UseFontAction(font=fonts.A2DefaultFont),
                    UseFontAction(font=fonts.A2MouseTextFont),
                    id="a1", separator=True),
                FontChoiceGroup(id="a2", separator=True),
                Group(
                    LoadFontAction(),
                    GetFontFromSelectionAction(),
                    id="a3", separator=True),
                id='mm5', separator=False, name="Font"),
            SMenu(
                Group(
                    *font_renderer_actions,
                    id="a1", separator=True),
                Group(
                    *font_mapping_actions,
                    id="a2", separator=True),
                Group(
                    FontMappingWidthAction(),
                    id="a3", separator=True),
                id='mm6', separator=False, name="Character Display"),
            SMenu(
                Group(
                    *bitmap_renderer_actions,
                    id="a1", separator=True),
                Group(
                    BitmapWidthAction(),
                    BitmapZoomAction(),
                    id="a1", separator=True),
                id='mm7', separator=False, name="Bitmap Display"),
            ]
    
    def get_actions_Menu_DiskImage_EmulatorGroup(self):
        return [
            RunEmulatorAction(id="a3"),
            SMenu(
                EmulatorChoiceGroup(id="a2"),
                Group(
                    AddNewEmulatorAction(),
                    EditEmulatorsAction(),
                    SetSystemDefaultEmulatorAction(),
                    id="a3", separator=True),
                id='MachineEmulator1', name="Emulators"),
            ]
    
    def get_actions_Menu_DiskImage_ParserGroup(self):
        groups = []
        for mime, pretty, parsers in iter_known_segment_parsers():
            actions = [SegmentParserAction(segment_parser=s) for s in parsers]
            if not pretty:
                groups.append(Group(CurrentSegmentParserAction(), separator=True))
                groups.append(Group(*actions, separator=True))
            else:
                groups.append(SMenu(Group(*actions, separator=True), name=pretty))
        return [
            SMenu(
                *groups,
                id='submenu1', separator=False, name="File Type"),
            ]
    
    def get_actions_Menu_DiskImage_ActionGroup(self):
        return [
            GetSegmentFromSelectionAction(),
            MultipleSegmentsFromSelectionAction(),
            InterleaveSegmentsAction(),
            SetSegmentOriginAction(),
            Separator(),
            AddCommentAction(),
            RemoveCommentAction(),
            Separator(),
            LoadBaselineVersionAction(),
            FindNextBaselineDiffAction(),
            FindPrevBaselineDiffAction(),
            ListDiffAction(),
            Separator(),
            SegmentGotoAction(),
            ]
    
    def get_actions_Menu_Segments_SegmentGroup(self):
        return [
            SegmentChoiceGroup(id="a2", separator=True),
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
            ReverseBitsAction(),
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
            UndoCursorPositionAction(),
            RedoCursorPositionAction(),
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
