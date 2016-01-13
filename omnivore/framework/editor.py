import os

# Major package imports.
from fs.opener import opener
import wx

# Enthought library imports.
from traits.api import on_trait_change, Any, Bool, Int, Unicode, Property, Dict
from pyface.tasks.api import Editor
from pyface.action.api import ActionEvent

from omnivore.utils.command import StatusFlags

from document import Document

import logging
log = logging.getLogger(__name__)


class FrameworkEditor(Editor):
    """The pyface editor template for the omnivore framework
    
    The abstract methods 
    """

    #### 'IProjectEditor' interface ############################################

    document = Any(None)
    
    name = Property(Bool, depends_on='document')

    tooltip = Property(Unicode, depends_on='document')
    
    can_undo = Bool(False)  # has to be a property of Editor because EditorActions need to refer to this trait
    
    undo_label = Unicode("Undo")
    
    can_redo = Bool(False)
    
    redo_label = Unicode("Redo")
    
    printable = Bool(False)
    
    can_cut = Bool(False)
    
    can_copy = Bool(False)
    
    # can_paste is set by the idle handler of the FrameworkApplication for the
    # active window
    can_paste = Bool(False)
    
    # Cursor index points to positions between bytes, so zero is before the
    # first byte and the max index is the number of bytes, which points to
    # after the last byte
    
    cursor_index = Int(0)
    
    # Anchor indexes behave like cursor positions: they indicate positions
    # between bytes
    anchor_start_index = Int(0)
    
    anchor_initial_start_index = Int(0)
    
    anchor_initial_end_index = Int(0)

    anchor_end_index = Int(0)
    
    last_search_settings = Dict()
    
    mouse_mode = Any

    #### trait default values

    def _document_default(self):
        return Document()
    
    def _last_search_settings_default(self):
        return {
            "find": "",
            "replace": "",
            "case_sensitive": False,
            "allow_inverse": False,
            "regex": False,
            }

    #### property getters

    def _get_name(self):
        return self.document.name

    def _get_tooltip(self):
        return self.document.metadata.uri

    ###########################################################################
    # 'FrameworkEditor' interface.
    ###########################################################################

    def create(self, parent):
        """ Creates the toolkit-specific control for the widget.
        """
        raise NotImplementedError

    def load(self, guess=None):
        """ Loads the contents of the editor.
        """
        if guess is None:
            doc = Document()
        else:
            metadata = guess.get_metadata()
            bytes = guess.get_utf8()
            doc = Document(metadata=metadata, bytes=bytes)
            self.init_user_segments(doc)
            self.view_document(doc)

    def init_user_segments(self, doc):
        """ Set up any pre-calculated segments based on the type or content of
        the just-loaded document.
        """
        pass

    def view_document(self, doc, old_editor=None):
        """ Change the view to the specified document
        """
        doc.last_task_id = self.task.id
        self.document = self.task.window.application.add_document(doc)
        self.rebuild_document_properties()
        if old_editor is not None:
            self.copy_view_properties(old_editor)
        self.update_panes()
        self.document.undo_stack_changed = True
        self.task.document_changed = self.document
    
    def rebuild_document_properties(self):
        """ Recreate any editor attributes for the new document
        """
        pass
    
    def copy_view_properties(self, old_editor):
        """ Copy editor properties to the new view
        """
        pass
    
    def document_length(self):
        return len(self.document)

    def save(self, uri=None):
        """ Saves the contents of the editor.
        """
        if uri is None:
            uri = self.document.uri

        try:
            # Have to use a two-step process to write to the file: open the
            # filesystem, then open the file.  Have to open the filesystem
            # as writeable in case this is a virtual filesystem (like ZipFS),
            # otherwise the write to the actual file will fail with a read-
            # only filesystem error.
            if uri.startswith("file://"):
                # FIXME: workaround to allow opening of file:// URLs with the
                # ! character
                uri = uri.replace("file://", "")
            fs, relpath = opener.parse(uri, writeable=True)
            fh = fs.open(relpath, 'wb')
            log.debug("saving to %s" % uri)
            fh.write(self.document.bytes.tostring())
            fh.close()
            fs.close()
            self.document.undo_stack.set_save_point()
            self.document.undo_stack_changed = True
        except Exception, e:
            log.error("%s: %s" % (uri, str(e)))
            self.window.error("Error trying to save:\n\n%s\n\n%s" % (uri, str(e)), "File Save Error")

    def undo(self):
        """ Undoes the last action
        """
        raise NotImplementedError

    def redo(self):
        """ Re-performs the last undone action
        """
        raise NotImplementedError

    def cut(self):
        """ Copies the current selection to the clipboard and removes the selection
        """
        raise NotImplementedError

    def copy(self):
        """ Copies the current selection to the clipboard
        """
        self.data_obj = self.create_clipboard_data_object()
        if self.data_obj is None:
            return
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(self.data_obj)
            wx.TheClipboard.Close()
        else:
            self.window.error("Unable to open clipboard", "Clipboard Error")

    def paste(self):
        """ Pastes the current clipboard at the current insertion point or over
        the current selection
        """
        data_obj = self.get_paste_data_object()
        if data_obj is not None:
            self.process_paste_data_object(data_obj)
        else:
            self.window.error("Unsupported data format", "Paste Error")
    
    def get_paste_data_object(self):
        data_objs = self.supported_clipboard_data_objects
        
        if wx.TheClipboard.Open():
            for data_obj in data_objs:
                success = wx.TheClipboard.GetData(data_obj)
                if success:
                    break
            wx.TheClipboard.Close()
        else:
            self.window.error("Unable to open clipboard", "Clipboard Error")
            success = False
        if success:
            return data_obj
        return None
    
    def process_paste_data_object(self, data_obj):
        pass  # Override in subclass
    
    # must be a class attribute because for checking clipboard data formats of
    # custom objects, data formats must be singletons
    supported_clipboard_data_objects = [wx.TextDataObject()]
    
    def create_clipboard_data_object(self):
        return wx.TextDataObject("Omnivore!")
    
    def print_preview(self):
        raise NotImplementedError
    
    def print_page(self):
        raise NotImplementedError
    
    def save_as_pdf(self, path=None):
        raise NotImplementedError
    
    def update_history(self):
        """Hook to update any undo history list and/or save history log to a file
        """
        pass

    def update_panes(self):
        """Called when each pane should be rebuilt from the (possibly new)
        document, or when the document formatting or structure has changed.
        """
        pass
    
    def refresh_panes(self):
        """Called when the panes should be repainted.
        
        Typically this is called when the contents of the document have changed
        but the document formatting or structure hasn't changed.
        """
        pass
    
    def reconfigure_panes(self):
        """Called when the panes should be updated after a possible document
        formatting or structure change.
        """
        pass
    
    def ensure_visible(self, start, end):
        """Make sure the current range of indexes is shown
        """
        pass

    def select_all(self, refresh=True):
        """ Selects the entire document
        """
        self.anchor_start_index = self.anchor_initial_start_index = 0
        self.anchor_end_index = self.anchor_initial_end_index = len(self.document)
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
        if refresh:
            self.refresh_panes()

    def select_none(self, refresh=True):
        """ Clears any selection in the document
        """
        self.anchor_start_index = self.anchor_initial_start_index = self.anchor_end_index = self.anchor_initial_end_index = self.cursor_index
        self.can_copy = False
        if refresh:
            self.refresh_panes()
    
    def set_cursor(self, index, refresh=True):
        max_index = self.document_length()
        if index < 0:
            index = 0
        elif index > max_index:
            index = max_index
        self.cursor_index = index
        self.anchor_start_index = self.anchor_initial_start_index = index
        self.anchor_end_index = self.anchor_initial_end_index = index
        self.can_copy = False
        if refresh:
            self.refresh_panes()
        
        return index
    
    def invalidate_search(self):
        """Hook for subclasses to get notified if the document is changed and
        any search params should be cleared."""
        pass
    
    # Command processor

    def update_undo_redo(self):
        command = self.document.undo_stack.get_undo_command()
        if command is None:
            self.undo_label = "Undo"
            self.can_undo = False
        else:
            text = str(command).replace("&", "&&")
            self.undo_label = "Undo: %s" % text
            self.can_undo = True
            
        command = self.document.undo_stack.get_redo_command()
        if command is None:
            self.redo_label = "Redo"
            self.can_redo = False
        else:
            text = str(command).replace("&", "&&")
            self.redo_label = "Redo: %s" % text
            self.can_redo = True
        self.dirty = self.document.undo_stack.is_dirty()
    
    def undo(self):
        undo = self.document.undo_stack.undo(self)
        self.process_flags(undo.flags)
        self.document.undo_stack_changed = True
    
    def redo(self):
        undo = self.document.undo_stack.redo(self)
        self.process_flags(undo.flags)
        self.document.undo_stack_changed = True
    
    def process_command(self, command):
        """Process a single command and immediately update the UI to reflect
        the results of the command.
        """
        f = StatusFlags()
        undo = self.process_batch_command(command, f)
        if undo.flags.success:
            self.process_flags(f)
            self.document.undo_stack_changed = True
        return undo
        
    def process_batch_command(self, command, f):
        """Process a single command but don't update the UI immediately.
        Instead, update the batch flags to reflect the changes needed to
        the UI.
        
        """
        undo = self.document.undo_stack.perform(command, self)
        f.add_flags(undo.flags, command)
        return undo
    
    def process_flags(self, flags):
        """Perform the UI updates given the StatusFlags or BatchFlags flags
        
        """
        d = self.document
        visible_range = False
        
        if flags.cursor_index is not None:
            self.cursor_index = self.anchor_start_index = self.anchor_initial_start_index = self.anchor_end_index = self.anchor_initial_end_index = flags.cursor_index
            visible_range = True
            
        if flags.index_range is not None:
            if flags.select_range:
                self.anchor_start_index = self.anchor_initial_start_index = flags.index_range[0]
                self.anchor_end_index = self.anchor_initial_end_index = flags.index_range[1]
                d.change_count += 1
            visible_range = True
        
        if flags.message:
            self.task.status_bar.message = flags.message
        
        if flags.byte_values_changed:
            d.byte_values_changed = True  # also handles refresh
        elif flags.refresh_needed:
            self.refresh_panes()
        
        if visible_range:
            # Only update the range on the current editor, not other views which
            # are allowed to remain where they are
            self.ensure_visible(self.anchor_start_index, self.anchor_end_index)
            
    def popup_context_menu_from_commands(self, window, commands):
        """Popup a simple context menu with menu items defined by commands.
        
        Each entry is either None to indicate a separator, or a 2-tuple
        containing the string name and the command instance to process if the
        menu entry is selected.
        """
        popup = wx.Menu()
        context_menu_data = dict()
        for entry in commands:
            if entry is None:
                popup.AppendSeparator()
            else:
                name, cmd = entry
                i = wx.NewId()
                popup.Append(i, name)
                context_menu_data[i] = cmd
        ret = window.GetPopupMenuSelectionFromUser(popup)
        if ret == wx.ID_NONE:
            return
        cmd = context_menu_data[ret]
        self.process_command(cmd)
        
    def popup_context_menu_from_actions(self, window, actions):
        """Popup a simple context menu with menu items defined by actions.
        
        Each entry is either None to indicate a separator, or an action to be
        used as the menu item.  Note that the action may be either an Action
        instance or the class of that Action.  If it is a class, a temporary
        instance of that class will be created.
        """
        popup = wx.Menu()
        context_menu_data = dict()
        for action in actions:
            if action is None:
                popup.AppendSeparator()
            else:
                i = wx.NewId()
                if not hasattr(action, 'task'):
                    action = action(task=self.task)
                item = popup.Append(i, action.name)
                item.Enable(action.enabled)
                context_menu_data[i] = action
        ret = window.GetPopupMenuSelectionFromUser(popup)
        if ret == wx.ID_NONE:
            return
        action = context_menu_data[ret]
        action_event = ActionEvent(task=self.task)
        action.perform(action_event)
    
    #### Traits event handlers
    
    # Trait event handlers are used instead of calling these functions directly
    # because multiple views of the document might exist and all editors will
    # be informed of the update via the trait event on the document.
    
    @on_trait_change('document:undo_stack_changed')
    def undo_stack_changed(self):
        log.debug("undo_stack_changed called!!!")
        self.update_undo_redo()
        self.update_history()
    
    @on_trait_change('document:byte_values_changed')
    def byte_values_changed(self):
        log.debug("byte_values_changed called!!!")
        self.invalidate_search()
        self.reconfigure_panes()

    #### convenience functions
    
    @property
    def task(self):
        return self.editor_area.task
    
    @property
    def window(self):
        return self.editor_area.task.window

    @property
    def most_recent_path(self):
        return os.path.dirname(self.document.uri)
