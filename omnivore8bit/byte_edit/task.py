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
from omnivore.framework.toolbar import get_toolbar_group
from byte_editor import ByteEditor
from preferences import ByteEditPreferences
import pane_layout
from actions import *
import omnivore8bit.arch.fonts as fonts
import omnivore8bit.arch.colors as colors
import omnivore8bit.arch.machine as machine
from omnivore8bit.utils.segmentutil import iter_known_segment_parsers


class ByteEditTask(FrameworkTask):
    """The byte editor was designed for reverse engineering 6502 machine code,
    initially for the Atari 8-bit computer systems, but expanded to Apple ][
    and other 6502-based processors. There is also support for most other 8-bit
    processors, but as the author doesn't have experience with other 8-bit
    processors they have not been extensively tested.

    Opening a file to edit will present the main hex edit user interface that
    shows many different views of the data. Editing is supported in the hex
    view, character view, and the disassembly. There is also a bitmap view but
    is presently only for viewing, not editing.

    Viewing Data
    ------------

    The various views can be scrolled independently, but there is only one
    cursor location. Clicking on a location in one view will move the other
    views to show the same location. `Selections`_ are analogous; see below.

    Segments
    --------

    Binary data is parsed using code that started life as part of Omnivore but
    I spun it out because it's useful as a standalone library: `atrcopy
    <https://pypi.python.org/pypi/atrcopy/>`_. It knows a lot about Atari 8-bit
    files and disk images, knows some stuff about Apple ][ files and disk
    images, and knows almost nothing about anything else (yet). Atrcopy thinks
    of binary data in terms of *segments*, where a segment is simply a portion
    of the disk image.

    The interesting feature of atrcopy is due to the use of `numpy
    <http://www.numpy.org/>`_, and it's this: segments can provide views of the
    same data *in different orders*. And, changing a byte in one segment also
    changes the value in other segments that contain that byte because there is
    only one copy of the data.

    This turns out to be super useful. For instance, the first segment that
    appears in Omnivore's list of segments will contain all the data from the
    disk image, in the order that the bytes appear in the file. This may or may
    not mean much depending on the format of the image. As an example, the
    catalog of an Apple DOS 3.3 disk is stored in sectors that increment
    downwards, so the catalog appears backwards(-ish. It's complicated). So
    atrcopy goes further and breaks this disk image segment into smaller
    segments depending on the type of the file. In the catalog example above,
    it creates another segment that displays the catalog in the correct order.
    Changing a byte in either of those segments will change the value in the
    other, because it's really the same value. It's just two different looks
    into the same data.

    Editing Data
    ------------

    Hex data can be edited by:

     * clicking on a cell and changing the hex data
     * selecting a region (or multiple regions; see `Selections`_ below) and using one of the operations in the `Bytes Menu`_
     * cutting and pasting hex data from elsewhere in the file
     * cutting and pasting hex data from another file edited in a different tab or window
     * pasting in data from an external application.

    Character data can be edited by clicking on a character in the character
    map to set the cursor and then typing. Inverse text is supported for Atari
    modes. Also supported are all the selection and cut/paste methods as above.

    Baseline Data
    -------------

    Omnivore automatically highlights changes to each segment as compared to
    the state of the data when first loaded.

    Optionally, you can specify a baseline difference file to compare to a
    different set of data, like a canonical or reference image. This is useful
    to compare changes to some known state over several Omnivore editing
    sessions, as Omnivore will remember the path to the reference image and
    will reload it when the disk image is edited in the future.

    As data is changed, the changes as compared to the baseline will be
    displayed in red.

    By default, baseline data difference highlighting is turned on, you can
    change this with the `Show Baseline Differences`_ menu item.

    Selections
    ----------

    Left clicking on a byte in any of the data views (hex, char, disassembly,
    bitmap, etc.) and dragging the mouse with the button held down will start a
    new selection, finished by releasing the mouse button. The selection will
    be shown in all views of the data, scrolling each view independently if
    necessary.

    The selection may be extended by shift-left-click, extending
    from either the beginning or the end of the selection as appropriate.

    Multiple selections are supported by holding the Control key (Command on
    Mac) while clicking and dragging as above. Extending a selection when using
    multiple selection is not currently supported.

    Find
    ----

    The data is searchable in multiple ways. Starting any search will display a
    search bar on the bottom of the main window. The basic search bar available
    with the `Find`_ menu item tries to be flexible and will show matches in
    any data view using an appropriate conversion for that view. For instance,
    the text string "00" in the search bar will find values of 0 in the hex
    view, strings of "00" in the character view, labels that have "00" anywhere
    in their text, "00" as an operand in the disassembly, or anything that has
    "00" in a comment.

    The `Find Next`_ and `Find Prev`_ menu items (or keyboard shortcuts) will
    traverse the list of matches.

    A more complicated search can be performed using the `Find Using
    Expression`_ menu item that support ranges of addresses or specific data
    values as search parameters using arbitrary boolean expressions.

    Comments
    --------

    Comments are a hugely important part of reverse engineering, because by
    definition the original source has been lost (or was never available). As
    you figure things out, it's important to write things down. Omnivore
    supports adding a comment to any byte in the file, and it will appear in
    any segment that views that byte.

    In the sidebar is a big ol' list of comments, and selecting one of the
    comments will move the data views to display the byte that is referenced by
    that comment. Because there may be multiple views of the same byte, the
    comment shown in the comments list is the *first* segment that contains
    that comment.

    Note that segments must have a defined origin for the segment to be
    considered as the primary for that comment.

    Disassembler
    ------------

    Omnivore started out as a reverse engineering tool for Atari 8-bit
    computers, which use the 6502 processor. After developing for a while, I
    found a python disassembler called `udis
    <https://github.com/jefftranter/udis>`_ that supports multiple processors.
    Through its usage, Omnivore can disassemble (and assemble! See below) code
    for:

    * 6502
    * 65816
    * 65c02
    * 6800
    * 6809
    * 6811
    * 8051
    * 8080
    * z80

    but the 6502 is the only processor have direct knowledge of and so the only
    one I've tested thoroughly. `Bug reports
    <https://github.com/robmcmullen/omnivore/issues>`_ (and patches!) for
    the other processors are welcome.

    Mini-Assembler
    ~~~~~~~~~~~~~~

    The disassembly can be edited using a simple mini-assembler; clicking on an
    opcode provides a text entry box to change the command. The mini-assembler
    supports all CPU types, not just 6502.

    Labels
    ~~~~~~

    Labels can be set on an address, and the label will be reflected in the
    disassembly code. Also, memory mapping files can be supplied that
    automatically label operating system locations.

    Data Regions
    ~~~~~~~~~~~~

    To support reverse engineering, regions can be marked as data, code, ANTIC
    display lists, and other types. Regions are highlighted in a different
    style and changes how the disassembly is displayed.

    Static Tracing of Disassembly
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    To help identify regions, static tracing can be used. Turning on static
    tracing assumes that every byte is data and shows temporary highlights over
    the entire segment. Starting a trace at an address causes Omnivore to
    follow the path of execution until it hits a return, break or bad
    instruction, marking every byte that it traverses as code. It will also
    follow both code paths at any branch. This is not an emulator, however, so
    it is not able to tell if there is any self-modifying code. Any blocks of
    code that aren't reached will require additional traces. When tracing is
    finished, the results can be applied to the segment to mark as data or
    code.

    """

    new_file_text = ["Blank Atari DOS 2 SD (90K) Image", "Blank Atari DOS 2 DD (180K) Image", "Blank Atari DOS 2 ED (130K) Image", "Blank Apple DOS 3.3 Image"]

    editor_id = "omnivore.byte_edit"

    pane_layout_version = pane_layout.pane_layout_version

    hex_grid_lower_case = Bool(True)

    assembly_lower_case = Bool(False)

    #### Task interface #######################################################

    id = editor_id + "." + pane_layout_version if pane_layout_version else editor_id
    name = 'Byte Editor'

    preferences_helper = ByteEditPreferences

    #### Menu events ##########################################################

    machine_menu_changed = Event

    emulator_changed = Event

    segments_changed = Event

    # Must use different trait event in order for actions populated in the
    # dynamic menu (set by segments_changed event above) to have their radio
    # buttons updated properly
    segment_selected = Event

    ui_layout_overrides = {
        "menu": {
            "order": ["File", "Edit", "View", "Bytes", "Segment", "Disk Image", "Documents", "Window", "Help"],
            "View": ["PredefinedGroup", "ProcessorGroup", "AssemblerGroup", "MemoryMapGroup", "ColorGroup", "FontGroup", "BitmapGroup", "ZoomGroup", "ChangeGroup", "ConfigGroup", "ToggleGroup", "TaskGroup", "DebugGroup"],
            "Bytes": ["HexModifyGroup"],
            "Segment": ["ListGroup", "ActionGroup"],
            "Disk Image": ["ParserGroup", "EmulatorGroup", "ActionGroup"],
        },
    }

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _hex_grid_lower_case_default(self):
        prefs = self.preferences
        return prefs.hex_grid_lower_case

    def _assembly_lower_case_default(self):
        prefs = self.preferences
        return prefs.assembly_lower_case

    def _default_layout_default(self):
        return pane_layout.pane_layout()

    def create_dock_panes(self):
        return pane_layout.pane_create()

    def _active_editor_changed(self, editor):
        # Make sure it's a valid document before refreshing
        if editor is not None and editor.document.segments:
            editor.rebuild_ui()

    def _tool_bars_default(self):
        toolbars = []
        modes = []
        for v in self.known_viewers:
            modes.extend(v.valid_mouse_modes)
        toolbars.append(get_toolbar_group("%s:Modes" % self.id, modes))
        toolbars.extend(FrameworkTask._tool_bars_default(self))
        return toolbars

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, task_arguments="", **kwargs):
        """ Opens a new empty window
        """
        editor = ByteEditor(task_arguments=task_arguments)
        return editor

    @on_trait_change('window.application.preferences_changed_event')
    def refresh_from_new_preferences(self):
        prefs = self.preferences
        self.hex_grid_lower_case = prefs.hex_grid_lower_case
        self.assembly_lower_case = prefs.assembly_lower_case
        e = self.active_editor
        if e is not None:
            e.process_preference_change(prefs)
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
            SaveAsImageAction(),
            ]

    def get_actions_Menu_Edit_UndoGroup(self):
        return [
            UndoAction(),
            RedoAction(),
            RevertToBaselineAction(),
            ]

    def get_actions_Menu_Edit_CopyPasteGroup(self):
        copy_special_actions = [
            CopyAsReprAction(),
            CopyAsCBytesAction()
            ]
        for v in self.known_viewers:
            copy_special_actions.extend([action_cls() for action_cls in v.copy_special])
        copy_special_actions.sort(key=lambda a:a.name)
        return [
            CutAction(),
            CopyAction(),
            SMenu(
                *copy_special_actions,
                id='copyspecial', name="Copy Special"),
            PasteAction(),
            SMenu(
                PasteAndRepeatAction(),
                PasteCommentsAction(),
                id='pastespecial', name="Paste Special"),
            ]

    def get_actions_Menu_Edit_SelectGroup(self):
        return [
            SelectAllAction(),
            SelectNoneAction(),
            SelectInvertAction(),
            SMenu(
                MarkSelectionAsCodeAction(),
                MarkSelectionAsDataAction(),
                MarkSelectionAsUninitializedDataAction(),
                MarkSelectionAsDisplayListAction(),
                MarkSelectionAsJumpmanLevelAction(),
                MarkSelectionAsJumpmanHarvestAction(),
                id="mark1", name="Mark Selection As"),
            ]

    def get_actions_Menu_Edit_FindGroup(self):
        return [
            FindAction(),
            FindAlgorithmAction(),
            FindNextAction(),
            # SMenu(
            #     FindCodeAction(),
            #     FindDataAction(),
            #     FindDisplayListAction(),
            #     FindJumpmanLevelAction(),
            #     FindJumpmanHarvestAction(),
            #     FindUninitializedAction(),
            #     id="sel1", name="Find Style", separator=False),
            FindToSelectionAction(),
            ]

    def get_actions_Menu_View_ConfigGroup(self):
        data_actions = []
        info_actions = []
        center_actions = []
        for v in self.known_viewers:
            if v.has_metadata_only:
                info_actions.append(AddViewerAction(viewer=v))
            else:
                data_actions.append(AddViewerAction(viewer=v))
                center_actions.append(ReplaceCenterViewerAction(viewer=v))
        return [
            SMenu(
                Group(
                    *center_actions,
                    id="a1", separator=True),
                id='ViewerChoiceSubmenu0', separator=True, name="Change Main Viewer"),
            SMenu(
                Group(
                    *data_actions,
                    id="a1", separator=True),
                id='ViewerChoiceSubmenu1', separator=False, name="Add Auxiliary Viewer"),
            SMenu(
                Group(
                    *info_actions,
                    id="a1", separator=True),
                id='ViewerChoiceSubmenu2', separator=False, name="Add Info Pane"),
            Separator(),
            ViewDiffHighlightAction(),
            TextFontAction(),
            ]

    def get_actions_Menu_View_PredefinedGroup(self):
        actions = []
        for m in machine.predefined['machine']:
            actions.append(PredefinedMachineAction(machine=m))
        return [
            SMenu(
                Group(
                    *actions,
                    id="a1", separator=True),
                id='MachineChoiceSubmenu1', separator=False, name="Predefined Machines"),
            ]

    def get_actions_Menu_View_ProcessorGroup(self):
        actions = []
        for r in machine.predefined['disassembler']:
            actions.append(ProcessorTypeAction(disassembler=r))
        return [
            SMenu(
                Group(
                    *actions,
                    id="a1", separator=True),
                id='mm1', separator=True, name="Processor"),
            ]

    def get_actions_Menu_View_AssemblerGroup(self):
        return [
            SMenu(
                AssemblerChoiceGroup(id="a2", separator=True),
                Group(
                    AddNewAssemblerAction(),
                    EditAssemblersAction(),
                    SetSystemDefaultAssemblerAction(),
                    id="a3", separator=True),
                id='mm2', separator=False, name="Assembler Syntax"),
            ]

    def get_actions_Menu_View_MemoryMapGroup(self):
        actions = []
        for r in machine.predefined['memory_map']:
            actions.append(MemoryMapAction(memory_map=r))
        return [
            SMenu(
                Group(
                    *actions,
                    id="a1", separator=True),
                id='mm3', separator=False, name="Memory Map"),
            ]

    def get_actions_Menu_View_ColorGroup(self):
        return [
            SMenu(
                Group(
                    ColorStandardAction(name="NTSC", color_standard=0),
                    ColorStandardAction(name="PAL", color_standard=1),
                    id="a0", separator=True),
                Group(
                    UseColorsAction(name="ANTIC Powerup Colors", colors=colors.powerup_colors()),
                    id="a1", separator=True),
                Group(
                    AnticColorAction(),
                    id="a2", separator=True),
                id='mm4', separator=False, name="Colors"),
            ]

    def get_actions_Menu_View_FontGroup(self):
        font_mapping_actions = self.get_font_mapping_actions()
        font_renderer_actions = []
        for r in machine.predefined['font_renderer']:
            font_renderer_actions.append(FontRendererAction(font_renderer=r))
        return [
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
            ]

    def get_actions_Menu_View_BitmapGroup(self):
        actions = []
        for r in machine.predefined['bitmap_renderer']:
            actions.append(BitmapRendererAction(bitmap_renderer=r))
        return [
            SMenu(
                Group(
                    *actions,
                    id="a1", separator=True),
                Group(
                    BitmapWidthAction(),
                    BitmapZoomAction(),
                    id="a1", separator=True),
                id='mm7', separator=False, name="Bitmap Display"),
            ]

    def get_actions_Menu_DiskImage_EmulatorGroup(self):
        return [
            RunEmulatorAction(),
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
            ExpandDocumentAction(),
            Separator(),
            LoadBaselineVersionAction(),
            FindNextBaselineDiffAction(),
            FindPrevBaselineDiffAction(),
            ListDiffAction(),
            Separator(),
            SegmentGotoAction(),
            ]

    def get_actions_Menu_Segment_ListGroup(self):
        return [
            SMenu(
                SegmentChoiceGroup(id="a2", separator=True),
                id='segmentlist1', separator=False, name="View Segment"),
            ]

    def get_actions_Menu_Segment_ActionGroup(self):
        return [
            GetSegmentFromSelectionAction(),
            MultipleSegmentsFromSelectionAction(),
            InterleaveSegmentsAction(),
            SetSegmentOriginAction(),
            Separator(),
            AddCommentAction(),
            RemoveCommentAction(),
            AddLabelAction(),
            RemoveLabelAction(),
            SMenu(
                Group(
                    ImportSegmentLabelsAction(name="Import"),
                    id="sl1", separator=True),
                Group(
                    ExportSegmentLabelsAction(name="Export User Defined Labels"),
                    ExportSegmentLabelsAction(name="Export All Labels", include_disassembly_labels=True),
                    id="sl2", separator=True),
                id='segmentlabels1', separator=False, name="Manage Segment Labels"),
            Separator(),
            StartTraceAction(),
            AddTraceStartPointAction(),
            ApplyTraceSegmentAction(),
            ClearTraceAction(),
            ]

    def get_actions_Menu_Bytes_HexModifyGroup(self):
        return [
            ZeroAction(),
            FFAction(),
            NOPAction(),
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
            RandomBytesAction(),
            Separator(),
            ReverseSelectionAction(),
            ReverseGroupAction(),
            ]

    def get_keyboard_actions(self):
        return [
            FindPrevAction(),
            CancelMinibufferAction(),
            UndoCursorPositionAction(),
            RedoCursorPositionAction(),
            ]

    ###

    @property
    def known_viewers(self):
        viewers = self.window.application.get_extensions('omnivore8bit.viewers')
        return viewers

    def find_viewer_by_name(self, name):
        for v in self.known_viewers:
            if v.check_name(name):
                return v
        raise ValueError

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
