import os
import sys
import time
import argparse
import json
import jsonpickle
from datetime import datetime

import fs

from filesystem import init_filesystems
from document import Document

import logging
log = logging.getLogger(__name__)

# Create the wx app here so we can capture the Mac specific stuff that
# traitsui.wx.toolkit's wx creation routines don't handle.  Also, monkey
# patching wx.GetApp() to add MacOpenFile (etc) doesn't seem to work, so we
# have to have these routines at app creation time.
import wx
class EnthoughtWxApp(wx.App):
    def MacOpenFiles(self, filenames):
        """OSX specific routine to handle files that are dropped on the icon
        
        """
        if hasattr(self, 'tasks_application'):
            # The tasks_application attribute is added to this wx.App instance
            # when the application has been initialized.  This is used as a
            # flag to indicate that the subsequent calls to MacOpenFile are
            # real drops of files onto the dock icon.  Prior to that, this
            # method gets called for all the command line arguments which would
            # give us two copies of each file specified on the command line.
            for filename in filenames:
                log.debug("MacOpenFile: loading %s" % filename)
                self.tasks_application.load_file(filename, None)
        else:
            log.debug("MacOpenFile: skipping %s because it's a command line argument" % filename)
    
    throw_out_next_wheel_rotation = False
    
    def FilterEvent(self, evt):
        if hasattr(evt, "GetWheelRotation"):
            print "FILTEREVENT!!!", evt.GetWheelRotation(), evt
            wheel = evt.GetWheelRotation()
            if wheel != 0:
                if self.throw_out_next_wheel_rotation:
                    self.throw_out_next_wheel_rotation = False
                    return 0
                self.throw_out_next_wheel_rotation = True
        if hasattr(evt, "GetKeyCode"):
            print "FILTEREVENT!!! char=%s, key=%s, modifiers=%s" % (evt.GetUniChar(), evt.GetKeyCode(), bin(evt.GetModifiers()))
        return -1

from traits.etsconfig.api import ETSConfig

_app = EnthoughtWxApp(redirect=False)
if False:  # enable this to use FilterEvent
    _app.SetCallFilterEvent(True)

# Enthought library imports.
from envisage.ui.tasks.api import TasksApplication
from envisage.ui.tasks.task_window_event import TaskWindowEvent, VetoableTaskWindowEvent
from pyface.api import ImageResource
from pyface.tasks.api import Task, TaskWindowLayout
from traits.api import provides, Bool, Instance, List, Property, Str, Unicode, Event, Dict, Int, Float, Tuple

# Local imports.
from omnivore.framework.preferences import FrameworkPreferences, \
    FrameworkPreferencesPane


def _task_window_wx_on_mousewheel(self, event):
    if self.active_task and hasattr(self.active_task, '_wx_on_mousewheel_from_window'):
        log.debug("calling mousewheel in task %s" % self.active_task)
        self.active_task._wx_on_mousewheel_from_window(event)

class FrameworkApplication(TasksApplication):
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

    # Whether to restore the previous application-level layout when the
    # applicaton is started.
    always_use_default_layout = Property(Bool)

    #### 'FrameworkApplication' interface ####################################

    preferences_helper = Instance(FrameworkPreferences)
    
    startup_task = Str('omnivore.framework.text_edit_task')
    
    successfully_loaded_event = Event
    
    plugin_event = Event
    
    preferences_changed_event = Event
    
    plugin_data = {}
    
    command_line_args = List
    
    log_dir = Str
    
    log_file_ext = Str
    
    cache_dir = Str
    
    next_document_id = Int(0)
    
    documents = List
    
    last_clipboard_check_time = Float(-1)
    
    clipboard_check_interval = Float(.75)
    
    perspectives = Dict
    
    default_window_size = (800, 600)
    
    last_window_size = Tuple(default_window_size)

    ###########################################################################
    # Private interface.
    ###########################################################################

    #### Trait initializers ###################################################
    
    def _about_title_default(self):
        return self.name
    
    def _about_version_default(self):
        from omnivore import __version__
        return __version__

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

    #### Trait property getter/setters ########################################

    def _get_always_use_default_layout(self):
        #return self.preferences_helper.always_use_default_layout
        return True


    #### Trait event handlers
    
    def _application_initialized_fired(self):
        log.debug("STARTING!!!")
        init_filesystems()
        loaded = False
        parser = argparse.ArgumentParser(description="Application parser")
        parser.add_argument("-t", "--task_id", "--edit_with", action="store", default="", help="Use the editing mode specified by this task id for all files listed on the command line")
        parser.add_argument("--show_editors", action="store_true", default=False, help="List all task ids")
        options, extra_args = parser.parse_known_args(self.command_line_args)
        if options.show_editors:
            for factory in self.task_factories:
                print("%s %s" % (factory.id, factory.name))
        for arg in extra_args:
            if arg.startswith("-"):
                log.debug("skipping flag %s" % arg)
                continue
            log.debug("processing %s" % arg)
            task_id = self.find_best_task_id(options.task_id)
            self.load_file(arg, None, task_id=task_id)
            loaded = True
        if not loaded:
            factory = self.get_task_factory(self.startup_task)
            url = factory.factory.about_application
            if url:
                self.load_file(url)
        app = wx.GetApp()
        app.tasks_application = self
        
        app.Bind(wx.EVT_IDLE, self.on_idle)
    
    def on_idle(self, evt):
        evt.Skip()
        if not self.active_window:
            return
        editor = self.active_window.active_task.active_editor
        if editor is None:
            return
        t = time.time()
        if t > self.last_clipboard_check_time + self.clipboard_check_interval:
            wx.CallAfter(self.check_clipboard_can_paste, editor)
            self.last_clipboard_check_time = time.time()
        editor.perform_idle()
    
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
            task.new()
        
        if sys.platform.startswith("win"):
            # monkey patch to include mousewheel handler on the TaskWindow
            import types
            event.window._wx_on_mousewheel = types.MethodType(_task_window_wx_on_mousewheel, event.window)
            event.window.control.Bind(wx.EVT_MOUSEWHEEL, event.window._wx_on_mousewheel)

    #### API

    def load_file(self, uri, active_task=None, task_id="", in_current_window=False, **kwargs):
        service = self.get_service("omnivore.file_type.i_file_recognizer.IFileRecognizerDriver")
        log.debug("SERVICE!!! %s" % service)
        
        from omnivore.utils.file_guess import FileGuess
        # The FileGuess loads the first part of the file and tries to identify it.
        try:
            guess = FileGuess(uri)
        except fs.errors.FSError, e:
            log.error("File load error: %s" % str(e))
            if active_task is not None:
                active_task.window.error(str(e), "File Load Error")
            return
        
        # Attempt to classify the guess using the file recognizer service
        document = service.recognize(guess)
        log.debug("created document %s (mime=%s) %d segments from parser %s" % (document, document.metadata.mime, len(document.segments), document.segment_parser.__class__.__name__))
        
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
        
        if active_task is not None:
            # Ask the active task if it's OK to load a different editor
            if not active_task.allow_different_task(guess, best.factory):
                return
            dummy = Document(metadata="application/octet-stream")
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
        self.create_task_from_factory_id(document, best.id)
    
    def get_possible_task_factories(self, document, task_id=""):
        possibilities = []
        for factory in self.task_factories:
            log.debug("factory: %s=%s" % (factory.id, factory.name))
            if task_id:
                if factory.id == task_id:
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
            if document.last_task_id == factory.id:
                # short circuit if document is requesting a specific task
                return factory
            score = factory.factory.get_match_score(document)
            scores.append((score, factory))
        scores.sort()
        log.debug("find_best_task_factory: %s" % str([(s, p.name, p.id) for (s, p) in scores]))
        return scores[-1][1]
    
    def get_task_factory(self, task_id):
        for factory in self.task_factories:
            if factory.id == task_id:
                return factory
        return None
    
    def find_best_task_id(self, task_id):
        if task_id:
            for factory in self.task_factories:
                if factory.id == task_id or ".%s." % task_id in factory.id or ".%s" % task_id in factory.id:
                    return factory.id
        return ""  # empty string will result in scanning the file for the best match
    
    def create_task_from_factory_id(self, guess, factory_id):
        window = self.create_window()
        log.debug("  window=%s" % str(window))
        task = self.create_task(factory_id)
        self.add_task_to_window(window, task)
        window.open()
        task.new(guess)
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

        from omnivore.third_party.appdirs import user_config_dir, user_log_dir, user_cache_dir
        dirname = user_config_dir(self.name)
        ETSConfig.application_home = dirname

        # Make sure it exists!
        if not os.path.exists(ETSConfig.application_home):
            os.makedirs(ETSConfig.application_home)

        dirname = user_log_dir(self.name)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        self.log_dir = dirname
        
        self.log_file_ext = "-%s" % datetime.now().strftime("%Y%m%d-%H%M%S")

        dirname = user_cache_dir(self.name)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        self.cache_dir = dirname
        
        # Prevent py2exe from creating a dialog box on exit saying that there
        # are error messages.  It thinks that anything written to stderr is an
        # error, and the python logging module redirects everything to stderr.
        # Instead, redirect stderr to a log file in the user log directory
        frozen = getattr(sys, 'frozen', False)
        if frozen in ('dll', 'windows_exe', 'console_exe'):
            # redirect py2exe stderr/stdout to log file
            log = self.get_log_file_name("py2exe")
            oldlog = sys.stdout
            sys.stdout = open(log, 'w')
            if hasattr(oldlog, "saved_text"):
                sys.stdout.write("".join(oldlog.saved_text))
            sys.stderr = sys.stdout
            
            # The logging module won't redirect to the new stderr without help
            handler = logging.StreamHandler(sys.stderr)
            logger = logging.getLogger('')
            logger.addHandler(handler)
        else:
            log = self.get_log_file_name("log")
            handler = logging.FileHandler(log)
            formatter = logging.Formatter("%(levelname)s:%(name)s:%(msg)s")
            handler.setFormatter(formatter)
            logger = logging.getLogger('')
            logger.addHandler(handler)
    
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
    
    def get_log_file_name(self, log_file_name_base, ext=""):
        filename = log_file_name_base + self.log_file_ext
        if ext:
            if not ext.startswith("."):
                filename += "."
            filename += ext
        else:
            filename += ".log"
        filename = os.path.join(self.log_dir, filename)
        return filename
    
    def save_log(self, text, log_file_name_base, ext=""):
        filename = self.get_log_file_name(log_file_name_base, ext)
        
        try:
            with open(filename, "wb") as fh:
                fh.write(text)
        except IOError:
            log.error("Failed writing %s to %s" % (log_file_name_base, filename))
    
    def get_config_dir_filename(self, subdir, json_name):
        config_dir = ETSConfig.application_home
        dirname = os.path.join(config_dir, subdir)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        return os.path.join(dirname, json_name)
    
    def get_json_data(self, json_name, default_on_error=None):
        try:
            file_path = self.get_config_dir_filename("json", json_name)
            with open(file_path, "r") as fh:
                raw = fh.read()
            json_data = jsonpickle.decode(raw)
            try:
                # new format is a list with a format identifier as the first entry
                if json_data[0] == "format=v2":
                    decoded = json_data[1]
            except KeyError:
                # deprecated format was a dictionary, and was creating an extra
                # layer of indirection by encoding the jsonpickle as another string
                json_data = json.loads(raw)
                encoded = json_data[json_name]
                decoded = jsonpickle.decode(encoded)
            return decoded
        except IOError:
            # file not found
            return default_on_error
        except ValueError:
            # bad JSON format
            log.error("Bad JSON format in preferences file: %s" % json_name)
            return default_on_error
    
    def save_json_data(self, json_name, data):
        file_path = self.get_config_dir_filename("json", json_name)
        json_data = ["format=v2", data]
        encoded = jsonpickle.encode(json_data)
        with open(file_path, "w") as fh:
            fh.write(encoded)
    
    def get_bson_data(self, bson_name):
        import bson
        
        file_path = self.get_config_dir_filename("bson", bson_name)
        with open(file_path, "r") as fh:
            raw = fh.read()
        if len(raw) > 0:
            bson_data = bson.loads(raw)
            data = bson_data[bson_name]
        else:
            raise IOError("Blank BSON data")
        return data
    
    def save_bson_data(self, bson_name, data):
        import bson
        
        file_path = self.get_config_dir_filename("bson", bson_name)
        bson_data = {bson_name: data}
        raw = bson.dumps(bson_data)
        with open(file_path, "w") as fh:
            fh.write(raw)
    
    # class attributes
    
    perspectives_loaded = False
    
    def init_perspectives(self):
        if self.perspectives_loaded:
            return
        try:
            data = self.get_json_data("perspectives")
        except IOError:
            # file not found
            data = {}
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

def setup_frozen_logging():
    # set up early py2exe logging redirection, saving any messages until the log
    # file directory can be determined after the application is initialized.
    frozen = getattr(sys, 'frozen', False)
    if frozen in ('dll', 'windows_exe', 'console_exe'):
        class Blackhole(object):
            softspace = 0
            saved_text = []
            def write(self, text):
                self.saved_text.append(text)
            def flush(self):
                pass
        sys.stdout = Blackhole()
        sys.stderr = sys.stdout

def run(plugins=[], use_eggs=True, egg_path=[], image_path=[], startup_task="", application_name="", debug_log=False):
    """Start the application
    
    :param plugins: list of user plugins
    :param use_eggs Boolean: search for setuptools plugins and plugins in local eggs?
    :param egg_path: list of user-specified paths to search for more plugins
    :param startup_task string: task factory identifier for task shown in initial window
    :param application_name string: change application name instead of default Omnivore
    """
    # Enthought library imports.
    from envisage.api import PluginManager
    from envisage.core_plugin import CorePlugin
    
    # Local imports.
    from omnivore.framework.plugin import OmnivoreTasksPlugin, OmnivoreMainPlugin
    from omnivore.file_type.plugin import FileTypePlugin
    from omnivore import get_image_path
    from omnivore.utils.jobs import get_global_job_manager
    
    # Include standard plugins
    core_plugins = [ CorePlugin(), OmnivoreTasksPlugin(), OmnivoreMainPlugin(), FileTypePlugin() ]
    if sys.platform == "darwin":
        from omnivore.framework.osx_plugin import OSXMenuBarPlugin
        core_plugins.append(OSXMenuBarPlugin())
    
    import omnivore.file_type.recognizers
    core_plugins.extend(omnivore.file_type.recognizers.plugins)
    
    import omnivore.plugins
    core_plugins.extend(omnivore.plugins.plugins)
    
    # Add the user's plugins
    core_plugins.extend(plugins)
    
    # Check basic command line args
    default_parser = argparse.ArgumentParser(description="Default Parser")
    default_parser.add_argument("--no-eggs", dest="use_eggs", action="store_false", default=True, help="Do not load plugins from python eggs")
    options, extra_args = default_parser.parse_known_args()

    # The default is to use the specified plugins as well as any found
    # through setuptools and any local eggs (if an egg_path is specified).
    # Egg/setuptool plugin searching is turned off by the use_eggs parameter.
    default = PluginManager(
        plugins = core_plugins,
    )
    if use_eggs and options.use_eggs:
        from pkg_resources import Environment, working_set
        from envisage.api import EggPluginManager
        from envisage.composite_plugin_manager import CompositePluginManager
        
        # Find all additional eggs and add them to the working set
        environment = Environment(egg_path)
        distributions, errors = working_set.find_plugins(environment)
        if len(errors) > 0:
            raise SystemError('cannot add eggs %s' % errors)
        logger = logging.getLogger()
        logger.debug('added eggs %s' % distributions)
        map(working_set.add, distributions)

        # The plugin manager specifies which eggs to include and ignores all others
        egg = EggPluginManager(
            include = [
                'omnivore.tasks',
            ]
        )
        
        plugin_manager = CompositePluginManager(
            plugin_managers=[default, egg]
        )
    else:
        plugin_manager = default

    # Add omnivore icons after all image paths to allow user icon themes to take
    # precidence
    from pyface.resource_manager import resource_manager
    import os
    image_paths = image_path[:]
    image_paths.append(get_image_path("icons"))
    resource_manager.extra_paths.extend(image_paths)

    kwargs = {}
    if startup_task:
        kwargs['startup_task'] = startup_task
    if application_name:
        kwargs['name'] = application_name
    app = FrameworkApplication(plugin_manager=plugin_manager, command_line_args=extra_args, **kwargs)
    
    # Create a debugging log
    if debug_log:
        filename = app.get_log_file_name("debug")
        handler = logging.FileHandler(filename)
        logger = logging.getLogger('')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    
    # Turn off omnivore log debug messages by default
    log = logging.getLogger("omnivore")
    log.setLevel(logging.INFO)

    app.run()
    
    job_manager = get_global_job_manager()
    if job_manager is not None:
        job_manager.shutdown()
