# Standard library imports.
import os.path

# Enthought library imports.
from envisage.api import ExtensionPoint, Plugin, ServiceOffer
from envisage.ui.tasks.api import TaskFactory
from traits.api import List


class FrameworkPlugin(Plugin):
    """ The sample framework plugin.
    """

    # Extension point IDs.
    PREFERENCES       = 'envisage.preferences'
    PREFERENCES_PANES = 'envisage.ui.tasks.preferences_panes'
    TASKS             = 'envisage.ui.tasks.tasks'
    SERVICE_OFFERS    = 'envisage.service_offers'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'peppy.framework'

    # The plugin's name (suitable for displaying to the user).
    name = 'Framework'

    #### Contributions to extension points made by this plugin ################

    preferences = List(contributes_to=PREFERENCES)
    preferences_panes = List(contributes_to=PREFERENCES_PANES)
    tasks = List(contributes_to=TASKS)
    service_offers = List(contributes_to=SERVICE_OFFERS)

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _preferences_default(self):
        filename = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'preferences.ini')
        return [ 'file://' + filename ]

    def _preferences_panes_default(self):
        from framework_preferences import FrameworkPreferencesPane
        from text_edit import TextEditPreferencesPane
        from image_edit import ImageEditPreferencesPane
        return [ FrameworkPreferencesPane, TextEditPreferencesPane, ImageEditPreferencesPane ]

    def _tasks_default(self):
        from attractors import Visualize2dTask
        from skeleton import SkeletonTask
        from text_edit import TextEditTask
        from image_edit import ImageEditTask

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

    def _service_offers_default(self):
        """ Trait initializer. """

        print "in _service_offers_default"
        offer1 = ServiceOffer(
            protocol = 'file_type.i_filetype.IFileType',
            factory  = self._create_image_file_type_service
        )

        return [offer1]

    def _create_image_file_type_service(self):
        """ Factory method for the ImageFileType service. """

        # Only do imports when you need to! This makes sure that the import
        # only happens when somebody needs an 'IMOTD' service.
        from file_type.image import ImageFileType

        return ImageFileType()
