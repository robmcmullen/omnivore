""" Skeleton sample task

"""
# Enthought library imports.
from pyface.api import ImageResource
from pyface.tasks.api import Task, TaskWindow, TaskLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, TaskToggleGroup
from traits.api import on_trait_change, Property, Instance

from panes import SkeletonPane1, SkeletonPane2, SkeletonPane3


class SkeletonTask(Task):
    """ A simple task for opening a blank editor.
    """

    #### Task interface #######################################################

    id = 'omnivore.framework.text_edit_task'
    name = 'Skeleton'

    active_editor = Property(Instance(IEditor),
                             depends_on='editor_area.active_editor')

    editor_area = Instance(IEditorAreaPane)

    menu_bar = SMenuBar(SMenu(TaskAction(name='New', method='new',
                                         accelerator='Ctrl+N'),
                              id='File', name='&File'),
                        SMenu(id='Edit', name='&Edit'),
                        SMenu(#DockPaneToggleGroup(),
                              TaskToggleGroup(),
                              id='View', name='&View'))

    tool_bars = [ SToolBar(TaskAction(method='new',
                                      tooltip='New file',
                                      image=ImageResource('document_new')),
                           image_size = (32, 32)), ]

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _default_layout_default(self):
        return TaskLayout(
            left=VSplitter(
                PaneItem('text_edit.pane1'),
                HSplitter(
                    PaneItem('text_edit.pane2'),
                    PaneItem('text_edit.pane3'),
                    ),
                ))

    def create_central_pane(self):
        """ Create the central pane: the text editor.
        """
        self.editor_area = EditorAreaPane()
        return self.editor_area

    def create_dock_panes(self):
        """ Create the file browser and connect to its double click event.
        """
        return [ SkeletonPane1(), SkeletonPane2(), SkeletonPane3() ]

    ###########################################################################
    # 'ExampleTask' interface.
    ###########################################################################

    def new(self):
        """ Opens a new empty window
        """
        editor = Editor()
        self.editor_area.add_editor(editor)
        self.editor_area.activate_editor(editor)
        self.activated()

    #### Trait property getter/setters ########################################

    def _get_active_editor(self):
        if self.editor_area is not None:
            return self.editor_area.active_editor
        return None
