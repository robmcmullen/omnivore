import os
import sys
import time
import argparse

from datetime import datetime
import fs
import wx

# Enthought library imports.
from traits.etsconfig.api import ETSConfig
from envisage.ui.tasks.api import TasksApplication
from envisage.ui.tasks.task_window_event import TaskWindowEvent, VetoableTaskWindowEvent
from pyface.api import ImageResource
from pyface.tasks.api import Task, TaskWindowLayout
from traits.api import provides, Bool, Instance, List, Property, Str, Unicode, Event, Dict, Int, Float, Tuple, Any, TraitError, Callable
from apptools.preferences.api import Preferences

# Local imports.
from .enthought_api import FrameworkTaskWindow
from .persistence import FilePersistenceMixin
from filesystem import init_filesystems
from document import BaseDocument
import documentation
from omnivore.help import get_htmlhelp, MissingDocumentationError
from omnivore.framework.preferences import FrameworkPreferences, \
    FrameworkPreferencesPane
from omnivore.utils.background_http import BackgroundHttpDownloader
import omnivore.utils.wx.error_logger as error_logger

import logging
log = logging.getLogger(__name__)


def _task_window_wx_on_mousewheel(self, event):
    if self.active_task and hasattr(self.active_task, '_wx_on_mousewheel_from_window'):
        log.debug("calling mousewheel in task %s" % self.active_task)
        self.active_task._wx_on_mousewheel_from_window(event)


class FrameworkApplication(TasksApplication, FilePersistenceMixin):
    """ The sample framework Tasks application.
    """

    #### 'IApplication' interface #############################################

    # The application's globally unique identifier.
    id = 'omnivore.framework.application'

    # The application's user-visible name.
    name = 'Omnivore'

    #### 'TasksApplication' interface #########################################

    # The default window-level layout for the application.
    default_layout = List(TaskWindowLayout)

    # Substitute the framework's TaskWindow so it can use the FrameworkActions
    # that don't use nearly as many traits as a pyface EditorAction
    window_factory = Callable(FrameworkTaskWindow)

    # Whether to restore the previous application-level layout when the
    # applicaton is started.
    always_use_default_layout = Property(Bool)

    #### 'FrameworkApplication' interface ####################################

    preferences_helper = Instance(FrameworkPreferences)

    startup_task = Str('omnivore.framework.text_edit_task')

    successfully_loaded_event = Event

    successfully_saved_event = Event

    plugin_event = Event

    preferences_changed_event = Event

    plugin_data = {}

    command_line_args = List

    log_dir = Str

    log_file_ext = Str

    cache_dir = Str

    user_data_dir = Str

    next_document_id = Int(0)

    document_class = Any

    documents = List

    last_clipboard_check_time = Float(-1)

    clipboard_check_interval = Float(.75)

    perspectives = Dict

    default_window_size = (800, 600)

    last_window_size = Tuple(default_window_size)

    downloader = Any

    ###########################################################################
    # Private interface.
    ###########################################################################

    #### Trait initializers ###################################################

    def _default_layout_default(self):
        active_task = self.preferences_helper.default_task
        log.debug("active task: -->%s<--" % active_task)
        if not active_task:
            active_task = self.startup_task
        log.debug("active task: -->%s<--" % active_task)
        log.debug("factories: %s" % " ".join([ factory.id for factory in self.task_factories]))
        tasks = [ factory.id for factory in self.task_factories if active_task and active_task == factory.id ]
        log.debug("Default layout: %s" % str(tasks))
        return [ TaskWindowLayout(*tasks,
                                  active_task = active_task,
                                  size = self.last_window_size) ]

    def _preferences_helper_default(self):
        return FrameworkPreferences(preferences = self.preferences)

    def _document_class_default(self):
        return BaseDocument

    #### Trait property getter/setters ########################################

    def _get_always_use_default_layout(self):
        #return self.preferences_helper.always_use_default_layout
        return True

    #### Trait event handlers

    def _application_initialized_fired(self):
        # Note: happens after _window_created_fired and _window_open_fired
        log.debug("STARTING!!!")
        init_filesystems(self.task_factories)
        loaded = False
        parser = argparse.ArgumentParser(description="Application parser")
        parser.add_argument("-t", "--task_id", "--task-id", "--edit_with","--edit-with", action="store", default="", help="Use the editing mode specified by this task id for all files listed on the command line")
        parser.add_argument("--show_editors", "--show-editors", action="store_true", default=False, help="List all task ids")
        parser.add_argument("--build_docs", "--build-docs", action="store_true", default=False, help="Build documentation from the menubar")
        options, extra_args = parser.parse_known_args(self.command_line_args)
        if options.show_editors:
            for factory in self.task_factories:
                print("%s %s" % (factory.id, factory.name))
        i = 0
        if ":" in options.task_id:
            options.task_id, task_arguments = options.task_id.split(":", 1)
        else:
            task_arguments = ""
        log.debug("task arguments: %s" % task_arguments)
        while i < len(extra_args):
            arg = extra_args[i]
            if arg.startswith("-"):
                if arg == "-d":
                    i += 1
                    error_logger.enable_loggers(extra_args[i])
                else:
                    log.debug("skipping flag %s" % arg)
                i += 1
                continue
            log.debug("processing %s" % arg)
            task_id = self.find_best_task_id(options.task_id)
            self.load_file(arg, None, task_id=task_id, task_arguments=task_arguments)
            i += 1

        # if any files were successfully loaded, some task will have an active
        # editor
        for w in self.windows:
            for t in w.tasks:
                if t.active_editor is not None:
                    loaded = True
                    break

        if not loaded:
            factory = self.get_task_factory(self.startup_task)
            url = factory.factory.about_application
            if url:
                log.debug("No filename on command line, starting %s in %s" % (url, factory.factory.editor_id))
                self.load_file(url)
        app = wx.GetApp()
        app.tasks_application = self

        if options.build_docs:
            idle = self.on_idle_build_docs
        else:
            idle = self.on_idle
        app.Bind(wx.EVT_IDLE, idle)

    @property
    def application_initialization_finished(self):
        app = wx.GetApp()
        return hasattr(app, 'tasks_application')

    def _application_exiting_fired(self):
        log.debug("CLEANING UP!!!")
        if self.downloader:
            self.downloader.stop_threads()

        import threading
        for thread in threading.enumerate():
            log.debug("thread running: %s" % thread.name)

        log.debug("Cleaning up globally allocated resources in documents")
        for doc in self.documents:
            log.debug("Cleaning up resources from %s" % doc)
            doc.global_resource_cleanup()

    def on_idle(self, evt):
        evt.Skip()
        if not self.active_window:
            return
        editor = self.active_window.active_task.active_editor
        if editor is None:
            return
        t = time.time()
        if t > self.last_clipboard_check_time + self.clipboard_check_interval:
            wx.CallAfter(self.update_dynamic_menu_items, editor)
            self.last_clipboard_check_time = time.time()
        editor.perform_idle()

        # Workaround: pyface doesn't seem to update the enabled status in any
        # timely manner, so force an update here. Toolbars are instances of
        # pyface.ui.wx.action.tool_bar_manager.ToolBarManager, and its window
        # attribute is a pyface.ui.wx.action.tool_bar_manager._AuiToolBar which
        # itself is a tiny subclass of wx.lib.agw.aui.AuiToolBar
        toolbars = editor.window._window_backend.get_toolbars()
        for t in [t.window for t in toolbars]:
            t.Refresh(False)

    def on_idle_build_docs(self, evt):
        evt.Skip()
        if not self.active_window:
            return
        editor = self.active_window.active_task.active_editor
        if editor is None:
            return
        print "Building documentation."
        wx.CallAfter(self.build_docs)

    def build_docs(self):
        import task as frameworktask
        task = frameworktask.FrameworkTask()
        sections = []
        docs = documentation.RSTOnePageDocs("%s %s User's Guide" % (task.about_title, task.about_version), "manual")
        for factory in self.task_factories:
            if "omnivore" not in factory.id or "framework" in factory.id:
                print "Skipping documentation for %s" % factory.id
                continue

            # For testing, uncomment the following block to only process
            # a single task

            # if not factory.id.startswith("omnivore.map_edit"):
            #     print "Skipping documentation for %s" % factory.id
            #     continue

            print "Building documentation for %s (%s)" % (factory.id, factory.name)
            task = self.create_task(factory.id)
            try:
                self.add_task_to_window(self.active_window, task)
                task.new()
            except AttributeError, e:
                print "Error creating documentation for %s: %s" % (factory.id, e)
                continue
            docs.add_task(task)
        docs.create_manual()
        print "Finished creating documentation! Exiting."
        sys.exit()

    def update_dynamic_menu_items(self, editor):
        editor.task.menu_update_event = editor
        self.check_clipboard_can_paste(editor)

    def check_clipboard_can_paste(self, editor):
        data_formats = [o.GetFormat() for o in editor.supported_clipboard_data_objects]
        log.debug("Checking clipboard formats %s" % str(data_formats))
        supported = False
        if not wx.TheClipboard.IsOpened():
            try:
                if wx.TheClipboard.Open():
                    for f in data_formats:
                        if wx.TheClipboard.IsSupported(f):
                            log.debug("  found clipboard format: %s" % str(f))
                            supported = True
            finally:
                if wx.TheClipboard.IsOpened():
                    wx.TheClipboard.Close()
            editor.can_paste = supported

    def _window_created_fired(self, event):
        """The toolkit window doesn't exist yet.
        """
        self.init_perspectives()

    def _window_opened_fired(self, event):
        """The toolkit window does exist here.
        """
        log.debug("WINDOW OPENED!!! %s, size=%s" % (event.window.control, str(self.last_window_size)))
        event.window.size = tuple(self.last_window_size)

        # Check to see that there's at least one task.  If a bad application
        # memento (~/.config/Omnivore/tasks/wx/application_memento), the window
        # may be blank in which case we need to add the default task.
        if not event.window.tasks:
            self.create_task_in_window(self.startup_task, event.window)
            log.debug("EMPTY WINDOW OPENED!!! Created task.")

        task = event.window.active_task
        if task.active_editor is None and task.start_new_editor_in_new_window:
            task.new(window_opening=True)

        if sys.platform.startswith("win"):
            # monkey patch to include mousewheel handler on the TaskWindow
            import types
            event.window._wx_on_mousewheel = types.MethodType(_task_window_wx_on_mousewheel, event.window)
            event.window.control.Bind(wx.EVT_MOUSEWHEEL, event.window._wx_on_mousewheel)

    #### API

    def guess_document(self, guess):
        service = self.get_service("omnivore.file_type.i_file_recognizer.IFileRecognizerDriver")
        log.debug("SERVICE!!! %s" % service)

        # Attempt to classify the guess using the file recognizer service
        document = service.recognize(guess)
        log.debug("created document %s (mime=%s)" % (document, document.metadata.mime))
        return document

    def load_file(self, uri, active_task=None, task_id="", in_current_window=False, **kwargs):
        log.debug("load_file: uri=%s task_id=%s" % (uri, task_id))
        from omnivore.utils.file_guess import FileGuess
        # The FileGuess loads the first part of the file and tries to identify it.
        try:
            guess = FileGuess(uri)
        except fs.errors.FSError, e:
            log.error("File load error: %s" % str(e))
            if active_task is not None:
                active_task.window.error(str(e), "File Load Error")
            return

        if len(guess.bytes) == 0:
            if active_task is not None:
                active_task.window.error("Zero length file!\nUnable to determine file type.", "File Load Error")
            return

        # Attempt to classify the guess using the file recognizer service
        document = self.guess_document(guess)
        log.debug("using %s for %s" % (document.__class__.__name__, guess.metadata.uri))
        if document.load_error:
            if self.active_window:
                self.active_window.warning(document.load_error, "Document Load Error")

        # Short circuit: if the file can be edited by the active task, use that!
        if active_task is not None and active_task.can_edit(document):
            log.debug("active task %s can edit %s" % (active_task, document))
            active_task.new(document, **kwargs)
            return

        possibilities = self.get_possible_task_factories(document, task_id)
        if not possibilities:
            log.debug("no editor for %s" % uri)
            return
        best = self.find_best_task_factory(document, possibilities)
        log.debug("best task match: %s" % best.id)

        if active_task is not None:
            # Ask the active task if it's OK to load a different editor
            if not active_task.allow_different_task(guess, best.factory):
                return
            dummy = self.document_class(metadata="application/octet-stream")
            if active_task.can_edit(document) and active_task.ask_attempt_loading_as_octet_stream(guess, best.factory):
                log.debug("Active task %s allows application/octet-stream" % active_task.id)
                active_task.new(document, **kwargs)
                return
            if in_current_window:
                task = self.create_task_in_window(best.id, active_task.window)
                task.new(document, **kwargs)
                return

        # Look for existing task in current windows
        task = self.find_active_task_of_type(best.id)
        if task:
            log.debug("Found task %s in current window" % best.id)
            task.new(document, **kwargs)
            return

        log.debug("Creating task %s in current window" % best.id)
        self.create_task_from_factory_id(document, best.id, **kwargs)

    def get_possible_task_factories(self, document, task_id=""):
        possibilities = []
        for factory in self.task_factories:
            log.debug("checking factory: %s=%s for %s" % (factory.id, factory.name, task_id))
            if task_id:
                if factory.id == task_id or factory.factory.editor_id == task_id:
                    possibilities.append(factory)
            elif hasattr(factory.factory, "can_edit"):
                if factory.factory.can_edit(document):
                    log.debug("  can edit: %s" % document)
                    possibilities.append(factory)
        log.debug("get_possible_task_factories: %s" % str([(p.name, p.id) for p in possibilities]))
        return possibilities

    def find_best_task_factory(self, document, factories):
        scores = []
        for factory in factories:
            log.debug("factory: %s=%s" % (factory.id, factory.name))
            if document.last_task_id == factory.id or document.last_task_id == factory.factory.editor_id:
                # short circuit if document is requesting a specific task
                return factory
            score = factory.factory.get_match_score(document)
            scores.append((score, factory))
        scores.sort()
        log.debug("find_best_task_factory: %s" % str([(s, p.name, p.id) for (s, p) in scores]))
        return scores[-1][1]

    def get_task_factory(self, task_id):
        for factory in self.task_factories:
            if factory.id == task_id or factory.factory.editor_id == task_id:
                return factory
        return None

    def find_best_task_id(self, task_id):
        if task_id:
            for factory in self.task_factories:
                if factory.id == task_id or ".%s." % task_id in factory.id or ".%s" % task_id in factory.id:
                    return factory.id
        return ""  # empty string will result in scanning the file for the best match

    def create_task_from_factory_id(self, guess, factory_id, **kwargs):
        window = self.active_window
        log.debug("  window=%s" % str(window))
        for task in window.tasks:
            if task.id == factory_id:
                break
        else:
            task = self.create_task(factory_id)
        self.add_task_to_window(window, task)
        task.new(guess, **kwargs)
        return task

    def create_task_in_window(self, task_id, window):
        log.debug("creating %s task" % task_id)
        task = self.create_task(task_id)
        self.add_task_to_window(window, task)
        return task

    def add_task_to_window(self, window, task):
        window.add_task(task)
        window.activate_task(task)
        self.restore_perspective(window, task)

    def find_active_task_of_type(self, task_id):
        # Until remove_task bug is fixed, don't create any new windows, just
        # add a new task to the current window unless the task already exists
        w = list(self.windows)
        if not w:
            # OS X might not have any windows open; a menubar is allowed to
            # exist without windows.
            return None
        try:
            i = w.index(self.active_window)
            w[0:0] = [self.active_window]
            w.pop(i)
        except ValueError:
            pass

        for window in w:
            for t in window.tasks:
                if t.id == task_id:
                    log.debug("found non-active task in current window; activating!")
                    window.activate_task(t)
                    return t
        if window:
            task = self.create_task_in_window(task_id, window)
            return task
#        # Check active window first, then other windows
#        w = list(self.windows)
#        try:
#            i = w.index(self.active_window)
#            w[0:0] = [self.active_window]
#            w.pop(i)
#        except ValueError:
#            pass
#
#        for window in w:
#            log.debug("window: %s" % window)
#            log.debug("  active task: %s" % window.active_task)
#            if window.active_task.id == task_id:
#                log.debug("  found active task")
#                return window.active_task
#        log.debug("  no active task matches %s" % task_id)
#        for window in w:
#            task = window.active_task
#            if task is None:
#                continue
#            # if no editors in the task, replace the task with the new task
#            log.debug("  window %s: %d" % (window, len(task.editor_area.editors)))
#            if len(task.editor_area.editors) == 0:
#                log.debug("  replacing unused task!")
#                # The bugs in remove_task seem to have been fixed so that the
#                # subsequent adding of a new task does seem to work now.  But
#                # I'm leaving in the workaround for now of simply closing the
#                # active window, forcing the new task to open in a new window.
#                if True:
#                    log.debug("removing task %s" % task)
#                    print window
#                    #window.remove_task(task)
#                    task = self.create_task_in_window(task_id, window)
#                    return task
#                else:
#                    window.close()
#                    return None

    def find_or_create_task_of_type(self, task_id):
        task = self.find_active_task_of_type(task_id)
        if not task:
            log.debug("task %s not found in active windows; creating new window" % task_id)
            window = self.create_window()
            task = self.create_task_in_window(task_id, window)
            window.open()
        return task

    # Override the default window closing event handlers only on Mac because
    # Mac allows the application to remain open while no windows are open
    if sys.platform == "darwin":
        def _on_window_closing(self, window, trait_name, event):
            # Event notification.
            self.window_closing = window_event = VetoableTaskWindowEvent(
                window=window)

            if window_event.veto:
                event.veto = True
            else:
                # Store the layout of the window.
                window_layout = window.get_window_layout()
                self._state.push_window_layout(window_layout)

        def _on_window_closed(self, window, trait_name, event):
            self.windows.remove(window)

            # Event notification.
            self.window_closed = TaskWindowEvent(window=window)

            # Was this the last window?
            if len(self.windows) == 0 and self._explicit_exit:
                self.stop()

    def _initialize_application_home(self):
        """Override the envisage.application method to force the use of standard
        config directory location instead of ~/.enthought 
        """
        self.setup_file_persistence(self.name)
        ETSConfig.application_home = self.app_home_dir

    #### Convenience methods

    def add_document(self, document):
        """Add document to the application list of open documents
        
        FIXME: check for duplicates?
        """
        existing = self.get_document(document.document_id)
        if existing:
            return existing

        document.document_id = self.next_document_id
        self.next_document_id += 1
        self.documents.append(document)
        return document

    def get_document(self, document_id):
        """Find an existing document given the document_id
        """
        for doc in self.documents:
            if doc.document_id == document_id:
                return doc
        return None

    def get_plugin_data(self, plugin_id):
        return self.plugin_data[plugin_id]

    def get_preferences(self, helper_object, debug=True):
        """Get preferences for a particular PreferenceHelper object.
        
        Handle mistakes in preference files by using the default value for any
        bad preference values.
        """

        # Give the helper application a class attribute to the application
        helper_object.application = self

        try:
            helper = helper_object(preferences=self.preferences)
        except TraitError:
            # Create an empty preference object and helper so we can try
            # preferences one-by-one to see which are bad
            empty = Preferences()
            helper = helper_object(preferences=empty)
            if debug:
                log.debug("Application preferences before determining error:")
                self.preferences.dump()
            for t in helper.trait_names():
                if helper._is_preference_trait(t):
                    pref_name = "%s.%s" % (helper.preferences_path, t)
                    text_value = self.preferences.get(pref_name)
                    if text_value is None:
                        # None means the preference isn't specified, which
                        # isn't an error.
                        continue
                    try:
                        empty.set(pref_name, self.preferences.get(pref_name))
                    except:
                        log.error("Invalid preference for %s: %s. Using default value %s" % (pref_name, self.preferences.get(pref_name), getattr(helper, t)))
                        self.preferences.remove(pref_name)
                        # Also remove from default scope
                        self.preferences.remove("default/%s" % pref_name)
            if debug:
                log.debug("Application preferences after removing bad preferences:")
                self.preferences.dump()
            helper = helper_object(preferences=self.preferences)
        return helper

    # class attributes

    perspectives_loaded = False

    def init_perspectives(self):
        if self.perspectives_loaded:
            return
        data = self.get_json_data("perspectives", default_on_error={})
        self.perspectives = data.get("perspectives", {})
        self.last_window_size = tuple(data.get("window_size", self.default_window_size))
        log.debug("init_perspectives: size=%s" % str(self.last_window_size))

    def remember_perspectives(self, window):
        layout = window.get_layout()
        if layout is not None:
            p = layout.perspective
            # make sure central pane exists, otherwise will restore without
            # central pane visible
            if "name=Central;" in p:
                log.debug("remember_perspective: %s, size=%s" % (layout.id, str(window.size)))
                self.perspectives[layout.id] = p
                self.last_window_size = window.size
                data = {"perspectives": dict(self.perspectives),
                        "window_size": list(self.last_window_size),
                        }
                self.save_json_data("perspectives", data)

    def restore_perspective(self, window, task):
        # get layout object that can be used to restore perspective since we
        # only serialize the perspective string and not the whole layout object
        layout = window.get_layout()
        if task.id in self.perspectives:
            layout.perspective = self.perspectives[task.id]
            window.set_layout(layout)
        task.restore_toolbars(window)

    def get_downloader(self):
        if self.downloader is None:
            self.downloader = BackgroundHttpDownloader()
        return self.downloader

    help_frame = None

    def show_help(self, section=None):
        from wx.html import HtmlHelpController
        if self.help_frame is None:
            filename = self.get_config_dir_filename(".", "htmlhelp.cfg")
            cfg = wx.FileConfig(localFilename=filename, style=wx.CONFIG_USE_LOCAL_FILE)
            # NOTE: using a FileConfig directly in the HtmlHelpController by
            # self.help_frame.UseConfig(cfg) crashes when closing the help
            # window
            wx.ConfigBase.Set(cfg)
            self.help_frame = HtmlHelpController()

        try:
            filename = get_htmlhelp("userguide.hhp")
        except MissingDocumentationError, e:
            self.active_window.warning(str(e), "Help Files Not Found")
            return

        self.help_frame.AddBook(filename)
        # plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        # for plugin in plugins:
        #     for book in plugin.getHelpBooks():
        #         self.help_frame.AddBook(book)
        if section:
            self.help_frame.Display(section)

            # Make sure it actually displayed something, otherwise show
            # the work-in-progress page
            data = self.help_frame.GetHelpWindow().GetData()
            filename = data.FindPageByName(section)
            if not filename:
                # FIXME: change this to something in omnivore
                self.help_frame.Display("work-in-progress.html")
        else:
            self.help_frame.DisplayContents()
