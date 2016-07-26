""" Text editor sample task

"""
import wx

# Enthought library imports.
from pyface.wx.aui import aui
from pyface.api import ImageResource, FileDialog, YES, NO, OK, CANCEL
from pyface.action.api import StatusBarManager, Group, Separator, ActionEvent
from pyface.tasks.api import Task, TaskWindow, TaskLayout, TaskWindowLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, TaskToggleGroup
from traits.api import provides, on_trait_change, Property, Instance, Bool, Str, Unicode, Int, Event
from apptools.preferences.api import PreferencesHelper

from omnivore.dock_panes import FileBrowserPane
from omnivore.framework.i_about import IAbout
from omnivore.framework.actions import *
from omnivore.framework.status_bar_manager import FrameworkStatusBarManager

import logging
log = logging.getLogger(__name__)

@provides(IAbout)
class FrameworkTask(Task):
    """ A simple task for opening a blank editor.
    """
    
    # Class properties (not traits!) because they must be available in a TaskFactory 
    
    new_file_text = ''
    
    about_application = "about://omnivore"  # URL to load if no document specified on the command line

    #### Task interface #######################################################

    id = 'omnivore.framework.framework_task'
    name = 'Framework'

    icon = Instance(ImageResource)

    active_editor = Property(Instance(IEditor),
                             depends_on='editor_area.active_editor')

    editor_area = Instance(IEditorAreaPane)
    
    #### FrameworkTask interface ##############################################
    
    preferences_helper = Instance(PreferencesHelper)
    
    status_bar_debug_width = Int(150)
    
    start_new_editor_in_new_window = Bool(False)
    
    print_data = Any
    
    document_changed = Event
    
    keyboard_shortcuts = Any
    
    #### 'IAbout' interface ###################################################
    
    about_title = Unicode('Omnivore XL')
    
    about_version = Unicode
    
    about_description = Unicode('Byte into the meat of Atari Software!')
    
    about_website = Str('http://playermissile.com/omnivore')
    
    about_image = Instance(ImageResource, ImageResource('omnivore256'))
    
    #### 'IErrorReporter' interface ###########################################
    
    error_email_from = Str
    
    error_email_passwd = Str
    
    error_email_to = Str
    
    def _about_version_default(self):
        from omnivore import __version__
        return __version__
    
    ###########################################################################
    # 'Task' interface.
    ###########################################################################
    
    def _icon_default(self):
        return ImageResource('omnivore')

    def _menu_bar_default(self):
        menus = []
        self.add_menu(menus, "Menu", "File", "NewGroup", "OpenGroup", "ImportGroup", "SaveGroup", "RevertGroup", "PrintGroup", "ExportGroup", "ExitGroup")
        self.add_menu(menus, "Menu", "Edit", "UndoGroup", "CopyPasteGroup", "SelectGroup", "FindGroup", "PrefGroup")
        self.add_menu(menus, "Menu", "View", "ViewPredefinedGroup", "ViewZoomGroup", "ViewChangeGroup", "ViewConfigGroup", "ViewToggleGroup", "TaskGroup", "ViewDebugGroup")
        self.add_menu(menus, "Menu", "Documents", "DocumentGroup")
        self.add_menu(menus, "Menu", "Window", "NewTaskGroup", "WindowGroup")
        self.add_menu(menus, "Menu", "Help", "AboutGroup", "DocGroup", "BugReportGroup", "DebugGroup")
        
        return SMenuBar(*menus)

    def _tool_bars_default(self):
        return [ SToolBar(self.get_groups("Tool", "File", "NewGroup", "OpenGroup", "SaveGroup"),
                          self.get_groups("Tool", "Edit", "UndoGroup", "CopyPasteGroup", "SelectGroup", "FindGroup"),
                          self.get_groups("Tool", "View", "ViewZoomGroup", "ViewChangeGroup", "ViewConfigGroup"),
                          show_tool_names=False, id="%s:ToolBar" % self.id),
                 ]

    def _status_bar_default(self):
        return FrameworkStatusBarManager(message="Hi!", debug_width=self.status_bar_debug_width)

    def _default_layout_default(self):
        return TaskLayout(
            left=VSplitter(
                PaneItem('omnivore.framework.file_browser_pane'),
                ))
    
    def _keyboard_shortcuts_default(self):
        actions = []
        
        # Give each keyboard action a wx ID so that it can be identified in the
        # menu callback
        for action in self.get_keyboard_actions():
            id = wx.NewId()
            action.keyboard_shortcut_id = id
            actions.append(action)
        return actions

    ##### Task setup/cleanup

    def initialized(self):
        self.window.application.remember_perspectives(self.window)
        self.initialize_class_preferences()
        c = self.editor_area.control
        c.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN, self.on_tab_context_menu)
        c.Bind(aui.EVT_AUINOTEBOOK_BG_RIGHT_DOWN, self.on_tab_background_context_menu)
    
    def initialize_class_preferences(self):
        pass

    def activated(self):
        log.debug("  status bar: %s" % self.status_bar)
        active = self.active_editor
        if active:
            self.status_bar.message = active.name
        else:
            self.status_bar.message = self.name
        self.window.icon = self.icon
        self.set_keyboard_shortcuts()
        self._active_editor_tab_change(None)
        visible = self.pane_layout_initial_visibility()
        for pane in self.window.dock_panes:
            if pane.id in visible:
                pane.visible = visible[pane.id]

    def pane_layout_initial_visibility(self):
        return {}

    def create_central_pane(self):
        """ Create the central pane: the text editor.
        """
        self.editor_area = EditorAreaPane()
        return self.editor_area

    def create_dock_panes(self):
        """ Create the file browser and connect to its double click event.
        """
        browser = FileBrowserPane()
        handler = lambda: self.window.application.load_file(browser.selected_file, self)
        browser.on_trait_change(handler, 'activated')
        return [ browser ]
    
    def prepare_destroy(self):
        self.window.application.remember_perspectives(self.window)
        self.destroy_minibuffer()

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def new(self, source=None, **kwargs):
        """ Opens a new tab
        
        :param source: optional :class:`FileGuess` or :class:`Editor` instance
        that will load a new file or create a new view of the existing editor,
        respectively.
        """
        editor = self.get_editor()
        self.editor_area.add_editor(editor)
        self.editor_area.activate_editor(editor)
        if hasattr(source, 'get_metadata') or source is None:
            editor.load(source, **kwargs)
            if source is not None:
                self.window.application.successfully_loaded_event = source.metadata.uri
        elif hasattr(source, 'document_id'):
            source.load_permute(editor)
            editor.init_extra_metadata(source)
            editor.view_document(source)
            self.window.application.successfully_loaded_event = source.metadata.uri
        else:
            editor.view_document(source.document, source)
        self.activated()
    
    def find_tab_or_open(self, document):
        for editor in self.editor_area.editors:
            if editor.document == document:
                self.editor_area.activate_editor(editor)
                return
        self.new(document)

    def new_window(self, task=None, view=None):
        """ Opens a new window
        
        With no arguments, opens an empty window with the default task.
        
        :keyword task: optional task to set the task of the new window
        
        :keyword view: optional :class:`Editor` instance that will set the
        task of the new window and will create a new view of the editor in the
        first tab
        """
        log.debug("Opening new window!!!")
        window = self.window.application.create_window()
        log.debug("  window=%s" % str(window))
        log.debug("  self=%s" % str(self.window))
        log.debug("  task type: %s" % str(task))
        log.debug("  view of: %s" % str(view))
        task_id = None
        if view is not None:
            task_cls = view.editor_area.task.__class__
            log.debug("  task_cls: %s" % str(task_cls))
        elif task is not None:
            if isinstance(task, FrameworkTask):
                task_cls = task.__class__
            else:
                task_cls = task
        else:
            task_id = self.window.application.startup_task
        if task_id is None:
            task = task_cls()
            task_id = task.id
        log.debug("  task id: %s" % task_id)
        log.debug("  returned factory: %s" % self.window.application._get_task_factory(task_id))
        for factory in self.window.application.task_factories:
            log.debug("    factory: %s, %s" % (factory.id, factory))
        
        task = self.window.application.create_task(task_id)
        log.debug("  created task: %s" % task)
        window.add_task(task)
        window.activate_task(task)
        if view is not None:
            task.new(view)
        window.open()
        log.debug("All windows: %s" % self.window.application.windows)

    def save(self):
        """ Attempts to save the current file, prompting for a path if
            necessary. Returns whether the file was saved.
        """
        editor = self.active_editor
        try:
            editor.save()
        except IOError:
            # If you are trying to save to a file that doesn't exist, open up a
            # FileDialog with a 'save as' action.
            dialog = FileDialog(parent=self.window.control,
                                action='save as')
            if dialog.open() == OK:
                editor.save(dialog.path)
            else:
                return False
        return True

    def allow_different_task(self, guess, other_task):
        """Hook to allow tasks to abort loading different task window.
        
        This method allows a hook to confirm that the user wants to load a file
        that can't be handled by the current task.  For example, this can be
        used to prompt with a dialog box.
        
        :rtype: Boolean; True means continue with the file load in a separate
        task window
        """
        return True

    def _print_data_default(self):
        data = wx.PrintData()
        data.SetPaperId(wx.PAPER_LETTER)
        data.SetOrientation(wx.PORTRAIT)
        return data

    def page_setup(self):
        data = wx.PageSetupDialogData(self.print_data)
        data.SetDefaultMinMargins(True)

        dlg = wx.PageSetupDialog(self.window.control, data)

        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetPageSetupData().GetPrintData()
            self.print_data = wx.PrintData(data)  # Force a copy

        dlg.Destroy()

    def debug(self):
        """Debug stuff!
        """
        action_schemas = list(self.menu_bar.items)
        action_schemas.extend(self.tool_bars)
        for action in self._iter_schema_items(action_schemas):
            if hasattr(action, 'name'):
                action.name = action.name + "!"

    def ask_attempt_loading_as_octet_stream(self, guess, other_task):
        return self.window.confirm("%s\n\nwas identified with a MIME type of %s\nand can also be edited in a %s window.\n\nOpen here in the %s window instead?" % (guess.metadata.uri, guess.metadata.mime, other_task.new_file_text, self.name), "Edit in %s?" % self.name) == YES

    ###########################################################################
    # 'FrameworkTask' convenience functions.
    ###########################################################################
    
    def get_preferences(self):
        return self.window.application.get_preferences(self.preferences_helper)

    def create_menu(self, location, menu_name, *group_names):
        items = []
        for group_name in group_names:
            self.add_actions_and_groups(items, location, menu_name, group_name)
        return SMenu(*items, id=menu_name, name=menu_name)

    def add_menu(self, menu, location, menu_name, *group_names):
        entry = self.create_menu(location, menu_name, *group_names)
        menu.append(entry)

    def add_actions_and_groups(self, menu_items, location, menu_name, group_name):
        actions = self.get_actions_wrapper(location, menu_name, group_name)

        groups = []
        group_suffix = ""
        group_index = 0
        current = []
        
        for item in actions:
            if isinstance(item, Group) or isinstance(item, SMenu):
                if current:
                    group = Group(*current, id="%s%s" % (group_name, group_suffix))
                    group_index += 1
                    group_suffix = str(group_index)
                    groups.append(group)
                    current = []
                groups.append(item)
            else:
                current.append(item)
        if current:
            group = Group(*current, id="%s%s" % (group_name, group_suffix))
            groups.append(group)

        menu_items.append(Separator(id="%sStart" % group_name, separator=False))
        for group in groups:
            menu_items.append(group)
        menu_items.append(Separator(id="%sEnd" % group_name, separator=False))

    def get_group(self, location, menu_name, group_name):
        actions = self.get_actions_wrapper(location, menu_name, group_name)
        return Group(*actions, id=group_name)
    
    def get_groups(self, location, menu_name, *group_names):
        actions = []
        for group_name in group_names:
            actions.extend(self.get_actions_wrapper(location, menu_name, group_name))
        return Group(*actions, id=menu_name)

    def get_actions_wrapper(self, location, menu_name, group_name):
        actions = self.get_actions(location, menu_name, group_name)
        if actions is None:
            # fall back to this class if it's not found in subclass
            actions = FrameworkTask.get_actions(self, location, menu_name, group_name)
        return actions

    def get_actions(self, location, menu_name, group_name):
        # allow spaces in menu names by removing them for function lookup
        menu_lookup = menu_name.replace(" ","")
        method_name = "get_actions_%s_%s_%s" % (location, menu_lookup, group_name)
        try:
            method = getattr(self, method_name)
            actions = method()
        except AttributeError:
            log.warning("%s actions not found for %s/%s in %s" % (location, menu_name, group_name, self.id))
            actions = []
        return actions
    
    def get_actions_Menu_File_NewGroup(self):
        return [
            SMenu(NewFileGroup(), id="NewFileGroup", name="New"),
            ]
    
    def get_actions_Menu_File_OpenGroup(self):
        return [
            OpenAction(),
            ]
    
    def get_actions_Menu_File_SaveGroup(self):
        return [
            SaveAction(),
            SaveAsAction(),
            ]
    
    def get_actions_Menu_File_RevertGroup(self):
        return [
            RevertAction(),
            ]
    
    def get_actions_Menu_File_PrintGroup(self):
        return [
            PageSetupAction(),
            PrintPreviewAction(),
            PrintAction(),
            ]
    
    def get_actions_Menu_File_ExportGroup(self):
        return [
            SaveAsPDFAction(),
            ]
    
    def get_actions_Menu_File_ExitGroup(self):
        return [
            ExitAction(),
            ]

    def get_actions_Menu_Edit_UndoGroup(self):
        return [
            UndoAction(),
            RedoAction(),
            ]
    
    def get_actions_Menu_Edit_CopyPasteGroup(self):
        return [
            CutAction(),
            CopyAction(),
            PasteAction(),
            ]
    
    def get_actions_Menu_Edit_SelectGroup(self):
        return [
            SelectAllAction(),
            SelectNoneAction(),
            SelectInvertAction(),
            ]
    
    def get_actions_Menu_Edit_PrefGroup(self):
        return [
            Group(PreferencesAction(), absolute_position="last"),
            ]
    
    def get_actions_Menu_View_TaskGroup(self):
        return [
            DockPaneToggleGroup(),
            TaskToggleGroup(),
            ]
    
    def get_actions_Menu_Documents_DocumentGroup(self):
        return [
            DocumentSelectGroup(),
            ]
    
    def get_actions_Menu_Window_NewTaskGroup(self):
        return [
            SMenu(
                NewViewInGroup(id="a1", separator=True),
                id='WindowTabGroupSubmenu2', name="New View In..."),
            ]
    
    def get_actions_Menu_Window_WindowGroup(self):
        return [
            NewWindowAction(),
            ]
    
    def get_actions_Menu_Help_AboutGroup(self):
        return [
            AboutAction()
            ]
    
    def get_actions_Menu_Help_BugReportGroup(self):
        return [
            OpenLogDirectoryAction(),
            ]
    
    def get_actions_Menu_Help_DebugGroup(self):
        return [
            SMenu(TaskAction(name='Dynamic Menu Names', method='debug',
                             tooltip='Do some debug stuff',
                             image=ImageResource('debug')),
                  WidgetInspectorAction(),
                  id="Debug", name="Debug"),
            ]
    
    def get_actions_Tool_File_NewGroup(self):
        return [
            TaskAction(method='new',
                       tooltip='New file',
                       image=ImageResource('file_new')),
            ]
    
    def get_actions_Tool_File_OpenGroup(self):
        return [
            OpenAction(),
            ]
    
    def get_actions_Tool_File_SaveGroup(self):
        return [
            SaveAction(),
            SaveAsAction(),
            ]
    
    def get_actions_Tool_Edit_UndoGroup(self):
        return [
            UndoAction(),
            RedoAction(),
            ]
    
    def get_keyboard_actions(self):
        """Return a list of actions to be used as keyboard shortcuts only, not
        appearing in a menubar or toolbar
        """
        return []
    
    def parse_accelerator(self, text, id):
        if text:
            entry = wx.AcceleratorEntry(cmdID=id)
            entry.FromString(text)
            return entry
        return None
    
    def create_accelerator_table(self):
        shortcut_map = {}
        table_entries = []
        for action in self.keyboard_shortcuts:
            id = action.keyboard_shortcut_id
            table_entry = self.parse_accelerator(action.accelerator, id)
            if table_entry is not None:
                shortcut_map[id] = action
                table_entries.append(table_entry)
        log.debug("Accelerator table entries: %s" % str([t.ToString() for t in table_entries]))
        return shortcut_map, wx.AcceleratorTable(table_entries)
    
    def on_keyboard_shortcut(self, event):
        id = event.GetId()
        log.debug("Keyboard shortcut! %s", id)
        try:
            action = self.keyboard_shortcut_map[id]
        except KeyError:
            log.error("Keyboard shortcut for %s not in this task" % id)
            return
        event = ActionEvent(task=self)
        # Set the task so that dependent traits (e.g.  active_editor for
        # EditorActions) will be available
        action.task = self
        action.perform(event)
    
    def set_keyboard_shortcuts(self):
        shortcut_map, table = self.create_accelerator_table()
        self.window.control.SetAcceleratorTable(table)
        self.keyboard_shortcut_map = shortcut_map
        for id in shortcut_map.keys():
            self.window.control.Bind(wx.EVT_MENU, self.on_keyboard_shortcut, id=id)

    def get_editor(self):
        raise NotImplementedError
    
    def restore_toolbars(self, window):
        toolbars = window._window_backend.get_toolbars()
        window._window_backend.show_toolbars(toolbars)

    ###########################################################################
    # Minibuffer convenience routines
    ###########################################################################
    
    minibuffer_pane_name = "omnivore.framework.minibuffer"
    
    def create_minibuffer_info(self):
        log.debug("Creating space for minibuffer")
        info = aui.AuiPaneInfo()
        info.Caption("Minibuffer")
        info.LeftDockable(False)
        info.Name(self.minibuffer_pane_name)
        info.RightDockable(False)
        info.Layer(99)
        info.Bottom()
        info.Hide()
        info.DockFixed(True)
        info.CaptionVisible(False)  # hides the caption bar & close button
        info.minibuffer = None
        return info
    
    def show_minibuffer(self, minibuffer, **kwargs):
        # minibuffer_pane_info is stored in the TaskWindow instance because all
        # tasks use the same minibuffer pane in the AUI manager
        try:
            info = self.window.minibuffer_pane_info
        except AttributeError:
            panel = wx.Panel(self.window.control, style=wx.NO_BORDER)
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            close_image = ImageResource('cancel')
            bmp = close_image.create_bitmap()
            close = wx.BitmapButton(panel, -1, bmp, size=(bmp.GetWidth()+10, bmp.GetHeight()+10), style=wx.NO_BORDER)
            close.Bind(wx.EVT_BUTTON, self.on_hide_minibuffer_or_cancel)
            sizer.Add(close, 0, wx.EXPAND)
            panel.SetSizer(sizer)
            info = self.create_minibuffer_info()
            self.window._aui_manager.AddPane(panel, info)
            # info.window is set to panel in the AUI code
            self.window.minibuffer_pane_info = info
        repeat = False
        if info.minibuffer is not None:
            if info.minibuffer.is_repeat(minibuffer):
                log.debug("Reusing old minibuffer control: %s" % info.minibuffer.control)
                repeat = True
            else:
                log.debug("Removing old minibuffer control: %s" % info.minibuffer.control)
                info.window.GetSizer().Hide(0)
                info.window.GetSizer().Remove(0)
                info.minibuffer.destroy_control()
                log.debug("Children: %s" % info.window.GetSizer().Children)
        if not repeat:
            minibuffer.create_control(info.window)
            info.window.GetSizer().Insert(0, minibuffer.control, 1, wx.EXPAND)
            info.window.GetSizer().Layout()
            minibuffer.focus()
            info.minibuffer = minibuffer
            log.debug("Window: %s, info: %s" % (self.window, info))
        else:
            info.minibuffer.focus()
            info.minibuffer.repeat(minibuffer)  # Include new minibuffer
        if not info.IsShown():
            info.Show()
            self.window._aui_manager.Update()
    
    def find_cancel_edit(self, control):
        while control is not None:
            if hasattr(control, "cancel_edit"):
                control.cancel_edit()
                return
            else:
                control = control.GetParent()
    
    def on_hide_minibuffer_or_cancel(self, event):
        try:
            info = self.window.minibuffer_pane_info
        except AttributeError:
            info = None
        if info is None or not info.IsShown():
            focused = self.window.control.FindFocus()
            self.find_cancel_edit(focused)
        else:
            info.Hide()
            self.window._aui_manager.Update()
    
    def change_minibuffer_editor(self, editor):
        """Inform the currently open minibuffer that the editor has changed
        so it can update its internal state to match
        """
        try:
            info = self.window.minibuffer_pane_info
        except AttributeError:
            return
        if info.minibuffer is not None:
            info.minibuffer.change_editor(editor)
    
    def destroy_minibuffer(self):
        try:
            info = self.window.minibuffer_pane_info
        except AttributeError:
            return
        self.window._aui_manager.DetachPane(info.minibuffer.control)
        info.minibuffer.destroy_control()

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _iter_schema_items(self, items):
        """Generator to pull all Actions out of the list of Schemas
        
        Schemas may contain other schemas, which requires this recursive
        approach.
        
        Usage:
            action_schemas = list(self.menu_bar.items)
            action_schemas.extend(self.tool_bars)
            for action in self._iter_schema_items(action_schemas):
                # do something
        """
        for item in items:
            if hasattr(item, 'items'):
                for a in self._iter_schema_items(item.items):
                    yield a
            else:
                yield item

    def _prompt_for_save(self):
        """ Prompts the user to save if necessary. Returns whether the dialog
            was cancelled.
        """
        dirty_editors = dict([(editor.name, editor)
                              for editor in self.editor_area.editors
                              if editor.dirty])
        if not dirty_editors.keys():
            return True
        message = 'You have unsaved files. Would you like to save them?'
        result = self.window.confirm(message=message, cancel=True,
                                    default=CANCEL, title='Save Changes?')
        if result == CANCEL:
            return False
        elif result == YES:
            for name, editor in dirty_editors.items():
                editor.save(editor.path)
        return True

    #### Trait change handlers ################################################

    @on_trait_change('window:closing')
    def _prompt_on_close(self, event):
        """ Prompt the user to save when exiting.
        """
        close = self._prompt_for_save()
        event.veto = not close

    @on_trait_change('editor_area:active_editor')
    def _active_editor_tab_change(self, event):
        """ Prompt the user to save when exiting.
        """
        active = self.active_editor
        if active is not None:
            self.window._title = "%s - %s %s" % (self.active_editor.name, self.about_title, self.about_version)
            # Can't call the following during the trait handler because the
            # trait handlers for the toolbar actions won't be completed yet.
            # When delayed until afterwards, the toolbar update works properly.
            wx.CallAfter(active.made_current_active_editor)
        else:
            self.window._title = "%s %s" % (self.about_title, self.about_version)

    #### Trait property getter/setters ########################################

    def _get_active_editor(self):
        if self.editor_area is not None:
            return self.editor_area.active_editor
        return None


    ###
    @classmethod
    def can_edit(cls, document):
        raise NotImplementedError
    
    @classmethod
    def get_match_score(cls, document):
        """Return a number based on how good of a match this task is to the
        incoming Document.
        
        0 = generic match
        ...
        10 = absolute match
        """
        return 0

    #### wx event handlers

    def on_tab_context_menu(self, evt):
        pass

    def on_tab_background_context_menu(self, evt):
        pass

    #### convenience functions
    
    def confirm(self, message, title=None, cancel=False, default=NO, no_label="", yes_label=""):
        """ Convenience method to show a confirmation dialog. """

        from pyface.confirmation_dialog import ConfirmationDialog

        if title is None:
            title = "Confirmation"

        dialog = ConfirmationDialog(parent=self.window.control, message=message, cancel=cancel, default=default, title=title, no_label=no_label, yes_label=yes_label)

        return dialog.open()

    def information(self, message, title='Information'):
        """ Convenience method to show an information message dialog. """

        from pyface.message_dialog import information

        return information(self.window.control, message, title)

    def warning(self, message, title='Warning'):
        """ Convenience method to show a warning message dialog. """

        from pyface.message_dialog import warning

        return warning(self.window.control, message, title)

    def error(self, message, title='Error'):
        """ Convenience method to show an error message dialog. """

        from pyface.message_dialog import error

        return error(self.window.control, message, title)
