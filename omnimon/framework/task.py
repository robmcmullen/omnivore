""" Text editor sample task

"""
import wx

# Enthought library imports.
from pyface.wx.aui import aui
from pyface.api import ImageResource, FileDialog, YES, OK, CANCEL
from pyface.action.api import StatusBarManager, Group, Separator
from pyface.tasks.api import Task, TaskWindow, TaskLayout, TaskWindowLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, TaskToggleGroup
from traits.api import provides, on_trait_change, Property, Instance, Bool, Str, Unicode, Int, Event
from apptools.preferences.api import PreferencesHelper

from omnimon.dock_panes import FileBrowserPane
from omnimon.framework.i_about import IAbout
from omnimon.framework.actions import *
from omnimon.framework.status_bar_manager import FrameworkStatusBarManager

import logging
log = logging.getLogger(__name__)

@provides(IAbout)
class FrameworkTask(Task):
    """ A simple task for opening a blank editor.
    """
    
    # Class properties (not traits!)
    
    new_file_text = ''

    #### Task interface #######################################################

    id = 'omnimon.framework.framework_task'
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
    
    #### 'IAbout' interface ###################################################
    
    about_title = Unicode('Omnimon')
    
    about_version = Unicode
    
    about_description = Unicode('Edit stuff.')
    
    about_website = Str('http://playermissile.com/omnimon')
    
    about_image = Instance(ImageResource, ImageResource('omnimon256'))
    
    #### 'IErrorReporter' interface ###########################################
    
    error_email_from = Str
    
    error_email_passwd = Str
    
    error_email_to = Str
    
    def _about_version_default(self):
        from omnimon import __version__
        return __version__
    
    ###########################################################################
    # 'Task' interface.
    ###########################################################################
    
    def _icon_default(self):
        return ImageResource('omnimon')

    def _menu_bar_default(self):
        menus = []
        self.add_menu(menus, "Menu", "File", "NewGroup", "OpenGroup", "SaveGroup", "RevertGroup", "PrintGroup", "ExitGroup")
        self.add_menu(menus, "Menu", "Edit", "UndoGroup", "CopyPasteGroup", "SelectGroup", "FindGroup", "PrefGroup")
        self.add_menu(menus, "Menu", "View", "ViewChangeGroup", "ViewConfigGroup", "ViewToggleGroup", "ViewDebugGroup", "TaskGroup")
        self.add_menu(menus, "Menu", "Documents", "DocumentGroup")
        self.add_menu(menus, "Menu", "Window", "NewTaskGroup", "WindowGroup")
        self.add_menu(menus, "Menu", "Help", "AboutGroup", "DocGroup", "BugReportGroup", "DebugGroup")
        
        return SMenuBar(*menus)

    def _tool_bars_default(self):
        return [ SToolBar(self.get_groups("ToolBar", "File", "NewGroup", "OpenGroup", "SaveGroup"),
                          Group(UndoAction(),
                                RedoAction(),
                                id="Undo"),
                          show_tool_names=False), ]

    def _status_bar_default(self):
        return FrameworkStatusBarManager(message="Hi!", debug_width=self.status_bar_debug_width)

    def _default_layout_default(self):
        return TaskLayout(
            left=VSplitter(
                PaneItem('omnimon.framework.file_browser_pane'),
                ))

    def activated(self):
        log.debug("  status bar: %s" % self.status_bar)
        active = self.active_editor
        if active:
            self.status_bar.message = active.name
        else:
            self.status_bar.message = self.name
        self.window.icon = self.icon

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
        else:
            editor.view_document(source.document)
        self.activated()

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
        if location == "Menu":
            if menu_name == "File":
                if group_name == "NewGroup":
                    return [
                        SMenu(NewFileGroup(), id="NewFileGroup", name="New"),
                        ]
                elif group_name == "OpenGroup":
                    return [
                        OpenAction(),
                        ]
                elif group_name == "SaveGroup":
                    return [
                        SaveAction(),
                        SaveAsAction(),
                        ]
                elif group_name == "RevertGroup":
                    return [
                        RevertAction(),
                        ]
                elif group_name == "PrintGroup":
                    return [
                        PageSetupAction(),
                        PrintPreviewAction(),
                        PrintAction(),
                        SaveAsPDFAction(),
                        ]
                elif group_name == "ExitGroup":
                    return [
                        ExitAction(),
                        ]
            elif menu_name == "Edit":
                if group_name == "UndoGroup":
                    return [
                        UndoAction(),
                        RedoAction(),
                        ]
                elif group_name == "CopyPasteGroup":
                    return [
                        CutAction(),
                        CopyAction(),
                        PasteAction(),
                        ]
                elif group_name == "SelectGroup":
                    return [
                        SelectAllAction(),
                        ]
                elif group_name == "PrefGroup":
                    return [
                        Group(PreferencesAction(), absolute_position="last"),
                        ]
            elif menu_name == "View":
                if group_name == "TaskGroup":
                    return [
                        DockPaneToggleGroup(),
                        TaskToggleGroup(),
                        ]
            elif menu_name == "Documents":
                if group_name == "DocumentGroup":
                    return [
                        DocumentSelectGroup(),
                        ]
            elif menu_name == "Window":
                if group_name == "NewTaskGroup":
                    return [
                        SMenu(
                            NewViewInGroup(id="a1", separator=True),
                            id='WindowTabGroupSubmenu2', separator=True, name="New View In..."),
                        ]
                if group_name == "WindowGroup":
                    return [
                        NewWindowAction(),
                        ]
            elif menu_name == "Help":
                if group_name == "AboutGroup":
                    return [
                        AboutAction()
                        ]
                elif group_name == "DebugGroup":
                    return [
                        SMenu(TaskAction(name='Dynamic Menu Names', method='debug',
                                         tooltip='Do some debug stuff',
                                         image=ImageResource('debug')),
                              WidgetInspectorAction(),
                              id="Debug", name="Debug"),
                        ]
        
        if location.startswith("Tool"):
            if menu_name == "File":
                if group_name == "NewGroup":
                    return [
                        TaskAction(method='new',
                                   tooltip='New file',
                                   image=ImageResource('file_new')),
                        ]
                elif group_name == "OpenGroup":
                    return [
                        OpenAction(),
                        ]
                elif group_name == "SaveGroup":
                    return [
                        SaveAction(),
                        SaveAsAction(),
                        ]
                
        return []

    def get_editor(self):
        raise NotImplementedError

    ###########################################################################
    # Minibuffer convenience routines
    ###########################################################################
    
    minibuffer_pane_name = "omnimon.framework.minibuffer"
    
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
        #info.CaptionVisible(False)  # hides the caption bar & close button
        info.minibuffer = None
        return info
    
    def show_minibuffer(self, minibuffer):
        # minibuffer_pane_info is stored in the TaskWindow instance because all
        # tasks use the same minibuffer pane in the AUI manager
        try:
            info = self.window.minibuffer_pane_info
        except AttributeError:
            info = self.create_minibuffer_info()
            self.window.minibuffer_pane_info = info
        if info.minibuffer is not None:
            info.minibuffer.destroy()
        info.minibuffer = minibuffer
        minibuffer.create_control(self.window.control)
#        panel = wx.Panel(self.window.control, -1, name="Minibuffer")
#        panel.SetSize((500, 40))
#        panel.SetBackgroundColour('blue')
        self.window._aui_manager.AddPane(minibuffer.control, info)
        log.debug("Window: %s, info: %s" % (self.window, info))
        info.Show()
        self.window._aui_manager.Update()
    
    def destroy_minibuffer(self):
        try:
            info = self.window.minibuffer_pane_info
        except AttributeError:
            return
        self.window._aui_manager.DetachPane(info.minibuffer.control)
        info.minibuffer.destroy()

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

    #### Trait property getter/setters ########################################

    def _get_active_editor(self):
        if self.editor_area is not None:
            return self.editor_area.active_editor
        return None


    ###
    @classmethod
    def can_edit(cls, mime):
        raise NotImplementedError
    
    @classmethod
    def get_match_score(cls, guess):
        """Return a number based on how good of a match this task is to the
        incoming FileGuess.
        
        0 = generic match
        ...
        10 = absolute match
        """
        return 0
