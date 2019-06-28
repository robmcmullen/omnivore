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
from . import filesystem


import logging
log = logging.getLogger(__name__)
sync_log = logging.getLogger("sync")
progress_log = logging.getLogger("progress")


class SawxFrame(wx.Frame):
    def __init__(self, editor, uri=None):
        wx.Frame.__init__(self, None , -1, uri or editor.title, size=wx.GetApp().last_window_size)

        self.create_icon()

        self.raw_menubar = wx.MenuBar()
        self.Bind(wx.EVT_MENU, self.on_menu)

        self.raw_toolbar = self.CreateToolBar(wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT)

        self.raw_statusbar = statusbar.RawStatusBar(self)

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

        if wx.Platform == "__WXMAC__":
            self.Bind(wx.EVT_MENU_OPEN, self.on_menu_open_mac)
        else:
            # Mac needs deferred SetMenuBar because that's where it moves the About
            # and Preferences to the Application menu. Other platforms set it
            # here and forget about it.
            self.SetMenuBar(self.raw_menubar)

            if wx.Platform == "__WXMSW__":
                self.Bind(wx.EVT_MENU_OPEN, self.on_menu_open_win)
            else:
                # EVT_MENU_OPEN fires every time the mouse moves to a different main
                # menu item, so this reduces it to only once: when the mouse
                # enters the menubar control itself. This doesn't seem to work on
                # other platforms, as they have native menubars which don't seem
                # to operate like regular wx.Window classes.
                self.raw_menubar.Bind(wx.EVT_ENTER_WINDOW, self.on_menu_open_linux)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = self.create_notebook()
        sizer.Add(self.notebook, 1, wx.GROW)
        self.SetSizer(sizer)

        self.active_editor = None
        self.active_editor_can_paste = False
        self.pending_editor_close = None
        if uri is not None:
            self.load_file(uri)
        else:
            self.add_editor(editor)

    @property
    def editors(self):
        for index in range(self.notebook.GetPageCount()):
            control = self.notebook.GetPage(index)
            yield control.editor

    @property
    def is_dirty(self):
        state = False
        for e in self.editors:
            state |= e.is_dirty
        return state

    def create_notebook(self):
        notebook = aui.AuiNotebook(self, -1)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_page_changed)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.on_page_closing)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSED, self.on_page_closed)
        return notebook

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
        if wx.Platform == "__WXMAC__":
            self.SetMenuBar(self.raw_menubar)

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
        # This function is called by a timer, so it's possible the frame has
        # been destroyed before the timer calls this. Checking for the truth
        # value of the wx object is supposed to fail if the C++ part has been
        # destroyed. We'll see how well it works. Otherwise, it will take a
        # try/except on RuntimeError
        log.debug("sync_active_tab: sync start")
        if self.notebook and self.notebook.GetPageCount() > 0:
            log.debug("sync_active_tab: sync_name")
            self.sync_name()
            log.debug("sync_active_tab: sync_toolbar")
            self.sync_toolbar()
            log.debug("sync_active_tab: sync_can_paste")
            self.sync_can_paste()
        log.debug("sync_active_tab: sync done")

    def add_editor(self, editor, args=None):
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
        editor.show(args)

    def add_document(self, document, current_editor=None, args=None):
        if current_editor is not None and current_editor.can_edit_document(document):
            editor_cls = current_editor.__class__
        else:
            editor_cls = editor_module.find_editor_class_for_document(document)
        new_editor = editor_cls(document)
        log.debug(f"load_file: Created editor {new_editor}")
        # have to add before load so the control exists
        self.add_editor(new_editor, args)
        return new_editor

    def close_editor(self, editor, remove=True, quit=False):
        control = editor.control
        if remove:
            index = self.find_index_of_editor(editor)
            self.notebook.RemovePage(index)
            control.Destroy()
        control.editor = None
        editor.control = None
        if not quit:
            wx.CallAfter(self.find_active_editor)
        del editor

    def load_file(self, path, current_editor=None, args=None, show_progress_bar=True):
        try:
            filesystem.filesystem_path(path)
        except FileNotFoundError:
            show_progress_bar = False
        if show_progress_bar:
            # usually True except when loading a file before the Frame is shown
            # (as in app startup). It uses Yield and can cause refresh events
            # to happen before the editor is finished loading.
            progress_log.info(f"START=Loading {path}...")
        try:
            file_metadata = loader.identify_file(path)
            log.debug(f"load_file: file_metadata={file_metadata}")
            if current_editor is not None and current_editor.can_load_file(file_metadata):
                current_editor.load_file(file_metadata)
                return
            document = identify_document(file_metadata)
            new_editor = self.add_document(document, current_editor, args)
        except Exception as e:
            # force close the progress bar so the error dialog doesn't get lost
            # under the progress bar dialog
            progress_log.info("END")
            import traceback
            traceback.print_exc()
            self.error(str(e))
        else:
            new_editor.load_success(document.uri)
            index = self.find_index_of_editor(new_editor)
            self.notebook.SetPageText(index, new_editor.tab_name)
        finally:
            if show_progress_bar:
                wx.CallAfter(progress_log.info, f"END")
        self.set_title()

    def make_active(self, editor, force=False, in_event_loop=False):
        last = self.active_editor
        self.active_editor = editor
        wx.GetApp().active_frame = self
        if force or last != editor or self.raw_menubar.GetMenuCount() == 0:
            if in_event_loop:
                wx.CallAfter(self.make_active_rebuild, editor)
            else:
                self.make_active_rebuild(editor)

    def make_active_rebuild(self, editor):
        log.debug(f"make_active_rebuild: for {editor}")
        try:
            index = self.find_index_of_control(editor.control)
        except errors.EditorNotFound:
            log.debug("attempt to rebuild removed editor; probably the result of a CallAfter")
        else:
            self.create_menubar()
            self.sync_menubar()
            self.create_toolbar()
            self.sync_toolbar()
            self.create_statusbar()
            self.sync_statusbar()
            self.create_keybindings()
            log.debug(f"setting tab focus to {index}")
            self.notebook.SetSelection(index)
            editor.control.SetFocus()
            self.sync_name()
            self.sync_can_paste()

    def enumerate_tabs(self):
        for index in range(self.notebook.GetPageCount()):
            control = self.notebook.GetPage(index)
            log.debug(f"index={index}, control={control}, editor={control.editor}")
            yield index, control, control.editor

    def close_all_tabs(self):
        editors = list(self.editors)
        for editor in editors:
            log.debug(f"Closing {editor}")
            self.close_editor(editor, quit=True)

    def find_index_of_editor(self, editor):
        return self.find_index_of_control(editor.control)

    def find_editor_from_control(self, control):
        for index in range(self.notebook.GetPageCount()):
            if control == self.notebook.GetPage(index):
                return control.editor
        raise errors.EditorNotFound

    def find_index_of_control(self, control):
        log.debug(f"find_index_of_control: looking for control={control}")
        for index in range(self.notebook.GetPageCount()):
            notebook_control = self.notebook.GetPage(index)
            log.debug(f"find_index_of_control: index={index}, control={notebook_control}")
            if control == notebook_control:
                return index
        raise errors.EditorNotFound

    def find_editor_from_index(self, index):
        control = self.notebook.GetPage(index)
        return self.find_editor_from_control(control)

    def find_active_editor(self):
        control = self.notebook.GetCurrentPage()
        editor = self.find_editor_from_control(control)
        self.make_active(editor, True)

    #### Event callbacks

    def on_menu_open_win(self, evt):
        # windows only works when updating the menu during the event call
        log.debug(f"on_menu_open_win: syncing menubar. From {evt.GetMenu()}")
        self.sync_menubar()
        evt.Skip()

    def on_menu_open_linux(self, evt):
        # workaround for linux which crashes updating the menu bar during an event
        log.debug(f"on_menu_open: syncing menubar.")
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
                log.warning("on_menu: No id {action_id} found in menubar or toolbar")
        if action is not None:
            log.debug(f"on_menu: action_key={action_key}, action={action}")
            try:
                wx.CallAfter(action.perform_as_menu_item, action_key)
            except AttributeError:
                log.debug(f"on_menu: no perform method for {action}")
        evt.Skip()

    def on_page_changed(self, evt):
        index = evt.GetSelection()
        editor = self.find_editor_from_index(index)

        # Can get stuck in a loop if the page changes while you're still in the
        # initial process of displaying the frame.
        still_booting = wx.GetApp().in_bootup_process
        log.debug(f"on_page_changed: page id: {index}, {editor.document.uri}, still_booting={still_booting}")
        self.make_active(editor, force=True, in_event_loop=not still_booting)
        evt.Skip()

    def on_page_closing(self, evt):
        index = evt.GetSelection()
        editor = self.find_editor_from_index(index)
        self.pending_editor_close = index, editor
        log.debug(f"on_page_changing: page id: {index}, {editor.document.uri}")
        editor.prepare_destroy()
        evt.Skip()

    def on_page_closed(self, evt):
        index, editor = self.pending_editor_close
        count = self.notebook.GetPageCount()
        if index >= count:
            index = count - 1
        log.debug(f"on_page_closed: new active page id: {index}")
        wx.CallAfter(self.close_editor, editor, remove=False)
        self.pending_editor_close = None
        evt.Skip()

    def on_activate(self, evt):
        wx.CallAfter(self.sync_active_tab)

    def on_char_hook(self, evt):
        key_id = (evt.GetModifiers(), evt.GetKeyCode())
        log.debug(f"on_char_hook: key: {key_id}")
        try:
            action_key, action = self.keybindings.valid_key_map[key_id]
            try:
                log.debug(f"found action {action}")
                action.perform_as_keystroke(action_key)
            except errors.ProcessKeystrokeNormally as e:
                log.debug(f"processing keystroke normally instead of action: {e}")
                evt.Skip()
        except KeyError as e:
            log.debug(f"key id {key_id} not found in {self.keybindings.valid_key_map}")
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

    def confirm(self, message, title="Confirm", cancel=False, yes_default=False, no_label=wx.ID_NO, yes_label=wx.ID_YES):
        """ Convenience method to show a confirmation dialog. """

        style = wx.ICON_INFORMATION | wx.YES_NO
        if cancel:
            style |= wx.CANCEL
        elif yes_default:
            style |= wx.YES_DEFAULT
        else:
            style |= wx.NO_DEFAULT
        dlg = wx.MessageDialog(self, message, title, style)
        dlg.SetYesNoLabels(yes_label, no_label)
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


class FakeNotebook(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.notebook_page = None
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

    def GetPageCount(self):
        return 1 if self.notebook_page is not None else 0

    def GetPage(self, index):
        return self.notebook_page

    def GetCurrentPage(self):
        return self.notebook_page

    def GetSelection(self):
        return 0

    def SetSelection(self, index):
        pass

    def SetPageText(self, index, title):
        pass

    def AddPage(self, control, name):
        if self.notebook_page is None:
            self.notebook_page = control
            self.GetSizer().Add(control, 1, wx.GROW)
        else:
            raise IndexError("Only one page allowed")

    def RemovePage(self, index):
        page = self.notebook_page
        self.notebook_page = None
        self.GetSizer().Clear()
        return page


class SawxSingleEditorFrame(SawxFrame):
    def create_notebook(self):
        notebook = FakeNotebook(self)
        return notebook
