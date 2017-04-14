""" Bitmap editor

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

from omnivore.framework.actions import *
from omnivore8bit.hex_edit.task import HexEditTask
from omnivore8bit.hex_edit.actions import *
from omnivore8bit.hex_edit.preferences import HexEditPreferences
import omnivore8bit.arch.colors as colors
from omnivore.framework.toolbar import get_toolbar_group

from jumpman_editor import JumpmanEditor
from commands import *
import pane_layout
from actions import *


class JumpmanEditTask(HexEditTask):
    """ Jumpman level display decoder
    """

    new_file_text = "Jumpman Level"

    editor_id = "omnivore.jumpman"

    pane_layout_version = pane_layout.pane_layout_version

    #### Task interface #######################################################

    id = editor_id + "." + pane_layout_version if pane_layout_version else editor_id
    name = 'Jumpman Level Editor'

    preferences_helper = HexEditPreferences

    #### Menu events ##########################################################

    ui_layout_overrides = {
        "menu": {
            "order": ["File", "Edit", "View", "Jumpman", "Disk Image", "Documents", "Window", "Help"],
            "Disk Image": ["ParserGroup", "EmulatorGroup", "ActionGroup"],
            "Jumpman":  ["LevelGroup", "SelectionGroup", "CustomCodeGroup"],
        },
    }

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _default_layout_default(self):
        return pane_layout.pane_layout()

    def create_dock_panes(self):
        return pane_layout.pane_create()

    def _tool_bars_default(self):
        toolbars = []
        toolbars.append(get_toolbar_group("%s:Modes" % self.id, JumpmanEditor.valid_mouse_modes))
        toolbars.extend(HexEditTask._tool_bars_default(self))
        return toolbars

    def pane_layout_initial_visibility(self):
        return pane_layout.pane_initially_visible()

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = JumpmanEditor()
        return editor

    @on_trait_change('window.application.preferences_changed_event')
    def refresh_from_new_preferences(self):
        e = self.active_editor
        if e is not None:
            prefs = self.preferences

    def get_actions_Menu_Edit_UndoGroup(self):
        return [
            UndoAction(),
            RedoAction(),
            ]

    def get_actions_Menu_Edit_CopyPasteGroup(self):
        return [
            CutAction(),
            CopyAction(),
            PasteAction(),
            ]

    def get_actions_Menu_Edit_SelectGroup(self):
        return [
            SelectAllJumpmanAction(),
            SelectNoneJumpmanAction(),
            SelectInvertJumpmanAction(),
            ]

    def get_actions_Menu_Edit_FindGroup(self):
        return [
            FlipVerticalAction(),
            FlipHorizontalAction(),
            ]

    def get_actions_Menu_View_ViewPredefinedGroup(self):
        return []

    def get_actions_Menu_View_ViewChangeGroup(self):
        return [
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
            ]

    def get_actions_Menu_Jumpman_LevelGroup(self):
        return [
            SMenu(
                LevelListGroup(id="a2", separator=True),
                id='segmentlist1', separator=False, name="Edit Level"),
            ]

    def get_actions_Menu_Jumpman_SelectionGroup(self):
        return [
            ClearTriggerAction(),
            SetTriggerAction(),
            ]

    def get_actions_Menu_Jumpman_CustomCodeGroup(self):
        return [
            AssemblySourceAction(),
            RecompileAction(),
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
        return 0
