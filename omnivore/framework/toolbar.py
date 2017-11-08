from pyface.api import ImageResource
from pyface.action.api import Group
from pyface.tasks.action.api import SToolBar
from traits.api import on_trait_change, Any, Undefined

from .enthought_api import EditorAction

import logging
log = logging.getLogger(__name__)


class MouseHandlerBaseAction(EditorAction):
    """Save a bit of boilerplate with a base class for toolbar mouse mode buttons
    
    Note that the traits for name, tooltip, and image must be repeated
    in subclasses because the trait initialization appears to reference
    the handler in the class that is named, not superclasses.  E.g.:
    handler.menu_item_name in this base class doesn't appear to look at the
    handler class attribute of subclasses.
    """
    # Traits
    handler = Any

    style = 'radio'

    enabled_name = ''

    def _name_default(self):
        return self.handler.menu_item_name

    def _tooltip_default(self):
        return self.handler.menu_item_tooltip

    def _image_default(self):
        return ImageResource(self.handler.icon)

    def perform(self, event):
        log.debug("performing %s" % self.handler)
        self.active_editor.focused_viewer.update_mouse_mode(self.handler)

    @on_trait_change('active_editor.mouse_mode_factory')
    def _update_checked(self, ui_state):
        if self.active_editor:
            self.checked = self.active_editor.focused_viewer.mouse_mode_factory == self.handler

    @on_trait_change('task.menu_update_event')
    def on_dynamic_menu_update(self, ui_state):
        if ui_state is Undefined:
            return
        self.enabled = self.handler in ui_state.focused_viewer.valid_mouse_modes
        log.debug("on_dynamic_menu_update %s: focused_viewer=%s enabled=%s" % (self.handler, ui_state.focused_viewer, self.enabled))


def get_toolbar_group(toolbar_name, mouse_handlers):
    """Create the toolbar groups with buttons in the order specified in the
    valid_mouse_modes dict.
    """
    actions = [MouseHandlerBaseAction(handler=mode, enabled_name=mode.editor_trait_for_enabled) for mode in mouse_handlers]
    return SToolBar(Group(*actions),
                    show_tool_names=False,
                    # image_size=(22,22),
                    id=toolbar_name)
