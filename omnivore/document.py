import sys
from collections import namedtuple

import numpy as np
import jsonpickle

from atrip import Collection, Container, Segment, errors

from sawx.document import SawxDocument
from sawx.utils.nputil import to_numpy
from sawx.events import EventHandler

from .disassembler import DisassemblyConfig, valid_cpu_ids, cpu_name_to_id
from .utils.archutil import Labels, load_memory_map

import logging
log = logging.getLogger(__name__)


class DiskImageDocument(SawxDocument):
    """Document for atrcopy-parsed segmented files

    Events:

    During high framerate operations, some panels may not need to be updated
    very frequently so only those panels that absolutely need it will get a
    high priority refresh event. Others will get lower priority. An integer
    should be passed as this event's data; it is up to the viewers to decide
    what the value means. Confusingly, high priority levels are lower
    numbers! This could mean the number of frames to skip, but it's up to the
    viewers, really.

    """
    json_expand_keywords = {
        'linked bases': 2,
        'viewers': 2,
    }

    session_save_file_extension = ".omnivore"

    def __init__(self, file_metadata):
        self.document_memory_map = {}
        self._cpu = "6502"
        self._disassembler = None
        self._operating_system = "atari800"
        self._machine_labels = None
        SawxDocument.__init__(self, file_metadata)

        self.cpu_changed_event = EventHandler(self)

        # default emulator class, if the user selects something different than
        # the normal default. This is usually None, which means that omnivore
        # will chose the best emulator based on the type of this segment
        self.emulator_class_override = None

    @property
    def can_resize(self):
        return self.segments and self.collection.can_resize

    @property
    def labels(self):
        return self.machine_labels.labels

    @property
    def cpu(self):
        return self._cpu

    @cpu.setter
    def cpu(self, value):
        self._cpu = value
        self._disassembler = None
        self.cpu_changed_event(value)

    @property
    def operating_system(self):
        return self._operating_system

    @operating_system.setter
    def operating_system(self, value):
        self._operating_system = value
        self._machine_labels = None
        self.cpu_changed_event(value)

    @property
    def machine_labels(self):
        if self._machine_labels is None:
            self._machine_labels = load_memory_map(self._operating_system)
        return self._machine_labels

    @property
    def disassembler(self):
        if self._disassembler is None:
            default_cpu = cpu_name_to_id.get(self._cpu, 0)
            driver = DisassemblyConfig(default_cpu)
            # driver.register_parser(self._cpu, 0)
            self._disassembler = driver
        return self._disassembler

    #### object methods

    def __str__(self):
        lines = []
        lines.append(f"DiskImageDocument: uuid={self.uuid}, {self.collection}")
        if log.isEnabledFor(logging.DEBUG):
            lines.extend(self.collection.verbose_info.splitlines())
        return "\n---- ".join(lines)

    def __len__(self):
        # different that superclass; reports number of containers in collection
        return len(self.collection)

    #### loaders

    def load(self, file_metadata):
        log.debug(f"load: file_metadata={file_metadata}")
        collection = file_metadata["atrip_collection"]
        self.load_collection(collection, file_metadata)

    def load_collection(self, collection, file_metadata):
        self.collection = collection
        log.debug(f"load: found collection {self.collection}")
        self.file_metadata = file_metadata
        self.load_session()
        self.segments = list(self.collection.iter_segments())
        self.user_segments = []

    def calc_raw_data_to_save(self):
        return self.collection.calc_compressed_data()

    #### serialization methods

    def serialize_session(self, s):
        SawxDocument.serialize_session(self, s)
        s2 = {}
        self.collection.serialize_session(s2)
        s["atrip_session"] = s2

        s["serialized user segments"] = list(self.user_segments)
        s["document memory map"] = sorted([list(i) for i in list(self.document_memory_map.items())])  # save as list of pairs because json doesn't allow int keys for dict

    def restore_session(self, e):
        SawxDocument.restore_session(self, e)
        s2 = e.get("atrip_session", None)
        if s2 is not None:
            self.collection.restore_session(s2)
        if 'user segments' in e:
            # Segment objects created by the utils.extra_metadata module
            for s in e['user segments']:
                self.add_user_segment(s, replace=True)
        if 'serialized user segments' in e:
            log.warning("found serialized user segments from Omnivore 1.0. These will not be restored.")
        if 'document memory map' in e:
            self.document_memory_map = dict(e['document memory map'])

    #### convenience methods

    def calc_layout_template_name(self, task_id):
        return "%s.default_layout" % task_id

    def find_matching_segment(self, segment):
        for s in self.segments:
            if len(s) == len(segment) and s.origin == segment.origin and s.name == segment.name:
                return True
        return False

    def find_matching_user_segment(self, segment):
        for s in self.user_segments:
            if len(s) == len(segment) and s.origin == segment.origin and s.name == segment.name:
                return s
        return None

    def find_segment_index(self, segment):
        try:
            return self.segments.index(segment)
        except ValueError:
            for i, s in enumerate(self.segments):
                if s.name == segment or s.uuid == segment:
                    return i
        return -1

    def find_segment_by_name(self, name):
        """Assuming segments had a origin param, find first segment that
        has addr as a valid address
        """
        for i, s in enumerate(self.segments):
            if s.name == name:
                return s
        return None

    def find_segments_in_range(self, addr):
        """Assuming segments had a origin param, find first segment that
        has addr as a valid address
        """
        found = []
        for i, s in enumerate(self.segments):
            if s.origin > 0 and addr >= s.origin and addr < (s.origin + len(s)):
                found.append((i, s, addr - s.origin))
        return found

    def find_segments_with_raw_index(self, raw_index):
        """Find all segments that contain the specified raw index

        The raw index points to a specific byte, so this will return all
        segments that have a view of this byte. This function ignores the
        segment start address because different views may have different start
        addresses; to find segments that contain a specific address, use
        find_segment_in_range.
        """
        found = []
        for i, s in enumerate(self.segments):
            try:
                index = s.get_index_from_base_index(raw_index)
                found.append((i, s, index))
            except IndexError:
                pass
        return found

    ##### Initial viewer defaults

    def find_initial_visible_segment(self, linked_base, default=None):
        """Hook for subclasses to force a particular segment to be viewed on
        document load. Used in emulators to show the main memory, which is not
        usually the first segment in the list.

        By default, it does show the first segment.
        """
        segment = self.collection.containers[0].segments[0]
        linked_base.find_segment(segment, refresh=False)

    #### Baseline document for comparisons

    def init_baseline(self, metadata, raw_data):
        d = DiskImageDocument(metadata=metadata, raw_data=raw_data)
        d.parse_segments([])
        self.baseline_document = d

    def del_baseline(self):
        self.baseline_document = None

    def update_baseline(self):
        if self.baseline_document is not None:
            self.change_count += 1
            self.collection.compare_segment(self.baseline_document.collection)

    def clear_baseline(self):
        self.change_count += 1
        self.collection.clear_style_bits(diff=True)

    @property
    def has_baseline(self):
        return self.baseline_document is not None

    @classmethod
    def create_from_segments(cls, root, user_segments):
        doc = cls(raw_data=root.data, style=root.style)
        Parser = namedtuple("Parser", ['segments'])
        segs = [root]
        p = Parser(segments=segs)
        doc.user_segments = list(user_segments)
        doc.set_segments(p)
        return doc

    #### file recognition

    @classmethod
    def can_load_file_exact(cls, file_metadata):
        return "atrip_identified" in file_metadata
 
    @classmethod
    def can_load_file_generic(cls, file_metadata):
        mime_type = file_metadata['mime']
        return mime_type == "application/octet-stream"
