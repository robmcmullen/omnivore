""" Map editor

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
from map_editor import MapEditor
from preferences import MapEditPreferences
from commands import *
from omnivore.tasks.hex_edit.task import HexEditTask
from omnivore.tasks.hex_edit.actions import *
import pane_layout
from omnivore.framework.toolbar import get_toolbar_group


class MapEditTask(HexEditTask):
    """ Tile-based map editor
    """

    new_file_text = "Map File"

    #### Task interface #######################################################

    id = pane_layout.task_id_with_pane_layout
    name = 'Map Editor'
    
    preferences_helper = MapEditPreferences
    
    #### Menu events ##########################################################
    
    
    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _default_layout_default(self):
        return pane_layout.pane_layout()

    def create_dock_panes(self):
        return pane_layout.pane_create()

    def _extra_actions_default(self):
        machine_menu = self.create_menu("Menu", "Machine", "MachineTypeGroup", "MachineCharacteristicsGroup", "MachineEmulatorGroup")
        segment_menu = self.create_menu("Menu", "Segments", "SegmentParserGroup", "SegmentGroup")
        tiles_menu = self.create_menu("Menu", "Tiles", "TileModifyGroup")
        actions = [
            # Menubar additions
            SchemaAddition(factory=lambda: machine_menu,
                           path='MenuBar',
                           after="Edit",
                           ),
            SchemaAddition(factory=lambda: segment_menu,
                           path='MenuBar',
                           after="Edit",
                           ),
            SchemaAddition(factory=lambda: tiles_menu,
                           path='MenuBar',
                           after="Edit",
                           ),
            ]
        return actions

    def _tool_bars_default(self):
        toolbars = []
        toolbars.append(get_toolbar_group("%s:Modes" % self.id, MapEditor.valid_mouse_modes))
        toolbars.extend(HexEditTask._tool_bars_default(self))
        return toolbars

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################
    
    def initialize_class_preferences(self):
        prefs = self.get_preferences()

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = MapEditor()
        return editor

    @on_trait_change('window.application.preferences_changed_event')
    def refresh_from_new_preferences(self):
        e = self.active_editor
        if e is not None:
            prefs = self.get_preferences()
    
    def get_actions_Menu_View_ViewConfigGroup(self):
        return self.get_common_ViewConfigGroup()

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
