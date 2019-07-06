import os
import types
import io as BytesIO
import uuid

import numpy as np
import jsonpickle

# Enthought library imports.
from .events import EventHandler
from .utils.command import UndoStack
from .utils import jsonutil
from .utils.nputil import to_numpy
from .utils.pyutil import get_plugins
from .persistence import get_template
from . import filesystem
from .filesystem import fsopen as open
from . import errors

import logging
log = logging.getLogger(__name__)


def find_document_class_for_file(file_metadata):
    """Find the "best" document for a given MIME type string.

    First attempts all documents with exact matches for the MIME string,
    and if no exact matches are found, returns through the list to find
    one that can edit that class of MIME.
    """
    all_documents = get_plugins('sawx.documents', SawxDocument)
    log.debug(f"find_document_class_for_file: file={file_metadata}, known documents: {all_documents}")
    matching_documents = [document for document in all_documents if document.can_load_file_exact(file_metadata)]
    log.debug(f"find_document_class_for_file: exact matches: {matching_documents}")

    if matching_documents:
        return matching_documents[0]

    # Try generic matches if all else fails
    for document in all_documents:
        if document.can_load_file_generic(file_metadata):
            return document
    raise errors.UnsupportedFileType(f"No document available for {file_metadata}")


def identify_document(file_metadata):
    doc_cls = find_document_class_for_file(file_metadata)
    return doc_cls(file_metadata)


class SawxDocument:
    # Class properties

    json_expand_keywords = {}

    session_save_file_extension = ""

    def __init__(self, file_metadata):
        self.undo_stack = UndoStack()
        self.extra_metadata = {}
        self.load(file_metadata)
        self.uuid = str(uuid.uuid4())
        self.change_count = 0
        self.permute = None
        self.baseline_document = None

        # events
        self.recalc_event = EventHandler(self)
        self.structure_changed_event = EventHandler(self)
        self.byte_values_changed_event = EventHandler(self)  # and possibly style, but size of array remains unchanged

        self.byte_style_changed_event = EventHandler(self)  # only styling info may have changed, not any of the data byte values

    def load(self, file_metadata):
        if file_metadata is None:
            self.create_empty()
        else:
            self.file_metadata = file_metadata
            raw = self.load_raw_data()
            self.raw_data = self.calc_raw_data(raw)
            self.load_session()

    def load_raw_data(self):
        fh = open(self.uri, 'rb')
        return fh.read()

    def calc_raw_data(self, raw):
        return to_numpy(raw)

    def create_empty(self):
        self.raw_data = np.zeros(0, dtype=np.uint8)
        self.file_metadata = {'uri': '', 'mime': "application/octet-stream"}

    @property
    def can_revert(self):
        return self.uri != ""

    @property
    def uri(self):
        return self.file_metadata['uri']

    @property
    def mime(self):
        return self.file_metadata['mime']

    @property
    def name(self):
        return os.path.basename(self.uri)

    @property
    def menu_name(self):
        if self.uri:
            return "%s (%s)" % (self.name, self.uri)
        return self.name

    @property
    def root_name(self):
        name, _ = os.path.splitext(self.name)
        return name

    @property
    def extension(self):
        _, ext = os.path.splitext(self.name)
        return ext

    @property
    def is_on_local_filesystem(self):
        try:
            self.filesystem_path()
        except OSError:
            return False
        return True

    @classmethod
    def get_blank(cls):
        return cls(raw_data=b"")

    def __str__(self):
        return f"Document: uuid={self.uuid}, mime={self.mime}, {self.uri}"

    def __len__(self):
        return np.alen(self.raw_data)

    def __getitem__(self, val):
        return self.raw_data[val]

    @property
    def is_dirty(self):
        return self.undo_stack.is_dirty()

    def to_bytes(self):
        return self.raw_data.tostring()

    def load_permute(self, editor):
        if self.permute:
            self.permute.load(self, editor)

    def filesystem_path(self):
        return filesystem.filesystem_path(self.uri)

    @property
    def bytestream(self):
        return BytesIO.BytesIO(self.raw_data)

    # serialization

    def load_session(self):
        d = self.calc_default_session()
        last = self.load_last_session()
        d.update(last)
        self.last_session = d
        self.restore_session(d)

    def calc_default_session(self):
        mime = self.mime
        log.debug(f"calc_default_session: looking for {mime}")
        try:
            text = get_template(mime)
            log.debug(f"calc_default_template: found template for {mime}")
        except OSError:
            log.debug(f"calc_default_template: no template for {mime}")
            e = {}
        else:
            e = jsonutil.unserialize(mime, text)
        return e

    def load_last_session(self):
        session_info = {}
        ext = self.session_save_file_extension
        if ext:
            uri = self.uri + ext
            try:
                fh = open(uri, 'r')
                text = fh.read()
            except IOError:
                log.debug(f"load_last_session: no metadata found at {uri}")
                pass
            else:
                try:
                    session_info = jsonutil.unserialize(uri, text)
                except ValueError as e:
                    log.error(f"invalid data in {uri}: {e}")
        return session_info

    def serialize_session(self, mdict):
        """Save session information to a dict so that it can be serialized
        """
        mdict["document uuid"] = self.uuid
        if self.baseline_document is not None:
            mdict["baseline document"] = self.baseline_document.metadata.uri

    def restore_session(self, e):
        log.debug("restoring sesssion data: %s" % str(e))
        if 'document uuid' in e:
            self.uuid = e['document uuid']
        # if 'baseline document' in e:
        #     try:
        #         self.load_baseline(e['baseline document'])
        #     except DocumentError:
        #         pass
        if 'last_task_id' in e:
            self.last_task_id = e['last_task_id']

    def load_baseline(self, uri, confirm_callback=None):
        log.debug(f"loading baseline data from {uri}")
        if confirm_callback is None:
            confirm_callback = lambda a,b: True
        try:
            guess = FileGuess(uri)
        except Exception as e:
            log.error("Problem loading baseline file %s: %s" % (uri, str(e)))
            raise DocumentError(str(e))
        raw_data = guess.numpy
        difference = len(raw_data) - len(self)
        if difference > 0:
            if confirm_callback("Truncate baseline data by %d bytes?" % difference, "Baseline Size Difference"):
                raw_data = raw_data[0:len(self)]
            else:
                raw_data = []
        elif difference < 0:
            if confirm_callback("Pad baseline data with %d zeros?" % (-difference), "Baseline Size Difference"):
                raw_data = np.pad(raw_data, (0, -difference), "constant", constant_values=0)
            else:
                raw_data = []
        if len(raw_data) > 0:
            self.init_baseline(guess.metadata, raw_data)
        else:
            self.del_baseline()

    def save(self, uri=None):
        if uri is None:
            uri = self.uri
        if not self.verify_writeable_uri(uri):
            raise errors.ReadOnlyFilesystemError(uri)
        if self.verify_ok_to_save():
            raw_data = self.calc_raw_data_to_save()
            self.save_raw_data(uri, raw_data)
            self.file_metadata['uri'] = uri
            self.undo_stack.set_save_point()

    def verify_writeable_uri(self, uri):
        return filesystem.is_user_writeable_uri(uri)

    def verify_ok_to_save(self):
        return True

    def calc_raw_data_to_save(self):
        return self.raw_data.tostring()

    def save_raw_data(self, uri, raw_data):
        fh = open(uri, 'wb')
        log.debug("saving to %s" % uri)
        fh.write(raw_data)
        fh.close()

    def save_session(self, editor_id, editor_session):
        if not self.session_save_file_extension:
            log.debug("no filename extension for session data; not saving")
        else:
            s = {}
            self.serialize_session(s)
            if s and editor_session:
                s[editor_id] = editor_session
                jsonpickle.set_encoder_options("json", sort_keys=True, indent=4)
                text = jsonpickle.dumps(s)
                text = jsonutil.collapse_json(text, 8, self.json_expand_keywords)
                path = self.save_adjacent(self.session_save_file_extension, text)
                log.debug("saved session to {path}")
                return path

    def save_adjacent(self, ext, data, mode="w"):
        if ext:
            path = self.filesystem_path() + ext
            with open(path, mode) as fh:
                fh.write(data)
        else:
            raise RuntimeError(f"Must specify non-blank extension to write a file adjacent to the data file")
        return path

    #### Cleanup functions

    def add_cleanup_function(self, func):
        if not hasattr(self, "global_resource_cleanup_functions"):
            self.global_resource_cleanup_functions = []
        # Prevent same function from being added multiple times
        if func not in self.global_resource_cleanup_functions:
            self.global_resource_cleanup_functions.append(func)

    def global_resource_cleanup(self):
        if hasattr(self, "global_resource_cleanup_functions"):
            for f in self.global_resource_cleanup_functions:
                log.debug("Calling cleanup function %s" % f)
                f()

    #### file identification

    @classmethod
    def can_load_file_exact(cls, file_metadata):
        return False

    @classmethod
    def can_load_file_generic(cls, file_metadata):
        return False

    @classmethod
    def can_load_file(cls, file_metadata):
        return cls.can_load_file_exact(file_metadata) or cls.can_load_file_generic(file_metadata)
