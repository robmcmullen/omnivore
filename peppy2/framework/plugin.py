# Standard library imports.
import os

# Enthought library imports.
from envisage.api import ExtensionPoint, Plugin
from envisage.ui.tasks.api import TaskFactory
from traits.api import List, TraitError
from envisage.ui.tasks.tasks_plugin import TasksPlugin
from traits.etsconfig.api import ETSConfig
from apptools.preferences.api import Preferences, PreferencesHelper

class PeppyTasksPlugin(TasksPlugin):
    # Override the default task extensions that supply redundant Exit and
    # Preferences menu items and the default dock pane viewing group.
    def _my_task_extensions_default(self):
        return []

class FrameworkPlugin(Plugin):
    """ The sample framework plugin.
    """

    def get_helper(self, helper_object, debug=True):
        """Handle mistakes in preference files by using the default value for
        any bad preference values.
        
        """
        try:
            helper = helper_object(preferences=self.application.preferences)
        except TraitError:
            # Create an empty preference object and helper so we can try
            # preferences one-by-one to see which are bad
            empty = Preferences()
            helper = helper_object(preferences=empty)
            if debug:
                print "Application preferences before determining error:"
                self.application.preferences.dump()
            for t in helper.trait_names():
                if helper._is_preference_trait(t):
                    pref_name = "%s.%s" % (helper.preferences_path, t)
                    text_value = self.application.preferences.get(pref_name)
                    if text_value is None:
                        # None means the preference isn't specified, which
                        # isn't an error.
                        continue
                    try:
                        empty.set(pref_name, self.application.preferences.get(pref_name))
                    except:
                        print "Invalid preference for %s: %s. Using default value %s" % (pref_name, self.application.preferences.get(pref_name), getattr(helper, t))
                        self.application.preferences.remove(pref_name)
                        # Also remove from default scope
                        self.application.preferences.remove("default/%s" % pref_name)
            if debug:
                print "Application preferences after removing bad preferences:"
                self.application.preferences.dump()
            helper = helper_object(preferences=self.application.preferences)
        return helper
    
    def set_plugin_data(self, data):
        """Store some plugin data in the application so that objects outside
        the plugin can have access to it
        
        The data is stored in a dict keyed on the plugin's id, so make
        sure plugins don't have the same id.  (Perhaps this is enforced in
        Enthought, haven't checked yet.)
        """
        self.application.plugin_data[self.id] = data
    
    def get_plugin_data(self):
        """Return the plugin data previously stored by a call to
        :py:meth:`set_plugin_data`
        
        """
        return self.application.plugin_data[self.id]

    def fire_plugin_event(self, data=None):
        """Send a plugin event.
        
        Plugin events will get fired to all who listen for the
        'application:plugin_event' event, e.g.:
        
            @on_trait_change('application:plugin_event')
        
        The event handler will be passed a tuple of the plugin's ID and some
        data.  All handlers that listen for this event will get called, so
        check the first item in the tuple and for the desired plugin ID.
        """
        self.application.plugin_event = (self.id, data)


class PeppyMainPlugin(FrameworkPlugin):
    """ The sample framework plugin.
    """

    # Extension point IDs.
    PREFERENCES       = 'envisage.preferences'
    PREFERENCES_PANES = 'envisage.ui.tasks.preferences_panes'
    TASKS             = 'envisage.ui.tasks.tasks'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'peppy2.framework.plugin'

    # The plugin's name (suitable for displaying to the user).
    name = 'Peppy2'

    #### Contributions to extension points made by this plugin ################

    preferences = List(contributes_to=PREFERENCES)
    preferences_panes = List(contributes_to=PREFERENCES_PANES)
    tasks = List(contributes_to=TASKS)

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _preferences_default(self):
        filename = os.path.join(ETSConfig.application_home, 'preferences.ini')
        if not os.path.exists(filename):
            fh = open(filename, "wb")
            fh.close()
        return [ 'file://' + filename ]

    def _preferences_panes_default(self):
        from preferences import FrameworkPreferencesPane
        from peppy2.tasks.text_edit import TextEditPreferencesPane
        from peppy2.tasks.image_edit import ImageEditPreferencesPane
        return [ FrameworkPreferencesPane, TextEditPreferencesPane, ImageEditPreferencesPane ]

    def _tasks_default(self):
        from peppy2.tasks.skeleton import SkeletonTask
        from peppy2.tasks.text_edit import TextEditTask
        from peppy2.tasks.image_edit import ImageEditTask

        return [ 
            TaskFactory(id = 'peppy.framework.text_edit',
                        name = 'Text Editor',
                        factory = TextEditTask),

            TaskFactory(id = 'peppy.framework.image_edit',
                        name = 'Image Editor',
                        factory = ImageEditTask),

            TaskFactory(id = 'peppy.framework.skeleton',
                        name = 'Dummy Task',
                        factory = SkeletonTask),

#            TaskFactory(id = 'peppy.framework.task_2d',
#                        name = '2D Visualization',
#                        factory = Visualize2dTask),
            ]
