import wx.lib.inspection

# Enthought library imports.
from pyface.api import ImageResource, FileDialog, YES, OK, CANCEL
from pyface.action.api import Action, ActionItem, Group
from pyface.tasks.action.api import EditorAction
from traits.api import Property, Instance, Bool, Str, Unicode, Any, List

from peppy2.framework.about import AboutDialog

import logging
log = logging.getLogger(__name__)


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

class PageSetupAction(Action):
    name = 'Page Setup...'
    tooltip = 'Choose options for printing'

    def perform(self, event):
        event.task.page_setup()

class PrintPreviewAction(EditorAction):
    name = 'Print Preview'
    tooltip = 'Preview the pages to be printed'
    enabled_name = 'printable'

    def perform(self, event):
        self.active_editor.print_preview()

class PrintAction(EditorAction):
    name = 'Print...'
    tooltip = 'Print the current view to a printer'
    enabled_name = 'printable'

    def perform(self, event):
        self.active_editor.print_page()

class SaveAsPDFAction(EditorAction):
    name = 'Export As PDF...'
    tooltip = 'Save the current view as a PDF'
    enabled_name = 'printable'

    def perform(self, event):
        dialog = FileDialog(parent=event.task.window.control, action='save as')
        if dialog.open() == OK:
            self.active_editor.save_as_pdf(dialog.path)

class ExitAction(Action):
    name = 'Quit'
    accelerator = 'Ctrl+Q'
    tooltip = 'Quit the program'
    menu_role = "Quit"

    def perform(self, event):
        event.task.window.application.exit()

class NameChangeAction(EditorAction):
    """Extension to the EditorAction that provides a user-updatable menu item
    name based on a trait
    
    EditorAction is subclassed from ListeningAction, and the ListeningAction
    methods destroy and _object_chaged must be called because the new
    trait name 'menu_item_name' can't be added to list of traits managed by
    ListeningAction and so must be taken care of here before the superclass
    can do its work.
    """
    menu_item_name = Str

    def destroy(self):
        """ Called when the action is no longer required.

        Remove all the task listeners.

        """

        if self.object:
            self.object.on_trait_change(
                self._menu_item_update, self.menu_item_name, remove=True
            )
        super(NameChangeAction, self).destroy()

    def _menu_item_name_changed(self, old, new):
        obj = self.object
        if obj is not None:
            if old:
                obj.on_trait_change(self._menu_item_update, old, remove=True)
            if new:
                obj.on_trait_change(self._menu_item_update, new)
        self._label_update()

    def _object_changed(self, old, new):
        kind = 'menu_item'
        method = getattr(self, '_%s_update' % kind)
        name = getattr(self, '%s_name' % kind)
        if name:
            if old:
                old.on_trait_change(method, name, remove=True)
            if new:
                new.on_trait_change(method, name)
        method()
        super(NameChangeAction, self)._object_changed(old, new)

    def _menu_item_update(self):
        if self.menu_item_name:
            if self.object:
                self.name = str(self._get_attr(self.object, 
                                               self.menu_item_name, 'Undo'))
            else:
                self.name = 'Undo'
        else:
            self.name = 'Undo'

class UndoAction(NameChangeAction):
    name = 'Undo'
    accelerator = 'Ctrl+Z'
    tooltip = 'Undo last action'
    image = ImageResource('undo')
    enabled_name = 'can_undo'
    menu_item_name = 'undo_label'

    def perform(self, event):
        self.active_editor.undo()

class RedoAction(NameChangeAction):
    name = 'Redo'
    accelerator = 'Ctrl+Shift+Z'
    tooltip = 'Redo the last undone action'
    image = ImageResource('redo')
    enabled_name = 'can_redo'
    menu_item_name = 'redo_label'

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

class WidgetInspectorAction(Action):
    name = 'Widget Inspector'
    tooltip = 'Open the wxPython Widget Inspector'

    def perform(self, event):
        wx.lib.inspection.InspectionTool().Show()


class BaseDynamicSubmenuGroup(Group):
    """ A group used for a dynamic menu.
    """

    #### 'ActionManager' interface ############################################

    id = 'DynamicMenuGroup'
    items = List

    #### 'TaskChangeMenuManager' interface ####################################

    # The ActionManager to which the group belongs.
    manager = Any

    # ENTHOUGHT QUIRK: This doesn't work: can't have a property depending on
    # a task because this forces task_default to be called very early in the
    # initialization process, before the window hierarchy is defined.
    #
    # active_editor = Property(Instance(IEditor),
    #                         depends_on='task.active_editor')
    
    event_name = Str('change this to the Event trait')
        
    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self, *args, **kwargs):
        # Override this in your subclass to return the list of actions
        return []

    def _rebuild(self, *args, **kwargs):
        # Clear out the old group, then build the new one.
        self.destroy()
        
        # Get the new items, passing the event arguments to the method
        self.items = self._get_items(*args, **kwargs)

        # Inform our manager that it needs to be rebuilt.
        self.manager.changed = True
        
    #### Trait initializers ###################################################

    def _items_default(self):
        log.debug("DYNAMICGROUP: _items_default!!!")
        if True:
            t = self._get_trait_for_event()
            t.on_trait_change(self._rebuild, self.event_name)
        else:
            self._set_trait_event()
        return self._get_items()

    def _set_trait_event(self):
        raise NotImplementedError

    def _manager_default(self):
        manager = self
        while isinstance(manager, Group):
            manager = manager.parent
        log.debug("DYNAMICGROUP: _manager_default=%s!!!" % manager)
        return manager
    
    # ENTHOUGHT QUIRK: This doesn't work: the trait change decorator never
    # seems to get called, however specifying the on_trait_change in the
    # _items_default method works.
    #
    #    @on_trait_change('task.layer_selection_changed')
    #    def updated_fired(self, event):
    #        log.debug("SAVELAYERGROUP: updated!!!")
    #        self._rebuild(event)


class TaskDynamicSubmenuGroup(BaseDynamicSubmenuGroup):
    """ A group used for a dynamic menu.
    """

    # The task instance must be passed in as an attribute creation argument
    # because we need to bind on a task trait change to update the menu
    task = Instance('peppy2.framework.task.FrameworkTask')
        
    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_trait_for_event(self):
        return self.task
        
    def _set_trait_event(self):
        self.task.on_trait_change(self._rebuild, self.event_name)
        
    #### Trait initializers ###################################################
    
    def _task_default(self):
        log.debug("DYNAMICGROUP: _task_default=%s!!!" % self.manager.controller.task)
        return self.manager.controller.task


class ApplicationDynamicSubmenuGroup(BaseDynamicSubmenuGroup):
    """ A group used for a dynamic menu based on an application event.
    """

    # The application instance must be a trait so we can set an on_trait_change
    # handler
    application = Instance('envisage.ui.tasks.api.TasksApplication')

    def _get_trait_for_event(self):
        return self.application
        
    def _set_trait_event(self):
        self.application.on_trait_change(self._rebuild, self.event_name)

    #### Trait initializers ###################################################
    
    def _application_default(self):
        print "APPLICATION!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        print "APPLICATION!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        print "APPLICATION!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        print "APPLICATION!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        print "APPLICATION!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        print self.manager.controller.task.window.application
        log.debug("DYNAMICGROUP: _task_default=%s!!!" % self.manager.controller.task)
        return self.manager.controller.task.window.application
