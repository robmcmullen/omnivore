import os
import sys

# Create the wx app here so we can capture the Mac specific stuff that
# traitsui.wx.toolkit's wx creation routines don't handle.  Also, monkey
# patching wx.GetApp() to add MacOpenFile (etc) doesn't seem to work, so we
# have to have these routines at app creation time.
import wx
class EnthoughtWxApp(wx.App):
    def MacOpenFile(self, filename):
        """OSX specific routine to handle files that are dropped on the icon
        
        """
        print "MacOpenFile: opening %s" % filename
        if hasattr(self, 'tasks_application'):
            print "MacOpenFile: application started!"
            if not hasattr(sys, "frozen") and len(sys.argv) > 0 and filename == sys.argv[0]:
                # MacOpenFile appears to be called once for each command line
                # argument, so this will get called for each comman line
                # argument.  While the argument to this function matches the
                # command line arguments, skip them.
                print "MacOpenFile: skipping command line argument %s" % filename
                del sys.argv[0]
            else:
                self.tasks_application.load_file(filename, None)

from traits.etsconfig.api import ETSConfig

_app = EnthoughtWxApp(redirect=False)

# Enthought library imports.
from envisage.ui.tasks.api import TasksApplication
from envisage.ui.tasks.task_window_event import TaskWindowEvent, VetoableTaskWindowEvent
from pyface.tasks.api import Task, TaskWindowLayout
from traits.api import Bool, Instance, List, Property, Str, Event, Dict

# Local imports.
from peppy2.framework.preferences import FrameworkPreferences, \
    FrameworkPreferencesPane


class FrameworkApplication(TasksApplication):
    """ The sample framework Tasks application.
    """

    #### 'IApplication' interface #############################################

    # The application's globally unique identifier.
    id = 'peppy2.framework.application'

    # The application's user-visible name.
    name = 'Peppy2'

    #### 'TasksApplication' interface #########################################

    # The default window-level layout for the application.
    default_layout = List(TaskWindowLayout)

    # Whether to restore the previous application-level layout when the
    # applicaton is started.
    always_use_default_layout = Property(Bool)

    #### 'FrameworkApplication' interface ####################################

    preferences_helper = Instance(FrameworkPreferences)
    
    startup_task = Str('peppy.framework.text_edit')
    
    successfully_loaded_event = Event
    
    plugin_event = Event
    
    plugin_data = {}

    ###########################################################################
    # Private interface.
    ###########################################################################

    #### Trait initializers ###################################################

    def _default_layout_default(self):
        active_task = self.preferences_helper.default_task
        if not active_task:
            active_task = self.startup_task
        tasks = [ factory.id for factory in self.task_factories if active_task and active_task == factory.id ]
        return [ TaskWindowLayout(*tasks,
                                  active_task = active_task,
                                  size = (800, 600)) ]

    def _preferences_helper_default(self):
        return FrameworkPreferences(preferences = self.preferences)

    #### Trait property getter/setters ########################################

    def _get_always_use_default_layout(self):
        return self.preferences_helper.always_use_default_layout


    #### Trait event handlers
    
    def _application_initialized_fired(self):
        print "STARTING!!!"
        for arg in sys.argv[1:]:
            if arg.startswith("-"):
                print "skipping flag %s" % arg
            print "processing %s" % arg
            self.load_file(arg, None)
    
    def _window_created_fired(self, event):
        """The toolkit window doesn't exist yet.
        """
    
    def _window_opened_fired(self, event):
        """The toolkit window does exist here.
        """
        print "WINDOW OPENED!!! %s" % event.window.control
        import wx
        # If using wx idle event handler, uncomment this next line
        #event.window.control.Bind(wx.EVT_IDLE, self._wx_on_idle)

    #### API

    def load_file(self, uri, active_task, **kwargs):
        service = self.get_service("peppy2.file_type.i_file_recognizer.IFileRecognizerDriver")
        print "SERVICE!!!", service
        
        from peppy2.utils.file_guess import FileGuess
        # The FileGuess loads the first part of the file and tries to identify it.
        guess = FileGuess(uri)
        
        # Attempt to classify the guess using the file recognizer service
        service.recognize(guess)
        
        possibilities = []
        for factory in self.task_factories:
            print "factory: %s" % factory.name
            if hasattr(factory.factory, "can_edit"):
                if factory.factory.can_edit(guess.metadata.mime):
                    print "  can edit: %s" % guess.metadata.mime
                    possibilities.append(factory)
        print possibilities
        if not possibilities:
            print "no editor for %s" % uri
            return
        
        best = possibilities[0]
        
        # Look for existing task in current windows
        task = self.find_active_task_of_type(best.factory)
        if task:
            task.new(guess, **kwargs)
            return
        
        # Not found in existing windows, so open new window with task
        tasks = [ factory.id for factory in possibilities ]
        print "no task window found: creating new layout for %s" % str(tasks)
#        window = self.create_window(TaskWindowLayout(size = (800, 600)))
        window = self.create_window(layout=TaskWindowLayout())
        print "  window=%s" % str(window)
        first = None
        for factory in possibilities:
            task = factory.factory()
            window.add_task(task)
            first = first or task
        window.activate_task(first)
        window.open()
        print "All windows: %s" % self.windows
        task.new(guess, **kwargs)
        metadata = guess.get_metadata()
        print guess.metadata
        print guess.metadata.mime
        print metadata
        print metadata.mime
        print dir(metadata)
    
    def get_task_class(self, task):
        if isinstance(task, Task):
            task = task.__class__
        return task
    
    def find_active_task_of_type(self, requested_task):
        task_cls = self.get_task_class(requested_task)
        for window in self.windows:
            print "window: %s" % window
            print "  active task: %s" % window.active_task
            if window.active_task.__class__ == task_cls:
                print "  found active task"
                return window.active_task
    
    def find_or_create_task_of_type(self, requested_task):
        task = self.find_active_task_of_type(requested_task)
        if not task:
            task_cls = self.get_task_class(requested_task)
            window = self.create_window(layout=TaskWindowLayout())
            task = task_cls()
            window.add_task(task)
            window.activate_task(task)
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

    #### wx event handlers ####################################################

    def _wx_on_idle(self, evt):
        """ Called during idle time. """
        control = evt.GetEventObject()
#        if not self.active_window:
#            print "No active window!!!"
        if control == self.active_window.control:
            #print "Processing idle on %s" % self.active_window
            self.active_window.active_task.process_idle()
        else:
            #print "Skipping idle on %s" % control
            pass

    def _initialize_application_home(self):
        """ Initialize the application home directory. """

        from peppy2.third_party.appdirs import user_config_dir
        dirname = user_config_dir(self.name)
        ETSConfig.application_home = dirname

        # Make sure it exists!
        if not os.path.exists(ETSConfig.application_home):
            os.makedirs(ETSConfig.application_home)

        return
    
    #### Convenience methods
    
    def get_plugin_data(self, plugin_id):
        return self.plugin_data[plugin_id]
    

def run(plugins=[], use_eggs=True, egg_path=[], image_path=[], startup_task=""):
    """Start the application
    
    :param plugins: list of user plugins
    :param use_eggs Boolean: search for setuptools plugins and plugins in local eggs?
    :param egg_path: list of user-specified paths to search for more plugins
    :param startup_task string: task factory identifier for task shown in initial window
    """
    import logging
    
    # Enthought library imports.
    from envisage.api import PluginManager
    from envisage.core_plugin import CorePlugin
    
    # Local imports.
    from peppy2.framework.plugin import PeppyTasksPlugin, PeppyMainPlugin
    from peppy2.file_type.plugin import FileTypePlugin
    from peppy2 import get_image_path
    
    # Include standard plugins
    core_plugins = [ CorePlugin(), PeppyTasksPlugin(), PeppyMainPlugin(), FileTypePlugin() ]
    if sys.platform == "darwin":
        from peppy2.framework.osx_plugin import OSXMenuBarPlugin
        core_plugins.append(OSXMenuBarPlugin())
    
    import peppy2.file_type.recognizers
    core_plugins.extend(peppy2.file_type.recognizers.plugins)
    
    import peppy2.plugins
    core_plugins.extend(peppy2.plugins.plugins)
    
    # Add the user's plugins
    core_plugins.extend(plugins)
    
    # The default is to use the specified plugins as well as any found
    # through setuptools and any local eggs (if an egg_path is specified).
    # Egg/setuptool plugin searching is turned off by the use_eggs parameter.
    default = PluginManager(
        plugins = core_plugins,
    )
    if use_eggs:
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
                'peppy2.tasks',
            ]
        )
        
        plugin_manager = CompositePluginManager(
            plugin_managers=[default, egg]
        )
    else:
        plugin_manager = default

    # Add peppy2 icons after all image paths to allow user icon themes to take
    # precidence
    from pyface.resource_manager import resource_manager
    import os
    image_paths = image_path[:]
    image_paths.append(get_image_path("icons"))
    resource_manager.extra_paths.extend(image_paths)

    kwargs = {}
    if startup_task:
        kwargs['startup_task'] = startup_task
    app = FrameworkApplication(plugin_manager=plugin_manager, **kwargs)
    
    app.run()
