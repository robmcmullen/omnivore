from collections import namedtuple

import numpy as np
import jsonpickle
import fs

from omnivore.framework.document import BaseDocument, TraitNumpyConverter
from omnivore.utils.file_guess import FileGuess

# Enthought library imports.
from traits.api import Trait, Any, List, Event, Dict, Property, Bool

from atrcopy import SegmentData, DefaultSegment, DefaultSegmentParser, InvalidSegmentParser, iter_parsers

import logging
log = logging.getLogger(__name__)


class SegmentedDocument(BaseDocument):
    style = Trait("", TraitNumpyConverter())

    segment_parser = Any

    user_segments = List

    emulator = Any

    emulator_list = None

    emulator_change_event = Event

    can_resize = Property(Bool, depends_on='segments')

    document_memory_map = Dict

    #### trait default values

    def _style_default(self):
        return np.zeros(len(self), dtype=np.uint8)

    def _segments_default(self):
        r = SegmentData(self.bytes,self.style)
        return list([DefaultSegment(r, 0)])

    def _program_memory_map_default(self):
        return dict()

    #### trait property getters

    def _get_can_resize(self):
        return self.segments and self.container_segment.can_resize

    #### serialization methods

    def load_extra_metadata(self, guess):
        # don't load check_builtin until now because it causes some circular
        # imports
        from omnivore8bit.utils.extra_metadata import check_builtin

        log.debug("extra metadata: parser=%s" % guess.parser)
        self.set_segments(guess.parser)
        extra = check_builtin(self)
        if 'machine mime' not in extra:
            extra['machine mime'] = self.metadata.mime
        loaded_extra = self.load_filesystem_extra_metadata()
        if 'serialized user segments' in loaded_extra and 'user segments' in extra:
            # Ignore the segments from the built-in data if serialized user
            # segments exist in the .omnivore file. Any built-in segments will
            # have already been saved in the .omnivore file, so this prevents
            # duplication.
            del extra['user segments']

        # Overwrite any builtin stuff with saved data from the user
        extra.update(loaded_extra)
        return extra

    def get_filesystem_extra_metadata_uri(self):
        """ Get filename of file used to store extra metadata
        """
        return self.metadata.uri + ".omnivore"

    def serialize_extra_to_dict(self, mdict):
        BaseDocument.serialize_extra_to_dict(self, mdict)

        mdict["segment parser"] = self.segment_parser
        mdict["serialized user segments"] = list(self.user_segments)
        self.container_segment.serialize_extra_to_dict(mdict)
        emu = self.emulator
        if emu and not 'system default' in emu:
            mdict["emulator"] = self.emulator
        mdict["document memory map"] = sorted([list(i) for i in self.document_memory_map.iteritems()])  # save as list of pairs because json doesn't allow int keys for dict

    def restore_extra_from_dict(self, e):
        BaseDocument.restore_extra_from_dict(self, e)

        if 'segment parser' in e:
            parser = e['segment parser']
            for s in parser.segments:
                s.reconstruct_raw(self.container_segment.rawdata)
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
        if 'emulator' in e:
            self.emulator = e['emulator']
        if 'document memory map' in e:
            self.document_memory_map = dict(e['document memory map'])

        # One-time call to enforce the new requirement that bytes marked with
        # the comment style must have text associated with them.
        self.container_segment.fixup_comments()

    #### convenience methods

    def __str__(self):
        lines = []
        lines.append("Document(id=%s): %s" % (self.document_id, self.metadata.uri))
        if log.isEnabledFor(logging.DEBUG):
            lines.append("parser: %s" % self.segment_parser)
            lines.append("segments:")
            for s in self.segment_parser.segments:
                lines.append("  %s" % s)
            lines.append("user segments:")
            for s in self.user_segments:
                lines.append("  %s" % s)
        return "\n".join(lines)

    def parse_segments(self, parser_list):
        parser_list.append(DefaultSegmentParser)
        r = SegmentData(self.bytes, self.style)
        for parser in parser_list:
            try:
                s = parser(r)
                break
            except InvalidSegmentParser:
                pass
        self.set_segments(s)

    def set_segments(self, parser):
        log.debug("setting parser: %s" % parser)
        self.segment_parser = parser
        self.segments = []
        self.segments.extend(parser.segments)
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
            self.bytes = c.data
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
            if len(s) == len(segment) and s.start_addr == segment.start_addr and s.name == segment.name:
                return True
        return False

    def find_matching_user_segment(self, segment):
        for s in self.user_segments:
            if len(s) == len(segment) and s.start_addr == segment.start_addr and s.name == segment.name:
                return s
        return None

    def find_segment_index(self, segment):
        try:
            return self.segments.index(segment)
        except ValueError:
            return -1

    def find_segment_index_by_name(self, name):
        for i, s in enumerate(self.segments):
            if s.name == name:
                return i
        return -1

    def find_segment_by_name(self, name):
        for s in self.segments:
            if s.name == name:
                return s
        raise ValueError("No segment with name %s" % name)

    def find_segments_in_range(self, addr):
        """Assuming segments had a start_addr param, find first segment that
        has addr as a valid address
        """
        found = []
        for i, s in enumerate(self.segments):
            if s.start_addr > 0 and addr >= s.start_addr and addr < (s.start_addr + len(s)):
                found.append((i, s, addr - s.start_addr))
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

    #### Emulator

    def set_emulator(self, emu):
        self.emulator = emu
        self.emulator_change_event = True

    def add_emulator(self, task, emu):
        self.emulator_list.append(emu)
        self.remember_emulators(task.window.application)
        task.machine_menu_changed = self

    @classmethod
    def init_emulators(cls, editor):
        if cls.emulator_list is None:
            cls.emulator_list = editor.window.application.get_json_data("emulator_list", [])
            default = editor.window.application.get_json_data("system_default_emulator", None)

            if default is None:
                default = cls.guess_system_default_emulator()
            if not cls.is_known_emulator(default):
                cls.emulator_list[0:0] = [default]

    @classmethod
    def remember_emulators(cls, application):
        e_list = []
        default = None
        for emu in cls.emulator_list:
            if 'system default' in emu:
                default = emu
            else:
                if 'system default' in emu:
                    # remove system default tags on any other emulator
                    del emu['system default']
                e_list.append(emu)
        if e_list:
            application.save_json_data("emulator_list", e_list)
        if default:
            application.save_json_data("system_default_emulator", default)

    @classmethod
    def is_known_emulator(cls, emu):
        for e in cls.emulator_list:
            if e == emu:
                return True
        return False

    @classmethod
    def guess_system_default_emulator(cls):
        if sys.platform == "win32":
            exe = "Altirra.exe"
        elif sys.platform == "darwin":
            exe = "Atari800MacX"
        else:
            exe = "atari800"
        emu = {'exe': exe,
               'args': "",
               'name': "system default: %s" % exe,
               'system default': True,
               }
        return emu

    @classmethod
    def get_system_default_emulator(cls, task):
        try:
            default = cls.emulator_list[0]
        except IndexError:
            # somehow, all the elements have been removed!
            default = cls.guess_system_default_emulator()
            cls.remember_emulators(task.window.application)
            task.machine_menu_changed = cls
        return default

    @classmethod
    def set_system_default_emulator(cls, task, emu):
        emu = dict(emu)  # copy to make sure we're not referencing an item in the existing emulator_list
        emu['system default'] = True
        emu['name'] = "system default: %s" % emu['name']
        default = cls.emulator_list[0]
        if 'system default' not in default:
            cls.emulator_list[0:0] = [emu]
        else:
            cls.emulator_list[0] = emu
        cls.remember_emulators(task.window.application)
        task.machine_menu_changed = cls

    @classmethod
    def get_user_defined_emulator_list(cls):
        """Return list of user defined emulators (i.e. not including the system
        default emulator
        """
        emus = []
        for e in cls.emulator_list:
            if 'system default' not in e:
                emus.append(e)
        return emus

    @classmethod
    def set_user_defined_emulator_list(cls, task, emus):
        default = None
        for e in cls.emulator_list:
            if 'system default' in e:
                default = e
        emus[0:0] = [default]
        cls.emulator_list = emus
        cls.remember_emulators(task.window.application)
        task.machine_menu_changed = cls

    #### Baseline document for comparisons

    def init_baseline(self, metadata, bytes):
        d = SegmentedDocument(metadata=metadata, bytes=bytes)
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
        doc = cls(bytes=root.data, style=root.style)
        Parser = namedtuple("Parser", ['segments'])
        segs = [root]
        p = Parser(segments=segs)
        doc.user_segments = list(user_segments)
        doc.set_segments(p)
        return doc
