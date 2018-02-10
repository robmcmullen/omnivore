import os
import sys
import wx.lib.inspection
import wx.lib.dialogs

import fs

# Enthought library imports.
from pyface.api import ImageResource, FileDialog, YES, NO, OK, CANCEL
from traits.api import on_trait_change, Property, Instance, Bool, Str, Unicode, Any, List, Int

from .enthought_api import Action, ActionItem, Group, EditorAction, NameChangeAction, TaskDynamicSubmenuGroup, ApplicationDynamicSubmenuGroup
from omnivore.framework.about import AboutDialog
from omnivore.utils.file_guess import FileGuess
from omnivore.utils.wx.dialogs import get_file_dialog_wildcard, prompt_for_dec
from omnivore.utils.wx.error_logger import show_logging_frame
from omnivore.templates import iter_templates

import logging
log = logging.getLogger(__name__)


class DocumentationOnlyAction(Action):
    ""
    enabled = False
    description = ""
    tooltip = ""


class ShowLoggerAction(Action):
    """ Displays a window that can be used to turn on debugging of particular
    parts of the program.

    The log levels shown initially are the default log levels for each logger.
    Using the ``Filter`` text entry box, you can enter a string or a comma
    separated list of strings that will be used to select which loggers get
    switched to *DEBUG* mode. Everything else gets set to its default state,
    usually either *INFO* or *WARNING*.

    The string is not a regular expression, but will match partial strings.
    """
    name = "Show Debug Log"
    tooltip = "Open a window to view and manage debug logging"

    def perform(self, event=None):
        show_logging_frame()


class NewFileAction(Action):
    """A list of supported file types that can be created by Omnivore.

    Choosing an item in this list will open up a new tab in the current window
    showing a new blank template of the selected file format.

    Available templates include:
    """
    doc_hint = "parent,list"
    tooltip = Property(Unicode, depends_on='name')

    task_id = Any

    uri = Str

    def perform(self, event=None):
        task = event.task.window.application.find_or_create_task_of_type(self.task_id)
        log.debug("Loading %s as %s" % (self.uri, task))
        guess = FileGuess(self.uri)
        task.new(guess)

    def _get_tooltip(self):
        return u'Open a new %s' % self.name


class NewEmptyFileAction(EditorAction):
    """Create a blank file by specifying the size in bytes
    """
    name = "Blank File"
    tooltip = "Create a blank file"

    def perform(self, event=None):
        e = self.active_editor
        val = prompt_for_dec(e.window.control, 'Enter file size in bytes', 'New Blank File', 256)
        val = 256
        if val is not None and val > 0:
            uri = "blank://%d" % val
            guess = FileGuess(uri)
            self.task.new(guess)


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

        for template in iter_templates():
            name = template.get("label", template["uri"])
            task_id = self.application.find_best_task_id(template.get("task", "byte_edit"))
            log.debug("NewFileAction for %s as %s" % (name, task_id))
            action = NewFileAction(name=name, uri=template["uri"], task_id=task_id)
            items.append((name, ActionItem(action=action)))
        items.sort()
        items = [i[1] for i in items]
        blank = NewEmptyFileAction(task_id=task_id)
        items[0:0] = [ActionItem(action=blank)]
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
    """Open a file using a file select dialog box.

    """
    name = 'Open...'
    accelerator = 'Ctrl+O'
    tooltip = 'Open a file'
    image = ImageResource('file_open')

    def perform(self, event):
        path = event.task.prompt_local_file_dialog()
        if path is not None:
            event.task.window.application.load_file(path, event.task)


class SaveAction(EditorAction):
    """Save the file, overwriting the previously saved version

    """
    name = 'Save'
    accelerator = 'Ctrl+S'
    tooltip = 'Save the current file'
    image = ImageResource('file_save')
    enabled_name = 'can_save' # enabled based on state of task.active_editor.can_save

    def perform(self, event):
        self.active_editor.save(None)


class SaveAsAction(EditorAction):
    """Save the file to a new filename, leaving the originally loaded unchanged
    on disk.

    """
    name = 'Save As...'
    accelerator = 'Ctrl+Shift+S'
    tooltip = 'Save the current file with a new name'
    image = ImageResource('file_save_as')

    def perform(self, event):
        wx.CallAfter(self.prompt)

    def prompt(self):
        path = self.active_editor.task.prompt_local_file_dialog(save=True, default_filename=self.active_editor.document.name)
        if path:
            self.active_editor.save(path, saver=self.active_editor.encode_data)


class RevertAction(EditorAction):
    """Reverts the file to the last saved version on disk

    This throws away any edits and is not undoable.
    """
    name = 'Revert'
    tooltip = 'Revert to last saved version'

    def perform(self, event):
        uri = self.active_editor.document.metadata.uri
        message = "Revert file from\n\n%s?" % uri
        result = event.task.confirm(message=message, title='Revert File?')
        if result:
            try:
                guess = FileGuess(uri)
                document = event.task.window.application.guess_document(guess)
                self.active_editor.load(document)
            except fs.errors.FSError, e:
                event.task.error("Can't revert from %s:\n\n%s" % (uri, str(e)), 'Revert Error')


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
    tooltip = 'Save the current view as a PDF (if possible with this editor)'
    enabled_name = 'printable'

    def perform(self, event):
        path = event.task.prompt_local_file_dialog(save=True, title="Save PDF")
        if path:
            self.active_editor.save_as_pdf(path)


class SaveAsImageAction(EditorAction):
    name = 'Save As Image...'
    tooltip = 'Save the current view as an image (if possible with this editor)'
    enabled_name = 'imageable'

    def perform(self, event):
        path = event.task.prompt_local_file_dialog(save=True, title="Save Image")
        if path:
            self.active_editor.save_as_image(path)


class ExitAction(Action):
    name = 'Quit'
    accelerator = 'Ctrl+Q'
    tooltip = 'Quit the program'
    menu_role = "Quit"

    def perform(self, event):
        event.task.window.application.exit()


class UndoAction(NameChangeAction):
    """Undo the last action

    Actions that modify data are undoable; some that modify the metadata are
    but movement commands are not stored in the undo list, so for example
    caret moves or changes to selection regions are not undoable.
    """
    default_name = 'Undo'
    name = default_name
    accelerator = 'Ctrl+Z'
    tooltip = 'Undo last action'
    image = ImageResource('undo')
    enabled_name = 'can_undo'
    menu_item_name = 'undo_label'

    def perform(self, event):
        self.active_editor.undo()


class RedoAction(NameChangeAction):
    """Redo the last operation that was undone.  See `Undo`_.
    """
    default_name = 'Redo'
    name = default_name
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
    """Inverts the selection; that is, select everything that is currently unselected and unselect those that were selected.

    """
    name = 'Invert Selection'
    tooltip = 'Invert selection'

    def perform(self, event):
        event.task.active_editor.select_invert()


class PreferencesAction(Action):
    """Open a window to change program settings and defaults.

    """
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
    tooltip = 'Display window with version number and author info'
    menu_role = "About"

    def perform(self, event):
        # Don't rely on the event window as this might be called by the OSX
        # minimal menu which, once installed by the OSX plugin, never changes
        # with the task.
        top = event.task.window.application.active_window
        AboutDialog(top.control, top.active_task)


class OpenLogDirectoryAction(Action):
    """Open the log directory in the desktop file manager program.

    The log directory will contain debug logs (if enabled) and other files,
    most of which are generally only useful for developers or to get more
    information to send to the developers in the event of a problem.
    """
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


class UserGuideAction(Action):
    name = "User Guide"
    tooltip = 'Display the user guide in a new window'

    def perform(self, event):
        # Don't rely on the event window as this might be called by the OSX
        # minimal menu which, once installed by the OSX plugin, never changes
        # with the task.
        event.task.window.application.show_help()


class NewWindowAction(Action):
    """Open a new, blank Omnivore window that can be used to load new files
    or to provide a second view on a currently loaded file.

    """
    name = 'New Window'
    tooltip = 'Open a new window'

    def perform(self, event):
        event.task.new_window()


class WidgetInspectorAction(Action):
    name = 'Widget Inspector'
    tooltip = 'Open the wxPython Widget Inspector'

    def perform(self, event):
        wx.lib.inspection.InspectionTool().Show()


class GarbageObjectsAction(Action):
    name = 'View Uncollectable GC Objects'
    tooltip = "View list of objects that have no external references but the gc can't collect"

    def perform(self, event):
        import gc
        obj_list = []
        for obj in gc.garbage:
            obj_list.append(str(obj))
        text = "\n".join(obj_list)
        dlg = wx.lib.dialogs.ScrolledMessageDialog(event.task.window.control, text, "Unreachable but Uncollectable Objects")
        dlg.ShowModal()


class SwitchDocumentAction(Action):
    doc_hint = "ignore"

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
                action = NewViewInNewTaskAction(name="In a %s Tab" % factory.name, factor_id=factory.id)
                items.append(ActionItem(action=action))
        return items
