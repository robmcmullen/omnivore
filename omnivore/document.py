import sys
from collections import namedtuple

import numpy as np
import jsonpickle
import fs

from atrcopy import SegmentData, DefaultSegment, DefaultSegmentParser, errors, iter_parsers

from omnivore_framework.document import BaseDocument
from omnivore_framework.utils.nputil import to_numpy
from omnivore_framework.utils.events import EventHandler

import logging
log = logging.getLogger(__name__)


class SegmentedDocument(BaseDocument):
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

    def __init__(self, raw_bytes=b"", style=b""):
        BaseDocument.__init__(self, raw_bytes)
        if not style:
            style = np.zeros(len(self), dtype=np.uint8)
        self.style = to_numpy(style)
        self.segment_parser = None

        r = SegmentData(self.raw_bytes, self.style)
        self.segments = list([DefaultSegment(r, 0)])
        self.user_segments = []
        self.document_memory_map = {}

        self.priority_level_refresh_event = EventHandler(self)
        self.emulator_breakpoint_event = EventHandler(self)

        # default emulator class, if the user selects something different than
        # the normal default. This is usually None, which means that omnivore
        # will chose the best emulator based on the type of this segment
        self.emulator_class_override = None

    @property
    def can_resize(self):
        return self.segments and self.container_segment.can_resize

    #### object methods

    def __str__(self):
        lines = []
        lines.append(f"Document: id={self.document_id}, mime={self.mime}, {self.uri}")
        if log.isEnabledFor(logging.DEBUG):
            lines.append("parser: %s" % self.segment_parser)
            lines.append("segments:")
            for s in self.segment_parser.segments:
                lines.append("  %s" % s)
            lines.append("user segments:")
            for s in self.user_segments:
                lines.append("  %s" % s)
        return "\n".join(lines)

    #### loaders
    def load_from_atrcopy_parser(self, file_metadata, editor_metadata):
        # make sure a parser exists; it probably does in most cases, but
        # emulators use a source document to create the EmulationDocument, and
        # the EmulationDocument won't have a parser assigned if it isn't being
        # restored from a .omnivore file
        if self.segment_parser is None:
            self.set_segments(file_metadata["atrcopy_parser"])
        self.restore_extra_from_dict(editor_metadata)

    def load_from_raw_data(self, data, file_metadata, editor_metadata):
        self.raw_bytes = data
        self.parse_segments([])
        self.restore_extra_from_dict(editor_metadata)

    #### serialization methods

    def get_document_template_metadata(self, file_metadata):
        mime = file_metadata["mime"]
        log.debug("extra metadata_before_editor: parser=%s, mime=%s" % (file_metadata["atrcopy_parser"], mime))
        extra = self.calc_unserialized_template(mime)
        if extra:
            log.debug("extra metadata: loaded template for %s" % mime)
        if 'machine mime' not in extra:
            extra['machine mime'] = mime

        # if 'serialized user segments' in editor_metadata and 'user segments' in extra:
        #     # Ignore the segments from the built-in data if serialized user
        #     # segments exist in the .omnivore file. Any built-in segments will
        #     # have already been saved in the .omnivore file, so this prevents
        #     # duplication.
        #     del extra['user segments']
        return extra

    def serialize_extra_to_dict(self, mdict):
        BaseDocument.serialize_extra_to_dict(self, mdict)

        mdict["segment parser"] = self.segment_parser
        mdict["serialized user segments"] = list(self.user_segments)
        self.container_segment.serialize_extra_to_dict(mdict)
        mdict["document memory map"] = sorted([list(i) for i in list(self.document_memory_map.items())])  # save as list of pairs because json doesn't allow int keys for dict

    def restore_extra_from_dict(self, e):
        BaseDocument.restore_extra_from_dict(self, e)

        if 'segment parser' in e:
            parser = e['segment parser']
            parser.reconstruct_segments(self.container_segment.rawdata)
            self.set_segments(parser)
        if 'user segments' in e:
            # Segment objects created by the utils.extra_metadata module
            for s in e['user segments']:
                self.add_user_segment(s, replace=True)
        if 'serialized user segments' in e:
            # Segments that need to be restored via deserialization
            for s in e['serialized user segments']:
                s.reconstruct_raw(self.container_segment.rawdata)
                self.add_user_segment(s, replace=True)
        self.container_segment.restore_extra_from_dict(e)
        if 'document memory map' in e:
            self.document_memory_map = dict(e['document memory map'])

        # One-time call to enforce the new requirement that bytes marked with
        # the comment style must have text associated with them.
        self.container_segment.fixup_comments()

    #### convenience methods

    def calc_layout_template_name(self, task_id):
        return "%s.default_layout" % task_id

    def parse_segments(self, parser_list):
        parser_list.append(DefaultSegmentParser)
        r = SegmentData(self.raw_bytes, self.style)
        for parser in parser_list:
            try:
                s = parser(r)
                break
            except errors.InvalidSegmentParser:
                pass
        self.set_segments(s)

    def set_segments(self, parser):
        log.debug("setting parser: %s" % parser)
        self.segment_parser = parser
        self.segments = []
        self.segments.extend(parser.segments)
        self.segments.extend(self.user_segments)

    def set_segment_parser(self, parser_cls):
        log.debug("setting parser: %s" % parser_cls)
        self.segment_parser = parser_cls(self.container_segment.rawdata)
        self.segments = []
        self.segments.extend(self.segment_parser.segments)
        self.segments.extend(self.user_segments)

    def parse_sub_segments(self, segment):
        mime, parser = iter_parsers(segment.rawdata)
        if parser is not None:
            index = self.find_segment_index(segment)
            self.segments[index + 1:index + 1] = parser.segments[1:] # Skip the "All" segment as it would just be a duplicate of the expanded segment
        return parser

    @property
    def container_segment(self):
        return self.segments[0]

    @property
    def contained_segments(self):
        return iter(self.segments[1:])

    def expand_container(self, size):
        c = self.container_segment
        if c.can_resize:
            oldsize, newsize = c.resize(size)
            for s in self.contained_segments:
                s.replace_data(c)
            self.raw_bytes = c.data
            start, end = oldsize, newsize
            r = c.rawdata[start:end]
            s = DefaultSegment(r, 0)
            return s

    def add_user_segment(self, segment, replace=False):
        if replace:
            current = self.find_matching_user_segment(segment)
            if current is not None:
                log.debug("replacing %s with %s" % (current, segment))
                self.replace_user_segment(current, segment)
                return
        self.user_segments.append(segment)
        self.segments.append(segment)

    def is_user_segment(self, segment):
        return segment in self.user_segments

    def delete_user_segment(self, segment):
        self.user_segments.remove(segment)
        self.segments.remove(segment)

    def replace_user_segment(self, current_segment, segment):
        try:
            i = self.user_segments.index(current_segment)
            self.user_segments[i:i+1] = [segment]
            i = self.segments.index(current_segment)
            self.segments[i:i+1] = [segment]
        except ValueError:
            log.error("Attempted to replace segment %s that isn't here!")

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

    def find_initial_visible_segment(self, linked_base, default=0):
        """Hook for subclasses to force a particular segment to be viewed on
        document load. Used in emulators to show the main memory, which is not
        usually the first segment in the list.

        By default, it does show the first segment.
        """
        linked_base.find_segment(self.segments[default], refresh=False)

    #### Baseline document for comparisons

    def init_baseline(self, metadata, raw_bytes):
        d = SegmentedDocument(metadata=metadata, raw_bytes=raw_bytes)
        d.parse_segments([])
        self.baseline_document = d

    def del_baseline(self):
        self.baseline_document = None

    def update_baseline(self):
        if self.baseline_document is not None:
            self.change_count += 1
            self.container_segment.compare_segment(self.baseline_document.container_segment)

    def clear_baseline(self):
        self.change_count += 1
        self.container_segment.clear_style_bits(diff=True)

    @property
    def has_baseline(self):
        return self.baseline_document is not None

    @classmethod
    def create_from_segments(cls, root, user_segments):
        doc = cls(raw_bytes=root.data, style=root.style)
        Parser = namedtuple("Parser", ['segments'])
        segs = [root]
        p = Parser(segments=segs)
        doc.user_segments = list(user_segments)
        doc.set_segments(p)
        return doc
