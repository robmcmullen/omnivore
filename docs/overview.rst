================
Code Walkthrough
================

Basic Enthought Framework
=========================

Omnivore uses the Enthought framework to provide multi-window,
multi-frame user interface.  Enthought uses `Traits
<http://code.enthought.com/projects/traits/>`_ which provide python with typed
instance attributes of a class.  Traits are defined as class attributes, but
through an implicit __init__ method, each instance of the class gets instance
attributes as defined by these class attributes.  See `the Traits User Manual
<http://docs.enthought.com/traits/traits_user_manual/index.html>`_ for more.

Traits also have callback methods when they are changed, and this feature is
used occasionally in omnivore.  I'm getting away from some of this use in later
revisions, because it is not obvious that methods are called when an attribute
is set.

For instance, the trait ``window_opening`` is defined in envisage/ui/tasks/tasks_application.py::

    # Fired when a task window is opening.
    window_opening = Event(VetoableTaskWindowEvent)

so whenever a value is set on window_opening, a listener can be called.

Application
-----------

There is one instance of a
:class:`envisage.ui.tasks.tasks_application.TasksApplication` in an
Enthought app.  Everything in Enthought is configured through plugins,
then initialized in when the TasksApplication is instantiated.  In
:func:`omnivore.framework.application.run`, note the definition of the
plugins is a list that is extended with all the file recognizers in
:data:`omnivore.file_type.recognizers.plugins` and other plugins in the
:mod:`omnivore.pugins` module.

A TasksApplication is analogous to the wx.App in a normal wxpython project, and
in fact under the covers of Enthought there is a pointer to the wx.App used by
the TasksApplication.

Omnivore uses a subclass of the TasksApplication called the
:class:`omnivore.framework.FrameworkApplication`.  This is the class that is
instantiated in the :func:`omnivore.framework.application.run` function described
above, and contains some common functionality used by the Omnivore framework.

Task
----

A :class:`pyface.tasks.task.Task` is the Enthought terminology for a group of
UI items related to editing a particular type of file in a certain way.  It's
a place to put the definitions for menu bars, tool bars, sidebar panes, and
the tabbed central pane (each tab of which contains an editor control).  It
doesn't manage a window, but provides the place for the window to look when it
wants to populate itself with the UI.

It doesn't map one-to-one with a file type necessarily, there can be different
tasks to edit Python source code.  For instance, there could be a pure text
editing task, but there could also be a task to step through the file with a
debugger.  Each task could present its own user interface but edit the same
file type.

The omnivore subclass is the :class:`omnivore.framework.task.FrameworkTask`.  It
includes some convenience methods to define menu bars, as the normal Enthought
way to define menu bars is through plugins which is flexible but doesn't
handle menu item grouping well.

Tasks hold a reference to a :class:`envisage.ui.tasks.task_window.TaskWindow`
which is where the reference to the wx.Frame top level window is kept.

Editors
-------

Omnivore top level windows (the wx.Frame objects referenced by the
TaskWindow) contain menu bars, tool bars, sidebar panes, and a
tabbed central area that holds a set of editors that implement the
:class:`pyface.tasks.i_editor.IEditor` interface.  Omnivore's abstract base
class is the :class:`omnivore.framework.editor.FrameworkEditor` class, and must
be subclassed to provide a concrete implementation that knows how to perform
several functions: create the user interface control that can view/edit the
data, load and save the data in the control, undo/redo, and manage other
information that the task needs.

The editor requires a concrete FrameworkTask subclass that
provides a way to create a specific control (in this case the
:class:`omnivore.tasks.text_edit.styled_text_editor_wx.StyledTextEditor`) using
a ``get_editor`` method::

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = StyledTextEditor()
        return editor

and a ``can_edit`` class method that the framework uses to
connect a MIME type with that editor.  For example, see
:meth:`omnivore.tasks.text_edit.task.TextEditTask.can_edit`::

    @classmethod
    def can_edit(cls, mime):
        return mime.startswith("text/")

where it shows that this TextEditTask (and therefore the Editor linked to it)
can handle any MIME type that starts with "text/", e.g.: a plain text file
"text/plain", an HTML source file "text/html", a comma separated value file
"text/csv", etc.



Sidebar Panes
-------------

Preferences
-----------

Actions
-------




Advanced Enthought Framework
============================

Window Layout
-------------

The Enthought framework saves the editor and pane layouts for every open window
at the time of application exit to try to restore the same layout at the
next application start.  This file is the application_memento file (described
below).

If the window layout has changed in the program but an old version of the
layout is restored, not all panes may be visible, pane titles might still be
the old pane titles, etc.

To work around this without modifying the Enthought code to check for a version
number, you can simply change the Task's id to something previously unused and
the default layout as specified in the task will be used.

For instance, changing the Task.id from "example.task" to "example.task.v2"
will force the old layout to be discarded.

Blank Window
~~~~~~~~~~~~

If you get a blank window, that probably means that no tasks have
been added to the window.  One way this happens is a bad application
memento in the config directory.  In most cases, removing the file
:file:`/home/[user]/.config/Omnivore/tasks/wx/application_memento` can fix it.
In another case, an incorrect task id was found (due to a typo in the task id
itself) and the call to application.create_task(task_id) returned None.


Plugins
-------

Services
--------


Omnivore Framework
================

Loading Files
-------------

To load a file, the URI of the desired file is passed to the
:meth:`omnivore.framework.FrameworkApplication.load_file`, which tries to guess
the MIME type of the file by loading the first part of the file (currently the
first 1MB) using the :class:`omnivore.utils.file_guess.FileGuess` class, then
passed to through the :class:`omnivore.file_type.driver.FileRecognizerDriver`
using the :meth:`omnivore.file_type.driver.FileRecognizerDriver.recognizer`
method which loops through all the known recognizers to find the best match.
(The recognizer service is described in more detail later.) The MIME type
is stored in the FileGuess object, defaulting to ``application/octet-stream``
if unknown.

Once a MIME type is found, the set of tasks is examined to determine the subset
that can edit that MIME type.  The best match of the subset is used as the
default task, and an editor tab is opened in a window that is using that task's
UI.  Omnivore currently enforces the limitation that a window will only show one
task, so if no current windows are showing that task, a new window is opened.

Recognizing MIME Types
----------------------

