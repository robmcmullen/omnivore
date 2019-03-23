import wx
import wx.adv
import wx.aui as aui
# import wx.lib.agw.aui as aui

from . import menubar
from . import toolbar
from . import statusbar
from . import keybindings
from . import errors
from . import editor as editor_module
from . import loader
from . import clipboard
from .ui import dialogs
from .document import identify_document
from .filesystem import fsopen as open


import logging
log = logging.getLogger(__name__)
sync_log = logging.getLogger("sync")


class SawxFrame(wx.Frame):
    def __init__(self, editor, uri=None):
        wx.Frame.__init__(self, None , -1, uri or editor.title, size=wx.GetApp().last_window_size)

        self.create_icon()

        self.raw_menubar = wx.MenuBar()
        self.SetMenuBar(self.raw_menubar)
        self.Bind(wx.EVT_MENU, self.on_menu)

        self.raw_toolbar = self.CreateToolBar(wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT)

        self.raw_statusbar = statusbar.RawStatusBar(self)

        self.toolbar_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

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
        self.active_editor_can_paste = False
        if uri is not None:
            self.load_file(uri)
        else:
            self.add_editor(editor)

    @property
    def editors(self):
        for index in range(self.notebook.GetPageCount()):
            control = self.notebook.GetPage(index)
            yield control.editor

    def create_icon(self):
        data = open(wx.GetApp().app_icon, 'rb')
        image = wx.Image(data)
        icon = wx.Icon()
        try:
            icon.CopyFromBitmap(wx.Bitmap(image))
            self.SetIcon(icon)
        except:
            log.error("AboutDialog: bad icon file: %s" % self.about_image)

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

    def rebuild_toolbar(self):
        self.create_toolbar()
        self.toolbar.sync_with_editor(self.raw_toolbar)

    def sync_toolbar(self):
        try:
            self.toolbar.sync_with_editor(self.raw_toolbar)
        except errors.RecreateDynamicMenuBar:
            self.create_toolbar()
            self.toolbar.sync_with_editor(self.raw_toolbar)

    def create_statusbar(self):
        log.debug(f"create_statusbar: active editor={self.active_editor}")
        self.statusbar = statusbar.StatusbarDescription(self, self.active_editor)
        self.SetStatusBar(self.raw_statusbar)

    def sync_statusbar(self):
        try:
            self.statusbar.sync_with_editor(self.raw_statusbar)
        except errors.RecreateDynamicMenuBar:
            self.create_statusbar()
            self.statusbar.sync_with_editor(self.raw_statusbar)

    def create_keybindings(self):
        log.debug(f"create_menubar: active editor={self.active_editor}")
        self.keybindings = keybindings.KeyBindingDescription(self.active_editor, self.menubar.valid_id_map)

    def set_title(self):
        app = wx.GetApp()
        title = f"{self.active_editor.title} - {app.app_name}"
        self.SetTitle(title)

    def sync_name(self):
        self.set_title()
        index = self.notebook.GetSelection()
        editor = self.find_editor_from_index(index)
        sync_log.debug(f"title={self.GetTitle()}, tab_name={editor.tab_name}")
        self.notebook.SetPageText(index, editor.tab_name)

    def sync_can_paste(self):
        """Check if the active editor can paste anything in the clipboard
        """
        self.active_editor_can_paste = clipboard.can_paste(self.active_editor.supported_clipboard_data)

    def sync_active_tab(self):
        self.sync_name()
        self.sync_toolbar()
        self.sync_can_paste()

    def add_editor(self, editor):
        editor.frame = self
        control = editor.create_control(self.notebook)
        editor.control = control
        control.editor = editor
        editor.create_event_bindings()
        editor.create_layout()
        if self.active_editor is not None and self.active_editor.is_transient:
            self.close_editor(self.active_editor)
        self.notebook.AddPage(control, editor.tab_name)
        self.make_active(editor)

    def close_editor(self, editor):
        index = self.find_index_of_editor(editor)
        control = editor.control
        control.editor = None
        editor.prepare_destroy()
        self.notebook.RemovePage(index)
        control.Destroy()
        editor.control = None
        del editor

    def load_file(self, path, current_editor=None, args=None):
        try:
            file_metadata = loader.identify_file(path)
            document = identify_document(file_metadata)
            if current_editor is not None and current_editor.can_edit_document(document):
                editor_cls = current_editor.__class__
            else:
                editor_cls = editor_module.find_editor_class_for_document(document)
            new_editor = editor_cls(document)
            # have to add before load so the control exists
            self.add_editor(new_editor)
            new_editor.show(args)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error(str(e))
        else:
            self.load_success(document)
            index = self.find_index_of_editor(new_editor)
            self.notebook.SetPageText(index, new_editor.tab_name)
        self.set_title()

    def load_success(self, document):
        from sawx.actions import open_recent
        open_recent.open_recent.append(document.uri)
        self.status_message(f"loaded {document.uri} {document}", True)

    def make_active(self, editor, force=False):
        last = self.active_editor
        self.active_editor = editor
        if force or last != editor or self.raw_menubar.GetMenuCount() == 0:
            self.create_menubar()
            self.sync_menubar()
            self.create_toolbar()
            self.sync_toolbar()
            self.create_statusbar()
            self.sync_statusbar()
            self.create_keybindings()
            index = self.find_index_of_control(editor.control)
            log.debug(f"setting tab focus to {index}")
            self.notebook.SetSelection(index)
            editor.control.SetFocus()
            self.sync_name()
            self.sync_can_paste()

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

    #### Event callbacks

    def on_menu_open_win(self, evt):
        # windows only works when updating the menu during the event call
        log.debug(f"on_menu_open_win: syncing menubar. From {evt.GetMenu()}")
        self.sync_menubar()
        evt.Skip()

    def on_menu_open_linux(self, evt):
        # workaround for linux which crashes updating the menu bar during an event
        log.debug(f"on_menu_open: syncing menubar. From {evt.GetMenu()}")
        wx.CallAfter(self.sync_menubar)
        evt.Skip()

    def on_menu_open_mac(self, evt):
        # workaround for Mac which sends the EVT_MENU_OPEN for lots of stuff unrelated to menus
        state = wx.GetMouseState()
        if state.LeftIsDown():
            log.debug(f"on_menu_open_mac: syncing menubar. From {evt.GetMenu()}")
            wx.CallAfter(self.sync_menubar)
        else:
            log.debug(f"on_menu_open_mac: skipping menubar sync because mouse isn't down. From {evt.GetMenu()}")
        evt.Skip()

    def on_menu(self, evt):
        action_id = evt.GetId()
        log.debug(f"on_menu: menu id: {action_id}")
        action = None
        try:
            action_key, action = self.menubar.valid_id_map[action_id]
        except KeyError:
            try:
                action_key, action = self.toolbar.valid_id_map[action_id]
            except KeyError:
                log.warning("No id {action_id} found in menubar or toolbar")
        if action is not None:
            log.debug(f"found action {action}")
            try:
                action.perform_as_menu_item(action_key)
            except AttributeError:
                log.debug(f"no perform method for {action}")
            else:
                log.debug(f"on_menu: found action_key={action_key}, action={action}")
        evt.Skip()

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
        self.close_editor(editor)
        evt.Skip()

    def on_timer(self, evt):
        evt.Skip()
        wx.CallAfter(self.sync_active_tab)

    def on_activate(self, evt):
        if evt.GetActive():
            log.debug("restarting toolbar timer")
            self.toolbar_timer.Start(wx.GetApp().clipboard_check_interval * 1000)
        else:
            log.debug("halting toolbar timer")
            self.toolbar_timer.Stop()
        wx.CallAfter(self.sync_active_tab)

    def on_char_hook(self, evt):
        key_id = (evt.GetModifiers(), evt.GetKeyCode())
        print(f"on_char_hook: key: {key_id}")
        try:
            action_key, action = self.keybindings.valid_key_map[key_id]
            try:
                print(f"found action {action}")
                action.perform_as_keystroke(action_key)
            except errors.ProcessKeystrokeNormally as e:
                print(f"processing keystroke normally instead of action: {e}")
                evt.Skip()
        except KeyError as e:
            print(f"key id {key_id} not found in {self.keybindings.valid_key_map}")
            evt.Skip()

    def on_size(self, evt):
        wx.GetApp().last_window_size = evt.GetSize()
        evt.Skip()


    #### convenience functions for alerts and dialogs

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

    def prompt(self, message, title='Prompt', default_value=""):
        """ Convenience method to show a text entry dialog."""
        d = dialogs.SimplePromptDialog(self, message, title, default_value)
        return d.show_and_get_value()

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
        return None if state == wx.ID_CANCEL else state == wx.ID_YES

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

    def status_message(self, message, debug=False):
        if debug:
            self.raw_statusbar.debug(message)
        else:
            self.raw_statusbar.message(message)
