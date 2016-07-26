import os

# Major package imports.
import numpy as np
from fs.opener import opener
import wx
import fs
import jsonpickle

# Enthought library imports.
from traits.api import on_trait_change, Any, Bool, Int, Unicode, Property, Dict, List
from pyface.api import YES, NO
from pyface.tasks.api import Editor
from pyface.action.api import ActionEvent

from omnivore import __version__
from omnivore.utils.command import HistoryList, StatusFlags
from omnivore.utils.sortutil import collapse_overlapping_ranges, invert_ranges, ranges_to_indexes
from omnivore.utils.file_guess import FileGuess
import omnivore.utils.jsonutil as jsonutil

from document import Document

import logging
log = logging.getLogger(__name__)


class FrameworkEditor(Editor):
    """The pyface editor template for the omnivore framework
    
    The abstract methods 
    """

    #### 'IProjectEditor' interface ############################################

    document = Any(None)
    
    name = Property(Unicode, depends_on='document')

    tooltip = Property(Unicode, depends_on='document')

    can_save = Bool(True)
    
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

    cursor_history = Any
    
    # Anchor indexes behave like cursor positions: they indicate positions
    # between bytes
    anchor_start_index = Int(0)
    
    anchor_initial_start_index = Int(0)
    
    anchor_initial_end_index = Int(0)

    anchor_end_index = Int(0)
    
    selected_ranges = List([])
    
    last_search_settings = Dict()
    
    mouse_mode_factory = Any
    
    baseline_present = Bool
    
    diff_highlight = Bool
    
    _metadata_dirty = Bool(transient=True)

    #### trait default values

    def _document_default(self):
        return Document()

    def _cursor_history_default(self):
        return HistoryList()
    
    def _last_search_settings_default(self):
        return {
            "find": "",
            "replace": "",
            "case_sensitive": False,
            "allow_inverse": False,
            "regex": False,
            "algorithm": "",
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

    def load(self, source=None):
        """ Loads the contents of the editor.
        """
        if source is None:
            doc = Document()
        elif hasattr(source, 'document_id'):
            self.view_document(source)
        else:
            metadata = source.get_metadata()
            bytes = source.get_utf8()
            doc = Document(metadata=metadata, bytes=bytes)
            self.init_extra_metadata(doc)
            self.view_document(doc)

    def init_extra_metadata(self, doc):
        """ Hook to load any extra metadata for the given document
        """
        e = self.load_builtin_extra_metadata(doc)
        if e is not None:
            self.process_extra_metadata(doc, e)
        e = self.load_filesystem_extra_metadata(doc)
        if e is not None:
            self.process_extra_metadata(doc, e)
        self.metadata_dirty = False

    def load_builtin_extra_metadata(self, doc):
        """ Find any extra metadata associated with the document that is built-
        in to the application.
        """
        pass

    def load_filesystem_extra_metadata(self, doc):
        """ Find any extra metadata associated with the document, typically
        used to load an extra file off the disk.
        
        If successful, return a dict to be processed by init_extra_metadata
        """
        uri = self.get_filesystem_extra_metadata_uri(doc)
        if uri is None:
            return
        try:
            guess = FileGuess(uri)
        except fs.errors.FSError, e:
            log.error("File load error: %s" % str(e))
            return
        try:
            b = guess.bytes
            if b.startswith("#"):
                header, b = b.split("\n", 1)
            unserialized = jsonpickle.loads(b)
        except ValueError, e:
            log.error("JSON parsing error for extra metadata in %s: %s" % (uri, str(e)))
            unserialized = None
        return unserialized
    
    def get_filesystem_extra_metadata_uri(self, doc):
        """ Get filename of file used to store extra metadata
        """
        pass

    def process_extra_metadata(self, doc, e):
        """ Set up any additional metadata from the dict argument
        """
        pass
    
    def load_baseline(self, uri, doc=None):
        if doc is None:
            doc = self.document
        try:
            guess = FileGuess(uri)
        except Exception, e:
            self.window.error("Failed opening baseline document file\n\n%s\n\nError: %s" % (uri, str(e)), "Baseline Document Loading Error")
            return
        bytes = guess.numpy
        difference = len(bytes) - len(doc)
        if difference > 0:
            if self.task.confirm("Truncate baseline data by %d bytes?" % difference, "Baseline Size Difference") == YES:
                bytes = bytes[0:len(doc)]
            else:
                bytes = []
        elif difference < 0:
            if self.task.confirm("Pad baseline data with %d zeros?" % (-difference), "Baseline Size Difference") == YES:
                bytes = np.pad(bytes, (0, -difference), "constant", constant_values=0)
            else:
                bytes = []
        if len(bytes) > 0:
            doc.init_baseline(guess.metadata, bytes)
        else:
            doc.del_baseline()
        if doc == self.document:
            self.baseline_present = doc.has_baseline
            self.diff_highlight = self.baseline_present

    def view_document(self, doc, old_editor=None):
        """ Change the view to the specified document
        """
        doc.last_task_id = self.task.id
        self.document = self.task.window.application.add_document(doc)
        self.rebuild_document_properties()
        if old_editor is not None:
            self.copy_view_properties(old_editor)
        else:
            self.init_view_properties()
        self.update_panes()
        self.document.undo_stack_changed = True
        self.task.document_changed = self.document
    
    def rebuild_document_properties(self):
        """ Recreate any editor attributes for the new document
        """
        self.baseline_present = self.document.has_baseline
        self.diff_highlight = self.diff_highlight and self.baseline_present
    
    def init_view_properties(self):
        """ Set up editor properties when loading a new file
        """
        pass

    def copy_view_properties(self, old_editor):
        """ Copy editor properties to the new view
        """
        pass
    
    @property
    def document_length(self):
        return len(self.document)

    def save(self, uri=None, saver=None):
        """ Saves the contents of the editor.
        """
        if uri is None:
            uri = self.document.uri

        try:
            if saver is None:
                bytes = self.document.bytes.tostring()
            else:
                bytes = saver(self.document)
            self.save_to_uri(bytes, uri)
            self.document.undo_stack.set_save_point()

            # force an update to the document name as the URI may have changed
            self.document.uri = uri

            # force update: just got saved, can't be read only!
            self.document.read_only = False

            self.document.undo_stack_changed = True
            saved = True
        except Exception, e:
            import traceback
            stack = traceback.format_exc()
            log.error("%s:\n%s" % (uri, stack))
            self.window.error("Error trying to save:\n\n%s\n\n%s" % (uri, str(e)), "File Save Error")
            saved = False
        return saved
    
    def save_to_uri(self, bytes, uri, save_metadata=True):
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
        fh.write(bytes)
        fh.close()
        
        if save_metadata:
            metadata_dict = dict()
            self.get_extra_metadata(metadata_dict)
            if metadata_dict:
                relpath += ".omnivore"
                log.debug("saving extra metadata to %s" % relpath)
                jsonpickle.set_encoder_options("json", sort_keys=True, indent=4)
                bytes = jsonpickle.dumps(metadata_dict)
                text = jsonutil.collapse_json(bytes)
                header = self.get_extra_metadata_header()
                fh = fs.open(relpath, 'wb')
                fh.write(header)
                fh.write(text)
                fh.close()
                self.metadata_dirty = False
        
        fs.close()
    
    # Segment saver interface for menu item display
    export_data_name = "Any"
    export_extensions = [".*"]
    
    def encode_data(self, document):
        """Document saver interface: take a document and produce a byte
        representation to save to disk.
        """
        data = document.bytes.tostring()
        return data
    
    def get_extra_metadata_header(self):
        return "# omnivore %s extra_metadata=v1\n" % __version__
    
    def get_extra_metadata(self, metadata_dict):
        pass
    
    @property
    def metadata_dirty(self):
        return self._metadata_dirty
    
    @metadata_dirty.setter
    def metadata_dirty(self, val):
        self._metadata_dirty = bool(val)
        self.dirty = self.document.dirty or self._metadata_dirty
        self.can_save = not self.document.read_only and self.dirty

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
        data_obj = self.create_clipboard_data_object()
        if data_obj is None:
            return False
        return self.set_clipboard_object(data_obj)
    
    def set_clipboard_object(self, data_obj):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(data_obj)
            wx.TheClipboard.Close()
            return True
        else:
            self.window.error("Unable to open clipboard", "Clipboard Error")
            return False

    def paste(self, cmd_cls=None):
        """ Pastes the current clipboard at the current insertion point or over
        the current selection
        """
        data_obj = self.get_paste_data_object()
        if data_obj is not None:
            self.process_paste_data_object(data_obj, cmd_cls)
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
    
    def process_paste_data_object(self, data_obj, cmd_cls=None):
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

    def made_current_active_editor(self):
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
        self.anchor_end_index = self.anchor_initial_end_index = self.document_length
        self.selected_ranges = [(self.anchor_start_index, self.anchor_end_index)]
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
        self.highlight_selected_ranges()
        if refresh:
            self.refresh_panes()

    def select_none(self, refresh=True):
        """ Clears any selection in the document
        """
        self.anchor_start_index = self.anchor_initial_start_index = self.anchor_end_index = self.anchor_initial_end_index = self.cursor_index
        self.can_copy = False
        self.selected_ranges = []
        self.highlight_selected_ranges()
        if refresh:
            self.refresh_panes()

    def select_invert(self, refresh=True):
        """ Selects the entire document
        """
        self.selected_ranges = self.invert_selection_ranges(self.selected_ranges)
        try:
            start, end = self.selected_ranges[-1]
        except IndexError:
            start, end = 0, 0
        self.anchor_start_index = self.anchor_initial_start_index = start
        self.anchor_end_index = self.anchor_initial_end_index = end
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
        self.highlight_selected_ranges()
        if refresh:
            self.refresh_panes()
    
    def select_range(self, start, end, add=False, extend=False):
        """ Adjust the current selection to the new start and end indexes
        """
        if extend:
            self.selected_ranges[-1] = (start, end)
        elif add:
            self.selected_ranges.append((start, end))
        else:
            self.selected_ranges = [(start, end)]
        self.anchor_start_index = start
        self.anchor_end_index = end
        self.highlight_selected_ranges()
    
    def highlight_selected_ranges(self):
        pass
    
    def get_optimized_selected_ranges(self):
        """ Get the list of monotonically increasing, non-overlapping selected
        ranges
        """
        return collapse_overlapping_ranges(self.selected_ranges)
    
    def get_selected_ranges_and_indexes(self):
        opt = self.get_optimized_selected_ranges()
        return opt, ranges_to_indexes(opt)
    
    def invert_selection_ranges(self, ranges):
        return invert_ranges(ranges, self.document_length)
    
    def set_cursor(self, index, refresh=True):
        max_index = self.document_length - 1
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

    def update_cursor_history(self):
        state = self.get_cursor_state()
        last = self.cursor_history.get_undo_command()
        if last is None or last != state:
            cmd = self.cursor_history.get_redo_command()
            if cmd is None or cmd != state:
                self.cursor_history.add_command(state)

    def get_cursor_state(self):
        return self.cursor_index

    def undo_cursor_history(self):
        if not self.cursor_history.can_redo():
            # at the end of the history list, the last item will be the current position, so skip it
            _ = self.cursor_history.prev_command()
        cmd = self.cursor_history.prev_command()
        if cmd is None:
            return
        self.restore_cursor_state(cmd)

    def redo_cursor_history(self):
        if not self.cursor_history.can_undo():
            # at the start of the history list, the last item will be the current position, so skip it
            _ = self.cursor_history.next_command()
        cmd = self.cursor_history.next_command()
        if cmd is None:
            return
        self.restore_cursor_state(cmd)

    def restore_cursor_state(self, state):
        self.set_cursor(state)

    def mark_index_range_changed(self, index_range):
        """Hook for subclasses to be informed when bytes within the specified
        index range have changed.
        """
        pass
    
    def rebuild_display_objects(self):
        """Hook for subclasses to get notified when the document is changed and
        to rebuild any objects necessary for display before the call to
        refresh_panes."""
        pass
    
    def invalidate_search(self):
        """Hook for subclasses to get notified if the document is changed and
        any search params should be cleared."""
        pass
    
    def compare_to_baseline(self):
        """Hook for subclasses to update any comparisons to the baseline data."""
        pass
    
    def update_mouse_mode(self, mouse_handler=None):
        """Hook for subclasses to process the change to a new mouse mode 
        """
        pass
    
    def perform_idle(self):
        """Hook for subclasses to do some (small!) processing during UI idle
        time.
        """
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
        self.dirty = self.document.dirty or self._metadata_dirty
        self.can_save = not self.document.read_only and self.dirty
    
    def undo(self):
        undo = self.document.undo_stack.undo(self)
        self.process_flags(undo.flags)
        self.document.undo_stack_changed = True
        self.undo_post_hook()

    def undo_post_hook(self):
        pass
    
    def redo(self):
        undo = self.document.undo_stack.redo(self)
        self.process_flags(undo.flags)
        self.document.undo_stack_changed = True
        self.redo_post_hook()

    def redo_post_hook(self):
        pass
    
    def end_batch(self):
        self.document.undo_stack.end_batch()
        self.document.undo_stack_changed = True
    
    def process_command(self, command, batch=None):
        """Process a single command and immediately update the UI to reflect
        the results of the command.
        """
        f = StatusFlags()
        undo = self.process_batch_command(command, f, batch)
        if undo.flags.success:
            self.process_flags(f)
            self.document.undo_stack_changed = True
        self.refresh_toolbar_state()
        return undo
        
    def process_batch_command(self, command, f, batch=None):
        """Process a single command but don't update the UI immediately.
        Instead, update the batch flags to reflect the changes needed to
        the UI.
        
        """
        undo = self.document.undo_stack.perform(command, self, batch)
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
            self.mark_index_range_changed(flags.index_range)
        
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
        
    def popup_context_menu_from_actions(self, window, actions, popup_data=None):
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
                
                # wxpython popup entries can't have empty name
                name = action.name if action.name else " "
                item = popup.Append(i, name)
                item.Enable(action.enabled)
                context_menu_data[i] = action
        ret = window.GetPopupMenuSelectionFromUser(popup)
        if ret == wx.ID_NONE:
            return
        action = context_menu_data[ret]
        action_event = ActionEvent(task=self.task, popup_data=popup_data)
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
        wx.CallAfter(self.refresh_toolbar_state)
    
    @on_trait_change('document:byte_values_changed')
    def byte_values_changed(self):
        log.debug("byte_values_changed called!!!")
        self.document.change_count += 1
        self.invalidate_search()
        self.compare_to_baseline()
        self.rebuild_display_objects()
        self.refresh_panes()

    #### wx hacks

    def refresh_toolbar_state(self):
        """The toolbar doesn't seem to refresh itself when its state is changed
        programmatically. This is provided as a convenience function to update
        any tools that are trait-dependent.
        """
        #for toolbar in self.window.tool_bar_managers:
        #    name = toolbar.id
        #    info = self.window._aui_manager.GetPane(name)
        #    tool_bar = info.window
        #    tool_bar.Refresh(False)
        self.window._aui_manager.Update()

    #### convenience functions
    
    @property
    def task(self):
        return self.editor_area.task
    
    @property
    def window(self):
        return self.editor_area.task.window

    @property
    def most_recent_uri(self):
        return self.document.uri
