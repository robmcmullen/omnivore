import os
import types
import cStringIO as StringIO
import uuid

import numpy as np
import fs

# Enthought library imports.
from traits.api import HasTraits, Trait, TraitHandler, Int, Any, List, Set, Bool, Event, Dict, Set, Unicode, Property, Str

from omnivore.utils.command import UndoStack
from omnivore.utils.file_guess import FileGuess, FileMetadata

import logging
log = logging.getLogger(__name__)


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
    undo_stack = Any

    metadata = Any

    name = Property(Unicode, depends_on='metadata')

    uri = Property(Unicode, depends_on='metadata')

    read_only = Property(Bool, depends_on='metadata')

    document_id = Int(-1)

    uuid = Str

    last_task_id = Str

    bytes = Trait("", TraitNumpyConverter())

    segments = List

    extra_metadata = Dict

    # Trait events to provide view updating

    undo_stack_changed = Event

    byte_values_changed = Event  # but not the size of the bytes array. That's not handled yet

    byte_style_changed = Event  # only styling info may have changed, not any of the data byte values

    change_count = Int()

    can_revert = Property(Bool, depends_on='metadata')

    permute = Any

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
