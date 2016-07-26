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
from jumpman_editor import JumpmanEditor
from commands import *
from omnivore.tasks.hex_edit.task import HexEditTask
from omnivore.tasks.hex_edit.actions import *
from omnivore.tasks.hex_edit.preferences import HexEditPreferences
import omnivore.arch.colors as colors
import pane_layout
from omnivore.framework.toolbar import get_toolbar_group


class JumpmanEditTask(HexEditTask):
    """ Jumpman level display decoder
    """

    new_file_text = "Jumpman Level"

    #### Task interface #######################################################

    id = pane_layout.task_id_with_pane_layout
    name = 'Jumpman Level Editor'
    
    preferences_helper = HexEditPreferences
    
    #### Menu events ##########################################################
    
    
    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _default_layout_default(self):
        return pane_layout.pane_layout()

    def create_dock_panes(self):
        return pane_layout.pane_create()

    def _extra_actions_default(self):
        data_menu = self.create_menu("Menu", "Disk Image", "ParserGroup", "EmulatorGroup", "ActionGroup")
        segment_menu = self.create_menu("Menu", "Segments", "SegmentGroup")
        actions = [
            # Menubar additions
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
            prefs = self.get_preferences()

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
            SelectAllAction(),
            SelectNoneAction(),
            SelectInvertAction(),
            ]
    
    def get_actions_Menu_Edit_FindGroup(self):
        return []

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
