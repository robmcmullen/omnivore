""" Text editor sample task

"""
# Enthought library imports.
from pyface.api import ImageResource, ConfirmationDialog, FileDialog, \
    ImageResource, YES, OK, CANCEL
from pyface.action.api import Action
from pyface.tasks.api import Task, TaskWindow, TaskLayout, TaskWindowLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, TaskToggleGroup
from traits.api import on_trait_change, Property, Instance

from peppy2.dock_panes import FileBrowserPane

class OpenAction(Action):
    name = 'Open'
    accelerator = 'Ctrl+O'
    tooltip = 'Open a File'
    image = ImageResource('document_open')

    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control)
        if dialog.open() == OK:
            event.task.window.application.load_file(dialog.path, event.task)

class FrameworkTask(Task):
    """ A simple task for opening a blank editor.
    """

    #### Task interface #######################################################

    id = 'peppy.framework.framework_task'
    name = 'Framework'

    active_editor = Property(Instance(IEditor),
                             depends_on='editor_area.active_editor')

    editor_area = Instance(IEditorAreaPane)
    
#    tool_bars = [ SToolBar(TaskAction(method='new',
#                                      tooltip='New file',
#                                      image=ImageResource('document_new')),
#                           TaskAction(method='open',
#                                      tooltip='Open a file',
#                                      image=ImageResource('document_open')),
#                           TaskAction(method='save',
#                                      tooltip='Save the current file',
#                                      image=ImageResource('document_save')),
#                           image_size = (32, 32)), ]

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _menu_bar_default(self):
        open = OpenAction()
        return SMenuBar(SMenu(TaskAction(name='New', method='new',
                                         accelerator='Ctrl+N'),
                              open,
                              TaskAction(name='Save', method='save',
                                         accelerator='Ctrl+S'),
                              TaskAction(name='Exit', method='exit',
                                         accelerator='Ctrl+Q'),
                              id='File', name='&File'),
                        SMenu(id='Edit', name='&Edit'),
                        SMenu(#DockPaneToggleGroup(),
                              TaskToggleGroup(),
                              id='View', name='&View'),
                        SMenu(TaskAction(name='New Window', method='new_window',
                                         accelerator='Ctrl+W'),
                              id='Window', name='&Window'),
                        )

    def _tool_bars_default(self):
        open = OpenAction()
        return [ SToolBar(TaskAction(method='new',
                                      tooltip='New file',
                                      image=ImageResource('document_new')),
                           open,
                           TaskAction(method='save',
                                      tooltip='Save the current file',
                                      image=ImageResource('document_save')),
                           show_tool_names=False), ]

    def _default_layout_default(self):
        return TaskLayout(
            left=VSplitter(
                PaneItem('peppy.framework.file_browser_pane'),
                ))

    def create_central_pane(self):
        """ Create the central pane: the text editor.
        """
        self.editor_area = EditorAreaPane()
        return self.editor_area

    def create_dock_panes(self):
        """ Create the file browser and connect to its double click event.
        """
        browser = FileBrowserPane()
        handler = lambda: self.window.application.load_file(browser.selected_file, self)
        browser.on_trait_change(handler, 'activated')
        return [ browser ]

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def new(self, guess=None):
        """ Opens a new tab
        """
        editor = self.get_editor()
        self.editor_area.add_editor(editor)
        self.editor_area.activate_editor(editor)
        editor.load(guess)
        self.activated()

    def new_window(self):
        """ Opens a new empty window
        """
        print "Opening new window!!!"
        window = self.window.application.create_window()
        print "  window=%s" % str(window)
        print "  self=%s" % str(self.window)
        task = FrameworkTask()
        window.add_task(task)
        window.activate_task(task)
        window.open()
        print "All windows: %s" % self.window.application.windows

    def save(self):
        """ Attempts to save the current file, prompting for a path if
            necessary. Returns whether the file was saved.
        """
        editor = self.active_editor
        try:
            editor.save()
        except IOError:
            # If you are trying to save to a file that doesn't exist, open up a
            # FileDialog with a 'save as' action.
            dialog = FileDialog(parent=self.window.control,
                                action='save as')
            if dialog.open() == OK:
                editor.save(dialog.path)
            else:
                return False
        return True

    def exit(self):
        """ Opens a new empty window
        """
        print "Quitting!!!"
        self.window.application.exit()

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        raise NotImplementedError

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _prompt_for_save(self):
        """ Prompts the user to save if necessary. Returns whether the dialog
            was cancelled.
        """
        dirty_editors = dict([(editor.name, editor)
                              for editor in self.editor_area.editors
                              if editor.dirty])
        if not dirty_editors.keys():
            return True
        message = 'You have unsaved files. Would you like to save them?'
        dialog = ConfirmationDialog(parent=self.window.control,
                                    message=message, cancel=True,
                                    default=CANCEL, title='Save Changes?')
        result = dialog.open()
        if result == CANCEL:
            return False
        elif result == YES:
            for name, editor in dirty_editors.items():
                editor.save(editor.path)
        return True

    #### Trait change handlers ################################################

    @on_trait_change('window:closing')
    def _prompt_on_close(self, event):
        """ Prompt the user to save when exiting.
        """
        close = self._prompt_for_save()
        event.veto = not close

    #### Trait property getter/setters ########################################

    def _get_active_editor(self):
        if self.editor_area is not None:
            return self.editor_area.active_editor
        return None


    ###
    @classmethod
    def can_edit(cls, mime):
        raise NotImplementedError
