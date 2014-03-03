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

_app = EnthoughtWxApp(redirect=False)

# Enthought library imports.
from envisage.ui.tasks.api import TasksApplication
from envisage.ui.tasks.task_window_event import TaskWindowEvent, VetoableTaskWindowEvent
from pyface.tasks.api import TaskWindowLayout
from traits.api import Bool, Instance, List, Property

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

    ###########################################################################
    # Private interface.
    ###########################################################################

    #### Trait initializers ###################################################

    def _default_layout_default(self):
        active_task = self.preferences_helper.default_task
        tasks = [ factory.id for factory in self.task_factories ]
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

    def load_file(self, uri, active_task):
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
        for window in self.windows:
            print "window: %s" % window
            print "  active task: %s" % window.active_task
            if window.active_task.__class__ == best.factory:
                print "  found active task"
                window.active_task.new(guess)
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
        task.new(guess)
        metadata = guess.get_metadata()
        print guess.metadata
        print guess.metadata.mime
        print metadata
        print metadata.mime
        print dir(metadata)

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


def run(plugins=[], use_eggs=True, egg_path=[], image_path=[]):
    """Start the application
    
    :param plugins: list of user plugins
    :param use_eggs Boolean: search for setuptools plugins and plugins in local eggs?
    :param egg_path: list of user-specified paths to search for more plugins
    """
    import logging
    
    # Enthought library imports.
    from envisage.api import PluginManager
    from envisage.core_plugin import CorePlugin
    
    # Local imports.
    from peppy2.framework.plugin import PeppyTasksPlugin, FrameworkPlugin
    from peppy2.file_type.plugin import FileTypePlugin
    from peppy2 import get_image_path
    
    # Include standard plugins
    core_plugins = [ CorePlugin(), PeppyTasksPlugin(), FrameworkPlugin(), FileTypePlugin() ]
    if sys.platform == "darwin":
        from peppy2.framework.osx_plugin import OSXMenuBarPlugin
        core_plugins.append(OSXMenuBarPlugin())
    
    import peppy2.file_type.recognizers
    core_plugins.extend(peppy2.file_type.recognizers.plugins)
    
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

    app = FrameworkApplication(plugin_manager=plugin_manager)
    
    app.run()
