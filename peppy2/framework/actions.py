# Enthought library imports.
from pyface.api import ImageResource, FileDialog, YES, OK, CANCEL
from pyface.action.api import Action, ActionItem, Group
from pyface.tasks.action.api import EditorAction
from traits.api import Property, Instance, Bool, Str, Unicode, Any, List

from peppy2.framework.about import AboutDialog

class NewFileAction(Action):
    """ An action for creating a new empty file that can be edited by a particular task
    """
    tooltip = Property(Unicode, depends_on='name')

    task_id = Any
    
    def perform(self, event=None):
        task = event.task.window.application.find_or_create_task_of_type(self.task_id)
        task.new()

    def _get_tooltip(self):
        return u'Open a new %s' % self.name

class NewFileGroup(Group):
    """ A menu for creating a new file for each type of task
    """

    #### 'ActionManager' interface ############################################

    id = 'NewFileGroup'
    
    items = List

    #### 'TaskChangeMenuManager' interface ####################################

    # The ActionManager to which the group belongs.
    manager = Any

    # The window that contains the group.
    application = Instance('envisage.ui.tasks.api.TasksApplication')
        
    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self):
        items = []
        for factory in self.application.task_factories:
            if hasattr(factory.factory, 'new_file_text'):
                task_cls = factory.factory
                if task_cls.new_file_text:
                    action = NewFileAction(name=task_cls.new_file_text, task_id=factory.id)
                    items.append((task_cls.new_file_text, ActionItem(action=action)))
        items.sort()
        items = [i[1] for i in items]
        return items

    def _rebuild(self):
        # Clear out the old group, then build the new one.
        self.destroy()
        self.items = self._get_items()

        # Inform our manager that it needs to be rebuilt.
        self.manager.changed = True
        
    #### Trait initializers ###################################################

    def _items_default(self):
        self.application.on_trait_change(self._rebuild, 'task_factories[]')
        return self._get_items()

    def _manager_default(self):
        manager = self
        while isinstance(manager, Group):
            manager = manager.parent
        return manager
    
    def _application_default(self):
        return self.manager.controller.task.window.application


class OpenAction(Action):
    name = 'Open...'
    accelerator = 'Ctrl+O'
    tooltip = 'Open a file'
    image = ImageResource('file_open')

    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control)
        if dialog.open() == OK:
            event.task.window.application.load_file(dialog.path, event.task)

class SaveAction(EditorAction):
    name = 'Save'
    accelerator = 'Ctrl+S'
    tooltip = 'Save the current file'
    image = ImageResource('file_save')
    enabled_name = 'dirty' # enabled based on state of task.active_editor.dirty

    def perform(self, event):
        self.active_editor.save(None)

class SaveAsAction(EditorAction):
    name = 'Save As...'
    accelerator = 'Ctrl+Shift+S'
    tooltip = 'Save the current file with a new name'
    image = ImageResource('file_save_as')

    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control, action='save as')
        if dialog.open() == OK:
            self.active_editor.save(dialog.path)

class ExitAction(Action):
    name = 'Quit'
    accelerator = 'Ctrl+Q'
    tooltip = 'Quit the program'
    menu_role = "Quit"

    def perform(self, event):
        event.task.window.application.exit()

class UndoAction(EditorAction):
    name = 'Undo'
    accelerator = 'Ctrl+Z'
    tooltip = 'Undo last action'
    image = ImageResource('undo')
    enabled_name = 'can_undo'

    def perform(self, event):
        self.active_editor.undo()

class RedoAction(EditorAction):
    name = 'Redo'
    accelerator = 'Ctrl+Shift+Z'
    tooltip = 'Redo the last undone action'
    image = ImageResource('redo')
    enabled_name = 'can_redo'

    def perform(self, event):
        self.active_editor.redo()

class PreferencesAction(Action):
    name = 'Preferences...'
    accelerator = 'Ctrl+,'
    tooltip = 'Program settings and configuration options'
    menu_role = "Preferences"

    def perform(self, event):
        # FIXME: using the built-in dialog box handler segfaults on OS X:
        #0   libwx_osx_cocoau-2.9.4.0.0.dylib	0x0000000101539f07 wxWidgetCocoaImpl::mouseEvent(NSEvent*, NSView*, void*) + 183
        #1   com.apple.AppKit              	0x00007fff89efac98 -[NSWindow sendEvent:] + 6306
        #2   libwx_osx_cocoau-2.9.4.0.0.dylib	0x0000000101526a5c -[wxNSPanel sendEvent:] + 140
        #3   com.apple.AppKit              	0x00007fff89e943a5 -[NSApplication sendEvent:] + 5593
        #4   com.apple.AppKit              	0x00007fff8a0e2797 -[NSApplication _realDoModalLoop:peek:] + 708
        #5   com.apple.AppKit              	0x00007fff8a0e2369 -[NSApplication runModalForWindow:] + 120
        #6   libwx_osx_cocoau-2.9.4.0.0.dylib	0x000000010151804e wxModalEventLoop::DoRun() + 174
        #7   libwx_osx_cocoau-2.9.4.0.0.dylib	0x00000001013eb607 wxCFEventLoop::Run() + 55
        #8   libwx_osx_cocoau-2.9.4.0.0.dylib	0x00000001014538d9 wxDialog::ShowModal() + 73
        #9   _windows_.so                  	0x000000010422b7b6 _wrap_Dialog_ShowModal + 102
        if False:
            from envisage.ui.tasks.preferences_dialog import \
                PreferencesDialog

            window = event.task.window
            dialog = window.application.get_service(PreferencesDialog)
            ui = dialog.edit_traits(parent=window.control, kind='livemodal')
            
            if ui.result:
                window.application.preferences.save()
        
        from peppy2.framework.preferences import FrameworkPreferenceDialog
        dialog = FrameworkPreferenceDialog(application=event.task.window.application, style="modal")
        status = dialog.open()
        if status == OK:
            event.task.window.application.preferences_changed_event = True

class AboutAction(Action):
    name = 'About...'
    tooltip = 'About this program'
    menu_role = "About"

    def perform(self, event):
        # Don't rely on the event window as this might be called by the OSX
        # minimal menu which, once installed by the OSX plugin, never changes
        # with the task.
        top = event.task.window.application.active_window
        AboutDialog(top.control, top.active_task)

class NewViewAction(EditorAction):
    name = 'New View of Current Tab'
    tooltip = 'New view of the project in the current tab'

    def perform(self, event):
        event.task.new_window(view=event.task.active_editor)

class NewWindowAction(Action):
    name = 'New Window'
    tooltip = 'Open a new window'

    def perform(self, event):
        event.task.new_window()
