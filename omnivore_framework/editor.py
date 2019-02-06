import sys
import importlib
import pkgutil
import inspect

import wx

from . import action
from . import errors

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def iter_namespace(ns_pkg):
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")

def get_editors():
    import omnivore_framework.editors
    editors = []
    for finder, name, ispkg in iter_namespace(omnivore_framework.editors):
        try:
            mod = importlib.import_module(name)
        except ImportError as e:
            log.error(f"get_editors: Error importing moduole {name}: {e}")
        else:
            log.debug(f"get_editors: Found module {name}")
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


class OmnivoreEditor:
    name = "omnivore_framework_base_editor"
    pretty_name = "Omnivore Framework Base Editor"

    menubar_desc = [
    ["File", "new_file", "open_file", None, "save_file", "save_as", None, "quit"],
    ["Edit", "undo", "redo", None, "copy", "cut", "paste", None, "prefs"],
    ["Help", "about"],
    ]

    toolbar_desc = [
        "new_file", "open_file", "save_file", None, "undo", "redo", None, "copy", "cut", "paste"
    ]

    module_search_order = ["omnivore_framework.actions"]

    tool_bitmap_size = (24, 24)

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
    def title(self):
        uri = self.last_saved_uri or self.last_loaded_uri
        if uri:
            return os.path.basename(uri)
        return self.pretty_name

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

    def load(self, path, mime_info):
        pass

    def load_success(self, path, mime_info):
        self.last_loaded_uri = path

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
            action_factory = None
            for mod in self.module_search_order:
                action_factory = action.find_action_factory(mod, action_key)
                if action_factory is not None:
                    break
            else:
                raise KeyError(f"no action factory found for {action_key}")
            self.action_factory_lookup[action_key] = action_factory
        return action_factory(self, action_key)
