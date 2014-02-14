======================
Tasks and Applications
======================

The TaskApplication (envisage/ui/tasks/tasks_application.py, direct subclass
of Application from envisage/application.py) includes a set of traits for
managing the application:

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

Q: How do we get a reference to the application?
A: through the TaskWindow: TaskWindow.application

Q: How do we create a new top-level window?
A: TaskApplication.create_window
