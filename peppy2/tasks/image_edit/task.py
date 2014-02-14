"""Image editor sample task

"""
# Enthought library imports.
from pyface.api import ImageResource
from pyface.tasks.api import Task, TaskWindow, TaskLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, TaskToggleGroup
from traits.api import on_trait_change, Property, Instance


from peppy2.framework.task import FrameworkTask
from panes import Pane1, Pane2, Pane3
from bitmap_editor import BitmapEditor

class ImageEditTask(FrameworkTask):
    """ A simple task for opening a blank editor.
    """

    #### Task interface #######################################################

    id = 'peppy.framework.image_edit_task'
    name = 'Image Editor'

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _default_layout_default(self):
        return TaskLayout(
            top=HSplitter(
                PaneItem('image_edit.pane1'),
                PaneItem('image_edit.pane2'),
                PaneItem('image_edit.pane3'),
                ))

    def create_dock_panes(self):
        """ Create the file browser and connect to its double click event.
        """
        return [ Pane1(), Pane2(), Pane3() ]

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = BitmapEditor()
        return editor

    ###
    @classmethod
    def can_edit(cls, mime):
        return mime == "image/jpeg" or mime == "image/png"
