import os
import sys
import wx.lib.inspection

import fs

# Enthought library imports.
from pyface.api import ImageResource, FileDialog, YES, NO, OK, CANCEL
from pyface.action.api import Action, ActionItem, Group
from pyface.tasks.action.api import EditorAction
from traits.api import on_trait_change, Property, Instance, Bool, Str, Unicode, Any, List, Int

from omnivore.framework.about import AboutDialog
from omnivore.utils.file_guess import FileGuess
from omnivore.utils.wx.dialogs import get_file_dialog_wildcard

import logging
log = logging.getLogger(__name__)


class NewFileAction(Action):
    """ An action for creating a new empty file that can be edited by a particular task
    """
    tooltip = Property(Unicode, depends_on='name')

    task_id = Any
    
    def perform(self, event=None):
        task = event.task.window.application.find_or_create_task_of_type(self.task_id)
        guess = FileGuess.get_packaged_file(self.name)
        task.new(guess)

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
        if event.task.active_editor:
            uri = event.task.active_editor.most_recent_uri
            most_recent = ""
            try:
                fs_, relpath = fs.opener.opener.parse(uri)
                if fs_.hassyspath(relpath):
                    most_recent = os.path.dirname(fs_.getsyspath(relpath))
            except fs.errors.FSError:
                pass
            dialog = FileDialog(default_directory=most_recent, parent=event.task.window.control, title="Open File")
        else:
            dialog = FileDialog(parent=event.task.window.control, title="Open File")
        if dialog.open() == OK:
            event.task.window.application.load_file(dialog.path, event.task)

class SaveAction(EditorAction):
    name = 'Save'
    accelerator = 'Ctrl+S'
    tooltip = 'Save the current file'
    image = ImageResource('file_save')
    enabled_name = 'can_save' # enabled based on state of task.active_editor.can_save

    def perform(self, event):
        self.active_editor.save(None)

class SaveAsAction(EditorAction):
    name = 'Save As...'
    accelerator = 'Ctrl+Shift+S'
    tooltip = 'Save the current file with a new name'
    image = ImageResource('file_save_as')

    def perform(self, event):

        dialog = FileDialog(default_filename=self.active_editor.document.name, parent=event.task.window.control, action='save as', title="Save File As", wildcard=get_file_dialog_wildcard(self.active_editor.export_data_name, self.active_editor.export_extensions))
        if dialog.open() == OK:
            self.active_editor.save(dialog.path, saver=self.active_editor.encode_data)

class RevertAction(EditorAction):
    name = 'Revert'
    tooltip = 'Revert to last saved version'

    def perform(self, event):
        message = "Revert file from\n\n%s?" % self.active_editor.document.metadata.uri
        result = event.task.window.confirm(message=message, default=NO, title='Revert File?')
        if result == CANCEL:
            return
        elif result == YES:
            guess = FileGuess(self.active_editor.document.metadata.uri)
            self.active_editor.load(guess)

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
        dialog = FileDialog(parent=event.task.window.control, action='save as', title="Save PDF")
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

class CutAction(EditorAction):
    name = 'Cut'
    accelerator = 'Ctrl+X'
    tooltip = 'Cut and remove the current selection'
    enabled_name = 'can_cut'

    def perform(self, event):
        self.active_editor.cut()

class CopyAction(EditorAction):
    name = 'Copy'
    accelerator = 'Ctrl+C'
    tooltip = 'Copy the current selection'
    enabled_name = 'can_copy'

    def perform(self, event):
        self.active_editor.copy()

class PasteAction(EditorAction):
    name = 'Paste'
    accelerator = 'Ctrl+V'
    tooltip = 'Paste from the clipboard'
    enabled_name = 'can_paste'

    def perform(self, event):
        self.active_editor.paste()

class SelectAllAction(Action):
    name = 'Select All'
    accelerator = 'Ctrl+A'
    tooltip = 'Select the entire document'

    def perform(self, event):
        event.task.active_editor.select_all()

class SelectNoneAction(Action):
    name = 'Select None'
    accelerator = 'Shift+Ctrl+A'
    tooltip = 'Clear selection'

    def perform(self, event):
        event.task.active_editor.select_none()

class SelectInvertAction(Action):
    name = 'Invert Selection'
    tooltip = 'Invert selection'

    def perform(self, event):
        event.task.active_editor.select_invert()

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
        
        from omnivore.framework.preferences import FrameworkPreferenceDialog
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

class OpenLogDirectoryAction(Action):
    name = 'Open Log Directory in File Manager'
    tooltip = 'Open the log directory in the desktop file manager program'

    def perform(self, event):
        app = event.task.window.application
        filename = app.get_log_file_name("dummy")
        dirname = os.path.dirname(filename)
        import subprocess
        if sys.platform.startswith("win"):
            file_manager = 'explorer'
        elif sys.platform == "darwin":
            file_manager = '/usr/bin/open'
        else:
            file_manager = 'xdg-open'
        subprocess.call([file_manager, dirname])

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

    def _get_items(self, event_data=None):
        # Override this in your subclass to return the list of actions
        return []

    def _rebuild(self, new_trait_val):
        # Clear out the old group, then build the new one.
        self.destroy()
        
        # Get the new items, passing the event arguments to the method
        self.items = self._get_items(new_trait_val)
        
        # Set up parent so that radio items can determine their siblings to
        # uncheck others when checked. (see the _checked_changed method in
        # pyface/ui/wx/action/action_item.py)
        for item in self.items:
            item.parent = self

        # Inform our manager that it needs to be rebuilt.
        self.manager.changed = True
        
    #### Trait initializers ###################################################

    def _items_default(self):
        log.debug("DYNAMICGROUP: _items_default!!!")
        t = self._get_trait_for_event()
        t.on_trait_change(self._rebuild, self.event_name)
        return self._get_items()

    def _get_trait_for_event(self):
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
    task = Instance('omnivore.framework.task.FrameworkTask')
        
    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_trait_for_event(self):
        return self.task
        
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

    #### Trait initializers ###################################################
    
    def _application_default(self):
        log.debug("DYNAMICGROUP: _application_default=%s!!!" % self.manager.controller.task.window.application)
        return self.manager.controller.task.window.application


class SwitchDocumentAction(Action):
    document_id = Int
    
    name = Str
    
    def perform(self, event):
        app = event.task.window.application
        doc = app.get_document(self.document_id)
        if doc is not None:
            log.debug("Switching to %s, task=%s" % (doc, doc.last_task_id))
            task = app.find_active_task_of_type(doc.last_task_id)
            task.find_tab_or_open(doc)


class DocumentSelectGroup(ApplicationDynamicSubmenuGroup):
    """ A menu for creating a new file for each type of task
    """

    event_name = 'successfully_loaded_event'
    
    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self, event_data=None):
        documents = sorted(self.application.documents, key=lambda x: x.name.lower())
        items = []
        for document in documents:
            action = SwitchDocumentAction(document_id=document.document_id, name=document.menu_name)
            items.append(ActionItem(action=action))
        return items


class NewViewInNewTaskAction(Action):
    factory_id = Str
    
    def perform(self, event):
        event.task.window.application.create_task_from_factory_id(event.task.active_editor, self.factor_id)


class NewViewInGroup(TaskDynamicSubmenuGroup):
    name = '<this is not used; the name is set in the SMenu in which this group is added>'
    tooltip = 'New view of the project with a different task'
    event_name = 'document_changed'

    def perform(self, event):
        event.task.new_window(view=event.task.active_editor)
    
    @on_trait_change('task.document_changed')
    def _update_name(self):
        if self.task.active_editor:
            # The name of the menu is taken from the SMenu in which this Group
            # is included, not the name in this object.
            self.manager.name = "New View of %s" % self.task.active_editor.document.name
            # Tell the MenuManager in the hierarchy that the SMenu name has
            # changed.  This depth up the hierarchy (grandparent) works for
            # this instance where this group is a child of the SMen.
            self.manager.parent.parent.changed = True

    def _get_items(self, event_data=None):
        e = self.task.active_editor
        items = []
        if e:
            factories = self.task.window.application.get_possible_task_factories(e.document)
            for factory in factories:
                action = NewViewInNewTaskAction(name="In a %s Window" % factory.name, factor_id=factory.id)
                items.append(ActionItem(action=action))
        return items

