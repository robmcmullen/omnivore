# Enthought library imports.
from pyface.tasks.api import DockPane

import logging
log = logging.getLogger(__name__)


class FrameworkPane(DockPane):
    #### trait change handlers

    def _task_changed(self):
        log.debug("Task changed to %s in pane %s" % (self.task, self.id))
        if self.control:
            self.control.set_task(self.task)


class FrameworkFixedPane(DockPane):
    def update_dock_features(self, info):
        DockPane.update_dock_features(self, info)
        info.DockFixed()
