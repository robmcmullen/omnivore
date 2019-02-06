import wx
import wx.adv
import wx.aui as aui
# import wx.lib.agw.aui as aui

from . import menubar
from . import toolbar
from . import errors
from . import editor
from . import loader


import logging
log = logging.getLogger(__name__)


class OmnivoreFrame(wx.Frame):
    def __init__(self, editor):
        wx.Frame.__init__(self, None , -1, editor.title, size=wx.GetApp().last_window_size)

        self.raw_menubar = wx.MenuBar()
        self.SetMenuBar(self.raw_menubar)
        self.Bind(wx.EVT_MENU, self.on_menu)

        self.raw_toolbar = self.CreateToolBar(wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT)

        self.toolbar_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)

        if wx.Platform == "__WXMAC__":
            self.Bind(wx.EVT_MENU_OPEN, self.on_menu_open_mac)
        elif wx.Platform == "__WXMSW__":
            self.Bind(wx.EVT_MENU_OPEN, self.on_menu_open_win)
        else:
            self.Bind(wx.EVT_MENU_OPEN, self.on_menu_open_linux)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = aui.AuiNotebook(self, -1)
        sizer.Add(self.notebook, 1, wx.GROW)
        self.SetSizer(sizer)

        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_page_changed)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSED, self.on_page_closed)

        self.active_editor = None
        self.add_editor(editor)

    @property
    def editors(self):
        for index in range(self.notebook.GetPageCount()):
            control = self.notebook.GetPage(index)
            yield control.editor

    @property
    def is_dirty(self):
        for editor in self.editors:
            if editor.is_dirty:
                return True
        return False

    def create_menubar(self):
        log.debug(f"create_menubar: active editor={self.active_editor}")
        self.menubar = menubar.MenubarDescription(self, self.active_editor)

    def sync_menubar(self):
        try:
            self.menubar.sync_with_editor(self.raw_menubar)
        except errors.RecreateDynamicMenuBar:
            self.create_menubar()
            self.menubar.sync_with_editor(self.raw_menubar)

    def create_toolbar(self):
        log.debug(f"create_toolbar: active editor={self.active_editor}")
        self.toolbar = toolbar.ToolbarDescription(self, self.active_editor)
        self.raw_toolbar.Realize()

    def sync_toolbar(self):
        try:
            self.toolbar.sync_with_editor(self.raw_toolbar)
        except errors.RecreateDynamicMenuBar:
            self.create_toolbar()
            self.toolbar.sync_with_editor(self.raw_toolbar)

    def add_editor(self, editor):
        editor.frame = self
        control = editor.create_control(self.notebook)
        editor.control = control
        control.editor = editor
        self.notebook.AddPage(control, editor.tab_name)
        self.make_active(editor)

    def load_file(self, path, current_editor):
        try:
            mime_info = loader.identify_file(path)
            if current_editor.can_edit_mime(mime_info['mime']):
                new_editor = current_editor.__class__()
            else:
                new_editor = editor.find_editor_class_for_mime(mime_info['mime'])
            self.add_editor(new_editor)
            new_editor.load(path, mime_info)
            index = self.find_index_of_editor(new_editor)
            self.notebook.SetPageText(index, new_editor.tab_name)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error(str(e))

    def make_active(self, editor, force=False):
        last = self.active_editor
        self.active_editor = editor
        if force or last != editor or self.raw_menubar.GetMenuCount() == 0:
            self.create_menubar()
            self.sync_menubar()
            self.create_toolbar()
            self.sync_toolbar()
            index = self.find_index_of_control(editor.control)
            log.debug(f"setting tab focus to {index}")
            self.notebook.SetSelection(index)
            editor.control.SetFocus()

    def enumerate_tabs(self):
        for index in range(self.notebook.GetPageCount()):
            control = self.notebook.GetPage(index)
            yield index, control, control.editor

    def find_index_of_editor(self, editor):
        return self.find_index_of_control(editor.control)

    def find_editor_from_control(self, control):
        for index in range(self.notebook.GetPageCount()):
            if control == self.notebook.GetPage(index):
                return control.editor
        raise EditorNotFound

    def find_index_of_control(self, control):
        for index in range(self.notebook.GetPageCount()):
            if control == self.notebook.GetPage(index):
                return index
        raise EditorNotFound

    def find_editor_from_index(self, index):
        control = self.notebook.GetPage(index)
        return self.find_editor_from_control(control)

    def on_menu_open_win(self, evt):
        # windows only works when updating the menu during the event call
        log.debug(f"on_menu_open_win: syncing menubar. From {evt.GetMenu()}")
        self.sync_menubar()

    def on_menu_open_linux(self, evt):
        # workaround for linux which crashes updating the menu bar during an event
        log.debug(f"on_menu_open: syncing menubar. From {evt.GetMenu()}")
        wx.CallAfter(self.sync_menubar)

    def on_menu_open_mac(self, evt):
        # workaround for Mac which sends the EVT_MENU_OPEN for lots of stuff unrelated to menus
        state = wx.GetMouseState()
        if state.LeftIsDown():
            log.debug(f"on_menu_open_mac: syncing menubar. From {evt.GetMenu()}")
            wx.CallAfter(self.sync_menubar)
        else:
            log.debug(f"on_menu_open_mac: skipping menubar sync because mouse isn't down. From {evt.GetMenu()}")

    def on_menu(self, evt):
        action_id = evt.GetId()
        log.debug(f"on_menu: menu id: {action_id}")
        try:
            action_key, action = self.menubar.valid_id_map[action_id]
            try:
                wx.CallAfter(action.execute)
            except AttributeError:
                log.debug(f"no execute method for {action}")
        except KeyError as e:
            log.debug(f"menu id {action_id} not found: {e}")
        else:
            log.debug(f"found action {action}")

    def on_page_changed(self, evt):
        index = evt.GetSelection()
        editor = self.find_editor_from_index(index)
        log.debug(f"on_page_changed: page id: {index}, {editor}")
        self.make_active(editor, True)
        evt.Skip()

    def on_page_closed(self, evt):
        index = evt.GetSelection()
        log.debug(f"on_page_closed: page id: {index}")
        editor = self.find_editor_from_index(index)
        control = editor.control
        editor.prepare_destroy()
        self.notebook.RemovePage(index)
        del control
        evt.Skip()

    def on_timer(self, evt):
        evt.Skip()
        log.debug("timer")
        wx.CallAfter(self.sync_toolbar)

    def on_activate(self, evt):
        if evt.GetActive():
            log.debug("restarting toolbar timer")
            self.toolbar_timer.Start(wx.GetApp().clipboard_check_interval * 1000)
        else:
            log.debug("halting toolbar timer")
            self.toolbar_timer.Stop()
        wx.CallAfter(self.sync_toolbar)

    def prompt_local_file_dialog(self, title="", most_recent=True, save=False, default_filename="", wildcard="*"):
        """Display an "open file" dialog to load from the local filesystem,
        defaulting to the most recently used directory.

        If there is no previously used directory, default to the directory of
        the current file.

        Returns the directory path on the filesystem, or None if not found.
        """
        dirpath = ""
        if save:
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        else:
            style=wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW

        action = "save as" if save else "open"
        if not title:
            title = "Save File" if save else "Open File"
        if self.active_editor:
            # will try path of current file
            dirpath = self.active_editor.best_file_save_dir

        dlg = wx.FileDialog(self, message=title, defaultFile=default_filename, wildcard=wildcard, style=style)

        if dlg.ShowModal() == wx.ID_OK:
            return dlg.GetPath()
        return None

    def confirm(self, message, title="Confirm", cancel=False, yes_default=False):
        """ Convenience method to show a confirmation dialog. """

        style = wx.ICON_INFORMATION | wx.YES_NO
        if cancel:
            style |= wx.CANCEL
        elif yes_default:
            style |= wx.YES_DEFAULT
        else:
            style |= wx.NO_DEFAULT
        dlg = wx.MessageDialog(self, message, title, style)
        state = dlg.ShowModal()
        dlg.Destroy()
        return None if state == wx.CANCEL else state == wx.YES

    def confirm_cancel(self, message, title="Confirm"):
        """ Convenience method to show a confirmation dialog.

        Returns None if Cancel was chosen in addition to the usual True/False.
        """
        return self.confirm(message, title, cancel=True)

    def information(self, message, title='Information'):
        """ Convenience method to show an information message dialog. """

        current = self.FindFocus()
        dlg = wx.MessageDialog(current, message, title, wx.ICON_INFORMATION | wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def warning(self, message, title='Warning'):
        """ Convenience method to show a warning message dialog. """
        current = self.FindFocus()
        dlg = wx.MessageDialog(current, message, title, wx.ICON_WARNING | wx.OK)
        dlg.ShowModal()
        dlg.Destroy()


    def error(self, message, title='Error'):
        """ Convenience method to show an error message dialog. """
        current = self.FindFocus()
        dlg = wx.MessageDialog(current, message, title, wx.ICON_ERROR | wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
