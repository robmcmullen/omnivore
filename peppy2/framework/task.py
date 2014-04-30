""" Text editor sample task

"""
# Enthought library imports.
from pyface.api import ImageResource, FileDialog, YES, OK, CANCEL
from pyface.action.api import StatusBarManager, Group, Separator
from pyface.tasks.api import Task, TaskWindow, TaskLayout, TaskWindowLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, TaskToggleGroup
from traits.api import provides, on_trait_change, Property, Instance, Bool, Str, Unicode, Int

from peppy2.dock_panes import FileBrowserPane
from peppy2.framework.i_about import IAbout
from peppy2.framework.actions import *
from peppy2.framework.status_bar_manager import FrameworkStatusBarManager

@provides(IAbout)
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
    
    status_bar_debug_width = Int(150)
    
    #### 'IAbout' interface ###################################################
    
    about_title = Unicode('Peppy2')
    
    about_version = Unicode
    
    about_description = Unicode('Edit stuff.')
    
    about_website = Str('http://peppy.flipturn.org')
    
    about_image = Instance(ImageResource, ImageResource('peppy128'))
    
    #### 'IErrorReporter' interface ###########################################
    
    error_email_from = Str
    
    error_email_passwd = Str
    
    error_email_to = Str
    
    def _about_version_default(self):
        from peppy2 import __version__
        return __version__
    
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
                        SMenu(Group(
                                  UndoAction(),
                                  RedoAction(),
                                  id="UndoGroup"),
                              Separator(id="UndoGroupEnd", separator=False),
                              Separator(id="PrefGroup", separator=False),
                              Group(PreferencesAction(), absolute_position="last"),
                              id='Edit', name='&Edit'),
                        SMenu(DockPaneToggleGroup(),
                              TaskToggleGroup(),
                              Separator(id="TaskGroupEnd"),
                              id='View', name='&View'),
                        SMenu(NewViewAction(),
                              NewWindowAction(),
                              id='Window', name='&Window'),
                        SMenu(Separator(id="AboutGroup", separator=False),
                              Group(AboutAction()),
                              Separator(id="DebugGroupStart"),
                              SMenu(TaskAction(name='Dynamic Menu Names', method='debug',
                                               tooltip='Do some debug stuff',
                                               image=ImageResource('debug')),
                                    id="Debug", name="Debug", before="DebugGroupEnd", after="DebugGroupStart"),
                              Separator(id="DebugGroupEnd", separator=False),
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
                          Group(UndoAction(),
                                RedoAction(),
                                id="Undo"),
                          show_tool_names=False), ]

    def _status_bar_default(self):
        return FrameworkStatusBarManager(message="Hi!", debug_width=self.status_bar_debug_width)

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
            if source is not None:
                self.window.application.successfully_loaded_event = source.metadata.uri
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
        task_id = None
        if view is not None:
            task_cls = view.editor_area.task.__class__
            print "  task_cls: %s" % str(task_cls)
        elif task is not None:
            if isinstance(task, FrameworkTask):
                task_cls = task.__class__
            else:
                task_cls = task
        else:
            task_id = self.window.application.startup_task
        if task_id is None:
            task = task_cls()
            task_id = task.id
        print "  task id: %s" % task_id
        print "  returned factory: %s" % self.window.application._get_task_factory(task_id)
        for factory in self.window.application.task_factories:
            print "    factory: %s, %s" % (factory.id, factory)
        
        task = self.window.application.create_task(task_id)
        print "  created task: %s" % task
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

    def allow_different_task(self, guess, other_task):
        """Hook to allow tasks to abort loading different task window.
        
        This method allows a hook to confirm that the user wants to load a file
        that can't be handled by the current task.  For example, this can be
        used to prompt with a dialog box.
        
        :rtype: Boolean; True means continue with the file load
        """
        return True

    def debug(self):
        """Debug stuff!
        """
        action_schemas = list(self.menu_bar.items)
        action_schemas.extend(self.tool_bars)
        for action in self._iter_schema_items(action_schemas):
            if hasattr(action, 'name'):
                action.name = action.name + "!"

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
        result = self.window.confirm(message=message, cancel=True,
                                    default=CANCEL, title='Save Changes?')
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
