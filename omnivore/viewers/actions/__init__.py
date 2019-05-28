"""Baseclass for actions with common code applicable to viewers
"""
from sawx.action import SawxAction, SawxSubAction, SawxListAction, SawxRadioAction, SawxRadioListAction

import logging
log = logging.getLogger(__name__)


class ViewerActionMixin:
    @property
    def viewer(self):
        try:
            return self.popup_data["popup_viewer"]
        except (KeyError, TypeError) as e:
            return self.editor.focused_viewer

    @property
    def linked_base(self):
        return self.editor.focused_viewer.linked_base


class ViewerAction(ViewerActionMixin, SawxAction):
    pass


class ViewerSubAction(ViewerActionMixin, SawxSubAction):
    pass


class ViewerRadioAction(ViewerActionMixin, SawxRadioAction):
    pass


class ViewerListAction(ViewerActionMixin, SawxListAction):
    pass


class ViewerRadioListAction(ViewerActionMixin, SawxRadioListAction):
    pass
