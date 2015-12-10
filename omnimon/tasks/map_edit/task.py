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
    
    def get_actions(self, location, menu_name, group_name):
        if location == "Menu":
            if menu_name == "View":
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
                                *font_mapping_actions,
                                id="a2", separator=True),
                            Group(
                                FontMappingWidthAction(),
                                id="a3", separator=True),
                            id='FontChoiceSubmenu2a1', separator=True, name="Char Map"),
                        SMenu(
                            Group(
                                UseColorsAction(name="Powerup Colors", colors=colors.powerup_colors()),
                                id="a1", separator=True),
                            Group(
                                AnticColorAction(),
                                id="a2", separator=True),
                            id='FontChoiceSubmenu2a', separator=True, name="Antic Colors"),
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
