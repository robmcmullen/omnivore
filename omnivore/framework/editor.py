import os

# Major package imports.
import numpy as np
from fs.opener import opener
import wx
import fs

# Enthought library imports.
from traits.api import on_trait_change, Any, Bool, Int, Unicode, Property, Dict, List, Str, Undefined, Instance
from pyface.api import YES, NO
from pyface.tasks.api import Editor
from pyface.action.api import ActionEvent

from omnivore import __version__
from omnivore.utils.command import HistoryList, StatusFlags
from omnivore.utils.file_guess import FileGuess
from omnivore.framework.document import DocumentError
from omnivore.framework.caret import CaretHandler
import omnivore.framework.clipboard as clipboard

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

    task_arguments = Str("")

    can_save = Bool(True)

    can_undo = Bool(False)  # has to be a property of Editor because EditorActions need to refer to this trait

    undo_label = Unicode("Undo")

    can_redo = Bool(False)

    redo_label = Unicode("Redo")

    printable = Bool(False)

    imageable = Bool(False)

    can_cut = Bool(False)

    can_copy = Bool(False)

    # can_paste is set by the idle handler of the FrameworkApplication for the
    # active window
    can_paste = Bool(False)

    caret_handler = Instance(CaretHandler)

    last_search_settings = Dict()

    mouse_mode_factory = Any

    baseline_present = Bool

    diff_highlight = Bool

    _metadata_dirty = Bool(transient=True)

    last_saved_uri = Str()

    last_loaded_uri = Str()

    #### trait default values

    def _document_default(self):
        return self.task.window.application.document_class()

    def _last_search_settings_default(self):
        return {
            "find": "",
            "replace": "",
            "match_case": False,
            "allow_inverse": False,
            "regex": False,
            "algorithm": "",
            }

    def _caret_handler_default(self):
        return CaretHandler()

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

    def load(self, source=None, **kwargs):
        """ Loads the contents of the editor.
        """
        log.debug("loading: %s" % source)
        if source is None:
            log.debug("loading a blank document")
            doc = self.task.window.application.document_class()
            self.init_blank_document(doc, **kwargs)
        elif hasattr(source, 'document_id'):
            log.debug("loading document: %s" % source)
            self.init_extra_metadata(source, **kwargs)
            self.view_document(source, **kwargs)
        else:
            log.debug("loading FileGuess object: %s" % source)
            doc = self.task.window.application.guess_document(source)
            self.init_extra_metadata(doc, **kwargs)
            self.view_document(doc, **kwargs)
        doc.read_only = doc.metadata.check_read_only()

    def init_blank_document(self, doc, **kwargs):
        pass

    def init_extra_metadata(self, doc, **kwargs):
        """ Hook to load any extra metadata for the given document
        """
        e = doc.get_metadata_for(self.task)
        self.from_metadata_dict(e)
        self.metadata_dirty = False

    def get_extra_metadata_header(self):
        return "# omnivore %s extra_metadata=v1\n" % __version__

    def from_metadata_dict(self, e):
        """ Set up additional object attributes from the dict argument
        """
        pass

    def to_metadata_dict(self, metadata_dict, document):
        """ Store any persistent object attributes in a dictionary that
        will be serialized and later loaded in from_metadata_dict
        """
        pass

    def load_baseline(self, uri, doc=None):
        if doc is None:
            doc = self.document
        try:
            doc.load_baseline(uri, confirm_callback=self.task.confirm)
        except DocumentError, e:
            self.window.error("Failed opening baseline document file\n\n%s\n\nError: %s" % (uri, str(e)), "Baseline Document Loading Error")
            return
        if doc == self.document:
            self.baseline_present = doc.has_baseline
            self.diff_highlight = self.baseline_present

    def use_self_as_baseline(self, doc=None):
        if doc is None:
            doc = self.document
        bytes = np.copy(doc.bytes)
        doc.init_baseline(doc.metadata, bytes)
        if doc == self.document:
            self.baseline_present = doc.has_baseline
            self.diff_highlight = self.baseline_present

    def view_document(self, doc, old_editor=None, **kwargs):
        """ Change the view to the specified document
        """
        doc.last_task_id = self.task.id
        self.document = self.task.window.application.add_document(doc)
        self.rebuild_document_properties()
        if old_editor is not None:
            self.copy_view_properties(old_editor)
        else:
            self.init_view_properties()
        self.rebuild_ui()
        self.document.undo_stack_changed = True
        self.task.document_changed = self.document

    def rebuild_document_properties(self):
        """ Recreate any editor attributes for the new document
        """
        self.baseline_present = self.document.has_baseline

    def init_view_properties(self):
        """ Set up editor properties when loading a new file
        """
        pass

    def copy_view_properties(self, old_editor):
        """ Copy editor properties to the new view
        """
        pass

    def process_preference_change(self, prefs):
        """ Update any values dependent on application preferences
        """
        pass

    def save(self, uri=None, saver=None, document=None):
        """ Saves a document.

        It can be used 3 ways:

        1) save the contents of the editor
        2) save the specified document using the save format of this editor.
        3) save a document using the specified save conversion routine
        """
        if document is None:
            document = self.document

            # only check validity if saving the current document
            if not self.is_valid_for_save():
                document.undo_stack_changed = True
                return

        if uri is None:
            uri = document.uri

        try:
            document.save_to_uri(uri, self, saver)
            document.undo_stack.set_save_point()

            # force an update to the document name as the URI may have changed
            document.uri = uri

            # force update: just got saved, can't be read only!
            document.read_only = False

            # Update tab name.  Note that dirty must be changed in order for
            # the trait to be updated, so force a change if needed.  Also,
            # update the URI first because trait callbacks happen immediately
            # and because properties are used for the editor name, no trait
            # event gets called on updating the metadata URI.
            if document == self.document:
                if not self.dirty:
                    self.dirty = True
                self.metadata_dirty = False

            document.undo_stack_changed = True
            saved = True
            self.last_saved_uri = uri

            # refresh window name in case filename has changed
            self.task._active_editor_tab_change(None)
        except Exception, e:
            import traceback
            stack = traceback.format_exc()
            log.error("%s:\n%s" % (uri, stack))
            self.window.error("Error trying to save:\n\n%s\n\n%s" % (uri, str(e)), "File Save Error")
            saved = False
        return saved

    def is_valid_for_save(self):
        """Hook for subclasses to implement a validity check before saving
        file
        """
        return True

    # Segment saver interface for menu item display
    export_data_name = "Any"
    export_extensions = [".*"]

    def encode_data(self, document, editor):
        """Document saver interface: take a document and produce a byte
        representation to save to disk.
        """
        data = document.bytes.tostring()
        return data

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
        name = self.clipboard_data_format
        try:
            serialized_data = self.copy_selection_to_clipboard(name)
            self.task.status_bar.message = "Copied %s" % serialized_data.summary
        except clipboard.ClipboardError as e:
            self.window.error(e.message, "Clipboard Error")

    @property
    def clipboard_data_format(self):
        return "text"

    def copy_selection_to_clipboard(self, name):
        return clipboard.set_from_selection(self, name)

    def paste(self, cmd_cls=None):
        """ Pastes the current clipboard at the current insertion point or over
        the current selection
        """
        try:
            serialized_data = self.get_paste_data_from_clipboard()
            self.process_paste_data(serialized_data, cmd_cls)
            self.task.status_bar.message = "Pasted %s" % serialized_data.summary
        except clipboard.ClipboardError as e:
            self.window.error(e.message, "Paste Error")

    def get_paste_data_from_clipboard(self):
        return clipboard.get_paste_data()

    def process_paste_data(self, serialized_data, cmd_cls=None):
        pass  # Override in subclass

    def select_all(self):
        pass  # Override in subclass

    def select_none(self):
        pass  # Override in subclass

    def select_invert(self):
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

    def save_as_image(self, path):
        """ Saves the contents of the editor in a maproom project file
        """
        valid = {
            '.png': wx.BITMAP_TYPE_PNG,
            '.tif': wx.BITMAP_TYPE_TIFF,
            '.tiff': wx.BITMAP_TYPE_TIFF,
            '.jpg': wx.BITMAP_TYPE_JPEG,
            '.jpeg': wx.BITMAP_TYPE_JPEG,
            }
        _, ext = os.path.splitext(path)
        if ext not in valid:
            path += ".png"
            t = wx.BITMAP_TYPE_PNG
        else:
            t = valid[ext]

        raw_data = self.get_numpy_image()
        h, w, depth = raw_data.shape
        image = wx.Image(w, h, raw_data)
        image.SaveFile(path, t)

    def get_numpy_image(self):
        """Get a numpy array in RGB format to be saved to a file
        """
        raise NotImplementedError

    def made_current_active_editor(self):
        pass

    def rebuild_ui(self):
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

    def popup_visible(self):
        """Hook for subclass to state whether a popup is being shown
        """
        return False

    def clear_popup(self):
        """Hook for subclass to remove the topmost popup
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
        log.debug("processing flags: %s" % str(flags))
        d = self.document
        visible_range = False

        self.caret_handler.process_caret_flags(flags, d)
        do_refresh = flags.refresh_needed

        if flags.message:
            self.task.status_bar.message = flags.message

        if flags.metadata_dirty:
            self.metadata_dirty = True

        if flags.data_model_changed:
            d.data_model_changed = True
            d.change_count += 1
            flags.rebuild_ui = True
        elif flags.byte_values_changed:
            d.byte_values_changed = flags.index_range
            d.change_count += 1
            do_refresh = True
        elif flags.byte_style_changed:
            d.byte_style_changed = flags.index_range
            d.change_count += 1
            flags.rebuild_ui = True
            do_refresh = True

        if flags.rebuild_ui:
            d.recalc_event = True
        if do_refresh:
            self.caret_handler.refresh_event = flags

    def popup_context_menu_from_commands(self, control, commands):
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
        ret = self.do_popup(control, popup)
        if ret is not None:
            cmd = context_menu_data[ret]
            self.process_command(cmd)

    def popup_context_menu_from_actions(self, control, actions, popup_data=None):
        """Popup a simple context menu with menu items defined by actions.
        
        Each entry is either None to indicate a separator, or an action to be
        used as the menu item.  Note that the action may be either an Action
        instance or the class of that Action.  If it is a class, a temporary
        instance of that class will be created.
        """
        popup = wx.Menu()
        context_menu_data = dict()

        def add_to_menu(menu, action, context_menu_data):
            i = wx.NewId()
            if not hasattr(action, 'task'):
                action = action(task=self.task)
                try:
                    action.on_popup_menu_update(self, popup_data)
                except AttributeError:
                    pass

            # wxpython popup entries can't have empty name
            name = action.name if action.name else " "
            item = menu.Append(i, name)
            item.Enable(action.enabled)
            context_menu_data[i] = action

        def loop_over_actions(popup, actions):
            for action in actions:
                if action is None:
                    popup.AppendSeparator()
                elif hasattr(action, '__iter__'):
                    submenu = wx.Menu()
                    title = action[0]
                    popup.Append(wx.NewId(), title, submenu)
                    loop_over_actions(submenu, action[1:])
                else:
                    add_to_menu(popup, action, context_menu_data)

        loop_over_actions(popup, actions)

        ret = self.do_popup(control, popup)
        if ret is not None:
            action = context_menu_data[ret]
            action_event = ActionEvent(task=self.task, popup_data=popup_data)
            action.perform(action_event)

    def do_popup(self, control, popup):
        ret = control.GetPopupMenuSelectionFromUser(popup)
        if ret == wx.ID_NONE:
            ret = None
        return ret


    #### Traits event handlers

    # Trait event handlers are used instead of calling these functions directly
    # because multiple views of the document might exist and all editors will
    # be informed of the update via the trait event on the document.

    @on_trait_change('document:undo_stack_changed')
    def undo_stack_changed(self):
        log.debug("undo_stack_changed called!!!")
        self.update_undo_redo()
        wx.CallAfter(self.refresh_toolbar_state)

    @on_trait_change('document:byte_values_changed')
    def byte_values_changed(self):
        log.debug("byte_values_changed called!!!")
        self.document.change_count += 1
        self.invalidate_search()
        self.compare_to_baseline()

    @on_trait_change('document:byte_style_changed')
    def byte_style_changed(self):
        log.debug("byte_style_changed called!!!")
        self.document.change_count += 1
        self.rebuild_display_objects()
        # styling can affect formatting, so rebuild display contents
        self.reconfigure_panes()

    #### wx hacks

    def refresh_toolbar_state(self):
        """The toolbar doesn't seem to refresh itself when its state is changed
        programmatically. This is provided as a convenience function to update
        any tools that are trait-dependent.
        """
        # Instead of calling AUI manager refresh (which was taking over 50% of
        # the refresh time) just refresh the toolbars themselves
        for pane in self.window._aui_manager._panes:
            if pane.IsToolbar():
                pane.window.Refresh()

    #### convenience functions

    @property
    def section_name(self):
        """If the document can be broken up into sections, this should return
        the title of the current section so it can be shown in the title bar of
        the window.
        """
        return ""

    @property
    def task(self):
        return self.editor_area.task

    @property
    def window(self):
        return self.editor_area.task.window

    @on_trait_change('editor_area.task.window.application.successfully_saved_event')
    def update_last_saved_uri(self, uri):
        if uri and uri is not Undefined:
            log.debug("updating last saved uri: %s" % uri)
            self.last_saved_uri = uri

    @property
    def most_recent_uri(self):
        if self.last_saved_uri:
            return self.last_saved_uri
        return self.document.uri

    @on_trait_change('editor_area.task.window.application.successfully_loaded_event')
    def update_last_loaded_uri(self, uri):
        if uri and uri is not Undefined:
            log.debug("updating last loaded uri: %s" % uri)
            self.last_loaded_uri = uri

    @property
    def best_file_save_dir(self):
        attempts = []
        if self.last_saved_uri:
            # try most recent first
            attempts.append(self.last_saved_uri)
        if self.last_loaded_uri:
            # try directory of last loaded file next
            attempts.append(self.last_loaded_uri)
        if self.document.uri:
            # path of current file is the final try
            attempts.append(self.document.uri)

        print("attempts for best_file_save_dir: %s" % str(attempts))
        dirpath = ""
        for uri in attempts:
            try:
                uri_dir = os.path.dirname(uri)
                fs_, relpath = fs.opener.opener.parse(uri_dir)
                if fs_.hassyspath(relpath):
                    dirpath = fs_.getsyspath(relpath)
                    break
            except fs.errors.FSError:
                pass

        return dirpath

    @property
    def status_message(self):
        return ""

    @status_message.setter
    def status_message(self, msg):
        self.task.status_bar.message = msg

    @property
    def debug_message(self):
        return ""

    @debug_message.setter
    def debug_message(self, msg):
        self.task.status_bar.debug = msg

    def editor_summary(self):
        lines = []
        lines.append("name: %s" % self.name)
        lines.append("document: %s" % self.document)
        lines.append("task_arguments: %s" % self.task_arguments)
        lines.append("flags: can_save: %s\n  can_undo: %s\n  can_redo: %s\n  can_cut: %s\n  can_copy: %s\n  can_paste: %s" % (self.can_save, self.can_undo, self.can_redo, self.can_cut, self.can_copy, self.can_paste))
        lines.append("last saved: %s" % self.last_saved_uri)
        lines.append("last loaded: %s" % self.last_loaded_uri)
        return "\n".join(lines)
