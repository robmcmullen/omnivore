""" Text editor sample task

"""
# Enthought library imports.
from pyface.api import ImageResource, ConfirmationDialog, FileDialog, \
    ImageResource, YES, OK, CANCEL
from pyface.action.api import StatusBarManager, Action, ActionItem, Group, Separator
from pyface.tasks.api import Task, TaskWindow, TaskLayout, TaskWindowLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, EditorAction, TaskToggleGroup
from traits.api import on_trait_change, Property, Instance, Bool, Str, Unicode, Any, List

from peppy2.dock_panes import FileBrowserPane

class NewFileAction(Action):
    """ An action for creating a new empty file that can be edited by a particular task
    """
    tooltip = Property(Unicode, depends_on='name')

    task_cls = Any
    
    def perform(self, event=None):
        task = event.task.window.application.find_or_create_task_of_type(self.task_cls)
        task.new()

    def _get_tooltip(self):
        return u'Open a new %s' % self.name

class NewFileGroup(Group):
    """ A menu for creating a new file for each type of task
    """

    #### 'ActionManager' interface ############################################

    id = 'NewFileGroup'
    
    items = List

    #### 'TaskChangeMenuManager' interface ####################################

    # The ActionManager to which the group belongs.
    manager = Any

    # The window that contains the group.
    application = Instance('envisage.ui.tasks.api.TasksApplication')
        
    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self):
        items = []
        for factory in self.application.task_factories:
            if hasattr(factory.factory, 'new_file_text'):
                task_cls = factory.factory
                if task_cls.new_file_text:
                    action = NewFileAction(name=task_cls.new_file_text, task_cls=task_cls)
                    items.append((task_cls.new_file_text, ActionItem(action=action)))
        items.sort()
        items = [i[1] for i in items]
        return items

    def _rebuild(self):
        # Clear out the old group, then build the new one.
        self.destroy()
        self.items = self._get_items()

        # Inform our manager that it needs to be rebuilt.
        self.manager.changed = True
        
    #### Trait initializers ###################################################

    def _items_default(self):
        self.application.on_trait_change(self._rebuild, 'task_factories[]')
        return self._get_items()

    def _manager_default(self):
        manager = self
        while isinstance(manager, Group):
            manager = manager.parent
        return manager
    
    def _application_default(self):
        return self.manager.controller.task.window.application


class OpenAction(Action):
    name = 'Open'
    accelerator = 'Ctrl+O'
    tooltip = 'Open a file'
    image = ImageResource('file_open')

    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control)
        if dialog.open() == OK:
            event.task.window.application.load_file(dialog.path, event.task)

class SaveAction(EditorAction):
    name = 'Save'
    accelerator = 'Ctrl+S'
    tooltip = 'Save the current file'
    image = ImageResource('file_save')
    enabled_name = 'dirty' # enabled based on state of task.active_editor.dirty

    def perform(self, event):
        event.task.save_file(None)

class SaveAsAction(EditorAction):
    name = 'Save As...'
    accelerator = 'Ctrl+Shift+S'
    tooltip = 'Save the current file with a new name'
    image = ImageResource('file_save_as')

    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control, action='save as')
        if dialog.open() == OK:
            event.task.save_file(dialog.path)

class ExitAction(Action):
    name = 'Quit'
    accelerator = 'Ctrl+Q'
    tooltip = 'Quit the program'
    menu_role = "Quit"

    def perform(self, event):
        event.task.window.application.exit()

class PreferencesAction(Action):
    name = 'Preferences...'
    tooltip = 'Program settings and configuration options'
    menu_role = "Preferences"

    def perform(self, event):
        from envisage.ui.tasks.preferences_dialog import \
            PreferencesDialog

        window = event.task.window
        dialog = window.application.get_service(PreferencesDialog)
        ui = dialog.edit_traits(parent=window.control, kind='livemodal')

        if ui.result:
            window.application.preferences.save()

class AboutAction(Action):
    name = 'About...'
    tooltip = 'About this program'
    menu_role = "About"

    def perform(self, event):
        print "peform: %s" % self.name

class NewViewAction(EditorAction):
    name = 'New View of Current Tab'
    tooltip = 'New view of the project in the current tab'

    def perform(self, event):
        event.task.new_window(view=event.task.active_editor)

class NewWindowAction(Action):
    name = 'New Window'
    tooltip = 'Open a new window'

    def perform(self, event):
        event.task.new_window()

class FrameworkTask(Task):
    """ A simple task for opening a blank editor.
    """
    
    # Class properties (not traits!)
    
    new_file_text = ''

    #### Task interface #######################################################

    id = 'peppy.framework.framework_task'
    name = 'Framework'

    icon = Instance(ImageResource)

    active_editor = Property(Instance(IEditor),
                             depends_on='editor_area.active_editor')

    editor_area = Instance(IEditorAreaPane)
    
    ###########################################################################
    # 'Task' interface.
    ###########################################################################
    
    def _icon_default(self):
        return ImageResource('peppy48')

    def _menu_bar_default(self):
        return SMenuBar(SMenu(Separator(id="NewGroup", separator=False),
                              SMenu(NewFileGroup(), id="NewFileGroup", name="New", before="NewGroupEnd", after="NewGroup"),
                              Separator(id="NewGroupEnd", separator=False),
                              Group(OpenAction(), id="OpenGroup"),
                              Separator(id="OpenGroupEnd", separator=False),
                              Group(
                                  SaveAction(),
                                  SaveAsAction(),
                                  id="SaveGroup"),
                              Separator(id="SaveGroupEnd", separator=False),
                              Group(ExitAction(), id="ExitGroup"),
                              id='File', name='&File'),
                        SMenu(Separator(id="PrefGroup", separator=False),
                              Group(PreferencesAction(), absolute_position="last"),
                              id='Edit', name='&Edit'),
                        SMenu(DockPaneToggleGroup(),
                              TaskToggleGroup(),
                              Separator(id="TaskGroupEnd"),
                              id='View', name='&View'),
                        SMenu(NewViewAction(),
                              NewWindowAction(),
                              id='Window', name='&Window'),
                        SMenu(AboutAction(),
                              id='Help', name='&Help'),
                        )

    def _tool_bars_default(self):
        open = OpenAction()
        save = SaveAction()
        return [ SToolBar(Group(TaskAction(method='new',
                                           tooltip='New file',
                                           image=ImageResource('file_new')),
                                open,
                                save,
                                TaskAction(method='debug',
                                           tooltip='Do some debug stuff',
                                           image=ImageResource('debug')),
                                id="File"),
                          show_tool_names=False), ]

    def _status_bar_default(self):
        return StatusBarManager(message="Hi!")

    def _default_layout_default(self):
        return TaskLayout(
            left=VSplitter(
                PaneItem('peppy.framework.file_browser_pane'),
                ))

    def activated(self):
        print "  status bar: %s" % self.status_bar
        active = self.active_editor
        if active:
            self.status_bar.message = active.name
        else:
            self.status_bar.message = self.name
        self.window.icon = self.icon

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

    def new(self, source=None, **kwargs):
        """ Opens a new tab
        
        :param source: optional :class:`FileGuess` or :class:`Editor` instance
        that will load a new file or create a new view of the existing editor,
        respectively.
        """
        editor = self.get_editor()
        self.editor_area.add_editor(editor)
        self.editor_area.activate_editor(editor)
        if hasattr(source, 'get_metadata') or source is None:
            editor.load(source, **kwargs)
        else:
            editor.view_of(source, **kwargs)
        self.activated()

    def new_window(self, task=None, view=None):
        """ Opens a new window
        
        With no arguments, opens an empty window with the default task.
        
        :keyword task: optional task to set the task of the new window
        
        :keyword view: optional :class:`Editor` instance that will set the
        task of the new window and will create a new view of the editor in the
        first tab
        """
        print "Opening new window!!!"
        window = self.window.application.create_window()
        print "  window=%s" % str(window)
        print "  self=%s" % str(self.window)
        print "  task type: %s" % str(task)
        print "  view of: %s" % str(view)
        if view is not None:
            task_cls = view.editor_area.task.__class__
        elif task is not None:
            if isinstance(task, FrameworkTask):
                task_cls = task.__class__
            else:
                task_cls = task
        else:
            task_cls = FrameworkTask
        task = task_cls()
        window.add_task(task)
        window.activate_task(task)
        if view is not None:
            task.new(view)
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

    def debug(self):
        """Debug stuff!
        """
        action_schemas = list(self.menu_bar.items)
        action_schemas.extend(self.tool_bars)
        for action in self._iter_schema_items(action_schemas):
            if hasattr(action, 'name'):
                action.name = action.name + "!"
    
    def process_idle(self):
        self.update_actions()

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self):
        raise NotImplementedError

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _iter_schema_items(self, items):
        """Generator to pull all Actions out of the list of Schemas
        
        Schemas may contain other schemas, which requires this recursive
        approach.
        
        Usage:
            action_schemas = list(self.menu_bar.items)
            action_schemas.extend(self.tool_bars)
            for action in self._iter_schema_items(action_schemas):
                # do something
        """
        for item in items:
            if hasattr(item, 'items'):
                for a in self._iter_schema_items(item.items):
                    yield a
            else:
                yield item

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
