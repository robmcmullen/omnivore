""" Text editor sample task

"""
# Enthought library imports.
from pyface.api import ImageResource, ConfirmationDialog, FileDialog, \
    ImageResource, YES, OK, CANCEL
from pyface.action.api import Action
from pyface.tasks.api import Task, TaskWindow, TaskLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, TaskToggleGroup
from traits.api import on_trait_change, Property, Instance

from peppy2.framework.task import FrameworkTask
from hex_editor import HexEditor
from preferences import HexEditPreferences
import panes

class HexEditTask(FrameworkTask):
    """ A simple task for opening a blank editor.
    """

    new_file_text = "Binary File"

    #### Task interface #######################################################

    id = 'peppy.framework.hex_edit_task'
    name = 'Hex Editor'
    
    preferences_helper = HexEditPreferences

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

    ###
    @classmethod
    def can_edit(cls, mime):
        return mime == "application/octet-stream"
