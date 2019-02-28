"""Baseclass for actions with common code applicable to viewers
"""
from omnivore_framework.action import OmnivoreAction, OmnivoreRadioAction, OmnivoreRadioListAction

import logging
log = logging.getLogger(__name__)


class ViewerActionMixin:
    @property
    def viewer(self):
        return self.editor.focused_viewer

    @property
    def linked_base(self):
        return self.editor.focused_viewer.linked_base


class ViewerAction(ViewerActionMixin, OmnivoreAction):
    pass


class ViewerRadioAction(ViewerActionMixin, OmnivoreRadioAction):
    pass


class ViewerListAction(ViewerActionMixin, OmnivoreRadioListAction):
    pass
