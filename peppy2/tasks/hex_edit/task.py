""" Text editor sample task

"""
# Enthought library imports.
from pyface.api import ImageResource, ConfirmationDialog, FileDialog, \
    ImageResource, YES, OK, CANCEL
from pyface.action.api import Action, ActionItem
from pyface.tasks.api import Task, TaskWindow, TaskLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, TaskToggleGroup, EditorAction
from traits.api import on_trait_change, Property, Instance, Any, Event

from peppy2.framework.task import FrameworkTask
from peppy2.framework.actions import TaskDynamicSubmenuGroup
from hex_editor import HexEditor
from preferences import HexEditPreferences
import panes
import peppy2.utils.fonts as fonts

class FontChoiceGroup(TaskDynamicSubmenuGroup):
    """ A menu for changing the active task in a task window.
    """

    #### 'ActionManager' interface ############################################

    id = 'FontChoiceGroup'

    #### 'DynamicSubmenuGroup' interface ######################################

    event_name = 'fonts_changed'

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self, *args, **kwargs):
        items = []
        action = UseFontAction(font=fonts.A8DefaultFont)
        items.append(ActionItem(action=action))
        action = UseFontAction(font=fonts.A8ComputerFont)
        items.append(ActionItem(action=action))
            
        return items

class UseFontAction(EditorAction):
    font = Any
    
    def _name_default(self):
        return "%s" % (self.font['name'])
    
    def perform(self, event):
        self.active_editor.set_font(self.font)


class HexEditTask(FrameworkTask):
    """ A simple task for opening a blank editor.
    """

    new_file_text = "Binary File"

    #### Task interface #######################################################

    id = 'peppy.framework.hex_edit_task'
    name = 'Hex Editor'
    
    preferences_helper = HexEditPreferences
    
    #### Menu events ##########################################################
    
    fonts_changed = Event

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _default_layout_default(self):
        return TaskLayout(
            right=HSplitter(
                PaneItem('hex_edit.mos6502_disasmbly_pane'),
                PaneItem('hex_edit.byte_graphics'),
                PaneItem('hex_edit.font_map'),
                ),
            )

    def create_dock_panes(self):
        """ Create the file browser and connect to its double click event.
        """
        return [
            panes.MOS6502DisassemblyPane(),
            panes.ByteGraphicsPane(),
            panes.FontMapPane(),
            ]


    def _active_editor_changed(self, editor):
        print "active editor changed to ", editor
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
                        SMenu(FontChoiceGroup(),
                            id='FontChoiceSubmenu', name="Font"),
                        ]

    ###
    @classmethod
    def can_edit(cls, mime):
        return mime == "application/octet-stream"
