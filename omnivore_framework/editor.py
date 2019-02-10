import os
import sys
import inspect
import pkg_resources

import wx

from . import action
from . import errors

import logging
log = logging.getLogger(__name__)


def get_editors():
    editors = []
    for entry_point in pkg_resources.iter_entry_points('omnivore_framework.editors'):
        mod = entry_point.load()
        log.debug(f"get_edtiors: Found module {entry_point.name}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and OmnivoreEditor in obj.__mro__[1:]:
                # only use subclasses of OmnivoreEditor, not the
                # OmnivoreEditor base class itself
                log.debug(f"get_editors: Found editor class {name}")
                editors.append(obj)
    return editors


def find_editor_class_for_mime(mime_type):
    """Find the "best" editor for a given MIME type string.

    First attempts all editors with exact matches for the MIME string,
    and if no exact matches are found, returns through the list to find
    one that can edit that class of MIME.
    """
    editors = get_editors()
    log.debug(f"finding editors using {editors}")
    for editor in editors:
        if editor.can_edit_mime_exact(mime_type):
            return editor
    for editor in editors:
        if editor.can_edit_mime_generic(mime_type):
            return editor
    raise errors.UnsupportedFileType(f"No editor available for {mime_type}")

def find_editor_class_by_name(name):
    """Find the editor class given its class name

    Returns the OmnivoreEditor subclass whose `name` class attribute matches
    the given string.
    """
    editors = get_editors()
    log.debug(f"finding editors using {editors}")
    for editor in editors:
        if editor.name == name:
            return editor
        if name in editor.compatibility_names:
            return editor
    raise errors.EditorNotFound(f"No editor named {name}")


class OmnivoreEditor:
    name = "omnivore_framework_base_editor"
    pretty_name = "Omnivore Framework Base Editor"

    # list of alternate names for this editor, for compatibility with task_ids
    # from Omnivore 1.0
    compatibility_names = []

    menubar_desc = [
    ["File", "new_file", "open_file", ["Open Recent", "open_recent"], None, "save_file", "save_as", None, "quit"],
    ["Edit", "undo", "redo", None, "copy", "cut", "paste", None, "prefs"],
    ["Help", "about"],
    ]

    toolbar_desc = [
        "new_file", "open_file", "save_file", None, "undo", "redo", None, "copy", "cut", "paste"
    ]

    module_search_order = ["omnivore_framework.actions"]

    tool_bitmap_size = (24, 24)

    # if an editor is marked as transient, it will be replaced if it's the
    # active frame when a new frame is added.
    transient = False

    @property
    def is_dirty(self):
        return False

    @property
    def can_copy(self):
        return False

    @property
    def can_paste(self):
        return False

    @property
    def can_undo(self):
        return False

    @property
    def can_redo(self):
        return False

    @property
    def best_file_save_dir(self):
        attempts = []
        if self.last_saved_uri:
            # try most recent first
            attempts.append(self.last_saved_uri)
        if self.last_loaded_uri:
            # try directory of last loaded file next
            attempts.append(self.last_loaded_uri)
        if self.document and self.document.uri:
            # path of current file is the final try
            attempts.append(self.document.uri)

        print(("attempts for best_file_save_dir: %s" % str(attempts)))
        dirpath = ""
        for uri in attempts:
            uri_dir = os.path.dirname(uri)
            if os.path.exists(uri_dir):
                dirpath = uri_dir
                break

        return dirpath

    @property
    def title(self):
        uri = self.last_saved_uri or self.last_loaded_uri
        if uri:
            return os.path.basename(uri)
        return self.pretty_name

    @property
    def is_transient(self):
        return self.transient or self.__class__ == OmnivoreEditor

    def __init__(self, action_factory_lookup=None):
        self.tab_name = "Text"
        self.frame = None
        if action_factory_lookup is None:
            action_factory_lookup = {}
        self.action_factory_lookup = action_factory_lookup
        self.last_loaded_uri = None
        self.last_saved_uri = None
        self.document = None

    def prepare_destroy(self):
        print(f"prepare_destroy: {self.tab_name}")
        self.control = None
        self.frame = None

    def create_control(self, parent):
        return wx.StaticText(parent, -1, "Base class for Omnivore editors")

    def load(self, path, mime_info, args=None):
        pass

    def load_success(self, path, mime_info):
        self.last_loaded_uri = path
        from omnivore_framework.actions import open_recent
        open_recent.open_recent.append(path)

    @classmethod
    def can_edit_mime_exact(cls, mime_type):
        return False

    @classmethod
    def can_edit_mime_generic(cls, mime_type):
        return False

    @classmethod
    def can_edit_mime(cls, mime_type):
        return cls.can_edit_mime_exact(mime_type) or cls.can_edit_mime_generic(mime_type)

    def calc_usable_action(self, action_key):
        try:
            action_factory = self.action_factory_lookup[action_key]
        except KeyError:
            action_factory = action.find_action_factory(self.module_search_order, action_key)
            self.action_factory_lookup[action_key] = action_factory
        return action_factory(self, action_key)
