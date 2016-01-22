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

from omnivore.framework.task import FrameworkTask
from styled_text_editor import StyledTextEditor
from preferences import TextEditPreferences

class TextEditTask(FrameworkTask):
    """ A simple task for opening a blank editor.
    """

    new_file_text = "Text File"

    #### Task interface #######################################################

    id = 'omnivore.framework.text_edit_task'
    name = 'Text Editor'
    
    preferences_helper = TextEditPreferences

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = StyledTextEditor()
        return editor

    ###
    @classmethod
    def can_edit(cls, document):
        return document.metadata.mime.startswith("text/")
