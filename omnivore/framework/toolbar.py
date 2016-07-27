from pyface.api import ImageResource
from pyface.action.api import Group
from pyface.tasks.action.api import SToolBar, EditorAction
from traits.api import on_trait_change, Any

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
        self.active_editor.mouse_mode_factory = self.handler
        self.active_editor.update_mouse_mode()

    @on_trait_change('active_editor.mouse_mode_factory')
    def _update_checked(self):
        if self.active_editor:
            self.checked = self.active_editor.mouse_mode_factory == self.handler

def get_toolbar_group(toolbar_name, mouse_handlers):
    """Create the toolbar groups with buttons in the order specified in the
    valid_mouse_modes dict.
    """
    actions = [MouseHandlerBaseAction(handler=mode, enabled_name=mode.editor_trait_for_enabled) for mode in mouse_handlers]
    return SToolBar(Group(*actions),
                    show_tool_names=False,
                    # image_size=(22,22),
                    id=toolbar_name)
