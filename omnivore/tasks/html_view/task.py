""" Html Viewer

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

from omnivore.framework.task import FrameworkTask
from omnivore.framework.actions import *
from html_viewer import HtmlViewer
from preferences import HtmlViewPreferences
import pane_layout


class HtmlViewTask(FrameworkTask):
    """ Static HTML viewer
    """

    new_file_text = ""

    editor_id = "omnivore.htmlview"

    pane_layout_version = pane_layout.pane_layout_version

    doc_hint = "skip"

    #### Task interface #######################################################

    id = editor_id
    name = 'HTML Viewer'

    preferences_helper = HtmlViewPreferences

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _default_layout_default(self):
        return pane_layout.pane_layout()

    def create_dock_panes(self):
        return pane_layout.pane_create()

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, **kwargs):
        """ Opens a new empty window
        """
        editor = HtmlViewer()
        return editor

    ###
    @classmethod
    def can_edit(cls, document):
        return document.metadata.mime == "text/html"

    @classmethod
    def get_match_score(cls, guess):
        """Return a number based on how good of a match this task is to the
        incoming FileGuess.
        
        0 = generic match
        ...
        10 = absolute match
        """
        if guess.metadata.mime == "text/html":
            return 10
        return 1
