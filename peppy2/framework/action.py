from pyface.action.api import Action

class FrameworkAction(Action):
    """Action that provides callbacks for the FrameworkTask to set the enabled
    state.
    
    """
    
    def set_enabled(self, task, active_editor):
        self.enabled = True
    
    def set_enabled_no_editor(self, task):
        self.enabled = True
