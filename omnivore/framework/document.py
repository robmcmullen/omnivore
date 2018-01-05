import os
import types
import cStringIO as StringIO
import uuid

import numpy as np
import fs
from fs.opener import opener
import jsonpickle

# Enthought library imports.
from traits.api import HasTraits, Trait, TraitHandler, Int, Any, List, Set, Bool, Event, Dict, Set, Unicode, Property, Str

from omnivore.utils.command import UndoStack
from omnivore.utils.file_guess import FileGuess, FileMetadata
import omnivore.utils.jsonutil as jsonutil

import logging
log = logging.getLogger(__name__)


class DocumentError(RuntimeError):
    pass


class TraitNumpyConverter(TraitHandler):
    """Trait validator to convert bytes to numpy array"""

    def validate(self, object, name, value):
        if type(value) is np.ndarray:
            return value
        elif type(value) is types.StringType:
            return np.fromstring(value, dtype=np.uint8)
        self.error(object, name, value)

    def info(self):
        return '**a string or numpy array**'


class BaseDocument(HasTraits):

    # Class properties

    json_expand_keywords = {}

    # Traits

    undo_stack = Any

    metadata = Any

    name = Property(Unicode, depends_on='metadata')

    uri = Property(Unicode, depends_on='metadata')

    read_only = Property(Bool, depends_on='metadata')

    document_id = Int(-1)

    uuid = Str

    last_task_id = Str

    baseline_document = Any(transient=True)

    bytes = Trait("", TraitNumpyConverter())

    segments = List

    extra_metadata = Dict

    # Trait events to provide view updating

    undo_stack_changed = Event

    data_model_changed = Event  # update the data model because of a structural change to the data

    byte_values_changed = Event  # but not the size of the bytes array. That's not handled yet

    byte_style_changed = Event  # only styling info may have changed, not any of the data byte values

    recalc_event = Event  # recalculate view due to metadata change

    refresh_event = Event  # update the view on screen

    change_count = Int()

    can_revert = Property(Bool, depends_on='metadata')

    permute = Any

    load_error = Str(transient=True)

    global_resource_cleanup_functions = List([])

    #### trait default values

    def _metadata_default(self):
        return FileMetadata(uri="")

    def _undo_stack_default(self):
        return UndoStack()

    def _bytes_default(self):
        return ""

    def _uuid_default(self):
        return str(uuid.uuid4())

    #### trait property getters

    def _get_name(self):
        return self.metadata.name or 'Untitled'

    def _get_uri(self):
        return self.metadata.uri

    def _set_uri(self, uri):
        self.metadata.uri = uri

    def _get_read_only(self):
        return self.metadata.read_only

    def _set_read_only(self, read_only):
        self.metadata.read_only = read_only

    def _get_can_revert(self):
        return self.metadata.uri != ""

    @property
    def menu_name(self):
        if self.uri:
            return "%s (%s)" % (self.name, self.uri)
        return self.name

    @property
    def root_name(self):
        name, _ = os.path.splitext(self.name)
        return name

    @classmethod
    def get_blank(cls):
        return cls(bytes="")

    def __str__(self):
        return "Document(id=%s): %s" % (self.document_id, self.metadata.uri)

    def __len__(self):
        return np.alen(self.bytes)

    def __getitem__(self, val):
        return self.bytes[val]

    @property
    def dirty(self):
        return self.undo_stack.is_dirty()

    def to_bytes(self):
        return self.bytes.tostring()

    def load_permute(self, editor):
        if self.permute:
            self.permute.load(self, editor)

    def filesystem_path(self):
        try:
            fs_, relpath = fs.opener.opener.parse(self.uri)
            if fs_.hassyspath(relpath):
                return fs_.getsyspath(relpath)
        except fs.errors.FSError:
            pass
        return None

    @property
    def bytestream(self):
        return StringIO.StringIO(self.bytes)

    # serialization

    def load_metadata(self, guess):
        extra = self.load_extra_metadata(guess)
        self.restore_extra_from_dict(extra)
        self.extra_metadata = extra

    def load_extra_metadata(self, guess):
        return self.load_filesystem_extra_metadata()

    def load_filesystem_extra_metadata(self):
        """ Find any extra metadata associated with the document, typically
        used to load an extra file off the disk.
        
        If successful, return a dict to be processed by init_extra_metadata
        """
        uri = self.get_filesystem_extra_metadata_uri()
        if uri is None:
            return {}
        try:
            guess = FileGuess(uri)
        except fs.errors.FSError, e:
            log.error("File load error: %s" % str(e))
            return {}
        log.info("Loading metadata file: %s" % uri)
        try:
            b = guess.bytes
            if b.startswith("#"):
                header, b = b.split("\n", 1)
            unserialized = jsonpickle.loads(b)
        except ValueError, e:
            log.error("JSON parsing error for extra metadata in %s: %s" % (uri, str(e)))
            unserialized = {}
        except AttributeError, e:
            log.error("JSON library error: %s: %s" % (uri, str(e)))
            unserialized = {}
            raise DocumentError("JSON library error: % s" % str(e))
        return unserialized

    def get_filesystem_extra_metadata_uri(self):
        """ Get filename of file used to store extra metadata
        """
        return None

    def get_metadata_for(self, task):
        """Return extra metadata for the particular task

        """
        # Each task has its own section in the metadata so they can save stuff
        # without fear of stomping on another task's data. Also, when saving,
        # they can overwrite their task stuff without changing an other task's
        # info so that other task's stuff can be re-saved even if that task
        # wasn't used in this editing session.
        try:
            return self.extra_metadata[task.editor_id]
        except KeyError:
            log.info("%s not in task specific metadata; falling back to old metadata storage" % task.editor_id)

        # For compatibility with pre-1.0 versions of Omnivore which stored
        # metadata for all tasks in the root directory
        return self.extra_metadata

    def init_extra_metadata_dict(self, editor):
        """ Creates new metadata dictionary for metadata to be serialized

        The returned dict includes all the current document properties and all
        the task specific metadata in the originally loaded document.

        The task specific metadata will be replaced by values in the current
        task.
        """
        mdict = {}
        known = set(editor.task.known_editor_ids)
        for k, v in self.extra_metadata.iteritems():
            if k in known:
                mdict[k] = dict(v)
        self.serialize_extra_to_dict(mdict)
        return mdict

    def store_task_specific_metadata(self, editor, mdict, task_dict):
        # FIXME: should handle all tasks that have changed in this edit
        # session, not just the one that is being saved.
        task_name = editor.task.editor_id
        mdict[task_name] = task_dict
        mdict["last_task_id"] = task_name

    def serialize_extra_to_dict(self, mdict):
        """Save extra metadata to a dict so that it can be serialized
        """
        mdict["document uuid"] = self.uuid
        if self.baseline_document is not None:
            mdict["baseline document"] = self.baseline_document.metadata.uri

    def restore_extra_from_dict(self, e):
        log.debug("restoring extra metadata: %s" % str(e))
        if 'document uuid' in e:
            self.uuid = e['document uuid']
        if 'baseline document' in e:
            try:
                self.load_baseline(e['baseline document'])
            except DocumentError:
                pass
        if 'last_task_id' in e:
            self.last_task_id = e['last_task_id']

    def load_baseline(self, uri, confirm_callback=None):
        if confirm_callback is None:
            confirm_callback = lambda a: True
        try:
            guess = FileGuess(uri)
        except Exception, e:
            log.error("Problem loading baseline file %s: %s" % (uri, str(e)))
            raise DocumentError(str(e))
        bytes = guess.numpy
        difference = len(bytes) - len(self)
        if difference > 0:
            if confirm_callback("Truncate baseline data by %d bytes?" % difference, "Baseline Size Difference"):
                bytes = bytes[0:len(self)]
            else:
                bytes = []
        elif difference < 0:
            if confirm_callback("Pad baseline data with %d zeros?" % (-difference), "Baseline Size Difference"):
                bytes = np.pad(bytes, (0, -difference), "constant", constant_values=0)
            else:
                bytes = []
        if len(bytes) > 0:
            self.init_baseline(guess.metadata, bytes)
        else:
            self.del_baseline()

    def save_to_uri(self, uri, editor, saver=None, save_metadata=True):
        # Have to use a two-step process to write to the file: open the
        # filesystem, then open the file.  Have to open the filesystem
        # as writeable in case this is a virtual filesystem (like ZipFS),
        # otherwise the write to the actual file will fail with a read-
        # only filesystem error.
        if saver is None:
            bytes = self.bytes.tostring()
        else:
            bytes = saver(self, editor)

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
            mdict = self.init_extra_metadata_dict(editor)
            task_metadata = dict()
            editor.to_metadata_dict(task_metadata, self)
            self.store_task_specific_metadata(editor, mdict, task_metadata)
            if mdict:
                relpath += ".omnivore"
                log.debug("saving extra metadata to %s" % relpath)
                jsonpickle.set_encoder_options("json", sort_keys=True, indent=4)
                bytes = jsonpickle.dumps(mdict)
                text = jsonutil.collapse_json(bytes, 8, self.json_expand_keywords)
                header = editor.get_extra_metadata_header()
                fh = fs.open(relpath, 'wb')
                fh.write(header)
                fh.write(text)
                fh.close()

        fs.close()

    #### Cleanup functions

    def add_cleanup_function(self, func):
        # Prevent same function from being added multiple times
        if func not in self.global_resource_cleanup_functions:
            self.global_resource_cleanup_functions.append(func)

    def global_resource_cleanup(self):
        for f in self.global_resource_cleanup_functions:
            log.debug("Calling cleanup function %s" % f)
            f()
