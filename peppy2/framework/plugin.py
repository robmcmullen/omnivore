# Standard library imports.
import os

# Enthought library imports.
from envisage.api import ExtensionPoint, Plugin
from envisage.ui.tasks.api import TaskFactory
from traits.api import List
from envisage.ui.tasks.tasks_plugin import TasksPlugin

class PeppyTasksPlugin(TasksPlugin):
    # Override the default task extensions that supply redundant Exit and
    # Preferences menu items and the default dock pane viewing group.
    def _my_task_extensions_default(self):
        return []

class FrameworkPlugin(Plugin):
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
        from peppy2.third_party.appdirs import user_config_dir
        dirname = user_config_dir(self.name)
        if not os.path.exists(dirname):
            os.mkdir(dirname)
        filename = os.path.join(dirname, 'preferences.ini')
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
