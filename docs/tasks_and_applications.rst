======================
Tasks and Applications
======================

The TaskApplication (envisage/ui/tasks/tasks_application.py, direct subclass
of Application from envisage/application.py) includes a set of traits for
managing the application::

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

among others.

:Q: How do we get a reference to the application?
:A: through the TaskWindow: TaskWindow.application

:Q: How do we create a new top-level window?
:A: TaskApplication.create_window


Determining the TaskWindow
==========================

A reference to the TaskWindow is kept in the Task instance.  Here's how to
access the task window from:

:Task: self.window
:Editor: self.editor_area.task.window
:TaskAction event handler: event.task.window.
:EditorAction event handler: self.active_editor.task.window


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
