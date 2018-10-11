# Standard library imports.
import os

# Enthought library imports.
from traits.api import List, TraitError

from omnivore_framework.framework.plugin import FrameworkPlugin


class OmnivoreEditorPlugin(FrameworkPlugin):
    """ Plugin containing all the Omnivore binary editors
    """

    # Extension point IDs.
    PREFERENCES_PANES = 'envisage.ui.tasks.preferences_panes'
    TASKS             = 'envisage.ui.tasks.tasks'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'omnivore.binary.plugin'

    # The plugin's name (suitable for displaying to the user).
    name = 'Omnivore Binary Editor'

    #### Contributions to extension points made by this plugin ################

    preferences_panes = List(contributes_to=PREFERENCES_PANES)
    tasks = List(contributes_to=TASKS)

    def _preferences_panes_default(self):
        from .byte_edit import ByteEditPreferencesPane
        return [ByteEditPreferencesPane]

    def _tasks_default(self):
        from .byte_edit import ByteEditTask

        return self.task_factories_from_tasks([
            ByteEditTask,
            ])
