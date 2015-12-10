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

from omnimon.framework.actions import *
from map_editor import MapEditor
from preferences import MapEditPreferences
from commands import *
from omnimon.tasks.hex_edit.task import HexEditTask
from omnimon.tasks.hex_edit.actions import *
import pane_layout
import omnimon.utils.wx.fonts as fonts
from omnimon.utils.binutil import known_segment_parsers
import omnimon.utils.colors as colors


class MapEditTask(HexEditTask):
    """ Tile-based map editor
    """

    new_file_text = "Map File"

    #### Task interface #######################################################

    id = pane_layout.task_id_with_pane_layout
    name = 'Map Editor'
    
    preferences_helper = MapEditPreferences
    
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
        tiles_menu = self.create_menu("Menu", "Tiles", "TileModifyGroup")
        actions = [
            # Menubar additions
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

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = MapEditor()
        return editor
    
    def get_actions_Menu_View_ViewConfigGroup(self):
        return self.get_common_ViewConfigGroup()

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
        if guess.metadata.uri.endswith("Getaway!.xex"):
            return 10
        return 0
