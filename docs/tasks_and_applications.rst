======================
Tasks and Applications
======================


Configuration Directory
=======================

Omnivore changes the default configuration directory from
:file:`$(HOME)/.enthought/omnivore.framework.application` to
:file:`$(HOME)/.config/Omnivore` on unix. On Mac OS X it will be :file:`$(HOME)/Library/Application Support/Omnivore`, and windows will be :file:`C:\\Users\\<username>\\AppData\\Local\\Omnivore\\Omnivore`

TaskApplication
===============

* source: envisage/envisage/ui/tasks/tasks_application.py
* direct subclass of Application: envisage/envisage/application.py

Traits Summary
--------------

    # The active task window (the last one to get focus).
    active_window = Instance(TaskWindow)

    # The PyFace GUI for the application.
    gui = Instance(GUI)

    # Icon for the whole application. Will be used to override all taskWindows 
    # icons to have the same.
    icon = Instance(ImageResource, allow_none=True) #Any

    # The name of the application (also used on window title bars).
    name = Unicode

    # The splash screen for the application. By default, there is no splash
    # screen.
    splash_screen = Instance(SplashScreen)

    # The directory on the local file system used to persist window layout
    # information.
    state_location = Directory

    # Contributed task factories. This attribute is primarily for run-time
    # inspection; to instantiate a task, use the 'create_task' method.
    task_factories = ExtensionPoint(id=TASK_FACTORIES)

    # Contributed task extensions.
    task_extensions = ExtensionPoint(id=TASK_EXTENSIONS)

    # The list of task windows created by the application.
    windows = List(TaskWindow)

    # The factory for creating task windows.
    window_factory = Callable(TaskWindow)

    #### Application layout ###################################################

    # The default layout for the application. If not specified, a single window
    # will be created with the first available task factory.
    default_layout = List(TaskWindowLayout)

    # Whether to always apply the default *application level* layout when the
    # application is started. Even if this is False, the layout state of
    # individual tasks will be restored.
    always_use_default_layout = Bool(False)

    #### Application lifecycle events #########################################

    # Fired after the initial windows have been created and the GUI event loop
    # has been started.
    application_initialized = Event

    # Fired immediately before the extant windows are destroyed and the GUI
    # event loop is terminated.
    application_exiting = Event

    # Fired when a task window has been created.
    window_created = Event(TaskWindowEvent)

    # Fired when a task window is opening.
    window_opening = Event(VetoableTaskWindowEvent)

    # Fired when a task window has been opened.
    window_opened = Event(TaskWindowEvent)

    # Fired when a task window is closing.
    window_closing = Event(VetoableTaskWindowEvent)

    # Fired when a task window has been closed.
    window_closed = Event(TaskWindowEvent)


:Q: How do we get a reference to the application?
:A: through the TaskWindow: TaskWindow.application

:Q: How do we create a new top-level window?
:A: TaskApplication.create_window

:Q: How do you specify the size of a top-level window?
:A: TaskApplication.create_window(TaskWindowLayout(size = (800, 600)))


TaskWindow
==========

* source: envisage/envisage/ui/tasks/task_window.py
* direct subclass of pyface's TaskWindow: pyface/pyface/tasks/task_window.py

Traits Summary
--------------

    # From envisage.ui.tasks.TaskWindow:
    
    # The application that created and is managing this window.
    application = Instance('envisage.ui.tasks.api.TasksApplication')

    # The window's icon.  We override it so it can delegate to the application
    # icon if the window's icon is not set.
    icon = Property(Instance(ImageResource), depends_on='_icon')

    # From pyface.tasks.task_window.TaskWindow:

    #### IWindow interface ####################################################

    # Unless a title is specifically assigned, delegate to the active task.
    title = Property(Unicode, depends_on='active_task, _title')

    #### TaskWindow interface ################################################

    # The pane (central or dock) in the active task that currently has focus.
    active_pane = Instance(ITaskPane)

    # The active task for this window.
    active_task = Instance(Task)

    # The list of all tasks currently attached to this window. All panes of the
    # inactive tasks are hidden.
    tasks = List(Task)

    # The central pane of the active task, which is always visible.
    central_pane = Instance(ITaskPane)

    # The list of all dock panes in the active task, which may or may not be
    # visible.
    dock_panes = List(IDockPane)

    # The factory for the window's TaskActionManagerBuilder, which is
    # instantiated to translate menu and tool bar schemas into Pyface action
    # managers. This attribute can overridden to introduce custom logic into
    # the translation process, although this is not usually necessary.
    action_manager_builder_factory = Callable(TaskActionManagerBuilder)

Task
====

* source: pyface/pyface/tasks/task.py

Traits Summary
--------------

    # The task's identifier.
    id = Str

    # The task's user-visible name.
    name = Unicode

    # The default layout to use for the task. If not overridden, only the
    # central pane is displayed.
    default_layout = Instance(TaskLayout, ())

    # A list of extra IDockPane factories for the task. These dock panes are
    # used in conjunction with the dock panes returned by create_dock_panes().
    extra_dock_pane_factories = List(Callable)

    # The window to which the task is attached. Set by the framework.
    window = Instance('pyface.tasks.task_window.TaskWindow')

    #### Actions ##############################################################

    # The menu bar for the task.
    menu_bar = Instance(MenuBarSchema)

    # The (optional) status bar for the task.
    status_bar = Instance(StatusBarManager)

    # The list of tool bars for the tasks.
    tool_bars = List(ToolBarSchema)

    # A list of extra actions, groups, and menus that are inserted into menu
    # bars and tool bars constructed from the above schemas.
    extra_actions = List(SchemaAddition)

Determining the TaskWindow
--------------------------

A reference to the TaskWindow is kept in the Task instance.  Here's how to
access the task window from:

:Task: self.window
:Editor: self.editor_area.task.window
:TaskAction event handler: event.task.window.
:EditorAction event handler: self.active_editor.task.window

Blank Window
------------

If you get a blank window, that probably means that no tasks have
been added to the window.  One way this happens is a bad application
memento in the config directory.  In once case, removing the file
:file:`/home/rob/.config/Omnivore/tasks/wx/application_memento` can fix it.  In
another case, an incorrect task id was found (due to a typo in the task id
itself) and the call to application.create_task(task_id) returned None.

Saving and Restoring Window Layout
----------------------------------

The Enthought framework saves the editor and pane layouts for every open window
at the time of application exit to try to restore the same layout at the next
application start.  This file is the application_memento file, as above.

If the window layout has changed in the program but an old version of the
layout is restored, not all panes may be visible, pane titles might still be
the old pane titles, etc.

To work around this without modifying the Enthought code to check for a version
number, you can simply change the Task's id to something previously unused and
the default layout as specified in the task will be used.

For instance, changing the Task.id from "example.task" to "example.task.v2"
will force the old layout to be discarded.


Error Reporting
===============

The TaskWindow includes several convenience methods to show standard dialogs::

    def confirm(self, message, title=None, cancel=False, default=NO):
        """ Convenience method to show a confirmation dialog.

        message is the text of the message to display.
        title is the text of the window title.
        cancel is set if the dialog should contain a Cancel button.
        default is the default button.
        """

    def information(self, message, title='Information'):
        """ Convenience method to show an information message dialog.

        message is the text of the message to display.
        title is the text of the window title.
        """

    def warning(self, message, title='Warning'):
        """ Convenience method to show a warning message dialog.

        message is the text of the message to display.
        title is the text of the window title.
        """

    def error(self, message, title='Error'):
        """ Convenience method to show an error message dialog.

        message is the text of the message to display.
        title is the text of the window title.
        """

The confirm dialog returns constants for OK, CANCEL, YES and NO, accessed by::

    from pyface.api import OK, CANCEL, YES, NO

Since all those constants are positive numbers, using something like::

    if confirm("Save file?"):
        save()

will not work as expected.  Instead, use::

    if confirm("Save file?") == YES:
        save()
